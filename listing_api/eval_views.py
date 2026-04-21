"""Browser-based ground-truth labeling for the eval dataset.

Mounted at /listing/eval/ — shows the current dataset and a form to add new
items. Lets you drop photos + type/select truth labels and saves them to
listing_api/eval/items/{id}/ alongside the scraped Grailed items.

Gated behind DEBUG=True or is_staff (don't want random demo users creating
items in production).
"""

from __future__ import annotations

import io
import json
import re
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from PIL import Image

from . import taxonomy

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


ITEMS_DIR = Path(__file__).parent / "eval" / "items"
ROLE_ORDER = ["front", "back", "detail", "label"]


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
def _is_allowed(request) -> bool:
    """Local dev (DEBUG=True) → anyone. Production → is_staff only."""
    if getattr(settings, "DEBUG", False):
        return True
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _next_wardrobe_id() -> str:
    """Generate the next wardrobe-NNN id by scanning existing folders."""
    if not ITEMS_DIR.exists():
        return "wardrobe-001"
    taken = set()
    for child in ITEMS_DIR.iterdir():
        m = re.match(r"wardrobe-(\d+)$", child.name)
        if m:
            taken.add(int(m.group(1)))
    i = 1
    while i in taken:
        i += 1
    return f"wardrobe-{i:03d}"


def _prepare_upload(raw: bytes, max_side: int = 1600, quality: int = 88) -> bytes:
    """Normalize uploaded image (HEIC/PNG/etc) → JPEG, downsized.

    Keeps disk usage reasonable and makes the eval input deterministic.
    """
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


def _split_csv(s: str | None) -> list[str]:
    """Split a comma-separated string into a clean list."""
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def _load_items_summary() -> list[dict]:
    """Scan items/ and return a summary row per item."""
    if not ITEMS_DIR.exists():
        return []
    rows: list[dict] = []
    for child in sorted(ITEMS_DIR.iterdir()):
        if not child.is_dir():
            continue
        meta_p = child / "meta.json"
        if not meta_p.exists():
            continue
        try:
            m = json.loads(meta_p.read_text())
        except Exception:
            continue
        gt = m.get("ground_truth", {})
        images = m.get("images", [])
        front = next((i for i in images if i.get("role") == "front"), None)
        rows.append({
            "item_id": m.get("item_id", child.name),
            "source": m.get("source", ""),
            "category": gt.get("category", ""),
            "subcategory": gt.get("subcategory", ""),
            "brand": gt.get("brand", ""),
            "primary_material": gt.get("primary_material", ""),
            "primary_color": gt.get("primary_color", ""),
            "condition": gt.get("condition", ""),
            "n_images": len(images),
            "n_truth_fields": len(gt),
            "front_file": front["file"] if front else None,
            "folder": child.name,
        })
    return rows


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def label_index(request):
    """Landing page: shows current dataset + form to add a new item."""
    if not _is_allowed(request):
        return HttpResponseForbidden(
            "Eval labeling is only available in dev or to staff users."
        )

    items = _load_items_summary()
    n_total = len(items)
    by_source: dict[str, int] = {}
    for r in items:
        by_source[r["source"] or "unknown"] = by_source.get(r["source"] or "unknown", 0) + 1
    by_category: dict[str, int] = {}
    for r in items:
        by_category[r["category"] or "?"] = by_category.get(r["category"] or "?", 0) + 1

    # Flash messages via query string (no session required)
    success = request.GET.get("saved")
    deleted = request.GET.get("deleted")

    # Subcategory choices flattened (can't do dynamic JS without complicating things)
    all_subcategories = sorted({s for subs in taxonomy.SUBCATEGORIES.values() for s in subs})

    context = {
        "items": items,
        "n_total": n_total,
        "by_source": by_source,
        "by_category": by_category,
        "next_id": _next_wardrobe_id(),
        "success_id": success,
        "deleted_id": deleted,
        "categories": taxonomy.CATEGORIES,
        "subcategories": all_subcategories,
        "subcategories_by_cat": json.dumps(taxonomy.SUBCATEGORIES),
        "materials": taxonomy.MATERIAL_PRIMARY,
        "colors": taxonomy.COLORS_PRIMARY,
        "palettes": taxonomy.COLOR_PALETTES,
        "patterns": taxonomy.PATTERNS,
        "silhouettes": taxonomy.SILHOUETTES,
        "conditions": taxonomy.CONDITION_GRADES,
        "eras": taxonomy.ERA_ESTIMATES,
        "style_tags": taxonomy.STYLE_TAGS_CANONICAL,
        "brands": sorted(taxonomy.BRAND_ALIASES.keys()),
    }
    return render(request, "listing_api/label.html", context)


@csrf_exempt  # simpler for a dev tool; auth gate above still applies
@require_http_methods(["POST"])
def save_label(request):
    """Accept a multipart form submission and write meta.json + photos."""
    if not _is_allowed(request):
        return HttpResponseForbidden("Not allowed.")

    data = request.POST
    files = request.FILES

    # Require at least a front photo + category
    front_file = files.get("front")
    if not front_file:
        return _render_error(request, "A front photo is required.")
    category = (data.get("category") or "").strip()
    if not category:
        return _render_error(request, "Category is required.")

    # Build ground_truth dict from provided fields (skip blanks)
    def put(key: str, value):
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return
        if isinstance(value, list) and not value:
            return
        gt[key] = value

    gt: dict = {}
    put("category", category)
    put("subcategory", (data.get("subcategory") or "").strip() or None)
    put("brand", (data.get("brand") or "").strip() or None)
    put("primary_material", (data.get("primary_material") or "").strip() or None)
    put("primary_color", (data.get("primary_color") or "").strip() or None)
    put("color_palette", (data.get("color_palette") or "").strip() or None)
    put("pattern", (data.get("pattern") or "").strip() or None)
    put("size_label", (data.get("size_label") or "").strip() or None)
    put("condition", (data.get("condition") or "").strip() or None)
    put("era_estimate", (data.get("era_estimate") or "").strip() or None)
    put("secondary_colors", _split_csv(data.get("secondary_colors")))
    put("silhouette", _split_csv(data.get("silhouette")))
    put("style_tags", _split_csv(data.get("style_tags")))

    # Resolve item_id: use provided (trusted if not colliding) or auto
    raw_id = (data.get("item_id") or "").strip()
    if raw_id and re.fullmatch(r"[A-Za-z0-9_-]+", raw_id) and not (ITEMS_DIR / raw_id).exists():
        item_id = raw_id
    else:
        item_id = _next_wardrobe_id()

    folder = ITEMS_DIR / item_id
    folder.mkdir(parents=True, exist_ok=True)

    # Save photos, one per role, converted to JPEG
    images_manifest: list[dict] = []
    for role in ROLE_ORDER:
        f = files.get(role)
        if not f:
            continue
        try:
            raw = f.read()
            jpeg = _prepare_upload(raw)
        except Exception as e:
            return _render_error(request, f"Couldn't process {role} photo: {e}")
        fname = f"{role}.jpg"
        (folder / fname).write_bytes(jpeg)
        images_manifest.append({"file": fname, "role": role})

    if not images_manifest:
        return _render_error(request, "No valid photos uploaded.")

    meta = {
        "item_id": item_id,
        "source": "wardrobe",
        "notes": (data.get("notes") or "").strip(),
        "labeled_at": datetime.now().isoformat(timespec="seconds"),
        "ground_truth": gt,
        "images": images_manifest,
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))

    url = reverse("listing_api:label_index") + f"?saved={item_id}"
    return HttpResponseRedirect(url)


@csrf_exempt
@require_http_methods(["POST"])
def delete_label(request, item_id: str):
    """Delete a single item folder. Dev-only convenience."""
    if not _is_allowed(request):
        return HttpResponseForbidden("Not allowed.")

    # Guard against path traversal
    if not re.fullmatch(r"[A-Za-z0-9_-]+", item_id):
        return HttpResponseForbidden("Invalid id.")

    folder = ITEMS_DIR / item_id
    if folder.exists() and folder.is_dir():
        for p in folder.iterdir():
            p.unlink()
        folder.rmdir()

    url = reverse("listing_api:label_index") + f"?deleted={item_id}"
    return HttpResponseRedirect(url)


def item_photo(request, item_id: str, filename: str):
    """Serve a photo file from items/{item_id}/{filename}. Dev tool only."""
    if not _is_allowed(request):
        return HttpResponseForbidden("Not allowed.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", item_id):
        raise Http404
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename):
        raise Http404
    path = ITEMS_DIR / item_id / filename
    if not path.exists() or not path.is_file():
        raise Http404
    # Infer a sensible content type
    ct = "image/jpeg"
    low = filename.lower()
    if low.endswith(".png"):
        ct = "image/png"
    elif low.endswith(".webp"):
        ct = "image/webp"
    return FileResponse(open(path, "rb"), content_type=ct)


def _render_error(request, msg: str):
    """Re-render the index page with an error banner."""
    items = _load_items_summary()
    all_subcategories = sorted({s for subs in taxonomy.SUBCATEGORIES.values() for s in subs})
    return render(request, "listing_api/label.html", {
        "error": msg,
        "items": items,
        "n_total": len(items),
        "next_id": _next_wardrobe_id(),
        "categories": taxonomy.CATEGORIES,
        "subcategories": all_subcategories,
        "subcategories_by_cat": json.dumps(taxonomy.SUBCATEGORIES),
        "materials": taxonomy.MATERIAL_PRIMARY,
        "colors": taxonomy.COLORS_PRIMARY,
        "palettes": taxonomy.COLOR_PALETTES,
        "patterns": taxonomy.PATTERNS,
        "silhouettes": taxonomy.SILHOUETTES,
        "conditions": taxonomy.CONDITION_GRADES,
        "eras": taxonomy.ERA_ESTIMATES,
        "style_tags": taxonomy.STYLE_TAGS_CANONICAL,
        "brands": sorted(taxonomy.BRAND_ALIASES.keys()),
    })
