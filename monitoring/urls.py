from django.urls import path
from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("report/", views.report_view, name="report"),
    path("mentions/<str:source_type_name>/", views.mention_list, name="mention_list"),
    path("api/mentions/", views.mentions_api, name="mentions_api"),
    path("api/alerts/", views.urgent_mentions_api, name="urgent_mentions_api"),
    # Administration (superusers only)
    path("administration/login/", views.admin_login, name="admin_login"),
    path("administration/logout/", views.admin_logout, name="admin_logout"),
    path("administration/users/", views.admin_users, name="admin_users"),
    # Auth APIs
    path("api/auth/login/", views.api_auth_login, name="api_auth_login"),
    path("api/auth/logout/", views.api_auth_logout, name="api_auth_logout"),
    path("api/admin/login/", views.api_admin_login, name="api_admin_login"),
    path("api/admin/logout/", views.api_admin_logout, name="api_admin_logout"),
    path("api/admin/users/", views.api_admin_users, name="api_admin_users"),
    path("api/admin/users/<int:user_id>/", views.api_admin_user_detail, name="api_admin_user_detail"),
]
