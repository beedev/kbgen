from datetime import datetime, timedelta, timezone

from src.schemas.article import ArticleDraft
from src.schemas.ticket import Ticket
from src.scoring.health import score


def _ticket(resolution: str, days_ago: int = 0) -> Ticket:
    return Ticket(
        itsm_ticket_id="T-1",
        itsm_provider="test",
        title="test",
        resolution=resolution,
        resolved_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


def _draft(conf: float) -> ArticleDraft:
    return ArticleDraft(
        title="t", summary="s", problem="p", steps_md="1. step", tags=[], category=None, confidence=conf,
    )


def test_recent_high_confidence_scores_high():
    s = score(ticket=_ticket("x" * 200), draft=_draft(0.9), nearest_neighbour_relevance=0.1)
    assert s.overall > 0.75
    assert s.accuracy >= 0.85
    assert s.recency > 0.95
    assert s.coverage > 0.85


def test_thin_resolution_dampens_accuracy():
    s = score(ticket=_ticket("short"), draft=_draft(0.9), nearest_neighbour_relevance=None)
    assert s.accuracy < 0.85


def test_old_ticket_loses_recency():
    s = score(
        ticket=_ticket("x" * 200, days_ago=300),
        draft=_draft(0.9),
        nearest_neighbour_relevance=None,
    )
    assert s.recency < 0.3


def test_duplicate_kills_coverage():
    s = score(
        ticket=_ticket("x" * 200),
        draft=_draft(0.9),
        nearest_neighbour_relevance=0.95,
    )
    assert s.coverage < 0.1


def test_custom_weights_applied():
    s_default = score(
        ticket=_ticket("x" * 200), draft=_draft(0.5), nearest_neighbour_relevance=None
    )
    s_accuracy_heavy = score(
        ticket=_ticket("x" * 200),
        draft=_draft(0.5),
        nearest_neighbour_relevance=None,
        weights={"accuracy": 1.0, "recency": 0.0, "coverage": 0.0},
    )
    assert s_accuracy_heavy.overall == round(s_accuracy_heavy.accuracy, 3)
    assert s_default.overall != s_accuracy_heavy.overall
