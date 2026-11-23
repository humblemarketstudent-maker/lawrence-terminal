@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python was not found. Install Python 3.12 or 3.13 from https://www.python.org/downloads/
    echo On the first installer screen, tick "Add python.exe to PATH", then run this file again.
    pause
    exit /b 1
  )
  set "PY=python"
) else (
  set "PY=py -3"
)

where npm >nul 2>&1
if errorlevel 1 (
  echo Node.js was not found. Install Node.js 22 LTS from https://nodejs.org/ then run this file again.
  pause
  exit /b 1
)

if not exist ".env" copy /Y ".env.example" ".env" >nul

if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating the Python environment. This can take a few minutes the first time...
  %PY% -m venv backend\.venv
  if errorlevel 1 (
    echo Could not create the Python virtual environment.
    pause
    exit /b 1
  )
)

echo Installing API packages...
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo Package install failed. If curl_cffi or lxml is mentioned, install Docker Desktop and run: docker compose up --build
  pause
  exit /b 1
)

echo Installing the desk packages...
pushd frontend
call npm install
if errorlevel 1 (
  popd
  echo npm install failed. Check that Node.js 22 LTS is installed.
  pause
  exit /b 1
)
popd

echo Starting the API and the desk. Leave the two new windows open.
start "APEX API" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8741"
start "APEX desk" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo Waiting for the desk to come up...
set /a n=0
:wait
set /a n+=1
if %n% geq 40 goto open
curl -s -o nul http://127.0.0.1:4317/ && goto open
timeout /t 1 /nobreak >nul
goto wait

:open
start http://127.0.0.1:4317/
echo Opened http://127.0.0.1:4317/ in your default browser. If Chrome did not open, paste that address into Chrome.
pause
