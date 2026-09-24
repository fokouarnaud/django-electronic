"""Dashboard tests (written first): bento data, status badges, stats, labels, query count."""

import pytest
from django.urls import reverse

from apps.curriculum.models import Chapter, Concept

HOME = "curriculum:home"


@pytest.fixture
def content(db):
    ch1 = Chapter.objects.create(title_fr="Générateurs AC", title_en="AC Generators", slug="ac", order=1)
    ch2 = Chapter.objects.create(title_fr="Bobines", title_en="Coils", slug="coils", order=2)
    Concept.objects.create(
        chapter=ch1,
        title_fr="Loi de Faraday",
        title_en="Faraday's Law",
        slug="faraday",
        order=1,
        status="mastered",
    )
    Concept.objects.create(
        chapter=ch1,
        title_fr="Bagues collectrices",
        title_en="Slip rings",
        slug="slip",
        order=2,
        status="review",
    )
    Concept.objects.create(
        chapter=ch1, title_fr="Bagues fendues", title_en="Split rings", slug="split", order=3, status="draft"
    )
    return ch1, ch2


def test_stats_in_context(client, content):
    stats = client.get(reverse(HOME)).context["stats"]
    assert stats == {"total": 3, "mastered": 1, "review": 1, "draft": 1, "percent": 33}


def test_stats_empty_database(client, db):
    stats = client.get(reverse(HOME)).context["stats"]
    assert stats["total"] == 0 and stats["percent"] == 0


def test_chapter_concepts_listed_in_order(client, content):
    body = client.get(reverse(HOME)).content.decode()
    assert body.index("Loi de Faraday") < body.index("Bagues collectrices") < body.index("Bagues fendues")


def test_status_badges_carry_semantic_state(client, content):
    body = client.get(reverse(HOME)).content.decode()
    for status in ("mastered", "review", "draft"):
        assert f'data-status="{status}"' in body
    assert "Maîtrisé" in body and "En révision" in body and "Brouillon" in body


def test_labels_are_translated(client, content):
    fr = client.get("/fr/").content.decode()
    for label in ("Concepts", "Statistiques", "Progression", "Commencer"):
        assert label in fr
    en = client.get("/en/").content.decode()
    for label in ("Concepts", "Statistics", "Progress", "Start", "Mastered"):
        assert label in en
    assert "Statistiques" not in en


def test_dark_shell_and_bento_classes(client, content):
    body = client.get(reverse(HOME)).content.decode()
    for cls in (
        "bg-slate-950",
        "bg-slate-900/60",
        "border-slate-800",
        "hover:border-teal-500/40",
        "hover:scale-[1.01]",
        "duration-200",
        "ease-out",
    ):
        assert cls in body


def test_language_switcher_marks_active_language(client, content):
    body = client.get(reverse(HOME)).content.decode()
    assert 'value="fr" selected' in body


def test_query_count_is_constant(client, content, django_assert_max_num_queries):
    with django_assert_max_num_queries(2):
        client.get(reverse(HOME))
