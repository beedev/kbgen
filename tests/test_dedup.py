"""Dedup policy — unit-level test of the threshold logic without hitting the DB.

We stub the searcher via monkeypatch so we isolate the decision branch from
pgvector / Postgres.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.pipeline import dedup
from src.schemas.api import SearchHit, SearchResponse
from src.schemas.ticket import Ticket


class _StubSession:
    pass


@pytest.mark.asyncio
async def test_above_threshold_marks_covered(monkeypatch):
    hit_id = str(uuid4())

    async def fake_search(_session, *, query, limit):
        return SearchResponse(
            hits=[
                SearchHit(
                    article_id=hit_id,
                    chunk_id=str(uuid4()),
                    title="existing",
                    category=None,
                    preview="…",
                    relevance=0.9,
                    source_ticket_id=None,
                    itsm_kb_id=None,
                )
            ],
            query=query,
            total=1,
        )

    monkeypatch.setattr(dedup, "semantic_search", fake_search)

    t = Ticket(itsm_ticket_id="1", itsm_provider="x", title="reset vpn")
    result = await dedup.check_duplicate(_StubSession(), t, threshold=0.82)
    assert result.covered is True
    assert str(result.matched_article_id) == hit_id


@pytest.mark.asyncio
async def test_below_threshold_is_novel(monkeypatch):
    async def fake_search(_session, *, query, limit):
        return SearchResponse(
            hits=[
                SearchHit(
                    article_id=str(uuid4()),
                    chunk_id=str(uuid4()),
                    title="weakly related",
                    category=None,
                    preview="…",
                    relevance=0.4,
                    source_ticket_id=None,
                    itsm_kb_id=None,
                )
            ],
            query=query,
            total=1,
        )

    monkeypatch.setattr(dedup, "semantic_search", fake_search)

    t = Ticket(itsm_ticket_id="2", itsm_provider="x", title="something novel")
    result = await dedup.check_duplicate(_StubSession(), t, threshold=0.82)
    assert result.covered is False
    assert result.matched_relevance == 0.4


@pytest.mark.asyncio
async def test_empty_index_is_novel(monkeypatch):
    async def fake_search(_session, *, query, limit):
        return SearchResponse(hits=[], query=query, total=0)

    monkeypatch.setattr(dedup, "semantic_search", fake_search)

    t = Ticket(itsm_ticket_id="3", itsm_provider="x", title="anything")
    result = await dedup.check_duplicate(_StubSession(), t, threshold=0.82)
    assert result.covered is False
    assert result.matched_article_id is None
