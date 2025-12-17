"""
Scraper/LLM ingestion pipeline.

Steps:
1. Collect active scrape targets (or provided URLs).
2. Run the scraper for each URL (see scraper/ocp_scraper.py).
3. Persist scraped text immediately (filesystem + DB).
4. Send the cleaned text to the LLM pipeline for sentiment/summary.
5. Store structured results in Mention records for the dashboard.
"""

from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from typing import Any, Dict, Tuple
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from media_monitoring.llm_pipeline import run_llm_pipeline
from monitoring.models import Company, Mention, Source, SourceType, ScrapeTarget

import logging

logger = logging.getLogger(__name__)

try:
    from scraper.ocp_scraper import process_urls  # type: ignore
except Exception:  # noqa: BLE001
    process_urls = None

DEFAULT_COMPANY_NAME = "OCP"
DEFAULT_COMPANY_WEBSITE = "https://www.ocpgroup.ma"
DEFAULT_SOURCE_TYPE = "Web"


def _get_or_create_company() -> Company:
    qs = Company.objects.filter(name=DEFAULT_COMPANY_NAME).order_by("id")
    if qs.exists():
        company = qs.first()
        if company and not company.website:
            company.website = DEFAULT_COMPANY_WEBSITE
            company.save(update_fields=["website"])
        return company

    company = Company.objects.create(name=DEFAULT_COMPANY_NAME, website=DEFAULT_COMPANY_WEBSITE)
    return company


_SOURCE_CACHE: dict[str, Source] = {}


def _clean_article_text(text: str) -> str:
    """
    Remove HTML and template markers so the LLM gets plain article content.
    """
    if not text:
        return ""
    cleaned = re.sub(r"{%.*?%}", " ", text, flags=re.DOTALL)
    cleaned = re.sub(r"{{.*?}}", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _get_or_create_source(url: str) -> Source:
    parsed = urlparse(url)
    hostname = (parsed.netloc or parsed.path or url).strip() or url
    cache_key = hostname.lower()
    if cache_key in _SOURCE_CACHE:
        return _SOURCE_CACHE[cache_key]

    source_type, _ = SourceType.objects.get_or_create(name=DEFAULT_SOURCE_TYPE)
    display_name = hostname
    base_url = f"{parsed.scheme}://{hostname}" if parsed.scheme and hostname else url

    source, _ = Source.objects.get_or_create(
        name=display_name,
        type=source_type,
        defaults={"url": base_url},
    )
    if not source.url:
        source.url = base_url
        source.save(update_fields=["url"])
    if source.type_id != source_type.id:
        source.type = source_type
        source.save(update_fields=["type"])

    _SOURCE_CACHE[cache_key] = source
    return source


def _parse_sentiment_from_structured(structured: Dict[str, Any], model_output: str) -> Tuple[str, float | None, bool, str | None]:
    """
    Convert the LLM structured response (French) into persisted fields.
    """
    label_raw = structured.get("sentiment_label") or structured.get("sentiment_label_en") or "neutral"
    score = structured.get("sentiment_score")
    scores = structured.get("sentiment_scores") if isinstance(structured.get("sentiment_scores"), dict) else None
    risk_level = unicodedata.normalize("NFKD", str(structured.get("risk_level") or "")).encode("ascii", "ignore").decode().lower()

    is_urgent = bool(structured.get("is_urgent", False))
    urgency_reason = structured.get("urgency_reason")

    normalized = unicodedata.normalize("NFKD", str(label_raw)).encode("ascii", "ignore").decode().lower()
    if normalized in {"negative", "negatif"}:
        label = "negative"
    elif normalized in {"positive", "positif"}:
        label = "positive"
    elif normalized in {"neutral", "neutre"}:
        label = "neutral"
    else:
        # Fallback using keywords from raw model output.
        text = (model_output or "").lower()
        if "negatif" in text or "negative" in text:
            label = "negative"
        elif "positif" in text or "positive" in text:
            label = "positive"
        elif "neutre" in text or "neutral" in text:
            label = "neutral"
        else:
            label = "neutral"

    if score is None and scores:
        try:
            pos = float(scores.get("positif", 0))
            neg = float(scores.get("negatif", 0))
            score = (pos - neg) / 100.0
        except Exception:
            score = None

    if score is None:
        if label == "negative":
            score = -0.75
        elif label == "positive":
            score = 0.75
        else:
            score = 0.0

    if risk_level == "eleve" and not urgency_reason:
        urgency_reason = "Niveau de risque élevé détecté par le modèle"
    if risk_level == "eleve":
        is_urgent = True
    if label == "negative":
        is_urgent = True
        urgency_reason = urgency_reason or "Sentiment négatif détecté par le modèle"

    return label, score, is_urgent, urgency_reason


def _sanitize_display_title(candidate: str | None, fallback: str, sentiment_label: str) -> str:
    """
    Avoid storing system prompts or generic instructions as titles.
    Falls back to a neutral title mentioning the sentiment.
    """
    markers = [
        "output json only",
        "need to split into segments",
        "provide summary",
        "analyze the",
        "analyse the",
        "identify sentiment per segment",
    ]
    def is_prompt_like(value: str | None) -> bool:
        if not value:
            return False
        lower = value.lower()
        return any(marker in lower for marker in markers)

    if candidate and not is_prompt_like(candidate):
        return candidate[:280]

    if fallback and not is_prompt_like(fallback):
        return fallback[:280]

    return f"Mention detectee ({sentiment_label})"


def _store_scrape_result(scrape_result: Dict[str, Any], company: Company) -> Tuple[Mention, bool]:
    url = scrape_result.get("url") or ""
    text = scrape_result.get("text") or ""
    cleaned_text = _clean_article_text(text)
    page_title = scrape_result.get("title") or url
    saved_path = scrape_result.get("saved_path")

    source = _get_or_create_source(url)
    published_at = timezone.now()

    llm_result = run_llm_pipeline(url=url, scraped_data={"title": page_title, "content": cleaned_text}) or {}
    structured = llm_result.get("structured") if isinstance(llm_result, dict) else {}
    if structured is None:
        structured = {}
    model_output = llm_result.get("output") if isinstance(llm_result, dict) else ""
    if not llm_result.get("summary_valid"):
        error_detail = llm_result.get("error") if isinstance(llm_result, dict) else "Résumé manquant"
        raise ValueError(f"LLM summary invalid for {url}: {error_detail}")
    sentiment_label, sentiment_score, is_urgent, urgency_reason = _parse_sentiment_from_structured(
        structured or {}, model_output or ""
    )

    # Heuristic fallback: flag urgent if high-risk keywords appear in the scraped text.
    if not is_urgent and text:
        lowered = text.lower()
        keywords = ["scandal", "scandale", "الفضائح", "فضائح"]
        if any(k in lowered for k in keywords):
            is_urgent = True
            urgency_reason = urgency_reason or "Mot-clé critique détecté dans le texte"

    # Favor real scraped content for UI display; keep LLM details in raw_metadata.
    content_body = (
        cleaned_text
        or structured.get("article_summary")
        or structured.get("body")
        or structured.get("summary")
        or model_output
        or page_title
    )
    content_body = content_body[:4000]  # keep payload light for list rendering
    display_title = _sanitize_display_title(structured.get("title"), page_title or url, sentiment_label)

    mention_defaults = {
        "company": company,
        "source": source,
        "title": display_title,
        "content": content_body,
        "original_url": url,
        "published_at": published_at,
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "is_urgent": is_urgent,
        "urgency_reason": urgency_reason,
        "raw_metadata": {
            "scraper": {
                "saved_path": saved_path,
                "status": scrape_result.get("status"),
                "error": scrape_result.get("error"),
                "matched": scrape_result.get("matched"),
            },
            "raw_text": text,
            "llm": {
                "input": llm_result.get("input") if isinstance(llm_result, dict) else None,
                "output": model_output,
                "structured": structured,
                "error": llm_result.get("error") if isinstance(llm_result, dict) else None,
            },
        },
    }

    with transaction.atomic():
        mention, created = Mention.objects.update_or_create(
            original_url=url,
            defaults=mention_defaults,
        )

    return mention, created


def ingest_latest_articles(
    *,
    force: bool = False,
    max_articles_per_site: int = 0,
    refresh_interval_minutes: int = 0,
    urls: list[str] | None = None,
) -> Dict[str, Any]:
    """
    Run the scraper for provided URLs (or active ScrapeTarget entries) and
    persist results into the Mention table after LLM processing.
    """
    now_ts = timezone.now()
    summary: Dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "processed": 0,
        "matched": 0,
        "errors": 0,
        "total_seen": 0,
        "last_run": now_ts,
        "results": [],
    }

    if process_urls is None:
        summary["error"] = "Scraper module missing"
        return summary

    target_urls = urls or list(ScrapeTarget.objects.filter(is_active=True).values_list("url", flat=True))
    target_urls = [u for u in target_urls if u]
    if not target_urls:
        urls_file = Path("urls.txt")
        if urls_file.exists():
            target_urls = [line.strip() for line in urls_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            summary["info"] = f"Loaded {len(target_urls)} URLs from urls.txt"
        if not target_urls:
            summary["error"] = "No active scrape targets or urls.txt entries."
            logger.warning("No URLs to scrape. Add ScrapeTargets or urls.txt.")
            return summary

    logger.info("Ingestion: launching scraper for %d URL(s)", len(target_urls))

    try:
        scrape_summary = process_urls(target_urls)
    except Exception as exc:  # noqa: BLE001
        summary["error"] = str(exc)
        summary["errors"] = len(target_urls)
        return summary

    summary["processed"] = scrape_summary.get("processed", 0)
    summary["matched"] = scrape_summary.get("matched", 0)
    summary["errors"] = scrape_summary.get("errors", 0)
    summary["total_seen"] = summary["processed"]

    company = _get_or_create_company()

    for scrape_result in scrape_summary.get("results", []):
        if scrape_result.get("status") != "ok" or not scrape_result.get("text"):
            summary["results"].append(
                {
                    "url": scrape_result.get("url"),
                    "status": scrape_result.get("status"),
                    "error": scrape_result.get("error"),
                }
            )
            continue

        if not scrape_result.get("matched"):
            summary["results"].append(
                {
                    "url": scrape_result.get("url"),
                    "status": "skipped",
                    "reason": "no_ocp_match",
                }
            )
            continue

        try:
            mention, created = _store_scrape_result(scrape_result, company)
        except ValueError as exc:
            summary["errors"] += 1
            summary["results"].append(
                {
                    "url": scrape_result.get("url"),
                    "status": "error",
                    "error": str(exc),
                }
            )
            logger.error("Failed to store mention for %s: %s", scrape_result.get("url"), exc)
            continue

        logger.info(
            "Stored mention for %s (id=%s, created=%s)",
            scrape_result.get("url"),
            mention.id,
            created,
        )
        summary["results"].append(
            {
                "url": scrape_result.get("url"),
                "mention_id": mention.id,
                "created": created,
            }
        )
        if created:
            summary["created"] += 1
        else:
            summary["updated"] += 1

    return summary
