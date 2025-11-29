from django.contrib import admin
from .models import Company, SourceType, Source, Mention

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "website")

@admin.register(SourceType)
class SourceTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "url")
    list_filter = ("type",)

@admin.register(Mention)
class MentionAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "source", "sentiment_label", "is_urgent", "published_at")
    list_filter = ("company", "source__type", "sentiment_label", "is_urgent")
    search_fields = ("title", "content", "original_url")
