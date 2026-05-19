@echo off
setlocal

REM Stealth Escape AI Game launcher (double-click to run)
REM - Creates a Python 3.11 venv if missing
REM - Installs requirements if needed
REM - Runs the game

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :run

echo [Setup] Creating virtual environment with Python 3.11...
py -3.11 -m venv .venv
if errorlevel 1 goto :pyfail

echo [Setup] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :pipfail

:run
set "ARGS=%*"

REM No args => show in-game GUI menu.

:run_game
echo.
echo [Run] Starting game... %ARGS%
".venv\Scripts\python.exe" -m stealth_escape_ai_game %ARGS%
if errorlevel 1 goto :runfail

goto :eof

:pyfail
echo.
echo ERROR: Could not create venv with Python 3.11.
echo - Install Python 3.11 (or 3.10) and make sure the 'py' launcher exists.
echo - Then re-run this file.
echo.
pause
exit /b 1

:pipfail
echo.
echo ERROR: Dependency install failed.
echo Try running: .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
exit /b 1

:runfail
echo.
echo ERROR: Game crashed. If you enabled debug (F1), check the console output.
echo.
pause
exit /b 1
