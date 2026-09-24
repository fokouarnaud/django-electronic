"""Settings shared by every environment. See development.py / production.py."""

import os
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

# config/settings/base.py -> project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Load a local .env (git-ignored) if present. DJANGO_ENV_FILE lets tests and
# deployments point somewhere else. Real environment variables always win.
_env_file = Path(os.environ.get("DJANGO_ENV_FILE", BASE_DIR / ".env"))
if _env_file.is_file():
    environ.Env.read_env(_env_file)

# Only a placeholder for local work: production.py refuses to start with it.
INSECURE_DEV_SECRET_KEY = "django-insecure-dev-only-change-me-in-production"
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default=INSECURE_DEV_SECRET_KEY)

# Safe default; development.py switches it on, production.py forces it off.
DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    # Unfold must come before django.contrib.admin.
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "theme",
    "apps.curriculum",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise right after SecurityMiddleware: serves the collected static files.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite for dev and the first deploy. Only the ORM is used (no raw SQL) so the
# engine can be swapped for PostgreSQL later without code changes.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalisation -------------------------------------------------
USE_I18N = True
USE_TZ = True
TIME_ZONE = "Europe/Paris"

LANGUAGE_CODE = "fr"
LANGUAGES = [
    ("fr", _("French")),
    ("en", _("English")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "django_language"

# --- Static files ---------------------------------------------------------
# The compiled, minified Tailwind CSS (theme/static/css/dist/) is committed and
# served like any other static file: production never needs Node.js.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Unfold admin ---------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": _("Electronics Lab"),
    "SITE_HEADER": _("Electronics Lab"),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
