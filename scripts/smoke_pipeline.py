"""End-to-end smoke for P2 — mock ITSM → dedup → generate → score → persist.

Assumes Alembic migrations have been run and scripts/seed_kb.py has been
executed at least once (so the KB is populated + indexed).

    EMBEDDING_BACKEND=fake GEN_BACKEND=fake python scripts/smoke_pipeline.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, select

from src.pipeline.generate import run_cycle
from src.storage.db import SessionLocal, engine
from src.storage.models import Article, ProcessedTicket


async def main() -> None:
    async with SessionLocal() as db:
        # Wipe prior run-state for an idempotent smoke.
        await db.execute(delete(ProcessedTicket))
        await db.execute(delete(Article).where(Article.source == "generated"))
        await db.commit()

        result = await run_cycle(db)
        print("poll result:", result.model_dump())

        drafts = (await db.execute(select(Article).where(Article.source == "generated"))).scalars().all()
        print(f"\ngenerated drafts: {len(drafts)}")
        for a in drafts:
            print(
                f"  [{a.status}] {a.title}"
                f"  conf={a.confidence} overall={a.score_overall}"
            )

        processed = (await db.execute(select(ProcessedTicket))).scalars().all()
        print(f"\nprocessed tickets: {len(processed)}")
        for p in processed:
            print(f"  [{p.decision}] {p.itsm_ticket_id} — {p.decision_reason}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
