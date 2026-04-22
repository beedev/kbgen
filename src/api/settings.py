"""/settings — GET + PATCH for the single settings row."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.itsm import get_adapter
from src.schemas.api import SettingsUpdate
from src.storage.db import get_session
from src.storage.models import KbSettings

router = APIRouter()


@router.get("/settings")
async def get_settings_row(db: AsyncSession = Depends(get_session)) -> dict:
    row = (await db.execute(select(KbSettings).where(KbSettings.id == 1))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=500, detail="settings row missing — re-run migrations")
    return {
        "poll_interval_s": row.poll_interval_s,
        "openai_model": row.openai_model,
        "embedding_model": row.embedding_model,
        "chunk_size_tokens": row.chunk_size_tokens,
        "chunk_overlap": row.chunk_overlap,
        "confidence_threshold": float(row.confidence_threshold),
        "score_weights": row.score_weights,
        "itsm_adapter": row.itsm_adapter,
        "itsm_config": row.itsm_config,
        "dedup_threshold": float(row.dedup_threshold),
        "updated_at": row.updated_at,
    }


@router.patch("/settings")
async def update_settings(update: SettingsUpdate, db: AsyncSession = Depends(get_session)) -> dict:
    row = (await db.execute(select(KbSettings).where(KbSettings.id == 1))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=500, detail="settings row missing")
    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    return {"updated": list(data.keys())}


@router.post("/settings/test-connection")
async def test_connection(adapter: str | None = None) -> dict:
    a = get_adapter(adapter)
    ok, msg = await a.test_connection()
    return {"adapter": a.name, "ok": ok, "message": msg}
