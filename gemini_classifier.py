"""Gemini-backed message classifier.

Wraps google-generativeai so the rest of the app can call `classify()` and get
back a structured result, without caring about prompt construction or model
setup. Designed to fail soft: if no API key is configured, messages are
returned as "unclassified" instead of crashing the app, so the project still
runs end-to-end for a first try before secrets are set up.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_client = None
if GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here":
    _client = genai.Client(api_key=GEMINI_API_KEY)
else:
    logger.warning(
        "GEMINI_API_KEY is not set. Messages will be stored as 'unclassified' "
        "until a valid key is added to .env."
    )

_PROMPT_TEMPLATE = """You are a content moderation classifier for a WhatsApp group chat.
Classify the following message and respond with ONLY a compact JSON object,
no markdown, no extra text, matching this schema:

{{
  "category": one of ["safe", "spam", "harassment", "hate_speech", "explicit_content", "scam", "other"],
  "is_flagged": true or false,
  "confidence": integer 0-100,
  "reasoning": a one-sentence explanation
}}

Message:
\"\"\"{message}\"\"\"
"""


@dataclass
class ClassificationResult:
    category: str
    is_flagged: bool
    confidence: int
    reasoning: str


def _fallback_result(reason: str) -> ClassificationResult:
    return ClassificationResult(
        category="unclassified",
        is_flagged=False,
        confidence=0,
        reasoning=reason,
    )


def classify(message_text: str) -> ClassificationResult:
    """Classify a message's text using Gemini. Never raises; falls back on error."""
    if _client is None:
        return _fallback_result("Gemini API key not configured")

    if not message_text or not message_text.strip():
        return _fallback_result("Empty message")

    try:
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=_PROMPT_TEMPLATE.format(message=message_text),
        )
        raw = response.text.strip()
        # Models sometimes wrap JSON in ```json fences; strip them defensively.
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[-1] if raw.lower().startswith("json") else raw
        data = json.loads(raw)
        return ClassificationResult(
            category=str(data.get("category", "other")),
            is_flagged=bool(data.get("is_flagged", False)),
            confidence=int(data.get("confidence", 0)),
            reasoning=str(data.get("reasoning", "")),
        )
    except Exception as exc:  # noqa: BLE001 - classifier must never crash the pipeline
        logger.exception("Gemini classification failed")
        return _fallback_result(f"Classifier error: {exc}")
