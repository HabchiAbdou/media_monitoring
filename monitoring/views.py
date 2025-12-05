import json
import time
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

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


def _is_admin(user) -> bool:
    return user.is_authenticated and user.is_superuser


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Accès non autorisé")
            return redirect("monitoring:admin_login")
        if not request.user.is_superuser:
            messages.error(request, "Accès non autorisé")
            return redirect("monitoring:admin_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _json_body(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except Exception:
        return {}


def _auth_failure_delay():
    time.sleep(0.5)


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
        SourceType.objects.annotate(
            mention_count=Count("sources__mentions"),
            urgent_count=Count("sources__mentions", filter=Q(sources__mentions__is_urgent=True)),
            source_total=Count("sources", distinct=True),
        )
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
    urgent_count = Mention.objects.filter(is_urgent=True).count()
    source_reports = (
        Mention.objects.select_related("source", "source__type")
        .values("source_id", "source__name", "source__type__name")
        .annotate(
            total_mentions=Count("id"),
            urgent_mentions=Count("id", filter=Q(is_urgent=True)),
        )
        .order_by("-total_mentions")
    )

    context = {
        "sentiment_breakdown": sentiment_breakdown,
        "company_breakdown": company_breakdown,
        "total_mentions": total_mentions,
        "companies_count": companies_count,
        "urgent_count": urgent_count,
        "source_reports": source_reports,
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


# ---------------------------------------------------------------------------
# Administration views (superusers only)
# ---------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def admin_login(request):
    if _is_admin(request.user):
        return redirect("monitoring:admin_users")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and user.is_active and user.is_superuser:
            auth_login(request, user)
            return redirect("monitoring:admin_users")
        _auth_failure_delay()
        messages.error(request, "Identifiants invalides")

    return render(request, "admin/login.html")


def admin_logout(request):
    auth_logout(request)
    messages.success(request, "Vous êtes déconnecté.")
    return redirect("monitoring:admin_login")


@admin_required
@require_http_methods(["GET", "POST"])
def admin_users(request):
    User = get_user_model()

    if request.method == "POST":
        action = request.POST.get("action")
        target_id = request.POST.get("user_id")
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Create member
        if action == "create_user":
            if not username or not password:
                messages.error(request, "Nom d'utilisateur et mot de passe sont requis.")
            elif User.objects.filter(username=username).exists():
                messages.error(request, "Nom d'utilisateur déjà utilisé.")
            else:
                member = User.objects.create_user(username=username, password=password)
                member.is_superuser = False
                member.is_staff = False
                member.is_active = True
                member.save()
                messages.success(request, "Utilisateur créé avec succès.")

        # Change status or password
        elif target_id:
            try:
                member = User.objects.get(id=target_id)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur introuvable.")
                return redirect("monitoring:admin_users")

            if member.id == request.user.id:
                messages.error(request, "Vous ne pouvez pas vous supprimer vous-même.")
                return redirect("monitoring:admin_users")

            if action == "disable_user":
                if member.is_superuser:
                    messages.error(request, "Impossible de désactiver un superutilisateur.")
                else:
                    member.is_active = False
                    member.save()
                    messages.success(request, "Utilisateur désactivé.")
            elif action == "enable_user":
                member.is_active = True
                member.save()
                messages.success(request, "Utilisateur activé.")
            elif action == "delete_user":
                if member.is_superuser:
                    messages.error(request, "Impossible de supprimer un superutilisateur.")
                else:
                    member.delete()
                    messages.success(request, "Utilisateur supprimé.")
            elif action == "reset_password":
                if password:
                    member.set_password(password)
                    member.save()
                    messages.success(request, "Mot de passe réinitialisé.")
                else:
                    messages.error(request, "Mot de passe requis pour la réinitialisation.")

        return redirect("monitoring:admin_users")

    members = (
        get_user_model()
        .objects.all()
        .order_by("username")
        .values("id", "username", "is_active", "is_superuser", "date_joined")
    )
    return render(
        request,
        "admin/users.html",
        {
            "members": members,
        },
    )


# ---------------------------------------------------------------------------
# Authentication APIs
# ---------------------------------------------------------------------------


def _api_require_admin(request):
    if not _is_admin(request.user):
        return JsonResponse({"error": "Accès non autorisé"}, status=403)
    return None


@csrf_exempt
@require_POST
def api_auth_login(request):
    data = _json_body(request)
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user and user.is_active:
        auth_login(request, user)
        role = "superuser" if user.is_superuser else "member"
        return JsonResponse({"success": True, "role": role})
    _auth_failure_delay()
    return JsonResponse({"success": False, "error": "Identifiants invalides"}, status=400)


@csrf_exempt
@require_POST
def api_admin_login(request):
    data = _json_body(request)
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user and user.is_active and user.is_superuser:
        auth_login(request, user)
        return JsonResponse({"success": True, "role": "superuser"})
    _auth_failure_delay()
    return JsonResponse({"success": False, "error": "Identifiants invalides"}, status=400)


@csrf_exempt
@require_POST
def api_auth_logout(request):
    auth_logout(request)
    return JsonResponse({"success": True})


@csrf_exempt
@require_POST
def api_admin_logout(request):
    auth_logout(request)
    return JsonResponse({"success": True})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_admin_users(request):
    admin_error = _api_require_admin(request)
    if admin_error:
        return admin_error
    User = get_user_model()

    if request.method == "GET":
        users = []
        for u in User.objects.all().order_by("username"):
            users.append(
                {
                    "id": u.id,
                    "username": u.username,
                    "role": "superuser" if u.is_superuser else "member",
                    "is_active": u.is_active,
                    "created_at": u.date_joined.isoformat() if hasattr(u, "date_joined") else None,
                }
            )
        return JsonResponse({"results": users, "users": users})

    data = _json_body(request)
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    if not username or not password:
        return JsonResponse({"error": "Nom d'utilisateur et mot de passe sont requis."}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Nom d'utilisateur déjà utilisé."}, status=400)
    member = User.objects.create_user(username=username, password=password)
    member.is_superuser = False
    member.is_staff = False
    member.is_active = True
    member.save()
    return JsonResponse({"id": member.id, "username": member.username, "is_active": member.is_active})


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def api_admin_user_detail(request, user_id: int):
    admin_error = _api_require_admin(request)
    if admin_error:
        return admin_error
    User = get_user_model()
    try:
        member = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Utilisateur introuvable."}, status=404)

    if member.id == request.user.id:
        return JsonResponse({"error": "Impossible de supprimer/modifier votre propre compte."}, status=400)

    if request.method == "DELETE":
        if member.is_superuser:
            return JsonResponse({"error": "Impossible de supprimer un superutilisateur."}, status=400)
        member.delete()
        return JsonResponse({"success": True, "ok": True})

    data = _json_body(request)
    if "is_active" in data:
        member.is_active = bool(data.get("is_active"))
    if "password" in data and data.get("password"):
        member.set_password(data.get("password"))
    member.save()
    return JsonResponse({"id": member.id, "username": member.username, "is_active": member.is_active})
