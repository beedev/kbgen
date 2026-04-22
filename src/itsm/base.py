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

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Return (ok, human-readable status)."""
