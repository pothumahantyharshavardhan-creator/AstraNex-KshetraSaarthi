"""Unified Data Quality / confidence layer (v3.3).

This is deliberately NOT an "agricultural accuracy" score. It only describes
how trustworthy the *inputs* to an analysis were: how complete they are, how
fresh the sensor readings are, how reliable the sensors have been, how usable
the plant image was, and whether the environmental readings are internally
consistent. The agricultural engine's own confidence numbers (vision
confidence, context confidence, model confidence) are separate and are not
recomputed here.

Nothing in this module invents or validates agronomic accuracy.
"""
from __future__ import annotations

REQUIRED_FIELDS = ("soil_moisture", "temperature", "humidity")
STALE_AFTER_SECONDS = 30 * 60  # a reading older than 30 minutes is "stale" for a live field view


def _band(score: float) -> str:
    if score >= 80:
        return "GOOD"
    if score >= 55:
        return "FAIR"
    return "POOR"


def _completeness(context: dict) -> tuple[float, list[str]]:
    present = [f for f in REQUIRED_FIELDS if context.get(f) is not None]
    missing = [f for f in REQUIRED_FIELDS if context.get(f) is None]
    score = 100.0 * len(present) / len(REQUIRED_FIELDS)
    notes = [f"Missing {m.replace('_', ' ')} reading." for m in missing]
    return score, notes


def _freshness(recorded_at: float | None, now: float | None) -> tuple[float, list[str]]:
    if recorded_at is None or now is None:
        return 60.0, ["No timestamp supplied for the sensor reading; freshness is unknown."]
    age = max(0.0, now - recorded_at)
    if age <= 5 * 60:
        return 100.0, []
    if age <= STALE_AFTER_SECONDS:
        return 75.0, []
    minutes = round(age / 60)
    return 30.0, [f"Latest sensor reading is {minutes} minutes old; treat as stale."]


def _reliability(sensor_reliability: float | None, anomalies: list[str] | None) -> tuple[float, list[str]]:
    notes = []
    base = 100.0 * (sensor_reliability if sensor_reliability is not None else 1.0)
    if anomalies:
        base = min(base, 40.0)
        notes.append("Sensor anomaly flags reduce reliability confidence.")
    return max(0.0, min(100.0, base)), notes


def _image_quality(image_quality: float | None) -> tuple[float, list[str]]:
    if image_quality is None:
        return 100.0, []
    score = 100.0 * max(0.0, min(1.0, image_quality))
    notes = []
    if score < 60:
        notes.append("Plant image quality is below the reliable-analysis threshold.")
    return score, notes


def _environmental_consistency(context: dict) -> tuple[float, list[str]]:
    """Flags combinations that are individually valid but jointly implausible."""
    notes = []
    score = 100.0
    m, t, h = context.get("soil_moisture"), context.get("temperature"), context.get("humidity")
    weather = (context.get("weather") or "").lower()
    rainfall = context.get("recent_rainfall_mm")
    if m is not None and weather == "drought" and m >= 85:
        score -= 35
        notes.append("Very high soil moisture reported during a configured drought — check the sensor.")
    if h is not None and t is not None and h <= 5 and t is not None and t >= 45:
        score -= 20
        notes.append("Extremely low humidity with extreme heat is an unusual combination for most fields.")
    if rainfall is not None and rainfall >= 20 and m is not None and m <= 10:
        score -= 25
        notes.append("Heavy recent rainfall but very low soil moisture — verify the moisture sensor.")
    return max(0.0, score), notes


def compute_data_quality(
    context: dict,
    *,
    sensor_reliability: float | None = None,
    image_quality: float | None = None,
    model_confidence: float | None = None,
    sensor_anomalies: list[str] | None = None,
    recorded_at: float | None = None,
    now: float | None = None,
) -> dict:
    """Compute the unified Data Quality Score described in the v3.3 spec.

    Returns a dict with an overall 0-100 score, a qualitative band, the
    weighted component breakdown, and plain-language notes. This score
    describes *input trustworthiness*, never agricultural accuracy.
    """
    completeness, c_notes = _completeness(context)
    freshness, f_notes = _freshness(recorded_at, now)
    reliability, r_notes = _reliability(sensor_reliability, sensor_anomalies)
    img_quality, i_notes = _image_quality(image_quality)
    consistency, e_notes = _environmental_consistency(context)

    weights = {
        "completeness": 0.25,
        "freshness": 0.20,
        "reliability": 0.25,
        "image_quality": 0.10,
        "environmental_consistency": 0.20,
    }
    components = {
        "completeness": completeness,
        "freshness": freshness,
        "reliability": reliability,
        "image_quality": img_quality,
        "environmental_consistency": consistency,
    }
    overall = sum(components[k] * w for k, w in weights.items())
    overall = round(max(0.0, min(100.0, overall)), 1)
    band = _band(overall)

    notes = c_notes + f_notes + r_notes + i_notes + e_notes
    if not notes:
        notes = ["Most required sensor values are recent, complete and internally consistent."]

    explanation = {
        "GOOD": "Good quality — most required sensor values are recent and consistent.",
        "FAIR": "Fair quality — some inputs are incomplete, stale, or inconsistent; treat the analysis as indicative.",
        "POOR": "Poor quality — key inputs are missing, stale, or inconsistent; verify sensors before acting on this analysis.",
    }[band]

    return {
        "score": overall,
        "band": band,
        "explanation": explanation,
        "components": {k: round(v, 1) for k, v in components.items()},
        "weights": weights,
        "notes": notes,
        "label": "data_quality",  # explicit: this is NOT an agricultural-accuracy metric
    }
