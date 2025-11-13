"""Views for the Raspberry Pi Wi-Fi configuration portal."""
from __future__ import annotations

import json
import subprocess
import threading
import time

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt


PING_TARGET = "8.8.8.8"
RECIPE_PING_TARGET = "recipe.swestbrook.org"
RECIPE_APP_URL = "https://tyler-recipe-app-1-62732e39277f.herokuapp.com/"

_recipe_available = threading.Event()
_monitor_lock = threading.Lock()
_monitor_thread: threading.Thread | None = None


def _ping(host: str) -> bool:
    return (
        subprocess.run(
            ["ping", "-c", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def _has_internet() -> bool:
    """Return True when the device can reach the internet."""
    return _ping(PING_TARGET)


def _monitor_recipe_availability() -> None:
    """Continuously ping the recipe host until it becomes reachable."""
    while not _recipe_available.is_set():
        if _ping(RECIPE_PING_TARGET):
            _recipe_available.set()
            return
        time.sleep(5)


def _ensure_recipe_monitor() -> None:
    """Start the background monitor thread if it is not already running."""
    global _monitor_thread

    if _recipe_available.is_set():
        return

    with _monitor_lock:
        if _recipe_available.is_set():
            return
        if _monitor_thread and _monitor_thread.is_alive():
            return
        _monitor_thread = threading.Thread(
            target=_monitor_recipe_availability, name="recipe-monitor", daemon=True
        )
        _monitor_thread.start()


def wifi_setup(request):
    _ensure_recipe_monitor()
    if _recipe_available.is_set():
        return redirect(RECIPE_APP_URL)

    error = request.GET.get("error")
    return render(
        request,
        "wifi_portal/wifi_setup.html",
        {"error": error, "recipe_url": RECIPE_APP_URL},
    )


def wifi_connecting(request):
    if request.method == "POST":
        ssid = request.POST["ssid"]
        password = request.POST["password"]
        return render(
            request,
            "wifi_portal/connecting.html",
            {"ssid": ssid, "password": password},
        )
    return redirect("wifi_setup")


@csrf_exempt
def wifi_do_connect(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        ssid = data.get("ssid", "")
        password = data.get("password", "")
        subprocess.run(
            ["sudo", "nmcli", "dev", "wifi", "connect", ssid, "password", password],
            check=True,
        )
    except subprocess.CalledProcessError:
        return JsonResponse(
            {"status": "error", "error": "Wrong password, please try again"}, status=400
        )
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "error": "Invalid request"}, status=400)
    except Exception:
        return JsonResponse(
            {"status": "error", "error": "Unexpected error occurred"}, status=500
        )

    if _has_internet():
        return JsonResponse({"status": "ok"})
    return JsonResponse(
        {"status": "error", "error": "Failed to connect, please try again"}, status=400
    )


def configured(request):
    return render(request, "wifi_portal/configured.html")


def recipe_status(request):
    """Report whether the recipe site is reachable."""
    _ensure_recipe_monitor()
    return JsonResponse(
        {"reachable": _recipe_available.is_set(), "redirect_url": RECIPE_APP_URL}
    )
