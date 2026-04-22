"""Drive the full GLPI → kbgen → pgvector pipeline in one shot.

Steps:
  1. Import existing GLPI KB articles → index them into pgvector.
  2. Run a poll cycle over GLPI resolved tickets → dedup + draft + score.
  3. Dump summary stats + a topic breakdown so we can verify the demo setup.

Env: reads kbgen/.env (ITSM_ADAPTER=glpi etc.).
"""

from __future__ import annotations

import asyncio
from collections import Counter

from sqlalchemy import select

from src.pipeline.generate import run_cycle
from src.pipeline.importer import import_from_itsm
from src.storage.db import SessionLocal, engine
from src.storage.models import Article, ProcessedTicket


async def main() -> None:
    async with SessionLocal() as db:
        print("importing GLPI KB…")
        imp = await import_from_itsm(db)
        print(f"  imported {imp.imported} articles, {imp.indexed_chunks} chunks")

        print("\nrunning poll cycle over GLPI tickets…")
        result = await run_cycle(db)
        print(f"  processed={result.processed} drafted={result.drafted} covered={result.covered} skipped={result.skipped} errors={len(result.errors)}")
        if result.errors:
            for e in result.errors[:5]:
                print(f"  ! {e}")

        # Decision breakdown.
        rows = (await db.execute(select(ProcessedTicket.decision, ProcessedTicket.itsm_provider))).all()
        bd: Counter = Counter()
        for decision, provider in rows:
            bd[f"{provider}:{decision}"] += 1
        print(f"\nprocessed_ticket decisions: {dict(bd)}")

        # Article distribution.
        arows = (await db.execute(select(Article.source, Article.status))).all()
        asrc: Counter = Counter()
        for s, st in arows:
            asrc[f"{s}:{st}"] += 1
        print(f"article breakdown:          {dict(asrc)}")

        # Topic status via the /topics logic, inlined for visibility.
        pt_rows = (
            await db.execute(
                select(ProcessedTicket.topic)
                .where(ProcessedTicket.itsm_provider == "glpi")
                .where(ProcessedTicket.topic.is_not(None))
            )
        ).all()
        topics = Counter(t for (t,) in pt_rows)
        a_rows = (
            await db.execute(
                select(Article.category, Article.status).where(Article.category.is_not(None))
            )
        ).all()
        pub = {c for (c, st) in a_rows if st in ("PUSHED", "IMPORTED", "APPROVED")}
        drafted = {c for (c, st) in a_rows if st in ("DRAFT", "EDITED")}
        print(f"\ntopics (top 10 by ticket count):")
        for topic, cnt in topics.most_common(10):
            status = "covered" if topic in pub else "draft-pending" if topic in drafted else "gap"
            print(f"  {cnt:3d}  [{status:13}] {topic}")
        print(f"\ntotal distinct GLPI topics: {len(topics)} | gap: {sum(1 for t in topics if t not in pub and t not in drafted)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
