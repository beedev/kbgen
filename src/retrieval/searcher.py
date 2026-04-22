"""Semantic search over kb.chunk via pgvector cosine distance."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.embeddings import embed_one
from src.schemas.api import SearchHit, SearchResponse


async def semantic_search(
    db: AsyncSession,
    *,
    query: str,
    category: str | None = None,
    limit: int = 10,
) -> SearchResponse:
    if not query.strip():
        return SearchResponse(hits=[], query=query, total=0)

    vec = await embed_one(query)
    vec_literal = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"

    # End-user semantic search (the /ask + /search UIs) only wants published or
    # approved content. Internal dedup wants to match against drafts too — see
    # `semantic_search_for_dedup` below.
    where = "WHERE a.status IN ('PUSHED','IMPORTED','APPROVED')"
    params: dict = {"limit": limit}
    if category:
        where += " AND a.category = :category"
        params["category"] = category

    # For each matching chunk, compute relevance = 1 - cosine_distance, then
    # pick each article's best chunk (DISTINCT ON) and order by score.
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


async def semantic_search_for_dedup(
    db: AsyncSession,
    *,
    query: str,
    limit: int = 3,
) -> SearchResponse:
    """Broader search used by the dedup step — includes DRAFT + EDITED too.

    The key insight: if ticket #1 already produced a pending draft that
    matches ticket #2's content, ticket #2 is COVERED by that draft. One KB
    should serve many tickets.
    """
    if not query.strip():
        return SearchResponse(hits=[], query=query, total=0)

    vec = await embed_one(query)
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
