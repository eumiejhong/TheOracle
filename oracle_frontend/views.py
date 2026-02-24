from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import base64

from oracle_data.models import UserStyleProfile, DailyStyleInput, WardrobeItem
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

            saved_profile = UserStyleProfile.objects.filter(user_id=user_email).first()
            return render(request, "profile_saved.html", {
                "profile": profile,
                "archetype": saved_profile.style_archetype if saved_profile else ""
            })
    else:
        form = BaseStyleProfileForm()

    return render(request, "base_style_profile_form.html", {"form": form})


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

            # Extract visual descriptors BEFORE saving to model
            descriptors = describe_image_with_gpt4v(image_file)

            # Save the wardrobe item
            wardrobe_item = WardrobeItem.objects.create(
                user_id=user_id,
                name=form.cleaned_data["name"],
                category=form.cleaned_data["category"],
                image=image_file,
                visual_descriptors=descriptors  
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

    name = (request.POST.get("item_name") or "").strip()
    category = request.POST.get("category", "Uncategorized")
    if not name:
        return JsonResponse({"message": "Missing item name."}, status=400)

    # Keep a safety margin under DATA_UPLOAD_MAX_MEMORY_SIZE
    hard_limit = getattr(settings, "DATA_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)
    max_bytes = max(1024 * 1024, hard_limit - 128 * 1024)  # at least 1MB, minus 128KB buffer

    # --- Option 1: file uploaded via FormData (preferred; no base64 bloat) ---
    uploaded_file = request.FILES.get("image")
    if uploaded_file:
        raw = uploaded_file.read()
        compressed, ext = _compress_image_to_limit(raw, max_bytes=max_bytes, max_side=1600)
        from .models import WardrobeItem
        item = WardrobeItem(user_id=request.user.email, name=name, category=category)
        item.image.save(f"{slugify(name)}.{ext}", ContentFile(compressed), save=True)
        return JsonResponse({"message": f"✅ '{name}' added to your wardrobe!"})

    # --- Option 2: base64 fallback (works only if request size didn't exceed Django's limit) ---
    image_b64 = (request.POST.get("image_b64") or "").strip()
    if image_b64:
        # Strip data URL prefix if present
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        try:
            raw = base64.b64decode(image_b64)
        except Exception:
            return JsonResponse({"message": "Invalid image data."}, status=400)

        compressed, ext = _compress_image_to_limit(raw, max_bytes=max_bytes, max_side=1600)
        from .models import WardrobeItem
        item = WardrobeItem(user_id=request.user.email, name=name, category=category)
        item.image.save(f"{slugify(name)}.{ext}", ContentFile(compressed), save=True)
        return JsonResponse({"message": f"✅ '{name}' added to your wardrobe!"})

    return JsonResponse({"message": "Missing image (upload a file or include image_b64)."}, status=400)


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
