#!/bin/bash

# Always load splash page on startup
echo "Starting Raspberry Pi Recipe App in kiosk mode..."
/usr/bin/chromium \
  --kiosk \
  --start-fullscreen \
  --no-first-run \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --disable-infobars \
  --disable-restore-session-state \
  http://0.0.0.0:8000/