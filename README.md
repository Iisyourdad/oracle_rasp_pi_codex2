# Oracle Recipe Pi

This repository now contains two deployable pieces of the recipe kiosk experience:

- **`oracle_site/`** – the full Django application that should be deployed to your Oracle "Always Free" instance.
- **`raspberry_pi/`** – a lightweight Wi-Fi configuration portal that runs locally on the Raspberry Pi when the device cannot reach the internet.

The Raspberry Pi should normally boot into kiosk mode and open the Oracle-hosted site. When the Pi is offline, it automatically starts the Wi-Fi portal locally so that you can connect it to a network.

## Oracle deployment (`oracle_site/`)

1. Install the dependencies (Python 3.10+, Django, Pillow, etc.). A virtual environment is recommended.
2. Collect the static files and apply database migrations as usual.
3. Use `./run_server.sh` for a quick development server or plug the project into your production stack (gunicorn/uvicorn + nginx).
4. Update `REMOTE_URL` in your Raspberry Pi configuration so the kiosk loads this deployment.

Important changes for the hosted site:

- The Wi-Fi setup views have been removed. The navigation bar now shows a **Refresh** button instead of the Wi-Fi link.
- The `/splash/check/` view always redirects to the index page, so the Oracle server never references the Pi-only Wi-Fi routes.

## Raspberry Pi deployment (`raspberry_pi/`)

The `raspberry_pi/` folder is a minimal Django project that only contains the Wi-Fi setup flow.

### First-time setup

```bash
cd raspberry_pi
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt  # or install Django manually
```

### Running manually

```bash
cd raspberry_pi
./start_wifi_portal.sh
```

### Using kiosk mode

`run_kiosk.sh` checks for internet access:

1. If it can reach `REMOTE_URL` (defaults to `https://your-oracle-domain.example.com`) the Pi launches Chromium directly to that site.
2. If not, it bootstraps the local Wi-Fi portal and launches Chromium pointing at `http://127.0.0.1:8000/`.

Environment variables you can override:

- `REMOTE_URL` – the Oracle-hosted site to open when online.
- `LOCAL_URL` – the address of the local Wi-Fi portal (defaults to `http://127.0.0.1:8000/`).
- `PYTHON_BIN` – which Python interpreter to use when starting the local Django server.

The Wi-Fi portal reuses the existing on-screen keyboard and `nmcli` integration so you can keep the same setup flow you already had on the Pi.
