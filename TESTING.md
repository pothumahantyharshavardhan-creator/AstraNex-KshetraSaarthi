# TESTING.md

## How testing worked in the v3.3 session (read this first)

The sandbox this v3.3 work was done in has **no network access**, and did
not have `pytest`, `fastapi`, `httpx`, `qiskit`, or `qiskit-machine-learning`
pre-installed. That means:

- Every new **pure-Python** module (`data_quality.py`, `sensor_health.py`,
  `alert_engine.py`, `crop_profiles.py`, `timeline.py`, `weather.py`,
  `demo.py`, `feature_sensitivity.py`) and its logic was verified by
  **actually importing and exercising it** with a small manual test runner
  (no pytest needed — these modules only use the standard library) and by
  hand-running every pre-existing and new `test_*.py` function that doesn't
  require `fastapi`/`qiskit`.
- Every new **FastAPI endpoint** was written, wired into `main.py`, and
  checked with `python3 -m py_compile` (catches syntax errors only) — it was
  **never actually served or hit with a real HTTP request**, because
  `fastapi`/`httpx` are not installed here.
- The **quantum layer** (`backend/quantum/*`) was read and reasoned about,
  and `feature_sensitivity.py` was written to sit on top of the existing
  `pipeline.simulate()` function, but it was **never executed**, because
  `qiskit`/`qiskit-machine-learning` are not installed here.

**Before you trust this build, run the real suite in an environment with
dependencies installed:**

```bash
cd AstraNex_KshetraSaarthi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest httpx
pytest -q
```

## What was actually run and passed, in this session

A manual runner (no pytest) executed these test modules directly:

| File | Functions | Result |
|---|---|---|
| `tests/test_engine.py` (pre-existing) | 8 | **0 failures** (regression check against all v3.3 engine changes) |
| `tests/test_data_quality.py` (new) | 6 | **0 failures** |
| `tests/test_sensor_anomaly.py` (new) | 8 | **0 failures** |
| `tests/test_alert_engine.py` (new) | 5 | **0 failures** |
| `tests/test_crop_profiles.py` (new) | 4 | **0 failures** |
| `tests/test_timeline.py` (new) | 6 | **0 failures** |

That's 37 test functions actually executed and passing. (The nine functions
appended to `tests/test_api.py` bring the *written* new-test count to 44 —
see below for why those specific nine are unverified.)

## What was written but NOT executed (run these yourself first)

- `tests/test_api.py`, all functions, including the 9 appended under the
  `# ---------------- v3.3 additions ----------------` header. This file
  `pytest.importorskip("fastapi")`s itself, so it will silently skip rather
  than fail in an environment without `fastapi`+`httpx` — don't mistake a
  skip for a pass.
- `tests/test_quantum.py` and `tests/test_quantum_state.py` (pre-existing,
  untouched this session) — need `qiskit`.
- Anything about the actual HTTP behaviour of `/api/crops`,
  `/api/field-history`, `/api/timeline`, `/api/weather`, `/api/demo/*`, and
  `/api/quantum/feature-sensitivity` — reasoned through against FastAPI's
  documented behaviour, not observed.
- A clean-install-from-scratch run (spec §51) was not performed.
- Frontend tests: there were none before this session and none were added.

## Coverage against the spec's edge-case list (§42)

Explicitly covered by the new tests:

- soil moisture / temperature / humidity out of physical range → `invalid`
  (`test_sensor_anomaly.py`)
- missing sensor value → `disconnected` (`test_sensor_anomaly.py`)
- non-numeric sensor value → `invalid` (`test_sensor_anomaly.py`)
- sudden jump between readings → `noisy` (`test_sensor_anomaly.py`,
  matches the pre-existing v3.2 API-level test)
- repeated/identical readings → `stuck` (`test_sensor_anomaly.py`, new in
  v3.3)
- out-of-order timestamp → reduced overall score (`test_sensor_anomaly.py`)
- missing/incomplete agricultural context → reduced Data Quality Score,
  named in `notes` (`test_data_quality.py`)
- stale sensor reading → flagged (`test_data_quality.py`)
- physically-implausible but individually-valid combinations (e.g. very
  high moisture during a configured drought) → flagged
  (`test_data_quality.py`)
- unconfigured crop / unsupported growth stage → explicit fallback, no
  fabricated threshold (`test_crop_profiles.py`)
- insufficient historical data for a requested window → explicit message,
  not interpolation (`test_timeline.py`)
- invalid demo scenario id → handled without a 500
  (`test_api.py`, unverified — see above)

Not newly covered (pre-existing v3.2 tests already covered some of this,
per `tests/test_engine.py` and `tests/test_api.py`'s existing suites, which
were read but not extended for): empty/corrupt/oversized image upload,
offline sync interruption/duplication, quantum circuit failure paths.

## Honest bottom line

This session's testing gives you good confidence in the new **pure-logic**
modules (they were actually run). It gives you **no direct evidence** about
the new HTTP endpoints or anything quantum-related beyond static reasoning
and syntax checking. Treat those as "should work, not yet proven" until you
run `pytest` yourself.
