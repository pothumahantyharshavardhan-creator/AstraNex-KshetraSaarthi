# AstraNex — KshetraSaarthi · v3.2.0

**Quantum Agricultural Intelligence** — presentation-ready hybrid classical + experimental quantum ML prototype for early pest and crop-disease warning.

## Fast presentation launch

```bash
./run_presentation.sh
```

Then open `http://127.0.0.1:8000/`.

This launcher deliberately uses the bundled, clearly labelled fallback quantum simulator when Qiskit is unavailable. It never pretends that a fallback run is Qiskit execution.

## What is new in v3.2 (quantum)

Open **Quantum lab**: it now draws a **Bloch sphere per qubit**, reports **entanglement** (per-qubit entropy and the
Meyer–Wallach measure), and has a **playground** where you drag the four encoded features and watch the circuit re-run —
exact probabilities, sampled measurement shots, both risk predictions, and a simulated-noise robustness curve.
Everything is computed from the circuit's real state vector. The benchmark button now works with or without Qiskit,
and each result says exactly what executed.

## Recommended 5-minute demo

1. **Home** — explain the problem and the hybrid data flow.
2. **Field scan** — run a live synthetic/manual field analysis and show the warning decision.
3. **Quantum lab** — show the 4-qubit circuit, encoded features, runtime provenance and benchmark controls.
4. **Early warnings** — show how the risk signal becomes a scouting action.
5. **Analytics / India network** — show institutional views without implying national deployment.
6. **Research / About** — show methodology, provenance and limitations when asked about quantum advantage or validation.

## Important presentation wording

Say: **“Experimental quantum ML layer running in simulation.”**

Do not say: “quantum advantage,” “quantum hardware,” “field-validated outbreak prediction,” or “real multispectral/drone processing.” Those capabilities are future integration stages in this prototype.

## Full verification

```bash
python scripts/verify_quantum.py
pytest -q
python -m compileall -q backend scripts
```

If Qiskit and Qiskit Machine Learning are installed, the preferred execution tier is the real Qiskit ML path. Otherwise the fallback simulator remains available and is labelled throughout the UI and API.

See `PRESENTATION_READY.md` for the complete presenter checklist.
