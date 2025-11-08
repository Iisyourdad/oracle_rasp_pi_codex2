#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

PYTHON_BIN=${PYTHON_BIN:-python3}

"$PYTHON_BIN" manage.py migrate --noinput
"$PYTHON_BIN" manage.py runserver 0.0.0.0:8000
