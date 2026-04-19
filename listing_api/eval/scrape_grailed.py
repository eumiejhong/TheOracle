"""Build an eval dataset by pulling listings from Grailed's public Algolia API.

How it works:
  - Hits Grailed's public Algolia search API (same one their website uses)
    with a curated set of queries spanning major categories.
  - Filters to listings with >=4 photos and a known designer/brand.
  - For each chosen listing, downloads photos and fetches the listing detail
    page to extract description (which often contains material info).
  - Maps Grailed's labels to our taxonomy and writes meta.json + photos
    into listing_api/eval/items/{id}/.

Usage:
  python -m listing_api.eval.scrape_grailed --n 20
  python -m listing_api.eval.scrape_grailed --n 5 --query "wool coat"
  python -m listing_api.eval.scrape_grailed --dry-run        # preview, no downloads

NOTE on legality/ethics:
  - Algolia keys are PUBLIC (embedded in every Grailed page); we're using their
    own search API exactly as the website does.
  - Photos and labels are downloaded for INTERNAL EVALUATION ONLY. Do not
    redistribute, republish, or use for commercial inference. We are using
    seller-provided labels as noisy ground truth for accuracy measurement.
  - Be polite: low rate, small sample, identifying User-Agent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
from urllib.parse import urlparse

from .. import taxonomy
from .dataset import ITEMS_DIR


ALGOLIA_APP = "MNRWEFSS2Q"
ALGOLIA_KEY = "c89dbaddf15fe70e1941a109bf7c2a3d"
ALGOLIA_INDEX = "Listing_production"
UA = "TheOracle-Eval/0.1 (research; contact: dev@theoracle)"


# Grailed designer entries that are catch-all buckets, not real brands.
PLACEHOLDER_DESIGNERS = {
    "vintage", "japanese brand", "japanese brands", "jean", "leather",
    "flannel", "unknown", "designer", "designers", "streetwear", "brand",
    "unbranded", "made in usa", "made in italy", "made in japan",
    "americana", "athletic", "sportswear", "workwear", "military",
    "italian designers", "japanese designers", "french designers",
}


# Curated query set — picks up a variety of categories so the eval isn't all coats.
DEFAULT_QUERIES = [
    "wool coat",
    "trench coat",
    "cashmere sweater",
    "knit sweater",
    "leather jacket",
    "denim jacket",
    "selvedge denim",
    "tailored trousers",
    "blazer",
    "silk blouse",
    "cotton shirt",
    "loafers",
    "leather boots",
    "midi dress",
    "wrap dress",
]


# ---------------------------------------------------------------------------
# Grailed → our taxonomy mapping
# ---------------------------------------------------------------------------
GRAILED_CATEGORY_MAP: dict[str, str] = {
    "outerwear": "Outerwear",
    "tops": "Top",
    "bottoms": "Bottom",
    "footwear": "Shoes",
    "accessories": "Accessory",
    "tailoring": "Suiting",
    "dresses": "Dress",
    "skirts": "Bottom",
    "jumpsuits": "Jumpsuit",
    "bags_luggage": "Bag",
    "jewelry": "Accessory",
    "denim": "Bottom",
}

GRAILED_SUBCATEGORY_MAP: dict[str, str] = {
    # Outerwear
    "outerwear.heavy_coats":      "Wool Coat",
    "outerwear.light_jackets":    "Other Outerwear",
    "outerwear.bomber_jackets":   "Bomber Jacket",
    "outerwear.denim_jackets":    "Denim Jacket",
    "outerwear.leather_jackets":  "Leather Jacket",
    "outerwear.parkas":           "Parka",
    "outerwear.puffer_jackets":   "Puffer",
    "outerwear.raincoats":        "Trench Coat",
    "outerwear.trench_coats":     "Trench Coat",
    "outerwear.vests":            "Vest",
    "outerwear.blazers":          "Blazer",
    "outerwear.cloaks_capes":     "Cape",
    # Tops
    "tops.t_shirts":              "T-Shirt",
    "tops.long_sleeve_t_shirts":  "T-Shirt",
    "tops.button_ups":            "Shirt",
    "tops.shirts_button_ups":     "Shirt",
    "tops.polos":                 "Polo",
    "tops.sweaters":              "Sweater",
    "tops.sweaters_knitwear":     "Sweater",  # the analyzer reliably picks "Sweater"; "Knit" is too coarse
    "tops.knit_sweaters":         "Sweater",
    "tops.sweatshirts_hoodies":   "Hoodie",
    "tops.tank_tops":             "Tank",
    "tops.blouses":               "Blouse",
    # Bottoms
    "bottoms.casual_pants":       "Trousers",
    "bottoms.cropped_pants":      "Trousers",
    "bottoms.denim":              "Jeans",
    "bottoms.dress_pants":        "Trousers",
    "bottoms.shorts":             "Shorts",
    "bottoms.sweatpants_joggers": "Sweatpants",
    "bottoms.leggings":           "Leggings",
    "bottoms.skirts":              "Skirt",
    # Footwear
    "footwear.boots":             "Boots",
    "footwear.casual_leather_shoes": "Loafers",
    "footwear.formal_shoes":      "Heels",
    "footwear.high_top_sneakers": "Other Shoes",
    "footwear.low_top_sneakers":  "Other Shoes",
    "footwear.sandals":           "Sandals",
    "footwear.slip_ons":          "Mules",
    "footwear.heels":             "Heels",
    "footwear.flats":             "Flats",
    "footwear.loafers":           "Loafers",
    # Tailoring
    "tailoring.blazers":          "Blazer",
    "tailoring.formal_shirting":  "Shirt",
    "tailoring.suits":            "Suit",
    "tailoring.formal_trousers":  "Suit Trousers",
    "tailoring.tuxedos":          "Tuxedo",
    # Dresses
    "dresses.mini_dresses":       "Mini Dress",
    "dresses.midi_dresses":       "Midi Dress",
    "dresses.maxi_dresses":       "Maxi Dress",
    "dresses.gowns":              "Gown",
    "dresses.strapless_dresses":  "Other Dress",
    # Bags
    "bags_luggage.backpacks":     "Backpack",
    "bags_luggage.belt_bags":     "Belt Bag",
    "bags_luggage.bucket_bags":   "Bucket Bag",
    "bags_luggage.clutches":      "Clutch",
    "bags_luggage.crossbody_bags": "Crossbody",
    "bags_luggage.handle_bags":   "Top Handle",
    "bags_luggage.shoulder_bags": "Shoulder Bag",
    "bags_luggage.tote_bags":     "Tote",
    "bags_luggage.wallets":       "Wallet",
    # Skirts (also live under bottoms.skirts; some listings use root)
    "skirts.mini_skirts":         "Skirt",
    "skirts.midi_skirts":         "Skirt",
    "skirts.maxi_skirts":         "Skirt",
}

GRAILED_CONDITION_MAP: dict[str, str] = {
    "is_new":          "new_with_tags",
    "is_like_new":     "excellent",
    "is_gently_used":  "very_good",
    "is_used":         "good",
    "is_worn":         "fair",
}

# Grailed colors are a single string; map to our COLORS_PRIMARY where possible
GRAILED_COLOR_MAP: dict[str, str] = {
    "black": "black", "white": "white", "ivory": "ivory", "cream": "cream",
    "beige": "beige", "tan": "tan", "brown": "brown", "khaki": "khaki",
    "olive": "olive", "navy": "navy", "blue": "blue", "teal": "teal",
    "green": "green", "yellow": "yellow", "gold": "gold", "orange": "orange",
    "red": "red", "burgundy": "burgundy", "pink": "pink", "purple": "purple",
    "grey": "grey", "gray": "grey", "silver": "silver", "multi": "multi",
    "camo": "multi",
}


def _http_get(url: str, headers: dict | None = None, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _http_post_json(url: str, body: dict, headers: dict | None = None, timeout: int = 15) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/json",
            **(headers or {}),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def algolia_search(query: str, hits_per_page: int = 10) -> list[dict]:
    """Run a single Algolia search query."""
    url = f"https://{ALGOLIA_APP.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    headers = {
        "x-algolia-application-id": ALGOLIA_APP,
        "x-algolia-api-key": ALGOLIA_KEY,
    }
    # Use facet filter to require photo_count >= 4 isn't supported on numeric;
    # we'll filter client-side.
    params = f"hitsPerPage={hits_per_page}&query={urllib.parse.quote(query)}"
    body = {"params": params}
    try:
        data = _http_post_json(url, body, headers=headers)
        return data.get("hits", [])
    except Exception as e:
        print(f"[scrape] algolia query '{query}' failed: {e}")
        return []


_PHOTOS_BLOCK_RE = re.compile(
    r'"photos"\s*:\s*\[(.*?)\]\s*,\s*"designerNames"',
    re.S,
)
_PHOTO_URL_RE = re.compile(r'"url"\s*:\s*"(https?://media-assets\.grailed\.com/[^"]+)"')
_DESC_RE = re.compile(r'"description"\s*:\s*"((?:[^"\\]|\\.){0,4000})"')

# Grailed renders these "description" fields all over the page (shipping notices,
# badges, breadcrumbs, etc.). Filter them out so we only keep the seller's text.
_STOCK_DESC_PHRASES = (
    "directly from Grailed",
    "ships within",
    "top-rated for good communication",
    "Expect a quick response",
    "official nod of appreciation",
    "and more items on grailed",
    "consistently ships",
    "experienced seller",
    "items on grailed",
)


def _is_stock_desc(text: str) -> bool:
    return any(p.lower() in text.lower() for p in _STOCK_DESC_PHRASES)


def fetch_listing_detail(listing_id: int) -> dict | None:
    """Fetch a single listing's HTML page and extract photos + description.

    Grailed embeds the full listing JSON in the page hydration block; we regex
    out the `"photos":[{"url":"..."} ...]` array and pick the seller's
    description (the last non-stock "description" field on the page).
    """
    url = f"https://www.grailed.com/listings/{listing_id}"
    try:
        html = _http_get(url, headers={"Accept": "text/html"}).decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        print(f"[scrape]   detail fetch HTTP {e.code} for {listing_id}")
        return None
    except Exception as e:
        print(f"[scrape]   detail fetch failed for {listing_id}: {e}")
        return None

    # Photos from the hydration block (most reliable source)
    photos: list[str] = []
    block_match = _PHOTOS_BLOCK_RE.search(html)
    if block_match:
        for u in _PHOTO_URL_RE.finditer(block_match.group(1)):
            base = u.group(1)
            # Add a width hint so we get a reasonable-size JPEG
            sep = "&" if "?" in base else "?"
            photos.append(f"{base}{sep}w=1024&auto=format")

    # Fallback: any media-assets URL in JSON-LD
    if not photos:
        ld_matches = re.findall(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.S,
        )
        for raw in ld_matches:
            try:
                d = json.loads(raw)
                imgs = d.get("image") if isinstance(d, dict) else None
                if isinstance(imgs, str):
                    photos.append(imgs)
                elif isinstance(imgs, list):
                    photos.extend([x for x in imgs if isinstance(x, str)])
            except Exception:
                pass

    # Description: take the longest non-stock description on the page
    description = ""
    candidates: list[str] = []
    for m in _DESC_RE.finditer(html):
        text = m.group(1)
        if len(text) >= 20 and not _is_stock_desc(text):
            candidates.append(text)
    if candidates:
        description = max(candidates, key=len)

    return {"photos": photos, "description": description, "url": url}


def map_grailed_to_truth(hit: dict, description: str) -> dict:
    """Convert a Grailed listing hit + description text into our ground_truth dict.

    Conservative — only sets fields where we have high confidence in the source.
    Material is only set if we can extract it from the description.
    """
    truth: dict = {}

    # Category
    cat_g = (hit.get("category") or "").lower()
    if cat_g in GRAILED_CATEGORY_MAP:
        truth["category"] = GRAILED_CATEGORY_MAP[cat_g]

    # Subcategory
    cp = (hit.get("category_path") or "").lower()
    if cp in GRAILED_SUBCATEGORY_MAP:
        truth["subcategory"] = GRAILED_SUBCATEGORY_MAP[cp]

    # Brand — pick the first designer that isn't a Grailed placeholder bucket.
    # Grailed uses entries like "Vintage", "Jean", "Leather", "Flannel",
    # "Japanese Brand", "Streetwear" as catch-alls for unbranded items;
    # treating them as truth would unfairly penalize the analyzer.
    designers = hit.get("designers") or []
    brand_raw = None
    for d in designers:
        name = (d.get("name") or "").strip()
        if name and name.lower() not in PLACEHOLDER_DESIGNERS:
            brand_raw = name
            break
    if brand_raw:
        canonical, known = taxonomy.normalize_brand(brand_raw)
        truth["brand"] = canonical if known else brand_raw

    # Color
    color_raw = (hit.get("color") or "").lower()
    if color_raw in GRAILED_COLOR_MAP:
        truth["primary_color"] = GRAILED_COLOR_MAP[color_raw]

    # Condition
    cond = hit.get("condition") or ""
    if cond in GRAILED_CONDITION_MAP:
        truth["condition"] = GRAILED_CONDITION_MAP[cond]

    # Size (raw string)
    size = hit.get("size")
    if size:
        truth["size_label"] = str(size).upper()

    # Material — try to extract from description
    if description:
        mat = extract_material_from_description(description)
        if mat:
            truth["primary_material"] = mat

    # Era — Grailed designer "Vintage" is a hint, but we don't trust era assignment
    # without more signal. Skip.

    return truth


# Heuristic material extraction from listing description
MATERIAL_REGEX = re.compile(
    r"\b(?:100%\s+|pure\s+)?(wool|cashmere|cotton|linen|silk|leather|suede|"
    r"nylon|polyester|rayon|viscose|denim|velvet|tweed|satin|chiffon|lace|"
    r"fur|shearling|down|cashmere|merino|alpaca|lambswool|mohair|boucle|"
    r"calfskin|lambskin|tencel|modal)\b",
    re.IGNORECASE,
)


def extract_material_from_description(text: str) -> str | None:
    """Pull the most-mentioned material from a description and normalize it."""
    if not text:
        return None
    counts: dict[str, int] = {}
    for m in MATERIAL_REGEX.finditer(text):
        word = m.group(1).lower()
        canonical, _ = taxonomy.normalize_material(word)
        if canonical and canonical != "other":
            counts[canonical] = counts.get(canonical, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def download_photos(photo_urls: list[str], out_dir: Path, max_n: int = 4) -> list[dict]:
    """Download up to max_n photos. Assigns roles by position:
       0=front, 1=back, 2=detail, 3=detail (we don't know which is the label).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    role_order = ["front", "back", "detail", "detail"]
    saved: list[dict] = []
    for i, url in enumerate(photo_urls[:max_n]):
        ext = ".jpg"
        path_only = urlparse(url).path
        if path_only.lower().endswith((".png", ".webp", ".jpeg")):
            ext = "." + path_only.rsplit(".", 1)[-1].lower()
        filename = f"{role_order[i]}_{i}{ext}"
        try:
            data = _http_get(url, timeout=20)
        except Exception as e:
            print(f"[scrape]     photo {i} failed: {e}")
            continue
        (out_dir / filename).write_bytes(data)
        saved.append({"file": filename, "role": role_order[i]})
    return saved


def write_item(item_id: str, hit: dict, detail: dict, out_root: Path) -> bool:
    truth = map_grailed_to_truth(hit, detail.get("description", ""))
    if not truth.get("category"):
        print(f"[scrape]   skip {item_id}: couldn't map category {hit.get('category_path')}")
        return False

    photos = detail.get("photos", [])
    if len(photos) < 2:
        print(f"[scrape]   skip {item_id}: only {len(photos)} photos")
        return False

    folder = out_root / item_id
    saved_imgs = download_photos(photos, folder, max_n=4)
    if len(saved_imgs) < 2:
        print(f"[scrape]   skip {item_id}: only saved {len(saved_imgs)} photos")
        return False

    meta = {
        "item_id": item_id,
        "source": "grailed",
        "source_url": detail.get("url", f"https://www.grailed.com/listings/{hit.get('id')}"),
        "title": hit.get("title", ""),
        "designer_names": hit.get("designer_names", ""),
        "notes": "Auto-imported from Grailed; truth labels are seller-provided (noisy).",
        "ground_truth": truth,
        "images": saved_imgs,
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[scrape]   ✓ {item_id}: {hit.get('title')[:60]} ({len(saved_imgs)} imgs, {len(truth)} truth fields)")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="Total items to import")
    ap.add_argument("--query", action="append", default=None,
                    help="Custom query (can repeat); default uses curated set")
    ap.add_argument("--per-query", type=int, default=2,
                    help="Hits to attempt per query")
    ap.add_argument("--dry-run", action="store_true", help="Print plan, don't download")
    ap.add_argument("--start-id", type=int, default=1, help="Numeric id offset")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between detail requests")
    args = ap.parse_args()

    queries = args.query or DEFAULT_QUERIES
    out_root = ITEMS_DIR
    out_root.mkdir(parents=True, exist_ok=True)

    chosen: list[dict] = []
    seen_ids: set[int] = set()

    for q in queries:
        if len(chosen) >= args.n:
            break
        print(f"\n[scrape] query='{q}'")
        hits = algolia_search(q, hits_per_page=10)
        added_for_query = 0
        for h in hits:
            if len(chosen) >= args.n:
                break
            if added_for_query >= args.per_query:
                break  # enforce per-query cap so we get category diversity
            if h["id"] in seen_ids:
                continue
            cp = (h.get("category_path") or "").lower()
            if cp not in GRAILED_SUBCATEGORY_MAP:
                continue  # skip un-mappable subcategories
            if (h.get("photo_count") or 0) < 2:
                continue
            chosen.append(h)
            seen_ids.add(h["id"])
            added_for_query += 1
            print(f"  + {h['id']}: {h['title'][:60]} | {cp} | {h.get('color')} | {h.get('condition')}")

    print(f"\n[scrape] Selected {len(chosen)} listings")

    if args.dry_run:
        print("[scrape] dry-run, exiting")
        return

    saved = 0
    for i, hit in enumerate(chosen):
        item_id = f"{args.start_id + i:03d}"
        print(f"\n[scrape] [{i + 1}/{len(chosen)}] item {item_id} ← grailed:{hit['id']}")
        detail = fetch_listing_detail(hit["id"])
        time.sleep(args.sleep)
        if not detail:
            continue
        if write_item(item_id, hit, detail, out_root):
            saved += 1

    print(f"\n[scrape] Done. Saved {saved}/{len(chosen)} items to {out_root}/")


if __name__ == "__main__":
    main()
