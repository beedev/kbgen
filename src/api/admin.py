"""Admin endpoints — destructive operations live here, guarded by an explicit
`confirm=yes` query param to prevent accidental curls in a shared environment.

Currently exposes a single operation: `/admin/reset` — wipes kbgen's own
operational state (`kb.processed_ticket`, `kb.article`, `kb.chunk`,
`kb.push_log`, `kb.topic_snapshot`) so the service can be re-seeded from a
clean GLPI. Does NOT touch the `entities` table or any other service's data.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.demo.ticket_fixtures import next_pack
from src.itsm import get_adapter
from src.storage.db import get_session
from src.storage.models import Article, Chunk, ProcessedTicket, PushLog, TopicSnapshot

log = logging.getLogger(__name__)

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


@router.post("/admin/relink-kb")
async def relink_kb_to_tickets(db: AsyncSession = Depends(get_session)) -> dict:
    """Backfill ticket↔KB associations in the ITSM for every already-pushed article.

    For each PUSHED article with an itsm_kb_id, link it to:
      * its source ticket (the one whose resolution drafted the article), and
      * every covered sibling (ProcessedTicket.matched_article_id == article.id).

    Idempotent — the adapter treats duplicate associations as success. Useful
    after deploying this feature to retroactively surface KBs in GLPI ticket
    views for articles pushed before the auto-link existed.
    """
    adapter = get_adapter()
    articles = (
        await db.execute(
            select(Article).where(Article.status == "PUSHED", Article.itsm_kb_id.is_not(None))
        )
    ).scalars().all()

    articles_linked = 0
    links_created = 0
    errors: list[str] = []

    for article in articles:
        kb_id = str(article.itsm_kb_id)
        ticket_ids: list[str] = []
        if article.source_ticket_id:
            ticket_ids.append(str(article.source_ticket_id))
        covered = (
            await db.execute(
                select(ProcessedTicket.itsm_ticket_id).where(
                    ProcessedTicket.matched_article_id == article.id
                )
            )
        ).scalars().all()
        for tid in covered:
            if tid and tid not in ticket_ids:
                ticket_ids.append(str(tid))

        any_linked = False
        for tid in ticket_ids:
            try:
                ok = await adapter.link_kb_to_ticket(itsm_kb_id=kb_id, itsm_ticket_id=tid)
                if ok:
                    links_created += 1
                    any_linked = True
            except Exception as exc:
                errors.append(f"kb={kb_id} ticket={tid}: {exc.__class__.__name__}: {exc}")
                log.warning("relink_kb failed kb=%s ticket=%s: %s", kb_id, tid, exc)
        if any_linked:
            articles_linked += 1

    return {
        "articles_processed": len(articles),
        "articles_linked": articles_linked,
        "links_created": links_created,
        "errors": errors[:20],
    }


@router.post("/admin/seed-demo")
async def seed_demo_tickets() -> dict:
    """Drop the next demo fixture pack (10 themed tickets) into the ITSM.

    Rotates through curated packs on each call so successive demos show
    different stories. Every pack mixes:
      * a large themed cluster that will become 1 master draft + N-1 covered
      * a smaller cluster that drafts its own master
      * a couple of near-duplicates of already-live KBs that show up as
        COVERED → KB N in Workspace (no new draft needed)

    Next poll cycle will pick these up and produce drafts; the caller should
    trigger a poll immediately after to keep the demo tight.
    """
    adapter = get_adapter()
    pack = next_pack()

    created_ids: list[str] = []
    errors: list[str] = []
    for t in pack.tickets:
        try:
            tid = await adapter.create_resolved_ticket(
                title=t.title,
                description=t.description,
                resolution=t.resolution,
                category=t.category,
            )
            if tid:
                created_ids.append(tid)
            else:
                errors.append(f"{t.title}: adapter returned no id")
        except Exception as exc:
            errors.append(f"{t.title}: {exc.__class__.__name__}: {exc}")
            log.warning("seed-demo create_resolved_ticket failed: %s", exc)

    return {
        "theme": pack.theme,
        "narrative": pack.narrative,
        "seeded": len(created_ids),
        "requested": len(pack.tickets),
        "ticket_ids": created_ids,
        "errors": errors[:20],
    }
