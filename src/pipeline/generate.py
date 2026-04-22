"""Generation cycle — the core end-to-end flow.

    fetch resolved tickets from ITSM
  → for each ticket:
      check dedup via pgvector
      either mark COVERED
      or generate draft (OpenAI) → score → persist as DRAFT
  → return a PollCycleResult summary
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.itsm import get_adapter
from src.llm.openai_generator import generate_article
from src.pipeline.dedup import check_duplicate
from src.schemas.api import PollCycleResult
from src.schemas.ticket import Ticket
from src.scoring.health import score as score_health
from src.storage import articles as articles_dal
from src.storage import tickets as tickets_dal
from src.storage.models import Article, KbSettings

log = logging.getLogger(__name__)


async def _load_settings(db: AsyncSession) -> KbSettings:
    row = (await db.execute(select(KbSettings).where(KbSettings.id == 1))).scalar_one_or_none()
    if not row:
        raise RuntimeError("kb.settings row missing — re-run migrations")
    return row


async def process_ticket(db: AsyncSession, ticket: Ticket) -> dict:
    """Single-ticket pipeline. Returns a small status dict for the cycle summary."""
    # Allow retry of tickets that were previously SKIPPED (resolution might have
    # been added upstream). For DRAFTED/COVERED, exit idempotently.
    existing = await tickets_dal.get(db, ticket.itsm_ticket_id)
    if existing and existing.decision in ("DRAFTED", "COVERED"):
        return {"status": "skipped", "reason": f"already {existing.decision.lower()}"}

    settings = await _load_settings(db)

    # Gap material: tickets without useful resolution notes can't be drafted
    # honestly. Record them as SKIPPED so the Topics view can surface the gap.
    min_chars = int(settings.min_resolution_chars or 20)
    if len((ticket.resolution or "").strip()) < min_chars:
        await tickets_dal.record(
            db,
            itsm_ticket_id=ticket.itsm_ticket_id,
            itsm_provider=ticket.itsm_provider,
            title=ticket.title,
            description=ticket.description,
            resolution=ticket.resolution,
            topic=ticket.topic,
            resolved_at=ticket.resolved_at,
            decision="SKIPPED",
            decision_reason="resolution notes too thin to draft — flagged as gap",
        )
        return {"status": "skipped", "reason": "thin resolution"}

    dedup = await check_duplicate(db, ticket, threshold=float(settings.dedup_threshold))
    if dedup.covered:
        await tickets_dal.record(
            db,
            itsm_ticket_id=ticket.itsm_ticket_id,
            itsm_provider=ticket.itsm_provider,
            title=ticket.title,
            description=ticket.description,
            resolution=ticket.resolution,
            topic=ticket.topic,
            resolved_at=ticket.resolved_at,
            decision="COVERED",
            decision_reason=dedup.reason,
            matched_article_id=dedup.matched_article_id,
            matched_score=dedup.matched_relevance,
        )
        return {"status": "covered", "reason": dedup.reason}

    draft, model_name, prompt_version = await generate_article(ticket)
    scores = score_health(
        ticket=ticket,
        draft=draft,
        nearest_neighbour_relevance=dedup.matched_relevance,
        weights=settings.score_weights,
        thinness_threshold_chars=int(settings.thinness_threshold_chars or 120),
    )

    row = await articles_dal.create(
        db,
        source_ticket_id=ticket.itsm_ticket_id,
        itsm_provider=ticket.itsm_provider,
        title=draft.title,
        summary=draft.summary,
        problem=draft.problem,
        steps_md=draft.steps_md,
        tags=draft.tags,
        category=draft.category or ticket.topic,
        status="DRAFT",
        source="generated",
        model=model_name,
        prompt_version=prompt_version,
        confidence=draft.confidence,
        score_accuracy=scores.accuracy,
        score_recency=scores.recency,
        score_coverage=scores.coverage,
        score_overall=scores.overall,
    )
    # Index the fresh draft immediately — the next ticket in this cycle that
    # covers the same topic should be able to dedup against it.
    from src.indexing.indexer import index_article as _index  # local to avoid import cycle

    await _index(db, article_id=row.id, title=row.title, body=row.steps_md or "")
    await tickets_dal.record(
        db,
        itsm_ticket_id=ticket.itsm_ticket_id,
        itsm_provider=ticket.itsm_provider,
        title=ticket.title,
        description=ticket.description,
        resolution=ticket.resolution,
        topic=ticket.topic,
        resolved_at=ticket.resolved_at,
        decision="DRAFTED",
        decision_reason=dedup.reason,
        matched_article_id=dedup.matched_article_id,
        matched_score=dedup.matched_relevance,
        draft_article_id=row.id,
    )
    return {"status": "drafted", "draft_id": str(row.id), "overall_score": scores.overall}


async def run_cycle(db: AsyncSession, *, since: datetime | None = None) -> PollCycleResult:
    """One full poll cycle over resolved tickets from the active ITSM adapter."""
    result = PollCycleResult()
    adapter = get_adapter()
    try:
        tickets = await adapter.list_resolved_tickets(since=since)
    except NotImplementedError as exc:
        result.errors.append(f"ITSM adapter '{adapter.name}' not implemented: {exc}")
        return result
    except Exception as exc:
        result.errors.append(f"ITSM fetch failed: {exc.__class__.__name__}: {exc}")
        return result

    for t in tickets:
        result.processed += 1
        try:
            outcome = await process_ticket(db, t)
        except Exception as exc:
            log.exception("ticket %s failed", t.itsm_ticket_id)
            result.errors.append(f"{t.itsm_ticket_id}: {exc}")
            continue
        if outcome["status"] == "drafted":
            result.drafted += 1
        elif outcome["status"] == "covered":
            result.covered += 1
        elif outcome["status"] == "skipped":
            result.skipped += 1
    return result


async def generate_for_ticket_id(db: AsyncSession, ticket_id: str) -> dict:
    """Endpoint helper — generate for a single ticket by id, bypassing polling."""
    adapter = get_adapter()
    ticket = await adapter.get_ticket(ticket_id)
    if not ticket:
        raise ValueError(f"ticket {ticket_id} not found in ITSM '{adapter.name}'")
    return await process_ticket(db, ticket)


async def _article_to_draft_text(a: Article) -> str:
    return f"{a.title}\n\n{a.steps_md or ''}"
