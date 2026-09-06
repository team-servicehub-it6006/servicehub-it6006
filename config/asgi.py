"""ASGI entry point. Not used at the moment; kept so the project is deployable either way."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
