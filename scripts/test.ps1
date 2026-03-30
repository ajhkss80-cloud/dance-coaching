# ==============================================================================
# Dance Coaching Platform - Run All Tests (Windows PowerShell)
# ==============================================================================
# Runs server (vitest) and worker (pytest) test suites.
# Run from the repository root:
#     powershell -ExecutionPolicy Bypass -File scripts\test.ps1
# ==============================================================================

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$serverOk = $true
$workerOk = $true

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Running All Tests"
Write-Host "=====================================" -ForegroundColor Cyan

# ---------- server tests ----------

Write-Host ""
Write-Host "--- Server Tests (vitest) ---" -ForegroundColor Yellow

Push-Location "$RootDir\server"
try {
    npm test
    if ($LASTEXITCODE -ne 0) { throw "Server tests failed" }
    Write-Host "Server tests passed." -ForegroundColor Green
} catch {
    Write-Host "Server tests failed." -ForegroundColor Red
    $serverOk = $false
}
Pop-Location

# ---------- worker tests ----------

Write-Host ""
Write-Host "--- Worker Tests (pytest) ---" -ForegroundColor Yellow

$venvPython = "$RootDir\worker\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Worker virtual environment not found." -ForegroundColor Red
    Write-Host "Run setup first:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1"
    $workerOk = $false
} else {
    Push-Location "$RootDir\worker"
    try {
        & $venvPython -m pytest tests/ -v
        if ($LASTEXITCODE -ne 0) { throw "Worker tests failed" }
        Write-Host "Worker tests passed." -ForegroundColor Green
    } catch {
        Write-Host "Worker tests failed." -ForegroundColor Red
        $workerOk = $false
    }
    Pop-Location
}

# ---------- summary ----------

Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Test Summary"
Write-Host "=====================================" -ForegroundColor Cyan

if ($serverOk) {
    Write-Host "  Server:  PASSED" -ForegroundColor Green
} else {
    Write-Host "  Server:  FAILED" -ForegroundColor Red
}

if ($workerOk) {
    Write-Host "  Worker:  PASSED" -ForegroundColor Green
} else {
    Write-Host "  Worker:  FAILED" -ForegroundColor Red
}

Write-Host ""

if ($serverOk -and $workerOk) {
    Write-Host "All tests passed." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some tests failed." -ForegroundColor Red
    exit 1
}
