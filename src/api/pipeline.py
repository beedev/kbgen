"""Pipeline endpoints: /poll/run, /generate, /import/kb, /export/kb."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.pipeline.generate import generate_for_ticket_id, run_cycle
from src.pipeline.importer import import_from_itsm
from src.schemas.api import ImportResult, PollCycleResult
from src.storage.db import get_session
from src.storage.models import Article

router = APIRouter()


@router.post("/poll/run", response_model=PollCycleResult)
async def run_poll_cycle(db: AsyncSession = Depends(get_session)) -> PollCycleResult:
    return await run_cycle(db)


@router.post("/generate")
async def generate_for_ticket(
    ticket_id: str, db: AsyncSession = Depends(get_session)
) -> dict:
    try:
        return await generate_for_ticket_id(db, ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/import/kb", response_model=ImportResult)
async def import_kb_from_itsm(db: AsyncSession = Depends(get_session)) -> ImportResult:
    return await import_from_itsm(db)


@router.post("/export/kb")
async def export_kb_for_pipeline(
    path: str = "/tmp/kb_articles.json",
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Export published + imported KB articles to a JSON file the
    conversational-assistant's standard data-pipeline can ingest.

    Used by the Admin → Data Pipeline page to hydrate the `entities` table so
    the Agent Readiness dashboard reflects real KB coverage.
    """
    rows = (
        await db.execute(
            select(Article).where(Article.status.in_(["PUSHED", "IMPORTED", "APPROVED"]))
        )
    ).scalars().all()
    payload = [
        {
            "article_id": str(a.id),
            "title": a.title,
            "summary": a.summary or "",
            "steps_md": a.steps_md or "",
            "category": a.category or "",
            "itsm_kb_id": a.itsm_kb_id or "",
            "source_ticket_id": a.source_ticket_id or "",
            "status": a.status,
        }
        for a in rows
    ]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2))
    return {"exported": len(payload), "path": str(target.absolute())}
