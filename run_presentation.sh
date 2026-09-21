#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"
PY="$(command -v python3 || command -v python)"
# Presentation-safe mode: if Qiskit is not installed, the app still runs using
# the bundled simulator and labels that execution honestly in the UI/API.
# Offline demo: the vision model is not downloaded unless you opt in.
export ASTRANEX_FORCE_FALLBACK_SIM="${ASTRANEX_FORCE_FALLBACK_SIM:-0}"
export ASTRANEX_AUTO_DOWNLOAD_MODEL="${ASTRANEX_AUTO_DOWNLOAD_MODEL:-0}"
exec "$PY" -m uvicorn backend.main:app --host "${ASTRANEX_HOST:-127.0.0.1}" --port "${ASTRANEX_PORT:-8000}"
