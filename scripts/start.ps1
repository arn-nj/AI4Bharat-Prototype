# start.ps1 — Start the FastAPI backend and the React+Vite frontend (local dev)
# -------------------------------------------------------------------------------
# Run from anywhere; the script resolves its own location.
#
# Usage:
#   .\scripts\start.ps1
#
# Optional parameters:
#   -Port         <int>    Backend port           (default: 8000)
#   -NoReload              Disable uvicorn --reload
#   -FrontendPort <int>    Vite dev server port   (default: 5173)

param(
    [int]$Port          = 8000,
    [switch]$NoReload,
    [int]$FrontendPort  = 5173
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve paths relative to this script's location
# ---------------------------------------------------------------------------
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot     = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir   = Join-Path $RepoRoot "src\backend"
$FrontendDir  = Join-Path $RepoRoot "src\frontend"
$VenvPython   = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"

# ---------------------------------------------------------------------------
# Validate that the venv exists
# ---------------------------------------------------------------------------
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at '$VenvPython'. Create it first:  python -m venv .venv"
    exit 1
}

# ---------------------------------------------------------------------------
# Validate required files
# ---------------------------------------------------------------------------
if (-not (Test-Path (Join-Path $BackendDir "main.py"))) {
    Write-Error "Backend main.py not found in '$BackendDir'."
    exit 1
}

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Error "Frontend package.json not found in '$FrontendDir'. Run 'npm install' first."
    exit 1
}

# ---------------------------------------------------------------------------
# Build uvicorn command
# ---------------------------------------------------------------------------
$ReloadFlag   = if ($NoReload) { "" } else { "--reload" }
$UvicornArgs  = "main:app --port $Port $ReloadFlag".Trim() -split "\s+"

# ---------------------------------------------------------------------------
# Launch backend in a new terminal window
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Starting FastAPI backend on port $Port ..."
$BackendCmd = "& '$VenvActivate'; Set-Location '$BackendDir'; uvicorn $($UvicornArgs -join ' ')"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $BackendCmd

# ---------------------------------------------------------------------------
# Brief pause to let the backend bind its port before the browser opens
# ---------------------------------------------------------------------------
Start-Sleep -Seconds 3

# ---------------------------------------------------------------------------
# Launch React/Vite frontend dev server in a new terminal window
# ---------------------------------------------------------------------------
Write-Host "Starting React (Vite) frontend on port $FrontendPort ..."
$FrontendCmd = "Set-Location '$FrontendDir'; `$env:VITE_BACKEND_URL='http://localhost:$Port'; npm run dev -- --port $FrontendPort"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $FrontendCmd

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Both processes are running in separate terminal windows."
Write-Host ""
Write-Host "  Backend  ->  http://localhost:$Port"
Write-Host "  API docs ->  http://localhost:$Port/docs"
Write-Host "  Frontend ->  http://localhost:$FrontendPort"
Write-Host ""
Write-Host "Close the terminal windows to stop the services."
