"""
Shared test fixtures for autoquery tests.

Uses SQLite with type adaptations for PostgreSQL-specific column types.
"""
import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
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
                column.type = Text()


_adapted = False


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
