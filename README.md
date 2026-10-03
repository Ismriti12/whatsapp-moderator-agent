# WhatsApp Moderator Agent

Monitors a WhatsApp group via WhatsApp Web, classifies incoming messages with
Google Gemini, stores the results in a database, and surfaces them in a
Streamlit dashboard.

```
whatsapp-moderator-agent/
├── app/
│   ├── main.py                # FastAPI app (API + optional listener bootstrap)
│   ├── whatsapp_listener.py   # Playwright-based WhatsApp Web listener
│   ├── moderation_engine.py   # Classification + decision + persistence
│   ├── gemini_classifier.py   # Gemini API wrapper
│   └── database.py            # SQLAlchemy models & session (SQLite by default)
├── dashboard/
│   └── dashboard.py            # Streamlit review dashboard
├── data/                       # SQLite DB + Playwright browser profile (gitignored)
├── scripts/                    # One-command setup/run helpers
├── requirements.txt
└── .env.example
```

## Quick start (new machine, minimal manual setup)

**Prerequisite:** [Python 3.10+](https://www.python.org/downloads/) installed and on PATH. That's it — everything else is automated.

### Windows (PowerShell)

```powershell
git clone <your-repo-url>
cd whatsapp-moderator-agent
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

### macOS / Linux

```bash
git clone <your-repo-url>
cd whatsapp-moderator-agent
bash scripts/setup.sh
```

The setup script will:
1. Create a `venv/` virtual environment
2. Install everything in `requirements.txt`
3. Download the Playwright Chromium browser
4. Copy `.env.example` to `.env` (edit it next)

## Configure

Open `.env` and set at minimum:

- `GEMINI_API_KEY` — get one free at [Google AI Studio](https://aistudio.google.com/apikey)
- `WHATSAPP_TARGET_CHAT` — exact name of the group/chat to monitor

`DATABASE_URL` defaults to a local SQLite file (`data/whatsapp.db`), so no
database server needs to be installed. Switch it to a Postgres URL later if
you want a shared/production database, after installing the optional driver:

```bash
pip install -r requirements-postgres.txt
```

## Run

```powershell
# Windows: starts API/listener + dashboard in separate windows
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

```bash
# macOS/Linux: starts both in the background
bash scripts/run.sh
```

Or run each piece manually in its own terminal (after activating the venv):

```bash
python -m app.main                       # FastAPI + (if AUTO_START_LISTENER=true) the listener
python -m app.whatsapp_listener           # run just the listener on its own
streamlit run dashboard/dashboard.py      # review dashboard at http://localhost:8501
```

The first time the listener runs, a browser window opens WhatsApp Web and
waits for you to scan the QR code with your phone. The logged-in session is
cached in `data/playwright-profile/`, so you only need to scan it once per
machine.

- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

## How it works

1. `whatsapp_listener.py` polls the target chat in a real (Playwright
   automated) Chromium browser and extracts new message text/sender.
2. `moderation_engine.py` deduplicates messages, sends the text to
   `gemini_classifier.py`, and records the category, confidence, and whether
   it should be flagged.
3. Results are saved via `database.py` (SQLite by default) and exposed
   through the FastAPI `/messages` and `/stats` endpoints, and visualized in
   the Streamlit dashboard.

## Notes & limitations

- WhatsApp Web's DOM changes periodically; if message detection stops
  working, update the CSS selectors at the top of
  [whatsapp_listener.py](app/whatsapp_listener.py).
- This project automates your own logged-in WhatsApp Web session — review
  WhatsApp's Terms of Service before using it on a group you don't own/moderate.
- No messages are deleted automatically by default; flagged messages are
  recorded with `action_taken="flagged"` for a human to review in the
  dashboard.
