#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="python3"
if [ -x "$ROOT/.venv/bin/python" ]; then PYTHON="$ROOT/.venv/bin/python"; fi
if [ ! -f "$ROOT/.env" ]; then echo "Missing .env. Run ./setup.sh first."; exit 1; fi
cd "$ROOT/backend"
exec "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
