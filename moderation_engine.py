"""Moderation decision logic.

Takes a raw message, runs it through the Gemini classifier, stores the result
in the database, and decides what action to take (allow / flag / delete).
Deletion is logged only (not actually performed on WhatsApp) unless a
`delete_callback` is supplied, keeping the default behavior safe.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from dotenv import load_dotenv

from app import gemini_classifier
from app.database import Message, get_session

load_dotenv()

logger = logging.getLogger(__name__)

FLAG_CATEGORIES = {
    c.strip()
    for c in os.getenv(
        "MODERATION_FLAG_CATEGORIES",
        "spam,harassment,hate_speech,explicit_content,scam",
    ).split(",")
    if c.strip()
}


@dataclass
class IncomingMessage:
    chat_name: str
    sender: Optional[str]
    text: str


def _message_hash(chat_name: str, sender: Optional[str], text: str) -> str:
    """Stable fingerprint used to avoid storing/processing the same message twice."""
    raw = f"{chat_name}|{sender}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def process_message(
    incoming: IncomingMessage,
    delete_callback: Optional[Callable[[IncomingMessage], None]] = None,
) -> Optional[Message]:
    """Classify, persist, and act on a single incoming message.

    Returns the stored Message row, or None if it was a duplicate that had
    already been processed before.
    """
    msg_hash = _message_hash(incoming.chat_name, incoming.sender, incoming.text)

    session = get_session()
    try:
        if session.query(Message).filter_by(message_hash=msg_hash).first():
            return None  # already processed

        result = gemini_classifier.classify(incoming.text)
        should_flag = result.is_flagged or result.category in FLAG_CATEGORIES
        action = "flagged" if should_flag else "allowed"

        if should_flag and delete_callback is not None:
            try:
                delete_callback(incoming)
                action = "deleted"
            except Exception:  # noqa: BLE001
                logger.exception("delete_callback failed; leaving message flagged")

        record = Message(
            chat_name=incoming.chat_name,
            sender=incoming.sender,
            text=incoming.text,
            message_hash=msg_hash,
            category=result.category,
            is_flagged=should_flag,
            confidence=result.confidence,
            reasoning=result.reasoning,
            action_taken=action,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        logger.info(
            "Processed message from %s in %s -> category=%s action=%s",
            incoming.sender,
            incoming.chat_name,
            result.category,
            action,
        )
        return record
    finally:
        session.close()
