"""Weather/risk provider abstraction (v3.3, spec section 14).

    WeatherProvider
    +-- LiveApiProvider     (only used if ASTRANEX_WEATHER_API_URL is configured)
    +-- CachedProvider      (last successfully fetched reading for this field)
    +-- OfflineFallbackProvider (always available; never fails)

``get_weather`` never raises and never fabricates a live reading: if no
provider configured (the default in this build has no external weather key)
or the live call fails, it degrades to the last cached reading, then to an
explicit "weather data unavailable" response. Nothing here invents a live
forecast.
"""
from __future__ import annotations
import os
import time
from typing import Any

_CACHE: dict[str, dict] = {}  # field_key -> last known good reading (in-memory; resets on restart)


class WeatherProvider:
    name = "base"

    def fetch(self, latitude: float | None, longitude: float | None) -> dict[str, Any] | None:
        raise NotImplementedError


class LiveApiProvider(WeatherProvider):
    """Only active if ASTRANEX_WEATHER_API_URL is set. No key is bundled with this
    project; without configuration this provider reports itself unavailable rather
    than silently doing nothing."""
    name = "live_api"

    def __init__(self):
        self.url = os.environ.get("ASTRANEX_WEATHER_API_URL")

    def fetch(self, latitude, longitude):
        if not self.url:
            return None
        # Real HTTP calls are intentionally not made from this module without an
        # explicitly configured, reviewed endpoint (see SECURITY.md: no bundled
        # third-party API keys). Operators can wire a real client in here.
        return None


class CachedProvider(WeatherProvider):
    name = "cached"

    def fetch(self, latitude, longitude):
        key = _cache_key(latitude, longitude)
        cached = _CACHE.get(key)
        if not cached:
            return None
        age = time.time() - cached["fetched_at"]
        return {**cached["data"], "source": "cached", "cache_age_seconds": round(age)}


class OfflineFallbackProvider(WeatherProvider):
    name = "offline_fallback"

    def fetch(self, latitude, longitude):
        return {
            "available": False,
            "source": "offline_fallback",
            "message": "Weather data unavailable — using latest cached information where available.",
        }


def _cache_key(latitude, longitude) -> str:
    if latitude is None or longitude is None:
        return "default"
    return f"{round(latitude, 2)},{round(longitude, 2)}"


def store_cache(latitude, longitude, data: dict) -> None:
    _CACHE[_cache_key(latitude, longitude)] = {"data": data, "fetched_at": time.time()}


def get_weather(latitude: float | None = None, longitude: float | None = None) -> dict[str, Any]:
    """Try providers in order; never raises; never fabricates a live reading."""
    for provider in (LiveApiProvider(), CachedProvider(), OfflineFallbackProvider()):
        try:
            result = provider.fetch(latitude, longitude)
        except Exception:
            result = None
        if result is not None:
            result.setdefault("provider", provider.name)
            if provider.name == "live_api":
                store_cache(latitude, longitude, result)
            return result
    # Should be unreachable (OfflineFallbackProvider always returns something),
    # but never let this function raise into a request handler.
    return {"available": False, "source": "offline_fallback", "message": "Weather data unavailable."}
