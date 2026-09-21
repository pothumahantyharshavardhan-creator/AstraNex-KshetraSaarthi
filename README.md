# AstraNex — KshetraSaarthi
## Quantum Agricultural Intelligence
**Early pest and crop-disease warning using hybrid AI + quantum machine learning**

Built for **Qiskit Fall Fest 2026** on top of the existing AstraNex agricultural
decision-support backend. The classical system is unchanged and still authoritative;
the quantum layer is additive and experimental.

**Current version: v3.3.0.** See [`VERSION.txt`](VERSION.txt) and
[`CHANGELOG_v3.3.md`](CHANGELOG_v3.3.md) for what changed from v3.2, and
[`docs/ARCHITECTURE_V3.3.md`](docs/ARCHITECTURE_V3.3.md) for an honest list of
what v3.3 does and does not include.

---

## Run it

```bash
cd AstraNex_KshetraSaarthi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # includes Qiskit
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/>. The backend serves the interface from the same origin,
so there are no CORS problems. `./run_backend.sh` does the same thing.

### Verify the quantum stack

```bash
python scripts/verify_quantum.py
```

Prints whether Qiskit and qiskit-machine-learning are installed, their versions, which
engine will execute the circuit, and the result of a real inference.

**Quantum features (v3.2).** The Quantum lab shows, for the circuit that actually ran: a Bloch sphere per qubit (from the
reduced density matrix), per-qubit entanglement entropy and the Meyer–Wallach global entanglement, exact basis-state
probabilities, seeded finite-shot measurement counts, and a simplified depolarising-noise sweep. An interactive
*playground* re-runs the circuit as you move the four encoded features. All values derive from the simulated state vector;
none are hard-coded, and no hardware is involved.

**Qiskit is optional, and never faked.** With `qiskit` + `qiskit-machine-learning`
installed, a `ZZFeatureMap` → `RealAmplitudes` → `EstimatorQNN` model runs and the
backend is reported as Qiskit Machine Learning. With only `qiskit`, the built-in
circuit runs through `Statevector`. With neither, a bundled simulator runs the same
circuit and everything — status rail, Quantum lab, API, benchmark file — labels it
**"Fallback quantum simulation — not Qiskit execution"**. Set
`ASTRANEX_FORCE_FALLBACK_SIM=1` to compare the paths.

### Tests

```bash
pip install pytest httpx
pytest                      # engine, quantum layer, API contract, fallback behaviour
```

`tests/test_api.py` skips itself automatically if FastAPI's test stack is not installed.

---

## What this prototype is

An end-to-end agricultural early-warning workflow:

```
crop image + field sensors + weather context
        ↓  existing AstraNex vision / fusion / risk engine
8 multimodal agricultural features
        ↓  ranking and selection (training split only)
4 selected features → angle encoding → 4 qubits
        ↓                                    ↓
classical baseline                  variational quantum circuit
        └────────────── comparison ──────────┘
        ↓
early-warning level, confidence, recommended action
        ↓
farmers · RBKs · departments · insurers
```

### What is demonstrated today
- Image quality screening, ONNX vision inference, sensor-health weighting, multimodal fusion, risk bands, irrigation decision support, alerts, history, offline queue and sync — all preserved from the existing system.
- A real 4-qubit variational classifier — Qiskit Machine Learning `EstimatorQNN` (`ZZFeatureMap` + `RealAmplitudes`) when available, otherwise a Qiskit `Statevector` circuit, otherwise a clearly-labelled bundled simulator — trained by SPSA on features produced by that pipeline.
- A classical logistic-regression baseline on the identical features and split, with accuracy, precision, recall, F1 and inference time computed at runtime.
- Demo mode, institutional analytics, an insurer evidence trail and a stylised national field view.

### What is **not** claimed
- No quantum advantage, and no claim that the quantum model is more accurate. Benchmark numbers come only from an executed run on the labelled demonstration dataset, and each one is tagged with the engine that produced it (Qiskit ML, Qiskit state-vector, or the built-in simulator).
- No quantum-hardware execution — the circuit runs on a simulator.
- No real multispectral or drone processing. The architecture accepts those inputs; the prototype does not have that data.
- No deployment, no national monitoring, no validated outbreak prediction, no pesticide prescription, no insurance or financial recommendation.

---

## Project layout

```
AstraNex_KshetraSaarthi/
├── backend/
│   ├── main.py                 FastAPI app — existing endpoints unchanged
│   ├── engine.py               risk fusion engine (unchanged)
│   ├── db.py                   SQLite schema + additive quantum_runs table
│   ├── services/               inference, fusion, sensor health, irrigation (unchanged)
│   └── quantum/                NEW experimental layer
│       ├── feature_encoder.py  agricultural features → normalise → select → angles
│       ├── qiskit_vqc.py       Qiskit ML engine: ZZFeatureMap + RealAmplitudes + EstimatorQNN
│       ├── quantum_classifier.py  built-in circuit (Qiskit Statevector / labelled fallback)
│       ├── benchmark.py        real train/test evaluation, one artifact per execution mode
│       ├── quantum_state.py    Bloch vectors, entanglement, shots, noise model, true depth
│       ├── pipeline.py         hybrid analysis, system_health(), model_provenance()
│       ├── classical_baseline.py  logistic regression on identical features
│       ├── dataset.py          reproducible demonstration dataset
│       ├── pipeline.py         hybrid analysis service with safe fallbacks
│       └── api.py              /api/quantum/* router
├── frontend/                   NEW interface (index.html + assets/css + assets/js)
├── legacy/astranex_frontend.html   original interface, still served at /legacy
├── scripts/verify_quantum.py   prints Qiskit status, selected engine, a real inference, system health
├── tests/                      engine + quantum + API tests, isolated test database (conftest.py)
├── docs/                       architecture, quantum notes, changelog
└── hardware/                   ESP32 sensor sketch (unchanged)
```

## API

Existing endpoints are untouched: `/api/analyze`, `/api/analyze-image`,
`/api/analyze-multimodal`, `/api/sensors`, `/api/history`, `/api/alerts`, `/api/sync`,
`/api/fields`, `/api/farmer-profile`, `/api/irrigation`, `/api/validation`,
`/api/model-status`, `/api/model-capabilities`, `/api/geocode/*`.

Added: `/api/quantum/status`, `/circuit`, `/features`, `/analyze`, `/analyze-result`,
`/benchmark` (GET and POST), `/training`, `/runs`, `/health`, `/provenance`, plus
`/api/demo/fields`, `/api/demo/field/{code}`, `/api/analytics/summary`,
`/api/insurer/evidence` and `/api/system/health` (a single consolidated,
honestly-reported status for every subsystem — backend, database, vision model,
sensors, weather context, offline sync, Qiskit, Qiskit ML, classical model, QML
model, benchmark).

Interactive documentation: <http://127.0.0.1:8000/docs>.

**v3.3 additions:** `/api/crops`, `/api/field-history`, `/api/timeline`,
`/api/weather`, `/api/demo/scenarios`, `/api/demo/run/{id}`,
`/api/demo/reset`, `/api/quantum/feature-sensitivity`. See
`CHANGELOG_v3.3.md` for what each does and `TESTING.md` for what has and
hasn't actually been executed against them.

## Documentation

- [`SETUP.md`](SETUP.md) — install, run, troubleshoot, environment variables
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — data flow and dependency map
- [`docs/ARCHITECTURE_V3.3.md`](docs/ARCHITECTURE_V3.3.md) — v3.3 additions, and an honest list of what was *not* done
- [`docs/QUANTUM.md`](docs/QUANTUM.md) — circuit, features, training, benchmark methodology
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) / [`CHANGELOG_v3.3.md`](CHANGELOG_v3.3.md) — what changed in each build
- [`SECURITY.md`](SECURITY.md) — security review notes for v3.3
- [`TESTING.md`](TESTING.md) — what was actually run vs. reasoned through, this session
- [`DEMO_GUIDE.md`](DEMO_GUIDE.md) — the demo-fields and demo-scenario walkthroughs

## Safety

AstraNex provides preliminary screening and decision support, not a confirmed diagnosis.
Confirm symptoms in the field and follow local agricultural guidance before treatment.
No chemical product is prescribed and no irrigation hardware is actuated.
