"""Admin endpoints — destructive operations live here, guarded by an explicit
`confirm=yes` query param to prevent accidental curls in a shared environment.

Currently exposes a single operation: `/admin/reset` — wipes kbgen's own
operational state (`kb.processed_ticket`, `kb.article`, `kb.chunk`,
`kb.push_log`, `kb.topic_snapshot`) so the service can be re-seeded from a
clean GLPI. Does NOT touch the `entities` table or any other service's data.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.db import get_session
from src.storage.models import Article, Chunk, ProcessedTicket, PushLog, TopicSnapshot

router = APIRouter()


@router.post("/admin/reset")
async def reset_state(
    confirm: str = "",
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Wipe every row from kbgen's operational tables.

    Guard: pass `?confirm=yes`. Without it the call refuses. Intentionally
    low-ceremony — this is a dev/demo reset, not a production feature.

    Order matters: chunks and processed_ticket have FKs into article, so they
    must go first.
    """
    if confirm != "yes":
        raise HTTPException(
            status_code=400,
            detail="Refusing to reset without explicit confirmation. Add `?confirm=yes`.",
        )

    counts: dict[str, int] = {}

    async def _wipe(model, key: str) -> None:
        result = await db.execute(delete(model))
        counts[key] = result.rowcount or 0

    await _wipe(Chunk, "chunks")
    await _wipe(PushLog, "push_log")
    await _wipe(ProcessedTicket, "processed_tickets")
    await _wipe(Article, "articles")
    await _wipe(TopicSnapshot, "topic_snapshots")
    await db.commit()

    return {"reset": True, "deleted": counts}
