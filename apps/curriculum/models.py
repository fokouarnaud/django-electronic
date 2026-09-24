from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .i18n import TranslatedField


class Chapter(models.Model):
    title_fr = models.CharField(_("title (French)"), max_length=200, blank=True)
    title_en = models.CharField(_("title (English)"), max_length=200, blank=True)
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)
    description_fr = models.TextField(_("description (French)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)

    title = TranslatedField("title")
    description = TranslatedField("description")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title or self.slug


class Concept(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        REVIEW = "review", _("In review")
        MASTERED = "mastered", _("Mastered")

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="concepts")
    title_fr = models.CharField(_("title (French)"), max_length=200, blank=True)
    title_en = models.CharField(_("title (English)"), max_length=200, blank=True)
    slug = models.SlugField()
    order = models.PositiveIntegerField(default=0)
    clear_text_explanation_fr = models.TextField(
        _("explanation (French, Markdown)"), blank=True
    )
    clear_text_explanation_en = models.TextField(
        _("explanation (English, Markdown)"), blank=True
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    title = TranslatedField("title")
    clear_text_explanation = TranslatedField("clear_text_explanation")

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "slug"], name="unique_concept_slug_per_chapter"
            ),
        ]

    def __str__(self):
        return self.title or self.slug


class ResourceLink(models.Model):
    class Type(models.TextChoices):
        BOOK_SECTION = "book_section", _("Book section")
        YOUTUBE_REFERENCE = "youtube_reference", _("YouTube reference")
        FALSTAD_SIMULATION = "falstad_simulation", _("Falstad simulation")

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="resources")
    type = models.CharField(max_length=20, choices=Type.choices)
    title_fr = models.CharField(_("title (French)"), max_length=200, blank=True)
    title_en = models.CharField(_("title (English)"), max_length=200, blank=True)
    url = models.URLField(max_length=500, blank=True)

    title = TranslatedField("title")

    def __str__(self):
        return self.title or self.url


class UserProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress"
    )
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    youtube_obs_embedded_url = models.URLField(max_length=500, blank=True)

    class Meta:
        verbose_name_plural = "user progress"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "concept"], name="unique_progress_per_user_concept"
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.concept}"


class Flashcard(models.Model):
    class Difficulty(models.IntegerChoices):
        EASY = 1, _("Easy")
        MEDIUM = 2, _("Medium")
        HARD = 3, _("Hard")

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="flashcards")
    question_text_fr = models.TextField(_("question (French)"), blank=True)
    question_text_en = models.TextField(_("question (English)"), blank=True)
    explanation_fr = models.TextField(_("explanation (French)"), blank=True)
    explanation_en = models.TextField(_("explanation (English)"), blank=True)
    difficulty = models.PositiveSmallIntegerField(
        choices=Difficulty.choices, default=Difficulty.EASY
    )

    question_text = TranslatedField("question_text")
    explanation = TranslatedField("explanation")

    def __str__(self):
        return self.question_text[:60]


class Choice(models.Model):
    """One selectable answer of a Flashcard (multiple-choice quiz)."""

    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name="choices")
    text_fr = models.CharField(_("answer (French)"), max_length=300, blank=True)
    text_en = models.CharField(_("answer (English)"), max_length=300, blank=True)
    is_correct = models.BooleanField(_("correct answer"), default=False)
    order = models.PositiveIntegerField(default=0)

    text = TranslatedField("text")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text
