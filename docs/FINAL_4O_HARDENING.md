# FINAL 4.O — Hardening Pass

This release strengthens the existing AstraNex / KshetraSaarthi build without changing its identity or workflow.

## Strengthened areas
- Exact Qiskit/Qiskit Machine Learning versions remain pinned.
- Only genuine Qiskit Machine Learning execution may create the production benchmark artifact.
- Untrained or incompatible QML models are blocked from inference.
- Stale fallback benchmark numbers are removed from the packaged build.
- Vision status distinguishes model-file presence, ONNX Runtime readiness and real inference.
- `/api/readiness` separates working demo readiness from QML production readiness.
- System health reports missing vision weights honestly.
- Frontend quantum runtime wording is backend-driven.
- Quantum Lab wording matches `ZZFeatureMap + RealAmplitudes + EstimatorQNN`.
- Synthetic labels and lack of field validation remain explicit.

## Validation
```bash
python -m compileall backend
pytest -q
python scripts/verify_quantum.py
```

The test suite validates the fallback-capable software path. `verify_quantum.py` intentionally fails unless the pinned Qiskit/QML dependencies and a genuine trained Qiskit artifact are present.

## External prerequisites for full production-style demo
1. Install the pinned Qiskit/QML dependencies.
2. Run `python -m backend.quantum.train_qiskit` to generate `trained_qiskit_model.json`.
3. Prepare `cropguard.onnx` and its class map for real image inference.
4. Replace synthetic labels with field-validated agricultural labels before making real-world accuracy claims.
5. Quantum hardware remains future work.
