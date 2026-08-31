param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 127.0.0.1 --port $BackendPort"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd '$frontend'; npm run dev -- --host 127.0.0.1 --port $FrontendPort"

Write-Host "Backend:  http://127.0.0.1:$BackendPort/docs"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
