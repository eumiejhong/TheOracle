from django.db import models
from django.conf import settings
from django.db.models import JSONField
from django.contrib.postgres.fields import ArrayField

SEASON_CHOICES = [
    ('spring', 'Spring'),
    ('summer', 'Summer'),
    ('fall', 'Fall'),
    ('winter', 'Winter'),
    ('all', 'All Seasons'),
]

class UserStyleProfile(models.Model):
    user_id = models.CharField(max_length=100)
    raw_text = models.TextField()  # final text summary to embed
    embedding = models.BinaryField(null=True, blank=True)  # or vector(768) if using BGE

    appearance = JSONField()       # skin_tone, undertone, contrast_level
    style_identity = JSONField(default=dict)   # archetypes, texture_notes, color_pref, style_constraints, face_detail_preference, aspirational_style
    lifestyle = JSONField()        # mobility, climate, life_event, dress_formality, etc.
    style_archetype = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile for {self.user_id} at {self.created_at}"


class DailyStyleInput(models.Model):
    user_profile = models.ForeignKey(UserStyleProfile, on_delete=models.CASCADE, related_name="daily_inputs")
    mood_today = models.TextField(blank=True)
    occasion = models.CharField(max_length=100)
    weather = models.CharField(max_length=100)
    item_focus = models.TextField(blank=True)
    outfit_suggestion = models.TextField(null=True, blank=True)
    image_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Daily input for {self.user_profile.user_id} on {self.created_at.date()}"


class WardrobeItem(models.Model):
    user_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    color = models.CharField(max_length=100, blank=True, null=True)
    style_tags = models.JSONField(blank=True, null=True)  # e.g., ["sleek", "minimalist"]
    image = models.BinaryField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, default='all')
    is_favorite = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.category}) — {self.user_id}"


class StylingSuggestion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    mood = models.CharField(max_length=100, blank=True, null=True)
    occasion = models.CharField(max_length=100, blank=True, null=True)
    weather = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SuggestionFeedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    suggestion = models.ForeignKey(StylingSuggestion, on_delete=models.CASCADE)
    
    rating = models.CharField(
        max_length=10,
        choices=[
            ("loved", "Loved it"),
            ("meh", "Meh"),
            ("dislike", "Not my vibe")
        ]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

