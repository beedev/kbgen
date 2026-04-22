"""Pre-generation dedup — is this ticket already covered by an indexed KB article?"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.searcher import semantic_search_for_dedup
from src.schemas.ticket import Ticket
from src.storage.models import Article


@dataclass
class DedupResult:
    covered: bool
    matched_article_id: UUID | None
    matched_relevance: float | None
    reason: str


async def check_duplicate(
    db: AsyncSession,
    ticket: Ticket,
    threshold: float,
) -> DedupResult:
    # Broader search — matches against DRAFTS too, so the first ticket in a
    # topic produces the master draft, and subsequent similar tickets roll up
    # as COVERED by it. One KB article serves many tickets.
    result = await semantic_search_for_dedup(db, query=ticket.to_index_text(), limit=2)
    if not result.hits:
        return DedupResult(False, None, None, "no existing KB articles indexed")

    # Filter out self-matches: if the top hit is an article whose source was
    # this exact ticket, we're seeing our own draft from an earlier (possibly
    # interrupted) pass. Treat it as not matched and fall through to the next
    # hit, if any. Prevents the "ticket covers itself" rendering bug.
    candidate_hits = []
    for h in result.hits:
        src = (
            await db.execute(
                select(Article.source_ticket_id).where(Article.id == UUID(h.article_id))
            )
        ).scalar_one_or_none()
        if src == ticket.itsm_ticket_id:
            continue
        candidate_hits.append(h)

    if not candidate_hits:
        return DedupResult(False, None, None, "no existing KB articles indexed")

    top = candidate_hits[0]
    if top.relevance >= threshold:
        return DedupResult(
            covered=True,
            matched_article_id=UUID(top.article_id),
            matched_relevance=top.relevance,
            reason=f"matched KB '{top.title}' at relevance {top.relevance:.2f} (≥ {threshold:.2f})",
        )
    return DedupResult(
        covered=False,
        matched_article_id=UUID(top.article_id),
        matched_relevance=top.relevance,
        reason=f"closest KB only at relevance {top.relevance:.2f} (< {threshold:.2f}) — novel",
    )
