"""ITSMAdapter — the contract every ITSM integration implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.ticket import Ticket


class ItsmKbArticle(BaseModel):
    """KB article shape returned by an ITSM (read-side)."""

    itsm_kb_id: str
    title: str
    body: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KbSearchResult(BaseModel):
    itsm_kb_id: str
    title: str
    snippet: str
    score: float | None = None


class ITSMAdapter(ABC):
    """All ITSM integrations (GLPI, ServiceNow, Zendesk, mock) implement this."""

    name: str

    @abstractmethod
    async def list_resolved_tickets(self, since: datetime | None = None) -> list[Ticket]:
        ...

    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Ticket | None:
        ...

    @abstractmethod
    async def search_kb(self, query: str, limit: int = 5) -> list[KbSearchResult]:
        """Native ITSM KB search — secondary signal; primary dedup is pgvector."""

    @abstractmethod
    async def list_kb_articles(self, since: datetime | None = None) -> list[ItsmKbArticle]:
        ...

    @abstractmethod
    async def create_kb_draft(
        self,
        *,
        title: str,
        body: str,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Push a new KB draft. Returns the ITSM's KB id."""

    async def link_kb_to_ticket(self, *, itsm_kb_id: str, itsm_ticket_id: str) -> bool:
        """Associate a KB article with a ticket so the ticket's KB tab lists it.

        Default is a no-op (returns False) — adapters that can't express this
        association silently skip. GLPI overrides to POST a KnowbaseItem_Item
        row. Non-fatal: push flow logs but does not fail if this throws.
        """
        return False

    async def create_resolved_ticket(
        self,
        *,
        title: str,
        description: str,
        resolution: str,
        category: str | None = None,
    ) -> str | None:
        """Create a new ticket in a 'resolved' state for demo seeding.

        Default returns None — adapters that can't synthesize tickets skip.
        The intent is to drop a fresh ticket + resolution into the ITSM so
        the kbgen pipeline picks it up on the next poll. Returns the ITSM
        ticket id on success.
        """
        return None

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Return (ok, human-readable status)."""
