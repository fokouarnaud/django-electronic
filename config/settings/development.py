"""Local development: DEBUG on, plain static files, django-tailwind + browser reload."""

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE, env

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# django-tailwind (standalone CLI, no Node) and live reload are dev-only tools.
INSTALLED_APPS = [*INSTALLED_APPS, "tailwind", "django_browser_reload"]
MIDDLEWARE = [*MIDDLEWARE, "django_browser_reload.middleware.BrowserReloadMiddleware"]

TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]

# Standard local static handling (runserver serves files straight from the apps).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
