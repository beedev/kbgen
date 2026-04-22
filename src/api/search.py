"""/search — semantic search over the indexed KB."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.retrieval.searcher import semantic_search
from src.schemas.api import SearchResponse
from src.storage.db import get_session

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str,
    category: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_session),
) -> SearchResponse:
    return await semantic_search(db, query=q, category=category, limit=limit)
