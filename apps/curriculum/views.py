from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from .models import Chapter, Concept, Flashcard


class HomeView(TemplateView):
    template_name = "curriculum/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Two queries total (chapters + prefetched concepts); stats are computed
        # in Python from the prefetched rows so the count stays constant.
        chapters = list(Chapter.objects.prefetch_related("concepts"))
        counts = {status.value: 0 for status in Concept.Status}
        for chapter in chapters:
            concepts = list(chapter.concepts.all())
            chapter.first_concept = concepts[0] if concepts else None
            chapter.total_count = len(concepts)
            chapter.mastered_count = sum(c.status == Concept.Status.MASTERED for c in concepts)
            chapter.percent = (
                round(100 * chapter.mastered_count / chapter.total_count)
                if chapter.total_count
                else 0
            )
            for concept in concepts:
                counts[concept.status] += 1
        total = sum(counts.values())
        context["chapters"] = chapters
        context["stats"] = {
            "total": total,
            "mastered": counts["mastered"],
            "review": counts["review"],
            "draft": counts["draft"],
            "percent": round(100 * counts["mastered"] / total) if total else 0,
        }
        return context


class QuizView(TemplateView):
    """Self-evaluation for one concept. Answers are checked client-side (see quiz.js)."""

    template_name = "curriculum/quiz.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        concept = get_object_or_404(
            Concept.objects.select_related("chapter"),
            slug=kwargs["concept_slug"],
            chapter__slug=kwargs["chapter_slug"],
        )
        flashcards = Flashcard.objects.filter(concept=concept).order_by("id").prefetch_related(
            # Choices ordered by Meta.ordering; one extra query for all cards.
            "choices"
        )
        context.update(concept=concept, chapter=concept.chapter, flashcards=list(flashcards))
        return context
