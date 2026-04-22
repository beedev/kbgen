"""GLPI adapter smoke tests using pytest-httpx to stub the REST surface.

Covers: session lifecycle, list_resolved_tickets filter (only status 5/6),
KB listing, and create_kb_draft.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from src.itsm.glpi import GLPIAdapter


BASE = "http://test-glpi/apirest.php"


def _make() -> GLPIAdapter:
    return GLPIAdapter(base_url=BASE, basic_user="u", basic_password="p")


@pytest.mark.anyio
@pytest.mark.asyncio
async def test_test_connection_happy(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE}/initSession", json={"session_token": "abc"})
    httpx_mock.add_response(url=f"{BASE}/killSession", json=True)
    ok, _msg = await _make().test_connection()
    assert ok


@pytest.mark.asyncio
async def test_list_resolved_filters_non_closed(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE}/initSession", json={"session_token": "t"})
    # Mix: 1=new, 5=solved, 6=closed — only the last two should come through.
    tickets = [
        {"id": 1, "name": "new one", "status": 1, "content": "", "solvedate": None, "closedate": None},
        {"id": 2, "name": "solved", "status": 5, "content": "x", "solvedate": "2026-04-22 10:00:00", "closedate": None},
        {"id": 3, "name": "closed", "status": 6, "content": "y", "solvedate": "2026-04-21 09:00:00", "closedate": "2026-04-21 10:00:00"},
    ]
    import re
    httpx_mock.add_response(url=re.compile(rf"^{re.escape(BASE)}/Ticket\?.*"), json=tickets)
    # Solution + followup empty for both resolved tickets.
    for ticket_id in (2, 3):
        httpx_mock.add_response(url=f"{BASE}/Ticket/{ticket_id}/ITILSolution", json=[])
        httpx_mock.add_response(url=f"{BASE}/Ticket/{ticket_id}/ITILFollowup", json=[])
    httpx_mock.add_response(url=f"{BASE}/killSession", json=True)

    out = await _make().list_resolved_tickets()
    assert [t.itsm_ticket_id for t in out] == ["2", "3"]


@pytest.mark.asyncio
async def test_create_kb_draft_returns_id(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=f"{BASE}/initSession", json={"session_token": "t"})
    httpx_mock.add_response(
        url=f"{BASE}/KnowbaseItem", method="POST", json={"id": 42, "message": "ok"}
    )
    httpx_mock.add_response(url=f"{BASE}/killSession", json=True)

    kb_id = await _make().create_kb_draft(title="t", body="b")
    assert kb_id == "42"
