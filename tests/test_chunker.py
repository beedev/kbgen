from src.indexing.chunker import chunk_article


def test_short_article_single_chunk():
    chunks = chunk_article("Reset VPN", "Just clear cached creds and reconnect.")
    assert len(chunks) == 1
    assert "Reset VPN" in chunks[0].content
    assert chunks[0].token_count > 0


def test_title_prepended_to_each_chunk_for_long_articles():
    body = "step one. " * 600  # ~2000 tokens
    chunks = chunk_article("Canonical Topic", body, chunk_size=300, overlap=40)
    assert len(chunks) >= 2
    # Every chunk after the first should start with the title so retrieval
    # never loses topical context.
    for c in chunks[1:]:
        assert c.content.startswith("Canonical Topic")


def test_overlap_preserves_continuity():
    body = " ".join([f"word{i}" for i in range(2000)])
    chunks = chunk_article("T", body, chunk_size=200, overlap=50)
    # Adjacent chunks should share some tokens due to overlap.
    assert len(chunks) >= 2
    for a, b in zip(chunks, chunks[1:]):
        # Naive: some trailing word of `a` appears in the leading content of `b`.
        tail = a.content.split()[-10:]
        assert any(w in b.content for w in tail)


def test_invalid_overlap_rejected():
    import pytest

    with pytest.raises(ValueError):
        chunk_article("T", "body", chunk_size=100, overlap=100)
