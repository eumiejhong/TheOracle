from django.utils import timezone
from operator import itemgetter
from datetime import timedelta
from oracle_data.models import WardrobeItem
from io import BytesIO
from PIL import Image, ImageOps


def combine_style_summary(profile):
    appearance = profile.get("appearance", {})
    style_identity = profile.get("style_identity", {})
    lifestyle = profile.get("lifestyle", {})

    parts = []

    # 🌸 Appearance
    parts.append(f"Skin tone: {appearance.get('skin_tone')}, "
                 f"undertone: {appearance.get('undertone')}, "
                 f"contrast level: {appearance.get('contrast_level')}.")

    # ✨ Style Identity
    parts.append(f"Prefers: {style_identity.get('face_detail_preference')} details near the face.")
    parts.append(f"Texture and silhouettes: {style_identity.get('texture_notes')}.")
    parts.append(f"Color preferences: {style_identity.get('color_pref')}.")
    parts.append(f"Style constraints or dislikes: {style_identity.get('style_constraints')}.")
    parts.append(f"Archetype keywords: {style_identity.get('archetypes')}.")
    if style_identity.get("aspirational_style"):
        parts.append(f"Aspirational style: {style_identity['aspirational_style']}.")

    # 🌍 Lifestyle
    parts.append(f"Mobility: {lifestyle.get('mobility')}. Climate: {lifestyle.get('climate')}.")
    parts.append(f"Day-to-day style: {lifestyle.get('dress_formality')}.")
    parts.append(f"Wardrobe status: {lifestyle.get('wardrobe_phase')}.")
    parts.append(f"Shopping style: {lifestyle.get('shopping_behavior')}, budget comfort: {lifestyle.get('budget_preference')}.")
    if lifestyle.get("life_event"):
        parts.append(f"Life transition or emotional context: {lifestyle['life_event']}.")

    return " ".join(parts)


def combine_daily_context(daily_context):
    mood = daily_context.get("mood_today", "")
    occasion = daily_context.get("occasion", "")
    weather = daily_context.get("weather", "")
    item = daily_context.get("item_focus", "")

    return f"Today the user wants to feel: {mood}. Occasion: {occasion}. Weather: {weather}. Item in focus: {item}"


def update_last_used(user_id, used_items):
    for item_name in used_items:
        item = WardrobeItem.objects.filter(user_id=user_id, name__icontains=item_name).first()
        if item:
            item.last_used = timezone.now()
            item.save()


def compress_image_to_limit(
    raw: bytes,
    max_bytes: int,
    max_side: int = 1600,
    quality_start: int = 85,
    quality_floor: int = 40,
):
    """
    Returns (compressed_bytes, ext) with size <= max_bytes when possible.
    Prefers JPEG unless alpha channel is present.
    """
    with Image.open(BytesIO(raw)) as im:
        im = ImageOps.exif_transpose(im)
        # If not grayscale or RGB, convert to RGB to avoid huge PNGs
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        # Downscale if larger than max_side
        w, h = im.size
        scale = max(w, h) / float(max_side)
        if scale > 1.0:
            new_size = (int(w / scale), int(h / scale))
            im = im.resize(new_size, Image.LANCZOS)

        # Choose format: PNG only if there's transparency; otherwise JPEG
        has_alpha = "A" in im.getbands()
        fmt, ext = ("PNG", "png") if has_alpha else ("JPEG", "jpg")

        def save_with_quality(q: int) -> bytes:
            out = BytesIO()
            if fmt == "JPEG":
                im.save(out, format=fmt, quality=q, optimize=True)
            else:
                # PNG doesn't use 'quality'; try optimize only
                im.save(out, format=fmt, optimize=True)
            return out.getvalue()

        # First attempt
        q = quality_start
        data = save_with_quality(q)

        # If too big and JPEG, step quality down
        if fmt == "JPEG":
            while len(data) > max_bytes and q > quality_floor:
                q -= 5
                data = save_with_quality(q)

        # If still too big and PNG, try converting to JPEG
        if len(data) > max_bytes and fmt == "PNG":
            im_jpg = im.convert("RGB")
            fmt, ext = "JPEG", "jpg"
            q = quality_start
            def save_jpeg(qj: int) -> bytes:
                out = BytesIO()
                im_jpg.save(out, format="JPEG", quality=qj, optimize=True)
                return out.getvalue()
            data = save_jpeg(q)
            while len(data) > max_bytes and q > quality_floor:
                q -= 5
                data = save_jpeg(q)

        return data, ext
