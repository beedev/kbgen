"""First-boot bootstrap — runs once before the scheduler starts.

Idempotent. If AUTO_SEED_ITSM is true AND the active ITSM adapter is `glpi`
AND GLPI has no tickets yet, seed 135 healthcare tickets + 4 KB articles
via the ITSM API. Second boot is a no-op.

Used by the single-container demo compose — the shipped GLPI image is
pre-installed but empty, and this populates it with realistic data so the
UI shows something interesting on first browse.
"""

from __future__ import annotations

import asyncio
import logging

from src.config import get_settings
from src.itsm import get_adapter
from src.itsm.glpi import GLPIAdapter

log = logging.getLogger(__name__)


async def _seed_glpi_inline(adapter: GLPIAdapter) -> None:
    """Run the healthcare seeder as an in-process routine (no subprocess)."""
    # The seeder script is structured as an async main() that connects via its
    # own httpx client. We import and call it directly — credentials come from
    # the active adapter so a single ADAPTER env controls both targets.
    import importlib
    import sys
    from pathlib import Path

    seeder_path = Path(__file__).resolve().parent.parent / "scripts"
    if str(seeder_path) not in sys.path:
        sys.path.insert(0, str(seeder_path))
    seeder = importlib.import_module("seed_glpi_healthcare")

    # Point the seeder at the same GLPI the adapter uses. The seeder hard-codes
    # http://localhost:9080 but the compose sets that correctly from kbgen's
    # perspective via the service-internal alias — here we override to match
    # whatever the adapter is configured with.
    seeder.BASE = adapter.base_url
    await seeder.main(purge=False)


async def run_bootstrap() -> dict:
    """Returns a small status dict — logged at startup, also useful for tests."""
    s = get_settings()
    if not s.auto_seed_itsm:
        return {"skipped": "AUTO_SEED_ITSM not set"}

    adapter = get_adapter()
    if not isinstance(adapter, GLPIAdapter):
        return {"skipped": f"adapter is {adapter.name}, not glpi"}

    try:
        existing = await adapter.list_resolved_tickets()
    except Exception as exc:
        log.warning("bootstrap: GLPI not reachable for inventory — %s", exc)
        return {"error": str(exc)}

    if existing:
        return {"skipped": f"GLPI already has {len(existing)} tickets"}

    log.info("bootstrap: GLPI is empty, seeding healthcare fixtures…")
    try:
        await _seed_glpi_inline(adapter)
    except Exception as exc:
        log.exception("bootstrap: seed failed")
        return {"error": str(exc)}

    try:
        post = await adapter.list_resolved_tickets()
        return {"seeded": len(post)}
    except Exception:
        return {"seeded": "unknown", "note": "GLPI responded during seed but inventory reread failed"}


def schedule_bootstrap() -> None:
    """Fire-and-forget bootstrap so lifespan doesn't block FastAPI startup."""
    loop = asyncio.get_event_loop()

    async def _run():
        result = await run_bootstrap()
        log.info("bootstrap result: %s", result)

    loop.create_task(_run())
