"""Per-field scoring functions.

Each scorer takes (predicted, truth) and returns a float in [0.0, 1.0],
or `None` if the field has no ground truth (skip from accuracy averages).

We deliberately keep these functions field-aware rather than generic — material
needs synonym normalization, set fields use Jaccard, free-text uses overlap, etc.
"""

from __future__ import annotations

from typing import Any

from .. import taxonomy


# ---------------------------------------------------------------------------
# Color families — used by score_color_similarity to give partial credit when
# the model picks a more-precise sibling color than what the truth specifies
# (e.g. truth="green", pred="olive" -> 0.5; truth="black", pred="charcoal" -> 0.5).
# A color may belong to multiple families (intentional).
# ---------------------------------------------------------------------------
COLOR_FAMILIES: dict[str, set[str]] = {
    "neutral_warm":   {"beige", "tan", "camel", "cream", "ivory", "khaki"},
    "browns":         {"brown", "chocolate", "rust", "khaki", "camel", "tan"},
    "blacks":         {"black", "charcoal"},
    "greys":          {"grey", "charcoal", "silver"},
    "whites":         {"white", "ivory", "cream"},
    "blues":          {"blue", "navy", "sky-blue", "teal"},
    "greens":         {"green", "olive", "forest-green", "sage", "mint", "khaki"},
    "reds":           {"red", "burgundy", "wine", "rust"},
    "pinks":          {"pink", "blush", "fuchsia"},
    "yellows":        {"yellow", "mustard", "gold"},
    "purples":        {"purple", "lavender"},
    "oranges":        {"orange", "rust", "mustard"},
}


def _same_color_family(a: str, b: str) -> bool:
    a, b = a.strip().lower(), b.strip().lower()
    for members in COLOR_FAMILIES.values():
        if a in members and b in members:
            return True
    return False


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def _norm(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()


def _to_set(v: Any) -> set[str]:
    if v is None:
        return set()
    if isinstance(v, str):
        return {_norm(v)} if v.strip() else set()
    if isinstance(v, (list, tuple, set)):
        return {_norm(x) for x in v if x and str(x).strip()}
    return {_norm(v)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Field-specific scorers
# ---------------------------------------------------------------------------
def score_exact(pred: Any, truth: Any) -> float | None:
    """Strict equality after lowercasing/stripping."""
    if truth is None or _norm(truth) == "":
        return None
    return 1.0 if _norm(pred) == _norm(truth) else 0.0


def score_color(pred: Any, truth: Any) -> float | None:
    """Color match with partial credit for same-family colors.

      1.0 — exact match
      0.5 — both colors live in at least one common family (e.g. olive↔green,
            charcoal↔black, camel↔beige). Reflects "more precise but not wrong".
      0.0 — different families
    """
    if truth is None or _norm(truth) == "":
        return None
    p, t = _norm(pred), _norm(truth)
    if not p:
        return 0.0
    if p == t:
        return 1.0
    # "multi" is its own beast — only matches itself
    if p == "multi" or t == "multi":
        return 0.0
    return 0.5 if _same_color_family(p, t) else 0.0


def score_subcategory(pred: Any, truth: Any) -> float | None:
    """Subcategory match with wildcard credit for "Other X" truth labels.

    Many sources (Grailed, eBay) use coarse "Other Outerwear" / "Other Top"
    buckets when the listing-level subcategory isn't precise. If the model
    returns ANY subcategory that lives in the same parent category, give it
    0.5 — the model is being more specific than the truth, not wrong.
    """
    if truth is None or _norm(truth) == "":
        return None
    p, t = _norm(pred), _norm(truth)
    if p == t:
        return 1.0
    if not p:
        return 0.0
    # "Other X" wildcard
    if t.startswith("other "):
        parent_word = t.split("other ", 1)[1].strip().lower()
        # Resolve parent_word -> CATEGORIES key, then check pred is in that bucket
        for cat, subs in taxonomy.SUBCATEGORIES.items():
            if cat.lower() in parent_word or parent_word in cat.lower():
                pred_in_cat = any(_norm(s) == p for s in subs)
                return 0.5 if pred_in_cat else 0.0
    return 0.0


def score_brand(pred: Any, truth: Any) -> float | None:
    """Brand match after normalizing both through BRAND_ALIASES."""
    if truth is None or _norm(truth) == "":
        return None
    pred_canon, _ = taxonomy.normalize_brand(str(pred or ""))
    truth_canon, _ = taxonomy.normalize_brand(str(truth))
    if not _norm(truth_canon):
        return None
    return 1.0 if _norm(pred_canon) == _norm(truth_canon) else 0.0


def score_material(pred: Any, truth: Any) -> float | None:
    """Material match after normalizing both through MATERIAL_SYNONYMS."""
    if truth is None or _norm(truth) == "":
        return None
    pred_canon, _ = taxonomy.normalize_material(str(pred or ""))
    truth_canon, _ = taxonomy.normalize_material(str(truth))
    if truth_canon == "other":
        return None  # truth itself wasn't classifiable -> skip
    return 1.0 if pred_canon == truth_canon else 0.0


def score_set_jaccard(pred: Any, truth: Any) -> float | None:
    """Jaccard similarity between two sets (e.g., silhouette, secondary_colors)."""
    truth_set = _to_set(truth)
    if not truth_set:
        return None
    pred_set = _to_set(pred)
    return _jaccard(pred_set, truth_set)


def score_set_recall(pred: Any, truth: Any) -> float | None:
    """Recall: fraction of truth-set tokens present in pred-set.

    More forgiving than Jaccard for fields where the model picks 3-5 from a long
    enum (style_tags) — we mostly care about whether it caught the truth tags,
    not whether it added extras.
    """
    truth_set = _to_set(truth)
    if not truth_set:
        return None
    pred_set = _to_set(pred)
    if not pred_set:
        return 0.0
    return len(pred_set & truth_set) / len(truth_set)


def score_condition_adjacent(pred: Any, truth: Any) -> float | None:
    """Condition tier match. 1.0 if exact, 0.5 if adjacent tier, 0.0 otherwise."""
    if truth is None or _norm(truth) == "":
        return None
    grades = [g[0] for g in taxonomy.CONDITION_GRADES]
    p, t = _norm(pred), _norm(truth)
    if t not in grades:
        return None
    if p == t:
        return 1.0
    if p in grades and abs(grades.index(p) - grades.index(t)) == 1:
        return 0.5
    return 0.0


def score_era_adjacent(pred: Any, truth: Any) -> float | None:
    """Era match. 1.0 if exact, 0.5 if neighboring decade, 0.0 otherwise."""
    if truth is None or _norm(truth) == "":
        return None
    eras = taxonomy.ERA_ESTIMATES
    p, t = _norm(pred), _norm(truth)
    if t not in [e.lower() for e in eras]:
        return None
    if p == t:
        return 1.0
    eras_l = [e.lower() for e in eras]
    if p in eras_l and abs(eras_l.index(p) - eras_l.index(t)) == 1:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# The field map: which scorer applies to which field
# ---------------------------------------------------------------------------
FIELD_SCORERS: dict[str, callable] = {
    "category": score_exact,
    "subcategory": score_subcategory,
    "primary_color": score_color,
    "color_palette": score_exact,
    "pattern": score_exact,
    "size_label": score_exact,
    "primary_material": score_material,
    "brand": score_brand,
    "condition": score_condition_adjacent,
    "era_estimate": score_era_adjacent,
    "silhouette": score_set_jaccard,
    "secondary_colors": score_set_jaccard,
    "style_tags": score_set_recall,
}


# Fields that REQUIRE a label/tag photo to score fairly. If the eval run
# didn't include a "label" image, we skip scoring these fields rather than
# penalize the model for missing info it never had.
LABEL_DEPENDENT_FIELDS = {"size_label"}


def score_item(
    predicted: dict,
    truth: dict,
    image_roles: set[str] | None = None,
) -> dict[str, float | None]:
    """Score a single item. Returns {field: score | None}.

    `image_roles` is the set of roles that were ACTUALLY sent to the analyzer
    for this run (e.g. {"front", "back", "detail"} for a no-label run). Used
    to skip label-dependent fields when no label was sent.
    """
    image_roles = image_roles or set()
    has_label = "label" in image_roles

    out: dict[str, float | None] = {}
    for field, scorer in FIELD_SCORERS.items():
        if field not in truth:
            out[field] = None
            continue
        if field in LABEL_DEPENDENT_FIELDS and not has_label:
            out[field] = None  # skip — unfair to score without a label photo
            continue
        out[field] = scorer(predicted.get(field), truth.get(field))
    return out


def aggregate(per_item_scores: list[dict[str, float | None]]) -> dict[str, dict]:
    """Aggregate per-item scores into per-field stats.

    Returns: {field: {"mean": float, "n": int, "missing": int}}
    """
    fields = sorted({k for d in per_item_scores for k in d.keys()})
    out: dict[str, dict] = {}
    for f in fields:
        scored = [d[f] for d in per_item_scores if d.get(f) is not None]
        missing = sum(1 for d in per_item_scores if d.get(f) is None)
        out[f] = {
            "mean": (sum(scored) / len(scored)) if scored else 0.0,
            "n": len(scored),
            "missing": missing,
        }
    return out
