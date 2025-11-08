#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN=${PYTHON_BIN:-python3}

cd "$PROJECT_DIR"
"$PYTHON_BIN" manage.py migrate --noinput
"$PYTHON_BIN" manage.py runserver 0.0.0.0:8000
