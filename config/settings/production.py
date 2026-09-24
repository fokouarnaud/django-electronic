"""Production (PythonAnywhere): DEBUG off, WhiteNoise compressed manifest, hardening.

Required environment (WSGI file or .env): DJANGO_SECRET_KEY.
Optional: DJANGO_ALLOWED_HOSTS (comma separated extra hosts), DJANGO_SSL_REDIRECT,
DJANGO_HSTS_SECONDS.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, INSECURE_DEV_SECRET_KEY, SECRET_KEY, env

if not SECRET_KEY or SECRET_KEY == INSECURE_DEV_SECRET_KEY or SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("Set a real DJANGO_SECRET_KEY in the environment (or .env) for production.")

DEBUG = False  # never driven by the environment

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".pythonanywhere.com",
    *(host.strip() for host in env.list("DJANGO_ALLOWED_HOSTS", default=[]) if host.strip()),
]

# --- Static files: WhiteNoise, hashed + gzip/brotli-compressed --------------
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Security hardening -----------------------------------------------------
# PythonAnywhere terminates TLS at its proxy and forwards the scheme in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Opt-in: enable once HTTPS works for your domain (or use PythonAnywhere's
# "Force HTTPS" switch on the Web tab). HSTS is sticky, so it defaults to off.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=0)
