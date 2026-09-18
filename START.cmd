@echo off
setlocal
cd /d "%~dp0"
set "DJANGO_DEBUG=1"
set "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1"
set "DATABASE_URL="
set "PYTHONDONTWRITEBYTECODE=1"
set "PIP_CONFIG_FILE=NUL"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
if not exist ".runtime-temp" mkdir ".runtime-temp"
set "TEMP=%CD%\.runtime-temp"
set "TMP=%TEMP%"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:python
python -m venv .venv
if errorlevel 1 goto failed
:install
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] in [(3,12),(3,13),(3,14)], 'Use Python 3.12, 3.13 or 3.14.'"
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --no-cache-dir --no-index --find-links wheelhouse -r requirements-local.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" manage.py migrate --noinput
if errorlevel 1 goto failed
".venv\Scripts\python.exe" manage.py seed_demo
if errorlevel 1 goto failed
echo.
echo Open http://127.0.0.1:8000/ in your browser.
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000 --noreload
goto end
:failed
echo.
echo ServiceHub could not start. Read the error above and see README.md.
:end
pause
