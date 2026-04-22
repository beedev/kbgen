"""Semantic search over kb.chunk (KB articles) + kb.processed_ticket (tickets).

`/search` returns a unified ranked list across both corpora, with each hit
tagged `object_kind` so the UI can render KB chunks and tickets distinctly.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.embeddings import embed_one
from src.schemas.api import SearchHit, SearchResponse


async def _search_articles(
    db: AsyncSession,
    *,
    vec_literal: str,
    category: str | None,
    limit: int,
) -> list[SearchHit]:
    """KB-chunk search (the original /search behaviour). Filtered to
    published/approved content — internal dedup uses a separate helper."""
    where = "WHERE a.status IN ('PUSHED','IMPORTED','APPROVED')"
    params: dict = {"limit": limit}
    if category:
        where += " AND a.category = :category"
        params["category"] = category

    sql = text(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (c.article_id)
                c.id        AS chunk_id,
                c.article_id,
                c.content   AS preview,
                1 - (c.embedding <=> '{vec_literal}'::vector) AS relevance,
                a.title, a.category, a.source_ticket_id, a.itsm_kb_id
            FROM kb.chunk c
            JOIN kb.article a ON a.id = c.article_id
            {where}
            ORDER BY c.article_id, c.embedding <=> '{vec_literal}'::vector
        ) t
        ORDER BY t.relevance DESC
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, params)).mappings().all()
    return [
        SearchHit(
            object_kind="kb",
            article_id=str(r["article_id"]),
            chunk_id=str(r["chunk_id"]),
            itsm_kb_id=r["itsm_kb_id"],
            title=r["title"],
            category=r["category"],
            preview=_snip(r["preview"]),
            relevance=float(r["relevance"]),
            source_ticket_id=r["source_ticket_id"],
        )
        for r in rows
    ]


async def _search_tickets(
    db: AsyncSession,
    *,
    vec_literal: str,
    category: str | None,
    limit: int,
) -> list[SearchHit]:
    """Ticket search over kb.processed_ticket.embedding. Preview text is built
    from the ticket's description/resolution since tickets aren't chunked.
    """
    where = "WHERE pt.embedding IS NOT NULL"
    params: dict = {"limit": limit}
    if category:
        where += " AND pt.topic = :category"
        params["category"] = category

    sql = text(
        f"""
        SELECT
            pt.itsm_ticket_id,
            pt.title,
            pt.topic,
            pt.decision,
            COALESCE(NULLIF(pt.description, ''), NULLIF(pt.resolution, ''), pt.title)
                                                AS preview,
            1 - (pt.embedding <=> '{vec_literal}'::vector) AS relevance
        FROM kb.processed_ticket pt
        {where}
        ORDER BY pt.embedding <=> '{vec_literal}'::vector
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, params)).mappings().all()
    return [
        SearchHit(
            object_kind="ticket",
            itsm_ticket_id=r["itsm_ticket_id"],
            topic=r["topic"],
            decision=r["decision"],
            title=r["title"],
            category=r["topic"],
            preview=_snip(r["preview"]),
            relevance=float(r["relevance"]),
        )
        for r in rows
    ]


async def semantic_search(
    db: AsyncSession,
    *,
    query: str,
    category: str | None = None,
    kind: str | None = None,           # "kb" | "ticket" | None (both)
    limit: int = 10,
) -> SearchResponse:
    """Unified semantic search over KB chunks + tickets.

    Embeds `query` once, runs both pgvector lookups in parallel topology, then
    merges and re-sorts by relevance, trimming to `limit`. `kind` narrows to
    one corpus when the caller only wants one. `category` applies across both:
    article.category for KB hits and processed_ticket.topic for tickets.
    """
    if not query.strip():
        return SearchResponse(hits=[], query=query, total=0)

    vec = await embed_one(query)
    vec_literal = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"

    # Overshoot each corpus so the merged top-N includes the genuinely best
    # cross-corpus hits — otherwise a corpus with many high-scoring items
    # could crowd out a single stronger hit from the other one.
    per_source = max(limit, 10)

    hits: list[SearchHit] = []
    if kind != "ticket":
        hits.extend(
            await _search_articles(
                db, vec_literal=vec_literal, category=category, limit=per_source
            )
        )
    if kind != "kb":
        hits.extend(
            await _search_tickets(
                db, vec_literal=vec_literal, category=category, limit=per_source
            )
        )

    hits.sort(key=lambda h: h.relevance, reverse=True)
    hits = hits[:limit]
    return SearchResponse(hits=hits, query=query, total=len(hits))


async def semantic_search_for_dedup(
    db: AsyncSession,
    *,
    query: str,
    limit: int = 3,
    query_vec: list[float] | None = None,
) -> SearchResponse:
    """Broader search used by the dedup step — includes DRAFT + EDITED too.

    The key insight: if ticket #1 already produced a pending draft that
    matches ticket #2's content, ticket #2 is COVERED by that draft. One KB
    should serve many tickets.

    `query_vec` short-circuits the embedding call when the caller already has
    a vector for `query` (e.g. the poll cycle embeds each ticket once for
    storage and can hand the same vector here to skip a round-trip).
    """
    if not query.strip():
        return SearchResponse(hits=[], query=query, total=0)

    vec = query_vec if query_vec is not None else await embed_one(query)
    vec_literal = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"

    sql = text(
        f"""
        SELECT * FROM (
            SELECT DISTINCT ON (c.article_id)
                c.id        AS chunk_id,
                c.article_id,
                c.content   AS preview,
                1 - (c.embedding <=> '{vec_literal}'::vector) AS relevance,
                a.title, a.category, a.source_ticket_id, a.itsm_kb_id, a.status
            FROM kb.chunk c
            JOIN kb.article a ON a.id = c.article_id
            WHERE a.status IN ('PUSHED','IMPORTED','APPROVED','DRAFT','EDITED')
            ORDER BY c.article_id, c.embedding <=> '{vec_literal}'::vector
        ) t
        ORDER BY t.relevance DESC
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, {"limit": limit})).mappings().all()
    hits = [
        SearchHit(
            article_id=str(r["article_id"]),
            chunk_id=str(r["chunk_id"]),
            title=r["title"],
            category=r["category"],
            preview=_snip(r["preview"]),
            relevance=float(r["relevance"]),
            source_ticket_id=r["source_ticket_id"],
            itsm_kb_id=r["itsm_kb_id"],
        )
        for r in rows
    ]
    return SearchResponse(hits=hits, query=query, total=len(hits))


def _snip(text_: str, max_len: int = 240) -> str:
    t = text_.strip().replace("\n", " ")
    return t if len(t) <= max_len else t[: max_len - 1].rstrip() + "…"
