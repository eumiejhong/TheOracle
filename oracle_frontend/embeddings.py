"""Shared embedding helpers used by both the consumer app and the listing API.

Models:
- Text: BAAI/bge-base-en-v1.5 (768-dim, normalized)
- Image: clip-ViT-B-32 (512-dim, normalized)

Both models are loaded lazily on first use and kept in module-level singletons
so subsequent calls are fast. First call incurs model download + load (~10s on
cold start). In production, consider preloading at server boot.
"""

from __future__ import annotations

import io
from typing import Iterable

from PIL import Image

# Module-level singletons (lazy loaded)
_bge_text_model = None
_clip_image_model = None

BGE_MODEL_NAME = "BAAI/bge-base-en-v1.5"
BGE_DIM = 768

CLIP_MODEL_NAME = "clip-ViT-B-32"
CLIP_DIM = 512


def get_bge_model():
    """Return the BGE text embedding model (loaded once, cached)."""
    global _bge_text_model
    if _bge_text_model is None:
        from sentence_transformers import SentenceTransformer
        _bge_text_model = SentenceTransformer(BGE_MODEL_NAME)
    return _bge_text_model


def get_clip_model():
    """Return the CLIP image embedding model (loaded once, cached)."""
    global _clip_image_model
    if _clip_image_model is None:
        from sentence_transformers import SentenceTransformer
        _clip_image_model = SentenceTransformer(CLIP_MODEL_NAME)
    return _clip_image_model


def embed_text(text: str) -> list[float]:
    """Return a normalized BGE embedding for the given text.

    Returns an empty list if text is empty or embedding fails.
    """
    if not text or not text.strip():
        return []
    try:
        vec = get_bge_model().encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        print(f"[embeddings] BGE failed: {e}")
        return []


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Batch-embed multiple strings. Same model, same normalization."""
    text_list = [t for t in texts if t and t.strip()]
    if not text_list:
        return []
    try:
        vecs = get_bge_model().encode(text_list, normalize_embeddings=True)
        return [v.tolist() for v in vecs]
    except Exception as e:
        print(f"[embeddings] BGE batch failed: {e}")
        return []


def embed_text_bytes(text: str) -> bytes:
    """Return BGE embedding as raw bytes (for storing in a BinaryField).

    Backwards-compatible with the previous save_logic.py behaviour:
    `embedding.tobytes()` produces float32 little-endian bytes.
    """
    if not text or not text.strip():
        return b""
    try:
        import numpy as np
        vec = get_bge_model().encode(text, normalize_embeddings=True)
        if isinstance(vec, np.ndarray):
            return vec.astype(np.float32).tobytes()
        return bytes(vec)
    except Exception as e:
        print(f"[embeddings] BGE bytes failed: {e}")
        return b""


def embed_image(image_bytes: bytes) -> list[float]:
    """Return a normalized CLIP image embedding for the given image bytes.

    Returns an empty list on failure (corrupt image, missing model, etc.).
    """
    if not image_bytes:
        return []
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        vec = get_clip_model().encode(img, normalize_embeddings=True)
        return vec.tolist()
    except Exception as e:
        print(f"[embeddings] CLIP failed: {e}")
        return []


def preload_models() -> dict[str, bool]:
    """Eagerly load both models. Call from server boot to avoid cold-start latency.

    Returns a dict like {"bge": True, "clip": True} indicating success.
    """
    result = {"bge": False, "clip": False}
    try:
        get_bge_model()
        result["bge"] = True
    except Exception as e:
        print(f"[embeddings] BGE preload failed: {e}")
    try:
        get_clip_model()
        result["clip"] = True
    except Exception as e:
        print(f"[embeddings] CLIP preload failed: {e}")
    return result
