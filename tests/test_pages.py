"""Error pages, bilingual SEO and language switcher (written first)."""

import pytest
from django.template import loader
from django.utils import translation

from apps.curriculum.models import Chapter, Choice, Concept, Flashcard


@pytest.fixture
def concept(db):
    chapter = Chapter.objects.create(title_fr="Générateurs", slug="ac", order=1)
    return Concept.objects.create(chapter=chapter, title_fr="Faraday", slug="faraday")


def test_custom_404_is_branded_and_translated(client, db):
    response = client.get("/fr/nulle-part/")
    assert response.status_code == 404
    body = response.content.decode()
    assert "Page introuvable" in body and "Labo d'électronique" in body
    assert 'href="/fr/"' in body
    english = client.get("/en/nowhere/").content.decode()
    assert "Page not found" in english and 'href="/en/"' in english


def test_500_template_renders_without_any_context():
    html = loader.get_template("500.html").render()
    assert "500" in html and "<html" in html
    assert "stylesheet" not in html  # self-contained: must not depend on static files


def test_home_declares_hreflang_alternates(client, db):
    body = client.get("/fr/").content.decode()
    assert '<link rel="alternate" hreflang="fr" href="http://testserver/fr/">' in body
    assert '<link rel="alternate" hreflang="en" href="http://testserver/en/">' in body
    assert '<link rel="alternate" hreflang="x-default" href="http://testserver/fr/">' in body


def test_concept_page_hreflang_points_to_translated_path(client, concept):
    with translation.override("en"):
        url = concept.get_absolute_url()
    body = client.get(url).content.decode()
    assert 'hreflang="fr" href="http://testserver/fr/chapters/ac/concepts/faraday/"' in body
    assert 'hreflang="en" href="http://testserver/en/chapters/ac/concepts/faraday/"' in body


def test_language_switcher_uses_language_names_not_flags(client, db):
    body = client.get("/fr/").content.decode()
    assert "\U0001f1eb\U0001f1f7" not in body and "\U0001f1ec\U0001f1e7" not in body
    assert "Français" in body and "English" in body


def test_pages_have_a_meta_description(client, concept):
    assert '<meta name="description"' in client.get("/fr/").content.decode()
    assert '<meta name="description"' in client.get(concept.get_absolute_url()).content.decode()


def test_quiz_skips_unanswerable_cards(client, concept):
    good = Flashcard.objects.create(concept=concept, question_text_fr="Bonne question")
    Choice.objects.create(flashcard=good, text_fr="oui", is_correct=True)
    Choice.objects.create(flashcard=good, text_fr="non")
    Flashcard.objects.create(concept=concept, question_text_fr="Sans réponse")
    no_correct = Flashcard.objects.create(concept=concept, question_text_fr="Aucune bonne")
    Choice.objects.create(flashcard=no_correct, text_fr="x", is_correct=False)

    response = client.get(concept.get_quiz_url())
    body = response.content.decode()
    assert [c.pk for c in response.context["flashcards"]] == [good.pk]
    assert 'data-total="1"' in body
    assert "Sans réponse" not in body and "Aucune bonne" not in body
