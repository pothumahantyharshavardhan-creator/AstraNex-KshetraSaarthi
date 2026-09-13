# AstraNex KshetraSaarthi Backend v1.0

FastAPI backend for the AstraNex multimodal agriculture prototype.

## Endpoints
- `GET /api/health` — service/model readiness.
- `GET /api/model-status` — actual local vision status.
- `GET /api/model-capabilities` — exact PlantVillage crop coverage.
- `POST /api/analyze` — deterministic simulator/context analysis.
- `POST /api/analyze-multimodal` — authoritative image + sensor + weather analysis.
- `POST /api/analyze-image` — legacy image-only compatibility endpoint.
- `GET /api/history` — stored observations.
- `POST /api/sensors` — sensor ingestion and health assessment.
- `GET /api/sensors/latest` — recent sensor readings.
- `GET /api/alerts` — field alerts.
- `POST /api/feedback` — farmer feedback.
- `POST /api/irrigation` — simulation-only irrigation event.
- `POST /api/sync` — duplicate-safe offline observation sync.
- `GET /api/validation` — deterministic engineering validation cases.

## Architecture
Input validation → vision (when available) → sensor/context fusion → risk engine → confidence/uncertainty → recommendation → persistence.

The backend owns the final analysis result. The frontend renders it rather than maintaining a competing final-score formula.

## Vision model
The application defaults to context-only mode unless `ASTRANEX_MODEL_PATH` points to a compatible ONNX model. Automatic network model download is disabled by default for reliable offline demos. Use `POST /api/model/prepare` or `./prepare_ai_model.sh` when internet is available.

## Security
Uploads are MIME/size checked, stored with generated filenames and served only by basename. CORS is configurable with `ASTRANEX_CORS_ORIGINS`. Internal exceptions are not exposed through API responses.

## Connectivity
CORS permits localhost/127.0.0.1 development origins on arbitrary ports plus the `null` origin used by a direct `file://` preview. The frontend also prefers the current page origin when served by FastAPI.
