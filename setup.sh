#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  python - <<'PYSECRET'
from pathlib import Path
import secrets
p = Path(".env")
s = p.read_text()
s = s.replace("SQ_SECRET_KEY=replace-with-a-long-random-secret", f"SQ_SECRET_KEY={secrets.token_urlsafe(48)}")
p.write_text(s)
PYSECRET
  echo "Created .env with a fresh local secret. Configure SMTP before enabling real email delivery."
fi
printf '\nSetup complete. Start the app with ./run.sh (or double-click run.command on macOS).\n'
