"""Multi-image garment analyzer.

Accepts 1-6 images of a single garment (with optional per-image roles), runs a
single GPT vision call with the controlled-vocabulary taxonomy injected as
enum constraints, parses + normalizes the JSON output, and returns a structured
metadata dict.

Output schema (returned by `analyze_garment`):
{
  "category":           str (from CATEGORIES),
  "subcategory":        str (from SUBCATEGORIES[category]),
  "silhouette":         list[str] (1-4 from SILHOUETTES),
  "primary_color":      str (from COLORS_PRIMARY),
  "secondary_colors":   list[str] (0-3 from COLORS_PRIMARY),
  "color_palette":      str (from COLOR_PALETTES),
  "pattern":            str (from PATTERNS),
  "primary_material":   str (from MATERIAL_PRIMARY, normalized),
  "material_raw":       str (free text, e.g. "cotton gabardine"),
  "material_confidence":"high"|"medium"|"low",
  "brand":              str (canonical, normalized),
  "brand_confidence":   "high"|"medium"|"low",
  "brand_known":        bool,
  "size_label":         str | None (raw label text if visible),
  "condition":          str (from CONDITION_GRADES keys),
  "condition_notes":    str,
  "era_estimate":       str | None (from ERA_ESTIMATES),
  "style_tags":         list[str] (3-5 from STYLE_TAGS_CANONICAL),
  "style_descriptors":  list[str] (3-7 free-text aesthetic descriptors),
  "key_details":        list[str] (notable construction/design features),
  "model": str, "input_tokens": int, "output_tokens": int
}

Failures raise `AnalyzerError` (caller should map to HTTP 422 / 500).
"""

from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import dataclass

from PIL import Image

from oracle_frontend.ai_config import get_openai_client, OPENAI_MODEL

from . import taxonomy

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Errors + types
# ---------------------------------------------------------------------------
class AnalyzerError(Exception):
    """Raised when analysis fails (model error, parse error, validation error)."""


@dataclass
class ImageInput:
    """One image plus an optional role hint."""
    bytes_data: bytes
    role: str = "front"  # one of taxonomy.IMAGE_ROLES
    filename: str = ""


# ---------------------------------------------------------------------------
# Image preprocessing
# ---------------------------------------------------------------------------
def _prepare_image_for_vision(raw: bytes, max_side: int = 1024, quality: int = 85) -> bytes:
    """Convert any input (HEIC/PNG/etc) to a reasonably sized JPEG for the vision model."""
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _to_data_url(jpg_bytes: bytes) -> str:
    b64 = base64.b64encode(jpg_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a senior fashion cataloger working for a luxury resale platform. "
    "You analyze garment photos and produce strict, machine-readable metadata "
    "by selecting from controlled vocabularies. You never invent values outside "
    "the provided enums. When uncertain, you mark confidence as 'low' and "
    "describe what you can see rather than guessing."
)


def _build_user_prompt(images: list[ImageInput], hint: str | None) -> str:
    role_lines = []
    for i, img in enumerate(images, start=1):
        role_lines.append(f"  Image {i}: role={img.role}")
    role_block = "\n".join(role_lines) if role_lines else "  (no role hints provided)"

    hint_block = f"\nUSER HINT (optional, may be wrong): {hint}\n" if hint else ""

    return f"""You are analyzing photos of a SINGLE garment for a resale listing.

You will receive {len(images)} image(s). Each image has a role:
{role_block}

How to use the roles:
- "front" / "back": overall silhouette, color, length, drape, neckline
- "label": brand name, size label, material composition, country of origin
- "detail": fabric texture, hardware, stitching, prints, embellishments
- "worn": fit and proportions on a body
- "damage": condition flaws (use to downgrade condition grade)
{hint_block}
You MUST return ONLY valid JSON matching this exact schema. Use the controlled
vocabularies — do NOT invent new values for enum fields.

# CONTROLLED VOCABULARIES

category (pick exactly one):
  {taxonomy.enum_for_prompt(taxonomy.CATEGORIES)}

subcategory (pick exactly one, scoped to your chosen category):
{taxonomy.subcategories_for_prompt()}

silhouette (pick 1-4 that best apply):
  {taxonomy.enum_for_prompt(taxonomy.SILHOUETTES)}

primary_color (pick exactly one):
  {taxonomy.enum_for_prompt(taxonomy.COLORS_PRIMARY)}

secondary_colors (pick 0-3, from the same primary_color list, excluding the primary)

color_palette (pick exactly one):
  {taxonomy.enum_for_prompt(taxonomy.COLOR_PALETTES)}

pattern (pick exactly one):
  {taxonomy.enum_for_prompt(taxonomy.PATTERNS)}

primary_material (pick exactly one — your best inference of the dominant fabric):
  {taxonomy.enum_for_prompt(taxonomy.MATERIAL_PRIMARY)}

condition (pick exactly one grade key):
{taxonomy.condition_grades_for_prompt()}

era_estimate (pick exactly one or null):
  {taxonomy.enum_for_prompt(taxonomy.ERA_ESTIMATES)}

style_tags (pick 3-5 that best apply, from this canonical list ONLY):
  {taxonomy.enum_for_prompt(taxonomy.STYLE_TAGS_CANONICAL)}

# FREE-TEXT FIELDS (do not guess wildly — keep concise and visually grounded)

material_raw: short free-text fabric description IF you can see/read it
  (e.g. "cotton gabardine", "wool boucle", "calfskin"). Otherwise "".
brand: read it from the label image if present, else infer from logos/hardware/silhouette.
  If you cannot tell, return "" with brand_confidence="low".
size_label: literal size text from the label if visible (e.g. "M", "38", "EU 40"), else null.
condition_notes: 1-2 sentences describing what you actually see (pilling, fading, scuffs, etc.).
style_descriptors: 3-7 short evocative phrases (e.g. ["quiet luxury staple", "elevated minimalism",
  "investment outerwear"]). Free-form but grounded — avoid generic filler.
key_details: 3-6 short notable design/construction observations
  (e.g. ["double-faced wool", "horn buttons", "raglan sleeves"]).

# CONFIDENCE GUIDANCE
- "high": clearly visible / read directly from the image
- "medium": strong visual inference but not 100% certain
- "low": guessing from limited information (still record but flag it)

# REQUIRED JSON SHAPE — return EXACTLY this structure, no extra keys:

{{
  "category": "<one of CATEGORIES>",
  "subcategory": "<one of SUBCATEGORIES[category]>",
  "silhouette": ["<...>", "<...>"],
  "primary_color": "<one of COLORS_PRIMARY>",
  "secondary_colors": ["<...>"],
  "color_palette": "<one of COLOR_PALETTES>",
  "pattern": "<one of PATTERNS>",
  "primary_material": "<one of MATERIAL_PRIMARY>",
  "material_raw": "<short free text or empty>",
  "material_confidence": "high|medium|low",
  "brand": "<canonical name or empty>",
  "brand_confidence": "high|medium|low",
  "size_label": "<raw label text or null>",
  "condition": "<one of condition keys>",
  "condition_notes": "<1-2 sentences>",
  "era_estimate": "<one of ERA_ESTIMATES or null>",
  "style_tags": ["<...>", "<...>", "<...>"],
  "style_descriptors": ["<...>", "<...>", "<...>"],
  "key_details": ["<...>", "<...>", "<...>"]
}}

Return ONLY the JSON object — no prose, no markdown, no commentary.
"""


# ---------------------------------------------------------------------------
# Response normalization
# ---------------------------------------------------------------------------
def _coerce_to_enum(value: str | None, allowed: list[str], fallback: str = "") -> str:
    if not value:
        return fallback
    v = value.strip()
    if v in allowed:
        return v
    v_lower = v.lower()
    for a in allowed:
        if a.lower() == v_lower:
            return a
    return fallback


def _coerce_list_to_enum(values, allowed: list[str], min_len: int = 0, max_len: int = 99) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for v in values:
        if not isinstance(v, str):
            continue
        coerced = _coerce_to_enum(v, allowed, fallback="")
        if coerced and coerced not in out:
            out.append(coerced)
    return out[:max_len]


def _clean_string_list(values, max_len: int = 10) -> list[str]:
    if not isinstance(values, list):
        return []
    out = []
    for v in values:
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    return out[:max_len]


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from a model response, tolerating ```json``` fences and prose."""
    text = raw.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fence
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AnalyzerError(f"No JSON object in model response: {raw[:200]}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise AnalyzerError(f"Invalid JSON in model response: {e}") from e


def _normalize(parsed: dict) -> dict:
    """Coerce a raw model response into the validated output schema."""
    category = _coerce_to_enum(parsed.get("category"), taxonomy.CATEGORIES, fallback="Other")
    sub_options = taxonomy.SUBCATEGORIES.get(category, ["Other"])
    subcategory = _coerce_to_enum(parsed.get("subcategory"), sub_options, fallback=sub_options[0])

    silhouette = _coerce_list_to_enum(
        parsed.get("silhouette"), taxonomy.SILHOUETTES, max_len=4
    )

    primary_color = _coerce_to_enum(parsed.get("primary_color"), taxonomy.COLORS_PRIMARY, fallback="multi")
    secondary_colors = _coerce_list_to_enum(
        parsed.get("secondary_colors"), taxonomy.COLORS_PRIMARY, max_len=3
    )
    secondary_colors = [c for c in secondary_colors if c != primary_color]

    color_palette = _coerce_to_enum(parsed.get("color_palette"), taxonomy.COLOR_PALETTES, fallback="neutral")
    pattern = _coerce_to_enum(parsed.get("pattern"), taxonomy.PATTERNS, fallback="solid")

    material_raw = (parsed.get("material_raw") or "").strip()
    primary_material_input = (parsed.get("primary_material") or "").strip().lower()
    if primary_material_input in taxonomy.MATERIAL_PRIMARY:
        primary_material = primary_material_input
    else:
        primary_material, _ = taxonomy.normalize_material(material_raw or primary_material_input)

    material_confidence = _coerce_to_enum(
        parsed.get("material_confidence"), ["high", "medium", "low"], fallback="low"
    )

    brand_raw = (parsed.get("brand") or "").strip()
    brand_canonical, brand_known = taxonomy.normalize_brand(brand_raw)
    brand_confidence = _coerce_to_enum(
        parsed.get("brand_confidence"), ["high", "medium", "low"], fallback="low"
    )

    size_label_val = parsed.get("size_label")
    size_label = size_label_val.strip() if isinstance(size_label_val, str) and size_label_val.strip() else None

    condition_keys = [k for k, _ in taxonomy.CONDITION_GRADES]
    condition = _coerce_to_enum(parsed.get("condition"), condition_keys, fallback="good")
    condition_notes = (parsed.get("condition_notes") or "").strip()

    era_val = parsed.get("era_estimate")
    if isinstance(era_val, str) and era_val.strip():
        era_estimate = _coerce_to_enum(era_val, taxonomy.ERA_ESTIMATES, fallback="") or None
    else:
        era_estimate = None

    style_tags = _coerce_list_to_enum(
        parsed.get("style_tags"), taxonomy.STYLE_TAGS_CANONICAL, max_len=5
    )

    style_descriptors = _clean_string_list(parsed.get("style_descriptors"), max_len=7)
    key_details = _clean_string_list(parsed.get("key_details"), max_len=6)

    return {
        "category": category,
        "subcategory": subcategory,
        "silhouette": silhouette,
        "primary_color": primary_color,
        "secondary_colors": secondary_colors,
        "color_palette": color_palette,
        "pattern": pattern,
        "primary_material": primary_material,
        "material_raw": material_raw,
        "material_confidence": material_confidence,
        "brand": brand_canonical,
        "brand_confidence": brand_confidence,
        "brand_known": brand_known,
        "size_label": size_label,
        "condition": condition,
        "condition_notes": condition_notes,
        "era_estimate": era_estimate,
        "style_tags": style_tags,
        "style_descriptors": style_descriptors,
        "key_details": key_details,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def analyze_garment(
    images: list[ImageInput],
    hint: str | None = None,
    model: str | None = None,
) -> dict:
    """Run vision analysis on 1-6 images of a single garment.

    Args:
        images: list of ImageInput, ordered by relevance (front first).
        hint: optional free-text user hint about the item.
        model: override OPENAI_MODEL.

    Returns the normalized output schema (see module docstring) plus
    `_meta` with model/timing/token info.
    """
    if not images:
        raise AnalyzerError("at least one image is required")
    if len(images) > 6:
        raise AnalyzerError("maximum 6 images per request")

    for img in images:
        if img.role and img.role not in taxonomy.IMAGE_ROLES:
            raise AnalyzerError(
                f"invalid role '{img.role}' (allowed: {taxonomy.IMAGE_ROLES})"
            )

    prepared: list[bytes] = []
    for img in images:
        try:
            prepared.append(_prepare_image_for_vision(img.bytes_data))
        except Exception as e:
            raise AnalyzerError(f"could not decode image '{img.filename}': {e}") from e

    chosen_model = model or OPENAI_MODEL
    user_text = _build_user_prompt(images, hint)

    user_content: list[dict] = [{"type": "text", "text": user_text}]
    for jpg in prepared:
        user_content.append(
            {"type": "image_url", "image_url": {"url": _to_data_url(jpg)}}
        )

    started = time.time()
    try:
        resp = get_openai_client().chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception as e:
        raise AnalyzerError(f"vision model call failed: {e}") from e

    raw_text = resp.choices[0].message.content or ""
    parsed = _parse_json_response(raw_text)
    normalized = _normalize(parsed)

    elapsed_ms = int((time.time() - started) * 1000)
    usage = getattr(resp, "usage", None)
    normalized["_meta"] = {
        "model": chosen_model,
        "elapsed_ms": elapsed_ms,
        "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "image_count": len(images),
    }
    return normalized
