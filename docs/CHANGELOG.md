## v3.2.0 — Quantum-enhanced build (audit + fixes)

### Fixed
- **Map clicks resolved to the wrong place.** The map image has a padded plot area; the old code assumed lon 68–98 across the whole image (2–9° error). The image is now cropped and calibrated (67.01°E / 38.01°N origin, 31.8 px per degree) and all map code shares one projection.
- **Benchmark could never run without Qiskit** (`train_now` always failed). It now runs in every mode; artifacts are per mode and labelled.
- `circuit_depth` reported the gate count; it is now the true depth (also stored in the database).
- Re-trained models with a different selected-feature set were discarded on restart.
- Health status contradicted the alert colour (severe disease scored 78 → "GOOD"). Red now implies ACTION NEEDED (score ≤ 49); amber implies WATCH (≤ 74).
- Offline queue: any error (including 422s and render errors) was queued as "offline" and could block syncing forever. Only genuine network failures queue now; `/api/sync` processes records independently, keeps location, and reports retryable vs invalid records.
- Sensor timestamps that were device uptime seconds were stored as calendar times; noise detection never received the previous reading.
- Farmer dashboard marked healthy crops "Attention" (colour bands ignored direction); research links navigated to Home; About page health went stale; raw issue codes shown to farmers.
- Circuit tooltips and Quantum-lab labels always said ZZFeatureMap/RealAmplitudes even when the built-in circuit ran; circuit qubit labels overlapped gates.
- Header overflowed on phones (pre-existing) and the 11-link nav overflowed between ~860–1180px.
- Service worker served stale code forever and answered failed asset requests with HTML.
- Vision: plant-gate failure was treated as "not a plant"; class list now read from `classes.json` and validated against the network output width; image dimension cap; missing Pillow reported clearly.
- DB connections leaked on errors; geocoding was unthrottled/uncached; unused `ASTRANEX_AUTO_TRAIN` first-run gap (no Qiskit model ever shipped).

### Added
- `quantum_state.py`: Bloch vectors, entanglement entropy / purity / Meyer–Wallach, seeded shot sampling, depolarising-noise sweep, true depth.
- `/api/quantum/simulate`, `/api/quantum/feature-ranges`; Quantum lab Bloch spheres, interactive playground, engine-aware labels; Bloch spheres in scan results.
- Automatic background training on first start (`ASTRANEX_AUTO_TRAIN=0` disables); Qiskit self-test with recorded failure reasons; runtime error tracking.
- Quantum visual theme, calibrated India map with India highlighted, WAL-mode SQLite, tests for all of the above (90 total).
- Requirements use version ranges instead of exact pins.

## v3.1 — Final hardening + selectable field location

### Fixed
- Active Field Scan now contains the India map asset, clickable coordinate selection, search selection and GPS selection.
- Location coordinates are normalized before display, fixing the prior string-coordinate rendering failure.
- Scan results persist selected latitude/longitude/name provenance.
- Reverse geocoding rejects non-India results.
- Service-worker cache now includes the map asset and uses a new cache version.

### Added
- `scripts/check_model.py` for ONNX/class-map/runtime validation.
- `scripts/validate_field_dataset.py` plus `validation/` template and methodology.
- Separate readiness gates for demo, real vision inference, Qiskit ML and field validation.

### Integrity rule
No 95–99% agricultural accuracy figure is invented. A field accuracy percentage is reported only from expert-labelled field samples supplied to the validation tool.

# Changelog

## v2.4 — Full audit + reliability upgrade

### Fixed
- **Idempotent alerts:** repeated `/api/analyze` requests with the same `client_event_id` no longer create duplicate alerts.
- **Offline sync parity:** `/api/sync` now uses the same storage/alert path as live analysis, so synced high/moderate observations can populate the warning feed consistently.
- **Foreign-key validation:** analysis, sensor, feedback and simulated irrigation requests reject unknown field/observation IDs with HTTP 422 instead of surfacing SQLite errors as HTTP 500 responses.
- **Image validation:** uploaded bytes are now decoded/verified by Pillow before being persisted; invalid files are rejected rather than being accepted based only on their MIME header.
- **Timing telemetry:** multimodal preprocessing/validation time is reported separately from fusion time.
- **Background training race:** quantum background-training startup now checks the shared training state under the same lock used by synchronous training.
- **Quantum API cleanup:** removed a dead `if True` branch in the feature endpoint.
- **Verification script:** `scripts/verify_quantum.py` now works both as a module and as a directly executed script.

### Hardened
- Request text fields are normalised and empty values are rejected where they are used as analysis dimensions.
- Numeric request fields are checked for finite values in addition to range constraints.
- Offline sync batches are capped at 60 records, matching the browser queue's practical bound.

### Verified
- `pytest -q` — **64/64 passed** after the upgrade.
- `python -m compileall -q backend` — PASS.
- `node --check` for every frontend JavaScript module — PASS.
- Existing API contracts and quantum fallback honesty tests remain green.

### Environment limitation
The packaging environment still does not contain Qiskit, Qiskit Machine Learning, ONNX Runtime or model weights, so the real Qiskit ML execution tier and real vision inference cannot be exercised here. The project continues to report those prerequisites explicitly instead of fabricating readiness.


## v2.2 — 95–99% completeness pass

### Fixed
- **Test database isolation (the §37 bug).** `backend/db.py`'s `DB_PATH` is now overridable via `ASTRANEX_DB_PATH`. `tests/conftest.py` sets it to a fresh temp file and calls `init_db()` directly, before any test module can import `backend.main` — so `pytest` on a clean checkout never depends on FastAPI's lifespan event firing (it didn't reliably, with a bare `TestClient(app)` and no `with` block) and never touches a developer's real `backend/astranex.db`. Covered by `test_database_endpoints_work_with_no_manual_setup`.
- Encoding terminology no longer conflates the two engines (§20): copy that used to say "angle-encoded" unconditionally now says "encoded — the Quantum Lab names the exact method," and the Research page explains both ZZFeatureMap and angle-encoding paths by name, tied to which engine actually ran.

### Added
- **`GET /api/system/health`** and **`GET /api/quantum/health`** (§54) — a consolidated, honestly-reported status for backend, database, vision model, sensors, weather context, offline sync, Qiskit, Qiskit ML, the classical model, the QML model and the benchmark. Rendered live on the **About** page.
- **`GET /api/quantum/provenance`** (§55) — dataset type and caveat, selected features and method, classical algorithm, quantum engine, feature map, ansatz, trained state, and an explicit `quantum_advantage_claimed: false`. Rendered live on **About**.
- **Richer saved-model metadata** (§9): both `trained_model.json` and `trained_qiskit_model.json` now carry `engine`, `model_version`, feature-map/ansatz name *and configuration*, `feature_order`, `qiskit_version`, `qiskit_machine_learning_version` (where applicable) and full training metadata. Round-trip tested.
- **`benchmark_result.json` top-level provenance fields** (§18): `dataset_type`, `qiskit_installed`, `qiskit_machine_learning_installed`, `execution_backend`, `execution_label`, `qiskit_execution`, `qubits`, `quantum_engine`, `model_version`, `hardware_execution: false`, `quantum_advantage_claimed: false`, plus per-model `feature_map` / `ansatz` fields.
- **`scripts/verify_quantum.py`** now also prints the full system-health block.
- **"LIVE INPUT"** tag on field-scan results and an explicit **"DEMO MODE · SYNTHETIC / SIMULATED INPUTS"** tag in the demo-mode header (§49, §50) — the two are visually distinct everywhere.
- 8 new tests: system-health shape, provenance-matches-active-engine, saved-metadata self-description, Qiskit-ML metadata round-trip (skips cleanly without Qiskit ML), 4 new API contract tests for the health/provenance endpoints and the database-isolation regression.

### Verified this pass (§53, §67, §70 — only claiming what was actually run)
- `python -m compileall backend` — clean.
- `pytest` equivalent (`/tmp/run_tests.py`, since fastapi/qiskit aren't installed in this build sandbox) — **38/38 passed**.
- Every frontend `fetch` target in `assets/js/api.js` cross-checked against every FastAPI route in `main.py` and `quantum/api.py` — no dead references (§35).
- `scripts/verify_quantum.py` executed end to end: reports `qiskit_installed: false` truthfully, selects the `builtin_vqc` engine, executes a real inference, and prints full system health.
- **Not verified in this sandbox** (no network access to install packages): the `qiskit_machine_learning` execution tier itself. `qiskit_vqc.py`'s `to_dict`/`from_dict` round trip and metadata shape are unit-tested with `pytest.importorskip`, but the tier has not been exercised end-to-end against a real Qiskit install. Run `pip install -r requirements.txt && python scripts/verify_quantum.py` to confirm on your machine — the code path exists and is the preferred path (§59) whenever both packages import successfully.


## v2.1 — Qiskit execution path

### Added
- **`backend/quantum/qiskit_vqc.py`** — a genuine Qiskit Machine Learning engine: `ZZFeatureMap` + `RealAmplitudes` composed into an `EstimatorQNN` with a `Z⊗Z⊗Z⊗Z` observable. Selected automatically whenever `qiskit` and `qiskit-machine-learning` import. The circuit shown in the UI is read back from the Qiskit object.
- **Three-tier backend reporting**: `qiskit_machine_learning`, `qiskit_statevector`, `fallback_simulation`. The fallback is labelled **"Fallback quantum simulation — not Qiskit execution"** in the API, the status rail, the Quantum lab and the benchmark file. Tests assert it can never be reported as Qiskit.
- **`scripts/verify_quantum.py`** — prints Qiskit/QML availability and versions, the selected engine, and the outcome of a real inference.
- **Quantum layer status panel** in the Quantum lab (§18): Qiskit, QML package, model state, qubits, encoding, ansatz, backend, execution, circuit executed, status — all from the backend.
- Confusion matrices for both models, metric bar charts, prediction agreement and backend provenance chips in the benchmark panel.
- A **current-scan feature panel** in the Quantum lab showing the values actually encoded onto each qubit for the latest scan on this device.
- **Roadmap section** on the home page separating implemented capability from drone, multispectral, satellite, field-validation and hardware stages.
- **Sensor and weather panel** on the Intelligence page, showing ESP32/simulator readings and how they enter the feature pipeline.
- **Local trend charts** in Analytics, built only from scans stored on the device (fewer than two scans says so rather than inventing history).
- 5 quantum tests and 2 API tests covering execution provenance and forced fallback.

### Changed
- `requirements.txt`: `qiskit>=1.1`, `qiskit-machine-learning>=0.8`, `scikit-learn`, `numpy`.
- `benchmark_result.json` regenerated by the final implementation, now carrying `dataset_type`, `qubits`, execution provenance and circuit metadata.
- `/api/health` reports `mode`, `execution_label` and `qiskit_execution`.
- Field scan progress now mirrors the backend stages: image received, quality checked, sensor context, weather context, feature extraction, classical baseline, quantum circuit, risk synthesis.
- Navigation: "Field network" renamed **India network**.


## v2.0 — Qiskit Fall Fest 2026 build

### Preserved (unchanged behaviour)
- `backend/engine.py`, `backend/schemas.py` and every module in `backend/services/` — risk fusion, ONNX vision inference, sensor-health assessment and irrigation logic are byte-for-byte the same.
- All existing API endpoints and their response contracts: `/api/analyze`, `/api/analyze-image`, `/api/analyze-multimodal`, `/api/sensors`, `/api/devices`, `/api/history`, `/api/alerts`, `/api/feedback`, `/api/irrigation`, `/api/sync`, `/api/fields`, `/api/farmer-profile`, `/api/regional-context`, `/api/validation`, `/api/model-status`, `/api/model-capabilities`, `/api/model/prepare`, `/api/geocode/*`, `/api/images/{name}`.
- The SQLite schema. Existing tables and columns are untouched; existing databases keep working.
- Offline queue and duplicate-safe sync on `client_event_id`.
- EN / TE / HI support, the disease library content and the India map.
- The ESP32 hardware sketch, `scripts/download_model.py`, `prepare_ai_model.sh`, `run_backend.sh`, `pytest.ini`.
- The original interface, moved to `legacy/astranex_frontend.html` and still served at **`/legacy`**.
- `tests/test_engine.py` — all 7 tests still pass unmodified.

### Added
- **`backend/quantum/`** — the experimental hybrid layer: `feature_encoder.py`, `quantum_classifier.py`, `classical_baseline.py`, `dataset.py`, `benchmark.py`, `pipeline.py`, `api.py`.
- **Endpoints** `/api/quantum/status`, `/circuit`, `/features`, `/analyze`, `/analyze-result`, `/benchmark` (GET + POST), `/training`, `/runs`.
- **Endpoints** `/api/demo/fields`, `/api/demo/field/{code}`, `/api/analytics/summary`, `/api/insurer/evidence`.
- **`quantum_runs` table** plus `save_quantum_run()` and `list_quantum_runs()` in `db.py`. Model telemetry only; no additional farmer-identifying data.
- **A completely redesigned frontend** in `frontend/`: `index.html`, `assets/css/astranex.css` and six JavaScript modules (`data`, `i18n`, `api`, `viz`, `pages`, `app`), covering Home, Intelligence, Field scan, Quantum lab, Early warnings, Field network, Analytics, Disease library, Research and About, plus a ten-step Demo mode.
- **`frontend/sw.js`** service worker for offline shell caching, served from the root via a new `/sw.js` route. API responses are never cached.
- **`tests/test_quantum.py`** (22 tests) and **`tests/test_api.py`** (API contract, quantum endpoints, and a test asserting that a quantum failure leaves classical analysis working). `test_api.py` skips itself when FastAPI's test stack is absent.
- **Docs**: `README.md` rewritten, `SETUP.md`, `docs/ARCHITECTURE.md`, `docs/QUANTUM.md`, this changelog.
- Initial builds included a precomputed benchmark; the hardened build removes stale benchmark artifacts so the Quantum lab never displays old numbers as current Qiskit results.

### Changed
- `backend/main.py`: version `1.0.0` → `2.0.0`; `/` now serves the new interface; `/legacy` serves the original; `/static` mounts the new assets; `/api/health` additionally reports quantum state. The quantum router is imported inside `try/except` so the app starts even if that layer fails.
- `requirements.txt`: Qiskit added, marked optional.
- `.env.example`: `ASTRANEX_FORCE_FALLBACK_SIM` added.
- `START_HERE.md` and `VERSION.txt` updated for this build.

### Fixed
- `to_angles()` could round `1.0 × π` to `3.141593`, marginally above π. Angles are now clamped after rounding.

### Not implemented (explicitly)
No quantum-hardware execution, no multispectral or drone data processing, no field
validation, no deployment. See `docs/QUANTUM.md` §8.
