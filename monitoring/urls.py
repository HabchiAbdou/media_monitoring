from django.urls import path
from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("report/", views.report_view, name="report"),
    path("mentions/<str:source_type_name>/", views.mention_list, name="mention_list"),
    path("api/mentions/", views.mentions_api, name="mentions_api"),
    path("api/alerts/", views.urgent_mentions_api, name="urgent_mentions_api"),
]
