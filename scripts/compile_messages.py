"""Compile locale/**/django.po into .mo with polib (no GNU gettext needed).

Usage: python scripts/compile_messages.py
Use this on machines without `msgfmt` (e.g. Windows); `manage.py compilemessages`
is equivalent where gettext is installed. Commit the resulting .mo files so
PythonAnywhere only needs `git pull`.
"""

from pathlib import Path

import polib

LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"


def main():
    for po_path in sorted(LOCALE_DIR.glob("*/LC_MESSAGES/django.po")):
        po = polib.pofile(str(po_path))
        mo_path = po_path.with_suffix(".mo")
        po.save_as_mofile(str(mo_path))
        translated = len(po.translated_entries())
        print(f"{po_path.relative_to(LOCALE_DIR.parent)} -> {mo_path.name} ({translated} translated)")


if __name__ == "__main__":
    main()
