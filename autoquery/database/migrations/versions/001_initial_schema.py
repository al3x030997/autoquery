"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions — must come before any Vector() column
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2. Tables in FK-dependency order

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("plan", sa.Text(), server_default="free", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # agents
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("agency", sa.String(255)),
        sa.Column("profile_url", sa.Text(), nullable=False, unique=True),
        sa.Column("genres", ARRAY(sa.Text())),
        sa.Column("keywords", ARRAY(sa.Text())),
        sa.Column("audience", ARRAY(sa.Text())),
        sa.Column("hard_nos_keywords", ARRAY(sa.Text())),
        sa.Column("submission_req", JSONB()),
        sa.Column("is_open", sa.Boolean()),
        sa.Column("wishlist_raw", sa.Text(), comment="internal-only: raw scraped wishlist text"),
        sa.Column("bio_raw", sa.Text(), comment="internal-only: raw scraped bio text"),
        sa.Column("hard_nos_raw", sa.Text(), comment="internal-only: raw scraped hard-nos text"),
        sa.Column("email", sa.String(255), comment="internal-only: contact email"),
        sa.Column("embedding", Vector(1024)),
        sa.Column("fts_vector", TSVECTOR()),
        sa.Column("review_status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("opted_out", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # manuscripts
    op.create_table(
        "manuscripts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("genre", sa.String(255)),
        sa.Column("audience", ARRAY(sa.Text())),
        sa.Column("word_count", sa.Integer()),
        sa.Column("query_letter", sa.Text()),
        sa.Column("synopsis", sa.Text()),
        sa.Column("comps", ARRAY(sa.Text())),
        sa.Column("embedding_fulltext", Vector(1024)),
        sa.Column("embedding_query_expanded", Vector(1024)),
        sa.Column("genre_score_weight", sa.Float()),
        sa.Column("fts_score_weight", sa.Float()),
        sa.Column("semantic_score_weight", sa.Float()),
        sa.Column("audience_score_weight", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # matching_results
    op.create_table(
        "matching_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manuscript_id", sa.Integer(), sa.ForeignKey("manuscripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("genre_score", sa.Float()),
        sa.Column("fts_score", sa.Float()),
        sa.Column("semantic_score", sa.Float()),
        sa.Column("audience_score", sa.Float()),
        sa.Column("composite_score", sa.Float()),
        sa.Column("mmr_rank", sa.Integer()),
        sa.Column("algorithm_version", sa.String(50)),
        sa.Column("status", sa.String(50)),
        sa.Column("queried_at", sa.DateTime(timezone=True)),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("outcome", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # interaction_events (BigInteger PK — will be largest table)
    op.create_table(
        "interaction_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("manuscript_id", sa.Integer(), sa.ForeignKey("manuscripts.id", ondelete="SET NULL")),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # known_profile_urls
    op.create_table(
        "known_profile_urls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("domain", sa.String(255)),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # opt_out_requests
    op.create_table(
        "opt_out_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("reason", sa.Text()),
        sa.Column("processed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # recrawl_queue
    op.create_table(
        "recrawl_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # crawl_runs
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50)),
        sa.Column("pages_crawled", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pages_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pages_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_passed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("profiles_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("profiles_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("profiles_unchanged", sa.Integer(), server_default="0", nullable=False),
        sa.Column("top_issues", JSONB()),
    )

    # suggested_domains (stub — not exposed in MVP frontend)
    op.create_table(
        "suggested_domains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False, unique=True),
        sa.Column("suggested_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("reviewed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 3. Indexes

    # IVFFlat vector index — cosine similarity, 50 lists
    op.execute(
        "CREATE INDEX agents_embedding_idx ON agents "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)"
    )

    # GIN index on fts_vector
    op.execute("CREATE INDEX agents_fts_idx ON agents USING gin(fts_vector)")

    # Composite filter index for matching queries
    op.create_index(
        "agents_matching_filter_idx",
        "agents",
        ["review_status", "is_open", "opted_out"],
    )

    # Interaction events indexes
    op.create_index(
        "interaction_events_manuscript_agent_idx",
        "interaction_events",
        ["manuscript_id", "agent_id"],
    )
    op.create_index(
        "interaction_events_event_type_idx",
        "interaction_events",
        ["event_type"],
    )
    op.create_index(
        "interaction_events_created_at_idx",
        "interaction_events",
        ["created_at"],
    )

    # 4. FTS trigger — fires only on keywords, genres, hard_nos_keywords updates
    op.execute("""
CREATE OR REPLACE FUNCTION agents_fts_update() RETURNS trigger AS $$
BEGIN
    NEW.fts_vector :=
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.keywords, ' '), '')), 'A') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.genres, ' '), '')), 'B') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.hard_nos_keywords, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
""")

    op.execute("""
CREATE TRIGGER agents_fts_trigger
BEFORE INSERT OR UPDATE OF keywords, genres, hard_nos_keywords
ON agents FOR EACH ROW EXECUTE FUNCTION agents_fts_update()
""")


def downgrade() -> None:
    # Drop trigger and function first
    op.execute("DROP TRIGGER IF EXISTS agents_fts_trigger ON agents")
    op.execute("DROP FUNCTION IF EXISTS agents_fts_update()")

    # Drop indexes
    op.drop_index("interaction_events_created_at_idx", table_name="interaction_events")
    op.drop_index("interaction_events_event_type_idx", table_name="interaction_events")
    op.drop_index("interaction_events_manuscript_agent_idx", table_name="interaction_events")
    op.drop_index("agents_matching_filter_idx", table_name="agents")
    op.execute("DROP INDEX IF EXISTS agents_fts_idx")
    op.execute("DROP INDEX IF EXISTS agents_embedding_idx")

    # Drop tables in reverse FK-dependency order
    op.drop_table("suggested_domains")
    op.drop_table("crawl_runs")
    op.drop_table("recrawl_queue")
    op.drop_table("opt_out_requests")
    op.drop_table("known_profile_urls")
    op.drop_table("interaction_events")
    op.drop_table("matching_results")
    op.drop_table("manuscripts")
    op.drop_table("agents")
    op.drop_table("users")
