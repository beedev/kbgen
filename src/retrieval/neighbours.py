"""Neighbour retrieval for gap-ticket RAG drafting.

Given a ticket whose own resolution is too thin to draft from, find the
closest existing KB articles (and, where available, the source tickets
behind them) so the LLM can synthesise a new draft grounded in that
evidence rather than hallucinating.

Reuses the pgvector query shape from `semantic_search_for_dedup` but
widens the result set and joins back to `kb.processed_ticket` to pull
the raw resolution text from each neighbour's source ticket.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.embeddings import embed_one
from src.schemas.ticket import Ticket


@dataclass
class NeighbourContext:
    article_id: str
    relevance: float
    title: str
    category: str | None
    steps_md: str | None
    source_ticket_id: str | None
    source_ticket_title: str | None
    source_ticket_description: str | None
    source_ticket_resolution: str | None


async def fetch_neighbours(
    db: AsyncSession,
    ticket: Ticket,
    *,
    limit: int = 5,
    min_relevance: float = 0.55,
) -> list[NeighbourContext]:
    """Return the top-K KB articles closest to this ticket, ranked by cosine
    similarity against the article's best chunk. Each hit comes back with the
    raw source ticket attached (where the article has one) so the prompt can
    ground on concrete resolution language rather than only the distilled KB
    steps.

    Filters out anything below `min_relevance` — below that floor we'd rather
    refuse to draft than invite hallucination.
    """
    query_text = f"{ticket.title}\n\n{ticket.description}".strip()
    if not query_text:
        return []

    vec = await embed_one(query_text)
    vec_literal = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"

    sql = text(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (c.article_id)
                c.article_id,
                1 - (c.embedding <=> '{vec_literal}'::vector) AS relevance,
                a.title,
                a.category,
                a.steps_md,
                a.source_ticket_id,
                pt.title        AS src_title,
                pt.description  AS src_description,
                pt.resolution   AS src_resolution
            FROM kb.chunk c
            JOIN kb.article a ON a.id = c.article_id
            LEFT JOIN kb.processed_ticket pt
                ON pt.itsm_ticket_id = a.source_ticket_id
            WHERE a.status IN ('PUSHED','IMPORTED','APPROVED','DRAFT','EDITED')
            ORDER BY c.article_id, c.embedding <=> '{vec_literal}'::vector
        ) t
        WHERE t.relevance >= :min_relevance
        ORDER BY t.relevance DESC
        LIMIT :limit
        """
    )
    rows = (
        await db.execute(sql, {"limit": limit, "min_relevance": min_relevance})
    ).mappings().all()

    return [
        NeighbourContext(
            article_id=str(r["article_id"]),
            relevance=float(r["relevance"]),
            title=r["title"],
            category=r["category"],
            steps_md=r["steps_md"],
            source_ticket_id=r["source_ticket_id"],
            source_ticket_title=r["src_title"],
            source_ticket_description=r["src_description"],
            source_ticket_resolution=r["src_resolution"],
        )
        for r in rows
    ]
