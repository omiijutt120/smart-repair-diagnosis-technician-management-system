@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m flask --app app db upgrade
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m flask --app app seed
if errorlevel 1 goto failed
echo.
echo Smart Repair is starting at http://127.0.0.1:5000
echo Login: admin@smartrepair.test / RepairDemo123!
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" app.py
goto done
:failed
echo.
echo Setup failed. Check the error above and see README.md.
pause
:done
endlocal
