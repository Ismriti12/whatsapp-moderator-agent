[CmdletBinding()]
param()

# One-shot environment setup for Windows:
#   1. Create a virtual environment (venv/)
#   2. Install Python dependencies
#   3. Install the Playwright Chromium browser
#   4. Create a .env file from .env.example if missing
#
# Usage (from the project root):
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==> Creating virtual environment" -ForegroundColor Cyan
python -m venv "$root\venv"

$venvPython = "$root\venv\Scripts\python.exe"

Write-Host "==> Upgrading pip" -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

Write-Host "==> Installing Python dependencies" -ForegroundColor Cyan
& $venvPython -m pip install -r "$root\requirements.txt"

Write-Host "==> Installing Playwright browser (Chromium)" -ForegroundColor Cyan
& $venvPython -m playwright install chromium

$envFile = "$root\.env"
$envExample = "$root\.env.example"
if (-not (Test-Path $envFile)) {
    Write-Host "==> Creating .env from .env.example" -ForegroundColor Cyan
    Copy-Item $envExample $envFile
    Write-Host "    Edit .env and add your GEMINI_API_KEY before running the app." -ForegroundColor Yellow
} else {
    Write-Host "==> .env already exists, leaving it untouched" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Edit .env (set GEMINI_API_KEY and WHATSAPP_TARGET_CHAT)"
Write-Host "  2. venv\Scripts\activate"
Write-Host "  3. python -m app.main          # starts API + (optionally) the listener"
Write-Host "  4. streamlit run dashboard\dashboard.py   # in a second terminal"
