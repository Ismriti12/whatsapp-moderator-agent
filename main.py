"""FastAPI entry point.

Serves moderation data over HTTP and optionally starts the WhatsApp listener
in a background thread so one command (`python -m app.main`) boots the whole
backend.

Run:
    python -m app.main
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from pydantic import BaseModel

from app.database import Message, get_session, init_db
from app.whatsapp_listener import run_listener

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
AUTO_START_LISTENER = os.getenv("AUTO_START_LISTENER", "false").strip().lower() == "true"

app = FastAPI(title="WhatsApp Moderator Agent", version="0.1.0")


class MessageOut(BaseModel):
    id: int
    chat_name: str
    sender: Optional[str]
    text: str
    category: Optional[str]
    is_flagged: bool
    confidence: Optional[int]
    reasoning: Optional[str]
    action_taken: str

    class Config:
        from_attributes = True


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    if AUTO_START_LISTENER:
        logger.info("AUTO_START_LISTENER=true, starting WhatsApp listener thread")
        thread = threading.Thread(target=run_listener, daemon=True)
        thread.start()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/messages", response_model=list[MessageOut])
def list_messages(
    flagged_only: bool = Query(False, description="Only return flagged messages"),
    chat_name: Optional[str] = Query(None, description="Filter by chat/group name"),
    limit: int = Query(100, le=1000),
):
    session = get_session()
    try:
        query = session.query(Message).order_by(Message.received_at.desc())
        if flagged_only:
            query = query.filter(Message.is_flagged.is_(True))
        if chat_name:
            query = query.filter(Message.chat_name == chat_name)
        return query.limit(limit).all()
    finally:
        session.close()


@app.get("/stats")
def stats() -> dict:
    session = get_session()
    try:
        total = session.query(Message).count()
        flagged = session.query(Message).filter(Message.is_flagged.is_(True)).count()
        return {"total_messages": total, "flagged_messages": flagged}
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=False)
