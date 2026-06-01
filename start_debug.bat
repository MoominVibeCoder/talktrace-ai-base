@echo off
REM TalkTrace AI base -- DEBUG launcher.
REM
REM Same as start.bat, but:
REM   - the console window stays in the foreground (no self-minimize)
REM   - pip runs with -v (verbose) and writes a full log to pip-debug.log
REM   - pip prefers binary wheels (no surprise source builds)
REM
REM Use this when start.bat appears to hang during dependency installation.
REM Once everything works, switch back to start.bat.

setlocal

set "REINSTALL="
set "NOWINDOW="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="/reinstall" goto set_reinstall
if /I "%~1"=="-reinstall" goto set_reinstall
if /I "%~1"=="/nowindow"  goto set_nowindow
if /I "%~1"=="-nowindow"  goto set_nowindow
echo Unknown argument: %~1
goto fail
:set_reinstall
set "REINSTALL=1"
shift
goto parse_args
:set_nowindow
set "NOWINDOW=1"
shift
goto parse_args
:args_done

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
cd /d "%PROJECT_ROOT%"
if errorlevel 1 goto fail

echo [TalkTrace DEBUG] Project root: %PROJECT_ROOT%
echo [TalkTrace DEBUG] pip log will be written to: %PROJECT_ROOT%\pip-debug.log
echo.

REM --- 1. Locate Python ---------------------------------------------------
set "PY_CMD="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"

if not defined PY_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
    python3 --version >nul 2>nul
    if not errorlevel 1 set "PY_CMD=python3"
)

if not defined PY_CMD (
    echo [TalkTrace DEBUG] Python 3 not found. Install from https://www.python.org/downloads/ and re-run.
    goto fail
)
echo [TalkTrace DEBUG] Using Python launcher: %PY_CMD%

REM --- 1b. Python version check (3.12+) -----------------------------------
REM On Python 3.14+, pywebview/pythonnet are not installed (no 3.14 wheels yet);
REM the app falls back to opening in the default browser.
set "PY_VERSION="
for /f "tokens=2" %%V in ('%PY_CMD% --version 2^>^&1') do set "PY_VERSION=%%V"
echo [TalkTrace DEBUG] Detected Python version: %PY_VERSION%
%PY_CMD% -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,12) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [TalkTrace DEBUG] Python %PY_VERSION% is too old.
    echo [TalkTrace DEBUG] Minimum supported: Python 3.12. Install from https://www.python.org/downloads/ and re-run.
    goto fail
)
%PY_CMD% -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,14) else 1)" >nul 2>nul
if not errorlevel 1 (
    echo [TalkTrace DEBUG] Note: on Python %PY_VERSION%, the embedded desktop window
    echo [TalkTrace DEBUG] is unavailable ^(pywebview/pythonnet have no 3.14 wheels yet^).
    echo [TalkTrace DEBUG] The app will open in your default browser.
)

REM --- 2. Virtual environment ---------------------------------------------
set "VENV_DIR=%PROJECT_ROOT%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not defined REINSTALL goto skip_reinstall
if not exist "%VENV_DIR%"  goto skip_reinstall
echo [TalkTrace DEBUG] Removing existing venv ^(/reinstall^)...
rmdir /s /q "%VENV_DIR%"
:skip_reinstall

if not exist "%VENV_PY%" (
    echo [TalkTrace DEBUG] Creating virtual environment in .venv ...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto venv_fail
)
goto venv_ok
:venv_fail
echo [TalkTrace DEBUG] venv creation failed
goto fail
:venv_ok

REM --- 3. Install dependencies (verbose) ----------------------------------
set "REQ_FILE=%PROJECT_ROOT%\requirements.txt"
if not exist "%REQ_FILE%" (
    echo [TalkTrace DEBUG] requirements.txt not found at %REQ_FILE%
    goto fail
)

set "PIP_LOG=%PROJECT_ROOT%\pip-debug.log"

echo [TalkTrace DEBUG] Upgrading pip ...
"%VENV_PY%" -m pip install --upgrade pip --log "%PIP_LOG%"
if errorlevel 1 goto pip_fail

echo.
echo [TalkTrace DEBUG] Installing dependencies (verbose, prefer-binary) ...
echo [TalkTrace DEBUG] If this hangs, the active wheel name shows up in pip-debug.log.
echo.
"%VENV_PY%" -m pip install -v --prefer-binary --progress-bar on --log "%PIP_LOG%" -r "%REQ_FILE%"
if errorlevel 1 goto pip_fail

REM Stamp file so a subsequent start.bat run skips reinstall.
set "STAMP_FILE=%VENV_DIR%\.requirements.sha256"
set "CURRENT_HASH="
REM See start.bat for why skip=1 is wrong here — the hex IS the only surviving line.
for /f "tokens=* usebackq" %%H in (`certutil -hashfile "%REQ_FILE%" SHA256 ^| findstr /v ":"`) do (
    if not defined CURRENT_HASH set "CURRENT_HASH=%%H"
)
set "CURRENT_HASH=%CURRENT_HASH: =%"
if defined CURRENT_HASH (
    >"%STAMP_FILE%" echo %CURRENT_HASH%
) else (
    echo [TalkTrace DEBUG] Could not compute requirements hash; stamp file not written.
)
goto deps_ok
:pip_fail
echo.
echo [TalkTrace DEBUG] pip install failed. Last 40 lines of pip-debug.log:
echo --------------------------------------------------------------------
powershell -NoProfile -Command "Get-Content -Path '%PIP_LOG%' -Tail 40"
echo --------------------------------------------------------------------
goto fail
:deps_ok

REM --- 4. Launch the app --------------------------------------------------
echo.
echo [TalkTrace DEBUG] Starting Shiny app ... press Ctrl+C to stop.
echo.

if defined NOWINDOW goto launch_nowindow
"%VENV_PY%" -c "from talktrace_ai.app import main; main()"
goto launch_done
:launch_nowindow
"%VENV_PY%" -c "from talktrace_ai.app import main; main(open_window=False)"
:launch_done
if errorlevel 1 goto fail

endlocal
exit /b 0

:fail
echo.
echo [TalkTrace DEBUG] Startup failed. Press any key to close this window.
pause >nul
endlocal
exit /b 1
