# Setup

## Requirements
- Python 3.10 or newer
- ~200 MB disk for dependencies (plus ~94 MB if you prepare the optional vision model)

## Install and run

```bash
cd AstraNex_KshetraSaarthi
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/>.

`./run_backend.sh` runs the same command with sensible defaults.

## Verify Qiskit actually runs

```bash
python -c "import qiskit, qiskit_machine_learning; print(qiskit.__version__, qiskit_machine_learning.__version__)"
python scripts/verify_quantum.py
```

The second command executes a real inference and prints the engine that ran it. If it
reports `fallback_simulation`, Qiskit is not importable in that environment — the app
still works and says so everywhere rather than claiming Qiskit.

## Minimal install

The quantum layer, the engine and the interface all work without Qiskit:

```bash
pip install fastapi "uvicorn[standard]" pydantic python-multipart
```

Qiskit missing means the bundled state-vector simulator runs the circuit, and the
status rail and Quantum lab both say so. Pillow and onnxruntime missing means image
analysis falls back to context-only screening, which the interface also states.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `ASTRANEX_MODEL_PATH` | *(empty)* | Local ONNX vision model. Empty means context/screening mode until prepared. |
| `ASTRANEX_AUTO_DOWNLOAD_MODEL` | `1` | Allow a one-time model download via `huggingface_hub`. |
| `ASTRANEX_MODEL_REPO` | `AbhiCommits/cropguard-models` | Source repository for the vision model. |
| `ASTRANEX_CORS_ORIGINS` | *(empty)* | Extra allowed browser origins, comma separated. |
| `ASTRANEX_FORCE_FALLBACK_SIM` | `0` | Set to `1` to force the bundled simulator even when Qiskit is installed (useful for comparing the two paths). |

## First run checklist

1. The status rail at the top should read **Backend online**.
2. **Quantum layer** shows `Qiskit ML execution`, `Qiskit execution` or `fallback simulation (not Qiskit)`. All three are working states; only the first two involve Qiskit.
3. Open **Quantum lab**. Models are trained automatically on first start if none exist (a few seconds on the built-in simulator; longer with Qiskit ML). Press **Run experimental benchmark** any time to retrain; every metric is recomputed from that run and labelled with the engine that produced it.
4. Open **Field scan**, press **Analyse field**, and watch the pipeline stages advance.
5. Press **Demo mode** in the header for the guided walkthrough — no hardware needed.

## Optional: prepare the vision model

```bash
./prepare_ai_model.sh          # or press "Prepare AI model" in the legacy interface
```

Without it, image uploads are still screened for quality and analysed with sensor and
context evidence; the interface labels this as screening rather than model inference.

## Running tests from a clean checkout

```bash
pip install -r requirements.txt
pip install pytest httpx
pytest
```

No manual database setup is required — `tests/conftest.py` points the backend at a
throwaway SQLite file and initialises its schema before any test module imports
`backend.main`, so a bare `pytest` on a fresh clone never hits a "no such table"
error and never touches your real `backend/astranex.db`.

## System health at a glance

```bash
python scripts/verify_quantum.py
```

or, with the server running, open **About** in the interface, or call:

```bash
curl http://127.0.0.1:8000/api/system/health
```

Every line is measured at call time: backend, database, vision model, sensor system,
weather context, offline sync, Qiskit, Qiskit Machine Learning, the classical model,
the QML model, and the benchmark. Qiskit being unavailable shows as a clearly labelled
`ok: false` line, not a crash — the app still runs on the fallback simulator.

## Troubleshooting

**Backend shows offline.** Check the uvicorn terminal for a traceback and confirm the port. The interface keeps working and queues scans locally; press *Sync queued scans* once the backend is back.

**Quantum layer unavailable.** Classical analysis is unaffected by design. Check the uvicorn log for an import error from `backend/quantum/`. Reinstalling with `pip install -r requirements.txt` resolves most cases.

**Benchmark button does nothing / Quantum lab says training in progress.** Training runs in a background thread; the page refreshes itself while it runs. If it reports `failed`, the message names the reason. Set `ASTRANEX_AUTO_TRAIN=0` to disable first-start training.

**Qiskit is installed but the lab says "built-in simulator".** The app self-tests the Qiskit path on first use (the QNN output must match a direct Statevector calculation). The reason for any failed self-test is shown under *Qiskit note* in the Quantum lab and in `/api/quantum/status`.

**Fonts look different offline.** Typefaces load from Google Fonts. Offline, the system fallback stack is used and the layout is unchanged.

**Port already in use.** `uvicorn backend.main:app --port 8010` and open that port instead.


## Qiskit Machine Learning production benchmark

The production QML path uses `qiskit>=2.1,<3` and `qiskit-machine-learning>=0.9,<1` (ranges, so `pip install` does not fail on a version that is not published for your platform). After a successful install, `pip freeze > requirements.lock` records an exact environment. The application uses `ZZFeatureMap` + `RealAmplitudes` + `EstimatorQNN` with a local state-vector estimator.

Run:

```bash
pip install -r requirements.txt
python -m backend.quantum.train_qiskit --require-qiskit
python scripts/verify_quantum.py --require-qiskit
```

The application will never use random/untrained parameters for quantum inference. If `trained_qiskit_model.json` is absent, untrained, invalid, or incompatible with the active feature pipeline, the API returns `Quantum model unavailable — Training required before QML inference`. The bundled fallback simulator remains available and can be trained and benchmarked too; its artifacts are stored separately (`benchmark_result_fallback_simulation.json`) and labelled **Fallback quantum simulation — not Qiskit execution**.
