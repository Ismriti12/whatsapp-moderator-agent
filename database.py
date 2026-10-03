"""Database models and session helpers.

Defaults to a local SQLite file (data/whatsapp.db) so the project runs with
zero external services. Set DATABASE_URL in .env to point at Postgres (or any
SQLAlchemy-supported database) instead.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'whatsapp.db').as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

# SQLite needs this flag when accessed from multiple threads (FastAPI + listener).
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Message(Base):
    """A single WhatsApp message captured by the listener, with its moderation result."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_name = Column(String(255), nullable=False, index=True)
    sender = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    message_hash = Column(String(64), nullable=False, unique=True, index=True)
    received_at = Column(DateTime, default=dt.datetime.utcnow, index=True)

    # Moderation outcome, filled in by the moderation engine.
    category = Column(String(64), nullable=True)
    is_flagged = Column(Boolean, default=False, index=True)
    confidence = Column(Integer, nullable=True)  # 0-100
    reasoning = Column(Text, nullable=True)
    action_taken = Column(String(32), default="pending")  # pending|allowed|flagged|deleted


def init_db() -> None:
    """Create tables if they do not exist yet. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()
