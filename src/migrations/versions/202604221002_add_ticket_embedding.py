"""add embedding column + ivfflat index to kb.processed_ticket

Enables semantic search over tickets (not just KB chunks). Column is nullable
so existing rows remain valid after upgrade; the first poll cycle on each
ticket refills it, and the `/admin/reindex-tickets` endpoint backfills
historical rows in one shot.

Revision ID: 202604221002
Revises: 202604221001
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "202604221002"
down_revision = "202604221001"
branch_labels = None
depends_on = None


# Must match src.config.Settings.embedding_dim. Hardcoded here to keep the
# migration self-contained (Alembic shouldn't import application settings).
EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.add_column(
        "processed_ticket",
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        schema="kb",
    )
    # Cosine-ops ivfflat mirrors the kb.chunk index shape. `lists=100` is
    # appropriate for thousands-to-low-hundreds-of-thousands of rows; if the
    # corpus grows past that, re-tune.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kb_processed_ticket_embedding "
        "ON kb.processed_ticket USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS kb.ix_kb_processed_ticket_embedding")
    op.drop_column("processed_ticket", "embedding", schema="kb")
