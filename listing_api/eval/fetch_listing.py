"""Single-URL listing fetcher for The RealReal and Vestiaire Collective.

Why this exists:
  - Grailed has a public Algolia search; TRR and VC don't, and both sit behind
    Cloudflare with strict bot mitigation.
  - For eval, we don't need bulk — we need ~10 hand-picked items per source
    where the labels are professionally curated (TRR especially).
  - This fetcher accepts EITHER a live URL OR a saved HTML file. If Cloudflare
    blocks our urllib request, you can hit "Save Page As..." in the browser
    and feed us the file. Either way we extract the same data.

Strategy:
  - Both sites are Next.js apps and emit:
      1. <script type="application/ld+json"> Product schema  (universal, stable)
      2. <script id="__NEXT_DATA__"> with the page's full props (richer)
  - We pull JSON-LD first (clean, standardized) and augment from __NEXT_DATA__
    when we can find a product node there.
  - Image URLs in those blobs point at TRR's / VC's CDN — those endpoints
    serve raw images without bot mitigation, so downloads work even when
    the HTML fetch needs the fallback path.

Usage:
  # Live URL (works if Cloudflare doesn't block)
  python -m listing_api.eval.fetch_listing \
      --url "https://www.therealreal.com/products/women/clothing/coats/..."

  # Saved HTML (Cmd+S in your browser, "Web Page, HTML Only")
  python -m listing_api.eval.fetch_listing \
      --html /tmp/saved_page.html --source trr

  # Dry-run: parse and print without writing files
  python -m listing_api.eval.fetch_listing --url "..." --dry-run

  # Skip photos (faster iteration on label parsing)
  python -m listing_api.eval.fetch_listing --url "..." --no-photos

Legal/ethics:
  - Both sites prohibit scraping in their ToS. This tool is intentionally
    bounded: one URL at a time, manually selected, internal eval only.
  - Don't commit downloaded TRR/VC images or meta.json files to a public repo.
    Treat the eval/items/{trr-*,vc-*} folders as local-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import urllib.error
import urllib.request

from .. import taxonomy
from .dataset import ITEMS_DIR


# ---------------------------------------------------------------------------
# Browser-flavored UA + headers (live fetch will fail without these on TRR/VC)
# ---------------------------------------------------------------------------
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",  # avoid gzip; saves us a decompress dependency
    "Cache-Control": "no-cache",
    "Connection": "close",
}


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------
def detect_source(url_or_path: str) -> str | None:
    """Return 'trr', 'vestiaire', or None based on a URL or file path.

    Tolerates bare keywords and spacing variations so saved-HTML filenames
    like ``...The RealReal.html`` resolve correctly without --source.
    """
    s = (url_or_path or "").lower()
    if (
        "therealreal" in s or "the realreal" in s or "real real" in s
        or "_trr" in s or "/trr" in s or s.startswith("trr")
    ):
        return "trr"
    if (
        "vestiairecollective" in s or "vestiaire" in s
        or "_vc" in s or "/vc" in s
    ):
        return "vestiaire"
    return None


def detect_source_from_html(html: str) -> str | None:
    """Last-resort source detection by sniffing the HTML body for site markers."""
    head = html[:8000].lower()  # first 8KB is enough to spot canonical/og:url
    if "therealreal.com" in head or "therealreal" in head:
        return "trr"
    if "vestiairecollective.com" in head or "vestiaire" in head:
        return "vestiaire"
    return None


# ---------------------------------------------------------------------------
# HTML retrieval (URL or file)
# ---------------------------------------------------------------------------
def fetch_html(url: str, timeout: int = 25) -> str:
    """Fetch a page over HTTP. Raises on Cloudflare blocks (403)."""
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    # Pages are utf-8 in practice; be tolerant.
    return raw.decode("utf-8", errors="ignore")


def load_html(path: Path) -> str:
    """Load HTML from a saved file (any encoding tolerated)."""
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# JSON-LD extraction (first pass)
# ---------------------------------------------------------------------------
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)


def extract_jsonld_blocks(html: str) -> list[dict]:
    """Return parsed JSON-LD blocks; tolerate malformed entries."""
    out: list[dict] = []
    for m in _JSONLD_RE.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        if isinstance(data, list):
            out.extend([d for d in data if isinstance(d, dict)])
        elif isinstance(data, dict):
            out.append(data)
    return out


def find_product_jsonld(blocks: list[dict]) -> dict | None:
    """Find the @type=Product node anywhere in JSON-LD output (incl. @graph)."""
    def _matches(node: Any) -> bool:
        if not isinstance(node, dict):
            return False
        t = node.get("@type")
        if t == "Product":
            return True
        if isinstance(t, list) and "Product" in t:
            return True
        return False

    for block in blocks:
        if _matches(block):
            return block
        graph = block.get("@graph")
        if isinstance(graph, list):
            for n in graph:
                if _matches(n):
                    return n
    return None


# ---------------------------------------------------------------------------
# __NEXT_DATA__ extraction (second pass — for fields JSON-LD doesn't expose)
# ---------------------------------------------------------------------------
_NEXT_DATA_RE = re.compile(
    r'<script id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.S,
)


def extract_next_data(html: str) -> dict | None:
    m = _NEXT_DATA_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def walk_for_product_node(data: Any, source: str) -> dict | None:
    """Walk the __NEXT_DATA__ tree looking for a node that smells like a product.

    A 'product node' is a dict that has a brand/designer field AND either
    images/photos or a name/title. Different sites bury this in different
    paths (TRR: pageProps.initialState.products[0]; VC: pageProps.product).
    """
    # TRR fast path — the product is reliably at this exact location
    if source == "trr" and isinstance(data, dict):
        try:
            node = data["props"]["pageProps"]["product"]
            if isinstance(node, dict) and node.get("name"):
                return node
        except (KeyError, TypeError):
            pass

    best: dict | None = None
    best_score = 0

    def is_product(node: dict) -> int:
        score = 0
        keys = set(node.keys())
        if {"designer", "designerName"} & keys: score += 2
        if {"brand"} & keys: score += 2
        if {"name", "title"} & keys: score += 1
        if {"images", "photos", "media"} & keys: score += 1
        if {"condition", "conditionDisplay", "conditionTitle"} & keys: score += 2
        if {"taxonomy", "category", "categories"} & keys: score += 1
        if {"size", "sizeName"} & keys: score += 1
        if {"composition", "material", "materials"} & keys: score += 1
        if {"attributes"} & keys: score += 2  # TRR-style structured attributes
        return score

    def walk(node: Any) -> None:
        nonlocal best, best_score
        if isinstance(node, dict):
            score = is_product(node)
            if score >= 4 and score > best_score:
                best, best_score = node, score
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return best


# ---------------------------------------------------------------------------
# Source-specific normalization
# ---------------------------------------------------------------------------

# Both sites use prose category strings. Map keywords to our taxonomy.
# Order matters — more specific first.
CATEGORY_KEYWORDS: list[tuple[str, str, str | None]] = [
    # (keyword, our category, our subcategory or None)
    ("trench coat",        "Outerwear", "Trench Coat"),
    ("puffer",             "Outerwear", "Puffer"),
    ("parka",              "Outerwear", "Parka"),
    ("bomber",             "Outerwear", "Bomber Jacket"),
    ("denim jacket",       "Outerwear", "Denim Jacket"),
    ("leather jacket",     "Outerwear", "Leather Jacket"),
    ("blazer",             "Outerwear", "Blazer"),
    ("vest",               "Outerwear", "Vest"),
    ("cape",               "Outerwear", "Cape"),
    ("wool coat",          "Outerwear", "Wool Coat"),
    ("coat",               "Outerwear", "Wool Coat"),
    ("jacket",             "Outerwear", "Other Outerwear"),
    ("outerwear",          "Outerwear", None),
    ("cardigan",           "Top", "Cardigan"),
    ("sweater",            "Top", "Sweater"),
    ("knit",               "Top", "Sweater"),
    ("hoodie",             "Top", "Hoodie"),
    ("sweatshirt",         "Top", "Hoodie"),
    ("t-shirt",            "Top", "T-Shirt"),
    ("tee",                "Top", "T-Shirt"),
    ("polo",               "Top", "Polo"),
    ("blouse",             "Top", "Blouse"),
    ("shirt",              "Top", "Shirt"),
    ("top",                "Top", None),
    ("jeans",              "Bottom", "Jeans"),
    ("denim",              "Bottom", "Jeans"),
    ("trouser",            "Bottom", "Trousers"),
    ("pant",               "Bottom", "Trousers"),
    ("short",              "Bottom", "Shorts"),
    ("skirt",              "Bottom", "Skirt"),
    ("dress",              "Dress", None),
    ("gown",               "Dress", None),
    ("jumpsuit",           "Jumpsuit", None),
    ("romper",             "Jumpsuit", None),
    ("sneaker",            "Shoes", "Sneakers"),
    ("boot",               "Shoes", "Boots"),
    ("loafer",             "Shoes", "Loafers"),
    ("pump",               "Shoes", "Heels"),
    ("heel",               "Shoes", "Heels"),
    ("flat",               "Shoes", "Flats"),
    ("mule",               "Shoes", "Mules"),
    ("sandal",             "Shoes", "Sandals"),
    ("shoe",               "Shoes", None),
    ("tote",               "Bag", "Tote"),
    ("crossbody",          "Bag", "Crossbody"),
    ("clutch",             "Bag", "Clutch"),
    ("shoulder bag",       "Bag", "Shoulder Bag"),
    ("handbag",            "Bag", "Top Handle"),
    ("backpack",           "Bag", "Backpack"),
    ("wallet",             "Bag", "Wallet"),
    ("bag",                "Bag", None),
    ("scarf",              "Accessory", "Scarf"),
    ("belt",               "Accessory", "Belt"),
    ("hat",                "Accessory", "Hat"),
    ("sunglass",           "Accessory", "Sunglasses"),
]


def map_category_string(text: str) -> tuple[str | None, str | None]:
    """Best-effort map of a free-text category breadcrumb to (cat, subcat)."""
    if not text:
        return None, None
    low = text.lower()
    for kw, cat, sub in CATEGORY_KEYWORDS:
        if kw in low:
            return cat, sub
    return None, None


# TRR's condition strings are prose ("Excellent", "Pristine", etc.).
TRR_CONDITION_MAP = {
    "pristine":     "new_with_tags",
    "excellent":    "excellent",
    "very good":    "very_good",
    "good":         "good",
    "fair":         "fair",
}

# Vestiaire condition codes vary; keep both numeric and prose forms.
VC_CONDITION_MAP = {
    "never_worn_with_tag":  "new_with_tags",
    "never_worn":           "new_with_tags",
    "very_good_condition":  "excellent",
    "good_condition":       "very_good",
    "fair_condition":       "good",
    "never worn, with tag": "new_with_tags",
    "never worn":           "new_with_tags",
    "very good condition":  "excellent",
    "good condition":       "very_good",
    "fair condition":       "good",
}


def map_condition(raw: str | None, source: str) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower()
    if source == "trr":
        for k, v in TRR_CONDITION_MAP.items():
            if k in key:
                return v
    if source == "vestiaire":
        # Try keyed first, then prose substring
        if key in VC_CONDITION_MAP:
            return VC_CONDITION_MAP[key]
        for k, v in VC_CONDITION_MAP.items():
            if k in key:
                return v
    return None


# Color normalization — pull a primary color word out of free text.
# Heavy on fashion-specific names because TRR/VC use prose like "honey", "ecru".
COLOR_WORDS = {
    # Neutrals
    "black": "black",
    "white": "white", "ivory": "ivory", "ecru": "cream", "cream": "cream",
    "off-white": "white", "off white": "white",
    "beige": "beige", "nude": "beige", "stone": "beige", "sand": "beige",
    "tan": "tan", "camel": "tan", "honey": "tan",
    "brown": "brown", "chocolate": "brown", "espresso": "brown",
    "khaki": "khaki", "olive": "olive",
    "grey": "grey", "gray": "grey", "taupe": "grey",
    "charcoal": "charcoal", "silver": "silver",
    # Blues
    "navy": "navy", "indigo": "navy",
    "blue": "blue", "denim": "blue", "cobalt": "blue", "azure": "blue",
    "teal": "teal", "aqua": "teal", "turquoise": "teal",
    # Greens
    "green": "green", "emerald": "green", "forest": "green",
    "mint": "green", "sage": "green",
    # Yellows
    "yellow": "yellow", "mustard": "yellow", "ochre": "yellow",
    "gold": "gold",
    # Oranges
    "orange": "orange", "coral": "orange", "rust": "orange",
    "terracotta": "orange",
    # Reds
    "red": "red", "burgundy": "burgundy", "wine": "burgundy",
    "maroon": "burgundy",
    # Pinks
    "pink": "pink", "rose": "pink", "blush": "pink", "fuchsia": "pink",
    "salmon": "pink",
    # Purples
    "purple": "purple", "lilac": "purple", "lavender": "purple",
    "violet": "purple", "plum": "purple",
    # Multi
    "multi": "multi", "multicolor": "multi", "multicolour": "multi",
    "print": "multi",
}


def map_color(raw: str | None) -> str | None:
    """Map a free-text color string to one of our COLORS_PRIMARY.

    Prefers concrete colors over palette descriptors ("multi", "print") and
    skips TRR-style palette buckets ("neutrals", "blacks", "warm tones") that
    don't pin down a single primary color.
    """
    if not raw:
        return None
    text = str(raw).lower()

    # TRR sometimes reports the color *bucket* rather than a real color
    # (e.g. "Neutrals", "Warm Tones"). These are unhelpful as ground truth —
    # caller should fall back to title/description.
    PALETTE_BUCKETS = {
        "neutrals", "warm tones", "cool tones", "earth tones", "pastels",
        "brights", "blacks", "whites", "browns", "blues", "greens", "reds",
        "yellows", "purples", "pinks", "greys", "grays", "metallics",
    }
    if text.strip() in PALETTE_BUCKETS:
        return None

    palette_tokens = {"multi", "multicolor", "multicolour", "print"}
    tokens = re.split(r"[\s,/&]+", text)

    # Pass 1: prefer a concrete color (skip palette tokens).
    for token in tokens:
        if token in COLOR_WORDS and token not in palette_tokens:
            return COLOR_WORDS[token]

    # Pass 2: substring search for concrete colors (e.g., "off-white").
    for word, canonical in COLOR_WORDS.items():
        if word in palette_tokens:
            continue
        if word in text:
            return canonical

    # Pass 3: only now fall back to palette tokens (multi/print).
    for token in tokens:
        if token in COLOR_WORDS:
            return COLOR_WORDS[token]

    return None


# Material extraction: same regex as Grailed scraper, tuned for spec strings
MATERIAL_REGEX = re.compile(
    r"\b(?:100%\s+|pure\s+)?(wool|cashmere|cotton|linen|silk|leather|suede|"
    r"nylon|polyester|polyamide|rayon|viscose|denim|velvet|tweed|satin|chiffon|"
    r"lace|fur|shearling|down|merino|alpaca|lambswool|mohair|boucle|fleece|"
    r"gabardine|calfskin|lambskin|tencel|modal|elastane|spandex)\b",
    re.I,
)


# Strings that signal the seller didn't actually identify the fabric — we
# should NOT treat anything in such a description as ground truth.
_MATERIAL_GUESS_PHRASES = (
    "not listed",
    "feels like",
    "appears to be",
    "may be",
    "unknown",
    "unidentified",
    "best guess",
    "presumably",
)


def map_material(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw)
    if any(p in text.lower() for p in _MATERIAL_GUESS_PHRASES):
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


# ---------------------------------------------------------------------------
# Field plucking — small helpers that try multiple paths defensively
# ---------------------------------------------------------------------------
def _first_str(node: Any, *keys: str) -> str | None:
    if not isinstance(node, dict):
        return None
    for k in keys:
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            n = v.get("name") or v.get("value") or v.get("text")
            if isinstance(n, str) and n.strip():
                return n.strip()
    return None


def _images_from_jsonld(prod: dict) -> list[str]:
    img = prod.get("image")
    if isinstance(img, str):
        return [img]
    if isinstance(img, list):
        return [x for x in img if isinstance(x, str)]
    return []


def _attrs_from_trr_node(node: dict) -> dict[str, str]:
    """Pull TRR's `attributes` list ([{label, type, values}]) into a flat dict.

    Returns keys like 'color', 'fabric', 'clothing-size', 'condition' (the
    'type' field), each mapped to the joined values string.
    """
    out: dict[str, str] = {}
    attrs = node.get("attributes")
    if not isinstance(attrs, list):
        return out
    for a in attrs:
        if not isinstance(a, dict):
            continue
        type_key = (a.get("type") or "").lower().strip()
        label_key = (a.get("label") or "").lower().strip()
        values = a.get("values")
        if isinstance(values, list):
            joined = ", ".join(str(v) for v in values if v is not None)
        elif isinstance(values, str):
            joined = values
        else:
            continue
        if not joined:
            continue
        # Index by both type and label so callers can look up either way.
        if type_key:
            out.setdefault(type_key, joined)
        if label_key:
            out.setdefault(label_key, joined)
    return out


def _images_from_node(node: dict) -> list[str]:
    """Pull image URLs from a product-shaped node, handling nested shapes."""
    out: list[str] = []
    for key in ("images", "photos", "media", "pictures"):
        val = node.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.startswith("http"):
                    out.append(item)
                elif isinstance(item, dict):
                    for k in ("url", "src", "fullSize", "large", "imageUrl", "uri"):
                        v = item.get(k)
                        if isinstance(v, str) and v.startswith("http"):
                            out.append(v)
                            break
    # de-duplicate while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


# ---------------------------------------------------------------------------
# Top-level parse
# ---------------------------------------------------------------------------
def parse_listing(html: str, source: str) -> dict:
    """Extract everything we can from a TRR or VC product page HTML.

    Returns: {
        "title": str,
        "brand": str | None,
        "url": str | None,
        "description": str,
        "ground_truth": dict,
        "photos": list[str],
        "raw_signals": dict,    # for debugging/inspection
    }
    """
    parsed: dict = {
        "title": "",
        "brand": None,
        "url": None,
        "description": "",
        "ground_truth": {},
        "photos": [],
        "raw_signals": {},
    }

    blocks = extract_jsonld_blocks(html)
    prod = find_product_jsonld(blocks)
    next_data = extract_next_data(html)
    nxt_node = walk_for_product_node(next_data, source) if next_data else None

    # TRR stores color/fabric/size as a structured attributes[] array on the
    # product node. Extract once so the field-specific blocks below can use it.
    trr_attrs: dict[str, str] = {}
    if source == "trr" and nxt_node:
        trr_attrs = _attrs_from_trr_node(nxt_node)

    raw: dict[str, Any] = {}

    # ---- TITLE ----
    title = (
        _first_str(prod or {}, "name") or
        _first_str(nxt_node or {}, "name", "title", "displayName") or
        ""
    )
    parsed["title"] = title

    # ---- BRAND ----
    brand_raw = None
    if prod and isinstance(prod.get("brand"), dict):
        brand_raw = prod["brand"].get("name")
    elif prod and isinstance(prod.get("brand"), str):
        brand_raw = prod["brand"]
    if not brand_raw and nxt_node:
        brand_raw = (
            _first_str(nxt_node, "designer", "designerName", "brandName") or
            (nxt_node.get("brand") or {}).get("name") if isinstance(nxt_node.get("brand"), dict) else None
        )
        if not brand_raw and isinstance(nxt_node.get("brand"), str):
            brand_raw = nxt_node["brand"]
    if brand_raw:
        canonical, known = taxonomy.normalize_brand(brand_raw)
        parsed["brand"] = canonical if known else brand_raw.strip()
        raw["brand_raw"] = brand_raw

    # ---- DESCRIPTION ----
    desc = (
        (prod or {}).get("description") or
        _first_str(nxt_node or {}, "description", "details", "editorialDescription") or
        ""
    )
    if isinstance(desc, str):
        parsed["description"] = desc.strip()

    # ---- IMAGES ----
    photos = _images_from_jsonld(prod or {})
    if nxt_node:
        photos = photos + [u for u in _images_from_node(nxt_node) if u not in set(photos)]
    parsed["photos"] = photos

    # ---- GROUND TRUTH ----
    gt: dict = {}

    # Category — try JSON-LD category, then breadcrumb-ish fields, then title.
    # For TRR, JSON-LD doesn't carry category and product.category.name is just
    # gender ("Women"); the real signal is the URL path or canonical link.
    category_raw = None
    if isinstance((prod or {}).get("category"), str):
        category_raw = prod["category"]
    if not category_raw and nxt_node:
        category_raw = _first_str(nxt_node, "category", "taxonomy", "categoryName", "type")
        if not category_raw:
            cat_obj = nxt_node.get("category") if isinstance(nxt_node.get("category"), dict) else None
            if cat_obj:
                category_raw = " / ".join(
                    str(v) for k, v in cat_obj.items()
                    if isinstance(v, str)
                )
    if source == "trr":
        # TRR's URL path is gold for category: /products/women/clothing/coats/...
        canonical = re.search(
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
            html,
        )
        url_path = ""
        if canonical:
            url_path = urlparse(canonical.group(1)).path
        if not url_path and parsed.get("url"):
            url_path = urlparse(str(parsed["url"])).path
        if url_path:
            category_raw = (category_raw or "") + " " + url_path.replace("-", " ").replace("/", " ")
    raw["category_raw"] = category_raw
    cat_text_for_match = " ".join(filter(None, [category_raw or "", title]))
    cat, sub = map_category_string(cat_text_for_match)
    if cat:
        gt["category"] = cat
    if sub:
        gt["subcategory"] = sub

    # Color — TRR attributes win, then JSON-LD, then __NEXT_DATA__ direct,
    # then title, then description. We need that many fallbacks because TRR
    # sometimes only stores a generic palette bucket ("Neutrals") which
    # map_color rejects, and the real color word lives in the prose.
    color_raw = (
        trr_attrs.get("color") or
        (prod or {}).get("color") or
        _first_str(nxt_node or {}, "color", "colorName")
    )
    raw["color_raw"] = color_raw
    color = (
        map_color(color_raw) or
        map_color(title) or
        map_color(parsed["description"][:300] if parsed["description"] else None)
    )
    if color:
        gt["primary_color"] = color

    # Material — TRR fabric attribute first, then JSON-LD, then __NEXT_DATA__,
    # then description. We feed each candidate through MATERIAL_REGEX.
    mat_sources: list[str] = []
    if trr_attrs.get("fabric"):
        mat_sources.append(trr_attrs["fabric"])
    for src in (
        (prod or {}).get("material"),
        _first_str(nxt_node or {}, "material", "materials", "composition", "fabric"),
        parsed["description"],
    ):
        if isinstance(src, str):
            mat_sources.append(src)
        elif isinstance(src, list):
            mat_sources.extend([s for s in src if isinstance(s, str)])
    raw["material_raw"] = next(iter(mat_sources), None)
    for src in mat_sources:
        m = map_material(src)
        if m:
            gt["primary_material"] = m
            break

    # Condition — TRR exposes it as a clean prose grade on product.condition.
    # JSON-LD's offers.itemCondition is just a schema.org URL on TRR (useless).
    condition_raw = None
    if source == "trr" and nxt_node:
        cval = nxt_node.get("condition")
        if isinstance(cval, str) and cval.strip():
            condition_raw = cval.strip()
    if not condition_raw and isinstance((prod or {}).get("offers"), dict):
        ic = (prod["offers"] or {}).get("itemCondition")
        # Skip schema.org URLs — they don't carry a grade
        if isinstance(ic, str) and not ic.startswith("http"):
            condition_raw = ic
    if not condition_raw and nxt_node:
        condition_raw = _first_str(nxt_node, "condition", "conditionDisplay", "conditionTitle", "conditionName")
    raw["condition_raw"] = condition_raw
    cond = map_condition(condition_raw, source)
    if cond:
        gt["condition"] = cond

    # Size — TRR puts clothing-size in attributes; VC uses direct fields
    size_raw = (
        trr_attrs.get("clothing-size") or
        trr_attrs.get("shoe-size") or
        trr_attrs.get("size") or
        (prod or {}).get("size") or
        _first_str(nxt_node or {}, "size", "sizeName", "sizeLabel")
    )
    raw["size_raw"] = size_raw
    if isinstance(size_raw, str) and size_raw.strip():
        gt["size_label"] = size_raw.strip()

    # Brand into ground truth (if non-empty)
    if parsed["brand"]:
        gt["brand"] = parsed["brand"]

    # Source URL — pull from JSON-LD if present
    parsed["url"] = (prod or {}).get("url") or (prod or {}).get("@id")

    parsed["ground_truth"] = gt
    parsed["raw_signals"] = raw
    return parsed


# ---------------------------------------------------------------------------
# Photo download
# ---------------------------------------------------------------------------
def download_photos(urls: list[str], out_dir: Path, max_n: int = 5) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    role_order = ["front", "back", "detail", "detail", "label"]
    saved: list[dict] = []
    for i, url in enumerate(urls[:max_n]):
        ext = ".jpg"
        path_only = urlparse(url).path.lower()
        if path_only.endswith((".png", ".webp", ".jpeg")):
            ext = "." + path_only.rsplit(".", 1)[-1]
        role = role_order[i] if i < len(role_order) else "detail"
        # Disambiguate when the same role repeats
        existing = sum(1 for s in saved if s["role"] == role)
        suffix = f"_{existing}" if existing else ""
        filename = f"{role}{suffix}{ext}"
        try:
            req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
        except Exception as e:
            print(f"  photo {i} ({url[:60]}...) failed: {e}")
            continue
        (out_dir / filename).write_bytes(data)
        saved.append({"file": filename, "role": role})
    return saved


# ---------------------------------------------------------------------------
# Item id allocation
# ---------------------------------------------------------------------------
def next_id_for_source(source: str, items_root: Path) -> str:
    """Return the next available {source}-NNN id."""
    prefix = "trr" if source == "trr" else "vc"
    taken: set[int] = set()
    if items_root.exists():
        for child in items_root.iterdir():
            m = re.match(rf"{prefix}-(\d+)$", child.name)
            if m:
                taken.add(int(m.group(1)))
    i = 1
    while i in taken:
        i += 1
    return f"{prefix}-{i:03d}"


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def print_parsed_summary(parsed: dict) -> None:
    gt = parsed["ground_truth"]
    raw = parsed["raw_signals"]
    print(f"  title       : {parsed['title'][:80]}")
    print(f"  brand       : {parsed['brand'] or '—'} (raw: {raw.get('brand_raw') or '—'})")
    print(f"  category    : {gt.get('category') or '—'} / {gt.get('subcategory') or '—'} (raw: {raw.get('category_raw') or '—'})")
    print(f"  color       : {gt.get('primary_color') or '—'} (raw: {raw.get('color_raw') or '—'})")
    print(f"  material    : {gt.get('primary_material') or '—'} (raw: {(raw.get('material_raw') or '')[:60]})")
    print(f"  condition   : {gt.get('condition') or '—'} (raw: {raw.get('condition_raw') or '—'})")
    print(f"  size        : {gt.get('size_label') or '—'}")
    print(f"  photos      : {len(parsed['photos'])} found")
    print(f"  truth fields: {len(gt)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Live product URL on TRR or Vestiaire")
    src.add_argument("--html", help="Path to a saved HTML file (browser 'Save Page As')")
    ap.add_argument("--source", choices=("trr", "vestiaire", "auto"), default="auto",
                    help="Override source detection (default: auto from URL)")
    ap.add_argument("--id", help="Override item folder name (default: auto-incremented)")
    ap.add_argument("--out-root", default=str(ITEMS_DIR),
                    help=f"Output items root (default: {ITEMS_DIR})")
    ap.add_argument("--max-photos", type=int, default=5)
    ap.add_argument("--no-photos", action="store_true", help="Don't download images")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and print, but don't write any files")
    ap.add_argument("--print-raw", action="store_true",
                    help="Also print the raw signals from JSON-LD / __NEXT_DATA__")
    args = ap.parse_args()

    # 1. Resolve source from the path/URL if we can; otherwise we'll sniff the HTML body
    source: str | None = None
    if args.source != "auto":
        source = args.source
    else:
        source = detect_source(args.url or args.html or "")

    # 2. HTML retrieval (and last-resort source detection if needed)
    if args.url:
        print(f"[fetch] GET {args.url}")
        try:
            html = fetch_html(args.url)
        except urllib.error.HTTPError as e:
            print(f"[fetch] HTTP {e.code} — likely Cloudflare. Save the page in your browser")
            print(f"        (Cmd+S → 'Web Page, HTML Only') and re-run with --html <path>.")
            sys.exit(1)
        except Exception as e:
            print(f"[fetch] live fetch failed: {e}")
            sys.exit(1)
        url_for_meta = args.url
    else:
        path = Path(args.html).expanduser()
        if not path.exists():
            print(f"[fetch] HTML file not found: {path}")
            sys.exit(2)
        print(f"[fetch] reading {path}")
        html = load_html(path)
        url_for_meta = None

    if not source:
        source = detect_source_from_html(html)
    if not source:
        print("ERROR: couldn't detect source from URL/path or HTML body.")
        print("       Pass --source trr or --source vestiaire explicitly.")
        sys.exit(2)
    print(f"[fetch] source = {source}")

    print(f"[fetch] HTML size: {len(html):,} chars")

    # 3. Parse
    parsed = parse_listing(html, source)
    if url_for_meta and not parsed["url"]:
        parsed["url"] = url_for_meta

    print(f"\n[fetch] Parsed:")
    print_parsed_summary(parsed)
    if args.print_raw:
        print("\n[fetch] raw signals:")
        for k, v in parsed["raw_signals"].items():
            print(f"  {k}: {v}")

    # 4. Sanity checks
    if not parsed["ground_truth"].get("category"):
        print("\n[fetch] WARNING: couldn't infer category. Item still saved but you may want to edit meta.json.")
    if not parsed["photos"]:
        print("\n[fetch] WARNING: no photos found in JSON-LD or __NEXT_DATA__.")

    if args.dry_run:
        print("\n[fetch] dry-run, exiting.")
        return

    # 5. Write item
    items_root = Path(args.out_root)
    items_root.mkdir(parents=True, exist_ok=True)
    item_id = args.id or next_id_for_source(source, items_root)
    folder = items_root / item_id
    folder.mkdir(parents=True, exist_ok=True)

    saved_imgs: list[dict] = []
    if not args.no_photos and parsed["photos"]:
        print(f"\n[fetch] downloading up to {args.max_photos} photos → {folder}/")
        saved_imgs = download_photos(parsed["photos"], folder, max_n=args.max_photos)
        print(f"[fetch] saved {len(saved_imgs)} photos")

    notes_by_source = {
        "trr":       "Auto-imported from The RealReal; truth labels are professional human curation.",
        "vestiaire": "Auto-imported from Vestiaire Collective; truth labels are platform curation.",
    }

    meta = {
        "item_id": item_id,
        "source": source,
        "source_url": parsed.get("url") or url_for_meta or "",
        "title": parsed["title"],
        "designer_names": parsed["brand"] or "",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "notes": notes_by_source.get(source, ""),
        "ground_truth": parsed["ground_truth"],
        "images": saved_imgs,
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2))

    print(f"\n[fetch] ✓ wrote {folder}/meta.json")
    print(f"[fetch] item_id = {item_id}")
    print(f"[fetch] truth fields: {sorted(parsed['ground_truth'].keys())}")


if __name__ == "__main__":
    main()
