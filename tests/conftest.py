"""Shared test fixtures — nothing clever, just sets EMBEDDING_BACKEND=fake
and GEN_BACKEND=fake so tests never reach out to OpenAI.
"""

import os

os.environ.setdefault("EMBEDDING_BACKEND", "fake")
os.environ.setdefault("GEN_BACKEND", "fake")
