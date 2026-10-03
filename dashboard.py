"""Streamlit dashboard for reviewing moderated WhatsApp messages.

Run:
    streamlit run dashboard/dashboard.py

Reads directly from the same database configured via DATABASE_URL in .env, so
it works whether or not the FastAPI server is running.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `from app.database import ...` when run as `streamlit run dashboard/dashboard.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from app.database import Message, get_session, init_db

st.set_page_config(page_title="WhatsApp Moderator Dashboard", layout="wide")

init_db()

st.title("📋 WhatsApp Moderator Dashboard")

session = get_session()
try:
    rows = session.query(Message).order_by(Message.received_at.desc()).all()
    data = [
        {
            "id": r.id,
            "received_at": r.received_at,
            "chat_name": r.chat_name,
            "sender": r.sender,
            "text": r.text,
            "category": r.category,
            "is_flagged": r.is_flagged,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "action_taken": r.action_taken,
        }
        for r in rows
    ]
finally:
    session.close()

df = pd.DataFrame(data)

col1, col2, col3 = st.columns(3)
col1.metric("Total messages", len(df))
col2.metric("Flagged messages", int(df["is_flagged"].sum()) if not df.empty else 0)
col3.metric(
    "Unique chats", int(df["chat_name"].nunique()) if not df.empty else 0
)

st.divider()

if df.empty:
    st.info("No messages yet. Start the listener (python -m app.main) and send a message.")
else:
    chat_options = ["All"] + sorted(df["chat_name"].dropna().unique().tolist())
    selected_chat = st.selectbox("Chat/group", chat_options)
    flagged_only = st.checkbox("Show flagged only", value=False)

    filtered = df
    if selected_chat != "All":
        filtered = filtered[filtered["chat_name"] == selected_chat]
    if flagged_only:
        filtered = filtered[filtered["is_flagged"]]

    st.dataframe(
        filtered[
            [
                "received_at",
                "chat_name",
                "sender",
                "text",
                "category",
                "is_flagged",
                "confidence",
                "action_taken",
                "reasoning",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
