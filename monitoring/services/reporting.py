import csv
import io
import logging
import os
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.models import Count, Max, Min, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

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
    metadata = mention.raw_metadata if hasattr(mention, "raw_metadata") else None
    if isinstance(metadata, dict):
        for key in ("excerpt", "summary", "description", "snippet"):
            value = metadata.get(key)
            if value:
                return str(value)
    if mention.content:
        return str(mention.content)[:300]
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
    return {
        (entry["sentiment_label"] or "unknown"): entry["total"]
        for entry in qs.values("sentiment_label").annotate(total=Count("id"))
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

    report_data: Dict[str, Any] = {
        "generated_at": now,
        "company_name": "OCP",
        "time_window": {"start": timeframe.get("start"), "end": timeframe.get("end")},
        "kpis": {
            "total_mentions": len(mentions_list),
            "mentions_this_month": mentions_this_month,
            "mentions_by_source_type": _mentions_by_source_type(mentions_qs),
            "sentiment_counts": _sentiment_counts(mentions_qs),
        },
        "ai_sections": {
            "executive_summary": "",  # TODO: LLM: high-level synthesis in French
            "tone_overview": "",  # TODO: LLM: comment on overall tone
            "risk_overview": "",  # TODO: LLM: main risks to OCP's image
            "recommendations": "",  # TODO: LLM: key recommended actions
        },
        "mentions": [
            {
                "id": mention.id,
                "published_at": mention.published_at,
                "source_name": mention.source.name if mention.source else "",
                "source_type": mention.source.type.name if mention.source and mention.source.type else "",
                "title": mention.title,
                "url": getattr(mention, "original_url", None) or "",
                "raw_excerpt": _pick_excerpt(mention),
                "sentiment": mention.sentiment_label,
                "category": _resolve_category(mention),
                "ai_summary": "",
                "ai_impact_level": "",
                "ai_tone_comment": "",
                "ai_recommendation": "",
            }
            for mention in mentions_list
        ],
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


def render_report_pdf(report_data: Dict[str, Any]) -> HttpResponse:
    """
    Render the HTML template with `report_data` and return an HttpResponse
    with the generated PDF.
    """
    html = render_to_string("report_pdf.html", {"report": report_data})
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result, link_callback=_link_callback, encoding="utf-8")
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
