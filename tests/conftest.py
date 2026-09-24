import pytest
from django.conf import settings
from django.utils import translation


@pytest.fixture(autouse=True)
def reset_active_language():
    """Requests activate a language on the thread and never deactivate it;
    reset so reverse()/gettext in one test can't depend on a previous test."""
    translation.activate(settings.LANGUAGE_CODE)
    yield
    translation.deactivate_all()
