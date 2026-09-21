"""Genuine Qiskit Machine Learning execution path.

This module builds a real variational quantum classifier out of the official
Qiskit ecosystem:

    ZZFeatureMap(4 qubits)  →  RealAmplitudes(4 qubits, 2 reps)  →  ⟨Z⊗Z⊗Z⊗Z⟩
    wrapped in qiskit_machine_learning.neural_networks.EstimatorQNN

If ``qiskit`` and ``qiskit_machine_learning`` are installed, this is what runs and
``execution_backend`` says so. If either import fails, this module reports itself
unavailable and :mod:`backend.quantum.quantum_classifier` takes over with a
clearly labelled non-Qiskit fallback. Nothing here is ever labelled "Qiskit"
unless Qiskit actually executed the circuit.

Training uses the same SPSA routine as the fallback engine so that the two
execution paths remain comparable and a benchmark is not silently measuring two
different optimisers.
"""
from __future__ import annotations

import json
import math
import random
import threading
import time
from pathlib import Path
from typing import Any, Sequence

MODEL_FILE = Path(__file__).resolve().parent / "trained_qiskit_model.json"

N_QUBITS = 4
REPS = 2

QISKIT_AVAILABLE = False
QML_AVAILABLE = False
QISKIT_VERSION = None
QML_VERSION = None
IMPORT_ERROR: str | None = None

try:  # pragma: no cover - depends on the local environment
    import numpy as np  # noqa: F401
    import qiskit
    from qiskit.quantum_info import SparsePauliOp, Statevector
    from qiskit.primitives import StatevectorEstimator
    try:  # Qiskit >= 2.1: circuit-library *functions*
        from qiskit.circuit.library import real_amplitudes, zz_feature_map
    except ImportError:  # Qiskit 2.0: the (later deprecated) circuit-library *classes*
        from qiskit.circuit.library import RealAmplitudes as _RealAmplitudes, ZZFeatureMap as _ZZFeatureMap

        def zz_feature_map(feature_dimension, reps=1, entanglement="linear"):
            return _ZZFeatureMap(feature_dimension=feature_dimension, reps=reps, entanglement=entanglement)

        def real_amplitudes(num_qubits, reps=2, entanglement="circular"):
            return _RealAmplitudes(num_qubits=num_qubits, reps=reps, entanglement=entanglement)

    QISKIT_AVAILABLE = True
    QISKIT_VERSION = getattr(qiskit, "__version__", "unknown")

    import qiskit_machine_learning
    from qiskit_machine_learning.neural_networks import EstimatorQNN

    QML_AVAILABLE = True
    QML_VERSION = getattr(qiskit_machine_learning, "__version__", "unknown")
except Exception as exc:  # pragma: no cover
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


from .quantum_state import circuit_depth as _circuit_depth, depolarised

_SMOKE_LOCK = threading.Lock()
_SMOKE: dict[str, Any] = {"done": False, "ok": False, "error": None}


def _libs_present() -> bool:
    return bool(QISKIT_AVAILABLE and QML_AVAILABLE)


def _smoke_ok() -> bool:
    """One-off self-test: build the QNN, run it, and check it against Qiskit's own Statevector.

    Qiskit ML's API has moved between releases and this code cannot assume that the
    installed combination behaves. If the QNN fails to build/run, or its <ZZZZ> output
    disagrees with a direct state-vector calculation, the QML path reports itself
    unavailable (with the reason) instead of producing unverified numbers.
    """
    with _SMOKE_LOCK:
        if not _SMOKE["done"]:
            _SMOKE["done"] = True
            try:  # pragma: no cover - needs Qiskit
                m = QiskitVQC(seed=3)
                angles = [0.4, 1.1, 2.3, 0.7]
                raw = m._forward_raw([angles], m.weights)[0]
                state = m.statevector(angles)
                direct = sum(((-1) ** bin(i).count("1")) * (a.real ** 2 + a.imag ** 2) for i, a in enumerate(state))
                if not math.isfinite(raw) or abs(raw - direct) > 1e-6:
                    raise ValueError(f"EstimatorQNN output {raw:.6f} != direct Statevector <ZZZZ> {direct:.6f}")
                _SMOKE["ok"] = True
            except Exception as exc:  # pragma: no cover
                _SMOKE["error"] = f"qml_self_test_failed: {type(exc).__name__}: {exc}"
        return bool(_SMOKE["ok"])


def available() -> bool:
    """True only when a real Qiskit Machine Learning QNN can be built AND passed its self-test."""
    return _libs_present() and _smoke_ok()


def runtime_report() -> dict[str, Any]:
    return {
        "qiskit_installed": QISKIT_AVAILABLE,
        "qiskit_version": QISKIT_VERSION,
        "qiskit_machine_learning_installed": QML_AVAILABLE,
        "qiskit_machine_learning_version": QML_VERSION,
        "import_error": IMPORT_ERROR or _SMOKE["error"],
    }


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-min(z, 60)))
    e = math.exp(max(z, -60))
    return e / (1.0 + e)


class QiskitVQC:
    """Variational classifier executed through qiskit-machine-learning."""

    engine = "qiskit_machine_learning"

    def __init__(self, n_qubits: int = N_QUBITS, reps: int = REPS, seed: int = 7):
        if not _libs_present():  # pragma: no cover - guarded by callers
            raise RuntimeError(
                "qiskit and qiskit-machine-learning are required for this engine: " + str(IMPORT_ERROR))
        self.n_qubits = n_qubits
        self.reps = reps
        self.seed = seed
        self.feature_map = zz_feature_map(feature_dimension=n_qubits, reps=1, entanglement="linear")
        self.ansatz = real_amplitudes(num_qubits=n_qubits, reps=reps, entanglement="circular")
        self.circuit = self.feature_map.compose(self.ansatz)
        observable = SparsePauliOp("Z" * n_qubits)
        self.estimator = StatevectorEstimator()
        self.qnn = EstimatorQNN(
            circuit=self.circuit,
            estimator=self.estimator,
            observables=observable,
            input_params=list(self.feature_map.parameters),
            weight_params=list(self.ansatz.parameters),
        )
        rng = random.Random(seed)
        self.weights = [rng.uniform(-0.6, 0.6) for _ in range(self.qnn.num_weights)]
        self.scale = 2.2
        self.bias = 0.0
        self.trained = False
        self.training_info: dict[str, Any] = {}
        self.features: list[str] = []

    # -- inference ---------------------------------------------------------
    def _forward_raw(self, inputs: Sequence[Sequence[float]], weights: Sequence[float]) -> list[float]:
        out = self.qnn.forward(np.array(inputs, dtype=float), np.array(weights, dtype=float))
        return [float(np.reshape(row, -1)[0]) for row in np.array(out)]

    def forward(self, angles: Sequence[float]) -> tuple[float, list[float]]:
        raw = self._forward_raw([list(angles)], self.weights)[0]
        return _sigmoid(self.scale * (raw + self.bias)), [raw]

    def predict_proba(self, angles: Sequence[float]) -> float:
        return self.forward(angles)[0]

    def predict(self, angles: Sequence[float], threshold: float = 0.5) -> int:
        return int(self.predict_proba(angles) >= threshold)

    def _bound_circuit(self, angles: Sequence[float]):
        bind = {p: float(v) for p, v in zip(self.feature_map.parameters, list(angles))}
        bind.update({p: float(v) for p, v in zip(self.ansatz.parameters, self.weights)})
        return self.circuit.assign_parameters(bind)

    def statevector(self, angles: Sequence[float]) -> list[complex]:
        """Amplitudes of the state the Qiskit circuit prepares (little-endian, Qiskit order)."""
        return [complex(a) for a in Statevector.from_instruction(self._bound_circuit(angles)).data]

    def noisy_probability(self, angles: Sequence[float], p: float) -> float:
        """Risk if the output passes through a global depolarising channel (<ZZZZ> scales by 1-p)."""
        raw = self._forward_raw([list(angles)], self.weights)[0]
        return _sigmoid(self.scale * (depolarised(raw, p) + self.bias))

    # -- training ----------------------------------------------------------
    def _loss(self, X: Sequence[Sequence[float]], y: Sequence[int],
              weights: Sequence[float], bias: float) -> float:
        raws = self._forward_raw(X, weights)
        total = 0.0
        for raw, label in zip(raws, y):
            p = min(max(_sigmoid(self.scale * (raw + bias)), 1e-7), 1 - 1e-7)
            total += -(label * math.log(p) + (1 - label) * math.log(1 - p))
        return total / max(1, len(X))

    def fit(self, X: Sequence[Sequence[float]], y: Sequence[int], *, iterations: int = 60,
            batch_size: int = 48, seed: int = 11, progress: Any = None) -> dict[str, Any]:
        rng = random.Random(seed)
        started = time.perf_counter()
        params = list(self.weights) + [self.bias]
        history: list[dict[str, float]] = []
        a, c = 0.32, 0.20
        for k in range(iterations):
            idx = list(range(len(X)))
            rng.shuffle(idx)
            idx = idx[:batch_size]
            Xb = [list(X[i]) for i in idx]
            yb = [y[i] for i in idx]
            ak = a / ((k + 1 + 8) ** 0.602)
            ck = c / ((k + 1) ** 0.101)
            delta = [rng.choice((-1.0, 1.0)) for _ in params]
            lp = self._loss(Xb, yb, [p + ck * d for p, d in zip(params, delta)][:-1],
                            params[-1] + ck * delta[-1])
            lm = self._loss(Xb, yb, [p - ck * d for p, d in zip(params, delta)][:-1],
                            params[-1] - ck * delta[-1])
            g = (lp - lm) / (2 * ck)
            params = [p - ak * g * (1.0 / d) for p, d in zip(params, delta)]
            params = [max(-math.pi, min(math.pi, p)) for p in params]
            if k % 5 == 0 or k == iterations - 1:
                loss = (lp + lm) / 2
                history.append({"iteration": k, "loss": round(loss, 5)})
                if progress:
                    progress(k, iterations, loss)
        self.weights, self.bias = params[:-1], params[-1]
        final = self._loss(list(map(list, X)), list(y), self.weights, self.bias)
        self.trained = True
        self.training_info = {
            "optimizer": "SPSA (simultaneous perturbation stochastic approximation)",
            "iterations": iterations,
            "batch_size": batch_size,
            "samples": len(X),
            "final_loss": round(final, 5),
            "loss_history": history,
            "training_seconds": round(time.perf_counter() - started, 3),
            "execution_backend": "Qiskit Machine Learning EstimatorQNN (state-vector estimator)",
        }
        return self.training_info

    # -- description -------------------------------------------------------
    def describe_circuit(self, angles: Sequence[float] | None = None) -> dict[str, Any]:
        """Describe the circuit that actually executes, read back from Qiskit."""
        bound = self.circuit
        ops: list[dict[str, Any]] = []
        try:
            decomposed = self.circuit.decompose().decompose()
            qubit_index = {q: i for i, q in enumerate(decomposed.qubits)}
            n_inputs = len(self.feature_map.parameters)
            for inst in decomposed.data:
                name = inst.operation.name
                if name in {"barrier", "measure"}:
                    continue
                qubits = [qubit_index[q] for q in inst.qubits]
                is_encoding = any(
                    p in self.feature_map.parameters
                    for param in inst.operation.params if hasattr(param, "parameters")
                    for p in param.parameters)
                theta = None
                if inst.operation.params:
                    try:
                        theta = float(inst.operation.params[0])
                    except Exception:
                        theta = None
                ops.append({
                    "gate": name, "qubits": qubits, "theta": theta,
                    "kind": "encoding" if is_encoding else ("entangle" if len(qubits) > 1 else "variational"),
                    "label": name.upper(),
                })
            _ = n_inputs
        except Exception:
            ops = []
        for q in range(self.n_qubits):
            ops.append({"gate": "measure", "qubits": [q], "kind": "measurement", "label": "M ⟨Z⟩"})
        depth = _circuit_depth(ops)
        info = {
            "qubits": self.n_qubits,
            "layers": self.reps,
            "encoding": "ZZFeatureMap (Qiskit) — second-order Pauli-Z feature map",
            "ansatz": f"RealAmplitudes (Qiskit), {self.reps} reps, circular entanglement",
            "entanglement": "ZZFeatureMap linear + RealAmplitudes circular CX",
            "parameters": len(self.weights),
            "readout_parameters": 1,
            "gate_count": len([o for o in ops if o["gate"] != "measure"]),
            "circuit_depth": depth,
            "measurement": "⟨Z⊗Z⊗Z⊗Z⟩ expectation via EstimatorQNN",
            "operations": ops,
            "status": "Experimental",
            "engine": self.engine,
        }
        try:
            info["qiskit_circuit_text"] = str(self.circuit.decompose().draw(output="text"))
        except Exception:
            pass
        return info

    def measurement_distribution(self, angles: Sequence[float], top: int = 8) -> list[dict[str, Any]]:
        try:
            probs = [float(x) for x in Statevector.from_instruction(self._bound_circuit(angles)).probabilities()]
        except Exception:
            return []
        rows = [{"state": format(i, f"0{self.n_qubits}b"), "probability": round(float(p), 5)}
                for i, p in enumerate(probs)]
        rows.sort(key=lambda r: r["probability"], reverse=True)
        return rows[:top]

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "model_version": 1,
            "n_qubits": self.n_qubits,
            "reps": self.reps,
            "feature_map": "ZZFeatureMap",
            "feature_map_config": {"feature_dimension": self.n_qubits, "reps": 1, "entanglement": "linear"},
            "ansatz": "RealAmplitudes",
            "ansatz_config": {"num_qubits": self.n_qubits, "reps": self.reps, "entanglement": "circular"},
            "observable": "Z" * self.n_qubits,
            "weights": list(self.weights),
            "bias": self.bias,
            "scale": self.scale,
            "trained": self.trained,
            "training_info": self.training_info,
            "features": self.features,
            "feature_order": list(self.features),
            "normalization": {
                "method": "min-max physical ranges",
                "ranges": {
                    "disease_signal": [0.0, 100.0], "soil_moisture": [0.0, 100.0],
                    "temperature": [0.0, 50.0], "humidity": [0.0, 100.0],
                    "water_risk": [0.0, 100.0], "heat_risk": [0.0, 100.0],
                    "sensor_reliability": [0.0, 100.0], "image_confidence": [0.0, 100.0]
                }
            },
            "dataset_metadata": self.training_info.get("dataset_metadata", {}),
            "training_status": "trained" if self.trained else "untrained",
            "qiskit_version": QISKIT_VERSION,
            "qiskit_machine_learning_version": QML_VERSION,
            "saved_at": time.time(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QiskitVQC":
        m = cls(n_qubits=int(data.get("n_qubits", N_QUBITS)), reps=int(data.get("reps", REPS)))
        m.weights = [float(x) for x in data.get("weights", m.weights)]
        m.bias = float(data.get("bias", 0.0))
        m.scale = float(data.get("scale", 2.2))
        m.trained = bool(data.get("trained", False))
        m.training_info = data.get("training_info", {})
        m.features = list(data.get("features", []))
        return m

    def validate(self, *, expected_features: Sequence[str] | None = None) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not _libs_present():
            errors.append("Qiskit Machine Learning is unavailable")
        if not self.trained:
            errors.append("model is not marked trained")
        if self.n_qubits != N_QUBITS:
            errors.append(f"n_qubits mismatch: {self.n_qubits} != {N_QUBITS}")
        if self.reps != REPS:
            errors.append(f"reps mismatch: {self.reps} != {REPS}")
        if expected_features is not None and list(self.features) != list(expected_features):
            errors.append("feature order does not match the active pipeline")
        if len(self.weights) != self.qnn.num_weights:
            errors.append(f"parameter count mismatch: {len(self.weights)} != {self.qnn.num_weights}")
        if not all(math.isfinite(float(x)) for x in self.weights):
            errors.append("non-finite trained weights")
        if not math.isfinite(float(self.bias)) or not math.isfinite(float(self.scale)):
            errors.append("invalid bias/scale")
        return (not errors, errors)

    def save(self, path: Path | str = MODEL_FILE) -> None:
        ok, errors = self.validate(expected_features=self.features)
        if not ok:
            raise ValueError("Refusing to save invalid Qiskit model: " + "; ".join(errors))
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str = MODEL_FILE, *, expected_features: Sequence[str] | None = None) -> "QiskitVQC | None":
        p = Path(path)
        if not p.exists() or not _libs_present():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("engine") != cls.engine or data.get("trained") is not True:
                return None
            m = cls.from_dict(data)
            ok, _ = m.validate(expected_features=expected_features)
            return m if ok else None
        except Exception:
            return None
