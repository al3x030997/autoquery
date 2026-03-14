"""Add session_id column to manuscripts table.

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("manuscripts", sa.Column("session_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("manuscripts", "session_id")
