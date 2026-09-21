"""Variational quantum classifier for early crop-risk warning.

Execution backends
------------------
1. **Qiskit** (preferred). When ``qiskit`` is installed the circuit is a real
   ``QuantumCircuit`` and expectation values are produced with
   ``qiskit.quantum_info.Statevector``. Nothing about the circuit is faked.
2. **Bundled state-vector fallback**. If Qiskit is not installed, an included
   pure-Python state-vector simulator executes the *same* gate sequence so the
   prototype still runs (and reports honestly that Qiskit is absent).

Nothing in this module executes on quantum hardware. Everything is simulation.
"""
from __future__ import annotations

import cmath
import json
import math
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Sequence

N_QUBITS = 4
N_LAYERS = 2
MODEL_FILE = Path(__file__).resolve().parent / "trained_model.json"
from .quantum_state import circuit_depth as _circuit_depth, depolarised

# --------------------------------------------------------------------------
# Optional Qiskit import
# --------------------------------------------------------------------------
QISKIT_AVAILABLE = False
QISKIT_VERSION = None
QISKIT_IMPORT_ERROR = None
try:  # pragma: no cover - depends on the local environment
    import qiskit  # type: ignore
    from qiskit import QuantumCircuit  # type: ignore
    from qiskit.quantum_info import Statevector, SparsePauliOp  # type: ignore

    QISKIT_AVAILABLE = True
    QISKIT_VERSION = getattr(qiskit, "__version__", "unknown")
except Exception as exc:  # pragma: no cover
    QISKIT_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

_SV_LOCK = threading.Lock()
_SV_CHECK: dict[str, Any] = {"done": False, "ok": False, "error": None}
_RUNTIME_ERRORS: dict[str, Any] = {"count": 0, "last": None, "disabled": False}


def _forced_fallback() -> bool:
    return os.getenv("ASTRANEX_FORCE_FALLBACK_SIM", "0").lower() not in {"0", "false", "no"}


def _qiskit_statevector_ok() -> bool:
    """True only if Qiskit is importable AND its Statevector agrees with the bundled simulator.

    The check runs once. Agreement of two independent implementations on a sample
    circuit is what lets the app label an execution "Qiskit" with a straight face.
    """
    if not QISKIT_AVAILABLE:
        return False
    with _SV_LOCK:
        if not _SV_CHECK["done"]:
            _SV_CHECK["done"] = True
            try:  # pragma: no cover - depends on the local environment
                angles = [0.31, 1.27, 2.05, 0.88]
                weights = [0.11 * (i + 1) - 0.9 for i in range(n_parameters())]
                a = _expectations_qiskit(angles, weights, N_QUBITS, N_LAYERS)
                b = _expectations_fallback(angles, weights, N_QUBITS, N_LAYERS)
                if max(abs(x - y) for x, y in zip(a, b)) > 1e-6:
                    raise ValueError("Qiskit Statevector disagrees with the bundled reference simulator")
                _SV_CHECK["ok"] = True
            except Exception as exc:  # pragma: no cover
                _SV_CHECK["error"] = f"{type(exc).__name__}: {exc}"
        return bool(_SV_CHECK["ok"]) and not _RUNTIME_ERRORS["disabled"]


def _use_qiskit() -> bool:
    """Evaluated at call time so the reported engine always matches the executing engine."""
    return QISKIT_AVAILABLE and not _forced_fallback() and _qiskit_statevector_ok()


def _note_qiskit_failure(exc: Exception) -> None:
    """A Qiskit call failed mid-run. Record it and stop claiming Qiskit execution."""
    _RUNTIME_ERRORS["count"] += 1
    _RUNTIME_ERRORS["last"] = f"{type(exc).__name__}: {exc}"
    _RUNTIME_ERRORS["disabled"] = True


def quantum_runtime_status() -> dict[str, Any]:
    """Report exactly which engine will execute the circuit.

    Three tiers, never conflated:

    ``qiskit_machine_learning``  real Qiskit + qiskit-machine-learning EstimatorQNN
    ``qiskit_statevector``       real Qiskit circuit, qiskit.quantum_info.Statevector
    ``fallback_simulation``      bundled Python simulator — NOT Qiskit execution
    """
    from . import qiskit_vqc

    report = qiskit_vqc.runtime_report()
    forced = _forced_fallback()

    if qiskit_vqc.available() and not forced and not _RUNTIME_ERRORS["disabled"]:
        mode = "qiskit_machine_learning"
        backend = "Qiskit Machine Learning EstimatorQNN (state-vector estimator)"
        is_qiskit = True
        label = "Qiskit execution"
    elif _use_qiskit():
        mode = "qiskit_statevector"
        backend = "Qiskit state-vector simulator (qiskit.quantum_info.Statevector)"
        is_qiskit = True
        label = "Qiskit execution"
    else:
        mode = "fallback_simulation"
        backend = "Fallback quantum simulation \u2014 not Qiskit execution"
        is_qiskit = False
        label = "Fallback quantum simulation \u2014 not Qiskit execution"

    return {
        "qiskit_installed": QISKIT_AVAILABLE,
        "qiskit_version": QISKIT_VERSION,
        "qiskit_machine_learning_installed": report["qiskit_machine_learning_installed"],
        "qiskit_machine_learning_version": report["qiskit_machine_learning_version"],
        "import_error": QISKIT_IMPORT_ERROR or report["import_error"] or _SV_CHECK["error"],
        "qiskit_runtime_errors": _RUNTIME_ERRORS["count"],
        "qiskit_last_error": _RUNTIME_ERRORS["last"],
        "execution_backend": backend,
        "execution_label": label,
        "qiskit_execution": is_qiskit,
        "forced_fallback": forced,
        "mode": mode,
        "hardware_execution": False,
        "note": ("Simulation only. No quantum hardware is used and no quantum advantage is claimed."
                 if is_qiskit else
                 "Qiskit is not available in this environment, so a bundled Python simulator is "
                 "running the circuit. This is NOT Qiskit execution and is labelled as such "
                 "everywhere. Classical agricultural analysis is unaffected."),
    }


# --------------------------------------------------------------------------
# Bundled state-vector simulator (used when Qiskit is unavailable)
# --------------------------------------------------------------------------
class _StateVector:
    """Minimal, dependency-free state-vector simulator for a few qubits."""

    def __init__(self, n: int):
        self.n = n
        self.amps = [0j] * (2 ** n)
        self.amps[0] = 1 + 0j

    def _apply_1q(self, q: int, m: tuple[complex, complex, complex, complex]) -> None:
        a, b, c, d = m
        step = 1 << q
        for base in range(0, 1 << self.n, step << 1):
            for off in range(step):
                i0 = base + off
                i1 = i0 + step
                v0, v1 = self.amps[i0], self.amps[i1]
                self.amps[i0] = a * v0 + b * v1
                self.amps[i1] = c * v0 + d * v1

    def ry(self, q: int, theta: float) -> None:
        c, s = math.cos(theta / 2), math.sin(theta / 2)
        self._apply_1q(q, (c + 0j, -s + 0j, s + 0j, c + 0j))

    def rx(self, q: int, theta: float) -> None:
        c, s = math.cos(theta / 2), math.sin(theta / 2)
        self._apply_1q(q, (c + 0j, -1j * s, -1j * s, c + 0j))

    def rz(self, q: int, theta: float) -> None:
        e0 = cmath.exp(-1j * theta / 2)
        e1 = cmath.exp(1j * theta / 2)
        self._apply_1q(q, (e0, 0j, 0j, e1))

    def cx(self, control: int, target: int) -> None:
        for i in range(1 << self.n):
            if (i >> control) & 1 and not (i >> target) & 1:
                j = i | (1 << target)
                self.amps[i], self.amps[j] = self.amps[j], self.amps[i]

    def expectation_z(self, q: int) -> float:
        total = 0.0
        for i, amp in enumerate(self.amps):
            p = amp.real * amp.real + amp.imag * amp.imag
            total += p if not ((i >> q) & 1) else -p
        return total

    def probabilities(self) -> list[float]:
        return [a.real * a.real + a.imag * a.imag for a in self.amps]


# --------------------------------------------------------------------------
# Circuit definition (single source of truth for both backends)
# --------------------------------------------------------------------------

def circuit_operations(angles: Sequence[float], weights: Sequence[float],
                       n_qubits: int = N_QUBITS, layers: int = N_LAYERS) -> list[dict[str, Any]]:
    """The ordered gate list of the variational circuit.

    Layout per layer: entangling CX ring, then a trainable RY/RZ rotation pair on
    every qubit. Data is angle-encoded once with RY at the start.
    """
    ops: list[dict[str, Any]] = []
    for q in range(n_qubits):
        ops.append({"gate": "ry", "qubits": [q], "theta": float(angles[q] if q < len(angles) else 0.0),
                    "kind": "encoding", "label": f"RY(x{q + 1})"})
    p = 0
    for layer in range(layers):
        pairs = [(q, (q + 1) % n_qubits) for q in range(0, n_qubits, 2)] if layer % 2 == 0 \
            else [(q, (q + 1) % n_qubits) for q in range(1, n_qubits, 2)]
        for c, t in pairs:
            ops.append({"gate": "cx", "qubits": [c, t], "kind": "entangle", "label": "CX",
                        "layer": layer})
        for q in range(n_qubits):
            theta = float(weights[p]) if p < len(weights) else 0.0
            ops.append({"gate": "ry", "qubits": [q], "theta": theta, "kind": "variational",
                        "label": f"RY(\u03b8{p + 1})", "layer": layer})
            p += 1
            phi = float(weights[p]) if p < len(weights) else 0.0
            ops.append({"gate": "rz", "qubits": [q], "theta": phi, "kind": "variational",
                        "label": f"RZ(\u03b8{p + 1})", "layer": layer})
            p += 1
    for q in range(n_qubits):
        ops.append({"gate": "measure", "qubits": [q], "kind": "measurement", "label": "M \u27e8Z\u27e9"})
    return ops


def n_parameters(n_qubits: int = N_QUBITS, layers: int = N_LAYERS) -> int:
    return n_qubits * layers * 2


def build_qiskit_circuit(angles: Sequence[float], weights: Sequence[float],
                         n_qubits: int = N_QUBITS, layers: int = N_LAYERS):
    """Return a real :class:`qiskit.QuantumCircuit` (raises if Qiskit is absent)."""
    if not QISKIT_AVAILABLE:  # pragma: no cover
        raise RuntimeError("Qiskit is not installed in this environment.")
    qc = QuantumCircuit(n_qubits)
    for op in circuit_operations(angles, weights, n_qubits, layers):
        if op["gate"] == "ry":
            qc.ry(op["theta"], op["qubits"][0])
        elif op["gate"] == "rz":
            qc.rz(op["theta"], op["qubits"][0])
        elif op["gate"] == "rx":
            qc.rx(op["theta"], op["qubits"][0])
        elif op["gate"] == "cx":
            qc.cx(op["qubits"][0], op["qubits"][1])
    return qc


def _expectations_qiskit(angles: Sequence[float], weights: Sequence[float],
                         n_qubits: int, layers: int) -> list[float]:  # pragma: no cover
    qc = build_qiskit_circuit(angles, weights, n_qubits, layers)
    state = Statevector.from_instruction(qc)
    out = []
    for q in range(n_qubits):
        pauli = "".join("Z" if i == q else "I" for i in range(n_qubits - 1, -1, -1))
        out.append(float(state.expectation_value(SparsePauliOp(pauli)).real))
    return out


def _expectations_fallback(angles: Sequence[float], weights: Sequence[float],
                           n_qubits: int, layers: int) -> list[float]:
    sv = _StateVector(n_qubits)
    for op in circuit_operations(angles, weights, n_qubits, layers):
        g, qs = op["gate"], op["qubits"]
        if g == "ry":
            sv.ry(qs[0], op["theta"])
        elif g == "rz":
            sv.rz(qs[0], op["theta"])
        elif g == "rx":
            sv.rx(qs[0], op["theta"])
        elif g == "cx":
            sv.cx(qs[0], qs[1])
    return [sv.expectation_z(q) for q in range(n_qubits)]


def expectation_values(angles: Sequence[float], weights: Sequence[float],
                       n_qubits: int = N_QUBITS, layers: int = N_LAYERS) -> list[float]:
    if _use_qiskit():
        try:  # pragma: no cover
            return _expectations_qiskit(angles, weights, n_qubits, layers)
        except Exception as exc:
            _note_qiskit_failure(exc)
    return _expectations_fallback(angles, weights, n_qubits, layers)


def measurement_distribution(angles: Sequence[float], weights: Sequence[float],
                             n_qubits: int = N_QUBITS, layers: int = N_LAYERS,
                             top: int = 8) -> list[dict[str, Any]]:
    """Basis-state probabilities, for the circuit visualisation."""
    if _use_qiskit():
        try:  # pragma: no cover
            qc = build_qiskit_circuit(angles, weights, n_qubits, layers)
            probs = [float(x) for x in Statevector.from_instruction(qc).probabilities()]
        except Exception as exc:
            _note_qiskit_failure(exc)
            probs = _fallback_probs(angles, weights, n_qubits, layers)
    else:
        probs = _fallback_probs(angles, weights, n_qubits, layers)
    rows = [{"state": format(i, f"0{n_qubits}b"), "probability": round(p, 5)}
            for i, p in enumerate(probs)]
    rows.sort(key=lambda r: r["probability"], reverse=True)
    return rows[:top]


def _fallback_sv(angles, weights, n_qubits, layers) -> _StateVector:
    sv = _StateVector(n_qubits)
    for op in circuit_operations(angles, weights, n_qubits, layers):
        g, qs = op["gate"], op["qubits"]
        if g == "ry":
            sv.ry(qs[0], op["theta"])
        elif g == "rz":
            sv.rz(qs[0], op["theta"])
        elif g == "rx":
            sv.rx(qs[0], op["theta"])
        elif g == "cx":
            sv.cx(qs[0], qs[1])
    return sv


def _fallback_probs(angles, weights, n_qubits, layers) -> list[float]:
    return _fallback_sv(angles, weights, n_qubits, layers).probabilities()


def final_statevector(angles: Sequence[float], weights: Sequence[float],
                      n_qubits: int = N_QUBITS, layers: int = N_LAYERS) -> list[complex]:
    """Amplitudes of the circuit's output state (Qiskit when it verifiably runs, else bundled)."""
    if _use_qiskit():
        try:  # pragma: no cover
            qc = build_qiskit_circuit(angles, weights, n_qubits, layers)
            return [complex(a) for a in Statevector.from_instruction(qc).data]
        except Exception as exc:
            _note_qiskit_failure(exc)
    return list(_fallback_sv(angles, weights, n_qubits, layers).amps)


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-min(z, 60)))
    e = math.exp(max(z, -60))
    return e / (1.0 + e)


# --------------------------------------------------------------------------
# Classifier
# --------------------------------------------------------------------------
class QuantumClassifier:
    """Hybrid variational classifier: quantum circuit + classical optimiser.

    Used when qiskit-machine-learning is unavailable. Executes through Qiskit's
    Statevector when Qiskit alone is installed, otherwise through the bundled
    simulator (reported as "Fallback quantum simulation - not Qiskit execution").
    """

    engine = "builtin_vqc"

    def __init__(self, n_qubits: int = N_QUBITS, layers: int = N_LAYERS, seed: int = 7):
        self.n_qubits = n_qubits
        self.layers = layers
        self.seed = seed
        rng = random.Random(seed)
        n_w = n_parameters(n_qubits, layers)
        self.weights: list[float] = [rng.uniform(-0.6, 0.6) for _ in range(n_w)]
        # Trainable classical read-out on top of the <Z> expectations.
        self.readout: list[float] = [1.0] * n_qubits
        self.bias: float = 0.0
        self.trained = False
        self.training_info: dict[str, Any] = {}
        self.features: list[str] = []

    # -- inference ---------------------------------------------------------
    def forward(self, angles: Sequence[float]) -> tuple[float, list[float]]:
        z = expectation_values(angles, self.weights, self.n_qubits, self.layers)
        logit = self.bias + sum(w * e for w, e in zip(self.readout, z))
        return _sigmoid(2.2 * logit), z

    def predict_proba(self, angles: Sequence[float]) -> float:
        return self.forward(angles)[0]

    def predict(self, angles: Sequence[float], threshold: float = 0.5) -> int:
        return int(self.predict_proba(angles) >= threshold)

    def statevector(self, angles: Sequence[float]) -> list[complex]:
        return final_statevector(angles, self.weights, self.n_qubits, self.layers)

    def noisy_probability(self, angles: Sequence[float], p: float) -> float:
        """Risk probability if the output state passes through a global depolarising channel."""
        z = expectation_values(angles, self.weights, self.n_qubits, self.layers)
        logit = self.bias + sum(w * depolarised(e, p) for w, e in zip(self.readout, z))
        return _sigmoid(2.2 * logit)

    # -- training ----------------------------------------------------------
    def _loss(self, X: Sequence[Sequence[float]], y: Sequence[int],
              weights: Sequence[float], readout: Sequence[float], bias: float) -> float:
        total = 0.0
        for angles, label in zip(X, y):
            z = expectation_values(angles, weights, self.n_qubits, self.layers)
            p = _sigmoid(2.2 * (bias + sum(w * e for w, e in zip(readout, z))))
            p = min(max(p, 1e-7), 1 - 1e-7)
            total += -(label * math.log(p) + (1 - label) * math.log(1 - p))
        return total / max(1, len(X))

    def fit(self, X: Sequence[Sequence[float]], y: Sequence[int], *, iterations: int = 120,
            batch_size: int = 64, seed: int = 11, progress: Any = None) -> dict[str, Any]:
        """SPSA training of the circuit parameters and the classical read-out.

        SPSA needs only two circuit evaluations per iteration regardless of the
        parameter count, which keeps a simulator-based prototype practical.
        """
        rng = random.Random(seed)
        started = time.perf_counter()
        params = list(self.weights) + list(self.readout) + [self.bias]
        n_w = len(self.weights)
        n_r = len(self.readout)
        history: list[dict[str, float]] = []

        def unpack(p: Sequence[float]):
            return list(p[:n_w]), list(p[n_w:n_w + n_r]), float(p[-1])

        a, c = 0.32, 0.20
        for k in range(iterations):
            idx = list(range(len(X)))
            rng.shuffle(idx)
            idx = idx[:batch_size]
            Xb = [X[i] for i in idx]
            yb = [y[i] for i in idx]
            ak = a / ((k + 1 + 8) ** 0.602)
            ck = c / ((k + 1) ** 0.101)
            delta = [rng.choice((-1.0, 1.0)) for _ in params]
            p_plus = [p + ck * d for p, d in zip(params, delta)]
            p_minus = [p - ck * d for p, d in zip(params, delta)]
            l_plus = self._loss(Xb, yb, *unpack(p_plus))
            l_minus = self._loss(Xb, yb, *unpack(p_minus))
            grad_scale = (l_plus - l_minus) / (2 * ck)
            params = [p - ak * grad_scale * (1.0 / d) for p, d in zip(params, delta)]
            params = [max(-math.pi, min(math.pi, p)) for p in params]
            if k % 5 == 0 or k == iterations - 1:
                loss = (l_plus + l_minus) / 2
                history.append({"iteration": k, "loss": round(loss, 5)})
                if progress:
                    progress(k, iterations, loss)

        self.weights, self.readout, self.bias = unpack(params)
        final_loss = self._loss(X, y, self.weights, self.readout, self.bias)
        self.trained = True
        self.training_info = {
            "optimizer": "SPSA (simultaneous perturbation stochastic approximation)",
            "iterations": iterations,
            "batch_size": batch_size,
            "samples": len(X),
            "final_loss": round(final_loss, 5),
            "loss_history": history,
            "training_seconds": round(time.perf_counter() - started, 3),
            "execution_backend": quantum_runtime_status()["execution_backend"],
        }
        return self.training_info

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "model_version": 2,
            "n_qubits": self.n_qubits,
            "layers": self.layers,
            "feature_map": "Angle encoding (RY)",
            "ansatz": "Custom RY/RZ variational block, alternating CX ring",
            "weights": self.weights,
            "readout": self.readout,
            "bias": self.bias,
            "trained": self.trained,
            "training_info": self.training_info,
            "features": self.features,
            "feature_order": list(self.features),
            "qiskit_version": QISKIT_VERSION,
            "execution_backend": quantum_runtime_status()["execution_backend"],
            "saved_at": time.time(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuantumClassifier":
        clf = cls(n_qubits=int(data.get("n_qubits", N_QUBITS)),
                  layers=int(data.get("layers", N_LAYERS)))
        clf.weights = [float(x) for x in data.get("weights", clf.weights)]
        clf.readout = [float(x) for x in data.get("readout", clf.readout)]
        clf.bias = float(data.get("bias", 0.0))
        clf.trained = bool(data.get("trained", False))
        clf.training_info = data.get("training_info", {})
        clf.features = list(data.get("features", []))
        return clf

    def save(self, path: Path | str = MODEL_FILE) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str = MODEL_FILE) -> "QuantumClassifier | None":
        p = Path(path)
        if not p.exists():
            return None
        try:
            return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return None

    def measurement_distribution(self, angles: Sequence[float], top: int = 8) -> list[dict[str, Any]]:
        return measurement_distribution(angles, self.weights, self.n_qubits, self.layers, top)

    # -- description for the UI -------------------------------------------
    def describe_circuit(self, angles: Sequence[float] | None = None) -> dict[str, Any]:
        angles = list(angles or [0.0] * self.n_qubits)
        ops = circuit_operations(angles, self.weights, self.n_qubits, self.layers)
        gates = len([o for o in ops if o["gate"] != "measure"])
        depth = _circuit_depth(ops)
        info = {
            "qubits": self.n_qubits,
            "layers": self.layers,
            "encoding": "Angle encoding (RY, feature \u2192 [0, \u03c0])",
            "entanglement": "Alternating CX ring",
            "parameters": len(self.weights),
            "readout_parameters": len(self.readout) + 1,
            "gate_count": gates,
            "measurement": "\u27e8Z\u27e9 expectation on every qubit",
            "ansatz": "Custom RY/RZ variational block with alternating CX ring",
            "circuit_depth": depth,
            "engine": self.engine,
            "operations": ops,
            "status": "Experimental",
        }
        info.update({k: v for k, v in quantum_runtime_status().items()
                     if k in {"execution_backend", "qiskit_installed", "qiskit_version", "hardware_execution"}})
        if _use_qiskit():  # pragma: no cover
            try:
                info["qiskit_circuit_text"] = str(build_qiskit_circuit(
                    angles, self.weights, self.n_qubits, self.layers).draw(output="text"))
            except Exception:
                pass
        return info
