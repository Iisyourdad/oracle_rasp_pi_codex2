#!/bin/bash
# Oracle Recipe kiosk + Wi-Fi portal deployment script.
# Run this entire file on the Raspberry Pi as the tyler user (e.g. bash "How to set up raspberry pi").
# The script is idempotent where possible, but it assumes a clean Raspberry Pi OS installation.
set -euo pipefail

USER_NAME="tyler"
HOSTNAME_VALUE="recipe-oracle"
REMOTE_URL="https://tyler-recipe-app-1-62732e39277f.herokuapp.com/"
LOCAL_URL="http://127.0.0.1:8000/"
PROJECT_ROOT="/home/${USER_NAME}/raspberry_pi_recipe_oracle"
REPO_URL="https://github.com/Iisyourdad/oracle_rasp_pi_codex2.git"
REPO_DIR="${PROJECT_ROOT}/oracle_rasp_pi_codex2"
PI_DIR="${REPO_DIR}/raspberry_pi"
VENV_DIR="${PI_DIR}/venv"
BLACK_IMAGE="${REPO_DIR}/black.jpg"
LOG_DIR="/home/${USER_NAME}/logs"
USER_SYSTEMD_DIR="/home/${USER_NAME}/.config/systemd/user"
PING_TARGET="google.com"
PING_COUNT=3
PING_TIMEOUT=2
PING_INTERVAL=12

if [[ "$(whoami)" != "${USER_NAME}" ]]; then
  echo "Please run this script as ${USER_NAME}."
  exit 1
fi

export XDG_RUNTIME_DIR="/run/user/$(id -u "${USER_NAME}")"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
mkdir -p "${PROJECT_ROOT}" "${LOG_DIR}" "${USER_SYSTEMD_DIR}"
cd "/home/${USER_NAME}"

log() {
  printf "\n==== %s ====\n" "$1"
}

log "Configuring Raspberry Pi boot options"
sudo raspi-config nonint do_boot_behaviour B4      # Desktop auto-login
sudo raspi-config nonint do_hostname "${HOSTNAME_VALUE}"
sudo raspi-config nonint do_wifi_country US

log "Updating and installing base packages"
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y \
  git \
  python3-venv \
  python3-pip \
  python3-dev \
  unclutter \
  feh \
  curl \
  jq \
  xdotool \
  x11-xserver-utils \
  lightdm \
  pkg-config

log "Installing Chromium browser (with fallback)"
if ! sudo apt install -y chromium-browser; then
  log "chromium-browser package unavailable; installing chromium instead"
  sudo apt install -y chromium
fi

log "Installing optional math acceleration libraries"
if ! sudo apt install -y libatlas-base-dev; then
  log "libatlas-base-dev not available; continuing without it"
fi

log "Cloning or updating the project repository"
if [[ -d "${REPO_DIR}/.git" ]]; then
  cd "${REPO_DIR}"
  git pull --ff-only
else
  cd "${PROJECT_ROOT}"
  git clone "${REPO_URL}" oracle_rasp_pi_codex2
fi
cd "${REPO_DIR}"
git submodule update --init --recursive || true

log "Creating the Python virtual environment"
cd "${PI_DIR}"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "${REPO_DIR}/requirements.txt"
deactivate

log "Creating Django server launcher"
cat <<'EOF' > /home/tyler/django_server_run.sh
#!/bin/bash
set -euo pipefail

PROJECT_DIR="/home/tyler/raspberry_pi_recipe_oracle/oracle_rasp_pi_codex2/raspberry_pi"
VENV_DIR="${PROJECT_DIR}/venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
LOG_FILE="/home/tyler/logs/django_server.log"

mkdir -p "$(dirname "${LOG_FILE}")"
cd "${PROJECT_DIR}"

export DJANGO_SETTINGS_MODULE="pi_wifi_site.settings"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

"${PYTHON_BIN}" manage.py migrate --noinput
exec "${PYTHON_BIN}" manage.py runserver 0.0.0.0:8000 >> "${LOG_FILE}" 2>&1
EOF

log "Creating kiosk launcher that shows black splash, pings, and launches Chromium"
cat <<'EOF' > /home/tyler/run_kiosk.sh
#!/bin/bash
set -euo pipefail

USER_NAME="tyler"
REMOTE_URL="https://tyler-recipe-app-1-62732e39277f.herokuapp.com/"
LOCAL_URL="http://127.0.0.1:8000/"
BLACK_IMAGE="/home/tyler/raspberry_pi_recipe_oracle/oracle_rasp_pi_codex2/black.jpg"
PING_TARGET="google.com"
PING_COUNT=3
PING_TIMEOUT=2
CHECK_INTERVAL=12
DISPLAY_ID=":0"
FEH="/usr/bin/feh"
UNCLUTTER="/usr/bin/unclutter"
LOG_FILE="/home/tyler/logs/kiosk.log"

export DISPLAY="${DISPLAY_ID}"
export XDG_RUNTIME_DIR="/run/user/$(id -u "${USER_NAME}")"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"

mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"

if command -v chromium-browser >/dev/null 2>&1; then
  CHROMIUM_BIN="$(command -v chromium-browser)"
elif command -v chromium >/dev/null 2>&1; then
  CHROMIUM_BIN="$(command -v chromium)"
else
  echo "Chromium browser not found. Install chromium-browser or chromium." | tee -a "${LOG_FILE}"
  exit 1
fi

SPLASH_PID=""
CURRENT_MODE=""

cleanup() {
  if [[ -n "${SPLASH_PID}" ]] && kill -0 "${SPLASH_PID}" >/dev/null 2>&1; then
    kill "${SPLASH_PID}" >/dev/null 2>&1 || true
    wait "${SPLASH_PID}" >/dev/null 2>&1 || true
  fi
  pkill -f "${UNCLUTTER}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

launch_splash() {
  if [[ -x "${FEH}" && -f "${BLACK_IMAGE}" ]]; then
    "${FEH}" --fullscreen --hide-pointer --quiet "${BLACK_IMAGE}" &
    SPLASH_PID=$!
  fi
}

stop_splash() {
  if [[ -n "${SPLASH_PID}" ]]; then
    kill "${SPLASH_PID}" >/dev/null 2>&1 || true
    wait "${SPLASH_PID}" >/dev/null 2>&1 || true
    SPLASH_PID=""
  fi
}

launch_browser() {
  local url="$1"
  pkill -f "${CHROMIUM_BIN}" >/dev/null 2>&1 || true
  "${CHROMIUM_BIN}" \
    --kiosk \
    --start-fullscreen \
    --incognito \
    --no-first-run \
    --disable-translate \
    --disable-session-crashed-bubble \
    --enable-features=OverlayScrollbar \
    --simulate-touch-screen-with-mouse \
    --enable-touch-drag-drop \
    --overscroll-history-navigation=0 \
    "${url}" >> "${LOG_FILE}" 2>&1 &
}

ensure_unclutter() {
  if ! pgrep -x unclutter >/dev/null 2>&1; then
    "${UNCLUTTER}" -idle 0 -root &
  fi
}

has_internet() {
  ping -q -c "${PING_COUNT}" -W "${PING_TIMEOUT}" "${PING_TARGET}" >/dev/null 2>&1
}

launch_splash
ensure_unclutter

while true; do
  if has_internet; then
    if [[ "${CURRENT_MODE}" != "remote" ]]; then
      CURRENT_MODE="remote"
      stop_splash
      launch_browser "${REMOTE_URL}"
    fi
  else
    if [[ "${CURRENT_MODE}" != "local" ]]; then
      CURRENT_MODE="local"
      stop_splash
      launch_browser "${LOCAL_URL}"
    fi
  fi
  sleep "${CHECK_INTERVAL}"
done
EOF

chmod +x /home/tyler/django_server_run.sh /home/tyler/run_kiosk.sh

log "Building systemd service for Django server"
sudo tee /etc/systemd/system/django.service > /dev/null <<'EOF'
[Unit]
Description=Oracle Recipe Django Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=tyler
WorkingDirectory=/home/tyler/raspberry_pi_recipe_oracle/oracle_rasp_pi_codex2/raspberry_pi
ExecStart=/home/tyler/django_server_run.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

log "Building systemd user service for Chromium kiosk"
cat <<'EOF' > /home/tyler/.config/systemd/user/kiosk.service
[Unit]
Description=Chromium Kiosk Launcher
After=graphical-session.target network-online.target
Wants=graphical-session.target network-online.target

[Service]
Type=simple
ExecStart=/bin/bash /home/tyler/run_kiosk.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

log "Creating Wi-Fi helper script with passwordless sudo access"
sudo tee /usr/local/bin/update_wifi.sh > /dev/null <<'EOF'
#!/bin/bash
set -euo pipefail

if [[ -z "${1:-}" ]]; then
  echo "Usage: $0 \"network={...}\""
  exit 1
fi

CFG="/etc/wpa_supplicant/wpa_supplicant.conf"
printf "\n%s\n" "$1" >> "${CFG}"
chmod 600 "${CFG}"
/usr/sbin/wpa_cli -i wlan0 reconfigure
EOF
sudo chmod +x /usr/local/bin/update_wifi.sh
echo "tyler ALL=(root) NOPASSWD: /usr/local/bin/update_wifi.sh" | sudo tee /etc/sudoers.d/update_wifi > /dev/null
sudo chmod 440 /etc/sudoers.d/update_wifi

log "Disable splash screen and set framebuffer defaults"
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.$(date +%Y%m%d%H%M%S)
if ! grep -q "^disable_splash=1" /boot/firmware/config.txt; then
  echo "disable_splash=1" | sudo tee -a /boot/firmware/config.txt > /dev/null
fi

ROOT_PART=$(findmnt -n -o SOURCE /)
ROOT_PART=$(readlink -f "${ROOT_PART}")
PARTUUID=$(sudo blkid -s PARTUUID -o value "${ROOT_PART}")
sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.backup.$(date +%Y%m%d%H%M%S)
sudo tee /boot/firmware/cmdline.txt > /dev/null <<EOF
console=tty3 quiet loglevel=0 logo.nologo vt.global_cursor_default=0 root=PARTUUID=${PARTUUID} rootfstype=ext4 fsck.repair=yes rootwait plymouth.ignore-serial-consoles cfg80211.ieee80211_regdom=US
EOF

log "Disable virtual TTY login prompt to avoid flicker"
sudo systemctl disable --now getty@tty1.service || true

log "Apply LightDM display tweaks (no cursor, white background)"
sudo mkdir -p /etc/lightdm/lightdm.conf.d
sudo tee /etc/lightdm/lightdm.conf.d/99-kiosk.conf > /dev/null <<'EOF'
[Seat:*]
xserver-command=X -s 0 -dpms -nocursor -br -background white
EOF

log "Disable tap-to-click on the touchscreen"
sudo mkdir -p /usr/share/X11/xorg.conf.d
sudo tee /usr/share/X11/xorg.conf.d/40-libinput-touchscreen.conf > /dev/null <<'EOF'
Section "InputClass"
    Identifier "Disable tapping for touchscreen"
    MatchIsTouchscreen "on"
    Driver "libinput"
    Option "Tapping" "off"
EndSection
EOF

cat <<'EOF' > /home/tyler/disable_touch_tap.sh
#!/bin/bash
set -euo pipefail

export DISPLAY=":0"
export XAUTHORITY="/home/tyler/.Xauthority"
sleep 5
xinput set-button-map "xwayland-touch:14" 0 2 3
EOF
chmod +x /home/tyler/disable_touch_tap.sh

cat <<'EOF' > /home/tyler/.config/systemd/user/disable-touch.service
[Unit]
Description=Disable touchscreen tap-to-click
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/bin/bash /home/tyler/disable_touch_tap.sh

[Install]
WantedBy=graphical-session.target
EOF

log "Enable and start system services"
sudo systemctl daemon-reload
sudo systemctl enable django.service
sudo systemctl restart django.service

log "Enable and start user services"
systemctl --user daemon-reload
systemctl --user enable kiosk.service
systemctl --user enable disable-touch.service
systemctl --user restart kiosk.service || true
systemctl --user restart disable-touch.service || true

log "Allow user services to run without an interactive login"
sudo loginctl enable-linger "${USER_NAME}"

log "Update initramfs for splash/config changes"
sudo update-initramfs -u

log "Reminder: Install the ScrollAnywhere Chrome extension"
echo "Open Chromium once outside kiosk mode and install https://chromewebstore.google.com/detail/scrollanywhere/jehmdpemhgfgjblpkilmeoafmkhbckhi"

log "Setup complete. Reboot when ready to test the kiosk flow."
echo "Run: sudo reboot"
