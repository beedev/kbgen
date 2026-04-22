"""/health — liveness plus shallow pings to DB, ITSM, and OpenAI."""

from fastapi import APIRouter
from sqlalchemy import text

from src.config import get_settings
from src.itsm import get_adapter
from src.schemas.api import HealthResponse
from src.storage.db import engine

router = APIRouter()


async def _ping_db() -> str:
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar_one()
            # Check the kb schema exists too — gives a single-shot sanity signal.
            await conn.execute(text("SELECT to_regnamespace('kb')"))
        return "ok"
    except Exception as exc:  # pragma: no cover — surfaced in response
        return f"error: {exc.__class__.__name__}"


async def _ping_itsm() -> str:
    try:
        adapter = get_adapter()
        ok, msg = await adapter.test_connection()
        return "ok" if ok else f"degraded: {msg}"
    except Exception as exc:
        return f"error: {exc.__class__.__name__}"


async def _ping_openai() -> str:
    s = get_settings()
    if not s.openai_api_key:
        return "unconfigured"
    # Lazy import so boot doesn't require the key to be set.
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=s.openai_api_key)
        # Lightest check available — list a single model with a tiny page.
        await client.models.list()
        return "ok"
    except Exception as exc:
        return f"error: {exc.__class__.__name__}"


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db = await _ping_db()
    itsm = await _ping_itsm()
    openai = await _ping_openai()
    overall = "ok" if db == "ok" else "degraded"
    return HealthResponse(status=overall, db=db, itsm=itsm, openai=openai)
