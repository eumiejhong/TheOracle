"""High-level pipeline: images -> metadata + listing copy + embeddings.

Wraps analyzer + copy_generator + embeddings into a single orchestration
function used by both the demo view and the production /analyze endpoint.
"""

from __future__ import annotations

import time

from oracle_frontend.embeddings import (
    BGE_DIM,
    BGE_MODEL_NAME,
    CLIP_DIM,
    CLIP_MODEL_NAME,
    embed_image,
    embed_text,
)

from .analyzer import ImageInput, analyze_garment
from .copy_generator import generate_listing_copy


def _build_text_embedding_input(metadata: dict, listing: dict) -> str:
    """The text we embed is intentionally the rich descriptors + the listing
    description — this is what makes semantic search across listings useful.
    """
    parts: list[str] = []
    descriptors = metadata.get("style_descriptors") or []
    if descriptors:
        parts.append(" ".join(descriptors))
    desc = (listing or {}).get("description") or ""
    if desc:
        parts.append(desc)
    return " ".join(parts).strip()


def run_pipeline(
    images: list[ImageInput],
    hint: str | None = None,
    include_embeddings: bool = True,
    include_copy: bool = True,
    model: str | None = None,
) -> dict:
    """Run the full image-to-listing pipeline.

    Returns a dict with shape:
    {
      "metadata":   <analyzer output (without _meta)>,
      "listing":    {"title", "description", "tags"} | null,
      "embeddings": {
         "text":  {"model", "dim", "vector"} | null,
         "image": {"model", "dim", "vector"} | null,
      } | null,
      "_meta": {
         "elapsed_ms": int,
         "analyzer": {...},
         "copy_generator": {...} | null,
         "embeddings_included": bool,
      }
    }
    """
    t0 = time.time()

    metadata = analyze_garment(images, hint=hint, model=model)
    analyzer_meta = metadata.pop("_meta", {})

    listing = None
    copy_meta = None
    if include_copy:
        copy_result = generate_listing_copy(metadata, model=model)
        copy_meta = copy_result.pop("_meta", {})
        listing = copy_result

    embeddings = None
    if include_embeddings:
        text_input = _build_text_embedding_input(metadata, listing or {})
        text_vec = embed_text(text_input) if text_input else []

        # Front image (or first image) for CLIP
        front_img = next((img for img in images if img.role == "front"), images[0])
        image_vec = embed_image(front_img.bytes_data) if front_img else []

        embeddings = {
            "text": {
                "model": BGE_MODEL_NAME,
                "dim": BGE_DIM,
                "vector": text_vec,
                "source_text": text_input,
            } if text_vec else None,
            "image": {
                "model": CLIP_MODEL_NAME,
                "dim": CLIP_DIM,
                "vector": image_vec,
                "source_image_role": front_img.role if front_img else None,
            } if image_vec else None,
        }

    return {
        "metadata": metadata,
        "listing": listing,
        "embeddings": embeddings,
        "_meta": {
            "elapsed_ms": int((time.time() - t0) * 1000),
            "analyzer": analyzer_meta,
            "copy_generator": copy_meta,
            "embeddings_included": include_embeddings,
        },
    }
