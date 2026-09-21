"""Configurable crop profiles (v3.3, spec sections 17-18).

Profiles live as plain JSON under ``config/crops/`` so they can be reviewed,
extended, or corrected without touching application logic. If a crop or
growth stage isn't configured, callers must fall back to explicit
"guidance unavailable" behaviour rather than guessing — this module never
invents an agronomic threshold that wasn't supplied in a profile file.
"""
from __future__ import annotations
from pathlib import Path
import json

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "crops"

_cache: dict[str, dict] | None = None


def _load_all() -> dict[str, dict]:
    global _cache
    if _cache is not None:
        return _cache
    profiles: dict[str, dict] = {}
    if CONFIG_DIR.exists():
        for path in sorted(CONFIG_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                name = str(data.get("crop") or path.stem).strip().lower()
                profiles[name] = data
            except (json.JSONDecodeError, OSError):
                continue
    _cache = profiles
    return profiles


def list_crops() -> list[str]:
    return sorted(_load_all().keys())


def get_profile(crop: str) -> dict | None:
    return _load_all().get((crop or "").strip().lower())


def moisture_threshold(crop: str, growth_stage: str, default: float = 40.0) -> float:
    """Configured soil-moisture decision threshold for a crop/stage.

    Falls back to ``default`` (matching the v3.2 hardcoded behaviour) when
    the crop or growth stage isn't configured, so existing behaviour for
    unconfigured crops never changes.
    """
    profile = get_profile(crop)
    if not profile:
        return default
    table = profile.get("soil_moisture_threshold_pct", {})
    return float(table.get((growth_stage or "").strip().lower(), default))


def stage_supported(crop: str, growth_stage: str) -> bool:
    profile = get_profile(crop)
    if not profile:
        return False
    stages = [s.lower() for s in profile.get("growth_stages", [])]
    return (growth_stage or "").strip().lower() in stages


def reset_cache() -> None:
    """Test helper: force profiles to be re-read from disk on next access."""
    global _cache
    _cache = None
