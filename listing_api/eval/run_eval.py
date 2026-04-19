"""Eval runner.

Usage (from repo root, with Django env loaded):

  python -m listing_api.eval.run_eval                    # all items, default mode
  python -m listing_api.eval.run_eval --dual             # both with-label and without-label runs
  python -m listing_api.eval.run_eval --no-label         # exclude label.jpg from input
  python -m listing_api.eval.run_eval --limit 5          # first 5 items only
  python -m listing_api.eval.run_eval --items 001 003    # specific item IDs

Each item is run through `listing_api.pipeline.run_pipeline` with embeddings
disabled (we only score metadata). Results are written to:

  listing_api/eval/results/{timestamp}_{mode}.json
  listing_api/eval/results/{timestamp}_{mode}.md   (via report.py)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Ensure Django is configured even when run as a plain script
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oracle_backend.settings")
import django  # noqa: E402
django.setup()

from listing_api.eval.dataset import EVAL_DIR, EvalItem, load_items  # noqa: E402
from listing_api.eval.scoring import aggregate, score_item  # noqa: E402
from listing_api.pipeline import run_pipeline  # noqa: E402


RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def run_one(item: EvalItem, exclude_roles: set[str] | None = None) -> dict:
    """Run the pipeline on a single item and score it.

    Returns:
      {
        "item_id": ...,
        "ok": bool,
        "elapsed_ms": int,
        "predicted": <pipeline metadata>,
        "scores": {field: 0.0-1.0 | None},
        "error": str (if not ok)
      }
    """
    t0 = time.time()
    try:
        images = item.load_images(exclude_roles=exclude_roles)
    except FileNotFoundError as e:
        return {
            "item_id": item.item_id,
            "ok": False,
            "elapsed_ms": int((time.time() - t0) * 1000),
            "predicted": {},
            "scores": {},
            "error": str(e),
        }

    try:
        result = run_pipeline(
            images=images,
            include_embeddings=False,  # eval scores metadata only
            include_copy=False,        # skip copy gen (saves ~5s/item)
        )
        predicted = result.get("metadata", {})
        image_roles = {img.role for img in images}
        scores = score_item(predicted, item.ground_truth, image_roles=image_roles)
        return {
            "item_id": item.item_id,
            "ok": True,
            "elapsed_ms": int((time.time() - t0) * 1000),
            "predicted": predicted,
            "scores": scores,
        }
    except Exception as e:
        return {
            "item_id": item.item_id,
            "ok": False,
            "elapsed_ms": int((time.time() - t0) * 1000),
            "predicted": {},
            "scores": {},
            "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        }


def run(items: list[EvalItem], mode: str, exclude_roles: set[str] | None = None) -> dict:
    """Run all items, aggregate, and persist results."""
    print(f"\n=== eval mode={mode} | {len(items)} items ===")
    per_item: list[dict] = []
    for i, item in enumerate(items, 1):
        print(f"  [{i}/{len(items)}] {item.item_id} ... ", end="", flush=True)
        r = run_one(item, exclude_roles=exclude_roles)
        per_item.append(r)
        if r["ok"]:
            mean = [v for v in r["scores"].values() if v is not None]
            avg = (sum(mean) / len(mean)) if mean else 0.0
            print(f"ok ({r['elapsed_ms']}ms, avg={avg:.2f})")
        else:
            print(f"FAIL — {r['error'].splitlines()[0][:80]}")

    agg = aggregate([r["scores"] for r in per_item if r["ok"]])
    n_ok = sum(1 for r in per_item if r["ok"])
    n_fail = len(per_item) - n_ok

    summary = {
        "mode": mode,
        "n_total": len(per_item),
        "n_ok": n_ok,
        "n_fail": n_fail,
        "per_field": agg,
        "items": per_item,
        "ground_truth_by_id": {it.item_id: it.ground_truth for it in items},
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = RESULTS_DIR / f"{ts}_{mode}.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n→ wrote {json_path}")

    # Also generate the markdown report
    from listing_api.eval.report import write_report
    md_path = RESULTS_DIR / f"{ts}_{mode}.md"
    write_report(summary, md_path)
    print(f"→ wrote {md_path}")

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Run only first N items")
    ap.add_argument("--items", nargs="+", default=None, help="Specific item IDs")
    ap.add_argument("--no-label", action="store_true", help="Exclude care-label photos from input")
    ap.add_argument("--dual", action="store_true",
                    help="Run twice: with-label AND without-label, output both reports")
    args = ap.parse_args()

    items = load_items()
    if not items:
        print(f"No items found in {EVAL_DIR / 'items'}/")
        print("Add items with `python -m listing_api.eval.scrape_grailed --n 20` "
              "or by creating folders manually.")
        sys.exit(1)

    if args.items:
        wanted = set(args.items)
        items = [i for i in items if i.item_id in wanted]
    if args.limit:
        items = items[: args.limit]

    if args.dual:
        run(items, mode="with_label")
        run(items, mode="without_label", exclude_roles={"label"})
    elif args.no_label:
        run(items, mode="without_label", exclude_roles={"label"})
    else:
        run(items, mode="with_all")


if __name__ == "__main__":
    main()
