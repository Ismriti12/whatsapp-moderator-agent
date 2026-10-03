#!/usr/bin/env bash
# One-shot environment setup for macOS/Linux:
#   1. Create a virtual environment (venv/)
#   2. Install Python dependencies
#   3. Install the Playwright Chromium browser
#   4. Create a .env file from .env.example if missing
#
# Usage (from the project root):
#   bash scripts/setup.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Creating virtual environment"
python3 -m venv "$ROOT/venv"

echo "==> Upgrading pip"
"$ROOT/venv/bin/python" -m pip install --upgrade pip

echo "==> Installing Python dependencies"
"$ROOT/venv/bin/python" -m pip install -r "$ROOT/requirements.txt"

echo "==> Installing Playwright browser (Chromium)"
"$ROOT/venv/bin/python" -m playwright install chromium
# Linux CI/servers may also need OS-level deps; uncomment if browser launch fails:
# "$ROOT/venv/bin/python" -m playwright install-deps chromium

ENV_FILE="$ROOT/.env"
ENV_EXAMPLE="$ROOT/.env.example"
if [ ! -f "$ENV_FILE" ]; then
  echo "==> Creating .env from .env.example"
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "    Edit .env and add your GEMINI_API_KEY before running the app."
else
  echo "==> .env already exists, leaving it untouched"
fi

echo ""
echo "Setup complete!"
echo "Next steps:"
echo "  1. Edit .env (set GEMINI_API_KEY and WHATSAPP_TARGET_CHAT)"
echo "  2. source venv/bin/activate"
echo "  3. python -m app.main                      # starts API + (optionally) the listener"
echo "  4. streamlit run dashboard/dashboard.py    # in a second terminal"
