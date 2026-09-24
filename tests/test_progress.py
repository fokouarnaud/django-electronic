"""Progress persistence tests (written first): endpoint, auth/anonymous, stats, dashboard."""

import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import translation

from apps.curriculum.models import Chapter, Concept, Flashcard, UserProgress


def complete_url(lang="fr", chapter="ac", concept="faraday"):
    with translation.override(lang):
        return reverse("curriculum:complete", args=[chapter, concept])


@pytest.fixture
def content(db):
    ch = Chapter.objects.create(title_fr="Générateurs", title_en="Generators", slug="ac", order=1)
    concepts = [
        Concept.objects.create(chapter=ch, title_fr="Faraday", slug="faraday", order=1),
        Concept.objects.create(chapter=ch, title_fr="Bagues", slug="rings", order=2, status="review"),
        Concept.objects.create(chapter=ch, title_fr="Balais", slug="brushes", order=3),
    ]
    return ch, concepts


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("me", password="pw")


def post(client, **kwargs):
    return client.post(complete_url(**kwargs))


# --- Endpoint basics --------------------------------------------------------
def test_complete_url_has_language_prefix(content):
    assert complete_url("fr") == "/fr/chapters/ac/concepts/faraday/complete/"
    assert complete_url("en") == "/en/chapters/ac/concepts/faraday/complete/"


def test_get_is_not_allowed(client, content):
    assert client.get(complete_url()).status_code == 405


def test_unknown_concept_is_404(client, content):
    assert post(client, concept="nope").status_code == 404


def test_csrf_is_enforced(content, user):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(user)
    assert strict.post(complete_url()).status_code == 403
    assert not UserProgress.objects.exists()


def test_csrf_token_header_is_accepted(content, user):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(user)
    strict.get("/fr/")  # sets the csrftoken cookie
    token = strict.cookies["csrftoken"].value
    response = strict.post(complete_url(), HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
    assert UserProgress.objects.filter(user=user).count() == 1


# --- Authenticated users: database -----------------------------------------
def test_authenticated_completion_creates_progress_row(client, content, user):
    client.force_login(user)
    response = post(client)
    assert response.status_code == 200
    row = UserProgress.objects.get(user=user, concept__slug="faraday")
    assert row.completed_at is not None


def test_response_carries_updated_stats_payload(client, content, user):
    client.force_login(user)
    data = post(client).json()
    assert data["completed"] is True
    assert data["concept"] == "faraday"
    assert data["stats"] == {"total": 3, "mastered": 1, "review": 1, "draft": 1, "percent": 33}


def test_completion_is_idempotent(client, content, user):
    client.force_login(user)
    first = post(client)
    stamp = UserProgress.objects.get().completed_at
    second = post(client)
    assert UserProgress.objects.count() == 1
    assert UserProgress.objects.get().completed_at == stamp
    assert second.json()["stats"] == first.json()["stats"]


def test_existing_progress_row_is_updated_not_duplicated(client, content, user):
    _ch, concepts = content
    UserProgress.objects.create(
        user=user, concept=concepts[0], notes="mes notes", youtube_obs_embedded_url="https://youtu.be/abc123XYZ_-"
    )
    client.force_login(user)
    post(client)
    row = UserProgress.objects.get()
    assert row.completed_at is not None
    assert row.notes == "mes notes"
    assert row.youtube_obs_embedded_url == "https://youtu.be/abc123XYZ_-"


def test_progress_is_per_user(client, content, user):
    other = get_user_model().objects.create_user("other", password="pw")
    UserProgress.objects.create(user=other, concept=content[1][0], completed_at="2026-01-01T00:00:00Z")
    client.force_login(user)
    assert post(client).json()["stats"]["mastered"] == 1  # only my own completion counts


def test_authored_mastered_status_still_counts(client, content, user):
    Concept.objects.filter(slug="brushes").update(status="mastered")
    client.force_login(user)
    assert post(client).json()["stats"]["mastered"] == 2


# --- Anonymous users: session fallback -------------------------------------
def test_anonymous_completion_uses_session_not_database(client, content):
    response = post(client)
    assert response.status_code == 200
    assert not UserProgress.objects.exists()
    assert response.json()["stats"]["mastered"] == 1
    assert client.session["completed_concept_ids"] == [content[1][0].id]


def test_anonymous_completion_is_idempotent(client, content):
    post(client)
    assert post(client).json()["stats"]["mastered"] == 1
    assert len(client.session["completed_concept_ids"]) == 1


def test_anonymous_sessions_are_isolated(content):
    a, b = Client(), Client()
    post(a)
    assert b.get("/fr/").context["stats"]["mastered"] == 0
    assert a.get("/fr/").context["stats"]["mastered"] == 1


# --- Dashboard --------------------------------------------------------------
def test_home_stats_reflect_authenticated_progress(client, content, user):
    client.force_login(user)
    assert client.get("/fr/").context["stats"]["mastered"] == 0
    post(client)
    assert client.get("/fr/").context["stats"]["mastered"] == 1


def test_home_stats_reflect_anonymous_progress(client, content):
    post(client)
    stats = client.get("/fr/").context["stats"]
    assert stats["mastered"] == 1 and stats["percent"] == 33


def test_stats_tile_shows_exact_ratio(client, content):
    post(client)
    body = client.get("/en/").content.decode()
    match = re.search(r"<p data-stat-ratio[^>]*>(.*?)</p>", body, re.S)
    assert match, "stats ratio element missing"
    assert " ".join(re.sub(r"<[^>]+>", " ", match.group(1)).split()) == "1 / 3 Concepts"


def test_completed_concept_is_highlighted(client, content):
    post(client)
    body = client.get("/fr/").content.decode()
    assert "border-emerald-500/30" in body
    assert 'data-status="mastered"' in body
    assert "data-check" in body


def test_untouched_dashboard_has_no_mastered_markers(client, content):
    body = client.get("/fr/").content.decode()
    assert 'data-status="mastered"' not in body
    assert "data-check" not in body


def test_badge_label_uses_effective_status_in_active_language(client, content):
    post(client)
    assert "Maîtrisé" in client.get("/fr/").content.decode()
    assert "Mastered" in client.get("/en/").content.decode()


def test_home_query_count_for_authenticated_user(client, content, user, django_assert_max_num_queries):
    client.force_login(user)
    UserProgress.objects.create(user=user, concept=content[1][0], completed_at="2026-01-01T00:00:00Z")
    # session + user + chapters + concepts + progress
    with django_assert_max_num_queries(5):
        client.get("/fr/")


def test_concept_page_shows_completed_state(client, content):
    post(client)
    body = client.get("/fr/chapters/ac/concepts/faraday/").content.decode()
    assert 'data-status="mastered"' in body


# --- Quiz page hooks + client script ---------------------------------------
def test_quiz_page_exposes_completion_hooks(client, content):
    Flashcard.objects.create(concept=content[1][0], question_text_fr="Q")
    body = client.get("/fr/chapters/ac/concepts/faraday/quiz/").content.decode()
    assert f'data-complete-url="{complete_url("fr")}"' in body
    assert "data-csrf=" in body
    assert 'data-completed="false"' in body
    assert "data-mastered-count" in body and "data-mastered-total" in body
    assert "duration-200" in body and "motion-reduce" in body


def test_quiz_page_knows_when_already_completed(client, content):
    Flashcard.objects.create(concept=content[1][0], question_text_fr="Q")
    post(client)
    body = client.get("/fr/chapters/ac/concepts/faraday/quiz/").content.decode()
    assert 'data-completed="true"' in body
    assert "data-mastered-count" in body


def test_quiz_metrics_show_viewer_totals(client, content):
    Flashcard.objects.create(concept=content[1][0], question_text_fr="Q")
    post(client)
    ctx = client.get("/fr/chapters/ac/concepts/faraday/quiz/").context
    assert ctx["stats"]["mastered"] == 1 and ctx["stats"]["total"] == 3


def test_script_posts_with_fetch_and_csrf():
    js = Path("apps/curriculum/static/curriculum/quiz.js").read_text(encoding="utf-8")
    assert "fetch(" in js
    assert "X-CSRFToken" in js
    assert 'method: "POST"' in js
    assert 'credentials: "same-origin"' in js
