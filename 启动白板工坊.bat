@echo off
setlocal
cd /d "%~dp0"

if not exist "start-webapp.ps1" (
    echo Startup file start-webapp.ps1 was not found.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Python environment was not found. Please finish installation first.
    pause
    exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo Node.js and npm were not found. Please install Node.js first.
    pause
    exit /b 1
)

if not exist "web\node_modules" (
    echo Frontend dependencies were not found. Run npm ci in the web folder first.
    pause
    exit /b 1
)

if not exist "video_renderer\node_modules" (
    echo Renderer dependencies were not found. Run npm ci in the video_renderer folder first.
    pause
    exit /b 1
)

echo Starting the whiteboard video workshop...
".venv\Scripts\python.exe" "%~dp0start-webapp.py"
if errorlevel 1 (
    echo.
    echo Startup failed. See .webapp\backend-error.log or .webapp\frontend-error.log for details.
    pause
    exit /b 1
)

exit /b 0
