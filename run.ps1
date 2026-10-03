# Launches the API/listener and the Streamlit dashboard in separate windows.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\run.ps1

$root = Split-Path -Parent $PSScriptRoot
$venvPython = "$root\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment not found. Run scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "==> Starting API/listener in a new window" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$root`"; & `"$venvPython`" -m app.main"

Write-Host "==> Starting dashboard in a new window" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd `"$root`"; & `"$root\venv\Scripts\streamlit.exe`" run dashboard\dashboard.py"
