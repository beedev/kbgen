"""OpenAI article generator.

Two backends:
  * `openai` — calls `chat.completions` with structured outputs (JSON schema → ArticleDraft).
  * `fake`   — deterministic article derived from ticket text, for offline dev/tests.

Selection mirrors the embeddings client: `GEN_BACKEND` env > implicit (openai if key else fake).
"""

from __future__ import annotations

import json
import logging
import os

from tenacity import retry, stop_after_attempt, wait_exponential

from typing import TYPE_CHECKING

from src.config import get_settings
from src.llm.prompt import (
    GAP_RAG_PROMPT_VERSION,
    PROMPT_VERSION,
    build_gap_rag_system_prompt,
    build_gap_rag_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from src.schemas.article import ArticleDraft
from src.schemas.ticket import Ticket

if TYPE_CHECKING:
    from src.retrieval.neighbours import NeighbourContext

log = logging.getLogger(__name__)


def _resolve_backend() -> str:
    override = os.getenv("GEN_BACKEND")
    if override:
        return override.lower()
    return "openai" if get_settings().openai_api_key else "fake"


def _json_schema() -> dict:
    """JSON schema for OpenAI structured outputs. Derived from ArticleDraft."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "summary", "problem", "steps_md", "tags", "category", "confidence"],
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "problem": {"type": "string"},
            "steps_md": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "category": {"type": ["string", "null"]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _call_openai(ticket: Ticket) -> ArticleDraft:
    from openai import AsyncOpenAI

    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key)
    resp = await client.chat.completions.create(
        model=s.openai_model,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(ticket)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "kb_article_draft",
                "strict": True,
                "schema": _json_schema(),
            },
        },
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return ArticleDraft.model_validate(data)


def _fake_draft(ticket: Ticket) -> ArticleDraft:
    """Derive a reasonable article from ticket content without calling OpenAI.

    Penalizes short resolution notes so downstream scoring still sees signal.
    """
    resolution = (ticket.resolution or "").strip()
    confidence = 0.85 if len(resolution) >= 80 else 0.55 if resolution else 0.3
    steps_md = resolution if resolution else "Resolution notes were missing on the source ticket."
    summary = (
        ticket.description.strip().split("\n")[0][:200]
        if ticket.description
        else ticket.title[:200]
    )
    return ArticleDraft(
        title=ticket.title,
        summary=summary,
        problem=ticket.description or ticket.title,
        steps_md=steps_md,
        tags=list(ticket.tags),
        category=ticket.topic,
        confidence=confidence,
    )


async def generate_article(ticket: Ticket) -> tuple[ArticleDraft, str, str]:
    """Return (draft, model_name, prompt_version)."""
    s = get_settings()
    backend = _resolve_backend()
    if backend == "fake":
        log.warning("generation backend=fake (no OPENAI_API_KEY) — deterministic placeholder drafts")
        draft = _fake_draft(ticket)
        return draft, "fake", PROMPT_VERSION
    draft = await _call_openai(ticket)
    return draft, s.openai_model, PROMPT_VERSION


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _call_openai_gap_rag(
    ticket: Ticket, neighbours: "list[NeighbourContext]"
) -> ArticleDraft:
    from openai import AsyncOpenAI

    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key)
    resp = await client.chat.completions.create(
        model=s.openai_model,
        messages=[
            {"role": "system", "content": build_gap_rag_system_prompt()},
            {"role": "user", "content": build_gap_rag_user_prompt(ticket, neighbours)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "kb_article_draft",
                "strict": True,
                "schema": _json_schema(),
            },
        },
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return ArticleDraft.model_validate(data)


def _fake_gap_rag_draft(
    ticket: Ticket, neighbours: "list[NeighbourContext]"
) -> ArticleDraft:
    """Offline placeholder — stitches the top neighbour's steps onto the target
    ticket's framing so tests can exercise the gap-RAG path without a key."""
    top = neighbours[0]
    steps = (
        "(No OpenAI key — placeholder from neighbour 1)\n\n"
        + (top.steps_md or "No steps available in neighbour.")
    )
    summary = (
        ticket.description.strip().split("\n")[0][:200]
        if ticket.description
        else ticket.title[:200]
    )
    # Confidence caps low because we synthesised this from neighbours, not from
    # the target ticket's own (missing) resolution.
    confidence = min(0.35, max(0.1, top.relevance - 0.4))
    return ArticleDraft(
        title=ticket.title,
        summary=summary,
        problem=ticket.description or ticket.title,
        steps_md=steps,
        tags=list(ticket.tags),
        category=ticket.topic or top.category,
        confidence=round(confidence, 2),
    )


async def generate_article_from_neighbours(
    ticket: Ticket, neighbours: "list[NeighbourContext]"
) -> tuple[ArticleDraft, str, str]:
    """Return (draft, model_name, prompt_version) for a gap ticket synthesised
    from neighbour KBs. Matches the shape of `generate_article` so the caller
    site can stay symmetric with the normal pipeline."""
    if not neighbours:
        raise ValueError("generate_article_from_neighbours requires at least one neighbour")
    s = get_settings()
    backend = _resolve_backend()
    if backend == "fake":
        log.warning(
            "generation backend=fake (no OPENAI_API_KEY) — gap-RAG draft is a "
            "deterministic placeholder"
        )
        draft = _fake_gap_rag_draft(ticket, neighbours)
        return draft, "fake", GAP_RAG_PROMPT_VERSION
    draft = await _call_openai_gap_rag(ticket, neighbours)
    return draft, s.openai_model, GAP_RAG_PROMPT_VERSION
