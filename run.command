#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ] || [ ! -f ".env" ]; then
  ./setup.sh
fi
./run.sh
