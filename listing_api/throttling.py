"""Per-API-key throttling.

Uses DRF's SimpleRateThrottle. Rate limits are read from the APIKey instance
(so each customer can have different limits set in admin).
"""

from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle

from .models import APIKey


class _PerKeyRateThrottle(SimpleRateThrottle):
    """Base class — subclasses set `scope` and pick the field off APIKey."""

    cache_format = "throttle_%(scope)s_%(ident)s"

    # subclass must set:
    scope: str = ""
    default_rate: str = "30/min"
    apikey_field: str = "rate_limit_per_minute"
    period: str = "min"  # used to construct the rate string from APIKey's int field

    def get_cache_key(self, request, view):
        if not hasattr(request, "auth") or not isinstance(request.auth, APIKey):
            return None  # don't throttle unauthenticated requests (auth will reject them)
        ident = str(request.auth.pk)
        return self.cache_format % {"scope": self.scope, "ident": ident}

    def get_rate(self):
        return self.default_rate

    def allow_request(self, request, view):
        # If the request is carrying an APIKey, use its per-key limit rather than the default.
        if hasattr(request, "auth") and isinstance(request.auth, APIKey):
            limit = getattr(request.auth, self.apikey_field, None)
            if isinstance(limit, int) and limit > 0:
                self.num_requests, self.duration = limit, self._duration_seconds()
                self.key = self.get_cache_key(request, view)
                if self.key is None:
                    return True
                self.history = self.cache.get(self.key, [])
                self.now = self.timer()
                while self.history and self.history[-1] <= self.now - self.duration:
                    self.history.pop()
                if len(self.history) >= self.num_requests:
                    return self.throttle_failure()
                return self.throttle_success()
        return super().allow_request(request, view)

    def _duration_seconds(self) -> int:
        return {"sec": 1, "min": 60, "hour": 3600, "day": 86400}[self.period]


class PerKeyMinuteThrottle(_PerKeyRateThrottle):
    scope = "listing_api_per_key_minute"
    apikey_field = "rate_limit_per_minute"
    period = "min"
    default_rate = "30/min"


class PerKeyDayThrottle(_PerKeyRateThrottle):
    scope = "listing_api_per_key_day"
    apikey_field = "rate_limit_per_day"
    period = "day"
    default_rate = "5000/day"
