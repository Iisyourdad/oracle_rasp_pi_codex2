#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_URL=${REMOTE_URL:-"https://tyler-recipe-app-1-62732e39277f.herokuapp.com/"}
LOCAL_URL=${LOCAL_URL:-"http://127.0.0.1:8000/"}
PYTHON_BIN=${PYTHON_BIN:-python3}

launch_browser() {
  local url="$1"
  echo "Launching Chromium in kiosk mode for ${url}"
  /bin/chromium-browser \
    --touch-events=enabled \
    --enable-pinch \
    --enable-touch-drag-drop \
    --kiosk \
    --start-maximized \
    "$url"
}

start_local_portal() {
  echo "No internet connection detected. Starting local Wi-Fi portal..."
  cd "$PROJECT_DIR"

  if ! pgrep -f "manage.py runserver 0.0.0.0:8000" >/dev/null; then
    "$PYTHON_BIN" manage.py migrate --noinput
    "$PYTHON_BIN" manage.py runserver 0.0.0.0:8000 >/tmp/pi_wifi_portal.log 2>&1 &
    sleep 3
  fi

  launch_browser "$LOCAL_URL"
}

echo "Checking connectivity to ${REMOTE_URL}..."
if curl --silent --head --max-time 5 "$REMOTE_URL" >/dev/null; then
  echo "Connection successful. Using remote Oracle site."
  launch_browser "$REMOTE_URL"
else
  start_local_portal
fi
