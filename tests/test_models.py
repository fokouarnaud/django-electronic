"""Model-level rules (written first): validation, URLs, readable names."""

import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils import translation

from apps.curriculum.models import Chapter, Choice, Concept, Flashcard, ResourceLink, UserProgress

FALSTAD = "https://www.falstad.com/circuit/circuitjs.html?ctz=abc"
YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def chapter(db):
    return Chapter.objects.create(title_fr="Générateurs", slug="ac", order=1)


@pytest.fixture
def concept(chapter):
    return Concept.objects.create(chapter=chapter, title_fr="Faraday", slug="faraday")


def errors_of(instance):
    with pytest.raises(ValidationError) as exc:
        instance.full_clean()
    return exc.value.message_dict


# --- French (the fallback language) is mandatory ---------------------------
def test_chapter_requires_french_title(db):
    assert "title_fr" in errors_of(Chapter(slug="x", title_en="Only English"))


def test_concept_requires_french_title(chapter):
    assert "title_fr" in errors_of(Concept(chapter=chapter, slug="x", title_en="EN"))


def test_flashcard_requires_french_question(concept):
    assert "question_text_fr" in errors_of(Flashcard(concept=concept, question_text_en="Q?"))


def test_choice_requires_french_text(concept):
    card = Flashcard.objects.create(concept=concept, question_text_fr="Q")
    assert "text_fr" in errors_of(Choice(flashcard=card, text_en="A"))


def test_english_stays_optional(chapter):
    Concept(chapter=chapter, slug="ok", title_fr="Seulement FR").full_clean()


# --- Resource links: tell the author instead of silently ignoring ----------
@pytest.mark.parametrize(
    "type_, url",
    [
        (ResourceLink.Type.FALSTAD_SIMULATION, ""),
        (ResourceLink.Type.FALSTAD_SIMULATION, "https://evil.example.com/circuit"),
        (ResourceLink.Type.FALSTAD_SIMULATION, YOUTUBE),
        (ResourceLink.Type.YOUTUBE_REFERENCE, ""),
        (ResourceLink.Type.YOUTUBE_REFERENCE, "https://vimeo.com/123"),
        (ResourceLink.Type.YOUTUBE_REFERENCE, FALSTAD),
    ],
)
def test_embeddable_links_must_point_to_their_platform(concept, type_, url):
    link = ResourceLink(concept=concept, type=type_, title_fr="R", url=url)
    assert "url" in errors_of(link)


@pytest.mark.parametrize(
    "type_, url",
    [
        (ResourceLink.Type.FALSTAD_SIMULATION, FALSTAD),
        (ResourceLink.Type.YOUTUBE_REFERENCE, YOUTUBE),
        (ResourceLink.Type.BOOK_SECTION, ""),
        (ResourceLink.Type.BOOK_SECTION, "https://example.com/book#12"),
    ],
)
def test_valid_links_pass(concept, type_, url):
    ResourceLink(concept=concept, type=type_, title_fr="R", url=url).full_clean()


def test_resource_link_exposes_its_embed_url(concept):
    sim = ResourceLink(concept=concept, type=ResourceLink.Type.FALSTAD_SIMULATION, url=FALSTAD)
    video = ResourceLink(concept=concept, type=ResourceLink.Type.YOUTUBE_REFERENCE, url=YOUTUBE)
    book = ResourceLink(concept=concept, type=ResourceLink.Type.BOOK_SECTION, url="https://e.com")
    assert sim.embed_url == FALSTAD
    assert video.embed_url == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
    assert book.embed_url is None


def test_own_video_must_be_youtube(concept, django_user_model):
    user = django_user_model.objects.create_user("me", password="pw")
    bad = UserProgress(user=user, concept=concept, youtube_obs_embedded_url="https://vimeo.com/1")
    assert "youtube_obs_embedded_url" in errors_of(bad)
    UserProgress(
        user=user, concept=concept, youtube_obs_embedded_url="https://youtu.be/abc123XYZ_-"
    ).full_clean()
    UserProgress(user=user, concept=concept).full_clean()


# --- URLs -------------------------------------------------------------------
def test_concept_absolute_and_quiz_urls_follow_active_language(concept):
    with translation.override("fr"):
        assert concept.get_absolute_url() == "/fr/chapters/ac/concepts/faraday/"
        assert concept.get_quiz_url() == "/fr/chapters/ac/concepts/faraday/quiz/"
    with translation.override("en"):
        assert concept.get_absolute_url() == "/en/chapters/ac/concepts/faraday/"


# --- Readable, translated names ---------------------------------------------
def test_verbose_names_are_translated():
    with translation.override("fr"):
        assert str(apps.get_app_config("curriculum").verbose_name) == "Programme"
        assert str(Chapter._meta.verbose_name) == "chapitre"
        assert str(UserProgress._meta.verbose_name_plural) == "progressions"
        assert str(Flashcard._meta.verbose_name_plural) == "questions de quiz"
    with translation.override("en"):
        assert str(UserProgress._meta.verbose_name_plural) == "progress entries"


def test_str_is_never_empty(concept):
    card = Flashcard.objects.create(concept=concept, question_text_fr="")
    choice = Choice.objects.create(flashcard=card, text_fr="")
    assert str(card).strip()
    assert str(choice).strip()
