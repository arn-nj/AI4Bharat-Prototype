# start.ps1 — Start the FastAPI backend and the Streamlit frontend
# ----------------------------------------------------------------
# Run from anywhere; the script resolves its own location.
#
# Usage:
#   .\src\api_integration\start.ps1
#
# Optional parameters:
#   -Port      <int>    Backend port        (default: 8000)
#   -NoReload           Disable uvicorn --reload
#   -FrontendPort <int> Streamlit server port (default: 8501)

param(
    [int]$Port          = 8000,
    [switch]$NoReload,
    [int]$FrontendPort  = 8501
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Resolve paths relative to this script's location
# ---------------------------------------------------------------------------
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot    = Resolve-Path (Join-Path (Join-Path $ScriptDir "..") "..")
$BackendDir  = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"
$VenvPython  = Join-Path $RepoRoot ".venv\Scripts\python.exe"
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

if (-not (Test-Path (Join-Path $FrontendDir "app.py"))) {
    Write-Error "Frontend app.py not found in '$FrontendDir'."
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
# Launch Streamlit frontend in a new terminal window
# ---------------------------------------------------------------------------
Write-Host "Starting Streamlit frontend on port $FrontendPort ..."
$StreamlitArgs = "run app.py --server.port $FrontendPort"
$FrontendCmd   = "& '$VenvActivate'; Set-Location '$FrontendDir'; `$env:BACKEND_URL='http://localhost:$Port'; streamlit $StreamlitArgs"
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
