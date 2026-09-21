"""Physical analysis of the circuit's output state.

Everything here is *computed from the state vector the circuit actually produced*
(pure Python, no NumPy needed):

* per-qubit Bloch vectors (from the reduced single-qubit density matrix),
* per-qubit entanglement entropy and purity,
* the Meyer-Wallach global entanglement measure,
* basis-state probabilities and finite-shot sampling (what a real device would
  return, minus hardware noise),
* a simplified global-depolarising-noise model for a "NISQ robustness" sweep,
* the true depth of a gate list.

Qubit ordering follows Qiskit's little-endian convention: bit ``q`` of a basis
index is qubit ``q``, and bit-strings are printed with qubit 0 on the right.
"""
from __future__ import annotations

import bisect
import math
import random
from typing import Any, Sequence


def probabilities(amps: Sequence[complex]) -> list[float]:
    p = [(a.real * a.real + a.imag * a.imag) for a in amps]
    total = sum(p) or 1.0
    return [x / total for x in p]


def bloch_vector(amps: Sequence[complex], qubit: int) -> dict[str, float]:
    """Bloch vector of one qubit of a (possibly entangled) pure state.

    rho_red = (I + x X + y Y + z Z) / 2, so x = 2 Re(rho01), y = -2 Im(rho01),
    z = rho00 - rho11, with rho01 = sum a[i0] * conj(a[i1]).
    """
    bit = 1 << qubit
    r00 = r11 = 0.0
    r01 = 0j
    for i, a in enumerate(amps):
        if i & bit:
            r11 += a.real * a.real + a.imag * a.imag
        else:
            r00 += a.real * a.real + a.imag * a.imag
            r01 += a * amps[i | bit].conjugate()
    norm = (r00 + r11) or 1.0
    x, y, z = 2 * r01.real / norm, -2 * r01.imag / norm, (r00 - r11) / norm
    length = min(1.0, math.sqrt(x * x + y * y + z * z))
    return {"x": x, "y": y, "z": z, "length": length}


def binary_entropy(p: float) -> float:
    if p <= 1e-12 or p >= 1 - 1e-12:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def analyse_state(amps: Sequence[complex], n_qubits: int, *, shots: int = 1024,
                  seed: int = 2026, top: int = 8) -> dict[str, Any]:
    """Full physical read-out of an n-qubit pure state."""
    probs = probabilities(amps)
    qubits = []
    purities = []
    for q in range(n_qubits):
        b = bloch_vector(amps, q)
        purity = (1 + b["length"] ** 2) / 2          # Tr(rho^2) of the reduced state
        entropy = binary_entropy((1 + b["length"]) / 2)  # von Neumann entropy, bits, 0..1
        purities.append(purity)
        theta = math.degrees(math.acos(max(-1.0, min(1.0, b["z"] / (b["length"] or 1.0))))) if b["length"] > 1e-9 else None
        phi = math.degrees(math.atan2(b["y"], b["x"])) % 360 if b["length"] > 1e-9 and (abs(b["x"]) + abs(b["y"])) > 1e-9 else None
        qubits.append({
            "qubit": q,
            "bloch": {k: round(v, 5) for k, v in b.items()},
            "polar_deg": None if theta is None else round(theta, 2),
            "azimuth_deg": None if phi is None else round(phi, 2),
            "purity": round(purity, 5),
            "entanglement_entropy": round(entropy, 5),
            "p_one": round(sum(p for i, p in enumerate(probs) if i & (1 << q)), 5),
        })
    meyer_wallach = 2 * (1 - sum(purities) / max(1, n_qubits))
    counts = sample_counts(probs, n_qubits, shots=shots, seed=seed)
    ranked = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
    return {
        "n_qubits": n_qubits,
        "qubits": qubits,
        "meyer_wallach": round(max(0.0, meyer_wallach), 5),
        "mean_entropy": round(sum(q["entanglement_entropy"] for q in qubits) / max(1, n_qubits), 5),
        "probabilities": [{"state": format(i, f"0{n_qubits}b"), "probability": round(probs[i], 6),
                           "amplitude": [round(amps[i].real, 5), round(amps[i].imag, 5)]} for i in range(len(probs))],
        "top_states": [{"state": format(i, f"0{n_qubits}b"), "probability": round(probs[i], 6)} for i in ranked[:top]],
        "shots": counts,
        "state_norm": round(sum(a.real * a.real + a.imag * a.imag for a in amps), 6),
        "note": ("Computed from the simulated state vector. Shot counts are sampled from that "
                 "exact distribution with no hardware noise."),
    }


def sample_counts(probs: Sequence[float], n_qubits: int, *, shots: int = 1024, seed: int = 2026,
                  top: int = 8) -> dict[str, Any]:
    """Finite-shot measurement counts, reproducible for a given seed."""
    shots = max(1, min(int(shots), 20000))
    rng = random.Random(seed)
    cumulative, acc = [], 0.0
    for p in probs:
        acc += p
        cumulative.append(acc)
    tally: dict[int, int] = {}
    for _ in range(shots):
        i = min(bisect.bisect_left(cumulative, rng.random() * acc), len(probs) - 1)
        tally[i] = tally.get(i, 0) + 1
    rows = sorted(tally.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "shots": shots, "seed": seed, "distinct_outcomes": len(tally),
        "counts": [{"state": format(i, f"0{n_qubits}b"), "count": c, "frequency": round(c / shots, 5)}
                   for i, c in rows[:top]],
    }


def circuit_depth(ops: Sequence[dict[str, Any]]) -> int:
    """True circuit depth: the longest chain of gates that cannot run in parallel."""
    level: dict[int, int] = {}
    for op in ops:
        if op.get("gate") in {"measure", "barrier"}:
            continue
        qs = op.get("qubits") or []
        if not qs:
            continue
        d = max(level.get(q, 0) for q in qs) + 1
        for q in qs:
            level[q] = d
    return max(level.values()) if level else 0


def depolarised(value: float, p: float) -> float:
    """<P> after a global depolarising channel of strength p: every non-identity
    Pauli expectation is scaled by (1 - p)."""
    return (1.0 - p) * value


NOISE_LEVELS = [0.0, 0.02, 0.05, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30]
