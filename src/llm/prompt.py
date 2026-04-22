"""Versioned prompt templates for article generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.schemas.ticket import Ticket

if TYPE_CHECKING:
    from src.retrieval.neighbours import NeighbourContext

PROMPT_VERSION = "v1"
GAP_RAG_PROMPT_VERSION = "v1-gap-rag"

_SYSTEM = (
    "You convert resolved IT support tickets into concise, reusable knowledge-base articles. "
    "Audience: agents and end-users who will search for answers by intent. Tone: direct, "
    "instructive, no filler. Never invent facts not present in the ticket. If a step is "
    "uncertain, omit it rather than guess. Return only the structured JSON the caller requested."
)

_SYSTEM_GAP_RAG = (
    _SYSTEM
    + " You are drafting a KB for a ticket whose own resolution notes are missing or too thin. "
    "Ground every step in the neighbour tickets and articles provided below. Do NOT introduce "
    "facts, product names, commands, or steps that are not supported by at least one neighbour. "
    "If the neighbours do not converge on a clear resolution applicable to the target's problem, "
    "return confidence ≤ 0.3 and keep steps_md short and qualified."
)


def build_system_prompt() -> str:
    return _SYSTEM


def build_gap_rag_system_prompt() -> str:
    return _SYSTEM_GAP_RAG


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


def build_gap_rag_user_prompt(
    ticket: Ticket, neighbours: "list[NeighbourContext]"
) -> str:
    conv_lines = [f"[{e.author}] {e.body}" for e in ticket.conversation]
    conv_block = "\n".join(conv_lines) if conv_lines else "(none)"

    parts: list[str] = []
    parts.append(
        "# Target Ticket (resolution missing — needs drafting from neighbours)\n"
        f"ID: {ticket.itsm_ticket_id}\n"
        f"Provider: {ticket.itsm_provider}\n"
        f"Title: {ticket.title}\n"
        f"Topic/Category: {ticket.topic or 'unspecified'}\n"
        f"Tags: {', '.join(ticket.tags) if ticket.tags else '(none)'}\n\n"
        f"## Description\n{ticket.description or '(none)'}\n\n"
        f"## Conversation\n{conv_block}\n"
    )

    parts.append("\n# Neighbour Articles (ranked by semantic similarity)")
    for i, n in enumerate(neighbours, start=1):
        cat = f" ({n.category})" if n.category else ""
        block = (
            f"\n## Neighbour {i} — relevance {n.relevance:.2f} — KB \"{n.title}\"{cat}\n"
            f"### Distilled steps\n{n.steps_md or '(empty)'}\n"
        )
        if n.source_ticket_id:
            block += (
                "### Source ticket (raw)\n"
                f"Title: {n.source_ticket_title or '(unknown)'}\n"
                f"Description: {n.source_ticket_description or '(none)'}\n"
                f"Resolution Notes: {n.source_ticket_resolution or '(none)'}\n"
            )
        parts.append(block)

    parts.append(
        "\n# Instructions\n"
        "Draft a KB article for the target ticket, grounded only in the neighbour "
        "evidence above. Steps must be numbered Markdown. Confidence reflects how "
        "strongly the neighbours converge on a resolution pattern applicable to the "
        "target's problem."
    )
    return "\n".join(parts)
