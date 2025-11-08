"""ASGI config for the Raspberry Pi Wi-Fi portal."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pi_wifi_site.settings')

application = get_asgi_application()
