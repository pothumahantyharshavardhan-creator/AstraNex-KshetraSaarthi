# AstraNex — KshetraSaarthi v3.2 Quantum-Enhanced Build

See `docs/CHANGELOG.md` for the full list of fixes and additions.

## Verification performed on this build
- 90 automated tests pass (engine, quantum, quantum-state physics, API), run against a stand-in for FastAPI/Pydantic in an offline sandbox.
- The interface was exercised in headless Chromium: all 11 pages render with no JavaScript errors; the map click, scan, playground, offline-queue rules and mobile/tablet layouts were checked.
- `python scripts/verify_quantum.py` passes for the built-in simulator artifacts that ship in this package.

## Not verified (cannot be, from the build environment)
1. **The Qiskit paths have never been executed.** Qiskit / Qiskit Machine Learning were not installable offline. The code self-tests on first use and degrades honestly, but run `python scripts/verify_quantum.py --require-qiskit` on your machine to confirm.
2. **Real FastAPI/Pydantic** were not available; run `pytest -q` after `pip install -r requirements.txt pytest httpx`.
3. Vision weights (ONNX) and expert-labelled field validation remain external release gates, as before.

The shipped benchmark is from the **built-in simulator** and is labelled as such everywhere.
