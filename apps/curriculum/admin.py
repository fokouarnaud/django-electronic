from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .models import Chapter, Choice, Concept, Flashcard, ResourceLink, UserProgress

# Language block titles stay in their own language on purpose ("Français" / "English").
FR, EN = "Français", "English"

# Django 6.0 switches forms.URLField to https by default; opt in now (and silence
# the RemovedInDjango60Warning) for every URL typed in the admin.
HTTPS_URLS = {models.URLField: {"assume_scheme": "https"}}


class ConceptInline(TabularInline):
    model = Concept
    fields = ("title_fr", "title_en", "slug", "order", "status")
    prepopulated_fields = {"slug": ("title_fr",)}
    extra = 1
    show_change_link = True


class ResourceLinkInline(TabularInline):
    model = ResourceLink
    fields = ("type", "title_fr", "title_en", "url")
    formfield_overrides = HTTPS_URLS
    extra = 1


class FlashcardInline(StackedInline):
    model = Flashcard
    fieldsets = (
        (None, {"fields": ("difficulty",)}),
        (FR, {"fields": ("question_text_fr", "explanation_fr")}),
        (EN, {"fields": ("question_text_en", "explanation_en")}),
    )
    extra = 1
    show_change_link = True  # answers are edited on the flashcard page (no nested inlines)


@admin.register(Chapter)
class ChapterAdmin(ModelAdmin):
    inlines = [ConceptInline]
    list_display = ("title_fr", "title_en", "order", "slug")
    search_fields = ("title_fr", "title_en")
    prepopulated_fields = {"slug": ("title_fr",)}
    ordering = ("order",)
    fieldsets = (
        (FR, {"fields": ("title_fr", "description_fr")}),
        (EN, {"fields": ("title_en", "description_en")}),
        (_("Metadata & SEO"), {"fields": ("slug", "order")}),
    )


@admin.register(Concept)
class ConceptAdmin(ModelAdmin):
    inlines = [ResourceLinkInline, FlashcardInline]
    list_display = ("title_fr", "title_en", "chapter", "order", "status")
    list_filter = ("chapter", "status")
    list_editable = ("status", "order")
    search_fields = ("title_fr", "title_en")
    prepopulated_fields = {"slug": ("title_fr",)}
    list_select_related = ("chapter",)
    fieldsets = (
        (_("Configuration"), {"fields": ("chapter", "status", "order")}),
        (FR, {"fields": ("title_fr", "clear_text_explanation_fr")}),
        (EN, {"fields": ("title_en", "clear_text_explanation_en")}),
        (_("SEO"), {"fields": ("slug",)}),
    )


@admin.register(ResourceLink)
class ResourceLinkAdmin(ModelAdmin):
    list_display = ("title_fr", "title_en", "type", "concept")
    list_filter = ("type",)
    search_fields = ("title_fr", "title_en", "url")
    list_select_related = ("concept",)
    formfield_overrides = HTTPS_URLS


class ChoiceFormSet(BaseInlineFormSet):
    """A question needs at least two answers, one of them correct, or the quiz
    can never be completed."""

    def clean(self):
        super().clean()
        kept = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if len(kept) < 2:
            raise ValidationError(_("Add at least two answers."))
        if not any(data.get("is_correct") for data in kept):
            raise ValidationError(_("Mark at least one answer as correct."))


class ChoiceInline(TabularInline):
    model = Choice
    formset = ChoiceFormSet
    fields = ("text_fr", "text_en", "is_correct", "order")
    extra = 2


@admin.register(Flashcard)
class FlashcardAdmin(ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ("question_text_fr", "question_text_en", "concept", "difficulty")
    list_filter = ("difficulty", "concept")
    search_fields = ("question_text_fr", "question_text_en")
    list_select_related = ("concept",)


@admin.register(UserProgress)
class UserProgressAdmin(ModelAdmin):
    list_display = ("user", "concept", "completed_at")
    list_filter = ("completed_at",)
    list_select_related = ("user", "concept")
    autocomplete_fields = ("user", "concept")  # select boxes don't scale with many rows
    formfield_overrides = HTTPS_URLS
