# ARCHITECTURE — v3.3

This document describes what v3.3 actually is, on top of the existing
`docs/ARCHITECTURE.md` (v3.2) and `docs/QUANTUM.md`, which still apply
unchanged to the quantum layer's core design.

## Data flow (unchanged shape, new layers inserted)

```
Frontend
  |
  v
API (backend/main.py, backend/quantum/api.py)
  |
  v
Agricultural engine (backend/engine.py)
  |-- services/fusion.py          (confidence fusion — v3.2, unchanged)
  |-- services/irrigation.py      (v3.3: crop-profile-aware thresholds)
  |-- services/crop_profiles.py   (v3.3: NEW — config/crops/*.json loader)
  |-- services/data_quality.py    (v3.3: NEW — unified Data Quality Score)
  |-- services/alert_engine.py    (v3.3: NEW — structured INFO..CRITICAL alerts)
  |-- services/sensor_health.py   (v3.3: enhanced — stuck/repeat detection)
  |-- services/timeline.py        (v3.3: NEW — history windows + events)
  |-- services/weather.py         (v3.3: NEW — graceful-degradation provider)
  |-- services/demo.py            (v3.3: NEW — in-memory demo scenarios)
  v
Database (backend/db.py — SQLite, additive migrations only)
  v
Quantum/QML layer (backend/quantum/* — v3.2 core unchanged)
  |-- feature_sensitivity.py (v3.3: NEW — experimental sensitivity sweep)
```

## What each v3.3 layer is responsible for, and its honesty boundary

| Layer | Responsibility | Explicitly NOT claimed |
|---|---|---|
| `data_quality.py` | How trustworthy the *inputs* were | Agricultural accuracy |
| `sensor_health.py` | Is this specific reading physically plausible / consistent with recent history | Whether the crop is healthy |
| `alert_engine.py` | Did a configured trigger fire, and what to check | Certainty ("your crop has X") |
| `crop_profiles.py` | Externalised, editable thresholds | Scientifically validated agronomy — every profile file carries `"validation_status": "NOT_FIELD_VALIDATED"` |
| `timeline.py` | What the system actually recorded, when | Interpolated/estimated historical values |
| `weather.py` | Best available reading right now | A live forecast when none is configured or reachable |
| `demo.py` | A judge-facing walkthrough | Real farmer data — every result is tagged `demo: true` |
| `feature_sensitivity.py` | How much a simulated circuit's output moved under perturbation | Statistically validated feature importance |

## Implemented in v3.3 (this release)

Sections of the original spec implemented and manually verified this session
(pure-Python logic; see CHANGELOG_v3.3.md and TESTING.md for exactly what
"verified" means here):

- §5/7/8 Agricultural context + explainable recommendations + confidence —
  already present in v3.2's `engine.py`; extended with `data_quality`.
- §9 Sensor anomaly detection — extended (stuck/repeat, non-numeric,
  out-of-order timestamps).
- §11 Time-series field history (24h/7d/30d, honest insufficient-data state).
- §12 Farm events timeline.
- §13 Structured alert engine (INFO/WATCH/WARNING/CRITICAL,
  what/why/check/action).
- §14 Weather provider abstraction with graceful degradation.
- §17/18 Crop profiles + growth-stage awareness with explicit
  "unavailable" fallback.
- §22 Experimental quantum feature-sensitivity sweep (clearly disclaimed).
- §29–31 Demo Mode with 6 scenarios + honest reset.
- §3/4 Version bump to 3.3.0; dependency versions were reviewed but **not**
  changed (no network access in this session to test a re-pin — see below).

## NOT done in this release (honest gap list)

These spec sections were **not implemented** this session. Listed instead of
silently skipped, per the spec's own §54 rule ("do not say everything works
unless tested"):

- §4 Dependency pinning to exact `qiskit==2.5.2` / `qiskit-machine-learning==0.9.1`
  — not attempted; this sandbox has no network access to install/test a
  re-pinned environment, and changing pins without testing them would be
  irresponsible. `requirements.txt` is unchanged.
- §10 Formal sensor-fusion "Unified Field State" card — the underlying data
  now exists (`data_quality`, `alerts`, `timeline`) but no single endpoint
  assembles them into the exact `FIELD STATE` shape described.
- §15/16/32/33/34 Farmer dashboard reprioritisation, Field Health Index
  display, mobile breakpoint pass, accessibility audit, design-token system
  — frontend was **not modified** beyond the service-worker cache-name bump.
  `frontend/index.html`, `assets/js/*.js` and `assets/css/astranex.css` are
  unchanged.
- §19/20 Image pipeline 2.0 quality indicators (brightness/blur/resolution)
  and disease-result explanation screen — the engine already reports
  `vision_confidence` and guardrails (v3.2); the specific quality-indicator
  breakdown was not added.
- §23 Dedicated classical-vs-quantum comparison screen — `backend/quantum/benchmark.py`
  already trains and compares both models (v3.2); no new comparison
  endpoint/UI was added this session.
- §25 Quantum experiment replay (diff old vs current config) — not built;
  `backend/quantum/api.py`'s existing `/runs` and `/provenance` endpoints
  (v3.2) already store what a replay feature would need.
- §26/27 Noise-visualisation improvements and a "How QML Works" education
  mode — not built.
- §28 Explicit Farmer Mode / Research Mode UI split — not built (frontend
  unchanged).
- §35 Performance measurement — not instrumented.
- §36–38 Security/API/database hardening pass — **reviewed, not modified**.
  CORS, upload MIME/size limits, parameterised SQL, and error responses that
  return only `type(exc).__name__` (never a raw message or traceback) were
  already in place from v3.2 and look sound; see SECURITY.md for the review
  notes. No new hardening code was written because nothing unsound was found
  to fix, and speculative "hardening" without a concrete issue risks breaking
  working behaviour untested.
- §39 Offline-sync conflict resolution improvements — not built.
- §40 Structured logging — not built.
- §41–42 The "100+ meaningful tests" / property-edge-testing target — this
  session added 35 new test functions across 5 new files plus 9 appended to
  `test_api.py` (44 new, all logic-level or reasoned-through; the `test_api.py`
  additions have not actually been executed — see TESTING.md). This does not
  reach the spec's 100+ target on its own; combined with the existing v3.2
  suite the repository likely exceeds 100 total, but that combined count was
  not verified because the full suite cannot run in this sandbox.
- §43/44 Frontend error states and backend graceful-degradation review across
  every page — only the weather provider was built with explicit
  graceful-degradation this session; a full audit of every frontend
  loading/empty/error state was not performed.
- §45 SECURITY.md, TESTING.md, DEMO_GUIDE.md added this session (see below);
  QML_V3.3.md was not written as a separate file — the quantum-layer changes
  are documented inline above and in `docs/QUANTUM.md` (unchanged).
- §47/48 Dedicated judge-facing research dashboard / farmer dashboard UI
  pages — not built (frontend unchanged).
- §49 AI Farm Assistant — not built.
- §51/52 Full quality gate (clean install from scratch, mobile tests,
  dependency checks) — not run; this sandbox lacks `pytest`, `fastapi`,
  `qiskit` and network access to install them.

If you want the next session to pick this up, the gap list above is written
so each bullet is independently actionable.
