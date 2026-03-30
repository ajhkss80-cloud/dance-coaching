# ==============================================================================
# Dance Coaching Platform - Environment Setup (Windows PowerShell)
# ==============================================================================
# Checks prerequisites, installs dependencies, and prepares the project for
# local development.  Run from the repository root:
#     powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$errors = 0

function Write-Ok($msg)   { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg)  { Write-Host "[FAIL]  $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Dance Coaching Platform Setup"
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# ---------- prerequisite checks ----------

# Node.js >= 20
try {
    $nodeVer = (node -v) -replace '^v', ''
    $nodeMajor = [int]($nodeVer.Split('.')[0])
    if ($nodeMajor -ge 20) {
        Write-Ok "Node.js $nodeVer"
    } else {
        Write-Fail "Node.js $nodeVer found, but >= 20 required"
        Write-Host "       Install from https://nodejs.org/ or use nvm-windows"
        $errors++
    }
} catch {
    Write-Fail "Node.js not found"
    Write-Host "       Install from https://nodejs.org/ or use nvm-windows"
    $errors++
}

# Python >= 3.10
try {
    $pyVer = (python --version 2>&1) -replace 'Python ', ''
    $pyParts = $pyVer.Split('.')
    $pyMajor = [int]$pyParts[0]
    $pyMinor = [int]$pyParts[1]
    if ($pyMajor -ge 3 -and $pyMinor -ge 10) {
        Write-Ok "Python $pyVer"
    } else {
        Write-Fail "Python $pyVer found, but >= 3.10 required"
        Write-Host "       Install from https://www.python.org/downloads/"
        $errors++
    }
} catch {
    Write-Fail "Python not found"
    Write-Host "       Install from https://www.python.org/downloads/"
    Write-Host "       Make sure to check 'Add Python to PATH' during installation"
    $errors++
}

# Redis
try {
    $null = Get-Command redis-cli -ErrorAction Stop
    Write-Ok "Redis CLI found"
} catch {
    Write-Fail "Redis not found"
    Write-Host "       Option 1: Install Memurai (Redis-compatible for Windows): https://www.memurai.com/"
    Write-Host "       Option 2: Use Docker:  docker run -d -p 6379:6379 redis:7-alpine"
    Write-Host "       Option 3: Use WSL:     wsl -- sudo apt install redis-server"
    $errors++
}

# ffmpeg
try {
    $ffmpegOut = (ffmpeg -version 2>&1) | Select-Object -First 1
    $ffmpegVer = ($ffmpegOut -split ' ')[2]
    Write-Ok "ffmpeg $ffmpegVer"
} catch {
    Write-Fail "ffmpeg not found"
    Write-Host "       Install from https://ffmpeg.org/download.html"
    Write-Host "       Or via Chocolatey:  choco install ffmpeg"
    Write-Host "       Or via Scoop:       scoop install ffmpeg"
    $errors++
}

# Bail if prerequisites missing
if ($errors -gt 0) {
    Write-Host ""
    Write-Fail "$errors prerequisite(s) missing.  Fix the issues above and re-run."
    exit 1
}

Write-Host ""
Write-Host "All prerequisites satisfied." -ForegroundColor Green
Write-Host ""

# ---------- server dependencies ----------

Write-Host "--- Installing server dependencies ---"
Push-Location "$RootDir\server"
npm install
Pop-Location
Write-Ok "Server npm packages installed"

# ---------- worker dependencies ----------

Write-Host ""
Write-Host "--- Setting up worker Python environment ---"
Push-Location "$RootDir\worker"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Ok "Virtual environment created at worker\.venv"
} else {
    Write-Warn "Virtual environment already exists, skipping creation"
}

& .venv\Scripts\pip install --upgrade pip --quiet
& .venv\Scripts\pip install -r requirements.txt --quiet
Write-Ok "Worker Python packages installed"

# Dev dependencies
& .venv\Scripts\pip install pytest pytest-asyncio pytest-cov --quiet
Write-Ok "Worker dev dependencies installed"

Pop-Location

# ---------- storage directories ----------

Write-Host ""
Write-Host "--- Ensuring storage directories exist ---"
$storageDirs = @("$RootDir\storage\uploads", "$RootDir\storage\outputs", "$RootDir\storage\temp")
foreach ($dir in $storageDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
# Create .gitkeep files
foreach ($dir in $storageDirs) {
    $gitkeep = Join-Path $dir ".gitkeep"
    if (-not (Test-Path $gitkeep)) {
        New-Item -ItemType File -Path $gitkeep -Force | Out-Null
    }
}
Write-Ok "Storage directories ready"

# ---------- .env file ----------

if (-not (Test-Path "$RootDir\.env")) {
    Copy-Item "$RootDir\.env.example" "$RootDir\.env"
    Write-Ok "Created .env from .env.example"
    Write-Warn "Edit .env to add your API keys before running the platform"
} else {
    Write-Warn ".env already exists, not overwriting"
}

# ---------- done ----------

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit .env with your configuration (KLING_API_KEY, etc.)"
Write-Host "  2. Start Redis (Docker recommended on Windows):"
Write-Host "       docker run -d -p 6379:6379 redis:7-alpine"
Write-Host "  3. Start the server:  cd server && npm run dev"
Write-Host "  4. Start the worker:  cd worker && .venv\Scripts\python -m src.main"
Write-Host ""
Write-Host "For GPU setup (MimicMotion), run:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\setup-mimicmotion.ps1"
Write-Host ""
