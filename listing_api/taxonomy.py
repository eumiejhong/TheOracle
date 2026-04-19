"""Controlled vocabulary for listing analysis.

The analyzer prompt injects these enum lists so GPT must pick from them
(rather than free-generating synonyms). This keeps structured fields clean and
filterable for downstream search/faceting.

Edit this file to extend or refine the taxonomy. No code changes needed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Top-level garment category (broad)
# ---------------------------------------------------------------------------
CATEGORIES: list[str] = [
    "Outerwear",
    "Top",
    "Bottom",
    "Dress",
    "Suiting",
    "Jumpsuit",
    "Shoes",
    "Bag",
    "Accessory",
    "Other",
]


# ---------------------------------------------------------------------------
# Subcategory (scoped per category)
# ---------------------------------------------------------------------------
SUBCATEGORIES: dict[str, list[str]] = {
    "Outerwear": [
        "Trench Coat", "Wool Coat", "Cashmere Coat", "Down Jacket", "Puffer",
        "Parka", "Blazer", "Leather Jacket", "Denim Jacket", "Bomber Jacket",
        "Cape", "Cardigan Coat", "Vest", "Other Outerwear",
    ],
    "Top": [
        "Shirt", "Blouse", "T-Shirt", "Tank", "Sweater", "Knit", "Cardigan",
        "Hoodie", "Sweatshirt", "Polo", "Camisole", "Bodysuit", "Other Top",
    ],
    "Bottom": [
        "Trousers", "Jeans", "Shorts", "Leggings", "Skirt", "Culottes",
        "Sweatpants", "Other Bottom",
    ],
    "Dress": [
        "Mini Dress", "Midi Dress", "Maxi Dress", "Slip Dress", "Shirt Dress",
        "Wrap Dress", "Knit Dress", "Cocktail Dress", "Gown", "Other Dress",
    ],
    "Suiting": [
        "Suit", "Suit Jacket", "Suit Trousers", "Suit Skirt", "Tuxedo",
        "Other Suiting",
    ],
    "Jumpsuit": [
        "Jumpsuit", "Romper", "Overalls",
    ],
    "Shoes": [
        "Loafers", "Heels", "Pumps", "Boots", "Ankle Boots", "Knee Boots",
        "Mules", "Sandals", "Flats", "Ballet Flats", "Espadrilles",
        "Other Shoes",
    ],
    "Bag": [
        "Handbag", "Tote", "Shoulder Bag", "Crossbody", "Clutch", "Backpack",
        "Belt Bag", "Bucket Bag", "Top Handle", "Wallet", "Other Bag",
    ],
    "Accessory": [
        "Scarf", "Belt", "Hat", "Sunglasses", "Jewelry", "Necklace", "Earrings",
        "Bracelet", "Ring", "Watch", "Gloves", "Hair Accessory", "Other Accessory",
    ],
    "Other": ["Other"],
}


# ---------------------------------------------------------------------------
# Silhouette (model picks 1-4)
# ---------------------------------------------------------------------------
SILHOUETTES: list[str] = [
    # Volume
    "oversized", "boxy", "relaxed", "slim", "fitted", "tailored", "structured",
    "draped", "fluid",
    # Cut
    "A-line", "straight", "bias-cut", "wrap", "shift", "sheath", "empire-waist",
    "drop-waist", "high-waist", "low-rise",
    # Length
    "cropped", "regular-length", "long", "midi", "maxi", "mini", "knee-length",
    "ankle-length", "floor-length",
    # Construction
    "double-breasted", "single-breasted", "open-front", "belted",
    "pleated", "ruched", "asymmetric",
    # Sleeve
    "sleeveless", "short-sleeve", "long-sleeve", "puff-sleeve", "balloon-sleeve",
    # Neckline
    "v-neck", "crew-neck", "scoop-neck", "boat-neck", "halter", "off-shoulder",
    "turtleneck", "mock-neck", "cowl-neck",
]


# ---------------------------------------------------------------------------
# Colors (primary picks ONE; secondary picks 0-3)
# ---------------------------------------------------------------------------
COLORS_PRIMARY: list[str] = [
    "black", "white", "ivory", "cream", "beige", "camel", "tan", "brown",
    "chocolate", "khaki", "olive", "navy", "blue", "sky-blue", "teal",
    "green", "forest-green", "mint", "sage", "yellow", "mustard", "gold",
    "orange", "rust", "red", "burgundy", "wine", "pink", "blush", "fuchsia",
    "purple", "lavender", "grey", "charcoal", "silver", "multi",
]


# ---------------------------------------------------------------------------
# Color palette (mood)
# ---------------------------------------------------------------------------
COLOR_PALETTES: list[str] = [
    "neutral", "warm", "cool", "earth", "jewel", "pastel", "monochrome", "bright",
]


# ---------------------------------------------------------------------------
# Pattern (one)
# ---------------------------------------------------------------------------
PATTERNS: list[str] = [
    "solid", "stripe", "pinstripe", "check", "plaid", "houndstooth",
    "windowpane", "polka-dot", "floral", "abstract", "geometric", "paisley",
    "animal-print", "leopard", "snake", "zebra", "tie-dye", "logo-print",
    "color-block", "tweed", "herringbone", "embroidered", "lace",
    "sequined", "beaded", "other",
]


# ---------------------------------------------------------------------------
# Condition (5-tier industry standard)
# ---------------------------------------------------------------------------
CONDITION_GRADES: list[tuple[str, str]] = [
    ("new_with_tags", "New with tags — unworn, original tags attached"),
    ("excellent", "Excellent — like new, no visible signs of wear"),
    ("very_good", "Very good — minor signs of wear, well maintained"),
    ("good", "Good — visible wear, fully functional"),
    ("fair", "Fair — significant wear or noticeable flaws"),
]


# ---------------------------------------------------------------------------
# Era / decade estimate
# ---------------------------------------------------------------------------
ERA_ESTIMATES: list[str] = [
    "pre-1990", "1990s", "2000s", "2010s", "2015-2020", "2020s", "current-season",
]


# ---------------------------------------------------------------------------
# Style tags — controlled, filterable (model picks 3-5)
# ---------------------------------------------------------------------------
STYLE_TAGS_CANONICAL: list[str] = [
    # Aesthetic
    "classic", "minimalist", "maximalist", "avant-garde", "romantic",
    "preppy", "bohemian", "grunge", "punk", "gothic", "y2k", "vintage",
    "retro", "futuristic", "androgynous", "feminine", "masculine",
    # Mood
    "elegant", "sophisticated", "polished", "refined", "understated",
    "playful", "edgy", "sporty", "athletic", "casual", "smart-casual",
    "professional", "formal", "cocktail", "evening", "loungewear",
    # Lifestyle
    "investment", "everyday", "statement", "occasion", "travel", "resort",
    "workwear", "weekend", "date-night",
    # Quality cues
    "luxury", "designer", "heritage", "artisanal", "handmade", "crafted",
    "limited-edition", "collectible",
    # Trend
    "quiet-luxury", "old-money", "coastal", "western", "utility", "military",
    "nautical", "equestrian",
]


# ---------------------------------------------------------------------------
# Brand aliases — canonical name -> common variants/abbreviations
#
# Used post-extraction: if GPT returns a known alias, normalize to canonical.
# If brand is unknown, pass through with confidence: "low".
# ---------------------------------------------------------------------------
BRAND_ALIASES: dict[str, list[str]] = {
    "Saint Laurent": ["YSL", "Yves Saint Laurent", "Saint Laurent Paris"],
    "Comme des Garçons": ["CDG", "Comme des Garcons", "Comme des Garçons Play", "CDG Play"],
    "Maison Margiela": ["Margiela", "MM6", "Maison Martin Margiela", "MMM"],
    "Bottega Veneta": ["Bottega"],
    "Balenciaga": ["BB"],
    "Christian Dior": ["Dior", "Dior Homme", "Christian Dior Monsieur", "Dior Monsieur", "Dior Sport"],
    "Givenchy": [],
    "Louis Vuitton": ["LV"],
    "Gucci": [],
    "Chanel": [],
    "Hermès": ["Hermes"],
    "Prada": [],
    "Miu Miu": [],
    "Loewe": [],
    "The Row": [],
    "Khaite": [],
    "Toteme": [],
    "Lemaire": [],
    "Jil Sander": [],
    "A.P.C.": ["APC", "A P C", "A.P.C"],
    "C.P. Company": ["CP Company", "C P Company"],
    "Acne Studios": ["Acne"],
    "Phoebe Philo": [],
    "Céline": ["Celine", "Old Celine", "Phoebe Philo Celine"],
    "Valentino": [],
    "Burberry": ["Burberry London", "Burberry Prorsum", "Burberrys", "Burberrys of London"],
    "Stella McCartney": [],
    "Alexander McQueen": ["McQueen"],
    "Alexander Wang": [],
    "Alaïa": ["Alaia", "Azzedine Alaïa"],
    "Ann Demeulemeester": [],
    "Dries Van Noten": ["Dries"],
    "Issey Miyake": ["Pleats Please", "Pleats Please Issey Miyake", "Homme Plissé"],
    "Yohji Yamamoto": ["Yohji", "Y's"],
    "Junya Watanabe": [],
    "Sacai": [],
    "Undercover": [],
    "Toga": ["Toga Pulla", "Toga Archives"],
    "Kapital": [],
    "Visvim": [],
    "Engineered Garments": [],
    "Needles": [],
    "Auralee": [],
    "Studio Nicholson": [],
    "Tory Burch": [],
    "Tibi": [],
    "Vince": [],
    "Theory": [],
    "Frame": [],
    "Reformation": [],
    "Ganni": [],
    "Isabel Marant": [],
    "Sandro": [],
    "Maje": [],
    "Iro": [],
    "Rag & Bone": ["Rag and Bone"],
    "Re/Done": ["Redone"],
    "Polo Ralph Lauren": ["Ralph Lauren", "Polo", "RRL", "Ralph"],
    "Tommy Hilfiger": ["Tommy"],
    "Calvin Klein": ["CK"],
    "Levi's": ["Levis"],
    "G-Star": ["G-Star RAW", "G Star", "GStar"],
    "Carhartt": ["Carhartt WIP"],
    "Stone Island": [],
    "Patagonia": [],
    "Arc'teryx": ["Arcteryx"],
    "The North Face": ["North Face", "TNF"],
    "Nike": [],
    "Adidas": [],
    "New Balance": ["NB"],
    "Asics": [],
    "Hoka": ["Hoka One One"],
    "Salomon": [],
    "Birkenstock": [],
    "Dr. Martens": ["Doc Martens", "Docs", "DM"],
    "Manolo Blahnik": ["Manolos"],
    "Jimmy Choo": [],
    "Christian Louboutin": ["Louboutin"],
    "Roger Vivier": [],
}


def all_known_brands() -> set[str]:
    """Return the set of canonical brand names + all aliases (lowercased)."""
    out: set[str] = set()
    for canonical, aliases in BRAND_ALIASES.items():
        out.add(canonical.lower())
        for a in aliases:
            out.add(a.lower())
    return out


def normalize_brand(raw: str | None) -> tuple[str, bool]:
    """Map a free-text brand string to its canonical name.

    Match priority:
      1. exact match on canonical name or any alias (case-insensitive)
      2. substring/prefix match — if the raw string starts with or contains a
         canonical name (e.g. "Christian Dior Monsieur" -> "Christian Dior"
         when no exact alias was registered)

    Returns (canonical_name, was_known). If the brand isn't matched,
    returns the raw string unchanged with was_known=False.
    """
    if not raw:
        return "", False
    raw_norm = raw.strip()
    if not raw_norm:
        return "", False
    raw_lower = raw_norm.lower()

    # Pass 1: exact match against canonical or any alias
    for canonical, aliases in BRAND_ALIASES.items():
        if raw_lower == canonical.lower():
            return canonical, True
        for a in aliases:
            if raw_lower == a.lower():
                return canonical, True

    # Pass 2: substring/prefix match. Prefer the longest canonical name that
    # appears as a whole-word match in the raw string (so "Christian Dior
    # Monsieur" -> "Christian Dior", not "Dior").
    best_canonical = None
    best_len = 0
    for canonical in BRAND_ALIASES.keys():
        c_lower = canonical.lower()
        # Whole-word boundary check (rough): wrap in spaces
        if f" {c_lower} " in f" {raw_lower} " or raw_lower.startswith(c_lower + " ") \
                or raw_lower.endswith(" " + c_lower):
            if len(c_lower) > best_len:
                best_canonical = canonical
                best_len = len(c_lower)
    if best_canonical:
        return best_canonical, True

    return raw_norm, False


# ---------------------------------------------------------------------------
# Material synonyms — variant -> canonical primary material
# ---------------------------------------------------------------------------
MATERIAL_PRIMARY: list[str] = [
    "cotton", "linen", "silk", "wool", "cashmere", "leather", "suede",
    "nylon", "polyester", "rayon", "viscose", "denim", "velvet", "tweed",
    "satin", "chiffon", "lace", "fur", "shearling", "down", "synthetic",
    "blend", "other",
]

MATERIAL_SYNONYMS: dict[str, str] = {
    "merino": "wool",
    "merino wool": "wool",
    "lambswool": "wool",
    "alpaca": "wool",
    "mohair": "wool",
    "tweed": "wool",
    "boucle": "wool",
    "bouclé": "wool",
    "felted wool": "wool",
    "cashmere blend": "cashmere",
    "100% cashmere": "cashmere",
    "calfskin": "leather",
    "lambskin": "leather",
    "patent leather": "leather",
    "vegan leather": "synthetic",
    "faux leather": "synthetic",
    "pleather": "synthetic",
    "nubuck": "suede",
    "raw denim": "denim",
    "selvedge denim": "denim",
    "stretch denim": "denim",
    "poplin": "cotton",
    "twill": "cotton",
    "oxford cloth": "cotton",
    "jersey": "cotton",
    "terrycloth": "cotton",
    "flannel": "cotton",
    "gabardine": "cotton",
    "cotton gabardine": "cotton",
    "georgette": "silk",
    "crepe de chine": "silk",
    "charmeuse": "silk",
    "habotai": "silk",
    "dupioni": "silk",
    "shantung": "silk",
    "organza": "silk",
    "tulle": "synthetic",
    "spandex": "synthetic",
    "elastane": "synthetic",
    "lycra": "synthetic",
    "acrylic": "synthetic",
    "modal": "rayon",
    "tencel": "rayon",
    "lyocell": "rayon",
    "bamboo": "rayon",
    "cupro": "rayon",
}


def normalize_material(raw: str | None) -> tuple[str, bool]:
    """Map a free-text material string to its canonical primary material.

    Returns (canonical_material, was_known).
    """
    if not raw:
        return "other", False
    raw_norm = raw.strip().lower()
    if raw_norm in MATERIAL_PRIMARY:
        return raw_norm, True
    if raw_norm in MATERIAL_SYNONYMS:
        return MATERIAL_SYNONYMS[raw_norm], True
    # Substring fallback — "cotton blend" -> "cotton", "wool blend" -> "wool"
    for primary in MATERIAL_PRIMARY:
        if primary in raw_norm:
            return primary, True
    return "other", False


# ---------------------------------------------------------------------------
# Image roles (validated on input)
# ---------------------------------------------------------------------------
IMAGE_ROLES: list[str] = ["front", "back", "label", "detail", "worn", "damage"]


# ---------------------------------------------------------------------------
# Convenience: format a list as a prompt-friendly string
# ---------------------------------------------------------------------------
def enum_for_prompt(values: list[str]) -> str:
    return ", ".join(values)


def subcategories_for_prompt() -> str:
    """Render the SUBCATEGORIES dict as a readable block for the prompt."""
    lines = []
    for cat, subs in SUBCATEGORIES.items():
        lines.append(f"  {cat}: {', '.join(subs)}")
    return "\n".join(lines)


def condition_grades_for_prompt() -> str:
    return "\n".join(f"  - {grade}: {desc}" for grade, desc in CONDITION_GRADES)
