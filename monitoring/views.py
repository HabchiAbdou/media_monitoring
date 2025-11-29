from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Company, Mention, SourceType


def _serialize_mention(mention):
    """Compact serializer for API responses."""
    return {
        "id": mention.id,
        "title": mention.title,
        "company": mention.company.name,
        "source": mention.source.name,
        "source_type": mention.source.type.name,
        "sentiment": mention.sentiment_label,
        "is_urgent": mention.is_urgent,
        "published_at": mention.published_at.isoformat(),
        "original_url": mention.original_url,
    }


@login_required
def dashboard(request):
    companies_count = Company.objects.count()
    mention_count = Mention.objects.count()
    urgent_count = Mention.objects.filter(is_urgent=True).count()
    latest_mentions = (
        Mention.objects.select_related("company", "source", "source__type")
        .order_by("-published_at")[:8]
    )
    source_summary = (
        SourceType.objects.annotate(mention_count=Count("sources__mentions"))
        .order_by("-mention_count")
    )

    context = {
        "companies_count": companies_count,
        "mention_count": mention_count,
        "urgent_count": urgent_count,
        "latest_mentions": latest_mentions,
        "source_summary": source_summary,
    }
    return render(request, "dashboard.html", context)


@login_required
def report_view(request):
    sentiment_breakdown = (
        Mention.objects.values("sentiment_label")
        .order_by("sentiment_label")
        .annotate(total=Count("id"))
    )
    company_breakdown = (
        Mention.objects.values("company__name")
        .order_by("company__name")
        .annotate(total=Count("id"))
    )
    total_mentions = Mention.objects.count()
    companies_count = Company.objects.count()

    context = {
        "sentiment_breakdown": sentiment_breakdown,
        "company_breakdown": company_breakdown,
        "total_mentions": total_mentions,
        "companies_count": companies_count,
    }
    return render(request, "report.html", context)


@login_required
def mention_list(request, source_type_name):
    source_type = get_object_or_404(SourceType, name__iexact=source_type_name)
    mentions = (
        Mention.objects.filter(source__type=source_type)
        .select_related("company", "source", "source__type")
        .order_by("-published_at")
    )
    return render(
        request,
        "mention_list.html",
        {"source_type": source_type, "mentions": mentions},
    )


@require_GET
def mentions_api(request):
    mentions = (
        Mention.objects.select_related("company", "source", "source__type")
        .order_by("-published_at")[:100]
    )
    payload = [_serialize_mention(m) for m in mentions]
    return JsonResponse({"results": payload})


@require_GET
def urgent_mentions_api(request):
    mentions = (
        Mention.objects.filter(is_urgent=True)
        .select_related("company", "source", "source__type")
        .order_by("-published_at")[:50]
    )
    payload = [_serialize_mention(m) for m in mentions]
    return JsonResponse({"results": payload})
