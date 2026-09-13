# AstraNex — KshetraSaarthi v10

A farmer-first, multimodal smart-agriculture decision-support prototype for SIH demonstrations.

## What is implemented
- Unified backend analysis for simulator and real-image workflows.
- Image + soil moisture + temperature + humidity + weather + crop-stage context.
- Explainable risk bands and a single authoritative field-health score.
- Real ONNX vision support when a compatible local model is configured.
- Safe context-only fallback when the vision model is unavailable or the crop is outside PlantVillage coverage.
- Image quality and non-plant upload guardrails.
- Offline local queue and duplicate-safe observation synchronization.
- SQLite observation, sensor, alert, feedback and irrigation records.
- Interactive disease library, scenarios and future-expansion sections.
- Telugu / Hindi / English farmer-facing UI.
- Hardware proof-of-concept ESP32 example.

## Run
```bash
cd astranex_mobile_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/`. The backend serves the frontend and the bundled offline India map from the same origin. Same-origin mode avoids browser CORS problems; localhost/127.0.0.1 development ports are also supported.

## Optional local vision model
Set `ASTRANEX_MODEL_PATH` to a compatible ONNX model for fully local inference. The default model repository is `AbhiCommits/cropguard-models`, which publishes the CropGuard PlantVillage 38-class ONNX model. By default, model download is **off** so a first image scan never hangs waiting for a large download. The UI has **Prepare AI model**, or run `./prepare_ai_model.sh` when internet is available. If the model is not prepared, AstraNex immediately falls back to clearly labelled visual screening + sensor/context analysis.

## Model scope
The default PlantVillage class map covers 14 crop groups, including tomato and corn/maize. Paddy, cotton, chilli, groundnut and turmeric are not claimed as PlantVillage-vision-supported by the default model. For unsupported crops, AstraNex continues contextual sensor/risk monitoring and clearly labels the limitation.

## Safety
AstraNex provides preliminary screening and decision support, not a confirmed diagnosis. Recommendations require field verification and local agricultural guidance. Chemical products and irrigation are never autonomously prescribed or actuated.

## SIH demo flow
1. Select farmer and field.
2. Show live/simulated sensor values.
3. Run a field check.
4. Capture a leaf image.
5. Show the Observe → Validate → AI → Fuse → Verify → Guide pipeline.
6. Open the explainable result.
7. Demonstrate analytics/history.
8. Demonstrate offline fallback and sync.
9. Open disease library and supported scenarios.
10. Finish with the hardware/edge-AI architecture and validation lab.

## Validation
```bash
PYTHONPATH=. pytest -q
```
The included engineering suite must pass before a demo build is used. These tests are not field-accuracy validation.

### v11.1 bug-fix notes
- Fixed browser CORS preflight (`OPTIONS`) failures for localhost/127.0.0.1 development ports and direct `file://` previews.
- A failed API request no longer falsely changes the global backend status to offline; the UI re-checks `/api/health`.
- Field scan remains on the current screen and the backend result is authoritative when available.
- Added explicit AI model preparation so first image analysis does not block on a model download.
- Bundled India map is the default map; third-party map tiles are not required.
- Location lookup never invents a state-centre coordinate when exact geocoding fails.
- Multimodal image observations now carry a client event ID for duplicate-safe persistence.

### v11.2 polish/audit notes
- Fixed a vision-inference edge case (`backend/services/inference.py`) where a crop-mismatch result with an exact `0.0` confidence score could silently fall through and be treated as a match instead of returning the mismatch/verification response.
- Replaced the deprecated `@app.on_event('startup')` hook with FastAPI's `lifespan` context manager in `backend/main.py`, and removed an unused import.
- Fixed a copy/paste error message in the frontend's sensor-reading upload path that incorrectly referenced "image" instead of "sensor reading".
- Moved `API_BASE` and related shared frontend constants to the top of the script so they no longer depend on execution order to be defined before first use.
- Removed a duplicate copy of `backend/scripts/` (identical to the top-level `scripts/`, which is what `prepare_ai_model.sh` actually calls).
- Removed committed runtime artifacts (`backend/astranex.db`, `__pycache__/`, `.pytest_cache/`) from the distributed archive; these regenerate automatically on first run. Added a `.gitignore` covering Python caches, virtual environments and runtime data.
- Verified: all 7 `tests/test_engine.py` cases pass, every backend module compiles cleanly, the frontend `<script>` block is syntax-valid, and every `getElementById` reference in the frontend resolves to a real element ID.

