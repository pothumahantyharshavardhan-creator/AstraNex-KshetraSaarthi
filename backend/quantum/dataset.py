"""Experimental dataset for the QML layer.

HONESTY NOTE (read before quoting any number produced from this file)
---------------------------------------------------------------------
This is **not** a field-validated outbreak dataset. There is no labelled
multispectral drone corpus in this prototype. What this module builds is a
reproducible *demonstration* dataset:

* Inputs are agronomically plausible field scenarios (crop, soil moisture,
  temperature, humidity, weather, rainfall, sensor reliability, image quality).
* Every feature vector is produced by running the **real existing AstraNex
  engine** over that scenario - the same code path a live scan uses.
* The label is a forward-looking "outbreak within the next few days" proxy that
  depends on latent forward weather which is deliberately *not* given to either
  model. That makes the task a genuine (noisy, non-trivial) learning problem
  rather than a lookup of one input column.

Any metric computed on this dataset is therefore labelled
"Demonstration / Experimental Evaluation" everywhere in the UI and API.
"""
from __future__ import annotations

import random
from typing import Any

from ..engine import AnalysisInput, analyze_field
from .feature_encoder import FEATURE_NAMES, extract_features, normalise_features

DATA_SOURCE_LABEL = "Demonstration / Experimental Evaluation"
DATA_SOURCE_NOTE = (
    "Scenarios are synthetic but are processed by the real AstraNex risk engine. "
    "Labels are a forward-weather outbreak proxy, not field-verified ground truth. "
    "No field validation has been performed."
)

CROPS = ["tomato", "paddy", "chilli", "cotton", "maize", "groundnut", "brinjal", "turmeric"]
CONDITIONS = ["healthy", "healthy", "diseaseA", "diseaseB", "yellowing", "holes", "unknown"]
WEATHERS = ["normal", "normal", "humid", "heat", "drought", "flood"]
STAGES = ["seedling", "vegetative", "flowering", "fruiting"]


def _scenario(rng: random.Random) -> dict[str, Any]:
    weather = rng.choice(WEATHERS)
    soil = rng.uniform(8, 92)
    temp = rng.uniform(16, 43)
    hum = rng.uniform(22, 96)
    rain = rng.choice([0, 0, 0, rng.uniform(1, 12), rng.uniform(12, 45)])
    if weather == "flood":
        soil = min(100, soil + rng.uniform(10, 25)); rain = max(rain, rng.uniform(18, 60))
    if weather == "drought":
        soil = max(0, soil - rng.uniform(10, 25)); rain = 0
    if weather == "heat":
        temp = min(50, temp + rng.uniform(3, 8))
    return {
        "crop": rng.choice(CROPS),
        "condition": rng.choice(CONDITIONS),
        "growth_stage": rng.choice(STAGES),
        "soil_moisture": round(soil, 1),
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "weather": weather if weather != "humid" else "normal",
        "recent_rainfall_mm": round(float(rain), 1),
        "recent_irrigation_hours": round(rng.uniform(1, 96), 1),
        "sensor_reliability": round(rng.choice([1.0, 1.0, 0.92, 0.75, 0.5, 0.35]), 2),
        "image_quality": round(rng.choice([1.0, 1.0, 0.9, 0.72, 0.55]), 2),
    }


def _outbreak_label(scenario: dict[str, Any], result: dict[str, Any], rng: random.Random) -> tuple[int, float]:
    """Forward-looking outbreak proxy.

    Uses latent near-future weather (not exposed to the models) plus host
    susceptibility, so the models must generalise from present-day signals.
    """
    risks = result.get("risks", {})
    disease = float(risks.get("disease", 0)) / 100.0
    water = float(risks.get("water", 0)) / 100.0
    heat = float(risks.get("heat", 0)) / 100.0
    excess = float(risks.get("excess_water", 0)) / 100.0

    # Latent forward weather over the next few days (never given to the models).
    fwd_humidity = min(100.0, max(0.0, scenario["humidity"] + rng.gauss(4, 11)))
    fwd_rain = max(0.0, scenario["recent_rainfall_mm"] * rng.uniform(0.3, 1.5) + rng.gauss(2, 6))
    fwd_leaf_wetness = (fwd_humidity / 100.0) * (0.55 + min(1.0, fwd_rain / 25.0) * 0.45)
    thermal_fit = max(0.0, 1.0 - abs(scenario["temperature"] - 27.5) / 16.0)

    pressure = (
        0.42 * disease
        + 0.26 * fwd_leaf_wetness * thermal_fit
        + 0.12 * excess
        + 0.10 * max(water, heat)          # stressed plants are more susceptible
        + 0.10 * (1.0 if scenario["condition"] in {"diseaseA", "diseaseB", "holes"} else 0.0)
    )
    pressure += rng.gauss(0, 0.045)        # irreducible field noise
    return (1 if pressure >= 0.42 else 0), round(pressure, 4)


def build_dataset(n: int = 360, seed: int = 2026) -> dict[str, Any]:
    """Build the evaluation dataset. Deterministic for a given (n, seed)."""
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for _ in range(n):
        sc = _scenario(rng)
        result = analyze_field(AnalysisInput(**sc))
        feats = extract_features(result, sc)
        label, pressure = _outbreak_label(sc, result, rng)
        rows.append({
            "scenario": sc,
            "features": feats,
            "normalised": normalise_features(feats),
            "label": label,
            "pressure": pressure,
        })
    positives = sum(r["label"] for r in rows)
    return {
        "rows": rows,
        "size": len(rows),
        "positives": positives,
        "negatives": len(rows) - positives,
        "seed": seed,
        "feature_names": list(FEATURE_NAMES),
        "source": DATA_SOURCE_LABEL,
        "note": DATA_SOURCE_NOTE,
    }


def split(dataset: dict[str, Any], test_fraction: float = 0.3, seed: int = 5) -> dict[str, Any]:
    """Deterministic stratified train/test split."""
    rng = random.Random(seed)
    pos = [r for r in dataset["rows"] if r["label"] == 1]
    neg = [r for r in dataset["rows"] if r["label"] == 0]
    rng.shuffle(pos)
    rng.shuffle(neg)
    n_pos_test = int(len(pos) * test_fraction)
    n_neg_test = int(len(neg) * test_fraction)
    test = pos[:n_pos_test] + neg[:n_neg_test]
    train = pos[n_pos_test:] + neg[n_neg_test:]
    rng.shuffle(test)
    rng.shuffle(train)
    return {"train": train, "test": test, "test_fraction": test_fraction, "seed": seed}
