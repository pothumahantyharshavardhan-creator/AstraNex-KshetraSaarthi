"""Experimental quantum circuit sensitivity (v3.3, spec section 22).

For each selected input feature this perturbs it by a fixed delta, re-runs
the circuit via :func:`backend.quantum.pipeline.simulate`, and records how
much the circuit's output changed. This is labelled, deliberately and
repeatedly, as an *experimental circuit sensitivity* measurement — it is
NOT validated feature importance in the statistical/ML sense, and callers
must not present it as such.
"""
from __future__ import annotations
from typing import Any

from . import pipeline


def _output_metric(sim_result: dict[str, Any]) -> float:
    """A single scalar to compare across perturbations.

    Uses the trained quantum risk probability when a model is trained (the
    quantity the app actually reports to a user), and otherwise falls back
    to the top computational-basis-state probability so the experiment still
    runs on an untrained/fresh install.
    """
    if sim_result.get("trained") and sim_result.get("quantum"):
        return float(sim_result["quantum"]["risk_probability"])
    top = sim_result.get("state", {}).get("top_states") or []
    return float(top[0]["probability"]) * 100 if top else 0.0


def feature_sensitivity(base_values: list[float], delta: float = 0.15, shots: int = 256) -> dict[str, Any]:
    """Run the experimental circuit-sensitivity sweep.

    ``base_values`` are the normalised [0,1] feature values currently loaded
    in the quantum pipeline (same convention as ``pipeline.simulate``).
    """
    baseline = pipeline.simulate(list(base_values), shots=shots)
    base_metric = _output_metric(baseline)
    inputs = baseline.get("inputs", [])

    results = []
    for i, meta in enumerate(inputs):
        perturbed = list(base_values)
        perturbed[i] = max(0.0, min(1.0, perturbed[i] + delta))
        if perturbed[i] == base_values[i]:
            # Already at the boundary; perturb the other direction instead.
            perturbed[i] = max(0.0, min(1.0, base_values[i] - delta))
        probe = pipeline.simulate(perturbed, shots=shots)
        probe_metric = _output_metric(probe)
        sensitivity = round(abs(probe_metric - base_metric), 4)
        results.append({
            "feature": meta.get("feature"),
            "label": meta.get("label"),
            "qubit": meta.get("qubit"),
            "base_value": base_values[i],
            "perturbed_value": perturbed[i],
            "output_delta": sensitivity,
        })

    results.sort(key=lambda r: r["output_delta"], reverse=True)
    max_delta = max((r["output_delta"] for r in results), default=0.0)
    for r in results:
        r["relative_sensitivity"] = round(r["output_delta"] / max_delta, 4) if max_delta > 0 else 0.0

    return {
        "label": "Experimental circuit sensitivity",
        "disclaimer": (
            "This is an experimental circuit-sensitivity sweep, NOT scientific or statistically "
            "validated feature importance. It only shows how much this simulated circuit's output "
            "moved when one input was perturbed by the configured delta."
        ),
        "perturbation_delta": delta,
        "shots": shots,
        "baseline_metric": round(base_metric, 4),
        "trained": bool(baseline.get("trained")),
        "results": results,
    }
