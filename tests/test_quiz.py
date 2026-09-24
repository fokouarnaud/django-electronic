"""Quiz engine tests (written first): routing under a language prefix, i18n, fallback, markup."""

import pytest
from django.urls import reverse
from django.utils import translation

from apps.curriculum.models import Chapter, Choice, Concept, Flashcard


@pytest.fixture
def concept(db):
    chapter = Chapter.objects.create(title_fr="Générateurs", title_en="Generators", slug="ac", order=1)
    return Concept.objects.create(
        chapter=chapter, title_fr="Loi de Faraday", title_en="Faraday's Law", slug="faraday", order=1
    )


@pytest.fixture
def card(concept):
    card = Flashcard.objects.create(
        concept=concept,
        question_text_fr="Que produit un flux variable ?",
        question_text_en="What does a changing flux produce?",
        explanation_fr="Une force électromotrice induite.",
        explanation_en="An induced electromotive force.",
    )
    Choice.objects.create(flashcard=card, text_fr="Une fem", text_en="An emf", is_correct=True, order=1)
    Choice.objects.create(flashcard=card, text_fr="Rien", text_en="Nothing", is_correct=False, order=2)
    return card


def quiz_url(lang):
    with translation.override(lang):
        return reverse("curriculum:quiz", args=["ac", "faraday"])


# --- Routing ----------------------------------------------------------------
def test_quiz_url_carries_language_prefix(concept):
    assert quiz_url("fr") == "/fr/chapters/ac/concepts/faraday/quiz/"
    assert quiz_url("en") == "/en/chapters/ac/concepts/faraday/quiz/"


def test_root_redirects_to_default_language_prefix(client, db):
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == "/fr/"


def test_quiz_page_resolves(client, card):
    response = client.get(quiz_url("fr"))
    assert response.status_code == 200
    assert response.context["concept"].slug == "faraday"


def test_unknown_concept_is_404(client, card):
    assert client.get("/fr/chapters/ac/concepts/nope/quiz/").status_code == 404


def test_concept_from_another_chapter_is_404(client, card):
    Chapter.objects.create(title_fr="Autre", slug="other", order=2)
    assert client.get("/fr/chapters/other/concepts/faraday/quiz/").status_code == 404


# --- Translation by URL prefix ---------------------------------------------
def test_french_prefix_renders_french(client, card):
    response = client.get(quiz_url("fr"))
    body = response.content.decode()
    assert response.context["LANGUAGE_CODE"] == "fr"
    assert "Que produit un flux variable ?" in body
    assert "Une force électromotrice induite." in body
    assert "Une fem" in body
    assert "Explication" in body
    assert "What does a changing flux produce?" not in body


def test_english_prefix_renders_english(client, card):
    response = client.get(quiz_url("en"))
    body = response.content.decode()
    assert response.context["LANGUAGE_CODE"] == "en"
    assert "What does a changing flux produce?" in body
    assert "An induced electromotive force." in body
    assert "An emf" in body
    assert "Explanation" in body
    assert "Que produit" not in body


def test_prefix_beats_previous_language_cookie(client, card):
    client.post(reverse("set_language"), {"language": "en", "next": "/en/"})
    assert client.get(quiz_url("fr")).context["LANGUAGE_CODE"] == "fr"


def test_switcher_keeps_user_on_the_quiz_in_new_language(client, card):
    response = client.post(reverse("set_language"), {"language": "en", "next": quiz_url("fr")})
    assert response["Location"] == quiz_url("en")


# --- Fallback to French -----------------------------------------------------
def test_blank_english_fields_fall_back_to_french(client, concept):
    card = Flashcard.objects.create(
        concept=concept, question_text_fr="Question FR", explanation_fr="Explication FR"
    )
    Choice.objects.create(flashcard=card, text_fr="Réponse FR", is_correct=True)
    body = client.get(quiz_url("en")).content.decode()
    assert "Question FR" in body
    assert "Explication FR" in body
    assert "Réponse FR" in body


# --- Markup the JS relies on ------------------------------------------------
def test_choices_expose_correctness_and_explanation_hook(client, card):
    body = client.get(quiz_url("fr")).content.decode()
    assert body.count("data-choice") == 2
    assert 'data-correct="true"' in body and 'data-correct="false"' in body
    assert "data-explanation" in body
    assert "data-quiz" in body


def test_choices_follow_order(client, card):
    Choice.objects.filter(text_fr="Rien").update(order=0)
    body = client.get(quiz_url("fr")).content.decode()
    assert body.index("Rien") < body.index("Une fem")


def test_motion_classes_are_within_budget(client, card):
    body = client.get(quiz_url("fr")).content.decode()
    assert "duration-200" in body and "duration-250" in body and "ease-out" in body
    assert "motion-reduce" in body


def test_empty_quiz_shows_message(client, concept):
    response = client.get(quiz_url("en"))
    assert response.status_code == 200
    assert "No questions yet." in response.content.decode()


def test_query_count_is_constant(client, card, django_assert_max_num_queries):
    for i in range(3):
        extra = Flashcard.objects.create(concept=card.concept, question_text_fr=f"Q{i}")
        Choice.objects.create(flashcard=extra, text_fr="a", is_correct=True)
    with django_assert_max_num_queries(3):
        client.get(quiz_url("fr"))


def test_home_links_to_quiz(client, card):
    body = client.get("/fr/").content.decode()
    assert quiz_url("fr") in body


# --- Model ------------------------------------------------------------------
def test_choice_text_follows_active_language(card):
    choice = card.choices.get(is_correct=True)
    with translation.override("en"):
        assert choice.text == "An emf"
    with translation.override("fr"):
        assert choice.text == "Une fem"
