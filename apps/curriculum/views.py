from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from .embeds import falstad_embed_url, youtube_embed_url
from .models import Chapter, Concept, Flashcard, ResourceLink, UserProgress
from .progress import (
    SESSION_KEY,
    completed_concept_ids,
    compute_stats,
    effective_status,
    mark_completed,
)


def viewer_stats(request):
    """Stats over every concept for the current viewer (2 queries + progress lookup)."""
    concepts = Concept.objects.only("id", "status")
    return compute_stats(concepts, completed_concept_ids(request))


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
                round(100 * chapter.mastered_count / chapter.total_count)
                if chapter.total_count
                else 0
            )
            all_concepts.extend(concepts)
        context["chapters"] = chapters
        context["stats"] = compute_stats(all_concepts, completed)
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
        completed = completed_concept_ids(self.request)
        context.update(
            concept=concept,
            chapter=concept.chapter,
            flashcards=list(flashcards),
            stats=compute_stats(Concept.objects.only("id", "status"), completed),
            already_completed=concept.id in completed,
        )
        return context


class ConceptDetailView(TemplateView):
    """Explanation (Markdown) + Falstad simulation + video for one concept."""

    template_name = "curriculum/concept_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        concept = get_object_or_404(
            Concept.objects.select_related("chapter"),
            slug=kwargs["concept_slug"],
            chapter__slug=kwargs["chapter_slug"],
        )
        chapter = concept.chapter
        resources = list(concept.resources.all())

        simulations = []
        for link in resources:
            if link.type == ResourceLink.Type.FALSTAD_SIMULATION:
                embed = falstad_embed_url(link.url)
                if embed:  # untrusted hosts are silently not embedded
                    simulations.append({"title": link.title, "src": embed, "open_url": embed})

        # One progress lookup serves both the private OBS video and the completed state.
        request = self.request
        own_video, completed = None, False
        if request.user.is_authenticated:
            progress = UserProgress.objects.filter(user=request.user, concept=concept).first()
            if progress:
                own_video = youtube_embed_url(progress.youtube_obs_embedded_url)
                completed = progress.completed_at is not None
        else:
            completed = concept.id in request.session.get(SESSION_KEY, [])
        status = effective_status(concept, {concept.id} if completed else set())

        reference_videos = [
            {"title": link.title, "src": src}
            for link in resources
            if link.type == ResourceLink.Type.YOUTUBE_REFERENCE
            for src in [youtube_embed_url(link.url)]
            if src
        ]
        video = {"src": own_video, "own": True} if own_video else (
            {"src": reference_videos[0]["src"], "own": False, "title": reference_videos[0]["title"]}
            if reference_videos
            else None
        )

        # Next concept: following one in this chapter, else first of the next chapter.
        next_concept = (
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

        context.update(
            concept=concept,
            chapter=chapter,
            effective_status=status.value,
            status_label=status.label,
            book_sections=[r for r in resources if r.type == ResourceLink.Type.BOOK_SECTION],
            simulations=simulations,
            video=video,
            question_count=concept.flashcards.count(),
            next_concept=next_concept,
        )
        return context


@require_POST
def complete_concept(request, chapter_slug, concept_slug):
    """Log a finished quiz (called with fetch() from quiz.js; CSRF-protected).

    Signed-in users get a UserProgress row; anonymous visitors fall back to the
    session. Returns the viewer's fresh stats so the UI can update without reload.
    """
    concept = get_object_or_404(Concept, slug=concept_slug, chapter__slug=chapter_slug)
    mark_completed(request, concept)
    return JsonResponse(
        {"completed": True, "concept": concept.slug, "stats": viewer_stats(request)}
    )
