"""DAL for kb.article — used by pipeline, importer, and API."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import Article


async def get(db: AsyncSession, article_id: UUID) -> Article | None:
    return (await db.execute(select(Article).where(Article.id == article_id))).scalar_one_or_none()


async def get_by_itsm_kb_id(db: AsyncSession, itsm_kb_id: str) -> Article | None:
    return (
        await db.execute(select(Article).where(Article.itsm_kb_id == itsm_kb_id))
    ).scalar_one_or_none()


async def create(db: AsyncSession, **fields) -> Article:
    row = Article(**fields)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def upsert_imported(
    db: AsyncSession,
    *,
    itsm_provider: str,
    itsm_kb_id: str,
    title: str,
    body: str,
    category: str | None,
    tags: list[str],
) -> Article:
    """Create an IMPORTED article or update it if the KB id already exists."""
    existing = await get_by_itsm_kb_id(db, itsm_kb_id)
    if existing:
        existing.title = title
        existing.summary = title
        existing.steps_md = body
        existing.category = category
        existing.tags = tags
        await db.commit()
        await db.refresh(existing)
        return existing
    row = Article(
        itsm_provider=itsm_provider,
        itsm_kb_id=itsm_kb_id,
        title=title,
        summary=title,
        steps_md=body,
        tags=tags,
        category=category,
        status="IMPORTED",
        source="imported_from_itsm",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
