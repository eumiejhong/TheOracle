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

        system_prompt = f"""You are The Oracle — a sharp, honest personal stylist. You're having a one-on-one conversation with someone about whether they should buy a specific item. This should feel like a personalized shopping buddy experience.

IMPORTANT RULES:
- Speak directly to the person using "you" and "your" — never say "the client" or "the user"
- FIRST, check if the photo shows the person WEARING the item (fitting room selfie, mirror pic, trying it on). If they are wearing it, you MUST comment on:
  * How it fits their body — is the length right, are the shoulders sitting correctly, is it too tight/loose, does the drape work?
  * How the color works with their complexion — reference their skin tone ({profile.appearance.get('skin_tone', 'unknown')}), undertone ({profile.appearance.get('undertone', 'unknown')}), and contrast level ({profile.appearance.get('contrast_level', 'unknown')})
  * The overall vibe — does this look like "them"? Does it match how they want to present themselves?
- If the photo is just the item (product shot, hanger, flat lay), focus on describing the item and comparing to their wardrobe
- For wardrobe items where you can see photos, make specific visual comparisons (length, silhouette, texture, color)
- For items you can't see, only reference them by name and category — don't invent details
- Be honest — if something doesn't flatter them, say so directly but kindly
- No markdown, no asterisks, no bullet points. Just natural, direct sentences.
- End each message with a specific question to keep the conversation going (until you give a final verdict)

THEIR STYLE PROFILE:
{style_summary}

THEIR CURRENT WARDROBE:
{overlap_summary}"""

        first_message_text = f"""Look at the attached photo very carefully. This person is considering buying this item.
{visual_comparison_note}

STEP 1 — Is the person WEARING the item in the photo?

If YES (fitting room, mirror selfie, trying it on), your response MUST start with how it looks ON THEM:
- FIT: Comment on shoulder placement, length relative to their proportions, whether it's pulling or draping well, if the silhouette flatters their frame. Be specific — "the shoulders are sitting about an inch too wide" not "it fits nicely."
- COLOR: Look at their ACTUAL face, skin, and hair in the photo. Describe what you see — their complexion, their coloring. Then assess whether this garment's color brings warmth to their face, creates flattering contrast, or washes them out. DO NOT just repeat their profile data back to them. Use your own visual analysis first. Their profile says skin tone is {profile.appearance.get('skin_tone', 'unknown')} with {profile.appearance.get('undertone', 'unknown')} undertone — use this as a reference point, not a script.
- VIBE: Look at how they carry themselves in the photo — their posture, energy, overall presence. Does this piece suit that energy? Their style archetype is {profile.style_identity.get('archetypes', 'unknown')}. Does this look like it belongs on them or feels like a costume?

If NO (product photo, flat lay, hanger shot), describe the item itself: category, colors, fabric cues, silhouette.

STEP 2 — Compare to their wardrobe. Do they already own something that fills this same role? Name specific pieces.

STEP 3 — End with a specific question to continue the conversation.

Be conversational, direct, and personal — like a best friend who's a stylist and is right there shopping with them. DO NOT just generically describe the item. The value is in how it works for THIS specific person."""

        first_content = [{"type": "text", "text": first_message_text}]
        first_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(compressed).decode('utf-8')}"}
        })
        for sim in similar_items_with_images:
            first_content.append({"type": "text", "text": f"[Their existing item: {sim['name']}]"})
            first_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{sim['image_b64']}"}
            })

        messages_list = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": first_content},
        ]

        response = get_openai_client().chat.completions.create(
            model="gpt-4o",
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
    if not user_message:
        return JsonResponse({"error": "Please type a message."}, status=400)

    ctx = request.session.get(f"shopping_ctx_{eval_id}")
    if not ctx:
        return JsonResponse({"error": "Session expired. Please start a new evaluation."}, status=400)

    turn = ctx.get("turn", 1)
    messages_list = ctx["messages"]
    messages_list.append({"role": "user", "content": user_message})

    if turn >= 2:
        messages_list.append({
            "role": "system",
            "content": "This is the final turn. Give your definitive verdict now. Start with 'VERDICT:' followed by one of: STRONG BUY, WORTH CONSIDERING, SKIP IT, or YOU ALREADY OWN THIS. Then give your final honest assessment in 2-3 sentences — be direct about whether this is a smart purchase. Don't ask any more questions."
        })

    try:
        response = get_openai_client().chat.completions.create(
            model="gpt-4o",
            messages=messages_list,
            temperature=0.6,
        )
        oracle_reply = response.choices[0].message.content
    except Exception as e:
        return JsonResponse({"error": f"Failed to get response: {str(e)}"}, status=500)

    conversation = evaluation.conversation or []
    conversation.append({"role": "user", "text": user_message})
    conversation.append({"role": "oracle", "text": oracle_reply})
    evaluation.conversation = conversation

    if turn >= 2:
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
