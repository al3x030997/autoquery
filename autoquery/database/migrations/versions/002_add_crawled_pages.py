"""add crawled_pages table

Revision ID: 002
Revises: 001
Create Date: 2026-03-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crawled_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "crawl_run_id",
            sa.Integer(),
            sa.ForeignKey("crawl_runs.id", ondelete="CASCADE"),
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("page_type", sa.Text()),
        sa.Column("clean_text", sa.Text()),
        sa.Column("word_count", sa.Integer()),
        sa.Column("quality_score", sa.Float()),
        sa.Column("quality_action", sa.Text()),
        sa.Column("quality_dimensions", JSONB()),
        sa.Column("quality_issues", JSONB()),
        sa.Column(
            "crawled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "crawled_pages_crawl_run_id_idx",
        "crawled_pages",
        ["crawl_run_id"],
    )
    op.create_index(
        "crawled_pages_quality_action_idx",
        "crawled_pages",
        ["quality_action"],
    )


def downgrade() -> None:
    op.drop_index("crawled_pages_quality_action_idx", table_name="crawled_pages")
    op.drop_index("crawled_pages_crawl_run_id_idx", table_name="crawled_pages")
    op.drop_table("crawled_pages")
