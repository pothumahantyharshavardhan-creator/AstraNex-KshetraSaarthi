# Architecture

## Dependency map (what calls what)

```
frontend/index.html
  └ assets/js/app.js ── router, field scan, demo mode
      ├ api.js      ── fetch wrapper, offline queue, health polling
      ├ pages.js    ── page renderers
      ├ viz.js      ── circuit SVG, meters, India map
      ├ data.js     ── disease library, research copy, status badges
      └ i18n.js     ── EN / TE / HI strings
            │ HTTP
            ▼
backend/main.py (FastAPI)
  ├ engine.analyze_field ───── services/fusion, services/irrigation
  ├ services/inference.vision ─ ONNX Runtime + Pillow quality screening
  ├ services/sensor_health ──── range, freshness and noise assessment
  ├ db ──────────────────────── SQLite: observations, sensors, devices,
  │                             alerts, feedback, irrigation, sync_queue,
  │                             farmer_profiles, quantum_runs (new)
  └ quantum/api.router (new)
        └ quantum/pipeline
              ├ feature_encoder ── extract → normalise → select → angles
              ├ quantum_classifier ─ Qiskit QuantumCircuit / bundled simulator
              ├ classical_baseline ─ logistic regression
              ├ dataset ──────────── demonstration scenarios via engine
              └ benchmark ────────── train/test metrics for both models
```

## Request flow for one field scan

1. The browser posts to `/api/analyze-multimodal` (image present) or `/api/analyze` (context only).
2. `main.py` validates ranges and the MIME type, scores image quality with Pillow, then calls `vision.analyze` when an image is present.
3. `engine.analyze_field` fuses vision evidence, sensor values, weather and reliability into risks, confidence, health score, irrigation guidance and reasons.
4. The result is stored via `db.save_observation`; red or amber results also raise an alert.
5. The browser posts the result to `/api/quantum/analyze-result`. The hybrid layer extracts eight features, encodes four onto qubits, evaluates both models and returns an early-warning level.
6. If step 5 fails for any reason, the browser keeps and displays the step-4 result. The quantum panel shows "Quantum layer unavailable. Classical agricultural analysis continues normally."

## Why the quantum call is a second request

Keeping `/api/analyze` and `/api/analyze-multimodal` byte-for-byte compatible was a
requirement: existing clients, the legacy interface at `/legacy` and the stored
observation schema all keep working. A separate call also makes the failure mode
obvious — the classical result is already on screen before the quantum layer is asked
for anything.

## Database

Existing tables are untouched. One table is added:

```sql
quantum_runs(
  id, created_at, observation_id, field_id,
  feature_vector_json, selected_features_json,
  classical_prediction, quantum_prediction, confidence,
  qubits, circuit_depth, backend, execution_ms, warning_level
)
```

Only model telemetry is stored. No additional farmer-identifying information is written.

## Offline design

- The interface shell is cached by `sw.js`; API responses are never cached.
- A failed scan is queued in `localStorage` with a `client_event_id`.
- `POST /api/sync` accepts the queue and de-duplicates on `client_event_id`, so a retry cannot create duplicate observations.
- Local history keeps the last 40 scans on the device so the Intelligence page works without a backend.

## Scaling notes

Crops, states and sensors are data, not code paths: `REGIONAL_CROPS` in `main.py`, the
crop list in `data.js` and the disease library are all additive. The SQLite schema uses
no SQLite-specific types, so a PostgreSQL migration is a connection change plus the
`AUTOINCREMENT` keyword. Multispectral bands would enter as extra entries in
`FEATURE_NAMES` with ranges in `FEATURE_RANGES`; selection and encoding already handle
an arbitrary feature count with `k` qubits.
