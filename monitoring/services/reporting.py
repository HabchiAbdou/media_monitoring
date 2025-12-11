import csv
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, List
import unicodedata
import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.models import Count, Max, Min, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from monitoring.models import Company, Mention

logger = logging.getLogger(__name__)


def get_ocp_mentions_queryset(source_id: Optional[int] = None):
    """
    Return a queryset of mentions related to OCP.

    Prefers explicit Company matching; falls back to keyword search when the
    company record is missing.
    """
    qs = Mention.objects.select_related("company", "source", "source__type")
    ocp_company = Company.objects.filter(name__iexact="OCP").first()
    if ocp_company:
        qs = qs.filter(company=ocp_company)
    else:
        qs = qs.filter(
            Q(company__name__icontains="OCP")
            | Q(title__icontains="OCP")
            | Q(content__icontains="OCP")
            | Q(content__icontains="المكتب الشريف للفوسفاط")
        )
    if source_id:
        qs = qs.filter(source_id=source_id)
    return qs


def enrich_report_with_llm(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder for future LLM integration.

    This function will take report_data, call an LLM (e.g. via Cerebras or OpenAI),
    and fill:
      - report_data["ai_sections"]["executive_summary"]
      - report_data["ai_sections"]["tone_overview"]
      - report_data["ai_sections"]["risk_overview"]
      - report_data["ai_sections"]["recommendations"]
      - and per-mention fields: ai_summary, ai_impact_level, ai_tone_comment, ai_recommendation

    For now, DO NOT implement any API calls and DO NOT modify report_data.
    Just return it as-is.
    """
    return report_data


def _pick_excerpt(mention: Mention) -> str:
    """Extract a short excerpt from mention metadata/content."""
    def _strip_noise(value: str) -> str:
        cleaned = re.sub(r"{%.*?%}", " ", value, flags=re.DOTALL)
        cleaned = re.sub(r"{{.*?}}", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    metadata = mention.raw_metadata if hasattr(mention, "raw_metadata") else None
    if isinstance(metadata, dict):
        for key in ("excerpt", "summary", "description", "snippet"):
            value = metadata.get(key)
            if value:
                return _strip_noise(str(value))
    if mention.content:
        return _strip_noise(str(mention.content)[:300])
    return ""


def _resolve_category(mention: Mention) -> str:
    """Retrieve category from the model or metadata when available."""
    category_value = getattr(mention, "category", None)
    if category_value:
        return str(category_value)
    metadata = mention.raw_metadata if hasattr(mention, "raw_metadata") else None
    if isinstance(metadata, dict) and metadata.get("category"):
        return str(metadata.get("category"))
    return ""


def _mentions_by_source_type(qs: Iterable[Mention]) -> Dict[str, int]:
    return {
        (entry["source__type__name"] or "Inconnu"): entry["total"]
        for entry in qs.values("source__type__name").annotate(total=Count("id"))
    }


def _sentiment_counts(qs: Iterable[Mention]) -> Dict[str, int]:
    label_map = {"positive": "Positif", "negative": "Négatif", "neutral": "Neutre"}
    counts = {}
    for entry in qs.values("sentiment_label").annotate(total=Count("id")):
        key = entry["sentiment_label"] or "Inconnu"
        counts[label_map.get(key, key)] = entry["total"]
    return counts


def _normalize_label_french(label: Any) -> str:
    if not label:
        return "neutre"
    normalized = unicodedata.normalize("NFKD", str(label)).encode("ascii", "ignore").decode().strip().lower()
    if "posit" in normalized:
        return "positif"
    if "negat" in normalized or "defavor" in normalized:
        return "negatif"
    if "neut" in normalized or "mitige" in normalized:
        return "neutre"
    return "neutre"


def _normalize_scores(scores: Any) -> Dict[str, int]:
    base = {"positif": 0, "negatif": 0, "neutre": 0}
    if isinstance(scores, dict):
        for key in base.keys():
            if key in scores:
                try:
                    base[key] = max(0, int(round(float(scores[key]))))
                except Exception:
                    base[key] = 0
    if sum(base.values()) == 0:
        base = {"positif": 33, "negatif": 33, "neutre": 34}
    total = sum(base.values())
    normalized = {k: int(round(v / total * 100)) for k, v in base.items()}
    diff = 100 - sum(normalized.values())
    if diff:
        target = max(normalized, key=normalized.get)
        normalized[target] += diff
    return normalized


def _normalize_risk_level(value: Any) -> str:
    if not value:
        return "modéré"
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().strip().lower()
    if "eleve" in normalized or "haut" in normalized:
        return "élevé"
    if "faible" in normalized or "bas" in normalized:
        return "faible"
    return "modéré"


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item.strip())
    return result


def _extract_llm_payload(mention: Mention) -> Dict[str, Any]:
    raw_metadata = mention.raw_metadata if hasattr(mention, "raw_metadata") else None
    structured: Dict[str, Any] = {}
    if isinstance(raw_metadata, dict):
        llm_section = raw_metadata.get("llm") if isinstance(raw_metadata.get("llm"), dict) else raw_metadata
        if isinstance(llm_section, dict):
            structured_section = llm_section.get("structured")
            if isinstance(structured_section, dict):
                structured = structured_section
            else:
                structured = llm_section
    return structured


def _extract_sentiment_scores_from_float(score: Optional[float]) -> Dict[str, int]:
    if score is None:
        return {"positif": 33, "negatif": 33, "neutre": 34}
    # Map score -1..1 to a loose distribution
    pos = max(0, min(1.0, (score + 1) / 2))
    neg = max(0, min(1.0, 1 - pos))
    neutre = max(0, 1 - abs(score))
    base = {"positif": pos, "negatif": neg, "neutre": neutre}
    total = sum(base.values()) or 1
    normalized = {k: int(round(v / total * 100)) for k, v in base.items()}
    diff = 100 - sum(normalized.values())
    if diff:
        target = max(normalized, key=normalized.get)
        normalized[target] += diff
    return normalized


_SUMMARY_LABEL_RE = re.compile(
    r"^\s*(analyse generale|analyse générale|résumé|resume|summary)\s*[:\-–]\s*",
    flags=re.IGNORECASE,
)


def _clean_summary_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _SUMMARY_LABEL_RE.sub("", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _aggregate_scores(mentions: List[Dict[str, Any]]) -> Dict[str, int]:
    totals = {"positif": 0, "negatif": 0, "neutre": 0}
    if not mentions:
        return totals
    for mention in mentions:
        scores = mention.get("sentiment_scores") or {}
        for key in totals:
            totals[key] += int(scores.get(key, 0))
    if sum(totals.values()) == 0:
        return {"positif": 33, "negatif": 33, "neutre": 34}
    averages = {k: int(round(v / len(mentions))) for k, v in totals.items()}
    diff = 100 - sum(averages.values())
    if diff:
        target = max(averages, key=averages.get)
        averages[target] += diff
    return averages


def _build_ai_sections(mentions: List[Dict[str, Any]], kpis: Dict[str, Any]) -> Dict[str, str]:
    total_mentions = kpis.get("total_mentions", 0)
    aggregated_scores = _aggregate_scores(mentions)
    risk_counts = {"faible": 0, "modéré": 0, "élevé": 0}
    all_recommendations: List[str] = []
    for mention in mentions:
        risk = mention.get("risk_level") or "modéré"
        normalized_risk = _normalize_risk_level(risk)
        risk_counts[normalized_risk] = risk_counts.get(normalized_risk, 0) + 1
        all_recommendations.extend(mention.get("recommendations") or [])

    recommendations = _dedupe_preserve_order(all_recommendations)
    recommendations_text = " • ".join(recommendations) if recommendations else "Aucune recommandation disponible."

    if total_mentions == 0:
        return {
            "executive_summary": "",
            "tone_overview": "",
            "risk_overview": "",
            "recommendations": recommendations_text,
        }

    dominant_label = max(aggregated_scores, key=aggregated_scores.get)
    tone_overview = {
        "positif": "Tendance majoritairement positive.",
        "neutre": "Tendance globalement neutre.",
        "negatif": "Tendance majoritairement négative avec signaux critiques.",
    }.get(dominant_label, "Tendance générale difficile à déterminer.")

    risk_overview_parts = []
    if risk_counts["élevé"]:
        risk_overview_parts.append(f"{risk_counts['élevé']} mention(s) à risque élevé.")
    if risk_counts["modéré"]:
        risk_overview_parts.append(f"{risk_counts['modéré']} mention(s) à risque modéré.")
    if risk_counts["faible"]:
        risk_overview_parts.append(f"{risk_counts['faible']} mention(s) à risque faible.")
    risk_overview = " ".join(risk_overview_parts) or "Aucune donnée sur les risques."

    executive_summary = (
        f"Sur la période analysée, OCP a été mentionné {total_mentions} fois. "
        f"{tone_overview} "
        f"{'Présence de signaux critiques à surveiller.' if risk_counts['élevé'] else 'Risque global modéré.'}"
    )

    return {
        "executive_summary": executive_summary,
        "tone_overview": tone_overview,
        "risk_overview": risk_overview,
        "recommendations": recommendations_text,
    }


def build_ocp_report_data(source_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Build a structured dictionary capturing the OCP report content.
    """
    mentions_qs = get_ocp_mentions_queryset(source_id=source_id)
    mentions_list = list(mentions_qs.order_by("-published_at"))

    timeframe = mentions_qs.aggregate(start=Min("published_at"), end=Max("published_at"))
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mentions_this_month = mentions_qs.filter(published_at__gte=month_start).count()

    mention_details: List[Dict[str, Any]] = []
    for mention in mentions_list:
        llm_data = _extract_llm_payload(mention)
        label_fr = _normalize_label_french(llm_data.get("sentiment_label") or mention.sentiment_label)
        label_display = {"negatif": "négatif", "positif": "positif", "neutre": "neutre"}.get(label_fr, label_fr)
        scores = llm_data.get("sentiment_scores")
        normalized_scores = _normalize_scores(scores) if isinstance(scores, dict) else None
        article_summary = (
            _clean_summary_text(llm_data.get("resume_article"))
            or _clean_summary_text(llm_data.get("article_summary"))
            or _clean_summary_text(llm_data.get("summary"))
        )
        if not article_summary:
            article_summary = "Résumé indisponible."
        reasons = llm_data.get("sentiment_reasons")
        reasons = [str(r).strip() for r in reasons] if isinstance(reasons, list) else []
        reasons = [r for r in reasons if r][:3]
        risk_level = _normalize_risk_level(llm_data.get("risk_level"))
        recommendations = llm_data.get("recommendations")
        recommendations = [str(r).strip() for r in recommendations] if isinstance(recommendations, list) else []

        mention_details.append(
            {
                "id": mention.id,
                "published_at": mention.published_at,
                "source_name": mention.source.name if mention.source else "",
                "source_type": mention.source.type.name if mention.source and mention.source.type else "",
                "title": mention.title,
                "url": getattr(mention, "original_url", None) or "",
                "raw_excerpt": _pick_excerpt(mention),
                "sentiment": label_fr,
                "sentiment_label": label_display,
                "sentiment_scores": normalized_scores,
                "category": _resolve_category(mention),
                "article_summary": article_summary,
                "resume_article": article_summary,
                "sentiment_reasons": reasons,
                "risk_level": risk_level,
                "recommendations": recommendations,
            }
        )

    kpis = {
        "total_mentions": len(mention_details),
        "mentions_this_month": mentions_this_month,
        "mentions_by_source_type": _mentions_by_source_type(mentions_qs),
        "sentiment_counts": _sentiment_counts(mentions_qs),
    }

    report_data: Dict[str, Any] = {
        "generated_at": now,
        "company_name": "OCP",
        "time_window": {"start": timeframe.get("start"), "end": timeframe.get("end")},
        "kpis": kpis,
        "ai_sections": _build_ai_sections(mention_details, kpis),
        "mentions": mention_details,
    }

    # Keep placeholder to wire future LLM enhancements without changing callers.
    report_data = enrich_report_with_llm(report_data)
    return report_data


def _link_callback(uri: str, rel: str) -> str:
    """
    Resolve static/media URIs so xhtml2pdf can load assets.
    """
    if settings.STATIC_URL and uri.startswith(settings.STATIC_URL):
        path = uri.replace(settings.STATIC_URL, "")
        resolved = finders.find(path)
        if resolved:
            return resolved
    if getattr(settings, "MEDIA_URL", None) and uri.startswith(settings.MEDIA_URL):
        media_path = uri.replace(settings.MEDIA_URL, "")
        return os.path.join(settings.MEDIA_ROOT, media_path)
    return uri


def _font_uri(relative_path: str) -> str:
    resolved = finders.find(relative_path)
    if resolved:
        try:
            return Path(resolved).as_uri()
        except Exception:
            return resolved
    return relative_path


def _font_path(relative_path: str) -> str | None:
    resolved = finders.find(relative_path)
    if resolved and os.path.exists(resolved):
        return resolved
    return None


def build_report_html(report_data: Dict[str, Any]) -> str:
    return render_to_string(
        "report_pdf.html",
        {
            "report": report_data,
            "font_sans_path": _font_uri("fonts/NotoSans-Regular.ttf"),
            "font_arabic_path": _font_uri("fonts/NotoSansArabic-Regular.ttf"),
        },
    )


def render_report_pdf(report_data: Dict[str, Any]) -> HttpResponse:
    """
    Render the HTML template with `report_data` and return an HttpResponse
    with the generated PDF.
    """
    # Register fonts for Unicode (including Arabic) support.
    font_sans_file = _font_path("fonts/NotoSans-Regular.ttf")
    font_arabic_file = _font_path("fonts/NotoSansArabic-Regular.ttf")
    for name, path in (("ReportSans", font_sans_file), ("ReportArabic", font_arabic_file)):
        if path:
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass
    pdfmetrics.registerFontFamily(
        "ReportArabic",
        normal="ReportArabic",
        bold="ReportArabic",
        italic="ReportArabic",
        boldItalic="ReportArabic",
    )
    pdfmetrics.registerFontFamily(
        "ReportSans",
        normal="ReportSans",
        bold="ReportSans",
        italic="ReportSans",
        boldItalic="ReportSans",
    )

    html = build_report_html(report_data)
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        html,
        dest=result,
        link_callback=_link_callback,
        encoding="utf-8",
        default_font="ReportArabic",
    )
    if pisa_status.err:
        logger.warning("PDF generation encountered errors: %s", pisa_status.err)
    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"rapport_ocp_{timestamp}.pdf"
    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def render_report_csv(report_data: Dict[str, Any]) -> HttpResponse:
    """
    Build a CSV export from the structured report data.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "date", "source_name", "source_type", "title", "url", "sentiment", "category"])

    for mention in report_data.get("mentions", []):
        published = mention.get("published_at")
        published_str = published.isoformat() if hasattr(published, "isoformat") else ""
        writer.writerow(
            [
                mention.get("id", ""),
                published_str,
                mention.get("source_name", ""),
                mention.get("source_type", ""),
                mention.get("title", ""),
                mention.get("url", ""),
                mention.get("sentiment", ""),
                mention.get("category", ""),
            ]
        )

    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"rapport_ocp_{timestamp}.csv"
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
