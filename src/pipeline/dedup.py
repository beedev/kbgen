"""Pre-generation dedup — is this ticket already covered by an indexed KB article?"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.searcher import semantic_search_for_dedup
from src.schemas.ticket import Ticket


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
    result = await semantic_search_for_dedup(db, query=ticket.to_index_text(), limit=1)
    if not result.hits:
        return DedupResult(False, None, None, "no existing KB articles indexed")
    top = result.hits[0]
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
