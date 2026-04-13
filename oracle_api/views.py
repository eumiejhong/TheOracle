import base64
import json
import datetime
import secrets

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from oracle_data.models import (
    UserStyleProfile, WardrobeItem, ShoppingEvaluation,
    DailyStyleInput, StylingSuggestion,
)
from oracle_frontend.utils import combine_style_summary, compress_image_to_limit
from oracle_frontend.image_descriptor import describe_image_with_gpt4v
from oracle_frontend.save_logic import save_style_profile, save_daily_input
from oracle_frontend.shared_helpers import get_serialized_wardrobe, build_shopping_buddy_context
from oracle_frontend.ai_config import get_openai_client, OPENAI_MODEL

from .serializers import (
    StyleProfileSerializer, StyleProfileWriteSerializer,
    WardrobeItemSerializer, WardrobeItemCreateSerializer,
    DailyInputSerializer, ShoppingEvalSerializer,
    ShoppingBuddyStartSerializer, ShoppingReplySerializer,
    InsightsSerializer,
)


# ---------------------------------------------------------------------------
# Auth: exchange Google ID token for JWT
# ---------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([AllowAny])
def google_auth(request):
    """Exchange a Google ID token for a JWT access/refresh pair."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from django.contrib.auth import get_user_model
    from rest_framework_simplejwt.tokens import RefreshToken
    import os

    token = request.data.get("id_token", "")
    if not token:
        return Response({"error": "id_token required"}, status=400)

    try:
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
        email = idinfo.get("email")
        if not email:
            return Response({"error": "No email in token"}, status=400)
    except Exception as e:
        return Response({"error": f"Invalid token: {e}"}, status=400)

    User = get_user_model()
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "first_name": idinfo.get("given_name", "")},
    )

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "email": user.email,
        "created": created,
    })


# ---------------------------------------------------------------------------
# Style Profile
# ---------------------------------------------------------------------------
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    email = request.user.email

    if request.method == "GET":
        profile = UserStyleProfile.objects.filter(user_id=email).order_by("-created_at").first()
        if not profile:
            return Response({"profile": None})
        return Response({"profile": StyleProfileSerializer(profile).data})

    serializer = StyleProfileWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    d = serializer.validated_data

    profile_data = {
        "user_id": email,
        "appearance": d["appearance"],
        "style_identity": d["style_identity"],
        "lifestyle": d["lifestyle"],
    }

    try:
        save_style_profile(profile_data, user_id=email)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    profile = UserStyleProfile.objects.filter(user_id=email).latest("created_at")
    return Response({"profile": StyleProfileSerializer(profile).data}, status=201)


# ---------------------------------------------------------------------------
# Wardrobe
# ---------------------------------------------------------------------------
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def wardrobe_list(request):
    email = request.user.email

    if request.method == "GET":
        items = WardrobeItem.objects.filter(user_id=email).order_by("-is_favorite", "-added_at")
        return Response({"items": WardrobeItemSerializer(items, many=True).data})

    ser = WardrobeItemCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    image_data = None
    if d.get("image"):
        raw = d["image"].read()
        try:
            compressed, _ = compress_image_to_limit(raw, max_bytes=1024 * 1024, max_side=1600)
            image_data = compressed
        except Exception:
            image_data = raw

    item = WardrobeItem.objects.create(
        user_id=email,
        name=d["name"],
        category=d["category"],
        color=d.get("color", ""),
        image=image_data,
    )
    return Response({"item": WardrobeItemSerializer(item).data}, status=201)


@api_view(["DELETE", "PATCH"])
@permission_classes([IsAuthenticated])
def wardrobe_detail(request, item_id):
    try:
        item = WardrobeItem.objects.get(id=item_id, user_id=request.user.email)
    except WardrobeItem.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        item.delete()
        return Response({"deleted": True})

    if "is_favorite" in request.data:
        item.is_favorite = bool(request.data["is_favorite"])
        item.save()
    return Response({"item": WardrobeItemSerializer(item).data})


# ---------------------------------------------------------------------------
# Daily Input / Outfit Suggestion
# ---------------------------------------------------------------------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def daily_input(request):
    email = request.user.email
    ser = DailyInputSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    profile = UserStyleProfile.objects.filter(user_id=email).order_by("-created_at").first()
    if not profile:
        return Response({"error": "Create a style profile first."}, status=400)

    item_focus = d.get("item_focus", "")
    wardrobe_item_id = d.get("wardrobe_item_id")
    if wardrobe_item_id:
        try:
            focus_item = WardrobeItem.objects.get(id=wardrobe_item_id, user_id=email)
            item_focus = focus_item.name
        except WardrobeItem.DoesNotExist:
            pass

    image_file = request.FILES.get("image")
    image_description = {}
    if image_file:
        image_description = describe_image_with_gpt4v(image_file)
        name_hint = (request.data.get("image_name_hint") or "").strip()
        if not name_hint or name_hint.lower() == "none":
            name_hint = item_focus or "Uploaded Item"
        image_description["name_hint"] = name_hint

    daily_context = {
        "user_id": email,
        "mood_today": d.get("mood_today", ""),
        "occasion": d["occasion"],
        "weather": d["weather"],
        "item_focus": item_focus,
        "image_description": image_description,
    }

    try:
        outfit_suggestion = save_daily_input(
            user_id=email, daily_context=daily_context, model_name=OPENAI_MODEL
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)

    suggestion = StylingSuggestion.objects.create(
        user=request.user, content=outfit_suggestion
    )

    return Response({
        "outfit_suggestion": outfit_suggestion,
        "suggestion_id": suggestion.id,
        "context": daily_context,
    })


# ---------------------------------------------------------------------------
# Shopping Buddy
# ---------------------------------------------------------------------------
def _ensure_table():
    from django.db import connection, transaction
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS oracle_data_shoppingevaluation (
                        id BIGSERIAL PRIMARY KEY,
                        item_image BYTEA,
                        item_description JSONB NOT NULL DEFAULT '{}'::jsonb,
                        evaluation TEXT NOT NULL DEFAULT '',
                        conversation JSONB NOT NULL DEFAULT '[]'::jsonb,
                        verdict VARCHAR(20) NOT NULL DEFAULT 'consider',
                        is_complete BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
                    );
                """)
    except Exception:
        pass

    cols = [
        "ADD COLUMN IF NOT EXISTS conversation JSONB NOT NULL DEFAULT '[]'::jsonb",
        "ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS price NUMERIC(10,2)",
        "ADD COLUMN IF NOT EXISTS occasion VARCHAR(100) NOT NULL DEFAULT ''",
        "ADD COLUMN IF NOT EXISTS product_url VARCHAR(500) NOT NULL DEFAULT ''",
        "ADD COLUMN IF NOT EXISTS share_token VARCHAR(64) NOT NULL DEFAULT ''",
        "ADD COLUMN IF NOT EXISTS saved_for_later BOOLEAN NOT NULL DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS saved_at TIMESTAMPTZ",
        "ADD COLUMN IF NOT EXISTS outfit_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb",
    ]
    from django.db import connection, transaction
    for col_sql in cols:
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(f"ALTER TABLE oracle_data_shoppingevaluation {col_sql};")
        except Exception:
            pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def shopping_buddy_start(request):
    _ensure_table()
    email = request.user.email

    image_file = request.FILES.get("image")
    product_url = (request.data.get("product_url") or "").strip()
    price_str = (request.data.get("price") or "").strip()
    occasion = (request.data.get("occasion") or "").strip()

    if not image_file and not product_url:
        return Response({"error": "Provide an image or product URL."}, status=400)

    try:
        if product_url and not image_file:
            import requests as http_requests, re, io
            resp = http_requests.get(product_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "image" in ct:
                raw_bytes = resp.content
            else:
                html = resp.text[:50000]
                og = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
                if not og:
                    og = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
                if not og:
                    return Response({"error": "Couldn't find an image at that URL."}, status=400)
                img_resp = http_requests.get(og.group(1), timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                img_resp.raise_for_status()
                raw_bytes = img_resp.content
        else:
            raw_bytes = b""
            for chunk in image_file.chunks():
                raw_bytes += chunk
            if not raw_bytes:
                raw_bytes = image_file.read()

        import io, sys
        from PIL import Image as PILImage

        print(f"[SHOPPING BUDDY] Image received: size={len(raw_bytes)}, content_type={getattr(image_file, 'content_type', 'unknown')}, name={getattr(image_file, 'name', 'unknown')}, first_bytes={raw_bytes[:16]}", file=sys.stderr, flush=True)

        try:
            pil_img = PILImage.open(io.BytesIO(raw_bytes))
            pil_img.load()
        except Exception as e1:
            print(f"[SHOPPING BUDDY] PIL open failed: {e1}", file=sys.stderr, flush=True)
            # The file might be empty or have a wrapper — try re-reading
            try:
                image_file.seek(0)
                raw_bytes = image_file.read()
                print(f"[SHOPPING BUDDY] Re-read: size={len(raw_bytes)}, first_bytes={raw_bytes[:16]}", file=sys.stderr, flush=True)
                pil_img = PILImage.open(io.BytesIO(raw_bytes))
                pil_img.load()
            except Exception as e2:
                print(f"[SHOPPING BUDDY] Second attempt failed: {e2}", file=sys.stderr, flush=True)
                return Response({"error": f"Could not read that image ({getattr(image_file, 'content_type', 'unknown')}, {len(raw_bytes)} bytes). Try taking a new photo."}, status=400)

        # Re-encode as JPEG to normalize format
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="JPEG", quality=90)
        raw_bytes = buf.getvalue()

        compressed, _ = compress_image_to_limit(raw_bytes, max_bytes=1024 * 1024, max_side=1200)

        if image_file:
            image_file.seek(0)
            try:
                item_desc = describe_image_with_gpt4v(image_file)
            except Exception:
                item_desc = describe_image_with_gpt4v(io.BytesIO(compressed))
        else:
            item_desc = describe_image_with_gpt4v(io.BytesIO(compressed))

        price = None
        if price_str:
            from decimal import Decimal, InvalidOperation
            try:
                price = Decimal(price_str).quantize(Decimal("0.01"))
            except (ValueError, InvalidOperation):
                pass

        profile = UserStyleProfile.objects.filter(user_id=email).latest("created_at")
        style_summary = combine_style_summary({
            "appearance": profile.appearance,
            "style_identity": profile.style_identity,
            "lifestyle": profile.lifestyle,
        })

        wardrobe_items = get_serialized_wardrobe(email)
        wardrobe_names_by_category = {}
        for w in wardrobe_items:
            cat = w.get("category", "Other")
            wardrobe_names_by_category.setdefault(cat, []).append(w["name"])
        overlap_summary = "\n".join(
            f"  {cat}: {', '.join(names)}"
            for cat, names in wardrobe_names_by_category.items()
        )

        item_category = (item_desc.get("category_guess") or "").lower()
        category_map = {
            "coat": "Outerwear", "jacket": "Outerwear", "blazer": "Outerwear",
            "trench": "Outerwear", "parka": "Outerwear", "vest": "Outerwear",
            "top": "Top", "shirt": "Top", "blouse": "Top", "sweater": "Top",
            "tee": "Top", "knit": "Top", "cardigan": "Top", "hoodie": "Top",
            "pants": "Bottom", "trousers": "Bottom", "jeans": "Bottom",
            "skirt": "Bottom", "shorts": "Bottom",
            "shoes": "Shoes", "sneakers": "Shoes", "boots": "Shoes",
            "loafers": "Shoes", "sandals": "Shoes", "heels": "Shoes",
            "bag": "Bag", "tote": "Bag", "purse": "Bag", "clutch": "Bag",
            "scarf": "Accessory", "hat": "Accessory", "belt": "Accessory",
            "jewelry": "Accessory", "watch": "Accessory",
        }
        matched_category = None
        for kw, cat in category_map.items():
            if kw in item_category:
                matched_category = cat
                break

        similar_items_with_images = []
        if matched_category:
            db_items = WardrobeItem.objects.filter(
                user_id=email, category=matched_category
            ).order_by("-is_favorite", "-added_at")[:6]
            for db_item in db_items:
                if db_item.image:
                    try:
                        img_b64 = base64.b64encode(bytes(db_item.image)).decode("utf-8")
                        similar_items_with_images.append({
                            "name": db_item.name, "category": db_item.category, "image_b64": img_b64
                        })
                    except Exception:
                        pass

        now = datetime.date.today()
        month_name = now.strftime("%B")
        season_map = {1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
                      6: "summer", 7: "summer", 8: "summer", 9: "fall", 10: "fall",
                      11: "fall", 12: "winter"}
        current_season = season_map[now.month]

        price_note = ""
        if price:
            price_note = f"\nPrice: ${price:,.0f}. Factor this into your recommendation — is it worth it at this price point given their budget comfort level, how much they'd actually wear it, and what they already own?"
        occasion_note = ""
        if occasion:
            occasion_note = f"\nThey're considering this for: {occasion}. Check if their wardrobe already covers this occasion. If it does, call it out."

        personal_context = build_shopping_buddy_context(request.user)

        system_prompt = f"""You are the user's most stylish, brutally honest best friend. You know their closet inside out, you know their style, their budget, and their tendency to buy things they never wear. You say what a good friend would say in the fitting room — direct, warm, sometimes blunt, and always looking out for them. You're not trying to make a sale. You're trying to save them from bad purchases and hype them up for great ones.

Talk like a real person, not a consultant. No lists, no bullet points, no markdown, no asterisks, no headers, no labels, no bold text. Just talk naturally like you're standing next to them in the fitting room. Use "you" directly — this is a conversation between friends.

The user has asked you to analyze how clothing looks on their specific body, coloring, and frame. Be as specific as a tailor. Describe EXACTLY what you see: where the shoulder seam falls relative to their actual shoulder, whether the fabric is bunching or pulling, how the neckline frames their face, whether the color is bringing warmth to their skin or washing them out. Never use generic filler that could apply to anyone.

Don't guess height in feet/inches — describe proportions instead. If the photo limits your analysis — bad angle, arms covering the garment — give your best read and ask for a better photo. Be specific about what angle would help.

You are ONLY their style friend. If they ask anything unrelated to fashion or this item, just say something like "babe, I'm here to talk clothes — what do you think about this piece?" Never break character.

Be opinionated. Don't hedge. If it's not right, say so clearly. If it's amazing, get excited. Reference their actual wardrobe, their style identity, and their past shopping patterns. Make it feel like you genuinely know them.

Current month: {month_name} (season: {current_season}). If this item is seasonal and they won't wear it for months, flag that honestly.{price_note}{occasion_note}

Their style profile: {profile.style_identity.get('archetypes', 'unknown')}
{style_summary}

{personal_context}

Their wardrobe by category:
{overlap_summary}"""

        first_content = [
            {"type": "text", "text": "Photo of the item they're considering:"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(compressed).decode('utf-8')}", "detail": "high"}},
        ]
        for sim in similar_items_with_images:
            first_content.append({"type": "text", "text": f"Their existing wardrobe item — {sim['name']}:"})
            first_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{sim['image_b64']}"}})

        wardrobe_ref = ' I showed you photos of their similar pieces too — compare them visually and be specific about differences.' if similar_items_with_images else ''
        first_message_text = f"""Write your response as one flowing, conversational response — like a text from a friend who really knows fashion, not a stylist's report. NO section headers, NO labels, NO bold text.

Look at this person and tell them honestly how this piece works on THEM specifically. Talk about their frame and proportions — are their legs long relative to their torso? Are their shoulders narrow or broad compared to their hips? Then tell them how THIS garment interacts with THEIR proportions. Where the hem hits, whether it's elongating or shortening them, whether the volume is in the right places.

Look at the color against their skin at the neckline and face. Does it bring warmth or flatten them?

Connect this to what you know about them — their style identity, what they already own, what they tend to gravitate toward, their favorites. If this overlaps with something they already have, say so directly. If it fills a real gap, get excited about it.{wardrobe_ref}

Give a clear buy or skip recommendation with your honest reasoning. Then ask one specific follow-up question."""

        first_content.append({"type": "text", "text": first_message_text})

        messages_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": first_content},
        ]

        response = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL, messages=messages_list, temperature=0.65,
        )
        oracle_reply = response.choices[0].message.content or ""

        if not oracle_reply.strip():
            return Response({"error": "The Oracle returned an empty response."}, status=500)

        conversation = [{"role": "oracle", "text": oracle_reply}]

        evaluation = ShoppingEvaluation.objects.create(
            user=request.user, item_image=compressed, item_description=item_desc,
            evaluation="", conversation=conversation, verdict="consider",
            is_complete=False, price=price, occasion=occasion, product_url=product_url,
        )

        session_key = f"shopping_ctx_{evaluation.id}"
        request.session[session_key] = {
            "system_prompt": system_prompt,
            "item_desc": json.dumps(item_desc),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": first_message_text},
                {"role": "assistant", "content": oracle_reply},
            ],
            "turn": 1,
            "photos_sent": 0,
        }

        return Response({
            "evaluation": ShoppingEvalSerializer(evaluation).data,
        }, status=201)

    except UserStyleProfile.DoesNotExist:
        return Response({"error": "Create a style profile first."}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def shopping_buddy_reply(request, eval_id):
    _ensure_table()

    try:
        evaluation = ShoppingEvaluation.objects.get(id=eval_id, user=request.user)
    except ShoppingEvaluation.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    if evaluation.is_complete:
        return Response({"error": "I've already given my verdict on this one. Start a new evaluation if you have another item."}, status=400)

    user_message = (request.data.get("message") or "").strip()
    uploaded_image = request.FILES.get("image")

    if not user_message and not uploaded_image:
        return Response({"error": "Please type a message or attach a photo."}, status=400)

    image_b64 = None
    if uploaded_image:
        try:
            raw = uploaded_image.read()
            compressed, _ = compress_image_to_limit(raw, max_bytes=1024 * 1024, max_side=1200)
            image_b64 = base64.b64encode(compressed).decode("utf-8")
        except Exception:
            return Response({"error": "Could not process that image. Try another."}, status=400)

    ctx = request.session.get(f"shopping_ctx_{eval_id}")
    if not ctx:
        return Response({"error": "Looks like the session timed out — start a new evaluation and I'll take another look."}, status=400)

    turn = ctx.get("turn", 1)
    has_photo = ctx.get("photos_sent", 0)
    max_turns = 3 + min(has_photo, 2)
    if turn > max_turns + 2:
        return Response({"error": "We've gone back and forth enough — start a new evaluation if you want to try another item.", "is_complete": True}, status=400)

    messages_list = ctx["messages"]

    if image_b64:
        user_content = []
        if user_message:
            user_content.append({"type": "text", "text": user_message})
        user_content.append({"type": "text", "text": "Here's a new photo:"})
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "high"}})
        messages_list.append({"role": "user", "content": user_content})
        ctx["photos_sent"] = has_photo + 1
    else:
        messages_list.append({"role": "user", "content": user_message})

    is_final_turn = turn >= max_turns - 1
    if is_final_turn:
        messages_list.append({
            "role": "system",
            "content": """IMPORTANT: If the user's message is off-topic (not about fashion, clothing, or this item), respond ONLY with: "Babe, I'm here to talk clothes — what do you think about this piece?" and do NOT give a verdict.

Otherwise, this is the final turn. Time to be real with them. Start with 'VERDICT:' followed by one of: STRONG BUY, WORTH CONSIDERING, SKIP IT, or YOU ALREADY OWN THIS.

Then give your final honest assessment in 2-3 sentences as their friend. Be direct. Reference what you know about them — their style identity, their shopping patterns, their wardrobe gaps. Make it personal:
- If they're a selective shopper who skips most things, acknowledge that ("you're picky for a reason — trust your gut here")
- If this fits their archetype perfectly, say so
- If they already own something similar, remind them
- If the price doesn't match their budget comfort, flag it
- Don't hedge. Tell them what you'd actually say if you were standing next to them.

Don't ask any more questions.

If your verdict is STRONG BUY or WORTH CONSIDERING, end with 'STYLE WITH:' followed by 2-3 complete outfit ideas using pieces from their wardrobe. Prioritize their favorite pieces — the ones they actually reach for. Think about what category this item is (if outerwear, suggest what goes under it; if a top, suggest bottoms and shoes). Don't pair it with items from the same category. Each outfit should be a full look. Use the actual item names from their wardrobe, cleaned up to read naturally (drop "My" or "My old" prefixes).""",
        })

    try:
        resp = get_openai_client().chat.completions.create(
            model=OPENAI_MODEL, messages=messages_list, temperature=0.6,
        )
        oracle_reply = resp.choices[0].message.content or ""
    except Exception:
        return Response({"error": "I hit a snag trying to respond — give it another shot."}, status=500)

    conversation = evaluation.conversation or []
    conv_entry = {"role": "user", "text": user_message or "(photo)"}
    if image_b64:
        conv_entry["image_b64"] = image_b64
    conversation.append(conv_entry)
    conversation.append({"role": "oracle", "text": oracle_reply})
    evaluation.conversation = conversation

    has_verdict = "VERDICT:" in oracle_reply.upper()
    is_final = is_final_turn and has_verdict
    if is_final:
        evaluation.is_complete = True
        evaluation.evaluation = oracle_reply
        reply_upper = oracle_reply.upper()
        if "STRONG BUY" in reply_upper:
            evaluation.verdict = "strong_buy"
        elif "SKIP IT" in reply_upper:
            evaluation.verdict = "skip"
        elif "YOU ALREADY OWN" in reply_upper:
            evaluation.verdict = "redundant"
        else:
            evaluation.verdict = "consider"

        if "STYLE WITH:" in oracle_reply.upper():
            style_section = oracle_reply[oracle_reply.upper().index("STYLE WITH:") + len("STYLE WITH:"):]
            outfits = [l.strip() for l in style_section.strip().split("\n") if l.strip()]
            evaluation.outfit_suggestions = outfits

    evaluation.save()

    messages_list.append({"role": "assistant", "content": oracle_reply})
    ctx["messages"] = messages_list
    ctx["turn"] = turn + 1
    request.session[f"shopping_ctx_{eval_id}"] = ctx
    request.session.modified = True

    return Response({
        "reply": oracle_reply,
        "is_complete": evaluation.is_complete,
        "verdict": evaluation.get_verdict_display() if evaluation.is_complete else None,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def shopping_save_toggle(request, eval_id):
    _ensure_table()
    try:
        ev = ShoppingEvaluation.objects.get(id=eval_id, user=request.user)
    except ShoppingEvaluation.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    ev.saved_for_later = not ev.saved_for_later
    ev.saved_at = timezone.now() if ev.saved_for_later else None
    ev.save()
    return Response({"saved": ev.saved_for_later})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shopping_wishlist(request):
    _ensure_table()
    now = timezone.now()
    items = list(ShoppingEvaluation.objects.filter(
        user=request.user, saved_for_later=True
    ).order_by("-saved_at"))

    results = []
    for item in items:
        d = ShoppingEvalSerializer(item).data
        if item.saved_at:
            hours = (now - item.saved_at).total_seconds() / 3600
            d["cooloff_complete"] = hours >= 48
            d["hours_remaining"] = max(0, int(48 - hours))
        else:
            d["cooloff_complete"] = False
            d["hours_remaining"] = 48
        results.append(d)

    return Response({"items": results})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shopping_insights(request):
    _ensure_table()
    evaluations = list(ShoppingEvaluation.objects.filter(
        user=request.user, is_complete=True
    ).order_by("-created_at"))

    total = len(evaluations)
    verdict_counts = {}
    category_counts = {}
    monthly_counts = {}

    for ev in evaluations:
        v = ev.get_verdict_display()
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        cat = (ev.item_description or {}).get("category_guess", "Unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        mk = ev.created_at.strftime("%b %Y")
        monthly_counts[mk] = monthly_counts.get(mk, 0) + 1

    skip_rate = round(verdict_counts.get("Skip It", 0) / total * 100) if total else 0
    top_cat = max(category_counts, key=category_counts.get) if category_counts else None
    top_count = category_counts.get(top_cat, 0) if top_cat else 0

    insights = []
    if top_cat and top_count >= 3:
        insights.append(f"You've evaluated {top_count} items in the \"{top_cat}\" category.")
    if skip_rate >= 60 and total >= 5:
        insights.append(f"You've skipped {skip_rate}% of items. You know what you don't want.")
    if total >= 10:
        insights.append(f"You've evaluated {total} items total. Shop with intention, not boredom.")

    return Response({
        "total": total,
        "verdict_counts": verdict_counts,
        "category_counts": category_counts,
        "monthly_counts": monthly_counts,
        "insights": insights,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shopping_share(request, eval_id):
    _ensure_table()
    try:
        ev = ShoppingEvaluation.objects.get(id=eval_id, user=request.user)
    except ShoppingEvaluation.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    if not ev.share_token:
        ev.share_token = secrets.token_urlsafe(32)
        ev.save()

    share_url = request.build_absolute_uri(f"/shopping-buddy/shared/{ev.share_token}/")
    return Response({"share_url": share_url})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shopping_history(request):
    _ensure_table()
    evals = ShoppingEvaluation.objects.filter(
        user=request.user, is_complete=True
    ).order_by("-created_at")[:20]
    results = []
    for ev in evals:
        clean_conversation = []
        for msg in (ev.conversation or []):
            clean_conversation.append(
                {k: v for k, v in msg.items() if k != "image_b64"}
            )

        thumb_b64 = None
        if ev.item_image:
            try:
                from PIL import Image as PILImage
                import io
                img = PILImage.open(io.BytesIO(bytes(ev.item_image)))
                img.thumbnail((120, 120))
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=50)
                thumb_b64 = base64.b64encode(buf.getvalue()).decode()
            except Exception:
                pass

        results.append({
            "id": ev.id,
            "verdict": ev.verdict,
            "verdict_display": ev.get_verdict_display(),
            "is_complete": ev.is_complete,
            "conversation": clean_conversation,
            "price": str(ev.price) if ev.price else None,
            "occasion": ev.occasion,
            "saved_for_later": ev.saved_for_later,
            "outfit_suggestions": ev.outfit_suggestions,
            "created_at": ev.created_at.isoformat(),
            "thumb_b64": thumb_b64,
        })
    return Response({"evaluations": results})
