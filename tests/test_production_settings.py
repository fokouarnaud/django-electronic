"""Split-settings, django-environ and production packaging tests (written first)."""

import importlib
import pathlib
import sys

import pytest
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command

PKG = "config.settings"
ROOT = pathlib.Path(__file__).resolve().parent.parent
GOOD_KEY = "s3cret-for-tests-" + "x" * 40
ENV_VARS = (
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_DEBUG",
    "DJANGO_SSL_REDIRECT",
    "DJANGO_HSTS_SECONDS",
    "DJANGO_ENV_FILE",
    "DATABASE_URL",
    "DJANGO_ADMIN_URL",
)


def load(monkeypatch, name, tmp_path=None, **env):
    """Import a fresh copy of config.settings.<name> under a controlled environment.

    DJANGO_ENV_FILE points at a non-existent file by default so a developer's real
    .env can never leak into the tests.
    """
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("DJANGO_ENV_FILE", str((tmp_path or ROOT) / "does-not-exist.env"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for module in [m for m in sys.modules if m in (f"{PKG}.base", f"{PKG}.{name}")]:
        sys.modules.pop(module)
    try:
        return importlib.import_module(f"{PKG}.{name}")
    finally:
        for module in (f"{PKG}.base", f"{PKG}.{name}"):
            sys.modules.pop(module, None)


@pytest.fixture
def base(monkeypatch, tmp_path):
    return load(monkeypatch, "base", tmp_path)


@pytest.fixture
def dev(monkeypatch, tmp_path):
    return load(monkeypatch, "development", tmp_path)


@pytest.fixture
def prod(monkeypatch, tmp_path):
    return load(monkeypatch, "production", tmp_path, DJANGO_SECRET_KEY=GOOD_KEY)


# --- Package layout ---------------------------------------------------------
def test_settings_are_a_package_with_three_modules():
    pkg = ROOT / "config" / "settings"
    for name in ("__init__.py", "base.py", "development.py", "production.py"):
        assert (pkg / name).is_file(), name
    assert not (ROOT / "config" / "settings.py").exists()


def test_entry_points_use_the_new_modules():
    assert "config.settings.development" in (ROOT / "manage.py").read_text(encoding="utf-8")
    assert "config.settings.production" in (ROOT / "config" / "wsgi.py").read_text(encoding="utf-8")


def test_env_file_is_gitignored_and_an_example_is_shipped():
    assert ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DJANGO_SECRET_KEY" in example


def test_requirements_list_environ_and_whitenoise():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "django-environ" in text and "whitenoise" in text
    # Production stays lean: dev tooling lives in requirements-dev.txt.
    assert "pytest" not in text and "django-tailwind" not in text and "polib" not in text
    dev_text = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "django-tailwind" in dev_text and "polib" in dev_text and "pytest" in dev_text


# --- base.py ----------------------------------------------------------------
def test_base_uses_django_environ(base):
    import environ

    assert isinstance(base.env, environ.Env)


def test_base_reads_secret_key_from_environment(monkeypatch, tmp_path):
    base = load(monkeypatch, "base", tmp_path, DJANGO_SECRET_KEY="from-the-environment")
    assert base.SECRET_KEY == "from-the-environment"


def test_base_reads_dotenv_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DJANGO_SECRET_KEY=from-dotenv-file\n", encoding="utf-8")
    base = load(monkeypatch, "base", tmp_path, DJANGO_ENV_FILE=str(env_file))
    assert base.SECRET_KEY == "from-dotenv-file"
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)  # read_env populated os.environ


def test_base_common_configuration(base):
    assert base.INSTALLED_APPS[0] == "unfold"
    assert "apps.curriculum" in base.INSTALLED_APPS and "theme" in base.INSTALLED_APPS
    assert base.USE_I18N is True and base.LANGUAGE_CODE == "fr"
    assert [c for c, _ in base.LANGUAGES] == ["fr", "en"]
    assert base.TIME_ZONE == "Europe/Paris"
    assert base.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert base.BASE_DIR == ROOT
    assert base.LOCALE_PATHS == [ROOT / "locale"]
    assert base.DEBUG is False  # safe default; development turns it on


def test_base_middleware_order(base):
    mw = base.MIDDLEWARE
    assert mw[0] == "django.middleware.security.SecurityMiddleware"
    assert mw[1] == "whitenoise.middleware.WhiteNoiseMiddleware"
    assert (
        mw.index("django.contrib.sessions.middleware.SessionMiddleware")
        < mw.index("django.middleware.locale.LocaleMiddleware")
        < mw.index("django.middleware.common.CommonMiddleware")
    )


def test_base_has_no_dev_only_apps(base):
    assert "django_browser_reload" not in base.INSTALLED_APPS
    assert "tailwind" not in base.INSTALLED_APPS


# --- development.py ---------------------------------------------------------
def test_development_turns_debug_on_and_adds_tooling(dev):
    assert dev.DEBUG is True
    assert "django_browser_reload" in dev.INSTALLED_APPS
    assert "tailwind" in dev.INSTALLED_APPS
    assert "django_browser_reload.middleware.BrowserReloadMiddleware" in dev.MIDDLEWARE
    assert dev.TAILWIND_APP_NAME == "theme"


def test_development_uses_plain_static_storage(dev):
    assert dev.STORAGES["staticfiles"]["BACKEND"] == "django.contrib.staticfiles.storage.StaticFilesStorage"


def test_development_has_a_working_default_secret_key(dev):
    assert dev.SECRET_KEY and dev.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]


# --- production.py ----------------------------------------------------------
def test_production_secret_key_comes_from_environment(prod):
    assert prod.SECRET_KEY == GOOD_KEY


def test_production_without_secret_key_is_a_hard_error(monkeypatch, tmp_path):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load(monkeypatch, "production", tmp_path)


def test_production_rejects_the_insecure_development_key(monkeypatch, tmp_path):
    with pytest.raises(ImproperlyConfigured):
        load(monkeypatch, "production", tmp_path, DJANGO_SECRET_KEY="django-insecure-anything")


def test_production_forces_debug_off(monkeypatch, tmp_path):
    prod = load(monkeypatch, "production", tmp_path, DJANGO_SECRET_KEY=GOOD_KEY, DJANGO_DEBUG="1")
    assert prod.DEBUG is False


def test_production_allowed_hosts(prod):
    assert prod.ALLOWED_HOSTS == ["localhost", "127.0.0.1", ".pythonanywhere.com"]


def test_production_extra_hosts_from_environment(monkeypatch, tmp_path):
    prod = load(
        monkeypatch,
        "production",
        tmp_path,
        DJANGO_SECRET_KEY=GOOD_KEY,
        DJANGO_ALLOWED_HOSTS="labo.example.org, other.test",
    )
    assert prod.ALLOWED_HOSTS == [
        "localhost",
        "127.0.0.1",
        ".pythonanywhere.com",
        "labo.example.org",
        "other.test",
    ]


def test_production_static_storage_is_compressed_manifest(prod):
    backend = prod.STORAGES["staticfiles"]["BACKEND"]
    assert backend == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    assert prod.STATIC_ROOT == ROOT / "staticfiles"


def test_production_hardening(prod):
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SESSION_COOKIE_HTTPONLY is True
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert prod.X_FRAME_OPTIONS == "DENY"
    assert prod.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"


def test_production_https_redirect_and_hsts_are_opt_in(prod, monkeypatch, tmp_path):
    assert prod.SECURE_SSL_REDIRECT is False and prod.SECURE_HSTS_SECONDS == 0
    strict = load(
        monkeypatch,
        "production",
        tmp_path,
        DJANGO_SECRET_KEY=GOOD_KEY,
        DJANGO_SSL_REDIRECT="1",
        DJANGO_HSTS_SECONDS="3600",
    )
    assert strict.SECURE_SSL_REDIRECT is True and strict.SECURE_HSTS_SECONDS == 3600


def test_production_has_no_dev_only_apps(prod):
    assert "django_browser_reload" not in prod.INSTALLED_APPS
    assert "tailwind" not in prod.INSTALLED_APPS
    assert prod.INSTALLED_APPS[0] == "unfold"


# --- Portability ------------------------------------------------------------
def test_no_raw_sql_in_application_code():
    offenders = []
    for path in (ROOT / "apps").rglob("*.py"):
        if "migrations" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in (".raw(", "cursor()", ".extra(", "RawSQL")):
            offenders.append(str(path))
    assert offenders == []


# --- Static assets ----------------------------------------------------------
@pytest.mark.parametrize("asset", ["css/dist/styles.css", "curriculum/quiz.js", "curriculum/magnetic.js"])
def test_project_assets_are_discoverable(asset):
    assert finders.find(asset), f"{asset} not found by the staticfiles finders"


def test_base_template_links_compiled_css_directly(client, db):
    body = client.get("/fr/").content.decode()
    assert 'rel="stylesheet"' in body and "css/dist/styles" in body


def test_collectstatic_packages_hashed_and_compressed_assets(tmp_path, settings, capsys):
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    call_command("collectstatic", interactive=False, verbosity=1)
    captured = capsys.readouterr()
    assert "No directory at" not in captured.out + captured.err

    root = tmp_path / "staticfiles"
    assert (root / "staticfiles.json").is_file()
    css = list((root / "css" / "dist").glob("styles.*.css"))
    assert css, "hashed compiled CSS missing"
    assert css[0].with_name(css[0].name + ".gz").is_file(), "gzip variant missing"
    assert list((root / "curriculum").glob("quiz.*.js"))
    assert list((root / "curriculum").glob("magnetic.*.js"))
    assert not list(root.rglob("node_modules")), "node_modules must never be shipped"
    assert not (root / "static_src").exists(), "Tailwind sources must not be shipped"
    shipped_css = [p for p in root.rglob("*.css") if not p.name.endswith(".gz")]
    assert not [p for p in shipped_css if '@import "tailwindcss"' in p.read_text(encoding="utf-8")], (
        "uncompiled Tailwind source was collected"
    )


# --- Critique pass: database URL, logging, admin URL, pinning, CI ------------
def test_database_defaults_to_sqlite_and_accepts_database_url(monkeypatch, tmp_path):
    base = load(monkeypatch, "base", tmp_path)
    assert base.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
    assert pathlib.Path(base.DATABASES["default"]["NAME"]) == ROOT / "db.sqlite3"
    pg = load(monkeypatch, "base", tmp_path, DATABASE_URL="postgres://u:p@db.example:5432/lab")
    assert pg.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert pg.DATABASES["default"]["NAME"] == "lab"


def test_production_logs_errors_to_the_console(prod):
    assert prod.LOGGING["handlers"]["console"]["class"] == "logging.StreamHandler"
    assert prod.LOGGING["root"]["handlers"] == ["console"]
    assert prod.LOGGING["loggers"]["django.request"]["level"] == "ERROR"


def test_admin_url_is_configurable(monkeypatch, tmp_path):
    assert load(monkeypatch, "base", tmp_path).ADMIN_URL == "admin/"
    custom = load(monkeypatch, "base", tmp_path, DJANGO_ADMIN_URL="gestion-7f3a/")
    assert custom.ADMIN_URL == "gestion-7f3a/"


def test_admin_is_mounted_on_admin_url():
    from django.urls import reverse

    assert reverse("admin:index") == "/admin/"


@pytest.mark.parametrize("name", ["requirements.txt", "requirements-dev.txt"])
def test_requirements_are_pinned(name):
    for raw in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if line and not line.startswith("-r"):
            assert "==" in line, f"unpinned dependency in {name}: {line}"


def test_ci_runs_lint_tests_and_migration_check():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for step in ("ruff check", "ruff format --check", "pytest", "makemigrations --check"):
        assert step in workflow


@pytest.mark.parametrize(
    "weak_key",
    [
        "change-me",  # the .env.example placeholder: public on GitHub
        "short-but-random-3f9a",  # < 50 characters (Django's W009 threshold)
        "a" * 60,  # < 5 distinct characters
    ],
)
def test_production_rejects_placeholder_and_weak_keys(monkeypatch, tmp_path, weak_key):
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load(monkeypatch, "production", tmp_path, DJANGO_SECRET_KEY=weak_key)


def test_env_example_placeholder_is_rejected_in_production(monkeypatch, tmp_path):
    """Forgetting to edit the copied .env must stop the site, not run it with a public key."""
    env_file = tmp_path / ".env"
    env_file.write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ImproperlyConfigured):
        load(monkeypatch, "production", tmp_path, DJANGO_ENV_FILE=str(env_file))
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)  # read_env populated os.environ
