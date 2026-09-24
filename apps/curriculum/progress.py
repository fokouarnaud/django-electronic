"""Per-viewer progress: database rows for signed-in users, session for anonymous ones."""

from django.utils import timezone

from .models import Concept, UserProgress

SESSION_KEY = "completed_concept_ids"


def completed_concept_ids(request):
    """IDs of concepts the current viewer has completed."""
    if request.user.is_authenticated:
        return set(
            UserProgress.objects.filter(user=request.user, completed_at__isnull=False).values_list(
                "concept_id", flat=True
            )
        )
    return set(request.session.get(SESSION_KEY, []))


def mark_completed(request, concept):
    """Record a completion. Idempotent: the first completion time is kept."""
    if request.user.is_authenticated:
        # get_or_create keeps notes / OBS video on an existing row.
        progress, _created = UserProgress.objects.get_or_create(user=request.user, concept=concept)
        if progress.completed_at is None:
            progress.completed_at = timezone.now()
            progress.save(update_fields=["completed_at"])
        return
    ids = set(request.session.get(SESSION_KEY, []))
    ids.add(concept.id)
    request.session[SESSION_KEY] = sorted(ids)


def effective_status(concept, completed_ids):
    """Authored 'mastered' or the viewer's own completion both count as mastered."""
    if concept.status == Concept.Status.MASTERED or concept.id in completed_ids:
        return Concept.Status.MASTERED
    return Concept.Status(concept.status)


def compute_stats(concepts, completed_ids):
    counts = {status.value: 0 for status in Concept.Status}
    for concept in concepts:
        counts[effective_status(concept, completed_ids).value] += 1
    total = sum(counts.values())
    return {
        "total": total,
        "mastered": counts["mastered"],
        "review": counts["review"],
        "draft": counts["draft"],
        "percent": round(100 * counts["mastered"] / total) if total else 0,
    }
