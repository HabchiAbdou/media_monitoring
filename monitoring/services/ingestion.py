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
    company, _ = Company.objects.get_or_create(
        name=DEFAULT_COMPANY_NAME,
        defaults={"website": DEFAULT_COMPANY_WEBSITE},
    )
    return company


_SOURCE_CACHE: dict[str, Source] = {}


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
    label = structured.get("sentiment_label") or "neutral"
    score = structured.get("sentiment_score")
    is_urgent = bool(structured.get("is_urgent", label == "negative"))
    urgency_reason = structured.get("urgency_reason")

    normalized = str(label).lower()
    if normalized in {"negative", "negatif"}:
        label = "negative"
        score = score if score is not None else -0.75
        urgency_reason = urgency_reason or "Negative sentiment detected by LLM"
        is_urgent = True
    elif normalized in {"positive", "positif"}:
        label = "positive"
        score = score if score is not None else 0.75
    elif normalized in {"neutral", "neutre"}:
        label = "neutral"
        score = score if score is not None else 0.0
    else:
        # Fallback using keywords from raw model output.
        text = (model_output or "").lower()
        if "negatif" in text or "negative" in text:
            label, score, is_urgent = "negative", -0.75, True
            urgency_reason = urgency_reason or "Negative sentiment detected by LLM"
        elif "positif" in text or "positive" in text:
            label, score = "positive", 0.75
        elif "neutre" in text or "neutral" in text:
            label, score = "neutral", 0.0
        else:
            label = "neutral"

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
    page_title = scrape_result.get("title") or url
    saved_path = scrape_result.get("saved_path")

    source = _get_or_create_source(url)
    published_at = timezone.now()

    llm_result = run_llm_pipeline(url=url, scraped_data={"title": page_title, "content": text})
    structured = llm_result.get("structured") if isinstance(llm_result, dict) else {}  # type: ignore[assignment]
    model_output = llm_result.get("output") if isinstance(llm_result, dict) else ""
    sentiment_label, sentiment_score, is_urgent, urgency_reason = _parse_sentiment_from_structured(
        structured or {}, model_output or ""
    )

    # Favor real scraped content for UI display; keep LLM details in raw_metadata.
    content_body = text or structured.get("body") or structured.get("summary") or model_output or page_title
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

        mention, created = _store_scrape_result(scrape_result, company)
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
