from django.db import models
import secrets


def generate_api_key() -> str:
    return f"sk_live_{secrets.token_urlsafe(32)}"


class APIKey(models.Model):
    """API key issued to a B2B customer (resale platform).

    Created manually via Django admin during the early sales phase. Each key is
    associated with a contact and rate limits.
    """

    key = models.CharField(max_length=80, unique=True, db_index=True, default=generate_api_key)
    organization = models.CharField(max_length=200)
    contact_email = models.EmailField()
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    rate_limit_per_minute = models.IntegerField(default=30)
    rate_limit_per_day = models.IntegerField(default=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.organization} ({self.key[:16]}...)"


class AnalysisRequest(models.Model):
    """Log of every analysis request (demo or API) for usage reporting."""

    SOURCE_CHOICES = [
        ("api", "API"),
        ("demo", "Demo"),
    ]

    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="api")
    image_count = models.IntegerField(default=0)
    processing_time_ms = models.IntegerField(default=0)
    model_used = models.CharField(max_length=80, blank=True, default="")
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    embeddings_included = models.BooleanField(default=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Analysis Request"
        verbose_name_plural = "Analysis Requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        org = self.api_key.organization if self.api_key else "demo"
        return f"{org} — {self.image_count} imgs — {self.created_at:%Y-%m-%d %H:%M}"
