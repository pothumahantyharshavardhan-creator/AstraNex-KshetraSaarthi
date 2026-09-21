"""Hybrid classical-quantum analysis service.

Design rule: the quantum layer is *additive*. Every function here is written so
that a failure returns a structured "unavailable" payload instead of raising,
and the classical AstraNex analysis continues untouched.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from . import benchmark as bench
from .classical_baseline import ClassicalBaseline
import os

from .feature_encoder import (
    FEATURE_LABELS, FEATURE_NAMES, FEATURE_RANGES, extract_features, feature_report,
    normalise_features, to_angles,
)
from . import qiskit_vqc
from .quantum_classifier import QuantumClassifier, quantum_runtime_status
from .quantum_state import NOISE_LEVELS, analyse_state, circuit_depth as _true_depth

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "quantum": None,
    "classical": None,
    "selected": FEATURE_NAMES[:4],
    "loaded": False,
    "training": False,
    "training_progress": None,
    "last_error": None,
    "trained_at": None,
    "mode": None,
}
_DEPTH_CACHE: dict[str, int] = {}

DEFAULT_SELECTED = ["disease_signal", "image_confidence", "heat_risk", "temperature"]


def _valid_features(feats: Any, n_qubits: int = 4) -> bool:
    return (isinstance(feats, (list, tuple)) and len(feats) == n_qubits
            and len(set(feats)) == len(feats) and all(f in FEATURE_NAMES for f in feats))


def _qml_active() -> bool:
    return quantum_runtime_status()["mode"] == "qiskit_machine_learning"


def build_engine():
    """Pick the best available quantum engine.

    Preference order: qiskit-machine-learning EstimatorQNN (only if it passed its
    self-test), then the built-in variational classifier, which itself runs through
    Qiskit's Statevector when that verifiably works and the bundled simulator otherwise.
    """
    if _qml_active():
        try:
            return qiskit_vqc.QiskitVQC()
        except Exception:
            pass
    return QuantumClassifier()


def load_engine():
    """Load a validated, trained model for the ACTIVE engine; never return random parameters.

    The saved feature set is accepted whenever it is structurally valid (feature
    selection may legitimately pick a different top-4 after a retrain), instead of
    demanding one hard-coded list, which used to discard every re-trained model on restart.
    """
    if _qml_active():
        try:
            m = qiskit_vqc.QiskitVQC.load(expected_features=None)
            return m if (m and _valid_features(m.features, m.n_qubits)) else None
        except Exception:
            return None
    try:
        m = QuantumClassifier.load()
        if m and getattr(m, "trained", False) and _valid_features(getattr(m, "features", []), m.n_qubits):
            return m
    except Exception:
        pass
    return None


def _ensure_models(auto_train: bool = False) -> bool:
    """Load persisted models; optionally train synchronously if none exist."""
    mode = quantum_runtime_status()["mode"]
    with _LOCK:
        if _STATE["loaded"] and _STATE["quantum"] is not None and _STATE.get("mode") in (None, mode):
            return True
        if _STATE.get("mode") not in (None, mode):   # engine changed underneath us -> reload
            _STATE.update({"loaded": False, "quantum": None, "classical": None})
        q = load_engine()
        c = ClassicalBaseline.load()
        saved = bench.load_result()
        if q and c and list(getattr(c, "features", [])) == list(q.features):
            _STATE.update({
                "quantum": q, "classical": c, "loaded": True, "mode": mode,
                "selected": list(q.features) or (saved or {}).get("features", {}).get("selected") or DEFAULT_SELECTED,
                "trained_at": (q.to_dict() or {}).get("saved_at"),
            })
            return True
    if auto_train:
        train_now()
        return _STATE["quantum"] is not None
    # Keep an untrained object for circuit/status rendering only. It MUST NOT be used
    # for prediction.
    with _LOCK:
        if _STATE["quantum"] is None or _STATE.get("mode") not in (None, mode):
            q = build_engine()
            q.features = list(DEFAULT_SELECTED)
            c = ClassicalBaseline()
            c.features = list(DEFAULT_SELECTED)
            _STATE.update({"quantum": q, "classical": c, "selected": list(DEFAULT_SELECTED),
                           "loaded": False, "mode": mode})
    return False


def ensure_ready(background: bool = True) -> dict[str, Any]:
    """Called at start-up: load what exists, and train the missing model automatically.

    A fresh install has no Qiskit-trained model (it cannot be shipped without running
    Qiskit), so without this the Quantum Lab would sit on "Training required" until
    somebody found the benchmark button. Disable with ASTRANEX_AUTO_TRAIN=0.
    """
    if _ensure_models():
        return {"ok": True, "status": "ready"}
    if os.getenv("ASTRANEX_AUTO_TRAIN", "1").lower() in {"0", "false", "no"}:
        return {"ok": False, "status": "training_required"}
    return train_in_background() if background else train_now()


def train_now(dataset_size: int = 360, iterations: int = 120) -> dict[str, Any]:
    """Run a full benchmark + training pass (blocking)."""
    with _LOCK:
        if _STATE["training"]:
            return {"ok": False, "status": "already_training", "progress": _STATE["training_progress"]}
        _STATE["training"] = True
        _STATE["training_progress"] = {"iteration": 0, "iterations": iterations, "loss": None}

    def progress(k, total, loss):
        _STATE["training_progress"] = {"iteration": k + 1, "iterations": total, "loss": round(loss, 5)}

    try:
        result = bench.run_benchmark(dataset_size=dataset_size, iterations=iterations, progress=progress, require_qiskit=False)
        models = result.pop("_models", {})
        with _LOCK:
            _STATE.update({
                "quantum": models.get("quantum"),
                "classical": models.get("classical"),
                "selected": result["features"]["selected"],
                "loaded": True,
                "mode": result.get("mode"),
                "trained_at": time.time(),
                "last_error": None,
            })
        return {"ok": True, "status": "complete", "benchmark": result}
    except Exception as exc:
        _STATE["last_error"] = f"{type(exc).__name__}: {exc}"
        return {"ok": False, "status": "failed", "error": _STATE["last_error"]}
    finally:
        _STATE["training"] = False


def train_in_background(dataset_size: int = 360, iterations: int = 120) -> dict[str, Any]:
    with _LOCK:
        if _STATE["training"]:
            return {"ok": True, "status": "training", "progress": _STATE["training_progress"]}
    t = threading.Thread(target=train_now, kwargs={"dataset_size": dataset_size,
                                                   "iterations": iterations}, daemon=True)
    t.start()
    return {"ok": True, "status": "started",
            "message": "Experimental training started. Metrics appear when the run completes."}


def training_state() -> dict[str, Any]:
    return {
        "training": bool(_STATE["training"]),
        "progress": _STATE["training_progress"],
        "models_trained": bool(_STATE["loaded"]),
        "trained_at": _STATE["trained_at"],
        "last_error": _STATE["last_error"],
    }


def _encoding_label(q) -> str:
    if getattr(q, "engine", "") == "qiskit_machine_learning":
        return "ZZFeatureMap (Qiskit) \u2014 second-order Pauli-Z feature map"
    return "Angle encoding \u2014 one RY rotation per feature"


def _ansatz_label(q) -> str:
    if getattr(q, "engine", "") == "qiskit_machine_learning":
        return "RealAmplitudes (Qiskit), circular entanglement"
    return "RY/RZ variational layers with an alternating CX ring"


def _circuit_depth_for(q, angles) -> int | None:
    key = f"{getattr(q, 'engine', '?')}:{getattr(q, 'n_qubits', 0)}"
    if key not in _DEPTH_CACHE:
        try:
            _DEPTH_CACHE[key] = int(q.describe_circuit(angles).get("circuit_depth") or 0)
        except Exception:
            return None
    return _DEPTH_CACHE[key]


def quantum_status() -> dict[str, Any]:
    _ensure_models()
    runtime = quantum_runtime_status()
    saved = bench.load_result()
    q = _STATE["quantum"]
    return {
        "available": True,
        "layer": "experimental",
        "runtime": runtime,
        "circuit": {
            "qubits": q.n_qubits,
            "layers": getattr(q, "layers", getattr(q, "reps", 2)),
            "parameters": len(q.weights),
            "encoding": _encoding_label(q),
            "engine": getattr(q, "engine", "builtin_vqc"),
            "backend": runtime["execution_backend"],
            "execution_label": runtime["execution_label"],
            "qiskit_execution": runtime["qiskit_execution"],
            "status": "Experimental",
        },
        "models_trained": bool(_STATE["loaded"]),
        "model_status": "trained" if _STATE["loaded"] else "not_trained",
        "inference_enabled": bool(_STATE["loaded"]),
        "inference_message": None if _STATE["loaded"] else "Quantum model unavailable — Training required before QML inference",
        "selected_features": _STATE["selected"],
        "feature_labels": {k: FEATURE_LABELS[k] for k in FEATURE_NAMES},
        "benchmark_available": saved is not None,
        "benchmark_generated_at": (saved or {}).get("generated_at"),
        "training": training_state(),
        "claims": [
            "Simulator execution only - no quantum hardware is used.",
            "No quantum advantage is claimed or demonstrated.",
            "Benchmarks run on a labelled demonstration dataset, not field-validated data.",
        ],
    }


def _seed_from(vector) -> int:
    return int(sum((i + 1) * float(v) * 1009 for i, v in enumerate(vector))) % 1_000_003


def _state_or_none(q, angles, shots: int = 1024, seed: int | None = None):
    """Physical read-out of the circuit's state, or None if the engine cannot supply one."""
    try:
        amps = q.statevector(angles)
        return analyse_state(amps, q.n_qubits, shots=shots, seed=_seed_from(angles) if seed is None else seed)
    except Exception:
        return None


def circuit_blueprint(angles: list[float] | None = None) -> dict[str, Any]:
    _ensure_models()
    q = _STATE["quantum"]
    angles = angles or [0.9, 1.6, 1.2, 0.6]
    info = q.describe_circuit(angles)
    info["qubit_map"] = [
        {"qubit": i, "feature": _STATE["selected"][i] if i < len(_STATE["selected"]) else None,
         "label": FEATURE_LABELS.get(_STATE["selected"][i], "\u2014") if i < len(_STATE["selected"]) else "\u2014",
         "angle_rad": round(angles[i], 4) if i < len(angles) else None}
        for i in range(q.n_qubits)
    ]
    try:
        info["measurement_distribution"] = q.measurement_distribution(angles)
    except Exception:
        info["measurement_distribution"] = []
    info["state"] = _state_or_none(q, angles)
    info["encoding_label"] = _encoding_label(q)
    info["ansatz_label"] = _ansatz_label(q)
    info["trained"] = bool(_STATE["loaded"])
    return info


def system_health() -> dict[str, Any]:
    """One consolidated, honestly-reported status for every subsystem.

    Every entry is measured at call time — nothing here is a hard-coded "OK".
    A component that cannot be checked from this module (frontend, database)
    is checked by the caller in ``main.py`` and merged in; this function
    covers everything the quantum package can see for itself.
    """
    rt = quantum_runtime_status()
    _ensure_models()
    saved_bench = bench.load_result()
    q = _STATE.get("quantum")
    c = _STATE.get("classical")

    components: dict[str, dict[str, Any]] = {
        "qiskit": {
            "ok": rt["qiskit_installed"],
            "detail": rt["qiskit_version"] or "not installed",
        },
        "qiskit_machine_learning": {
            "ok": rt["qiskit_machine_learning_installed"],
            "detail": rt["qiskit_machine_learning_version"] or "not installed",
        },
        "classical_model": {
            "ok": bool(c and (c.trained or c.weights)),
            "detail": (c.implementation if c else "not initialised"),
        },
        "qml_model": {
            "ok": bool(q and getattr(q, "trained", False)),
            "detail": f"{getattr(q, 'engine', 'unknown')} · " + ("trained" if q and getattr(q, "trained", False) else "untrained parameters"),
        },
        "benchmark": {
            "ok": saved_bench is not None and saved_bench.get("status") == "complete",
            "detail": "available" if saved_bench else "not yet run — POST /api/quantum/benchmark",
        },
        "quantum_engine_selected": {
            "ok": True,
            "detail": f"{rt['mode']} ({rt['execution_label']})",
        },
    }
    all_ok_that_matter = components["classical_model"]["ok"] or components["qml_model"]["ok"]
    return {
        "components": components,
        "runtime": rt,
        "overall": "ok" if all_ok_that_matter else "degraded",
        "note": "Qiskit and Qiskit Machine Learning being unavailable is a supported, honestly-reported "
                "state, not a failure: the fallback simulator keeps the demo working.",
    }


def model_provenance() -> dict[str, Any]:
    """Everything needed to answer 'where did this number come from'."""
    _ensure_models()
    rt = quantum_runtime_status()
    q = _STATE.get("quantum")
    c = _STATE.get("classical")
    saved_bench = bench.load_result()
    return {
        "dataset": {
            "type": "demonstration_synthetic",
            "label": "Synthetic Demonstration Data — NOT field-validated ground truth",
            "note": ("Scenarios are synthetic but processed by the real AstraNex risk engine. "
                     "Labels are a forward-weather outbreak proxy, not verified outbreak records."),
        },
        "features": {
            "available": list(FEATURE_NAMES),
            "selected": _STATE.get("selected", []),
            "selection_method": (saved_bench or {}).get("features", {}).get("method"),
            "normalisation": "min-max to [0, 1] using physical ranges in FEATURE_RANGES",
        },
        "classical_model": {
            "algorithm": "Logistic regression",
            "implementation": c.implementation if c else None,
            "trained": bool(c and (c.trained or c.weights)),
        },
        "quantum_model": {
            "engine": getattr(q, "engine", "builtin_vqc"),
            "feature_map": "ZZFeatureMap" if getattr(q, "engine", "") == "qiskit_machine_learning" else "Angle encoding (RY)",
            "ansatz": ("RealAmplitudes" if getattr(q, "engine", "") == "qiskit_machine_learning"
                       else "Custom RY/RZ variational block with alternating CX ring"),
            "encoding_label": _encoding_label(q),
            "ansatz_label": _ansatz_label(q),
            "qubits": getattr(q, "n_qubits", 4),
            "layers": getattr(q, "layers", getattr(q, "reps", 2)),
            "parameters": len(getattr(q, "weights", [])),
            "trained": bool(q and getattr(q, "trained", False)),
            "training": getattr(q, "training_info", {}),
        },
        "runtime": {
            "engine_label": rt["execution_label"],
            "qiskit_execution": rt["qiskit_execution"],
            "hardware": "Simulation only",
            "qiskit_version": rt["qiskit_version"],
            "qiskit_machine_learning_version": rt["qiskit_machine_learning_version"],
        },
        "validation": "Not field validated. Experimental evaluation on synthetic demonstration data only.",
        "quantum_advantage_claimed": False,
        "benchmark_available": saved_bench is not None,
    }


def _warning_level(prob: float, disease_risk: float) -> dict[str, Any]:
    score = 0.6 * prob * 100 + 0.4 * disease_risk
    if score >= 68:
        return {"level": "EARLY WARNING", "color": "red",
                "action": "Scout the block today. Inspect several plants across the field and confirm locally before any treatment."}
    if score >= 42:
        return {"level": "MONITOR", "color": "amber",
                "action": "Re-scan in 24-48 hours and watch humidity and leaf wetness."}
    return {"level": "STABLE", "color": "green",
            "action": "Continue routine scouting. No early-warning signal at present."}


def hybrid_analyze(result: dict | None = None, raw: dict | None = None) -> dict[str, Any]:
    """Run the experimental hybrid layer over an AstraNex analysis result.

    Returns a payload that always contains ``available``; on any failure the
    caller keeps its classical result untouched.
    """
    started = time.perf_counter()
    try:
        models_ready = _ensure_models()
        q = _STATE["quantum"]
        c: ClassicalBaseline = _STATE["classical"]
        selected = _STATE["selected"]

        if not models_ready or not _STATE["loaded"] or q is None or not getattr(q, "trained", False):
            return {
                "available": False,
                "status": "model_unavailable",
                "error": "Quantum model unavailable",
                "message": "Training required before QML inference",
                "models_trained": False,
                "inference_enabled": False,
                "runtime": quantum_runtime_status(),
                "total_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        if list(getattr(q, "features", [])) != list(selected):
            return {
                "available": False,
                "status": "model_validation_failed",
                "error": "Quantum model architecture does not match the active feature pipeline",
                "message": "Inference blocked until the QML model is retrained with the current feature order",
                "models_trained": False,
                "inference_enabled": False,
                "runtime": quantum_runtime_status(),
                "total_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        if hasattr(q, "validate"):
            ok, errors = q.validate(expected_features=selected)
            if not ok:
                return {
                    "available": False,
                    "status": "model_validation_failed",
                    "error": "Stored quantum model failed validation",
                    "validation_errors": errors,
                    "message": "Inference blocked until the QML model is retrained",
                    "models_trained": False,
                    "inference_enabled": False,
                    "runtime": quantum_runtime_status(),
                    "total_ms": round((time.perf_counter() - started) * 1000, 3),
                }

        features = extract_features(result, raw)
        normalised = normalise_features(features)
        vector = [normalised[f] for f in selected]
        angles = to_angles(vector)

        t0 = time.perf_counter()
        q_prob, expectations = q.forward(angles)
        q_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        c_prob = c.predict_proba(vector) if c.trained or c.weights else None
        c_ms = (time.perf_counter() - t0) * 1000

        disease_risk = float((result or {}).get("risks", {}).get("disease", 0) or 0)
        warning = _warning_level(q_prob, disease_risk)
        agreement = None
        if c_prob is not None:
            agreement = bool((q_prob >= 0.5) == (c_prob >= 0.5))

        return {
            "available": True,
            "experimental": True,
            "models_trained": bool(_STATE["loaded"]),
            "untrained_note": None if _STATE["loaded"] else
                "Models are at their initial parameters. Run an experimental training pass for meaningful probabilities.",
            "features": {
                "vector": feature_report(features, selected),
                "selected": selected,
                "angles_rad": angles,
                "encoding": _encoding_label(q) + " \u00b7 feature \u2192 angle in [0, \u03c0]",
            },
            "quantum": {
                "risk_probability": round(q_prob * 100, 2),
                "expectations": [round(e, 5) for e in expectations],
                "inference_ms": round(q_ms, 3),
                "backend": quantum_runtime_status()["execution_backend"],
                "qubits": q.n_qubits,
                "layers": getattr(q, "layers", getattr(q, "reps", 2)),
                "execution_label": quantum_runtime_status()["execution_label"],
            },
            "classical": {
                "risk_probability": round(c_prob * 100, 2) if c_prob is not None else None,
                "inference_ms": round(c_ms, 3),
                "model": "Logistic regression",
            },
            "comparison": {
                "agreement": agreement,
                "delta": round((q_prob - c_prob) * 100, 2) if c_prob is not None else None,
                "note": "Both models consume the same selected feature vector.",
            },
            "early_warning": warning,
            "circuit": {
                "qubits": q.n_qubits, "layers": getattr(q, "layers", getattr(q, "reps", 2)),
                "parameters": len(q.weights),
                "encoding": _encoding_label(q), "status": "Experimental",
                "depth": _circuit_depth_for(q, angles),
                "engine": getattr(q, "engine", "builtin_vqc"),
                "backend": quantum_runtime_status()["execution_backend"],
                "execution_label": quantum_runtime_status()["execution_label"],
                "qiskit_execution": quantum_runtime_status()["qiskit_execution"],
            },
            "state": _state_or_none(q, angles),
            "total_ms": round((time.perf_counter() - started) * 1000, 3),
            "disclaimer": "Experimental quantum layer. Simulation only; not a validated diagnosis.",
        }
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}",
            "message": "Quantum layer unavailable. Classical agricultural analysis continues normally.",
            "total_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def feature_ranges() -> dict[str, Any]:
    """Selected features with physical ranges, for the interactive playground."""
    _ensure_models()
    q = _STATE["quantum"]
    selected = list(_STATE["selected"])[: getattr(q, "n_qubits", 4)]
    return {
        "selected": selected,
        "features": [{"qubit": i, "name": n, "label": FEATURE_LABELS.get(n, n),
                      "min": FEATURE_RANGES[n][0], "max": FEATURE_RANGES[n][1]}
                     for i, n in enumerate(selected)],
        "trained": bool(_STATE["loaded"]),
    }


def simulate(values: list[float], shots: int = 1024, seed: int | None = None) -> dict[str, Any]:
    """Interactive what-if: run the circuit on hand-chosen normalised features.

    Returns the exact state analysis (Bloch vectors, entanglement, probabilities,
    finite-shot counts). If the models are trained it also returns both risk
    predictions and a depolarising-noise sweep. Nothing is stored.
    """
    started = time.perf_counter()
    trained = _ensure_models()
    q = _STATE["quantum"]
    selected = list(_STATE["selected"])
    n = q.n_qubits
    if len(values) != n:
        raise ValueError(f"expected {n} feature values, got {len(values)}")
    vec = [max(0.0, min(1.0, float(v))) for v in values]
    angles = to_angles(vec)
    amps = q.statevector(angles)
    st = analyse_state(amps, n, shots=shots, seed=_seed_from(vec) if seed is None else int(seed))
    rt = quantum_runtime_status()
    inputs = []
    for i in range(n):
        name = selected[i] if i < len(selected) else None
        lo, hi = FEATURE_RANGES.get(name, (0.0, 1.0))
        inputs.append({"qubit": i, "feature": name, "label": FEATURE_LABELS.get(name, "\u2014"),
                       "normalised": round(vec[i], 4), "value": round(lo + vec[i] * (hi - lo), 2),
                       "angle_rad": round(angles[i], 4)})
    out: dict[str, Any] = {
        "available": True, "trained": bool(trained and getattr(q, "trained", False)),
        "inputs": inputs, "angles_rad": [round(a, 5) for a in angles], "state": st,
        "circuit_depth": _circuit_depth_for(q, angles),
        "runtime": {k: rt[k] for k in ("mode", "execution_backend", "execution_label", "qiskit_execution", "hardware_execution")},
        "engine": getattr(q, "engine", "builtin_vqc"),
        "encoding": _encoding_label(q), "ansatz": _ansatz_label(q),
    }
    if out["trained"]:
        c = _STATE["classical"]
        q_prob, exps = q.forward(angles)
        c_prob = c.predict_proba(vec) if (c.trained or c.weights) else None
        disease = None
        if "disease_signal" in selected:
            k = selected.index("disease_signal")
            disease = FEATURE_RANGES["disease_signal"][0] + vec[k] * (FEATURE_RANGES["disease_signal"][1] - FEATURE_RANGES["disease_signal"][0])
        out["quantum"] = {"risk_probability": round(q_prob * 100, 2), "expectations": [round(e, 5) for e in exps]}
        out["classical"] = {"risk_probability": round(c_prob * 100, 2) if c_prob is not None else None}
        out["early_warning"] = _warning_level(q_prob, disease if disease is not None else q_prob * 100)
        sweep = []
        for p in NOISE_LEVELS:
            try:
                sweep.append({"noise": p, "risk_probability": round(q.noisy_probability(angles, p) * 100, 2)})
            except Exception:
                break
        out["noise_sweep"] = {
            "model": "global depolarising channel on the output state (simplified NISQ noise model)",
            "note": "Simulated noise only - not a measurement from quantum hardware.",
            "points": sweep,
        }
    else:
        out["message"] = "Model not trained yet: state analysis is exact, but no risk prediction is shown."
    out["total_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return out
