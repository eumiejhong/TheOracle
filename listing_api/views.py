from __future__ import annotations

import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .analyzer import AnalyzerError, ImageInput
from .auth import APIKeyAuthentication
from .models import AnalysisRequest, APIKey
from .pipeline import run_pipeline
from .taxonomy import IMAGE_ROLES
from .throttling import PerKeyDayThrottle, PerKeyMinuteThrottle


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def health(request):
    return JsonResponse({"status": "ok", "service": "listing_api"})


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------
def landing(request):
    return render(request, "listing_api/landing.html")


# ---------------------------------------------------------------------------
# Docs page
# ---------------------------------------------------------------------------
def docs(request):
    from .taxonomy import (
        CATEGORIES, SILHOUETTES, COLORS_PRIMARY, COLOR_PALETTES, PATTERNS,
        CONDITION_GRADES, ERA_ESTIMATES, STYLE_TAGS_CANONICAL, MATERIAL_PRIMARY,
        BRAND_ALIASES, IMAGE_ROLES,
    )
    return render(request, "listing_api/docs.html", {
        "categories": CATEGORIES,
        "silhouettes": SILHOUETTES,
        "colors_primary": COLORS_PRIMARY,
        "color_palettes": COLOR_PALETTES,
        "patterns": PATTERNS,
        "condition_grades": CONDITION_GRADES,
        "era_estimates": ERA_ESTIMATES,
        "style_tags": STYLE_TAGS_CANONICAL,
        "materials": MATERIAL_PRIMARY,
        "brand_count": len(BRAND_ALIASES),
        "image_roles": IMAGE_ROLES,
    })


# ---------------------------------------------------------------------------
# Demo (browser-friendly: HTML form, runs the same pipeline as the API)
# ---------------------------------------------------------------------------
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB per image
MAX_IMAGES = 6


def _parse_uploaded_images(request) -> list[ImageInput]:
    files = request.FILES.getlist("images")
    if not files:
        raise AnalyzerError("at least one image is required (field: 'images')")
    if len(files) > MAX_IMAGES:
        raise AnalyzerError(f"maximum {MAX_IMAGES} images per request")

    roles_raw = request.POST.get("roles", "")
    roles = [r.strip() for r in roles_raw.split(",")] if roles_raw else []
    while len(roles) < len(files):
        roles.append("front" if not roles else "detail")

    images: list[ImageInput] = []
    for f, role in zip(files, roles):
        data = f.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise AnalyzerError(
                f"image '{f.name}' exceeds {MAX_IMAGE_BYTES // (1024 * 1024)}MB limit"
            )
        if role not in IMAGE_ROLES:
            role = "front" if not images else "detail"
        images.append(ImageInput(bytes_data=data, role=role, filename=f.name))
    return images


@csrf_exempt
@require_http_methods(["GET", "POST"])
def demo(request):
    """Browser demo page. Renders the upload form on GET; runs the pipeline on POST."""
    if request.method == "GET":
        return render(request, "listing_api/demo.html", {
            "image_roles": IMAGE_ROLES,
            "max_images": MAX_IMAGES,
        })

    hint = (request.POST.get("hint") or "").strip() or None
    include_embeddings = request.POST.get("include_embeddings", "true").lower() != "false"

    try:
        images = _parse_uploaded_images(request)
    except AnalyzerError as e:
        return _demo_error(request, str(e))

    try:
        result = run_pipeline(images, hint=hint, include_embeddings=include_embeddings)
    except AnalyzerError as e:
        return _demo_error(request, str(e))
    except Exception as e:
        return _demo_error(request, f"unexpected error: {e}")

    # Log the demo request (non-blocking — silent fail if migrations not yet applied)
    try:
        from .models import AnalysisRequest
        meta = result.get("_meta", {})
        analyzer_meta = meta.get("analyzer", {}) or {}
        copy_meta = meta.get("copy_generator", {}) or {}
        AnalysisRequest.objects.create(
            api_key=None,
            source="demo",
            image_count=len(images),
            processing_time_ms=meta.get("elapsed_ms", 0),
            model_used=analyzer_meta.get("model", ""),
            input_tokens=(analyzer_meta.get("input_tokens", 0) + copy_meta.get("input_tokens", 0)),
            output_tokens=(analyzer_meta.get("output_tokens", 0) + copy_meta.get("output_tokens", 0)),
            embeddings_included=include_embeddings,
            success=True,
        )
    except Exception as e:
        print(f"[listing_api.demo] usage log skipped: {e}")

    # Truncated copy of embeddings for display (full vectors are huge)
    display_embeddings = None
    embeddings = result.get("embeddings")
    if embeddings:
        display_embeddings = {}
        for kind, payload in embeddings.items():
            if not payload:
                display_embeddings[kind] = None
                continue
            vec = payload.get("vector") or []
            display_embeddings[kind] = {
                "model": payload.get("model"),
                "dim": payload.get("dim"),
                "preview": vec[:8],
                "vector_full_json": json.dumps(vec),
            }

    run_meta = result.get("_meta", {})
    return render(
        request,
        "listing_api/demo.html",
        {
            "image_roles": IMAGE_ROLES,
            "max_images": MAX_IMAGES,
            "metadata": result.get("metadata"),
            "listing": result.get("listing"),
            "run_meta": run_meta,
            "analyzer_meta": run_meta.get("analyzer") or {},
            "copy_meta": run_meta.get("copy_generator") or {},
            "result_json": json.dumps(result, indent=2),
            "display_embeddings": display_embeddings,
            "submitted_hint": hint or "",
            "submitted_include_embeddings": include_embeddings,
        },
    )


def _demo_error(request, message: str):
    return render(
        request,
        "listing_api/demo.html",
        {
            "image_roles": IMAGE_ROLES,
            "max_images": MAX_IMAGES,
            "error": message,
        },
        status=400,
    )


# ---------------------------------------------------------------------------
# Production API endpoint — POST /listing/api/v1/analyze
# ---------------------------------------------------------------------------
def _parse_api_images(files, roles_raw: str) -> list[ImageInput]:
    if not files:
        raise AnalyzerError("at least one image is required (field: 'images')")
    if len(files) > MAX_IMAGES:
        raise AnalyzerError(f"maximum {MAX_IMAGES} images per request")

    roles = [r.strip() for r in roles_raw.split(",")] if roles_raw else []
    while len(roles) < len(files):
        roles.append("front" if not roles else "detail")

    images: list[ImageInput] = []
    for f, role in zip(files, roles):
        data = f.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise AnalyzerError(
                f"image '{f.name}' exceeds {MAX_IMAGE_BYTES // (1024 * 1024)}MB limit"
            )
        if role not in IMAGE_ROLES:
            role = "front" if not images else "detail"
        images.append(ImageInput(bytes_data=data, role=role, filename=f.name))
    return images


@api_view(["POST"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([PerKeyMinuteThrottle, PerKeyDayThrottle])
def analyze(request):
    """Analyze 1-6 garment images and return metadata + listing copy + embeddings.

    Multipart form fields:
      - images:              one or more files (required)
      - roles:               CSV of roles matching images (optional)
      - hint:                free-text hint (optional)
      - include_embeddings:  "true"|"false" — default "true"
      - include_copy:        "true"|"false" — default "true"
    """
    api_key = request.auth  # APIKey instance (guaranteed by APIKeyAuthentication)

    files = request.FILES.getlist("images")
    roles_raw = (request.data.get("roles") or "").strip() if hasattr(request.data, "get") else ""
    hint = (request.data.get("hint") or "").strip() or None
    include_embeddings = _parse_bool(request.data.get("include_embeddings"), default=True)
    include_copy = _parse_bool(request.data.get("include_copy"), default=True)

    try:
        images = _parse_api_images(files, roles_raw)
    except AnalyzerError as e:
        _log_request(api_key, source="api", images=files, success=False, error=str(e))
        return Response(
            {"error": {"code": "invalid_request", "message": str(e)}},
            status=400,
        )

    try:
        result = run_pipeline(
            images,
            hint=hint,
            include_embeddings=include_embeddings,
            include_copy=include_copy,
        )
    except AnalyzerError as e:
        _log_request(api_key, source="api", images=files, success=False, error=str(e))
        return Response(
            {"error": {"code": "analysis_failed", "message": str(e)}},
            status=422,
        )
    except Exception as e:
        _log_request(api_key, source="api", images=files, success=False, error=str(e))
        return Response(
            {"error": {"code": "internal_error", "message": "internal error"}},
            status=500,
        )

    _log_request(
        api_key,
        source="api",
        images=files,
        success=True,
        include_embeddings=include_embeddings,
        result=result,
    )

    # Build a clean client-facing response (strip internal _meta bits we don't want to leak).
    rmeta = result.get("_meta", {})
    return Response(
        {
            "metadata": result.get("metadata"),
            "listing": result.get("listing"),
            "embeddings": result.get("embeddings"),
            "usage": {
                "elapsed_ms": rmeta.get("elapsed_ms"),
                "model": (rmeta.get("analyzer") or {}).get("model"),
                "input_tokens": (rmeta.get("analyzer") or {}).get("input_tokens", 0)
                + (rmeta.get("copy_generator") or {}).get("input_tokens", 0),
                "output_tokens": (rmeta.get("analyzer") or {}).get("output_tokens", 0)
                + (rmeta.get("copy_generator") or {}).get("output_tokens", 0),
                "image_count": len(files),
            },
        },
        status=200,
    )


def _parse_bool(val, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() not in ("false", "0", "no", "off", "")


def _log_request(api_key, source, images, success, error="", include_embeddings=True, result=None):
    try:
        meta = (result or {}).get("_meta", {}) if result else {}
        analyzer_meta = meta.get("analyzer", {}) or {}
        copy_meta = meta.get("copy_generator", {}) or {}
        AnalysisRequest.objects.create(
            api_key=api_key if isinstance(api_key, APIKey) else None,
            source=source,
            image_count=len(images) if images else 0,
            processing_time_ms=meta.get("elapsed_ms", 0),
            model_used=analyzer_meta.get("model", ""),
            input_tokens=analyzer_meta.get("input_tokens", 0) + copy_meta.get("input_tokens", 0),
            output_tokens=analyzer_meta.get("output_tokens", 0) + copy_meta.get("output_tokens", 0),
            embeddings_included=include_embeddings,
            success=success,
            error_message=(error or "")[:2000],
        )
    except Exception as e:
        print(f"[listing_api] usage log skipped: {e}")
