@echo off
title AR Aging Dashboard — Sandvik
echo ============================================
echo   AR Aging Dashboard Launcher
echo ============================================
echo.

:: Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Please copy .env.example to .env and fill in your Supabase credentials.
    echo.
    pause
    exit /b 1
)

echo Starting Streamlit dashboard...
echo Open your browser at: http://localhost:8501
echo.
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause
