#!/bin/bash

# Always load splash page on startup
echo "Starting Raspberry Pi Recipe App in kiosk mode..."
/bin/chromium-browser \
  --touch-events=enabled \
  --enable-pinch \
  --enable-touch-drag-drop \
  --kiosk \
  --start-maximized \
  http://0.0.0.0:8000
