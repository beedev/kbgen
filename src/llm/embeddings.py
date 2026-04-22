"""Embedding client.

Two backends:
  * `openai` — calls `text-embedding-3-small` (1536 dims). Requires OPENAI_API_KEY.
  * `fake`   — deterministic hash-based vectors for offline dev/tests. Same dim.

Backend selection: env `EMBEDDING_BACKEND` overrides. When unset, `openai`
is used if an API key is present, else `fake` with a warning. This keeps the
indexing pipeline testable end-to-end without burning tokens while still
letting the real pipeline run seamlessly when the key is configured.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import struct
from typing import Sequence

from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

log = logging.getLogger(__name__)

_OPENAI_BATCH = 100


def _resolve_backend() -> str:
    override = os.getenv("EMBEDDING_BACKEND")
    if override:
        return override.lower()
    return "openai" if get_settings().openai_api_key else "fake"


def _fake_vector(text: str, dim: int) -> list[float]:
    """Deterministic pseudo-embedding: seed SHA-256 → repeated floats → L2-normalize.

    Good enough for relevance-ranking smoke tests (same text produces same vector,
    similar text produces nearby vectors via shared seed bytes).
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # Expand digest to `dim` floats via repeated hashing.
    out: list[float] = []
    seed = digest
    while len(out) < dim:
        for i in range(0, len(seed), 4):
            if len(out) >= dim:
                break
            chunk = seed[i : i + 4].ljust(4, b"\0")
            (u,) = struct.unpack(">I", chunk)
            out.append((u / 0xFFFFFFFF) * 2.0 - 1.0)
        seed = hashlib.sha256(seed).digest()
    # L2 normalize — makes cosine similarity well-behaved.
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _openai_embed(texts: list[str], model: str) -> list[list[float]]:
    from openai import AsyncOpenAI

    s = get_settings()
    client = AsyncOpenAI(api_key=s.openai_api_key)
    resp = await client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


async def embed_many(texts: Sequence[str]) -> list[list[float]]:
    """Return one vector per input text, in order."""
    if not texts:
        return []
    s = get_settings()
    backend = _resolve_backend()
    if backend == "fake":
        log.warning("embedding backend=fake (no OPENAI_API_KEY) — vectors are deterministic hashes")
        return [_fake_vector(t, s.embedding_dim) for t in texts]

    # Batch to stay under OpenAI's per-request input cap.
    out: list[list[float]] = []
    for i in range(0, len(texts), _OPENAI_BATCH):
        batch = list(texts[i : i + _OPENAI_BATCH])
        vecs = await _openai_embed(batch, s.embedding_model)
        out.extend(vecs)
    return out


async def embed_one(text: str) -> list[float]:
    vecs = await embed_many([text])
    return vecs[0]
