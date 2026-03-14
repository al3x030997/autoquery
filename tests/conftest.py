"""
Shared test fixtures for autoquery tests.

Uses SQLite with type adaptations for PostgreSQL-specific column types.
"""
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Text, TypeDecorator, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from autoquery.database.db import Base


class JSONEncodedList(TypeDecorator):
    """Store lists as JSON strings in SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class JSONEncodedDict(TypeDecorator):
    """Store dicts as JSON strings in SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


def _adapt_pg_types_for_sqlite():
    """
    Replace PostgreSQL-specific types with SQLite-compatible ones
    at the column level before create_all.
    """
    from sqlalchemy import BigInteger, Integer
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
    from pgvector.sqlalchemy import Vector

    for table in Base.metadata.tables.values():
        for column in table.columns:
            col_type = type(column.type)
            if col_type is ARRAY:
                column.type = JSONEncodedList()
            elif col_type is JSONB:
                column.type = JSONEncodedDict()
            elif col_type is TSVECTOR:
                column.type = Text()
            elif col_type is Vector:
                column.type = JSONEncodedList()
            elif col_type is BigInteger and column.primary_key:
                # SQLite only auto-increments INTEGER PRIMARY KEY, not BIGINT
                column.type = Integer()


_adapted = False  # Reset to re-run adaptations after code changes


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    global _adapted
    if not _adapted:
        _adapt_pg_types_for_sqlite()
        _adapted = True

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class _FakeEmbeddingModel:
    """Fake embedding model for tests — returns zero vector."""
    dimensions = 1024

    async def embed(self, text: str) -> list[float]:
        return [0.0] * 1024

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 1024 for _ in texts]


@pytest.fixture
def fake_embedding_model():
    return _FakeEmbeddingModel()


@pytest.fixture
def client(db_session):
    """TestClient with DB and embedding model overrides."""
    from autoquery.api.main import app
    from autoquery.database.db import get_db
    from autoquery.api.deps import get_embedding_model

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_embedding_model] = lambda: _FakeEmbeddingModel()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
