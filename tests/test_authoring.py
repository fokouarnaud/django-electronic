"""Admin authoring guards (written first): the admin must refuse broken content."""

import pytest
from django.contrib import admin
from django.urls import reverse
from django.utils import translation

from apps.curriculum.models import Chapter, Concept, Flashcard, ResourceLink, UserProgress


@pytest.fixture
def concept(db):
    chapter = Chapter.objects.create(title_fr="Générateurs", slug="ac", order=1)
    return Concept.objects.create(chapter=chapter, title_fr="Faraday", slug="faraday")


def flashcard_post(concept, choices):
    data = {
        "concept": str(concept.pk),
        "question_text_fr": "Que produit un flux variable ?",
        "difficulty": "1",
        "choices-TOTAL_FORMS": str(len(choices)),
        "choices-INITIAL_FORMS": "0",
        "choices-MIN_NUM_FORMS": "0",
        "choices-MAX_NUM_FORMS": "1000",
        "_save": "Save",
    }
    for i, (text, correct) in enumerate(choices):
        data[f"choices-{i}-text_fr"] = text
        data[f"choices-{i}-order"] = str(i)
        if correct:
            data[f"choices-{i}-is_correct"] = "on"
    return data


def test_flashcard_needs_a_correct_choice(admin_client, concept):
    url = reverse("admin:curriculum_flashcard_add")

    response = admin_client.post(url, flashcard_post(concept, [("Une fem", False), ("Rien", False)]))
    assert response.status_code == 200  # redisplayed with an error
    assert not Flashcard.objects.exists()

    response = admin_client.post(url, flashcard_post(concept, [("Une fem", True), ("Rien", False)]))
    assert response.status_code == 302
    assert Flashcard.objects.get().choices.filter(is_correct=True).count() == 1


def test_flashcard_needs_at_least_two_choices(admin_client, concept):
    response = admin_client.post(
        reverse("admin:curriculum_flashcard_add"), flashcard_post(concept, [("Une fem", True)])
    )
    assert response.status_code == 200
    assert not Flashcard.objects.exists()


def test_url_fields_assume_https(rf, admin_user):
    request = rf.get("/")
    request.user = admin_user
    form_class = admin.site._registry[ResourceLink].get_form(request)
    assert form_class.base_fields["url"].assume_scheme == "https"
    form_class = admin.site._registry[UserProgress].get_form(request)
    assert form_class.base_fields["youtube_obs_embedded_url"].assume_scheme == "https"


def test_user_progress_uses_autocomplete():
    assert set(admin.site._registry[UserProgress].autocomplete_fields) == {"user", "concept"}


def test_generic_fieldset_labels_are_translated():
    with translation.override("fr"):
        concept_names = [str(name) for name, _opts in admin.site._registry[Concept].fieldsets]
        chapter_names = [str(name) for name, _opts in admin.site._registry[Chapter].fieldsets]
    assert concept_names == ["Configuration", "Français", "English", "Référencement"]
    assert chapter_names == ["Français", "English", "Métadonnées et référencement"]


def test_concept_admin_offers_view_on_site(admin_client, concept):
    body = admin_client.get(reverse("admin:curriculum_concept_change", args=[concept.pk])).content.decode()
    assert "/admin/r/" in body  # Django's "view on site" link, enabled by get_absolute_url
