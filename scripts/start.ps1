# start.ps1 — Start FastAPI backend + React/Vite frontend (local dev)
# Run from anywhere; the script resolves its own location.
#
# Usage:
#   .\scripts\start.ps1
#
# Optional parameters:
#   -Port         <int>    Backend port        (default: 8000)
#   -NoReload              Disable uvicorn --reload
#   -FrontendPort <int>    Vite dev port       (default: 5173)

param(
    [int]$Port          = 8000,
    [switch]$NoReload,
    [int]$FrontendPort  = 5173
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot     = Resolve-Path (Join-Path $ScriptDir "..")
$FrontendDir  = Join-Path $RepoRoot "src\frontend"
$VenvPython   = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at '$VenvPython'. Create it: python -m venv .venv"
    exit 1
}

# Launch backend from REPO ROOT using package path src.backend.main:app
$ReloadFlag  = if ($NoReload) { "" } else { "--reload" }
$UvicornCmd  = "src.backend.main:app --port $Port $ReloadFlag".Trim()
$BackendCmd  = "& '$VenvActivate'; Set-Location '$RepoRoot'; uvicorn $UvicornCmd"
Write-Host "Starting FastAPI backend on port $Port ..."
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $BackendCmd

Start-Sleep -Seconds 3

# Launch React/Vite frontend
$FrontendCmd = "Set-Location '$FrontendDir'; `$env:VITE_BACKEND_URL='http://localhost:$Port'; npm run dev -- --port $FrontendPort"
Write-Host "Starting React (Vite) frontend on port $FrontendPort ..."
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $FrontendCmd

Write-Host ""
Write-Host "  Backend  ->  http://localhost:$Port"
Write-Host "  API docs ->  http://localhost:$Port/docs"
Write-Host "  Frontend ->  http://localhost:$FrontendPort"
