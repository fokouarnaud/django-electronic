from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .models import Chapter, Choice, Concept, Flashcard, ResourceLink, UserProgress


class ConceptInline(TabularInline):
    model = Concept
    fields = ("title_fr", "title_en", "slug", "order", "status")
    prepopulated_fields = {"slug": ("title_fr",)}
    extra = 1
    show_change_link = True


class ResourceLinkInline(TabularInline):
    model = ResourceLink
    fields = ("type", "title_fr", "title_en", "url")
    extra = 1


class FlashcardInline(StackedInline):
    model = Flashcard
    fieldsets = (
        (None, {"fields": ("difficulty",)}),
        ("Français", {"fields": ("question_text_fr", "explanation_fr")}),
        ("English", {"fields": ("question_text_en", "explanation_en")}),
    )
    extra = 1


@admin.register(Chapter)
class ChapterAdmin(ModelAdmin):
    inlines = [ConceptInline]
    list_display = ("title_fr", "title_en", "order", "slug")
    search_fields = ("title_fr", "title_en")
    prepopulated_fields = {"slug": ("title_fr",)}
    ordering = ("order",)
    fieldsets = (
        ("Français", {"fields": ("title_fr", "description_fr")}),
        ("English", {"fields": ("title_en", "description_en")}),
        ("Metadata & SEO", {"fields": ("slug", "order")}),
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
        ("Configuration", {"fields": ("chapter", "status", "order")}),
        ("Français", {"fields": ("title_fr", "clear_text_explanation_fr")}),
        ("English", {"fields": ("title_en", "clear_text_explanation_en")}),
        ("SEO", {"fields": ("slug",)}),
    )


@admin.register(ResourceLink)
class ResourceLinkAdmin(ModelAdmin):
    list_display = ("title_fr", "title_en", "type", "concept")
    list_filter = ("type",)
    search_fields = ("title_fr", "title_en", "url")
    list_select_related = ("concept",)


class ChoiceInline(TabularInline):
    model = Choice
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
