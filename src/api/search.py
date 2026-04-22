"""/search — unified semantic search over KB articles + processed tickets."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.searcher import semantic_search
from src.schemas.api import SearchResponse
from src.storage.db import get_session

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    category: str | None = None,
    kind: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_session),
) -> SearchResponse:
    if kind not in (None, "", "kb", "ticket"):
        raise HTTPException(400, "kind must be one of: kb, ticket (omit for both)")
    return await semantic_search(
        db, query=q, category=category, kind=kind or None, limit=limit
    )
