import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
from oracle_data.models import WardrobeItem
from oracle_frontend.shared_helpers import get_serialized_wardrobe, fetch_user_wardrobe
from oracle_frontend.utils import update_last_used


load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


def generate_style_archetype(summary_text: str, user_id: str) -> str:
    wardrobe_items = fetch_user_wardrobe(user_id)
    if wardrobe_items:
        wardrobe_block = "\n".join([
            f"- {w['name']} ({w['category']}) | Season: {w.get('season', 'n/a')} | Usage: {w.get('usage', 'n/a')}"
            for w in wardrobe_items
        ])
        wardrobe_note = f"\n**User's Wardrobe Snapshot**:\n{wardrobe_block}"
    else:
        wardrobe_note = ""

    prompt = f"""You are The Oracle — an emotionally intelligent stylist who understands clothing as a mirror of emotion, movement, and identity.

You speak in refined prose. No bullet points. No markdown. No headers. No asterisks. Just flowing, literary text.

Based on the following profile, write a 2-3 paragraph archetype reading. Begin with a short evocative name for their style archetype (e.g., "Quiet Authority" or "Soft Armor"), then flow directly into prose exploring their style psyche — the tension between structure and fluidity, their relationship to form and fabric, what their choices reveal about how they move through the world.

Write as if you're composing a personal letter, not a listicle. Be specific. Be poetic but grounded.

---

Style Profile:
{summary_text}

{wardrobe_note}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )

    return response.choices[0].message.content


def generate_today_styling_suggestion(summary_text, daily_context, model_name="ft:gpt-4o-mini-2024-07-18:personal::D23UTjXs"):
    import json
    from openai import OpenAIError

    user_id = daily_context["user_id"]
    focus_item_name = daily_context.get("item_focus", "").strip()

    wardrobe_items = get_serialized_wardrobe(user_id)
    focus_items = []

    # ----- Handle image-derived pseudo item -----
    image_desc = daily_context.get("image_description", {})
    image_name_hint = image_desc.get("name_hint", "").strip()

    # If name_hint is missing or 'None', create a smart fallback name
    if not image_name_hint or image_name_hint.lower() == "none":
        color = image_desc.get("colors", ["Black"])[0].capitalize()
        category = image_desc.get("category_guess", "Item").capitalize()
        image_name_hint = f"{color} {category} (uploaded)"

    if isinstance(image_desc, dict) and image_desc:
        pseudo_item = {
            "name": image_name_hint,
            "category": image_desc.get("category_guess", "unknown"),
            "color": ", ".join(image_desc.get("colors", [])),
            "style_tags": image_desc.get("patterns", []) + [image_desc.get("silhouette", "")],
            "is_uploaded_focus": True,
            "image_b64": image_desc.get("image_b64")  
        }
        wardrobe_items.insert(0, pseudo_item)
        focus_items.append(pseudo_item)

    # ----- Handle wardrobe item from item_focus -----
    stored_focus = next(
        (item for item in wardrobe_items if focus_item_name.lower() in item.get("name", "").lower()),
        None
    )
    if stored_focus:
        focus_items.append(stored_focus)

    # ----- Compose focus note -----
    if focus_items:
        focus_descriptions = "\n".join(json.dumps(item, indent=2) for item in focus_items)
        focus_note = f"""
        The following items are marked as focus items and MUST be styled into today’s outfit:
        {focus_descriptions}

        Do NOT ignore or replace these. Each should appear as-is, without changing their category or style."""
    else:
        focus_note = "No specific focus item, use any item from the wardrobe as the anchor."

    wardrobe_note = f"\nThe user's wardrobe (JSON format):\n{json.dumps(wardrobe_items, indent=2)}"

    # ----- Final prompt -----
    prompt = f"""
You are The Oracle — an emotionally intelligent stylist.

Based on the user's style profile and today's context, write a short styling suggestion in flowing prose. No markdown. No bullet points. No asterisks. No headers. Just natural, refined sentences.

Structure your response as:
1. A brief opening line about the mood/vibe of the outfit (1 sentence)
2. The outfit itself, naming specific items naturally in prose (1-2 sentences)
3. Optional: a closing thought on why it works (1 sentence)

Rules:
- Include exactly one item per category, except when focus items span multiple categories
- Prioritize items tagged with is_uploaded_focus
- Only use items from the wardrobe provided — do not invent items
- The focus items below MUST appear in your suggestion

{focus_note}

---

Style Profile:
{summary_text}

Today's Context:
Mood: {daily_context.get("mood_today", "")}
Occasion: {daily_context.get("occasion", "")}
Weather: {daily_context.get("weather", "")}
{wardrobe_note}
""".strip()

    if isinstance(image_desc, dict) and image_desc:
        prompt += f"\nVisual reference: {json.dumps(image_desc, indent=2)}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        suggestion = response.choices[0].message.content
    except OpenAIError as e:
        suggestion = f"Styling suggestion could not be generated. Error: {str(e)}"

    item_names = [item['name'] for item in wardrobe_items if item['name'].lower() in suggestion.lower()]
    update_last_used(user_id, item_names)

    return suggestion





