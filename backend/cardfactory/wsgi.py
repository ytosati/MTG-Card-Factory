"""WSGI entry point used by the server."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cardfactory.settings")

application = get_wsgi_application()
