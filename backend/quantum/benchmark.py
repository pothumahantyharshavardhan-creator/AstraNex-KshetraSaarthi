"""Classical vs quantum evaluation.

Every number returned here is computed at runtime from an actual train/test run.
Nothing is hard-coded. When a benchmark has not been run yet the API returns
``status: "awaiting_benchmark"`` and the UI shows "Awaiting experimental
benchmark" instead of placeholder numbers.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Sequence

from .classical_baseline import ClassicalBaseline
from .dataset import DATA_SOURCE_LABEL, DATA_SOURCE_NOTE, build_dataset, split
from .feature_encoder import FEATURE_NAMES, select_features, to_angles
from .quantum_classifier import QuantumClassifier, quantum_runtime_status

RESULT_FILE = Path(__file__).resolve().parent / "benchmark_result.json"   # Qiskit ML (production) artifact
_HERE = Path(__file__).resolve().parent


def result_file(mode: str | None = None) -> Path:
    """Benchmark artifact for an execution mode.

    Each execution mode gets its own file, so a fallback-simulator benchmark can
    never be mistaken for (or overwrite) a genuine Qiskit Machine Learning one.
    """
    mode = mode or quantum_runtime_status()["mode"]
    if mode == "qiskit_machine_learning":
        return RESULT_FILE
    return _HERE / f"benchmark_result_{mode}.json"


def confusion(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, int]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, Any]:
    c = confusion(y_true, y_pred)
    tp, tn, fp, fn = c["tp"], c["tn"], c["fp"], c["fn"]
    total = max(1, tp + tn + fp + fn)
    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1": round(f1 * 100, 2),
        "confusion": c,
        "support": total,
    }


def _rows_to_matrix(rows: Sequence[dict[str, Any]], features: Sequence[str]):
    X = [[r["normalised"][f] for f in features] for r in rows]
    y = [int(r["label"]) for r in rows]
    return X, y


def run_benchmark(*, dataset_size: int = 360, n_qubits: int = 4, layers: int = 2,
                  iterations: int = 120, seed: int = 2026, save: bool = True,
                  progress: Any = None, require_qiskit: bool = False) -> dict[str, Any]:
    """Train both models on identical features and evaluate them on identical data.

    The benchmark runs in whichever execution mode is active and labels the result
    with what actually executed (``mode``, ``execution_label``, ``qiskit_execution``).
    ``require_qiskit=True`` additionally refuses to run unless the real Qiskit
    Machine Learning EstimatorQNN path is active (used by ``scripts/train_qiskit``).
    """
    runtime = quantum_runtime_status()
    if require_qiskit and runtime["mode"] != "qiskit_machine_learning":
        raise RuntimeError(
            "Real Qiskit Machine Learning benchmark unavailable: "
            + runtime["execution_backend"]
            + ". Install the pinned requirements and rerun training."
        )
    t_start = time.perf_counter()
    data = build_dataset(n=dataset_size, seed=seed)
    parts = split(data, test_fraction=0.3, seed=5)
    train_rows, test_rows = parts["train"], parts["test"]

    # --- feature selection on the TRAINING split only -----------------------
    train_vectors = [[r["normalised"][f] for f in FEATURE_NAMES] for r in train_rows]
    train_labels = [r["label"] for r in train_rows]
    selection = select_features(train_vectors, train_labels, k=n_qubits, names=FEATURE_NAMES)
    selected = selection["selected"]

    X_train, y_train = _rows_to_matrix(train_rows, selected)
    X_test, y_test = _rows_to_matrix(test_rows, selected)

    # --- classical baseline -------------------------------------------------
    classical = ClassicalBaseline()
    classical.features = selected
    classical.fit(X_train, y_train)
    t0 = time.perf_counter()
    c_pred = [classical.predict(row) for row in X_test]
    c_time_ms = (time.perf_counter() - t0) * 1000 / max(1, len(X_test))
    classical_metrics = metrics(y_test, c_pred)
    classical_metrics["inference_ms_per_sample"] = round(c_time_ms, 4)

    # --- quantum model (same features, same split) --------------------------
    from .pipeline import build_engine
    quantum = build_engine()
    quantum.features = selected
    angles_train = [to_angles(row) for row in X_train]
    angles_test = [to_angles(row) for row in X_test]
    training_info = quantum.fit(angles_train, y_train, iterations=iterations, progress=progress)
    t0 = time.perf_counter()
    q_pred = [quantum.predict(a) for a in angles_test]
    q_time_ms = (time.perf_counter() - t0) * 1000 / max(1, len(angles_test))
    quantum_metrics = metrics(y_test, q_pred)
    quantum_metrics["inference_ms_per_sample"] = round(q_time_ms, 4)

    runtime = quantum_runtime_status()
    try:
        circuit_info = {k: v for k, v in quantum.describe_circuit([0.5] * quantum.n_qubits).items()
                        if k != "operations"}
    except Exception:
        circuit_info = {}
    agreement = sum(1 for a, b in zip(c_pred, q_pred) if a == b) / max(1, len(q_pred))
    delta = quantum_metrics["accuracy"] - classical_metrics["accuracy"]
    if abs(delta) < 3.0:
        verdict = ("On this demonstration dataset the two models perform comparably. "
                   "No quantum advantage is demonstrated or claimed.")
    elif delta > 0:
        verdict = (f"The quantum model scored {delta:.2f} points higher on this small demonstration "
                   "dataset. This is an experimental observation on synthetic data, not evidence of "
                   "quantum advantage.")
    else:
        verdict = (f"The classical baseline scored {abs(delta):.2f} points higher on this demonstration "
                   "dataset. The quantum layer remains experimental.")

    result = {
        "status": "complete",
        "mode": runtime["mode"],
        "generated_at": time.time(),
        "evaluation_label": DATA_SOURCE_LABEL,
        "evaluation_note": DATA_SOURCE_NOTE,
        "dataset_type": "demonstration_synthetic",
        "qiskit_installed": runtime["qiskit_installed"],
        "qiskit_machine_learning_installed": runtime["qiskit_machine_learning_installed"],
        "qiskit_version": runtime["qiskit_version"],
        "qiskit_machine_learning_version": runtime["qiskit_machine_learning_version"],
        "python_version": __import__("platform").python_version(),
        "execution_backend": runtime["execution_backend"],
        "execution_label": runtime["execution_label"],
        "qiskit_execution": runtime["qiskit_execution"],
        "qubits": quantum.n_qubits,
        "quantum_engine": getattr(quantum, "engine", "builtin_vqc"),
        "model_version": 1,
        "hardware_execution": False,
        "quantum_advantage_claimed": False,
        "dataset": {
            "size": data["size"], "train": len(train_rows), "test": len(test_rows),
            "positives": data["positives"], "negatives": data["negatives"], "seed": seed,
        },
        "features": {
            "available": list(FEATURE_NAMES),
            "selected": selected,
            "ranking": selection["ranking"],
            "method": selection["method"],
        },
        "classical": {
            "model": "Logistic regression",
            "implementation": classical.implementation,
            "metrics": classical_metrics,
            "coefficients": classical.coefficients(),
            "training": classical.training_info,
        },
        "quantum": {
            "model": ("Qiskit Machine Learning VQC (ZZFeatureMap + RealAmplitudes, EstimatorQNN)"
                      if getattr(quantum, "engine", "") == "qiskit_machine_learning"
                      else f"Variational quantum classifier ({quantum.n_qubits} qubits, "
                           f"{getattr(quantum, 'layers', getattr(quantum, 'reps', layers))} layers)"),
            "engine": getattr(quantum, "engine", "builtin_vqc"),
            "feature_map": circuit_info.get("encoding") if getattr(quantum, "engine", "") != "qiskit_machine_learning" else "ZZFeatureMap",
            "ansatz": circuit_info.get("ansatz", "—"),
            "qubits": quantum.n_qubits,
            "metrics": quantum_metrics,
            "training": training_info,
            "runtime": runtime,
            "qiskit_version": runtime["qiskit_version"],
            "qiskit_machine_learning_version": runtime["qiskit_machine_learning_version"],
            "circuit": circuit_info,
            "hardware_execution": False,
            "quantum_advantage_claimed": False,
        },
        "comparison": {
            "accuracy_delta": round(delta, 2),
            "prediction_agreement": round(agreement * 100, 2),
            "verdict": verdict,
        },
        "total_seconds": round(time.perf_counter() - t_start, 3),
    }
    if save:
        if result["quantum_engine"] == "qiskit_machine_learning" and not result["qiskit_execution"]:
            raise RuntimeError("Refusing to save benchmark: labelled Qiskit ML but Qiskit did not execute")
        result_file(runtime["mode"]).write_text(json.dumps(result, indent=1), encoding="utf-8")
        quantum.training_info["dataset_metadata"] = result["dataset"]
        quantum.save()
        classical.save()
    result["_models"] = {"quantum": quantum, "classical": classical}
    return result


def load_result(mode: str | None = None) -> dict[str, Any] | None:
    """Benchmark artifact for the active (or requested) execution mode, if it is self-consistent."""
    mode = mode or quantum_runtime_status()["mode"]
    path = result_file(mode)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "complete":
            return None
        engine = data.get("quantum_engine")
        if mode == "qiskit_machine_learning":
            if data.get("qiskit_execution") is not True or engine != "qiskit_machine_learning":
                return None
        elif mode == "qiskit_statevector":
            if data.get("qiskit_execution") is not True or engine == "qiskit_machine_learning":
                return None
        else:  # fallback simulation must not claim Qiskit
            if data.get("qiskit_execution") is True:
                return None
        return data
    except Exception:
        return None


def awaiting_payload(reason: str = "No experimental benchmark has been run yet.") -> dict[str, Any]:
    empty = {"accuracy": None, "precision": None, "recall": None, "f1": None,
             "inference_ms_per_sample": None}
    return {
        "status": "awaiting_benchmark",
        "display": "Awaiting experimental benchmark",
        "reason": reason,
        "evaluation_label": DATA_SOURCE_LABEL,
        "classical": {"metrics": dict(empty)},
        "quantum": {"metrics": dict(empty)},
    }
