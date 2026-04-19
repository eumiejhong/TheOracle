"""Dataset loading helpers.

A dataset is a directory of per-item folders:

  listing_api/eval/items/
    {item_id}/
      meta.json          # ground truth + image manifest
      front.jpg          # required
      back.jpg           # optional
      detail.jpg         # optional
      label.jpg          # optional (interior care label)
      ...

`meta.json` schema (only fields you know go in `ground_truth`; everything else
is skipped during scoring):

  {
    "item_id": "001",
    "source": "grailed | wardrobe | ebay | manual",
    "source_url": "...",                   # optional
    "notes": "...",                        # optional human notes
    "ground_truth": {
      "category": "Outerwear",
      "subcategory": "Wool Coat",
      "brand": "Max Mara",
      "primary_material": "wool",
      "primary_color": "charcoal",
      "secondary_colors": [],
      "color_palette": "neutral",
      "pattern": "solid",
      "silhouette": ["long", "single-breasted", "structured"],
      "size_label": "US 6",
      "condition": "very_good",
      "era_estimate": "current-season",
      "style_tags": ["classic", "minimalist", "investment"]
    },
    "images": [
      {"file": "front.jpg",  "role": "front"},
      {"file": "back.jpg",   "role": "back"},
      {"file": "detail.jpg", "role": "detail"},
      {"file": "label.jpg",  "role": "label"}
    ]
  }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..analyzer import ImageInput

EVAL_DIR = Path(__file__).parent
ITEMS_DIR = EVAL_DIR / "items"


@dataclass
class EvalItem:
    item_id: str
    folder: Path
    ground_truth: dict
    images: list[dict] = field(default_factory=list)
    source: str = ""
    source_url: str = ""
    notes: str = ""

    def load_images(self, exclude_roles: set[str] | None = None) -> list[ImageInput]:
        """Load images from disk, optionally excluding certain roles.

        `exclude_roles={"label"}` is the "real-world" run (no care-label photo).
        Default loads all images present.
        """
        exclude_roles = exclude_roles or set()
        out: list[ImageInput] = []
        for img in self.images:
            role = img.get("role", "front")
            if role in exclude_roles:
                continue
            file_path = self.folder / img["file"]
            if not file_path.exists():
                continue
            out.append(
                ImageInput(
                    bytes_data=file_path.read_bytes(),
                    role=role,
                    filename=img["file"],
                )
            )
        if not out:
            raise FileNotFoundError(
                f"No images found for item {self.item_id} (after exclude={exclude_roles})"
            )
        return out


def load_items(items_dir: Path | None = None) -> list[EvalItem]:
    """Load all items from items/ directory."""
    items_dir = Path(items_dir) if items_dir else ITEMS_DIR
    if not items_dir.exists():
        return []

    out: list[EvalItem] = []
    for child in sorted(items_dir.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception as e:
            print(f"[dataset] WARN: skipping {child.name}, bad meta.json: {e}")
            continue

        out.append(
            EvalItem(
                item_id=meta.get("item_id", child.name),
                folder=child,
                ground_truth=meta.get("ground_truth", {}),
                images=meta.get("images", []),
                source=meta.get("source", ""),
                source_url=meta.get("source_url", ""),
                notes=meta.get("notes", ""),
            )
        )
    return out
