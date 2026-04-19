# Listing API — Evaluation Harness

Measure how accurate the analyzer pipeline actually is, per field, against
ground-truth labels.

## Why this exists

The demo *looks* good, but until we score it against real labels we don't know
which fields are shippable today and which need work. The first question every
B2B customer will ask is "what's your accuracy?" — this is how we answer it.

## Quick start

```bash
# 1. Populate the dataset (one-time, ~5 min, requires network):
python -m listing_api.eval.scrape_grailed --n 20

# 2. Run the eval (uses your OPENAI_API_KEY):
python -m listing_api.eval.run_eval

# 3. Read the report:
open listing_api/eval/results/<latest>.md
```

## Scoring

Each field has its own scorer (see `scoring.py`):

| Field | Scorer | Notes |
|---|---|---|
| `category`, `subcategory`, `primary_color`, `pattern`, `color_palette`, `size_label` | exact match | case-insensitive |
| `primary_material` | normalized exact | "merino" → "wool", etc. via `taxonomy.normalize_material` |
| `brand` | normalized exact | aliases collapsed via `taxonomy.normalize_brand` |
| `silhouette`, `secondary_colors` | Jaccard similarity | overlap over union |
| `style_tags` | recall | what fraction of truth tags did we catch |
| `condition` | tier-adjacent | 1.0 exact, 0.5 ±1 tier, 0.0 otherwise |
| `era_estimate` | tier-adjacent | 1.0 exact, 0.5 neighboring decade, 0.0 otherwise |

Fields without a `truth` value for a given item are skipped (don't count for or
against accuracy). This means scores reflect "of the items where we *know* the
truth, how often were we right?"

## Adding your own items (high-trust ground truth)

For your own wardrobe, you trust the labels 100%. Create a folder under
`listing_api/eval/items/`:

```
items/
  wardrobe-001/
    front.jpg
    back.jpg
    detail.jpg
    label.jpg            # optional interior care-label photo
    meta.json
```

Where `meta.json` looks like:

```json
{
  "item_id": "wardrobe-001",
  "source": "wardrobe",
  "ground_truth": {
    "category": "Outerwear",
    "subcategory": "Wool Coat",
    "brand": "Max Mara",
    "primary_material": "wool",
    "primary_color": "charcoal",
    "pattern": "solid",
    "condition": "very_good",
    "size_label": "US 6"
  },
  "images": [
    {"file": "front.jpg",  "role": "front"},
    {"file": "back.jpg",   "role": "back"},
    {"file": "detail.jpg", "role": "detail"},
    {"file": "label.jpg",  "role": "label"}
  ]
}
```

Only fill in `ground_truth` fields you're certain about — anything left out is
skipped during scoring.

## Run modes

```bash
# Default: send every photo we have (including label.jpg) to the analyzer
python -m listing_api.eval.run_eval

# "Real-world" run: don't send the care-label photo (most resale listings won't
# have one) — measures accuracy in the wild
python -m listing_api.eval.run_eval --no-label

# Dual: run BOTH so you can see how much the label photo helps (e.g.,
# "material accuracy: 62% → 91% with care-label photo")
python -m listing_api.eval.run_eval --dual

# Subset
python -m listing_api.eval.run_eval --limit 5
python -m listing_api.eval.run_eval --items 001 003 wardrobe-002
```

## Caveats

- **30 items is a sanity check, not a published benchmark.** Per-field
  accuracies have ~±10% confidence intervals at this sample size. Good enough
  to know if we're in the 80%/60%/40% ballpark; not good enough to put exact
  numbers on a sales deck.
- **Grailed labels are noisy** — sellers misidentify materials and conditions
  routinely. Treat scraped items as ~80% trustworthy. Your own wardrobe items
  are the gold-standard subset.
- **Free-text fields** (`style_descriptors`, `key_details`, `condition_notes`,
  `material_raw`) are not scored — there's no objective ground truth for prose.

## Files

- `dataset.py` — load items from `items/` directory
- `scoring.py` — per-field scoring functions + aggregator
- `run_eval.py` — runs the pipeline on each item, outputs JSON + markdown
- `report.py` — markdown report generator (called by `run_eval` automatically)
- `scrape_grailed.py` — pulls labeled listings from Grailed's public Algolia API

## Legal note on scraping

`scrape_grailed.py` uses Grailed's public Algolia API keys (embedded in every
Grailed page) the same way their website does. Photos and labels are
downloaded for **internal evaluation only** — do not redistribute, republish,
or use the scraped content commercially.
