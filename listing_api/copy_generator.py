"""SEO-friendly listing copy generator.

Takes a normalized analyzer output dict and produces:
- title:        80-char max, brand + key descriptor + subcategory
- description:  3-5 sentences in resale-platform house style
- tags:         15-25 lowercase searchable tokens (combines structured + free)

Strategy:
- Use a single GPT call with a tightly scoped prompt (cheap, deterministic).
- Provide a deterministic fallback (template-based) if the LLM call fails — so
  the API always returns valid copy even on partial outage.
"""

from __future__ import annotations

import json
import re
import time

from oracle_frontend.ai_config import get_openai_client, OPENAI_MODEL


SYSTEM_PROMPT = (
    "You are a senior copywriter for a luxury and contemporary resale platform "
    "(think Vestiaire Collective, The RealReal, Rebag). You write tight, "
    "factual, search-optimized listing copy that highlights brand heritage, "
    "construction, condition, and styling. You never invent details that "
    "aren't in the structured input. House style: confident, understated, "
    "no fluff, no exclamation marks, no emojis."
)


def _build_prompt(meta: dict) -> str:
    return f"""Write listing copy for the garment described by this structured metadata.

METADATA (do NOT invent additional facts):
{json.dumps(meta, indent=2)}

Output a single JSON object with EXACTLY these three keys:

{{
  "title": "<80 chars max — Brand + Key Descriptor + Subcategory + (Color or Material). E.g. 'Saint Laurent Oversized Black Wool Coat'. If brand is unknown, lead with the most specific descriptor.>",
  "description": "<3-5 sentences. Sentence 1: brand + item type + headline silhouette/material. Sentence 2: construction details (key_details, pattern, color story). Sentence 3: condition (use the condition + condition_notes). Sentence 4 (optional): styling suggestion grounded in style_tags. No marketing fluff, no superlatives like 'stunning' or 'gorgeous'.>",
  "tags": ["<15-25 lowercase tokens, hyphenated where appropriate. Include: brand (canonical + aliases if relevant), category, subcategory, primary_color, pattern, primary_material, all silhouettes, all style_tags, era_estimate if present. Deduplicated.>"]
}}

Return ONLY the JSON object. No prose, no markdown.
"""


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no json object in response: {raw[:200]}")
    return json.loads(text[start : end + 1])


def _normalize_title(t: str) -> str:
    t = re.sub(r"\s+", " ", (t or "")).strip()
    return t[:80]


def _normalize_tags(raw_tags) -> list[str]:
    if not isinstance(raw_tags, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for t in raw_tags:
        if not isinstance(t, str):
            continue
        norm = re.sub(r"\s+", "-", t.strip().lower())
        norm = re.sub(r"[^a-z0-9\-]", "", norm)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out[:25]


def _fallback_copy(meta: dict) -> dict:
    """Deterministic template fallback if the LLM call fails."""
    brand = (meta.get("brand") or "").strip()
    sub = meta.get("subcategory", "").strip()
    color = meta.get("primary_color", "").strip()
    material = meta.get("primary_material", "").strip()
    silhouette = meta.get("silhouette") or []
    pattern = meta.get("pattern", "")
    condition = meta.get("condition", "good").replace("_", " ")
    condition_notes = meta.get("condition_notes", "")
    style_tags = meta.get("style_tags") or []
    key_details = meta.get("key_details") or []
    era = meta.get("era_estimate")

    sub_lower = sub.lower()
    descriptor_bits = [
        b for b in [silhouette[0] if silhouette else "", color, material]
        if b and b.lower() not in sub_lower
    ]
    title_parts = [brand] if brand else []
    title_parts += [w.capitalize() for w in descriptor_bits]
    title_parts.append(sub)
    title = _normalize_title(" ".join(p for p in title_parts if p))

    sentences = []
    lead_brand = brand or "Designer"
    lead_silhouette = silhouette[0] if silhouette else ""
    sentences.append(
        f"{lead_brand} {sub.lower()} in {color} {material}".strip() + "."
    )
    if lead_silhouette or pattern != "solid" or key_details:
        details_str = ", ".join(filter(None, [
            lead_silhouette,
            None if pattern in ("", "solid") else pattern,
            *key_details[:3],
        ]))
        if details_str:
            sentences.append(f"Features {details_str}.")
    cond_sentence = f"Condition: {condition}."
    if condition_notes:
        cond_sentence = f"Condition: {condition} — {condition_notes.rstrip('.')}"
    sentences.append(cond_sentence)
    if style_tags:
        sentences.append(f"Pairs well with {', '.join(style_tags[:3])} pieces.")

    description = " ".join(sentences)

    raw_tags = []
    if brand:
        raw_tags.append(brand)
    raw_tags += [meta.get("category"), sub, color, pattern, material]
    raw_tags += silhouette
    raw_tags += style_tags
    if era:
        raw_tags.append(era)
    tags = _normalize_tags(raw_tags)

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "source": "template_fallback",
    }


def generate_listing_copy(meta: dict, model: str | None = None) -> dict:
    """Generate title, description, tags from analyzer metadata.

    Returns:
        {"title": str, "description": str, "tags": list[str], "source": "llm"|"template_fallback",
         "_meta": {"model": str, "elapsed_ms": int, "input_tokens": int, "output_tokens": int}}
    """
    chosen_model = model or OPENAI_MODEL
    started = time.time()

    try:
        resp = get_openai_client().chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(meta)},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )
        raw = resp.choices[0].message.content or ""
        parsed = _parse_json_response(raw)
        title = _normalize_title(parsed.get("title", ""))
        description = (parsed.get("description") or "").strip()
        tags = _normalize_tags(parsed.get("tags"))
        if not title or not description or not tags:
            raise ValueError("missing required field in LLM output")

        usage = getattr(resp, "usage", None)
        return {
            "title": title,
            "description": description,
            "tags": tags,
            "source": "llm",
            "_meta": {
                "model": chosen_model,
                "elapsed_ms": int((time.time() - started) * 1000),
                "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            },
        }
    except Exception as e:
        print(f"[copy_generator] LLM call failed, using template fallback: {e}")
        fallback = _fallback_copy(meta)
        fallback["_meta"] = {
            "model": "template",
            "elapsed_ms": int((time.time() - started) * 1000),
            "input_tokens": 0,
            "output_tokens": 0,
            "fallback_reason": str(e),
        }
        return fallback
