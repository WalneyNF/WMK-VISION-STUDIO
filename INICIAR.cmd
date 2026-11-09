@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Ambiente ausente. Execute INSTALAR.cmd primeiro. & pause & exit /b 1)
echo.
echo WMK VISION STUDIO - http://127.0.0.1:8767
start "" "http://127.0.0.1:8767"
.venv\Scripts\python.exe app.py
if errorlevel 1 echo [ERRO] Confira a mensagem acima.
pause
