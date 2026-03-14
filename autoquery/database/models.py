from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from autoquery.database.db import Base


# Review status constants
REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUS_EXTRACTION_FAILED = "extraction_failed"
REVIEW_STATUS_UNREACHABLE = "unreachable"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(Text, server_default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    manuscripts = relationship("Manuscript", back_populates="user")
    interaction_events = relationship("InteractionEvent", back_populates="user")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agency: Mapped[str | None] = mapped_column(String(255))
    profile_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    # Extracted / structured fields
    genres: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    audience: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    hard_nos_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    submission_req: Mapped[dict | None] = mapped_column(JSONB)
    is_open: Mapped[bool | None] = mapped_column(Boolean)

    # Raw scraped text — internal only, never expose on public routes
    wishlist_raw: Mapped[str | None] = mapped_column(Text, comment="internal-only: raw scraped wishlist text")
    bio_raw: Mapped[str | None] = mapped_column(Text, comment="internal-only: raw scraped bio text")
    hard_nos_raw: Mapped[str | None] = mapped_column(Text, comment="internal-only: raw scraped hard-nos text")
    email: Mapped[str | None] = mapped_column(String(255), comment="internal-only: contact email")

    # Embedding + FTS
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    fts_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    # Quality gate metadata
    quality_score: Mapped[float | None] = mapped_column(Float)
    quality_action: Mapped[str | None] = mapped_column(Text)

    # Review metadata
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # Status
    review_status: Mapped[str] = mapped_column(
        String(50), server_default=REVIEW_STATUS_PENDING, nullable=False
    )
    opted_out: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    matching_results = relationship("MatchingResult", back_populates="agent")
    interaction_events = relationship("InteractionEvent", back_populates="agent")
    recrawl_queue_entries = relationship("RecrawlQueue", back_populates="agent")


class Manuscript(Base):
    __tablename__ = "manuscripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    session_id: Mapped[str | None] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(255))
    audience: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    word_count: Mapped[int | None] = mapped_column(Integer)
    query_letter: Mapped[str | None] = mapped_column(Text)
    synopsis: Mapped[str | None] = mapped_column(Text)
    comps: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # Embeddings — fulltext and query-expanded variants for A/B testing
    embedding_fulltext: Mapped[list[float] | None] = mapped_column(Vector(1024))
    embedding_query_expanded: Mapped[list[float] | None] = mapped_column(Vector(1024))

    # Per-row score weights for A/B testing
    genre_score_weight: Mapped[float | None] = mapped_column(Float)
    fts_score_weight: Mapped[float | None] = mapped_column(Float)
    semantic_score_weight: Mapped[float | None] = mapped_column(Float)
    audience_score_weight: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="manuscripts")
    matching_results = relationship("MatchingResult", back_populates="manuscript")
    interaction_events = relationship("InteractionEvent", back_populates="manuscript")


class MatchingResult(Base):
    __tablename__ = "matching_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manuscript_id: Mapped[int] = mapped_column(Integer, ForeignKey("manuscripts.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    # Score components
    genre_score: Mapped[float | None] = mapped_column(Float)
    fts_score: Mapped[float | None] = mapped_column(Float)
    semantic_score: Mapped[float | None] = mapped_column(Float)
    audience_score: Mapped[float | None] = mapped_column(Float)
    composite_score: Mapped[float | None] = mapped_column(Float)

    # Ranking
    mmr_rank: Mapped[int | None] = mapped_column(Integer)
    algorithm_version: Mapped[str | None] = mapped_column(String(50))

    # Status funnel
    status: Mapped[str | None] = mapped_column(String(50))
    queried_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    manuscript = relationship("Manuscript", back_populates="matching_results")
    agent = relationship("Agent", back_populates="matching_results")


class InteractionEvent(Base):
    __tablename__ = "interaction_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    manuscript_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("manuscripts.id", ondelete="SET NULL"))
    agent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agents.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    manuscript = relationship("Manuscript", back_populates="interaction_events")
    agent = relationship("Agent", back_populates="interaction_events")
    user = relationship("User", back_populates="interaction_events")


class KnownProfileUrl(Base):
    __tablename__ = "known_profile_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    discovered_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    discovery_method: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text, server_default="active")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    consecutive_failures: Mapped[int | None] = mapped_column(Integer, server_default="0")


class OptOutRequest(Base):
    __tablename__ = "opt_out_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("agents.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecrawlQueue(Base):
    __tablename__ = "recrawl_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_id: Mapped[int] = mapped_column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    priority: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agent = relationship("Agent", back_populates="recrawl_queue_entries")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str | None] = mapped_column(Text)
    run_type: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(Text)

    # Page stats
    pages_fetched: Mapped[int | None] = mapped_column(Integer, server_default="0")
    pages_index: Mapped[int | None] = mapped_column(Integer, server_default="0")
    pages_content: Mapped[int | None] = mapped_column(Integer, server_default="0")
    pages_skipped: Mapped[int | None] = mapped_column(Integer, server_default="0")
    pages_error: Mapped[int | None] = mapped_column(Integer, server_default="0")

    # Quality stats
    quality_extracted: Mapped[int | None] = mapped_column(Integer, server_default="0")
    quality_warned: Mapped[int | None] = mapped_column(Integer, server_default="0")
    quality_discarded: Mapped[int | None] = mapped_column(Integer, server_default="0")
    avg_quality_score: Mapped[float | None] = mapped_column(Float)

    # Profile stats
    profiles_new: Mapped[int | None] = mapped_column(Integer, server_default="0")
    profiles_updated: Mapped[int | None] = mapped_column(Integer, server_default="0")
    profiles_unchanged: Mapped[int | None] = mapped_column(Integer, server_default="0")

    top_issues: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)


class CrawledPage(Base):
    __tablename__ = "crawled_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crawl_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("crawl_runs.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    page_type: Mapped[str | None] = mapped_column(Text)
    clean_text: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    quality_score: Mapped[float | None] = mapped_column(Float)
    quality_action: Mapped[str | None] = mapped_column(Text)
    quality_dimensions: Mapped[dict | None] = mapped_column(JSONB)
    quality_issues: Mapped[list | None] = mapped_column(JSONB)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SuggestedDomain(Base):
    __tablename__ = "suggested_domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    suggested_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
