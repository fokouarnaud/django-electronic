"""Admin tests (written first): Unfold inheritance, layout, inlines, prepopulation."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.curriculum.models import Chapter, Concept, Flashcard, ResourceLink, UserProgress


@pytest.fixture
def admin_client(client, db):
    user = get_user_model().objects.create_superuser("root", "root@example.com", "pw")
    client.force_login(user)
    return client


@pytest.fixture
def chapter(db):
    return Chapter.objects.create(title_fr="Générateurs", title_en="Generators", slug="gen", order=1)


def _fieldset_map(model_admin):
    return {name: tuple(opts["fields"]) for name, opts in model_admin.fieldsets}


def test_all_curriculum_models_registered_with_unfold():
    for model in (Chapter, Concept, ResourceLink, Flashcard, UserProgress):
        model_admin = admin.site._registry[model]
        assert isinstance(model_admin, ModelAdmin), model
        for inline_cls in model_admin.inlines:
            assert issubclass(inline_cls, (TabularInline, StackedInline))


def test_chapter_admin_config():
    ma = admin.site._registry[Chapter]
    assert [i.model for i in ma.inlines] == [Concept]
    assert issubclass(ma.inlines[0], TabularInline)
    assert ma.inlines[0].fields == ("title_fr", "title_en", "slug", "order", "status")
    assert ma.inlines[0].extra == 1
    assert tuple(ma.list_display) == ("title_fr", "title_en", "order", "slug")
    assert tuple(ma.search_fields) == ("title_fr", "title_en")
    assert ma.prepopulated_fields == {"slug": ("title_fr",)}
    assert list(_fieldset_map(ma).values()) == [
        ("title_fr", "description_fr"),
        ("title_en", "description_en"),
        ("slug", "order"),
    ]


def test_concept_admin_config():
    ma = admin.site._registry[Concept]
    assert tuple(ma.list_display) == ("title_fr", "title_en", "chapter", "order", "status")
    assert tuple(ma.list_filter) == ("chapter", "status")
    assert tuple(ma.list_editable) == ("status", "order")
    assert ma.prepopulated_fields == {"slug": ("title_fr",)}
    assert list(_fieldset_map(ma).values()) == [
        ("chapter", "status", "order"),
        ("title_fr", "clear_text_explanation_fr"),
        ("title_en", "clear_text_explanation_en"),
        ("slug",),
    ]
    assert {i.model for i in ma.inlines} == {ResourceLink, Flashcard}


@pytest.mark.parametrize("name", ["chapter", "concept", "resourcelink", "flashcard", "userprogress"])
def test_changelist_renders(admin_client, name, chapter):
    response = admin_client.get(reverse(f"admin:curriculum_{name}_changelist"))
    assert response.status_code == 200


def test_chapter_change_page_shows_concept_inline(admin_client, chapter):
    response = admin_client.get(reverse("admin:curriculum_chapter_change", args=[chapter.pk]))
    assert response.status_code == 200
    assert "concepts-TOTAL_FORMS" in response.content.decode()


def test_concept_change_page_shows_resource_and_flashcard_inlines(admin_client, chapter):
    concept = Concept.objects.create(chapter=chapter, title_fr="Faraday", slug="faraday")
    response = admin_client.get(reverse("admin:curriculum_concept_change", args=[concept.pk]))
    body = response.content.decode()
    assert response.status_code == 200
    assert "resources-TOTAL_FORMS" in body
    assert "flashcards-TOTAL_FORMS" in body


def test_concept_list_editable_saves_status(admin_client, chapter):
    concept = Concept.objects.create(chapter=chapter, title_fr="Faraday", slug="faraday", order=1)
    data = {
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
        "form-0-id": str(concept.pk),
        "form-0-status": "mastered",
        "form-0-order": "5",
        "_save": "Save",
    }
    admin_client.post(reverse("admin:curriculum_concept_changelist"), data)
    concept.refresh_from_db()
    assert concept.status == "mastered"
    assert concept.order == 5
