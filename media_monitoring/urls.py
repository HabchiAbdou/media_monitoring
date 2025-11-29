from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

# Restrict admin to superusers only
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="auth/login.html"
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("monitoring.urls")),  # our app
]
