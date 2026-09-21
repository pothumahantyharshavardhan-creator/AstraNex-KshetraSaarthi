# AstraNex QFF2026 — Upgrade Verification

## Implemented
- Pinned Qiskit 2.5.2 and Qiskit Machine Learning 0.9.1.
- Updated the real QML path for the Qiskit 2.x / QML 0.9.x API using `ZZFeatureMap`, `RealAmplitudes`, `StatevectorEstimator`, and `EstimatorQNN`.
- Added strict persisted-model validation: trained flag, feature order/count, circuit configuration, parameter count, finite weights, and runtime compatibility.
- Quantum inference is blocked when a QML model is missing, untrained, invalid, or incompatible.
- Preserved the fallback simulator and labelled it exactly as `Fallback quantum simulation — not Qiskit execution`.
- Production benchmark saving is blocked unless the real Qiskit Machine Learning engine actually executed.
- Added reproducible `python -m backend.quantum.train_qiskit` training entry point and `python -m scripts.verify_quantum` verification command.
- Updated Quantum Lab UI to read runtime/model/circuit state dynamically and to distinguish QML execution from fallback execution.
- Added safety tests for missing/untrained QML inference and artifact loading.

## Verification performed in the packaging environment
- `python -m compileall -q backend` — PASS
- `pytest -q` — PASS
- `node --check frontend/assets/js/*.js` — PASS
- shell syntax checks — PASS
- FastAPI smoke tests for system health, quantum status, circuit, benchmark, training and provenance — PASS

## Environment limitation
The packaging environment has Python 3.13.5 but does not have Qiskit/Qiskit Machine Learning installed, and outbound PyPI access is unavailable. Therefore it was **not possible to truthfully execute the real Qiskit ML training pipeline here**. No fake `trained_qiskit_model.json` or fake Qiskit benchmark has been created.

`backend/quantum/benchmark_result.json` is intentionally an `awaiting_benchmark` artifact rather than fabricated Qiskit results. Install the pinned dependencies and run:

```bash
pip install -r requirements.txt
python -m backend.quantum.train_qiskit
python -m scripts.verify_quantum
```

Only after those commands execute successfully will the project contain a genuine `backend/quantum/trained_qiskit_model.json` and a genuine Qiskit ML `benchmark_result.json`.
