"""add tuning thresholds to kb.settings

Promotes two previously-hardcoded values to runtime settings so customers
can tune them without a rebuild:

  • min_resolution_chars   (default 20)
      Tickets whose resolution text has fewer characters (after trim) are
      marked SKIPPED — kbgen refuses to hallucinate a KB article from a
      ticket that carries no substantive resolution signal.

  • thinness_threshold_chars  (default 120)
      Accuracy dampening band. Resolutions below this length receive up
      to 25% Accuracy penalty (linearly scaled: at 0 chars → full 25%,
      at 120 chars → 0%). Drafts whose source tickets fall in this band
      still get published, just with a visibly lower confidence signal.

Revision ID: 202604221001
Revises: 202604220001
"""

from alembic import op
import sqlalchemy as sa

revision = "202604221001"
down_revision = "202604220001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "settings",
        sa.Column("min_resolution_chars", sa.Integer, server_default="20", nullable=False),
        schema="kb",
    )
    op.add_column(
        "settings",
        sa.Column(
            "thinness_threshold_chars", sa.Integer, server_default="120", nullable=False
        ),
        schema="kb",
    )


def downgrade() -> None:
    op.drop_column("settings", "thinness_threshold_chars", schema="kb")
    op.drop_column("settings", "min_resolution_chars", schema="kb")
