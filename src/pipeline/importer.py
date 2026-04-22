"""Import existing KB articles from the active ITSM and index them into pgvector."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.indexing.indexer import index_article
from src.itsm import get_adapter
from src.schemas.api import ImportResult
from src.storage import articles as articles_dal

log = logging.getLogger(__name__)


async def import_from_itsm(db: AsyncSession) -> ImportResult:
    adapter = get_adapter()
    try:
        kb_articles = await adapter.list_kb_articles()
    except NotImplementedError:
        log.warning("adapter %s has no list_kb_articles yet", adapter.name)
        return ImportResult(imported=0, indexed_chunks=0)

    imported = 0
    indexed = 0
    for a in kb_articles:
        row = await articles_dal.upsert_imported(
            db,
            itsm_provider=adapter.name,
            itsm_kb_id=a.itsm_kb_id,
            title=a.title,
            body=a.body,
            category=a.category,
            tags=a.tags,
        )
        imported += 1
        indexed += await index_article(db, article_id=row.id, title=row.title, body=row.steps_md or "")
    return ImportResult(imported=imported, indexed_chunks=indexed)
