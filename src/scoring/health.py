"""Compute health sub-scores for a generated draft.

Inputs: the ticket (for recency), the draft (for self-rated accuracy), and the
nearest-neighbour relevance from the dedup pass (for coverage — more novel =
higher coverage score).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.schemas.article import ArticleDraft, HealthScore
from src.schemas.ticket import Ticket


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def score(
    *,
    ticket: Ticket,
    draft: ArticleDraft,
    nearest_neighbour_relevance: float | None,
    weights: dict[str, float] | None = None,
) -> HealthScore:
    w = {"accuracy": 0.5, "recency": 0.2, "coverage": 0.3}
    if weights:
        w.update(weights)

    # Accuracy: trust the model's self-rated confidence, dampened when the ticket's
    # resolution notes were thin.
    resolution_len = len(ticket.resolution or "")
    thinness_penalty = 0.0 if resolution_len >= 120 else (1 - resolution_len / 120) * 0.25
    accuracy = _clip(draft.confidence - thinness_penalty)

    # Recency: 1 when resolved today, decays linearly over 365 days.
    if ticket.resolved_at:
        age_days = (datetime.now(timezone.utc) - ticket.resolved_at).total_seconds() / 86400
        recency = _clip(1.0 - (age_days / 365.0))
    else:
        recency = 0.5  # unknown → neutral

    # Coverage: higher when no similar KB already exists. Relevance is
    # cosine similarity in [0, 1] where 1 = near-duplicate.
    if nearest_neighbour_relevance is None:
        coverage = 1.0  # nothing similar exists
    else:
        coverage = _clip(1.0 - nearest_neighbour_relevance)

    overall = _clip(
        w["accuracy"] * accuracy + w["recency"] * recency + w["coverage"] * coverage
    )
    return HealthScore(
        accuracy=round(accuracy, 3),
        recency=round(recency, 3),
        coverage=round(coverage, 3),
        overall=round(overall, 3),
    )
