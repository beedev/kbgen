"""In-memory ITSM — deterministic fixtures for tests and smoke runs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.itsm.base import ITSMAdapter, ItsmKbArticle, KbSearchResult
from src.schemas.ticket import ConversationEntry, Ticket

_NOW = datetime.now(timezone.utc)


def _sample_tickets() -> list[Ticket]:
    return [
        Ticket(
            itsm_ticket_id="MOCK-1001",
            itsm_provider="mock",
            title="VPN client fails to connect after password rotation",
            description="User reports the corporate VPN rejects credentials after the monthly password change.",
            conversation=[
                ConversationEntry(author="user", body="My VPN won't connect after I reset my password."),
                ConversationEntry(author="agent", body="Did you also update the saved credentials on the VPN client?"),
                ConversationEntry(author="user", body="No, that fixed it."),
            ],
            resolution="Cached credentials in the VPN client were stale. Open VPN client → Preferences → Credentials → Clear, then reconnect with the new password.",
            topic="VPN",
            tags=["vpn", "auth"],
            resolved_at=_NOW,
        ),
        Ticket(
            itsm_ticket_id="MOCK-1002",
            itsm_provider="mock",
            title="Email search not returning recent messages",
            description="Outlook search missing messages from the last 48 hours.",
            resolution="Rebuild the local search index: File → Options → Search → Indexing Options → Advanced → Rebuild. Takes ~10 minutes.",
            topic="Email",
            tags=["outlook", "search"],
            resolved_at=_NOW,
        ),
        Ticket(
            itsm_ticket_id="MOCK-1003",
            itsm_provider="mock",
            title="Printer queue stuck with a failed job",
            description="Nothing prints; queue shows one job in error state.",
            resolution="Run `services.msc`, restart 'Print Spooler'. If that fails, delete the oldest file in C:\\Windows\\System32\\spool\\PRINTERS and restart the spooler.",
            topic="Printing",
            tags=["printing", "spooler"],
            resolved_at=_NOW,
        ),
    ]


def _sample_kb() -> list[ItsmKbArticle]:
    return [
        ItsmKbArticle(
            itsm_kb_id="KB-MOCK-9001",
            title="How to reset your corporate password",
            body="1. Visit https://pwreset/. 2. Enter your username. 3. Complete MFA. 4. Choose a new password meeting the complexity rules.",
            category="Accounts",
            tags=["password", "auth"],
            updated_at=_NOW,
        ),
    ]


class MockITSMAdapter(ITSMAdapter):
    name = "mock"

    def __init__(self) -> None:
        self._tickets: list[Ticket] = _sample_tickets()
        self._kb: dict[str, ItsmKbArticle] = {a.itsm_kb_id: a for a in _sample_kb()}

    async def list_resolved_tickets(self, since: datetime | None = None) -> list[Ticket]:
        if since is None:
            return list(self._tickets)
        return [t for t in self._tickets if t.resolved_at and t.resolved_at >= since]

    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        return next((t for t in self._tickets if t.itsm_ticket_id == ticket_id), None)

    async def search_kb(self, query: str, limit: int = 5) -> list[KbSearchResult]:
        q = query.lower()
        hits: list[KbSearchResult] = []
        for a in self._kb.values():
            if q in a.title.lower() or q in a.body.lower():
                hits.append(
                    KbSearchResult(
                        itsm_kb_id=a.itsm_kb_id,
                        title=a.title,
                        snippet=a.body[:200],
                        score=0.5,
                    )
                )
        return hits[:limit]

    async def list_kb_articles(self, since: datetime | None = None) -> list[ItsmKbArticle]:
        return list(self._kb.values())

    async def create_kb_draft(
        self, *, title: str, body: str, category: str | None = None, tags: list[str] | None = None
    ) -> str:
        kb_id = f"KB-MOCK-{uuid.uuid4().hex[:8].upper()}"
        self._kb[kb_id] = ItsmKbArticle(
            itsm_kb_id=kb_id,
            title=title,
            body=body,
            category=category,
            tags=tags or [],
            updated_at=datetime.now(timezone.utc),
        )
        return kb_id

    async def test_connection(self) -> tuple[bool, str]:
        return True, "mock adapter — always healthy"

    async def create_resolved_ticket(
        self,
        *,
        title: str,
        description: str,
        resolution: str,
        category: str | None = None,
    ) -> str | None:
        tid = f"MOCK-{uuid.uuid4().hex[:6].upper()}"
        self._tickets.append(
            Ticket(
                itsm_ticket_id=tid,
                itsm_provider=self.name,
                title=title,
                description=description,
                conversation=[],
                resolution=resolution,
                topic=category,
                tags=[],
                resolved_at=datetime.now(timezone.utc),
            )
        )
        return tid
