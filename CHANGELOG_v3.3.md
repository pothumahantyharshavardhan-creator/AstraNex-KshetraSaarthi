# CHANGELOG — v3.3.0

This changelog covers only what actually changed in this release. Anything not
listed here (frontend visual layout, mobile breakpoints, i18n, accessibility
audit, offline-sync conflict resolution, farmer/research mode UI split,
quantum experiment replay UI, judge-facing research dashboard UI) was **not**
modified in this pass — see `docs/ARCHITECTURE_V3.3.md` § "Not done in this
release" for the honest list.

## Added

- **`backend/services/data_quality.py`** — unified Data Quality Score
  (completeness, freshness, sensor reliability, image quality, environmental
  consistency), explicitly labelled `data_quality` and never conflated with
  agricultural accuracy. Wired into `engine.analyze_field` as
  `result['data_quality']`.
- **`backend/services/sensor_health.py` (rewritten)** — adds detection of
  repeated/identical ("stuck") readings, non-numeric values, and out-of-order
  timestamps, each with a plain-language `anomalies` explanation and an
  `anomaly_detected` flag. Backward compatible: the original `overall` and
  `sensors` keys are unchanged in shape.
- **`backend/services/alert_engine.py`** — structured alerts with a bounded
  `INFO / WATCH / WARNING / CRITICAL` severity vocabulary and required
  `what / why / check / action` fields. Wired into `engine.analyze_field` as
  `result['alerts']` / `result['alert_level']`.
- **`backend/services/crop_profiles.py` + `config/crops/{tomato,wheat,rice}.json`**
  — externalised, explicitly `NOT_FIELD_VALIDATED` crop thresholds instead of
  numbers hardcoded in `irrigation.py`. Unconfigured crops/stages fall back to
  the original v3.2 defaults unchanged, and unsupported growth stages report
  "Stage-specific guidance unavailable" instead of guessing.
- **`backend/services/timeline.py`** — `field_history()` (24h/7d/30d windows
  over sensor + observation data, with an explicit "not enough historical
  data" state instead of interpolation) and `farm_events_timeline()`
  (chronological merge of analyses, sensor readings, alerts and irrigation
  events).
- **`backend/services/weather.py`** — `WeatherProvider` abstraction
  (`LiveApiProvider` / `CachedProvider` / `OfflineFallbackProvider`). No live
  weather API key is bundled; the live provider is a documented extension
  point. `get_weather()` never raises and never fabricates a live reading.
- **`backend/services/demo.py`** — six Demo Mode scenarios (healthy field,
  low moisture, disease-risk image, sensor anomaly, environmental stress,
  quantum analysis) run through the real `analyze_field` engine in-memory.
  Every result is tagged `demo: true`; nothing is persisted, so `RESET DEMO`
  has nothing real to delete.
- **`backend/quantum/feature_sensitivity.py`** — experimental circuit
  perturb-and-measure sensitivity sweep over the quantum pipeline's selected
  features. Every response carries a `disclaimer` stating this is not
  validated feature importance.
- New API endpoints: `GET /api/crops`, `GET /api/field-history`,
  `GET /api/timeline`, `GET /api/weather`, `GET /api/demo/scenarios`,
  `POST /api/demo/run/{id}`, `POST /api/demo/reset`,
  `GET /api/quantum/feature-sensitivity`.
- New `alerts` table columns `level` and `detail_json` (additive migration
  via the existing `_ensure_column` mechanism — no destructive schema change).
- `backend/db.recent_sensor_history()` and `backend/db.list_irrigation_events()`
  read helpers.
- New tests: `test_data_quality.py`, `test_sensor_anomaly.py`,
  `test_alert_engine.py`, `test_crop_profiles.py`, `test_timeline.py`, plus
  nine new cases appended to `test_api.py` covering the endpoints above.

## Changed

- `backend/services/irrigation.decide()` now accepts an optional `crop`
  parameter and consults `crop_profiles` for the moisture threshold, falling
  back to the exact v3.2 hardcoded defaults when no profile/crop is given —
  verified to produce identical output to v3.2 for every existing test case.
- `backend/main.py` app version bumped `3.2.0` → `3.3.0`; the sensor-ingest
  endpoint now looks up recent per-device history for stuck-sensor detection
  and raises a structured alert on any detected sensor anomaly.
- `frontend/sw.js` cache name bumped to `astranex-shell-v3.3.0` so the service
  worker picks up frontend changes on next deploy.

## Verified this session

- All eight pre-existing `tests/test_engine.py` functions re-run by hand
  against the new code: **0 regressions**.
- All 35 new pure-Python test functions (`test_data_quality.py`,
  `test_sensor_anomaly.py`, `test_alert_engine.py`, `test_crop_profiles.py`,
  `test_timeline.py`) executed directly with a small manual runner and pass.
- `python3 -m py_compile` run on every modified/added `.py` file — no syntax
  errors.

## NOT VERIFIED this session (see TESTING.md for why and what to run)

- The full `pytest` suite, `test_api.py` (needs `fastapi`+`httpx`), and any
  `backend/quantum/*` behaviour (needs `qiskit`+`qiskit-machine-learning`) —
  **this sandbox has no network access to install them.** Run
  `pip install -r requirements.txt && pytest` in your own environment before
  relying on this build.
- The new FastAPI endpoints listed above have never actually been served or
  hit with a real HTTP request in this session — only reasoned about and
  syntax-checked.
- Frontend behaviour is unchanged apart from the one-line service-worker
  cache bump; nothing new was added to `frontend/` to surface these new
  endpoints in the UI.
