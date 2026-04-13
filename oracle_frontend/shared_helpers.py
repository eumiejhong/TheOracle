from oracle_data.models import WardrobeItem, ShoppingEvaluation, UserStyleProfile
from django.utils import timezone
from operator import itemgetter


def fetch_user_wardrobe(user_id):
    items = WardrobeItem.objects.filter(user_id=user_id)
    return [
        {
            "name": item.name,
            "category": item.category,
            "season": item.season,   
            "favorite": item.is_favorite,  
            "usage": item.last_used  
        }
        for item in items
    ]


# def get_sorted_wardrobe(user_id):
#     wardrobe = fetch_user_wardrobe(user_id)
    
#     now = timezone.now()
#     for item in wardrobe:
#         last_used = item["usage"]
#         if last_used:
#             days_since_used = (now - last_used).days
#         else:
#             days_since_used = 999  

#         item["staleness_score"] = days_since_used

#     return sorted(wardrobe, key=itemgetter("staleness_score"), reverse=True)

def get_serialized_wardrobe(user_id):
    items = WardrobeItem.objects.filter(user_id=user_id).order_by("-is_favorite", "-added_at")
    serialized = []
    for item in items:
        serialized.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "color": item.color,
            "style_tags": item.style_tags,
            "season": item.season,
            "is_favorite": item.is_favorite,
        })
    return serialized


def build_shopping_buddy_context(user):
    """Assemble rich personal context for the Shopping Buddy system prompt."""
    email = user.email
    sections = []

    # --- Style archetype narrative ---
    try:
        profile = UserStyleProfile.objects.filter(user_id=email).latest("created_at")
        if profile.style_archetype:
            paragraphs = profile.style_archetype.strip().split("\n\n")
            archetype_intro = paragraphs[0] if paragraphs else profile.style_archetype[:500]
            sections.append(f"STYLE IDENTITY:\n{archetype_intro}")

        # --- Aspirational style ---
        aspirational = profile.style_identity.get("aspirational_style", "")
        if aspirational:
            sections.append(f"Their aspirational style: {aspirational}")

        # --- Budget, wardrobe phase, shopping behavior ---
        lifestyle = profile.lifestyle or {}
        lifestyle_notes = []
        if lifestyle.get("budget_preference"):
            lifestyle_notes.append(f"Budget comfort: {lifestyle['budget_preference']}")
        if lifestyle.get("wardrobe_phase"):
            lifestyle_notes.append(f"Wardrobe phase: {lifestyle['wardrobe_phase']}")
        if lifestyle.get("shopping_behavior"):
            lifestyle_notes.append(f"Shopping style: {lifestyle['shopping_behavior']}")
        if lifestyle.get("life_event"):
            lifestyle_notes.append(f"Life context: {lifestyle['life_event']}")
        if lifestyle_notes:
            sections.append("LIFESTYLE CONTEXT:\n" + ". ".join(lifestyle_notes) + ".")
    except UserStyleProfile.DoesNotExist:
        pass

    # --- Favorite wardrobe items ---
    favorites = list(
        WardrobeItem.objects.filter(user_id=email, is_favorite=True)
        .values_list("name", flat=True)[:8]
    )
    if favorites:
        sections.append(
            f"FAVORITE PIECES (the items they reach for most): {', '.join(favorites)}"
        )

    # --- Past shopping history stats ---
    past_evals = list(
        ShoppingEvaluation.objects.filter(user=user, is_complete=True)
        .order_by("-created_at")[:20]
    )
    if past_evals:
        total = len(past_evals)
        verdicts = {}
        categories_shopped = {}
        for ev in past_evals:
            v = ev.get_verdict_display()
            verdicts[v] = verdicts.get(v, 0) + 1
            cat = (ev.item_description or {}).get("category_guess", "unknown")
            if cat and cat != "unknown":
                categories_shopped[cat] = categories_shopped.get(cat, 0) + 1

        verdict_breakdown = ", ".join(f"{v}: {c}" for v, c in verdicts.items())
        stats_line = f"Past {total} evaluations: {verdict_breakdown}."

        skip_count = verdicts.get("Skip It", 0)
        buy_count = verdicts.get("Strong Buy", 0)
        if total >= 3:
            if skip_count > total * 0.6:
                stats_line += " They skip most things \u2014 they're selective."
            elif buy_count > total * 0.6:
                stats_line += " They tend to buy most things they try."

        if categories_shopped:
            top_cats = sorted(categories_shopped.items(), key=lambda x: -x[1])[:3]
            cat_str = ", ".join(f"{c} ({n})" for c, n in top_cats)
            stats_line += f" Top categories they shop for: {cat_str}."

        sections.append(f"SHOPPING HISTORY:\n{stats_line}")

        recent = past_evals[:5]
        recent_lines = []
        for ev in recent:
            cat = (ev.item_description or {}).get("category_guess", "?")
            verdict = ev.get_verdict_display()
            ago_days = (timezone.now() - ev.created_at).days
            if ago_days == 0:
                when = "today"
            elif ago_days == 1:
                when = "yesterday"
            elif ago_days < 7:
                when = f"{ago_days} days ago"
            else:
                when = f"{ago_days // 7}w ago"
            recent_lines.append(f"  {cat} \u2014 {verdict} ({when})")
        sections.append("RECENT EVALUATIONS:\n" + "\n".join(recent_lines))

    return "\n\n".join(sections)

