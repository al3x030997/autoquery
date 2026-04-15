"""Add profile_notes JSONB, profile_notes_raw, prompt_version to agents.

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("profile_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("agents", sa.Column("profile_notes_raw", sa.Text(), nullable=True))
    op.add_column("agents", sa.Column("prompt_version", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "prompt_version")
    op.drop_column("agents", "profile_notes_raw")
    op.drop_column("agents", "profile_notes")
