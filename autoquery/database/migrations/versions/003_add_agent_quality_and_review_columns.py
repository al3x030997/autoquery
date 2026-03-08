"""add quality_score, quality_action, review metadata to agents

Revision ID: 003
Revises: 002
Create Date: 2026-03-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("agents", sa.Column("quality_action", sa.Text(), nullable=True))
    op.add_column("agents", sa.Column("reviewed_by", sa.String(255), nullable=True))
    op.add_column("agents", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agents", sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "rejection_reason")
    op.drop_column("agents", "reviewed_at")
    op.drop_column("agents", "reviewed_by")
    op.drop_column("agents", "quality_action")
    op.drop_column("agents", "quality_score")
