"""Seed the KB with sample articles and index them into pgvector.

Usage:
    EMBEDDING_BACKEND=fake python scripts/seed_kb.py        # offline
    python scripts/seed_kb.py                               # real OpenAI (if key set)
"""

from __future__ import annotations

import asyncio

from src.indexing.indexer import index_article
from src.retrieval.searcher import semantic_search
from src.storage.db import SessionLocal, engine
from src.storage.models import Article, Chunk
from sqlalchemy import delete


SAMPLES = [
    {
        "title": "How to reset corporate VPN credentials after password rotation",
        "category": "VPN",
        "steps_md": (
            "1. Open the VPN client.\n"
            "2. Go to Preferences → Credentials → Clear saved credentials.\n"
            "3. Reconnect and enter the new password.\n"
            "4. If prompted for MFA, approve the push in the authenticator app.\n"
        ),
    },
    {
        "title": "Rebuilding the Outlook search index when recent mail is missing",
        "category": "Email",
        "steps_md": "File → Options → Search → Indexing Options → Advanced → Rebuild. Takes ~10 minutes.",
    },
    {
        "title": "Clearing a stuck print job from the Windows spooler",
        "category": "Printing",
        "steps_md": "Restart the Print Spooler service; if that fails, delete files in C:\\Windows\\System32\\spool\\PRINTERS and restart the spooler.",
    },
    {
        "title": "Enabling MFA on corporate accounts for the first time",
        "category": "Accounts",
        "steps_md": "Visit https://mfa.corp/, scan the QR code in Microsoft Authenticator, confirm with a test push.",
    },
    {
        "title": "Resetting forgotten Windows login password",
        "category": "Accounts",
        "steps_md": "Use the self-service reset portal at https://pwreset.corp/. Requires verified mobile and security questions.",
    },
    {
        "title": "Configuring the office Wi-Fi on a new laptop",
        "category": "Network",
        "steps_md": "Select 'Corp-WPA2' from the Wi-Fi menu, sign in with your SSO credentials, trust the issued certificate.",
    },
    {
        "title": "Troubleshooting Zoom audio echo during meetings",
        "category": "Collaboration",
        "steps_md": "Enable 'Suppress Background Noise' and disable 'Original Sound' in Zoom audio settings.",
    },
    {
        "title": "Requesting access to a shared network drive",
        "category": "Storage",
        "steps_md": "Submit request through the self-service portal citing the drive letter and justification.",
    },
    {
        "title": "Installing approved software via the corporate portal",
        "category": "Software",
        "steps_md": "Open Company Portal, search for the application, click Install. Wait for success notification.",
    },
    {
        "title": "Updating browser bookmarks after the intranet migration",
        "category": "Web",
        "steps_md": "Old intranet.corp URLs now redirect to new.intranet.corp. Update any bookmarked deep links.",
    },
]


async def main() -> None:
    async with SessionLocal() as db:
        # Wipe previous seed so the script is idempotent.
        await db.execute(delete(Chunk))
        await db.execute(delete(Article).where(Article.source == "imported_from_itsm"))
        await db.commit()

        total_chunks = 0
        for s in SAMPLES:
            row = Article(
                title=s["title"],
                summary=s["title"],
                steps_md=s["steps_md"],
                tags=[],
                category=s["category"],
                status="IMPORTED",
                source="imported_from_itsm",
                itsm_provider="seed",
                itsm_kb_id=f"SEED-{abs(hash(s['title'])) % 10_000:04d}",
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            n = await index_article(
                db, article_id=row.id, title=row.title, body=row.steps_md or ""
            )
            total_chunks += n
        print(f"seeded {len(SAMPLES)} articles, indexed {total_chunks} chunks")

        # Smoke-search for something the first article answers.
        result = await semantic_search(
            db, query="my vpn stopped working after I changed my password", limit=3
        )
        print(f"\ntop hits for 'vpn password' query ({len(result.hits)}):")
        for h in result.hits:
            print(f"  {h.relevance:.3f}  {h.title}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
