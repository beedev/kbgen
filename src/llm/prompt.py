"""Versioned prompt templates for article generation."""

from __future__ import annotations

from src.schemas.ticket import Ticket

PROMPT_VERSION = "v1"

_SYSTEM = (
    "You convert resolved IT support tickets into concise, reusable knowledge-base articles. "
    "Audience: agents and end-users who will search for answers by intent. Tone: direct, "
    "instructive, no filler. Never invent facts not present in the ticket. If a step is "
    "uncertain, omit it rather than guess. Return only the structured JSON the caller requested."
)


def build_system_prompt() -> str:
    return _SYSTEM


def build_user_prompt(ticket: Ticket) -> str:
    conv_lines = [f"[{e.author}] {e.body}" for e in ticket.conversation]
    conv_block = "\n".join(conv_lines) if conv_lines else "(none)"
    return (
        f"# Source Ticket\n"
        f"ID: {ticket.itsm_ticket_id}\n"
        f"Provider: {ticket.itsm_provider}\n"
        f"Title: {ticket.title}\n"
        f"Topic/Category: {ticket.topic or 'unspecified'}\n"
        f"Tags: {', '.join(ticket.tags) if ticket.tags else '(none)'}\n\n"
        f"## Description\n{ticket.description or '(none)'}\n\n"
        f"## Conversation\n{conv_block}\n\n"
        f"## Resolution Notes (authoritative — the article must be grounded in these)\n"
        f"{ticket.resolution or '(none)'}\n\n"
        "Write a KB article from this ticket. Steps must be numbered Markdown. "
        "Confidence should reflect how strong the resolution evidence is (thin notes → low "
        "confidence; detailed, verified steps → high)."
    )
