"""Views for the Raspberry Pi Wi-Fi configuration portal."""
from __future__ import annotations

import json
import subprocess

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt


PING_TARGET = "8.8.8.8"


def _has_internet() -> bool:
    """Return True when the device can reach the internet."""
    return (
        subprocess.run(
            ["ping", "-c", "1", PING_TARGET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def wifi_setup(request):
    error = request.GET.get("error")
    return render(request, "wifi_portal/wifi_setup.html", {"error": error})


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
