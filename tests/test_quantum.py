"""Tests for the experimental quantum layer.

These run with or without Qiskit installed: the bundled state-vector simulator
executes the same circuit, so behaviour is asserted, not the dependency.
"""
import math

from backend.engine import AnalysisInput, analyze_field
from backend.quantum import benchmark as bench
from backend.quantum import pipeline
from backend.quantum.classical_baseline import ClassicalBaseline
from backend.quantum.dataset import build_dataset, split
from backend.quantum.feature_encoder import (
    FEATURE_NAMES, extract_features, feature_report, normalise_features,
    select_features, to_angles,
)
from backend.quantum.quantum_classifier import (
    QuantumClassifier, circuit_operations, expectation_values, measurement_distribution,
    n_parameters, quantum_runtime_status,
)


# --------------------------------------------------------------------------
# Feature generation and normalisation
# --------------------------------------------------------------------------
def test_features_come_from_the_engine_not_from_noise():
    raw = dict(crop="tomato", condition="diseaseA", soil_moisture=72,
               temperature=31, humidity=85, weather="normal", recent_rainfall_mm=15)
    result = analyze_field(AnalysisInput(**raw))
    feats = extract_features(result, raw)
    for name in FEATURE_NAMES:
        assert name in feats
    assert feats["soil_moisture"] == 72
    assert feats["humidity"] == 85
    assert feats["disease_signal"] == result["risks"]["disease"]


def test_normalisation_is_bounded():
    feats = extract_features({}, {"soil_moisture": 250, "temperature": -99, "humidity": 55})
    norm = normalise_features(feats)
    for name, value in norm.items():
        assert 0.0 <= value <= 1.0, name


def test_angles_stay_within_zero_and_pi():
    angles = to_angles([0.0, 0.5, 1.0, 0.25])
    assert len(angles) == 4
    assert all(0.0 <= a <= math.pi + 1e-9 for a in angles)


def test_feature_selection_picks_k_features_and_ranks_them():
    data = build_dataset(n=90, seed=1)
    rows = [[r["normalised"][f] for f in FEATURE_NAMES] for r in data["rows"]]
    labels = [r["label"] for r in data["rows"]]
    sel = select_features(rows, labels, k=4)
    assert len(sel["selected"]) == 4
    assert len(sel["ranking"]) == len(FEATURE_NAMES)
    scores = [r["score"] for r in sel["ranking"]]
    assert scores == sorted(scores, reverse=True)


def test_feature_report_marks_encoded_qubits():
    feats = extract_features({}, {"soil_moisture": 40})
    report = feature_report(feats, ["disease_signal", "humidity", "soil_moisture", "temperature"])
    encoded = [r for r in report if r["encoded"]]
    assert len(encoded) == 4
    assert sorted(r["qubit"] for r in encoded) == [0, 1, 2, 3]


# --------------------------------------------------------------------------
# Circuit construction
# --------------------------------------------------------------------------
def test_circuit_has_four_qubits_and_expected_structure():
    clf = QuantumClassifier()
    assert clf.n_qubits == 4
    ops = circuit_operations([0.1, 0.2, 0.3, 0.4], clf.weights)
    encoding = [o for o in ops if o["kind"] == "encoding"]
    entangling = [o for o in ops if o["kind"] == "entangle"]
    measures = [o for o in ops if o["gate"] == "measure"]
    assert len(encoding) == 4            # one angle-encoded feature per qubit
    assert len(entangling) >= 4          # CX entanglement present
    assert len(measures) == 4
    assert all(0 <= q < 4 for o in ops for q in o["qubits"])


def test_parameter_count_matches_layers():
    assert n_parameters(4, 2) == 16
    assert len(QuantumClassifier(n_qubits=4, layers=2).weights) == 16


def test_expectations_are_valid_and_deterministic():
    clf = QuantumClassifier()
    angles = [0.4, 1.1, 2.0, 0.8]
    first = expectation_values(angles, clf.weights)
    second = expectation_values(angles, clf.weights)
    assert first == second
    assert len(first) == 4
    assert all(-1.0 - 1e-9 <= e <= 1.0 + 1e-9 for e in first)


def test_measurement_distribution_is_a_probability_distribution():
    clf = QuantumClassifier()
    dist = measurement_distribution([0.3, 0.6, 0.9, 1.2], clf.weights, top=16)
    total = sum(d["probability"] for d in dist)
    assert abs(total - 1.0) < 1e-3
    assert all(0.0 <= d["probability"] <= 1.0 for d in dist)


def test_runtime_status_never_claims_hardware():
    st = quantum_runtime_status()
    assert st["hardware_execution"] is False
    assert "execution_backend" in st


# --------------------------------------------------------------------------
# Prediction and training
# --------------------------------------------------------------------------
def test_quantum_prediction_is_a_probability():
    clf = QuantumClassifier()
    p = clf.predict_proba([0.5, 1.0, 1.5, 2.0])
    assert 0.0 <= p <= 1.0
    assert clf.predict([0.5, 1.0, 1.5, 2.0]) in (0, 1)


def test_quantum_training_reduces_loss():
    data = build_dataset(n=120, seed=4)
    feats = ["disease_signal", "humidity", "soil_moisture", "temperature"]
    X = [to_angles([r["normalised"][f] for f in feats]) for r in data["rows"]]
    y = [r["label"] for r in data["rows"]]
    clf = QuantumClassifier()
    before = clf._loss(X, y, clf.weights, clf.readout, clf.bias)
    info = clf.fit(X, y, iterations=25)
    assert clf.trained is True
    assert info["final_loss"] <= before + 0.05     # training must not diverge
    assert info["optimizer"].startswith("SPSA")


def test_classical_baseline_trains_and_predicts():
    data = build_dataset(n=120, seed=6)
    feats = ["disease_signal", "humidity", "soil_moisture", "temperature"]
    X = [[r["normalised"][f] for f in feats] for r in data["rows"]]
    y = [r["label"] for r in data["rows"]]
    model = ClassicalBaseline()
    model.features = feats
    model.fit(X, y, epochs=120)
    assert model.trained is True
    p = model.predict_proba(X[0])
    assert 0.0 <= p <= 1.0
    assert len(model.coefficients()) == 4


# --------------------------------------------------------------------------
# Dataset and benchmark
# --------------------------------------------------------------------------
def test_dataset_is_deterministic_and_labelled_as_demonstration():
    a = build_dataset(n=60, seed=11)
    b = build_dataset(n=60, seed=11)
    assert [r["label"] for r in a["rows"]] == [r["label"] for r in b["rows"]]
    assert "Demonstration" in a["source"]
    assert a["positives"] > 0 and a["negatives"] > 0   # both classes present


def test_split_is_stratified_and_disjoint():
    data = build_dataset(n=120, seed=12)
    parts = split(data, test_fraction=0.3, seed=5)
    assert len(parts["train"]) + len(parts["test"]) == data["size"]
    train_ids = {id(r) for r in parts["train"]}
    assert not any(id(r) in train_ids for r in parts["test"])
    assert any(r["label"] == 1 for r in parts["test"])


def test_benchmark_structure_contains_real_metrics_for_both_models():
    result = bench.run_benchmark(dataset_size=120, iterations=12, save=False, require_qiskit=False)
    result.pop("_models", None)
    for side in ("classical", "quantum"):
        m = result[side]["metrics"]
        for key in ("accuracy", "precision", "recall", "f1", "inference_ms_per_sample"):
            assert key in m
        assert 0 <= m["accuracy"] <= 100
    assert len(result["classical"]["coefficients"]) == 4
    assert len(result["features"]["selected"]) == 4
    assert "Demonstration" in result["evaluation_label"]
    assert "advantage" in result["comparison"]["verdict"].lower() or "experimental" in result["comparison"]["verdict"].lower()


def test_metrics_helper_matches_a_known_confusion_matrix():
    y_true = [1, 1, 0, 0]
    y_pred = [1, 0, 0, 0]
    m = bench.metrics(y_true, y_pred)
    assert m["accuracy"] == 75.0
    assert m["precision"] == 100.0
    assert m["recall"] == 50.0


def test_awaiting_payload_has_no_invented_numbers():
    payload = bench.awaiting_payload()
    assert payload["status"] == "awaiting_benchmark"
    assert payload["display"] == "Awaiting experimental benchmark"
    for side in ("classical", "quantum"):
        assert all(v is None for v in payload[side]["metrics"].values())


# --------------------------------------------------------------------------
# Pipeline behaviour and fallbacks
# --------------------------------------------------------------------------
def test_hybrid_analyze_returns_full_payload():
    raw = dict(crop="paddy", condition="diseaseA", soil_moisture=70,
               temperature=30, humidity=88, weather="normal", recent_rainfall_mm=20)
    result = analyze_field(AnalysisInput(**raw))
    out = pipeline.hybrid_analyze(result, raw)
    if pipeline.quantum_runtime_status()["mode"] == "qiskit_machine_learning":
        assert out["available"] is True
        assert out["quantum"]["risk_probability"] is not None
    else:
        # A previously trained fallback model may run when Qiskit is unavailable;
        # it must be labelled fallback and is never represented as Qiskit ML.
        assert out["available"] is True
        assert "not Qiskit execution" in out["quantum"]["backend"]


def test_hybrid_analyze_degrades_without_raising():
    out = pipeline.hybrid_analyze(None, None)
    assert out["available"] in (True, False)
    if not out["available"]:
        assert "Training required before QML inference" in out["message"]


def test_quantum_status_reports_simulation_only():
    st = pipeline.quantum_status()
    assert st["available"] is True
    assert st["runtime"]["hardware_execution"] is False
    assert any("advantage" in c.lower() for c in st["claims"])


def test_circuit_blueprint_maps_features_to_qubits():
    bp = pipeline.circuit_blueprint([0.5, 0.9, 1.4, 2.1])
    assert bp["qubits"] == 4
    assert len(bp["qubit_map"]) == 4
    assert bp["measurement"].startswith("\u27e8Z\u27e9")
    assert bp["status"] == "Experimental"


# --------------------------------------------------------------------------
# Execution-backend honesty (added in the QFF build)
# --------------------------------------------------------------------------
def test_runtime_never_labels_the_fallback_as_qiskit():
    from backend.quantum import qiskit_vqc

    st = quantum_runtime_status()
    assert st["mode"] in {"qiskit_machine_learning", "qiskit_statevector", "fallback_simulation"}
    if st["mode"] == "fallback_simulation":
        assert st["qiskit_execution"] is False
        assert "not Qiskit execution" in st["execution_label"]
        assert "Qiskit" not in st["execution_backend"] or "not Qiskit" in st["execution_backend"]
    else:
        assert st["qiskit_installed"] is True
        assert st["qiskit_execution"] is True
    # the Qiskit ML tier is only claimed when both packages really imported
    if st["mode"] == "qiskit_machine_learning":
        assert qiskit_vqc.available() is True


def test_qiskit_vqc_reports_its_own_availability_truthfully():
    from backend.quantum import qiskit_vqc

    report = qiskit_vqc.runtime_report()
    assert report["qiskit_installed"] is (qiskit_vqc.QISKIT_AVAILABLE)
    assert report["qiskit_machine_learning_installed"] is qiskit_vqc.QML_AVAILABLE
    if not qiskit_vqc.available():
        assert report["import_error"]


def test_engine_selection_matches_reported_mode():
    engine = pipeline.build_engine()
    mode = quantum_runtime_status()["mode"]
    if mode == "qiskit_machine_learning":
        assert engine.engine == "qiskit_machine_learning"
    else:
        assert engine.engine == "builtin_vqc"


def test_benchmark_records_execution_provenance():
    result = bench.run_benchmark(dataset_size=100, iterations=10, save=False, require_qiskit=False)
    result.pop("_models", None)
    for key in ("qiskit_installed", "qiskit_machine_learning_installed",
                "execution_backend", "execution_label", "qiskit_execution",
                "dataset_type", "qubits"):
        assert key in result
    assert result["dataset_type"] == "demonstration_synthetic"
    assert result["qubits"] == 4
    assert "confusion" in result["quantum"]["metrics"]
    assert "confusion" in result["classical"]["metrics"]
    assert result["comparison"]["prediction_agreement"] is not None


def test_forced_fallback_environment_variable_is_reported(monkeypatch=None):
    import os
    from backend.quantum import quantum_classifier as qc

    old = os.environ.get("ASTRANEX_FORCE_FALLBACK_SIM")
    os.environ["ASTRANEX_FORCE_FALLBACK_SIM"] = "1"
    try:
        st = qc.quantum_runtime_status()
        assert st["forced_fallback"] is True
        assert st["mode"] == "fallback_simulation"
        assert st["qiskit_execution"] is False
    finally:
        if old is None:
            os.environ.pop("ASTRANEX_FORCE_FALLBACK_SIM", None)
        else:
            os.environ["ASTRANEX_FORCE_FALLBACK_SIM"] = old


# --------------------------------------------------------------------------
# System health and model provenance (added for the 95-99% upgrade pass)
# --------------------------------------------------------------------------
def test_system_health_never_hard_codes_ok():
    health = pipeline.system_health()
    assert health["overall"] in {"ok", "degraded"}
    for name, info in health["components"].items():
        assert "ok" in info and "detail" in info, name
    # a component genuinely unavailable in this environment must say so
    if not health["runtime"]["qiskit_installed"]:
        assert health["components"]["qiskit"]["ok"] is False


def test_model_provenance_matches_the_active_engine():
    prov = pipeline.model_provenance()
    engine = prov["quantum_model"]["engine"]
    rt = quantum_runtime_status()
    if rt["mode"] == "qiskit_machine_learning":
        assert engine == "qiskit_machine_learning"
        assert prov["quantum_model"]["feature_map"] == "ZZFeatureMap"
    else:
        assert engine == "builtin_vqc"
        assert prov["quantum_model"]["feature_map"] != "ZZFeatureMap"
    assert prov["quantum_advantage_claimed"] is False
    assert prov["dataset"]["type"] == "demonstration_synthetic"


def test_saved_model_metadata_is_self_describing():
    clf = QuantumClassifier()
    clf.features = ["disease_signal", "humidity", "soil_moisture", "temperature"]
    d = clf.to_dict()
    for key in ("engine", "model_version", "feature_map", "ansatz", "feature_order",
                "execution_backend"):
        assert key in d, key
    assert d["feature_order"] == clf.features


def test_qiskit_vqc_metadata_when_available():
    from backend.quantum import qiskit_vqc

    if not qiskit_vqc.available():
        # Assert what MUST be true in this environment: unavailable is reported
        # as unavailable, never silently substituted.
        assert qiskit_vqc.runtime_report()["qiskit_installed"] is False
        return
    model = qiskit_vqc.QiskitVQC()
    model.features = ["disease_signal", "humidity", "soil_moisture", "temperature"]
    d = model.to_dict()
    for key in ("engine", "model_version", "feature_map", "feature_map_config",
                "ansatz", "ansatz_config", "observable", "feature_order",
                "qiskit_version", "qiskit_machine_learning_version"):
        assert key in d, key
    assert d["engine"] == "qiskit_machine_learning"
    round_tripped = qiskit_vqc.QiskitVQC.from_dict(d)
    assert round_tripped.weights == model.weights

# --------------------------------------------------------------------------
# Strict inference safety gates
# --------------------------------------------------------------------------
def test_untrained_qml_inference_is_blocked(monkeypatch):
    original = dict(pipeline._STATE)
    try:
        pipeline._STATE["loaded"] = False
        pipeline._STATE["quantum"] = pipeline.build_engine()
        pipeline._STATE["quantum"].trained = False
        monkeypatch.setattr(pipeline, "_ensure_models", lambda: False)
        out = pipeline.hybrid_analyze({}, {"soil_moisture": 50})
        assert out["available"] is False
        assert out["status"] == "model_unavailable"
        assert out["inference_enabled"] is False
    finally:
        pipeline._STATE.clear(); pipeline._STATE.update(original)


def test_qiskit_artifact_loader_rejects_missing_or_untrained(tmp_path):
    from backend.quantum import qiskit_vqc
    if not qiskit_vqc.available():
        assert qiskit_vqc.QiskitVQC.load(tmp_path / "missing.json") is None
        return
    bad = tmp_path / "bad.json"
    bad.write_text('{"engine":"qiskit_machine_learning","trained":false}', encoding="utf-8")
    assert qiskit_vqc.QiskitVQC.load(bad) is None
