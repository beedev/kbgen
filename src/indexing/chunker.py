"""Token-aware chunker.

Splits an article into ~chunk_size-token chunks with configurable overlap.
The title is prepended to the first chunk so it stays searchable even for
articles whose body is long enough to push the title out of the first chunk.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken


@dataclass
class Chunk:
    index: int
    content: str
    token_count: int


_ENCODING_NAME = "cl100k_base"  # text-embedding-3-small + gpt-4.1 both use cl100k_base.


def _encoder():
    return tiktoken.get_encoding(_ENCODING_NAME)


def chunk_article(
    title: str,
    body: str,
    *,
    chunk_size: int = 500,
    overlap: int = 60,
) -> list[Chunk]:
    """Return chunks covering `title + body`. Always emits at least one chunk."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    enc = _encoder()
    title_prefix = f"{title}\n\n" if title else ""
    full = f"{title_prefix}{body}".strip()
    if not full:
        return [Chunk(index=0, content=title, token_count=len(enc.encode(title)))]

    tokens = enc.encode(full)
    if len(tokens) <= chunk_size:
        return [Chunk(index=0, content=full, token_count=len(tokens))]

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    i = 0
    idx = 0
    while i < len(tokens):
        slice_tokens = tokens[i : i + chunk_size]
        text = enc.decode(slice_tokens)
        # Re-prepend title for chunks after the first so headline context is preserved.
        if idx > 0 and title:
            text = f"{title}\n\n{text}"
            slice_tokens = enc.encode(text)
        chunks.append(Chunk(index=idx, content=text, token_count=len(slice_tokens)))
        idx += 1
        if i + chunk_size >= len(tokens):
            break
        i += step
    return chunks
