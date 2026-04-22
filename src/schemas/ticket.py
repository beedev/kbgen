"""Ticket schemas — normalized shape produced by ITSM adapters."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationEntry(BaseModel):
    author: str
    timestamp: datetime | None = None
    body: str


class Ticket(BaseModel):
    itsm_ticket_id: str
    itsm_provider: str
    title: str
    description: str = ""
    conversation: list[ConversationEntry] = Field(default_factory=list)
    resolution: str = ""
    topic: str | None = None
    tags: list[str] = Field(default_factory=list)
    resolved_at: datetime | None = None

    def to_index_text(self) -> str:
        """Text blob used for dedup embedding."""
        parts = [self.title]
        if self.description:
            parts.append(self.description)
        if self.resolution:
            parts.append(self.resolution)
        return "\n\n".join(parts)
