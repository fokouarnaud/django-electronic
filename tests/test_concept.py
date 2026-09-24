"""Concept detail page tests (written first): i18n, Markdown, embeds, navigation."""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import translation

from apps.curriculum.embeds import falstad_embed_url, youtube_embed_url
from apps.curriculum.models import Chapter, Concept, Flashcard, ResourceLink, UserProgress

FALSTAD = (
    "https://www.falstad.com/circuit/circuitjs.html?ctz=CQAgjCAMB0l3BWcMBMcUHYHMBOA0mAtNAGgDYA2AZmhFHGEA"
)
YOUTUBE_REF = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
OBS_VIDEO = "https://youtu.be/abc123XYZ_-"


def url(lang, chapter="ac", concept="faraday"):
    with translation.override(lang):
        return reverse("curriculum:concept_detail", args=[chapter, concept])


@pytest.fixture
def chapter(db):
    return Chapter.objects.create(title_fr="Générateurs", title_en="Generators", slug="ac", order=1)


@pytest.fixture
def concept(chapter):
    return Concept.objects.create(
        chapter=chapter,
        title_fr="Loi de Faraday",
        title_en="Faraday's Law",
        slug="faraday",
        order=1,
        clear_text_explanation_fr="Un **flux** variable induit une tension.",
        clear_text_explanation_en="A changing **flux** induces a voltage.",
    )


# --- Embed URL helpers (pure functions) ------------------------------------
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
        (
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=10s",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        ),
        ("https://youtu.be/abc123XYZ_-", "https://www.youtube-nocookie.com/embed/abc123XYZ_-"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=" + "x" * 30, None),
        ("https://evil.example.com/watch?v=dQw4w9WgXcQ", None),
        ("https://www.youtube.com.evil.com/watch?v=dQw4w9WgXcQ", None),
        ("javascript:alert(1)", None),
        ("", None),
    ],
)
def test_youtube_embed_url(raw, expected):
    assert youtube_embed_url(raw) == expected


@pytest.mark.parametrize(
    "raw, ok",
    [
        (FALSTAD, True),
        ("https://falstad.com/circuit/", True),
        ("http://www.falstad.com/circuit/circuitjs.html", True),  # upgraded to https
        ("https://falstad.com.evil.com/circuit/", False),
        ("https://evil.com/?u=falstad.com", False),
        ("javascript:alert(1)", False),
        ("", False),
    ],
)
def test_falstad_embed_url(raw, ok):
    result = falstad_embed_url(raw)
    if ok:
        assert result.startswith("https://") and "falstad.com" in result.split("/")[2]
    else:
        assert result is None


# --- Routing / i18n ---------------------------------------------------------
def test_detail_url_has_language_prefix(concept):
    assert url("fr") == "/fr/chapters/ac/concepts/faraday/"
    assert url("en") == "/en/chapters/ac/concepts/faraday/"


def test_detail_404s(client, concept):
    assert client.get("/fr/chapters/ac/concepts/nope/").status_code == 404
    Chapter.objects.create(title_fr="Autre", slug="other", order=2)
    assert client.get("/fr/chapters/other/concepts/faraday/").status_code == 404


def test_french_and_english_content(client, concept):
    fr = client.get(url("fr"))
    assert fr.status_code == 200
    assert "Loi de Faraday" in fr.content.decode()
    assert "Un <strong>flux</strong> variable induit une tension." in fr.content.decode()
    en = client.get(url("en")).content.decode()
    assert "Faraday&#x27;s Law" in en
    assert "A changing <strong>flux</strong> induces a voltage." in en
    assert "Loi de Faraday" not in en


def test_blank_english_explanation_falls_back_to_french(client, concept):
    Concept.objects.filter(pk=concept.pk).update(clear_text_explanation_en="", title_en="")
    body = client.get(url("en")).content.decode()
    assert "Un <strong>flux</strong> variable induit une tension." in body
    assert "Loi de Faraday" in body


def test_missing_explanation_shows_placeholder(client, concept):
    Concept.objects.filter(pk=concept.pk).update(clear_text_explanation_fr="", clear_text_explanation_en="")
    assert "No explanation yet." in client.get(url("en")).content.decode()


def test_markdown_renders_but_raw_html_is_escaped(client, concept):
    Concept.objects.filter(pk=concept.pk).update(
        clear_text_explanation_fr=(
            "## Titre\n\n- a\n- b\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>"
        )
    )
    body = client.get(url("fr")).content.decode()
    assert "<h2" in body and "<li>a</li>" in body
    assert "<script>alert(1)" not in body
    assert "<img src=x" not in body


# --- Embeds -----------------------------------------------------------------
def test_falstad_simulation_is_embedded_responsively(client, concept):
    ResourceLink.objects.create(
        concept=concept, type="falstad_simulation", title_fr="Alternateur", url=FALSTAD
    )
    body = client.get(url("fr")).content.decode()
    assert f'src="{falstad_embed_url(FALSTAD)}"' in body
    assert "<iframe" in body
    assert "Alternateur" in body
    # Responsive wrapper without scrollbars: fixed aspect ratio, clipped, frame fills it.
    assert "data-embed-frame" in body and "aspect-" in body and "overflow-hidden" in body
    assert 'sandbox="allow-scripts allow-same-origin"' in body
    assert 'loading="lazy"' in body


def test_untrusted_simulation_host_is_not_embedded(client, concept):
    ResourceLink.objects.create(
        concept=concept, type="falstad_simulation", title_fr="Piège", url="https://evil.example.com/x"
    )
    body = client.get(url("fr")).content.decode()
    assert "<iframe" not in body
    assert "evil.example.com" not in body


def test_youtube_reference_is_embedded_when_no_own_video(client, concept):
    ResourceLink.objects.create(concept=concept, type="youtube_reference", title_fr="Cours", url=YOUTUBE_REF)
    body = client.get(url("fr")).content.decode()
    assert "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" in body


def test_book_sections_are_listed_not_embedded(client, concept):
    ResourceLink.objects.create(
        concept=concept,
        type="book_section",
        title_fr="Chapitre 12",
        title_en="Chapter 12",
        url="https://example.com/book#12",
    )
    fr = client.get(url("fr")).content.decode()
    assert "Chapitre 12" in fr and "https://example.com/book#12" in fr
    assert "<iframe" not in fr
    assert "Chapter 12" in client.get(url("en")).content.decode()


def test_own_obs_video_from_progress_takes_precedence(client, concept):
    user = get_user_model().objects.create_user("me", password="pw")
    ResourceLink.objects.create(concept=concept, type="youtube_reference", title_fr="Cours", url=YOUTUBE_REF)
    UserProgress.objects.create(user=user, concept=concept, youtube_obs_embedded_url=OBS_VIDEO)
    client.force_login(user)
    body = client.get(url("fr")).content.decode()
    assert "https://www.youtube-nocookie.com/embed/abc123XYZ_-" in body
    assert "data-own-video" in body


def test_progress_video_is_private_to_its_user(client, concept):
    owner = get_user_model().objects.create_user("owner", password="pw")
    UserProgress.objects.create(user=owner, concept=concept, youtube_obs_embedded_url=OBS_VIDEO)
    assert "abc123XYZ_-" not in client.get(url("fr")).content.decode()  # anonymous
    other = get_user_model().objects.create_user("other", password="pw")
    client.force_login(other)
    assert "abc123XYZ_-" not in client.get(url("fr")).content.decode()


def test_no_embed_placeholders_when_no_resources(client, concept):
    body = client.get(url("en")).content.decode()
    assert "<iframe" not in body


# --- Navigation -------------------------------------------------------------
def test_take_the_quiz_link(client, concept):
    Flashcard.objects.create(concept=concept, question_text_fr="Q1")
    body = client.get(url("fr")).content.decode()
    with translation.override("fr"):
        quiz = reverse("curriculum:quiz", args=["ac", "faraday"])
    assert f'href="{quiz}"' in body
    assert "Passer le quiz" in body
    assert "Take the quiz" in client.get(url("en")).content.decode()


def test_next_concept_within_chapter(client, concept, chapter):
    Concept.objects.create(chapter=chapter, title_fr="Bagues", slug="rings", order=2)
    body = client.get(url("fr")).content.decode()
    assert url("fr", concept="rings") in body
    assert "Concept suivant" in body


def test_next_concept_rolls_over_to_next_chapter(client, concept):
    ch2 = Chapter.objects.create(title_fr="Bobines", slug="coils", order=2)
    Concept.objects.create(chapter=ch2, title_fr="Inductance", slug="inductance", order=1)
    assert url("fr", "coils", "inductance") in client.get(url("fr")).content.decode()


def test_last_concept_has_no_next_link(client, concept):
    assert "Concept suivant" not in client.get(url("fr")).content.decode()


# --- Motion + performance ---------------------------------------------------
def test_sections_use_staggered_entrance_within_budget(client, concept):
    body = client.get(url("fr")).content.decode()
    assert "animate-rise" in body and "motion-reduce:animate-none" in body
    assert "animation-delay" in body
    assert "data-magnetic" in body


def test_compiled_css_contains_entrance_animation():
    css = Path("theme/static/css/dist/styles.css").read_text(encoding="utf-8")
    assert ".animate-rise" in css and "@keyframes rise" in css
    assert "250ms" in css or ".25s" in css


def test_query_count_is_bounded(client, concept, chapter, django_assert_max_num_queries):
    for i in range(4):
        ResourceLink.objects.create(
            concept=concept, type="book_section", title_fr=f"B{i}", url="https://e.com"
        )
    Concept.objects.create(chapter=chapter, title_fr="Suivant", slug="next", order=2)
    with django_assert_max_num_queries(6):
        client.get(url("fr"))


def test_home_links_concepts_to_detail_page(client, concept):
    assert url("fr") in client.get("/fr/").content.decode()
