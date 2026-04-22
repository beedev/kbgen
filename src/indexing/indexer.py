"""Indexer — re-chunk an article, embed changed chunks, upsert kb.chunk rows.

`content_hash` lets us skip embedding for chunks whose text is unchanged, which
matters when approved drafts are edited and re-pushed.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.indexing.chunker import chunk_article
from src.llm.embeddings import embed_many
from src.storage.models import Chunk


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def index_article(
    db: AsyncSession,
    *,
    article_id: UUID,
    title: str,
    body: str,
) -> int:
    """Index (or re-index) a single article. Returns the number of chunks written.

    Strategy (simple + correct for MVP1):
      * Re-chunk deterministically from current title+body.
      * Compare hashes to existing chunks for this article; reuse the embedding
        where the hash matches, re-embed otherwise.
      * Replace the article's chunk set atomically.
    """
    s = get_settings()
    new_chunks = chunk_article(title, body, chunk_size=s.chunk_size_tokens, overlap=s.chunk_overlap)

    existing = (
        await db.execute(select(Chunk).where(Chunk.article_id == article_id))
    ).scalars().all()
    existing_by_hash = {c.content_hash: c for c in existing}

    # Embed only the chunks whose text changed (or all, if none existed).
    to_embed: list[tuple[int, str]] = []
    hashes: list[str] = []
    for c in new_chunks:
        h = _hash(c.content)
        hashes.append(h)
        if h not in existing_by_hash:
            to_embed.append((c.index, c.content))

    fresh_vectors: dict[int, list[float]] = {}
    if to_embed:
        vecs = await embed_many([t for _, t in to_embed])
        for (idx, _), v in zip(to_embed, vecs):
            fresh_vectors[idx] = v

    # Wipe + rewrite the chunk set. Cheap for MVP1-sized corpora.
    await db.execute(delete(Chunk).where(Chunk.article_id == article_id))
    for c, h in zip(new_chunks, hashes):
        embedding = (
            fresh_vectors.get(c.index)
            if c.index in fresh_vectors
            else existing_by_hash[h].embedding
        )
        db.add(
            Chunk(
                article_id=article_id,
                chunk_index=c.index,
                content=c.content,
                token_count=c.token_count,
                embedding=embedding,
                content_hash=h,
            )
        )
    await db.commit()
    return len(new_chunks)
