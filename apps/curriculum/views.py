from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from .embeds import youtube_embed_url
from .models import Chapter, Concept, Flashcard, ResourceLink, UserProgress
from .progress import (
    SESSION_KEY,
    completed_concept_ids,
    compute_stats,
    effective_status,
    mark_completed,
)


def get_concept(chapter_slug, concept_slug):
    """A concept by its URL slugs. Slugs are only unique within a chapter, so a
    concept requested under another chapter's slug is a 404."""
    return get_object_or_404(
        Concept.objects.select_related("chapter"), slug=concept_slug, chapter__slug=chapter_slug
    )


def viewer_stats(request):
    """Stats over every concept for the current viewer."""
    return compute_stats(Concept.objects.only("id", "status"), completed_concept_ids(request))


class ConceptMixin:
    """Resolves self.concept from the URL once per request."""

    def get_context_data(self, **kwargs):
        self.concept = get_concept(kwargs["chapter_slug"], kwargs["concept_slug"])
        context = super().get_context_data(**kwargs)
        context.update(concept=self.concept, chapter=self.concept.chapter)
        return context


class HomeView(TemplateView):
    template_name = "curriculum/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed = completed_concept_ids(self.request)
        # Chapters + prefetched concepts = 2 queries; everything else is computed in Python.
        chapters = list(Chapter.objects.prefetch_related("concepts"))
        all_concepts = []
        for chapter in chapters:
            concepts = list(chapter.concepts.all())
            for concept in concepts:
                status = effective_status(concept, completed)
                concept.effective_status = status.value
                concept.status_label = status.label
                concept.is_mastered = status == Concept.Status.MASTERED
            chapter.first_concept = concepts[0] if concepts else None
            chapter.total_count = len(concepts)
            chapter.mastered_count = sum(c.is_mastered for c in concepts)
            chapter.percent = (
                round(100 * chapter.mastered_count / chapter.total_count) if chapter.total_count else 0
            )
            all_concepts.extend(concepts)
        context["chapters"] = chapters
        context["stats"] = compute_stats(all_concepts, completed)
        return context


class QuizView(ConceptMixin, TemplateView):
    """Self-evaluation for one concept. Answers are checked client-side (see quiz.js)."""

    template_name = "curriculum/quiz.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only cards that can be answered correctly, or the quiz could never be completed.
        flashcards = Flashcard.objects.filter(concept=self.concept).answerable().prefetch_related("choices")
        completed = completed_concept_ids(self.request)
        context.update(
            flashcards=list(flashcards),
            stats=compute_stats(Concept.objects.only("id", "status"), completed),
            already_completed=self.concept.id in completed,
        )
        return context


class ConceptDetailView(ConceptMixin, TemplateView):
    """Explanation (Markdown) + Falstad simulation + video for one concept."""

    template_name = "curriculum/concept_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        concept = self.concept
        resources = list(concept.resources.all())
        by_type = {kind: [r for r in resources if r.type == kind] for kind in ResourceLink.Type}

        own_video, completed = self._viewer_progress()
        references = [link for link in by_type[ResourceLink.Type.YOUTUBE_REFERENCE] if link.embed_url]
        if own_video:
            video = {"src": own_video, "own": True}
        elif references:
            video = {"src": references[0].embed_url, "own": False, "title": references[0].title}
        else:
            video = None

        status = effective_status(concept, {concept.id} if completed else set())
        context.update(
            effective_status=status.value,
            status_label=status.label,
            book_sections=by_type[ResourceLink.Type.BOOK_SECTION],
            # Invalid URLs are rejected by ResourceLink.clean(); the filter is defence in depth.
            simulations=[link for link in by_type[ResourceLink.Type.FALSTAD_SIMULATION] if link.embed_url],
            video=video,
            question_count=concept.flashcards.answerable().count(),
            next_concept=self._next_concept(),
        )
        return context

    def _viewer_progress(self):
        """(own OBS video embed URL or None, completed?) for the current viewer.
        The OBS video is private: only its owner ever sees it."""
        request, concept = self.request, self.concept
        if not request.user.is_authenticated:
            return None, concept.id in request.session.get(SESSION_KEY, [])
        progress = UserProgress.objects.filter(user=request.user, concept=concept).first()
        if progress is None:
            return None, False
        return youtube_embed_url(progress.youtube_obs_embedded_url), progress.completed_at is not None

    def _next_concept(self):
        """The following concept in this chapter, else the first one of the next chapter."""
        concept, chapter = self.concept, self.concept.chapter
        return (
            Concept.objects.select_related("chapter")
            .filter(
                Q(chapter=chapter, order__gt=concept.order)
                | Q(chapter=chapter, order=concept.order, id__gt=concept.id)
                | Q(chapter__order__gt=chapter.order)
                | Q(chapter__order=chapter.order, chapter__id__gt=chapter.id)
            )
            .order_by("chapter__order", "chapter__id", "order", "id")
            .first()
        )


@require_POST
def complete_concept(request, chapter_slug, concept_slug):
    """Log a finished quiz (called with fetch() from quiz.js; CSRF-protected).

    Signed-in users get a UserProgress row; anonymous visitors fall back to the
    session. Returns the viewer's fresh stats so the UI can update without reload.
    """
    concept = get_concept(chapter_slug, concept_slug)
    mark_completed(request, concept)
    return JsonResponse({"completed": True, "concept": concept.slug, "stats": viewer_stats(request)})
