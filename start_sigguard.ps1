# SigGuard Startup Script (PowerShell)
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SigGuard Startup Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$sigguardPath = "C:\Users\lasan\Desktop\research\reserch_july_9\sigguard"

# Step 1: Check Docker Desktop
Write-Host "[1/3] Checking Docker Desktop..." -ForegroundColor Yellow
$dockerRunning = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue

if (-not $dockerRunning) {
    Write-Host "  Docker Desktop is not running. Starting it..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "  Waiting 90 seconds for Docker to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 90
} else {
    Write-Host "  Docker Desktop is already running." -ForegroundColor Green
}
Write-Host ""

# Step 2: Start API server
Write-Host "[2/3] Starting API server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$sigguardPath'; conda activate sigguard; python -m uvicorn src.api.main:app --reload"
Write-Host "  Waiting 10 seconds for API to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host ""

# Step 3: Start Streamlit frontend
Write-Host "[3/3] Starting Streamlit frontend..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$sigguardPath'; conda activate sigguard-frontend; python -m streamlit run frontend/app.py"
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "SigGuard is starting!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "API:      http://localhost:8000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "Frontend: http://localhost:8501" -ForegroundColor White
Write-Host ""
Write-Host "Please wait 30-60 seconds for all services to be ready." -ForegroundColor Yellow
Write-Host ""

Read-Host "Press Enter to exit"