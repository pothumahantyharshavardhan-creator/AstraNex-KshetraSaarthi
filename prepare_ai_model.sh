#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/download_model.py
echo 'AstraNex AI model prepared in backend/models.'
