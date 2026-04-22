"""/tickets — processed-ticket inspector + gap-RAG drafting."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.openai_generator import generate_article_from_neighbours
from src.retrieval.neighbours import fetch_neighbours
from src.schemas.ticket import Ticket
from src.scoring.health import score as score_health
from src.storage import articles as articles_dal
from src.storage import tickets as tickets_dal
from src.storage.db import get_session
from src.storage.models import KbSettings, ProcessedTicket

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tickets")
async def list_tickets(
    topic: str | None = None,
    limit: int = 1000,
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    stmt = select(ProcessedTicket)
    if topic:
        stmt = stmt.where(ProcessedTicket.topic == topic)
    stmt = stmt.order_by(ProcessedTicket.observed_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "itsm_ticket_id": r.itsm_ticket_id,
            "itsm_provider": r.itsm_provider,
            "title": r.title,
            "topic": r.topic,
            "decision": r.decision,
            "decision_reason": r.decision_reason,
            "matched_article_id": str(r.matched_article_id) if r.matched_article_id else None,
            "matched_score": float(r.matched_score) if r.matched_score is not None else None,
            "draft_article_id": str(r.draft_article_id) if r.draft_article_id else None,
            "resolved_at": r.resolved_at,
            "observed_at": r.observed_at,
        }
        for r in rows
    ]


def _processed_to_ticket_schema(pt: ProcessedTicket) -> Ticket:
    """Rehydrate a `Ticket` pydantic model from the persisted `ProcessedTicket`
    row so the generator / scorer can consume the same shape they get from the
    poll cycle. We don't store `conversation` or `tags` on the processed row,
    so those come back empty — sufficient for gap-RAG since the grounding comes
    from neighbours, not from the target's own conversation."""
    return Ticket(
        itsm_ticket_id=pt.itsm_ticket_id,
        itsm_provider=pt.itsm_provider or "",
        title=pt.title or "",
        description=pt.description or "",
        conversation=[],
        resolution=pt.resolution or "",
        topic=pt.topic,
        tags=[],
        resolved_at=pt.resolved_at,
    )


@router.post("/tickets/{itsm_ticket_id}/gap-draft")
async def draft_for_gap(
    itsm_ticket_id: str,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Synthesise a KB draft for a gap ticket using semantically similar
    existing KBs as grounding context. Returns 422 if no neighbours pass the
    relevance floor — kbgen refuses to draft from thin air.
    """
    pt = await tickets_dal.get(db, itsm_ticket_id)
    if not pt:
        raise HTTPException(404, "ticket not found in kbgen (run a poll first)")
    if pt.decision != "SKIPPED":
        raise HTTPException(
            409,
            f"ticket is {pt.decision}, not a gap — gap-draft only applies to SKIPPED",
        )
    if pt.draft_article_id is not None:
        raise HTTPException(409, "a draft already exists for this ticket")

    settings = (
        await db.execute(select(KbSettings).where(KbSettings.id == 1))
    ).scalar_one_or_none()
    if not settings:
        raise HTTPException(500, "kb.settings row missing — re-run migrations")

    ticket = _processed_to_ticket_schema(pt)
    neighbours = await fetch_neighbours(db, ticket, limit=5, min_relevance=0.55)
    if not neighbours:
        raise HTTPException(
            422,
            "no sufficiently similar existing KB to ground a draft — "
            "resolve the ticket in the ITSM or author a KB manually first",
        )

    draft, model_name, prompt_version = await generate_article_from_neighbours(ticket, neighbours)
    scores = score_health(
        ticket=ticket,
        draft=draft,
        nearest_neighbour_relevance=neighbours[0].relevance,
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
        source="gap-rag",
        model=model_name,
        prompt_version=prompt_version,
        confidence=draft.confidence,
        score_accuracy=scores.accuracy,
        score_recency=scores.recency,
        score_coverage=scores.coverage,
        score_overall=scores.overall,
    )

    from src.indexing.indexer import index_article as _index

    await _index(db, article_id=row.id, title=row.title, body=row.steps_md or "")

    top_rel = neighbours[0].relevance
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
        decision_reason=(
            f"gap-rag synthesis from {len(neighbours)} neighbour(s); "
            f"top relevance {top_rel:.2f}"
        ),
        draft_article_id=row.id,
    )

    return {
        "draft_id": str(row.id),
        "neighbours": [
            {
                "article_id": n.article_id,
                "title": n.title,
                "relevance": round(n.relevance, 3),
            }
            for n in neighbours
        ],
        "prompt_version": prompt_version,
    }
