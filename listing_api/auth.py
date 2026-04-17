"""API key authentication for the Listing Intelligence API.

Usage from a view:

    @api_view(["POST"])
    @authentication_classes([APIKeyAuthentication])
    @permission_classes([IsAuthenticated])
    def analyze(request):
        api_key = request.auth  # APIKey instance
        ...

Clients send the key in the `Authorization: Bearer <key>` header, or as
`X-API-Key: <key>`.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import APIKey


class APIKeyUser:
    """A minimal user-like object representing an authenticated API client."""

    is_authenticated = True
    is_active = True
    is_anonymous = False

    def __init__(self, api_key: APIKey):
        self.api_key = api_key
        self.pk = f"apikey:{api_key.pk}"
        self.username = api_key.organization

    def __str__(self) -> str:
        return self.username


class APIKeyAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        key = self._extract_key(request)
        if not key:
            return None  # let other auth classes try; view will 401 if none succeed

        try:
            api_key_obj = APIKey.objects.get(key=key)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key.")

        if not api_key_obj.is_active:
            raise exceptions.AuthenticationFailed("This API key has been revoked.")

        # Touch last_used_at — cheap update, fine to do every request.
        APIKey.objects.filter(pk=api_key_obj.pk).update(last_used_at=timezone.now())

        return (APIKeyUser(api_key_obj), api_key_obj)

    def authenticate_header(self, request):
        return self.keyword

    @staticmethod
    def _extract_key(request) -> str | None:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "").strip()
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() in ("bearer", "apikey"):
                return parts[1].strip()
            if len(parts) == 1:
                return parts[0].strip()
        x_header = request.META.get("HTTP_X_API_KEY", "").strip()
        if x_header:
            return x_header
        return None
