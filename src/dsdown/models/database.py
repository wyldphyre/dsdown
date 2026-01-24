"""Database setup and session management."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from dsdown.config import DEFAULT_DB_PATH


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(db_path: Path | None = None) -> Engine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        path = db_path or DEFAULT_DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{path}", echo=False)
    return _engine


def get_session(db_path: Path | None = None) -> Session:
    """Get a new database session."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(db_path)
        # expire_on_commit=False prevents objects from being expired after commit
        # This is important for GUI apps where we keep objects in widgets
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _session_factory()


def init_db(db_path: Path | None = None) -> None:
    """Initialize the database, creating all tables."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    _run_migrations(engine)


def _run_migrations(engine: Engine) -> None:
    """Run any necessary database migrations."""
    inspector = inspect(engine)

    # Migration: Add include_series_in_filename column to series table
    if "series" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("series")]
        if "include_series_in_filename" not in columns:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE series ADD COLUMN include_series_in_filename "
                        "BOOLEAN NOT NULL DEFAULT 1"
                    )
                )
                conn.commit()
