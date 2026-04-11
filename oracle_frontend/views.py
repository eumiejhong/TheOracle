from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import base64

from oracle_data.models import UserStyleProfile, DailyStyleInput, WardrobeItem, ShoppingEvaluation
from .forms import BaseStyleProfileForm, DailyStyleInputForm, WardrobeUploadForm
from oracle_frontend.save_logic import save_style_profile  
from oracle_frontend.image_descriptor import describe_image_with_gpt4v
from oracle_frontend.utils import combine_style_summary, compress_image_to_limit
from oracle_frontend.save_logic import save_daily_input
from oracle_data.models import UserStyleProfile, StylingSuggestion, WardrobeItem


@login_required
def dashboard_view(request):
    user_email = request.user.email

    # Handle wardrobe form submission here directly (optional)
    if request.method == "POST":
        form = WardrobeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.cleaned_data.get("image")
            image_data = image.read() if image else None
            WardrobeItem.objects.create(
                user_id=user_email,
                name=form.cleaned_data["name"],
                category=form.cleaned_data["category"],
                image=image_data
            )
            return redirect("dashboard")
    else:
        form = WardrobeUploadForm()

    base_profile = UserStyleProfile.objects.filter(user_id=user_email).first()
    daily_inputs = DailyStyleInput.objects.filter(user_profile__user_id=user_email).order_by('-created_at')[:5]
    today_suggestion = daily_inputs[0].outfit_suggestion if daily_inputs else None
    wardrobe_items = WardrobeItem.objects.filter(user_id=user_email).order_by('-added_at')

    return render(request, "dashboard.html", {
        "user_email": user_email,
        "base_profile": base_profile,
        "daily_inputs": daily_inputs,
        "today_suggestion": today_suggestion,
        "wardrobe_items": wardrobe_items,
        "wardrobe_form": form
    })


@login_required
def base_style_profile_view(request):
    user_email = request.user.email
    print(f"[PROFILE] {request.method} from {user_email}")

    if request.method == "POST":
        form = BaseStyleProfileForm(request.POST)
        print(f"[PROFILE] Form valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"[PROFILE] Form errors: {form.errors}")
        if form.is_valid():
            profile = {
                "user_id": user_email,
                "appearance": {
                    "skin_tone": form.cleaned_data["skin_tone"],
                    "contrast_level": form.cleaned_data["contrast_level"],
                    "undertone": form.cleaned_data["undertone"]
                },
                "style_identity": {
                    "face_detail_preference": form.cleaned_data["face_detail_preference"],
                    "texture_notes": form.cleaned_data["texture_notes"],
                    "color_pref": form.cleaned_data["color_pref"],
                    "style_constraints": form.cleaned_data["style_constraints"],
                    "archetypes": form.cleaned_data["archetypes"],
                    "aspirational_style": form.cleaned_data["aspirational_style"]
                },
                "lifestyle": {
                    "mobility": form.cleaned_data["mobility"],
                    "climate": form.cleaned_data["climate_wear"],
                    "life_event": form.cleaned_data["life_event"],
                    "dress_formality": form.cleaned_data["dress_formality"],
                    "wardrobe_phase": form.cleaned_data["wardrobe_phase"],
                    "shopping_behavior": form.cleaned_data["shopping_behavior"],
                    "budget_preference": form.cleaned_data["budget_preference"]
                }
            }

            print(f"[PROFILE] Calling save_style_profile...")
            try:
                save_style_profile(profile, user_id=request.user.email)
                print(f"[PROFILE] Save successful!")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[PROFILE] Save FAILED: {e}")
                return render(request, "base_style_profile_form.html", {
                    "form": form,
                    "save_error": f"Could not save profile: {e}"
                })

            return redirect("profile_saved")
    else:
        form = BaseStyleProfileForm()

    return render(request, "base_style_profile_form.html", {"form": form})


@login_required
def profile_saved_view(request):
    user_email = request.user.email
    profile = UserStyleProfile.objects.filter(user_id=user_email).first()
    if not profile:
        return redirect("base_profile")
    return render(request, "profile_saved.html", {"profile": profile})


def mark_item_as_worn(request, item_id):
    item = WardrobeItem.objects.get(id=item_id)
    item.last_used = timezone.now()
    item.save()
    return redirect('dashboard.html')


@login_required
def daily_style_input_view(request):
    user_email = request.user.email
    wardrobe_items = WardrobeItem.objects.filter(user_id=user_email)

    wardrobe_choices = [("", "—")] + [(str(item.id), item.name) for item in wardrobe_items]

    if request.method == "POST":
        form = DailyStyleInputForm(request.POST, request.FILES)
        form.fields["wardrobe_item"].choices = wardrobe_choices

        if form.is_valid():
            # Check that the user has a style profile before proceeding
            if not UserStyleProfile.objects.filter(user_id=user_email).exists():
                from django.contrib import messages
                messages.error(request, "Please create your style profile first before requesting daily guidance.")
                return redirect("base_profile")

            try:
                add_new_item = form.cleaned_data.get("add_new_item") == "yes"
                image = form.cleaned_data.get("image")
                item_focus = form.cleaned_data.get("item_focus", "").strip()

                if image:
                    image.seek(0)
                    image_description = describe_image_with_gpt4v(image)
                else:
                    image_description = {}

                name_hint = form.cleaned_data.get("image_name_hint", "").strip()
                if not name_hint or name_hint.lower() == "none":
                    name_hint = item_focus or "Uploaded Item"
                image_description["name_hint"] = name_hint

                selected_item_id = form.cleaned_data.get("wardrobe_item")
                if selected_item_id:
                    selected_item = wardrobe_items.get(id=selected_item_id)
                    item_focus = selected_item.name

                daily_context = {
                    "user_id": user_email,
                    "mood_today": form.cleaned_data["mood_today"],
                    "occasion": form.cleaned_data["occasion"],
                    "weather": form.cleaned_data["weather"],
                    "item_focus": item_focus,
                    "image_description": image_description,
                }

                outfit_suggestion = save_daily_input(
                    user_id=user_email,
                    daily_context=daily_context,
                    model_name="gpt-4o"
                )

                suggestion = StylingSuggestion.objects.create(
                    user=request.user,
                    content=outfit_suggestion
                )

                proposed_item = None
                uploaded_item_visual = None
                if add_new_item and image:
                    image.seek(0)
                    raw_bytes = image.read()
                    image_b64 = base64.b64encode(raw_bytes).decode("utf-8")

                    proposed_item = {
                        "name": item_focus,
                        "image_base64": image_b64,
                    }
                    uploaded_item_visual = {
                        "name": item_focus,
                        "image_b64": image_b64,
                    }

                matched_items = []
                suggestion_lower = outfit_suggestion.lower() if outfit_suggestion else ""
                seen_ids = set()

                if selected_item_id:
                    try:
                        focus_obj = wardrobe_items.get(id=selected_item_id)
                        matched_items.append(focus_obj)
                        seen_ids.add(focus_obj.id)
                    except WardrobeItem.DoesNotExist:
                        pass

                for item in wardrobe_items:
                    if item.id in seen_ids:
                        continue
                    name_lower = item.name.lower()
                    words = [w for w in name_lower.split() if len(w) > 3]
                    if any(word in suggestion_lower for word in words):
                        matched_items.append(item)
                        seen_ids.add(item.id)

                return render(
                    request,
                    "daily_input_result.html",
                    {
                        "context": daily_context,
                        "outfit_suggestion": outfit_suggestion,
                        "suggestion": suggestion,
                        "matched_items": matched_items,
                        "uploaded_item_visual": uploaded_item_visual,
                        "proposed_item": proposed_item,
                    }
                )

            except Exception as e:
                import traceback
                traceback.print_exc()
                from django.contrib import messages
                messages.error(request, f"Something went wrong generating your outfit: {e}")
                return redirect("daily_input")

    else:
        form = DailyStyleInputForm()
        form.fields["wardrobe_item"].choices = wardrobe_choices

    return render(request, "daily_input_form.html", {"form": form})


@login_required
def wardrobe_upload_view(request):
    user_id = request.user.email

    if request.method == "POST":
        form = WardrobeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image_file = form.cleaned_data.get("image")

            image_file.seek(0)
            raw = image_file.read()
            try:
                compressed, _ext = compress_image_to_limit(raw, max_bytes=1024*1024, max_side=1600)
            except Exception:
                compressed = raw

            WardrobeItem.objects.create(
                user_id=user_id,
                name=form.cleaned_data["name"],
                category=form.cleaned_data["category"],
                image=compressed,
            )

            return redirect("dashboard")  
    else:
        form = WardrobeUploadForm()

    items = WardrobeItem.objects.filter(user_id=user_id).order_by("-favorite", "-added_at")

    return render(request, "dashboard.html", {"form": form, "items": items})


@require_POST
@login_required
def submit_feedback(request, suggestion_id):
    from oracle_data.models import SuggestionFeedback
    suggestion = get_object_or_404(StylingSuggestion, id=suggestion_id, user=request.user)
    rating = request.POST.get("rating", "")
    comment = request.POST.get("comment", "")

    rating_labels = {"loved": "Loved it", "meh": "Neutral", "dislike": "Not for me"}

    feedback, created = SuggestionFeedback.objects.update_or_create(
        user=request.user,
        suggestion=suggestion,
        defaults={"rating": rating, "comment": comment},
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "status": "success",
            "rating": rating,
            "rating_display": rating_labels.get(rating, rating),
        })
    return redirect("dashboard")


@require_POST
def toggle_favorite(request):
    item_id = request.POST.get("item_id")
    try:
        item = WardrobeItem.objects.get(id=item_id, user_id=request.user.email)
        item.is_favorite = not item.is_favorite
        item.save()
        return JsonResponse({"status": "success", "favorite": item.is_favorite})
    except WardrobeItem.DoesNotExist:
        return JsonResponse({"status": "error"}, status=404)


@csrf_protect
@login_required
def add_from_daily_view(request):
    if request.method != 'POST':
        return JsonResponse({"message": "Only POST allowed"}, status=405)

    try:
        name = (request.POST.get("item_name") or "").strip()
        category = request.POST.get("category", "Uncategorized")
        if not name:
            return JsonResponse({"message": "Missing item name."}, status=400)

        hard_limit = getattr(settings, "DATA_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)
        max_bytes = max(1024 * 1024, hard_limit - 128 * 1024)

        uploaded_file = request.FILES.get("image")
        if uploaded_file:
            raw = uploaded_file.read()
            compressed, _ext = compress_image_to_limit(raw, max_bytes=max_bytes, max_side=1600)
            WardrobeItem.objects.create(
                user_id=request.user.email, name=name, category=category, image=compressed
            )
            return JsonResponse({"message": f"'{name}' added to your wardrobe!"})

        image_b64 = (request.POST.get("image_b64") or "").strip()
        if image_b64:
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]
            try:
                raw = base64.b64decode(image_b64)
            except Exception:
                return JsonResponse({"message": "Invalid image data."}, status=400)

            compressed, _ext = compress_image_to_limit(raw, max_bytes=max_bytes, max_side=1600)
            WardrobeItem.objects.create(
                user_id=request.user.email, name=name, category=category, image=compressed
            )
            return JsonResponse({"message": f"'{name}' added to your wardrobe!"})

        return JsonResponse({"message": "Missing image (upload a file or include image_b64)."}, status=400)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"message": f"Error saving item: {str(e)}"}, status=500)


@require_POST
@login_required
def delete_wardrobe_item(request):
    item_id = request.POST.get("item_id")
    if not item_id:
        return JsonResponse({"status": "error", "message": "No item ID provided."}, status=400)

    item = get_object_or_404(WardrobeItem, id=item_id, user_id=request.user.email)
    item.delete()

    return JsonResponse({"status": "success", "message": "Item deleted successfully."})


@login_required
def suggestion_detail_view(request, suggestion_id):
    """View details of a past outfit suggestion."""
    from oracle_data.models import StylingSuggestion, SuggestionFeedback
    
    suggestion = get_object_or_404(StylingSuggestion, id=suggestion_id, user_id=request.user.email)
    
    # Get feedback if exists
    feedback = SuggestionFeedback.objects.filter(suggestion=suggestion).first()
    
    # Parse context JSON
    context_data = {}
    if suggestion.context:
        import json
        try:
            context_data = json.loads(suggestion.context) if isinstance(suggestion.context, str) else suggestion.context
        except:
            context_data = {}
    
    # Find matched wardrobe items mentioned in suggestion
    wardrobe_items = WardrobeItem.objects.filter(user_id=request.user.email)
    matched_items = []
    suggestion_lower = suggestion.content.lower() if suggestion.content else ""
    
    for item in wardrobe_items:
        item_name_lower = item.name.lower()
        # Check if item name or significant words appear in suggestion
        words = [w for w in item_name_lower.split() if len(w) > 3]
        if any(word in suggestion_lower for word in words):
            matched_items.append(item)
    
    return render(request, "suggestion_detail.html", {
        "suggestion": suggestion,
        "context": context_data,
        "feedback": feedback,
        "matched_items": matched_items,
    })


def _ensure_shopping_table():
    from django.db import connection
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
        cursor.execute("ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS conversation JSONB NOT NULL DEFAULT '[]'::jsonb;")
        cursor.execute("ALTER TABLE oracle_data_shoppingevaluation ADD COLUMN IF NOT EXISTS is_complete BOOLEAN NOT NULL DEFAULT FALSE;")


@login_required
def shopping_buddy_view(request):
    import json
    from oracle_frontend.archetype_generator import get_openai_client
    from oracle_frontend.shared_helpers import get_serialized_wardrobe

    _ensure_shopping_table()

    user_email = request.user.email

    try:
        past_evals = list(ShoppingEvaluation.objects.filter(user=request.user, is_complete=True).order_by("-created_at")[:5])
    except Exception:
        past_evals = []

    if request.method != "POST":
        return render(request, "shopping_buddy_form.html", {"past_evals": past_evals})

    image_file = request.FILES.get("image")
    if not image_file:
        from django.contrib import messages
        messages.error(request, "Please upload a photo of the item you're considering.")
        return redirect("shopping_buddy")

    try:
        raw_bytes = image_file.read()
        compressed, _ext = compress_image_to_limit(raw_bytes, max_bytes=1024 * 1024, max_side=1200)

        image_file.seek(0)
        item_desc = describe_image_with_gpt4v(image_file)

        profile = UserStyleProfile.objects.filter(user_id=user_email).latest("created_at")
        style_summary = combine_style_summary({
            "appearance": profile.appearance,
            "style_identity": profile.style_identity,
            "lifestyle": profile.lifestyle,
        })

        wardrobe_items = get_serialized_wardrobe(user_email)
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
        for keyword, cat in category_map.items():
            if keyword in item_category:
                matched_category = cat
                break

        similar_items_with_images = []
        if matched_category:
            db_items = WardrobeItem.objects.filter(
                user_id=user_email, category=matched_category
            ).order_by("-is_favorite", "-added_at")[:6]
            for db_item in db_items:
                if db_item.image:
                    try:
                        img_b64 = base64.b64encode(bytes(db_item.image)).decode("utf-8")
                        similar_items_with_images.append({
                            "name": db_item.name,
                            "category": db_item.category,
                            "image_b64": img_b64,
                        })
                    except Exception:
                        pass

        visual_comparison_note = ""
        if similar_items_with_images:
            names = [s["name"] for s in similar_items_with_images]
            visual_comparison_note = f"\n\nI'm also showing you photos of their existing {matched_category} items ({', '.join(names)}) so you can visually compare silhouette, length, color, and style. Use what you SEE in these photos to make specific comparisons — don't guess."

        system_prompt = f"""You are a personal stylist doing a fitting room consultation. The user has explicitly asked you to analyze how clothing looks on their specific body, coloring, and frame. This is a consensual personal styling session — detailed physical observations about fit, body proportions, and how colors interact with their skin and features are exactly what they're paying you for. Be as specific as a tailor taking measurements.

Talk like a real person in a fitting room. No lists, no bullet points, no markdown, no asterisks. Always include a buy or skip recommendation.

Never use generic filler that could apply to anyone — every observation must be specific to what you see in this exact photo. No section headers, no labels, no bold text, no markdown. Don't guess height in feet/inches — describe proportions instead. Describe EXACTLY what you observe: where the shoulder seam falls relative to their actual shoulder, whether the fabric is bunching at the hip or pulling across the chest, how the neckline frames their jaw, whether their skin looks warmer or cooler right where it meets the fabric vs. further from it.

If the photo limits your analysis — bad angle, arms covering the garment, too far away, posture obscuring fit — give your best assessment with what you can see, then ask them to send a follow-up photo from a better angle. Be specific about what pose or angle would help (e.g. "drop your arms so I can see the shoulder line" or "step back so I can see where the hem hits"). The user can attach photos in their replies.

You are ONLY a personal stylist. If the user asks you anything unrelated to fashion, clothing, or this styling session — coding questions, math, trivia, writing requests, anything — do not answer it. Just say something like "I'm your stylist, not a search engine — let's stay focused on whether this piece works for you." Never break character.

Their style: {profile.style_identity.get('archetypes', 'unknown')}
{style_summary}

Wardrobe: {overlap_summary}"""

        first_content = []

        first_content.append({"type": "text", "text": "Photo of the item they're considering:"})
        first_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(compressed).decode('utf-8')}", "detail": "high"}
        })

        for sim in similar_items_with_images:
            first_content.append({"type": "text", "text": f"Their existing wardrobe item — {sim['name']}:"})
            first_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{sim['image_b64']}"}
            })

        wardrobe_ref = ' I showed you photos of their similar pieces too — compare visually.' if similar_items_with_images else ''

        first_message_text = f"""Write your response as flowing conversation — NO section headers, NO labels like "BODY:" or "SILHOUETTE:", NO bold text. Just talk naturally as one continuous response.

Look at this person and tell them how this piece works on them. Talk about their proportions and frame — are their legs long, is their torso short, are their shoulders narrow or broad relative to their hips? Then tell them how this garment interacts with those proportions. Where the hem hits, whether the silhouette is elongating or shortening them, whether the volume is in the right places for their frame. Don't guess their height in feet — just describe their proportions as you see them and how the garment relates to that.

Look at the color against their skin at the neckline and face. Does it bring warmth or flatten them?

Compare to their wardrobe if relevant.{wardrobe_ref} Say buy or skip and why. Ask one question."""

        first_content.append({"type": "text", "text": first_message_text})

        messages_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": first_content},
        ]

        response = get_openai_client().chat.completions.create(
            model="gpt-5.4",
            messages=messages_list,
            temperature=0.65,
        )
        oracle_reply = response.choices[0].message.content

        conversation = [
            {"role": "oracle", "text": oracle_reply},
        ]

        evaluation = ShoppingEvaluation.objects.create(
            user=request.user,
            item_image=compressed,
            item_description=item_desc,
            evaluation="",
            conversation=conversation,
            verdict="consider",
            is_complete=False,
        )

        session_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": first_message_text},
            {"role": "assistant", "content": oracle_reply},
        ]
        request.session[f"shopping_ctx_{evaluation.id}"] = {
            "system_prompt": system_prompt,
            "item_desc": json.dumps(item_desc),
            "messages": session_messages,
            "turn": 1,
            "photos_sent": 0,
        }

        return render(request, "shopping_buddy_chat.html", {
            "evaluation": evaluation,
            "item_desc": item_desc,
        })

    except UserStyleProfile.DoesNotExist:
        from django.contrib import messages
        messages.error(request, "Please create your style profile first so The Oracle can evaluate purchases for you.")
        return redirect("base_profile")
    except Exception as e:
        import traceback
        traceback.print_exc()
        from django.contrib import messages
        messages.error(request, f"Something went wrong: {str(e)}")
        return redirect("shopping_buddy")


@require_POST
@login_required
def shopping_buddy_reply(request, eval_id):
    import json
    from oracle_frontend.archetype_generator import get_openai_client

    _ensure_shopping_table()

    try:
        evaluation = ShoppingEvaluation.objects.get(id=eval_id, user=request.user)
    except ShoppingEvaluation.DoesNotExist:
        return JsonResponse({"error": "Evaluation not found."}, status=404)

    if evaluation.is_complete:
        return JsonResponse({"error": "This evaluation is already complete."}, status=400)

    user_message = (request.POST.get("message") or "").strip()
    uploaded_image = request.FILES.get("image")

    if not user_message and not uploaded_image:
        return JsonResponse({"error": "Please type a message or attach a photo."}, status=400)

    image_b64 = None
    if uploaded_image:
        try:
            raw = uploaded_image.read()
            compressed, _ext = compress_image_to_limit(raw, max_bytes=1024 * 1024, max_side=1200)
            image_b64 = base64.b64encode(compressed).decode("utf-8")
        except Exception:
            return JsonResponse({"error": "Could not process that image. Try another."}, status=400)

    ctx = request.session.get(f"shopping_ctx_{eval_id}")
    if not ctx:
        return JsonResponse({"error": "Session expired. Please start a new evaluation."}, status=400)

    turn = ctx.get("turn", 1)
    has_photo = ctx.get("photos_sent", 0)
    max_turns = 3 + min(has_photo, 2)
    messages_list = ctx["messages"]

    if image_b64:
        user_content = []
        if user_message:
            user_content.append({"type": "text", "text": user_message})
        user_content.append({"type": "text", "text": "Here's a new photo:"})
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "high"}
        })
        messages_list.append({"role": "user", "content": user_content})
        ctx["photos_sent"] = has_photo + 1
    else:
        messages_list.append({"role": "user", "content": user_message})

    if turn >= max_turns - 1:
        messages_list.append({
            "role": "system",
            "content": "This is the final turn. Give your definitive verdict now. Start with 'VERDICT:' followed by one of: STRONG BUY, WORTH CONSIDERING, SKIP IT, or YOU ALREADY OWN THIS. Then give your final honest assessment in 2-3 sentences — be direct about whether this is a smart purchase. Don't ask any more questions."
        })

    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-5.4",
            messages=messages_list,
            temperature=0.6,
        )
        oracle_reply = response.choices[0].message.content
    except Exception as e:
        return JsonResponse({"error": f"Failed to get response: {str(e)}"}, status=500)

    conversation = evaluation.conversation or []
    conv_entry = {"role": "user", "text": user_message or "(photo)"}
    if image_b64:
        conv_entry["image_b64"] = image_b64
    conversation.append(conv_entry)
    conversation.append({"role": "oracle", "text": oracle_reply})
    evaluation.conversation = conversation

    is_final = turn >= max_turns - 1
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

    evaluation.save()

    messages_list.append({"role": "assistant", "content": oracle_reply})
    ctx["messages"] = messages_list
    ctx["turn"] = turn + 1
    request.session[f"shopping_ctx_{eval_id}"] = ctx
    request.session.modified = True

    return JsonResponse({
        "reply": oracle_reply,
        "is_complete": evaluation.is_complete,
        "verdict": evaluation.get_verdict_display() if evaluation.is_complete else None,
    })
