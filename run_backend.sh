#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
PY="$(command -v python3 || command -v python)"
# Lazy-load the trained PlantVillage ONNX model only when a real image is analyzed.
# Override with ASTRANEX_AUTO_DOWNLOAD_MODEL=0 for strict offline operation.
export ASTRANEX_AUTO_DOWNLOAD_MODEL="${ASTRANEX_AUTO_DOWNLOAD_MODEL:-1}"
exec "$PY" -m uvicorn backend.main:app --host "${ASTRANEX_HOST:-127.0.0.1}" --port "${ASTRANEX_PORT:-8000}"
