@echo off
setlocal
cd /d "%~dp0"
echo Britsmaid local website and admin
echo Website: http://127.0.0.1:8000/
echo Admin:   http://127.0.0.1:8000/admin
echo Keep this window open while using the website.
echo.
set "BRITSMAID_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BRITSMAID_PYTHON%" (
    "%BRITSMAID_PYTHON%" app.py
) else (
    python app.py
)
if errorlevel 1 (
    echo.
    echo The server could not start. Share the error shown above for help.
    pause
)
endlocal
