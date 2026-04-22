"""APScheduler wiring — poll cycle runs on an interval.

P0 registers the job infrastructure; the job body is filled in P2 (pipeline.generate).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import get_settings

log = logging.getLogger(__name__)


async def _poll_job() -> None:
    """One poll cycle. Runs the full pipeline against the active ITSM adapter."""
    from src.pipeline.generate import run_cycle
    from src.storage.db import SessionLocal

    async with SessionLocal() as db:
        result = await run_cycle(db)
    log.info(
        "kbgen poll tick: processed=%d drafted=%d covered=%d skipped=%d errors=%d",
        result.processed,
        result.drafted,
        result.covered,
        result.skipped,
        len(result.errors),
    )


def start_scheduler() -> AsyncIOScheduler:
    s = get_settings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _poll_job,
        trigger=IntervalTrigger(seconds=s.poll_interval_s),
        id="kbgen-poll",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    log.info("kbgen scheduler started — poll every %ss", s.poll_interval_s)
    return scheduler


def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("kbgen scheduler stopped")
