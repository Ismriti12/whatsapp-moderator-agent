"""WhatsApp Web listener built on Playwright.

Opens WhatsApp Web in a persistent browser profile (stored under
data/playwright-profile) so the QR code only needs to be scanned once per
machine. Polls a target chat for new messages and forwards each one to the
moderation engine.

Note: WhatsApp Web's DOM/selectors change periodically. The selectors below
are a best-effort as of 2024/2025; if message detection stops working, the
`MESSAGE_ROW_SELECTOR` / `CHAT_TITLE_SELECTOR` constants are the first place
to update.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

from app.moderation_engine import IncomingMessage, process_message

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROFILE_DIR = Path(__file__).resolve().parent.parent / "data" / "playwright-profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

TARGET_CHAT = os.getenv("WHATSAPP_TARGET_CHAT", "")
POLL_INTERVAL = float(os.getenv("WHATSAPP_POLL_INTERVAL", "5"))
HEADLESS = os.getenv("WHATSAPP_HEADLESS", "false").strip().lower() == "true"

WHATSAPP_URL = "https://web.whatsapp.com"
CHAT_SEARCH_SELECTOR = 'div[contenteditable="true"][data-tab="3"]'
MESSAGE_ROW_SELECTOR = "div.message-in, div.message-out"
MESSAGE_TEXT_SELECTOR = "span.selectable-text"
SENDER_NAME_SELECTOR = "span[aria-label]._ao3e, span[dir='auto']"

_seen_message_ids: set[str] = set()


def _open_target_chat(page: Page, chat_name: str) -> None:
    """Search for and open the configured chat/group by name."""
    page.wait_for_selector(CHAT_SEARCH_SELECTOR, timeout=120_000)
    search_box = page.locator(CHAT_SEARCH_SELECTOR).first
    search_box.click()
    search_box.fill(chat_name)
    page.wait_for_timeout(1500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)


def _extract_new_messages(page: Page, chat_name: str) -> list[IncomingMessage]:
    """Read currently rendered message bubbles and return ones not seen yet."""
    rows = page.locator(MESSAGE_ROW_SELECTOR)
    count = rows.count()
    new_messages: list[IncomingMessage] = []

    # Only look at the tail of the conversation; full history isn't needed.
    start = max(0, count - 30)
    for i in range(start, count):
        row = rows.nth(i)
        row_id = row.get_attribute("data-id") or f"{chat_name}:{i}:{row.inner_text()[:50]}"
        if row_id in _seen_message_ids:
            continue

        text_nodes = row.locator(MESSAGE_TEXT_SELECTOR)
        text = ""
        for j in range(text_nodes.count()):
            text += text_nodes.nth(j).inner_text() + " "
        text = text.strip()
        if not text:
            continue

        sender = None
        try:
            sender_locator = row.locator(SENDER_NAME_SELECTOR).first
            if sender_locator.count() > 0:
                sender = sender_locator.get_attribute("aria-label") or sender_locator.inner_text()
        except Exception:  # noqa: BLE001
            sender = None

        _seen_message_ids.add(row_id)
        new_messages.append(IncomingMessage(chat_name=chat_name, sender=sender, text=text))

    return new_messages


def run_listener(chat_name: str | None = None, poll_interval: float | None = None) -> None:
    """Start the blocking listener loop. Intended to run in its own thread/process."""
    chat_name = chat_name or TARGET_CHAT
    poll_interval = poll_interval or POLL_INTERVAL

    if not chat_name:
        raise ValueError(
            "No target chat configured. Set WHATSAPP_TARGET_CHAT in .env or pass chat_name=."
        )

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=HEADLESS,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(WHATSAPP_URL)

        logger.info("If a QR code is shown, scan it with your phone once. Waiting for login...")
        _open_target_chat(page, chat_name)
        logger.info("Listening for new messages in '%s' every %ss", chat_name, poll_interval)

        try:
            while True:
                try:
                    for msg in _extract_new_messages(page, chat_name):
                        process_message(msg)
                except Exception:  # noqa: BLE001
                    logger.exception("Error while polling for messages; will retry")
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Listener stopped by user")
        finally:
            context.close()


if __name__ == "__main__":
    run_listener()
