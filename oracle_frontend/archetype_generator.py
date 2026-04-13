import json
from openai import OpenAIError
from oracle_frontend.ai_config import get_openai_client, OPENAI_MODEL
from oracle_frontend.shared_helpers import get_serialized_wardrobe, fetch_user_wardrobe
from oracle_frontend.utils import update_last_used


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

    prompt = f"""You are The Oracle \u2014 a sharp, experienced personal stylist with an editorial eye and deep knowledge of fashion houses, fit, and proportion.

No bullet points. No markdown. No headers. No asterisks. Just clear, confident sentences.

Based on the following profile, write a 2-3 paragraph style assessment. Start with a concise archetype name (e.g., "Quiet Authority" or "Modern Minimalist"), then describe their style in the way a top stylist would brief a client:

- What silhouettes and proportions they gravitate toward
- The brands, references, or aesthetic world they live in
- How their wardrobe choices reflect their lifestyle and preferences
- Specific, practical observations \u2014 not abstract metaphors

Be direct and knowledgeable, like a stylist who actually understands garments, not a poet. Think Celine-era Phoebe Philo, The Row, or a Vogue editor\u2019s fitting notes. Warm but precise.

---

Style Profile:
{summary_text}

{wardrobe_note}"""

    response = get_openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content


def generate_today_styling_suggestion(summary_text, daily_context, model_name=None):
    user_id = daily_context["user_id"]
    focus_item_name = daily_context.get("item_focus", "").strip()
    model = model_name or OPENAI_MODEL

    wardrobe_items = get_serialized_wardrobe(user_id)
    focus_items = []

    # ----- Handle image-derived pseudo item -----
    image_desc = daily_context.get("image_description", {})
    image_name_hint = image_desc.get("name_hint", "").strip()

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
        focus_categories = [item.get("category", "unknown") for item in focus_items]
        category_list = ", ".join(c for c in focus_categories if c and c != "unknown")
        focus_note = (
            f"The following items are the FOCUS of today's outfit and MUST be included:\n"
            f"{focus_descriptions}\n\n"
            f"CRITICAL RULES for focus items:\n"
            f"- Build the entire outfit AROUND these items.\n"
            f"- Each focus item fills its category slot. If the focus item is a jacket, coat, "
            f"blazer, or any outerwear, it IS the outerwear layer. Do NOT suggest a second "
            f"outerwear piece on top of it or alongside it. Same for any other category: "
            f"if the focus is trousers, do not add another bottom.\n"
            f"- Never double up on the same category as the focus item.\n"
            f"- The focus item's detected category: {category_list or 'see item details above'}.\n"
            f"- Do NOT ignore, replace, or rename the focus item."
        )
    else:
        focus_note = "No specific focus item, use any item from the wardrobe as the anchor."

    wardrobe_note = f"\nThe user's wardrobe (JSON format):\n{json.dumps(wardrobe_items, indent=2)}"

    # ----- Final prompt -----
    prompt = f"""You are The Oracle \u2014 a sharp personal stylist with deep knowledge of fashion, fit, and proportion.

Your job: pull a complete outfit from the user's ACTUAL wardrobe for today. Every single piece you suggest must be referenced by its EXACT name from the wardrobe list below.

WRONG \u2014 never do this:
"Layer the trench over a simple top and tailored bottoms. Pair with loafers for a chic look."
This is wrong because it uses vague descriptions and doesn't name actual wardrobe items.

ALSO WRONG \u2014 never do this:
"The Black Leather Loafers keep it grounded."
This is wrong because "Black Leather Loafers" does not exist in the user's wardrobe. You CANNOT invent item names.

ALSO WRONG \u2014 never suggest two items in the same category:
"Wear the uploaded jacket and layer the cream tweed blazer over it."
This is wrong because you cannot suggest two outerwear pieces. The focus item fills its slot.

You must ONLY use item names that appear in the wardrobe list provided at the bottom of this prompt. If an item name is not in that list, you cannot suggest it.

Format (no markdown, no asterisks, no headers, no bullet points \u2014 just natural sentences):
1. One sentence on the overall direction for the day.
2. Name EVERY piece in the outfit \u2014 top, bottom, outerwear (if needed), shoes, bag/accessory. Use the EXACT item name as it appears in the wardrobe list for each piece, and briefly say why it works here.
3. End with one specific styling tip (how to wear or style a piece).

RULES:
- ONLY use items from the wardrobe list below. If an item is not in the list, do NOT mention it.
- When referencing item names in your prose, use the name from the wardrobe but adapt it so it reads naturally. Drop leading words like "My", "My old", "The", etc. that sound awkward in a sentence. For example, if the wardrobe name is "My black Lemaire x Uniqlo sneakers", write "the black Lemaire x Uniqlo sneakers" in your sentence. The item must still be clearly identifiable \u2014 only strip possessive/article prefixes, never change the core description.
- Do not use generic descriptions like "a white tee" or "dark trousers" \u2014 use the actual name (cleaned up as above).
- If a focus item is specified, build the outfit around it. The focus item fills its category slot \u2014 do NOT suggest another item from the same category (e.g. no second jacket if the focus is a jacket).
- Double-check every item you reference against the wardrobe list before including it.

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
        response = get_openai_client().chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.65
        )
        suggestion = response.choices[0].message.content
    except OpenAIError as e:
        suggestion = f"Styling suggestion could not be generated. Error: {str(e)}"

    item_names = [item['name'] for item in wardrobe_items if item['name'].lower() in suggestion.lower()]
    update_last_used(user_id, item_names)

    return suggestion
