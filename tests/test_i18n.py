"""i18n tests: written first (TDD). They drive settings, models, views and the switcher."""

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import translation

from apps.curriculum.models import Chapter, Concept


# --- Settings ---------------------------------------------------------------
def test_i18n_settings():
    assert settings.USE_I18N is True
    assert settings.LANGUAGE_CODE == "fr"
    assert [code for code, _name in settings.LANGUAGES] == ["fr", "en"]


def test_locale_middleware_placement():
    mw = settings.MIDDLEWARE
    session = mw.index("django.contrib.sessions.middleware.SessionMiddleware")
    locale = mw.index("django.middleware.locale.LocaleMiddleware")
    common = mw.index("django.middleware.common.CommonMiddleware")
    assert session < locale < common


def test_unfold_is_first_installed_app():
    assert settings.INSTALLED_APPS[0] == "unfold"


# --- Language switching -----------------------------------------------------
@pytest.mark.django_db
def test_home_defaults_to_french(client):
    response = client.get(reverse("curriculum:home"))
    assert response.status_code == 200
    assert response.context["LANGUAGE_CODE"] == "fr"
    assert "Chapitres" in response.content.decode()


@pytest.mark.django_db
def test_set_language_switches_context_to_english(client):
    response = client.post(
        reverse("set_language"),
        {"language": "en", "next": reverse("curriculum:home")},
        follow=True,
    )
    assert settings.LANGUAGE_COOKIE_NAME in response.client.cookies
    assert response.context["LANGUAGE_CODE"] == "en"
    body = response.content.decode()
    assert "Chapters" in body
    assert "Chapitres" not in body


@pytest.mark.django_db
def test_set_language_can_switch_back_to_french(client):
    home = reverse("curriculum:home")
    client.post(reverse("set_language"), {"language": "en", "next": home})
    response = client.post(reverse("set_language"), {"language": "fr", "next": home}, follow=True)
    assert response.context["LANGUAGE_CODE"] == "fr"
    assert "Chapitres" in response.content.decode()


@pytest.mark.django_db
def test_set_language_rejects_unsupported_language(client):
    client.post(reverse("set_language"), {"language": "de", "next": "/"})
    response = client.get(reverse("curriculum:home"))
    assert response.context["LANGUAGE_CODE"] == "fr"


@pytest.mark.django_db
def test_navbar_renders_language_switcher(client):
    body = client.get(reverse("curriculum:home")).content.decode()
    assert f'action="{reverse("set_language")}"' in body
    assert 'name="language"' in body


# --- Model translation ------------------------------------------------------
@pytest.fixture
def chapter(db):
    return Chapter.objects.create(
        title_fr="Générateurs AC",
        title_en="AC Generators",
        slug="ac-generators",
        order=1,
        description_fr="Induction",
        description_en="Induction (EN)",
    )


def test_chapter_title_follows_active_language(chapter):
    with translation.override("fr"):
        assert chapter.title == "Générateurs AC"
        assert chapter.description == "Induction"
    with translation.override("en"):
        assert chapter.title == "AC Generators"
        assert chapter.description == "Induction (EN)"


def test_translation_falls_back_to_other_language(db):
    ch = Chapter.objects.create(title_fr="Seulement FR", slug="fr-only", order=2)
    with translation.override("en"):
        assert ch.title == "Seulement FR"


def test_concept_translated_fields_and_status(chapter):
    concept = Concept.objects.create(
        chapter=chapter,
        title_fr="Loi de Faraday",
        title_en="Faraday's Law",
        slug="faraday",
        order=1,
        clear_text_explanation_fr="**Flux** variable",
        clear_text_explanation_en="Changing **flux**",
    )
    assert concept.status == Concept.Status.DRAFT
    with translation.override("en"):
        assert concept.title == "Faraday's Law"
        assert concept.clear_text_explanation == "Changing **flux**"
    assert {s.value for s in Concept.Status} == {"draft", "review", "mastered"}


@pytest.mark.django_db
def test_home_lists_chapter_in_active_language(client, chapter):
    assert "Générateurs AC" in client.get("/fr/").content.decode()
    assert "AC Generators" in client.get("/en/").content.decode()
