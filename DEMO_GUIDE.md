# DEMO GUIDE

AstraNex has two complementary demo surfaces. Both compute results with the
real `backend.engine.analyze_field` engine — nothing shown in either is a
live sensor reading, and every response is explicitly labelled as
simulation/demo data.

## 1. Demo fields (v3.2, unchanged) — `GET /api/demo/fields`, `GET /api/demo/field/{code}`

A small set of pre-configured demonstration fields (`DEMO_FIELDS` in
`backend/main.py`) that walk through the classical engine and, when the
quantum layer is available, the hybrid quantum analysis too. Responses carry
`"data_label": "Simulation Data"`.

## 2. Scenario runner + reset (v3.3, new) — `GET /api/demo/scenarios`, `POST /api/demo/run/{id}`, `POST /api/demo/reset`

Six numbered scenarios matching the six situations judges typically want to
see in a walkthrough:

| id | Scenario | What it demonstrates |
|----|----------|----------------------|
| 1 | Healthy field | Baseline GOOD status, INFO-level alert |
| 2 | Low moisture | Water-stress risk, WATCH/WARNING alert, irrigation reasoning |
| 3 | Disease-risk image | Disease-pattern signal in a humid context, WARNING/CRITICAL alert |
| 4 | Sensor anomaly | An impossible soil-moisture value flagged by `sensor_health`, with a dedicated demo sensor-health payload |
| 5 | Environmental stress | Heat + low humidity during flowering |
| 6 | Quantum analysis | A representative feature vector suited to the Quantum Lab |

```bash
curl http://127.0.0.1:8000/api/demo/scenarios          # list all 6
curl -X POST http://127.0.0.1:8000/api/demo/run/4      # run the sensor-anomaly scenario
curl -X POST http://127.0.0.1:8000/api/demo/reset      # RESET DEMO
```

Every scenario result carries `"demo": true` and a `demo_scenario` block
naming the scenario. **Nothing computed here is written to the real
database** — `backend/services/demo.py` calls `analyze_field()` directly and
returns the result; it never calls `save_observation`, `add_alert`, or any
other persistence function. That is also why `reset()` has nothing real to
delete: it exists as an honest, explicit UI action rather than a silent
no-op.

## One-click walkthrough for a judge

There is no single `/demo` page wired up in the frontend yet (see
`docs/ARCHITECTURE_V3.3.md` § "Not done in this release" — the frontend was
not modified this session beyond a cache-name bump). To demo today:

1. Start the backend (`./run_backend.sh` or the `uvicorn` command in
   `README.md`).
2. Open `http://127.0.0.1:8000/docs` (FastAPI's interactive Swagger UI) and
   drive `/api/demo/scenarios` → `/api/demo/run/{id}` from there, or script
   the `curl` calls above.
3. For the quantum side, follow scenario 6's feature values into
   `/api/quantum/simulate` or the existing Quantum Lab playground in the
   frontend.

A wired-up "Run Demo" button in the frontend that walks all six scenarios in
sequence is the natural next step and is not yet built.

## NOT VERIFIED

These new endpoints were written and syntax-checked (`py_compile`) and
reasoned through by hand, but this sandbox has no `fastapi`/`httpx`
installed and no network access to install them, so **the endpoints above
have never actually been served or hit with a real HTTP request.** Run the
appended tests in `tests/test_api.py` (the ones under
`# ---------------- v3.3 additions ----------------`) in an environment with
dependencies installed before relying on this for a live demo.
