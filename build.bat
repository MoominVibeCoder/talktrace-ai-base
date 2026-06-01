@echo off
REM TalkTrace AI — Build standalone .exe (one-folder mode)
REM
REM Prerequisites: Python 3.13 venv with all deps installed.
REM Usage:         build.bat            (uses .venv from start.bat)
REM                build.bat /clean     (delete dist + build dirs first)

setlocal

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
cd /d "%PROJECT_ROOT%"

REM --- Parse args ----------------------------------------------------------
set "CLEAN="
if /I "%~1"=="/clean" set "CLEAN=1"
if /I "%~1"=="-clean" set "CLEAN=1"

REM --- Locate venv Python --------------------------------------------------
set "VENV_PY=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [Build] .venv not found. Run start.bat once first to create it.
    goto fail
)
echo [Build] Using Python: %VENV_PY%

REM --- Install PyInstaller if missing --------------------------------------
"%VENV_PY%" -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo [Build] Installing PyInstaller ...
    "%VENV_PY%" -m pip install pyinstaller
    if errorlevel 1 goto fail
)

REM --- Clean previous build -----------------------------------------------
if defined CLEAN (
    echo [Build] Cleaning dist/ and build/ ...
    if exist dist rmdir /s /q dist
    if exist build rmdir /s /q build
)

REM --- Pre-download tiktoken data ------------------------------------------
echo [Build] Pre-caching tiktoken encodings ...
"%VENV_PY%" -c "import tiktoken; tiktoken.get_encoding('cl100k_base'); tiktoken.get_encoding('o200k_base'); print('  tiktoken cache OK')"
if errorlevel 1 echo [Build] Warning: tiktoken pre-cache failed (app will download on first use)

REM --- Run PyInstaller -----------------------------------------------------
echo [Build] Running PyInstaller ...
"%VENV_PY%" -m PyInstaller TalkTraceAI.spec --noconfirm
if errorlevel 1 goto fail

echo.
echo ========================================================
echo [Build] SUCCESS
echo [Build] Output: dist\TalkTraceAI\TalkTraceAI.exe
echo ========================================================
echo.

endlocal
exit /b 0

:fail
echo.
echo [Build] FAILED. See errors above.
pause
endlocal
exit /b 1
