import base64
from rest_framework import serializers
from oracle_data.models import (
    UserStyleProfile, WardrobeItem, ShoppingEvaluation,
    DailyStyleInput, StylingSuggestion,
)


class StyleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStyleProfile
        fields = [
            "id", "appearance", "style_identity", "lifestyle",
            "style_archetype", "created_at",
        ]
        read_only_fields = ["id", "style_archetype", "created_at"]


class StyleProfileWriteSerializer(serializers.Serializer):
    appearance = serializers.JSONField()
    style_identity = serializers.JSONField()
    lifestyle = serializers.JSONField()


class WardrobeItemSerializer(serializers.ModelSerializer):
    image_b64 = serializers.SerializerMethodField()

    class Meta:
        model = WardrobeItem
        fields = [
            "id", "name", "category", "color", "style_tags",
            "season", "is_favorite", "added_at", "last_used", "image_b64",
        ]
        read_only_fields = ["id", "added_at", "last_used", "image_b64"]

    def get_image_b64(self, obj):
        if obj.image:
            try:
                import io
                from PIL import Image as PILImage
                img = PILImage.open(io.BytesIO(bytes(obj.image)))
                img.thumbnail((300, 300))
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=60)
                return base64.b64encode(buf.getvalue()).decode("utf-8")
            except Exception:
                return None
        return None


class WardrobeItemCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=50)
    color = serializers.CharField(max_length=100, required=False, default="")
    image = serializers.ImageField(required=False)


class DailyInputSerializer(serializers.Serializer):
    mood_today = serializers.CharField(required=False, default="", allow_blank=True)
    occasion = serializers.CharField(max_length=100)
    weather = serializers.CharField(max_length=100)
    item_focus = serializers.CharField(required=False, default="", allow_blank=True)
    wardrobe_item_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class DailyInputResultSerializer(serializers.Serializer):
    outfit_suggestion = serializers.CharField()
    suggestion_id = serializers.IntegerField()
    context = serializers.DictField()


class ShoppingEvalSerializer(serializers.ModelSerializer):
    verdict_display = serializers.CharField(source="get_verdict_display", read_only=True)
    image_b64 = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingEvaluation
        fields = [
            "id", "conversation", "verdict", "verdict_display",
            "is_complete", "price", "occasion", "product_url",
            "saved_for_later", "saved_at", "outfit_suggestions",
            "created_at", "image_b64", "item_description",
        ]

    def get_image_b64(self, obj):
        if obj.item_image:
            try:
                return base64.b64encode(bytes(obj.item_image)).decode("utf-8")
            except Exception:
                return None
        return None


class ShoppingBuddyStartSerializer(serializers.Serializer):
    image = serializers.ImageField(required=False)
    product_url = serializers.URLField(required=False, default="")
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    occasion = serializers.CharField(max_length=100, required=False, default="")


class ShoppingReplySerializer(serializers.Serializer):
    message = serializers.CharField(required=False, default="")
    image = serializers.ImageField(required=False)


class InsightsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    verdict_counts = serializers.DictField()
    category_counts = serializers.DictField()
    monthly_counts = serializers.DictField()
    insights = serializers.ListField(child=serializers.CharField())
