"""Generate a markdown report from a results JSON.

Standalone usage:
  python -m listing_api.eval.report listing_api/eval/results/20260219-120000_with_all.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Field display order + grouping
FIELD_GROUPS = [
    ("Easy / structural", ["category", "subcategory", "primary_color", "color_palette",
                            "pattern", "secondary_colors", "silhouette"]),
    ("Material & brand",  ["primary_material", "brand"]),
    ("Subjective",        ["condition", "era_estimate", "size_label", "style_tags"]),
]


def _bar(value: float, width: int = 20) -> str:
    """ASCII progress bar for a 0.0-1.0 value."""
    filled = int(round(value * width))
    return "█" * filled + "░" * (width - filled)


def write_report(summary: dict, path: Path) -> None:
    lines: list[str] = []
    mode = summary["mode"]
    lines.append(f"# Eval report — `{mode}`")
    lines.append("")
    lines.append(f"_Generated {summary.get('generated_at', '')}_")
    lines.append("")
    lines.append(f"- **Items run:** {summary['n_total']}  "
                 f"({summary['n_ok']} ok, {summary['n_fail']} failed)")

    # Top-line accuracy
    per_field = summary.get("per_field", {})
    macro_scores = [v["mean"] for v in per_field.values() if v["n"] > 0]
    macro = sum(macro_scores) / len(macro_scores) if macro_scores else 0.0
    lines.append(f"- **Macro accuracy** (mean of per-field means): **{macro:.1%}**")
    lines.append("")

    # Per-field table, grouped
    for group_name, group_fields in FIELD_GROUPS:
        present = [f for f in group_fields if f in per_field and per_field[f]["n"] > 0]
        if not present:
            continue
        lines.append(f"## {group_name}")
        lines.append("")
        lines.append("| Field | Accuracy |   | n | missing |")
        lines.append("|---|---:|---|---:|---:|")
        for f in present:
            stats = per_field[f]
            lines.append(
                f"| `{f}` | {stats['mean']:.1%} | `{_bar(stats['mean'])}` | "
                f"{stats['n']} | {stats['missing']} |"
            )
        lines.append("")

    # Per-item details (collapsible)
    lines.append("## Per-item breakdown")
    lines.append("")
    truth_lookup = summary.get("ground_truth_by_id", {})
    for r in summary["items"]:
        item_id = r["item_id"]
        if not r["ok"]:
            lines.append(f"### {item_id} — ❌ FAILED")
            lines.append("```")
            lines.append(r.get("error", "")[:600])
            lines.append("```")
            lines.append("")
            continue

        scores = r["scores"]
        scored = [v for v in scores.values() if v is not None]
        avg = sum(scored) / len(scored) if scored else 0.0
        lines.append(f"### {item_id} — avg {avg:.1%} ({r['elapsed_ms']}ms)")
        lines.append("")
        truth = truth_lookup.get(item_id, {})
        pred = r.get("predicted", {})
        lines.append("| Field | Truth | Predicted | Score |")
        lines.append("|---|---|---|---:|")
        for f in [f for grp in FIELD_GROUPS for f in grp[1]]:
            if scores.get(f) is None:
                continue
            t = truth.get(f, "—")
            p = pred.get(f, "—")
            t_s = ", ".join(t) if isinstance(t, list) else str(t)
            p_s = ", ".join(p) if isinstance(p, list) else str(p)
            mark = "✅" if scores[f] >= 0.99 else ("⚠️" if scores[f] >= 0.5 else "❌")
            lines.append(f"| `{f}` | {t_s} | {p_s} | {mark} {scores[f]:.0%} |")
        lines.append("")

    path.write_text("\n".join(lines))


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m listing_api.eval.report <results.json>")
        sys.exit(1)
    p = Path(sys.argv[1])
    summary = json.loads(p.read_text())
    out = p.with_suffix(".md")
    write_report(summary, out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
