from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from .embeds import falstad_embed_url, youtube_embed_url
from .models import Chapter, Concept, Flashcard, ResourceLink, UserProgress


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

        # The user's own OBS video (private to them) wins over reference videos.
        own_video = None
        if self.request.user.is_authenticated:
            progress = UserProgress.objects.filter(user=self.request.user, concept=concept).first()
            own_video = youtube_embed_url(progress.youtube_obs_embedded_url) if progress else None
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
            book_sections=[r for r in resources if r.type == ResourceLink.Type.BOOK_SECTION],
            simulations=simulations,
            video=video,
            question_count=concept.flashcards.count(),
            next_concept=next_concept,
        )
        return context
