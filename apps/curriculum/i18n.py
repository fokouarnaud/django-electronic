"""Lightweight model translation: explicit ``<name>_<lang>`` columns + a descriptor."""

from django.conf import settings
from django.utils.translation import get_language


class TranslatedField:
    """Read-only attribute returning ``<name>_<active lang>`` with fallback.

    Falls back to the other configured languages (in ``settings.LANGUAGES``
    order) when the active language's value is empty.
    """

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        active = (get_language() or settings.LANGUAGE_CODE).split("-")[0]
        codes = [code for code, _label in settings.LANGUAGES]
        ordered = [active] + [c for c in codes if c != active]
        for code in ordered:
            value = getattr(instance, f"{self.name}_{code}", "")
            if value:
                return value
        return ""
