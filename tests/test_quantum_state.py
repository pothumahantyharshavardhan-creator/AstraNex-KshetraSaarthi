"""Physics and plumbing checks for the quantum-state analysis and the v3.2 quantum features.

Every expected value below is derived by hand from quantum mechanics, not from the code under test.
"""
import math
import os

import pytest

from backend.quantum import benchmark as bench
from backend.quantum import pipeline
from backend.quantum.quantum_classifier import QuantumClassifier, circuit_operations, N_LAYERS, N_QUBITS, n_parameters
from backend.quantum.quantum_state import (
    analyse_state, bloch_vector, circuit_depth, depolarised, probabilities, sample_counts,
)

R = 1 / math.sqrt(2)


def test_bell_state_is_maximally_entangled():
    bell = [complex(R), 0j, 0j, complex(R)]                 # (|00> + |11>)/sqrt2
    st = analyse_state(bell, 2, shots=200)
    for q in st["qubits"]:
        assert q["bloch"]["length"] < 1e-9                   # reduced state is maximally mixed
        assert abs(q["entanglement_entropy"] - 1.0) < 1e-9   # exactly one bit
        assert abs(q["purity"] - 0.5) < 1e-9
    assert abs(st["meyer_wallach"] - 1.0) < 1e-9


def test_product_state_has_no_entanglement_and_correct_bloch_vector():
    # qubit0 = |+>, qubit1 = |0>  ->  amplitudes index = q1*2 + q0
    state = [complex(R), complex(R), 0j, 0j]
    st = analyse_state(state, 2, shots=100)
    assert st["meyer_wallach"] < 1e-9
    b0 = bloch_vector(state, 0)
    assert abs(b0["x"] - 1) < 1e-9 and abs(b0["y"]) < 1e-9 and abs(b0["z"]) < 1e-9
    b1 = bloch_vector(state, 1)
    assert abs(b1["z"] - 1) < 1e-9                            # |0> is the north pole


def test_bloch_y_axis_sign():
    # |+i> = (|0> + i|1>)/sqrt2 has Bloch vector (0, +1, 0)
    b = bloch_vector([complex(R), complex(0, R)], 0)
    assert abs(b["y"] - 1) < 1e-9 and abs(b["x"]) < 1e-9


def test_probabilities_and_shots_are_consistent_and_reproducible():
    probs = probabilities([complex(R), 0j, 0j, complex(R)])
    a = sample_counts(probs, 2, shots=1000, seed=1)
    b = sample_counts(probs, 2, shots=1000, seed=1)
    assert a == b
    assert sum(c["count"] for c in a["counts"]) == 1000
    assert {c["state"] for c in a["counts"]} == {"00", "11"}   # the Bell state never yields 01 or 10
    assert abs(a["counts"][0]["frequency"] - 0.5) < 0.08


def test_circuit_depth_counts_parallel_gates_once():
    ops = [{"gate": "ry", "qubits": [0]}, {"gate": "ry", "qubits": [1]}, {"gate": "ry", "qubits": [2]},
           {"gate": "cx", "qubits": [0, 1]}, {"gate": "cx", "qubits": [1, 2]},
           {"gate": "measure", "qubits": [0]}]
    assert circuit_depth(ops) == 3                            # ry || ry || ry, then cx(0,1), then cx(1,2)
    assert circuit_depth([]) == 0


def test_builtin_circuit_depth_is_not_the_gate_count():
    ops = circuit_operations([0.1, 0.2, 0.3, 0.4], [0.0] * n_parameters(), N_QUBITS, N_LAYERS)
    gates = [o for o in ops if o["gate"] != "measure"]
    assert 0 < circuit_depth(ops) < len(gates)                # the old code reported the gate count as "depth"
    info = QuantumClassifier().describe_circuit([0.1, 0.2, 0.3, 0.4])
    assert info["circuit_depth"] == circuit_depth(ops)
    assert info["gate_count"] == len(gates)


def test_depolarising_channel_scales_expectations():
    assert depolarised(0.8, 0.0) == 0.8
    assert abs(depolarised(0.8, 0.25) - 0.6) < 1e-12
    assert depolarised(-0.4, 1.0) == 0.0


def test_statevector_matches_expectations():
    q = QuantumClassifier()
    angles = [0.3, 1.1, 2.0, 0.7]
    amps = q.statevector(angles)
    assert abs(sum(abs(a) ** 2 for a in amps) - 1) < 1e-9
    # <Z_0> from the amplitudes must equal the engine's own expectation value for qubit 0
    z0 = sum((1 if not (i & 1) else -1) * abs(a) ** 2 for i, a in enumerate(amps))
    from backend.quantum.quantum_classifier import expectation_values
    assert abs(z0 - expectation_values(angles, q.weights)[0]) < 1e-9


def test_benchmark_runs_without_qiskit_and_labels_itself(monkeypatch):
    monkeypatch.setenv("ASTRANEX_FORCE_FALLBACK_SIM", "1")
    out = bench.run_benchmark(dataset_size=120, iterations=12, save=False)     # used to raise RuntimeError
    assert out["mode"] == "fallback_simulation"
    assert out["qiskit_execution"] is False
    assert "not Qiskit" in out["execution_label"]
    assert bench.result_file("fallback_simulation").name == "benchmark_result_fallback_simulation.json"
    assert bench.result_file("qiskit_machine_learning") == bench.RESULT_FILE


def test_fallback_artifact_cannot_pass_as_qiskit(monkeypatch, tmp_path):
    """A fallback benchmark file must be rejected if it claims Qiskit execution, and vice versa."""
    import json
    monkeypatch.setenv("ASTRANEX_FORCE_FALLBACK_SIM", "1")
    monkeypatch.setattr(bench, "_HERE", tmp_path)
    (tmp_path / "benchmark_result_fallback_simulation.json").write_text(json.dumps(
        {"status": "complete", "mode": "fallback_simulation", "qiskit_execution": True, "quantum_engine": "builtin_vqc"}))
    assert bench.load_result("fallback_simulation") is None
    (tmp_path / "benchmark_result_fallback_simulation.json").write_text(json.dumps(
        {"status": "complete", "mode": "fallback_simulation", "qiskit_execution": False, "quantum_engine": "builtin_vqc"}))
    assert bench.load_result("fallback_simulation") is not None


def test_saved_model_with_non_default_features_is_still_loaded(monkeypatch, tmp_path):
    """Regression: a retrain may legitimately select a different top-4; it used to be discarded on restart."""
    monkeypatch.setenv("ASTRANEX_FORCE_FALLBACK_SIM", "1")
    m = QuantumClassifier()
    m.features = ["soil_moisture", "humidity", "water_risk", "sensor_reliability"]
    m.trained = True
    path = tmp_path / "m.json"
    m.save(path)
    monkeypatch.setattr(QuantumClassifier, "load", classmethod(lambda cls, *a, **k: cls.from_dict(__import__("json").loads(path.read_text()))))
    loaded = pipeline.load_engine()
    assert loaded is not None and loaded.features == m.features
    assert pipeline._valid_features(loaded.features)
    assert not pipeline._valid_features(["disease_signal", "disease_signal", "heat_risk", "temperature"])
    assert not pipeline._valid_features(["disease_signal", "nonsense", "heat_risk", "temperature"])


def test_simulate_returns_full_physics_payload(monkeypatch):
    monkeypatch.setenv("ASTRANEX_FORCE_FALLBACK_SIM", "1")
    out = pipeline.simulate([0.8, 0.7, 0.3, 0.6], shots=500, seed=3)
    assert out["available"] is True
    st = out["state"]
    assert len(st["qubits"]) == 4 and len(st["probabilities"]) == 16
    assert abs(st["state_norm"] - 1) < 1e-5
    assert abs(sum(p["probability"] for p in st["probabilities"]) - 1) < 1e-3
    assert st["shots"]["shots"] == 500
    if out["trained"]:
        pts = out["noise_sweep"]["points"]
        assert pts[0]["noise"] == 0.0
        assert abs(pts[0]["risk_probability"] - out["quantum"]["risk_probability"]) < 0.05   # p=0 must equal the prediction
    with pytest.raises(ValueError):
        pipeline.simulate([0.1, 0.2], shots=10)


def test_hybrid_analyze_attaches_state_analysis(monkeypatch):
    monkeypatch.setenv("ASTRANEX_FORCE_FALLBACK_SIM", "1")
    result = {"risks": {"disease": 62, "water": 30, "heat": 20}, "evidence": {"soil_moisture": 40, "temperature": 31, "humidity": 70},
              "sensor_trust": 90, "vision_confidence": 70}
    out = pipeline.hybrid_analyze(result, {})
    if out.get("available"):
        assert out["state"] is not None and len(out["state"]["qubits"]) == 4
        assert out["circuit"]["depth"] is not None
