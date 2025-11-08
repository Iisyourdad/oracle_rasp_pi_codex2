"""WSGI config for the Raspberry Pi Wi-Fi portal."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pi_wifi_site.settings')

application = get_wsgi_application()
