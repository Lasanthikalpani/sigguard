@echo off
echo ============================================================
echo SigGuard Startup Script
echo ============================================================
echo.

echo [1/3] Starting Docker services...
docker compose -f docker\docker-compose.yml up -d
timeout /t 15 /nobreak

echo.
echo [2/3] Starting API server...
start "SigGuard API" cmd /k "conda activate sigguard && cd /d %CD% && uvicorn src.api.main:app --reload"

timeout /t 5 /nobreak

echo.
echo [3/3] Starting Streamlit frontend...
start "SigGuard Frontend" cmd /k "conda activate sigguard-frontend && cd /d %CD% && streamlit run frontend/app.py"

echo.
echo ============================================================
echo SigGuard is starting!
echo ============================================================
echo.
echo API:      http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:8501
echo.
echo Press any key to exit this window (services will continue running)
pause > nul
