"""init kb schema

Revision ID: 202604220001
Revises:
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "202604220001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make sure the extension + schema exist. pgvector is typically enabled by
    # the conversational-assistant's init.sql, but we idempotently ensure both.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE SCHEMA IF NOT EXISTS kb')

    op.create_table(
        "article",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_ticket_id", sa.String, index=True),
        sa.Column("itsm_provider", sa.String),
        sa.Column("itsm_kb_id", sa.String, unique=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("problem", sa.Text),
        sa.Column("steps_md", sa.Text),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("category", sa.String, index=True),
        sa.Column("status", sa.String, nullable=False, index=True),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("model", sa.String),
        sa.Column("prompt_version", sa.String),
        sa.Column("confidence", sa.Numeric),
        sa.Column("score_accuracy", sa.Numeric),
        sa.Column("score_recency", sa.Numeric),
        sa.Column("score_coverage", sa.Numeric),
        sa.Column("score_overall", sa.Numeric),
        sa.Column("reviewer", sa.String),
        sa.Column("review_notes", sa.Text),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("pushed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="kb",
    )

    op.create_table(
        "chunk",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kb.article.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, server_default="0"),
        sa.Column("embedding", Vector(1536)),
        sa.Column("content_hash", sa.String, index=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "chunk_index", name="uq_chunk_article_idx"),
        schema="kb",
    )
    # IVFFlat index — tuned for moderate corpora. Adjust lists for very large indexes.
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunk_embedding ON kb.chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    op.create_table(
        "processed_ticket",
        sa.Column("itsm_ticket_id", sa.String, primary_key=True),
        sa.Column("itsm_provider", sa.String, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("resolution", sa.Text),
        sa.Column("topic", sa.String, index=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decision", sa.String, nullable=False, index=True),
        sa.Column("decision_reason", sa.Text),
        sa.Column("matched_article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kb.article.id")),
        sa.Column("matched_score", sa.Numeric),
        sa.Column("draft_article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kb.article.id")),
        schema="kb",
    )

    op.create_table(
        "push_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kb.article.id"), index=True),
        sa.Column("itsm_provider", sa.String, nullable=False),
        sa.Column("request_payload", postgresql.JSONB),
        sa.Column("response_payload", postgresql.JSONB),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="kb",
    )

    op.create_table(
        "topic_snapshot",
        sa.Column("topic", sa.String, primary_key=True),
        sa.Column("window", sa.String, primary_key=True),
        sa.Column("ticket_count", sa.Integer, server_default="0"),
        sa.Column("kb_status", sa.String, nullable=False),
        sa.Column("last_activity", sa.DateTime(timezone=True)),
        schema="kb",
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("poll_interval_s", sa.Integer, server_default="60"),
        sa.Column("openai_model", sa.String, server_default="gpt-4.1"),
        sa.Column("embedding_model", sa.String, server_default="text-embedding-3-small"),
        sa.Column("chunk_size_tokens", sa.Integer, server_default="500"),
        sa.Column("chunk_overlap", sa.Integer, server_default="60"),
        sa.Column("confidence_threshold", sa.Numeric, server_default="0.6"),
        # Set the JSONB default in a follow-up statement to sidestep
        # SQLAlchemy's `text()` colon-as-bindparam parsing. Safe because the
        # INSERT ... VALUES (1) below explicitly seeds the row.
        sa.Column("score_weights", postgresql.JSONB),
        sa.Column("itsm_adapter", sa.String, server_default="mock"),
        sa.Column("itsm_config", postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dedup_threshold", sa.Numeric, server_default="0.82"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="kb",
    )
    # Default for JSONB column + seed the single settings row.
    # Build the JSON with jsonb_build_object to sidestep SQLAlchemy's
    # colon-as-bindparam parsing of literal JSON strings.
    op.execute(
        "ALTER TABLE kb.settings ALTER COLUMN score_weights "
        "SET DEFAULT jsonb_build_object('accuracy', 0.5, 'recency', 0.2, 'coverage', 0.3)"
    )
    op.execute(
        "INSERT INTO kb.settings (id, score_weights) "
        "VALUES (1, jsonb_build_object('accuracy', 0.5, 'recency', 0.2, 'coverage', 0.3)) "
        "ON CONFLICT DO NOTHING"
    )

    # Grant read-only access to the assistant_ro role (idempotent — role may not
    # exist yet in fresh environments; DO block swallows missing-role errors).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'assistant_ro') THEN
                GRANT USAGE ON SCHEMA kb TO assistant_ro;
                GRANT SELECT ON ALL TABLES IN SCHEMA kb TO assistant_ro;
                ALTER DEFAULT PRIVILEGES IN SCHEMA kb GRANT SELECT ON TABLES TO assistant_ro;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_table("settings", schema="kb")
    op.drop_table("topic_snapshot", schema="kb")
    op.drop_table("push_log", schema="kb")
    op.drop_table("processed_ticket", schema="kb")
    op.execute("DROP INDEX IF EXISTS kb.ix_kb_chunk_embedding")
    op.drop_table("chunk", schema="kb")
    op.drop_table("article", schema="kb")
