from django.contrib import admin

from .models import APIKey, AnalysisRequest


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("organization", "contact_email", "is_active", "rate_limit_per_minute", "rate_limit_per_day", "created_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("organization", "contact_email", "key")
    readonly_fields = ("key", "created_at", "last_used_at")


@admin.register(AnalysisRequest)
class AnalysisRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "api_key", "source", "image_count", "model_used", "processing_time_ms", "success")
    list_filter = ("source", "success", "model_used")
    search_fields = ("api_key__organization", "error_message")
    readonly_fields = (
        "api_key", "source", "image_count", "processing_time_ms", "model_used",
        "input_tokens", "output_tokens", "embeddings_included", "success",
        "error_message", "created_at",
    )
    date_hierarchy = "created_at"
