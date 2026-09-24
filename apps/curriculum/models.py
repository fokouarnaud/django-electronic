from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, OuterRef
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .embeds import falstad_embed_url, youtube_embed_url
from .i18n import TranslatedField

# French is the default and fallback language, so every translated pair requires
# its French column and keeps the English one optional.


class Chapter(models.Model):
    title_fr = models.CharField(_("title (French)"), max_length=200)
    title_en = models.CharField(_("title (English)"), max_length=200, blank=True)
    slug = models.SlugField(_("slug"), unique=True)
    order = models.PositiveIntegerField(_("order"), default=0)
    description_fr = models.TextField(_("description (French)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)

    title = TranslatedField("title")
    description = TranslatedField("description")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("chapter")
        verbose_name_plural = _("chapters")

    def __str__(self):
        return self.title or self.slug


class Concept(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        REVIEW = "review", _("In review")
        MASTERED = "mastered", _("Mastered")

    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="concepts", verbose_name=_("chapter")
    )
    title_fr = models.CharField(_("title (French)"), max_length=200)
    title_en = models.CharField(_("title (English)"), max_length=200, blank=True)
    slug = models.SlugField(_("slug"))
    order = models.PositiveIntegerField(_("order"), default=0)
    clear_text_explanation_fr = models.TextField(_("explanation (French, Markdown)"), blank=True)
    clear_text_explanation_en = models.TextField(_("explanation (English, Markdown)"), blank=True)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.DRAFT)

    title = TranslatedField("title")
    clear_text_explanation = TranslatedField("clear_text_explanation")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("concept")
        verbose_name_plural = _("concepts")
        constraints = [
            models.UniqueConstraint(fields=["chapter", "slug"], name="unique_concept_slug_per_chapter"),
        ]

    def __str__(self):
        return self.title or self.slug

    def get_absolute_url(self):
        return reverse("curriculum:concept_detail", kwargs=self._url_kwargs())

    def _url_kwargs(self):
        return {"chapter_slug": self.chapter.slug, "concept_slug": self.slug}

    def get_quiz_url(self):
        return reverse("curriculum:quiz", kwargs=self._url_kwargs())

    def get_complete_url(self):
        return reverse("curriculum:complete", kwargs=self._url_kwargs())


class ResourceLink(models.Model):
    class Type(models.TextChoices):
        BOOK_SECTION = "book_section", _("Book section")
        YOUTUBE_REFERENCE = "youtube_reference", _("YouTube reference")
        FALSTAD_SIMULATION = "falstad_simulation", _("Falstad simulation")

    # Types rendered in an <iframe>, with the function that validates their URL.
    EMBEDDERS = {
        Type.FALSTAD_SIMULATION: falstad_embed_url,
        Type.YOUTUBE_REFERENCE: youtube_embed_url,
    }

    concept = models.ForeignKey(
        Concept, on_delete=models.CASCADE, related_name="resources", verbose_name=_("concept")
    )
    type = models.CharField(_("type"), max_length=20, choices=Type.choices)
    title_fr = models.CharField(_("title (French)"), max_length=200, blank=True)
    title_en = models.CharField(_("title (English)"), max_length=200, blank=True)
    url = models.URLField(_("URL"), max_length=500, blank=True)

    title = TranslatedField("title")

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return self.title or self.url or f"#{self.pk}"

    @property
    def embed_url(self):
        """Safe iframe src for embeddable types, else None (host whitelist in embeds.py)."""
        embedder = self.EMBEDDERS.get(self.type)
        return embedder(self.url) if embedder else None

    def clean(self):
        super().clean()
        if self.type in self.EMBEDDERS and not self.embed_url:
            if self.type == self.Type.FALSTAD_SIMULATION:
                message = _("Enter a falstad.com simulation URL.")
            else:
                message = _("Enter a YouTube video URL.")
            raise ValidationError({"url": message})


class UserProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progress",
        verbose_name=_("user"),
    )
    concept = models.ForeignKey(
        Concept, on_delete=models.CASCADE, related_name="progress", verbose_name=_("concept")
    )
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    notes = models.TextField(_("notes"), blank=True)
    youtube_obs_embedded_url = models.URLField(_("my video (YouTube URL)"), max_length=500, blank=True)

    class Meta:
        verbose_name = _("progress entry")
        verbose_name_plural = _("progress entries")
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="unique_progress_per_user_concept"),
        ]

    def __str__(self):
        return f"{self.user} - {self.concept}"

    def clean(self):
        super().clean()
        if self.youtube_obs_embedded_url and not youtube_embed_url(self.youtube_obs_embedded_url):
            raise ValidationError({"youtube_obs_embedded_url": _("Enter a YouTube video URL.")})


class FlashcardQuerySet(models.QuerySet):
    def answerable(self):
        """Cards a learner can actually get right: at least one correct choice."""
        return self.filter(Exists(Choice.objects.filter(flashcard=OuterRef("pk"), is_correct=True)))


class Flashcard(models.Model):
    class Difficulty(models.IntegerChoices):
        EASY = 1, _("Easy")
        MEDIUM = 2, _("Medium")
        HARD = 3, _("Hard")

    concept = models.ForeignKey(
        Concept, on_delete=models.CASCADE, related_name="flashcards", verbose_name=_("concept")
    )
    question_text_fr = models.TextField(_("question (French)"))
    question_text_en = models.TextField(_("question (English)"), blank=True)
    explanation_fr = models.TextField(_("explanation (French)"), blank=True)
    explanation_en = models.TextField(_("explanation (English)"), blank=True)
    difficulty = models.PositiveSmallIntegerField(
        _("difficulty"), choices=Difficulty.choices, default=Difficulty.EASY
    )

    question_text = TranslatedField("question_text")
    explanation = TranslatedField("explanation")

    objects = FlashcardQuerySet.as_manager()

    class Meta:
        ordering = ["id"]
        verbose_name = _("quiz question")
        verbose_name_plural = _("quiz questions")

    def __str__(self):
        return self.question_text[:60] or f"#{self.pk}"


class Choice(models.Model):
    """One selectable answer of a Flashcard (multiple-choice quiz)."""

    flashcard = models.ForeignKey(
        Flashcard, on_delete=models.CASCADE, related_name="choices", verbose_name=_("quiz question")
    )
    text_fr = models.CharField(_("answer (French)"), max_length=300)
    text_en = models.CharField(_("answer (English)"), max_length=300, blank=True)
    is_correct = models.BooleanField(_("correct answer"), default=False)
    order = models.PositiveIntegerField(_("order"), default=0)

    text = TranslatedField("text")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("answer choice")
        verbose_name_plural = _("answer choices")

    def __str__(self):
        return self.text or f"#{self.pk}"
