@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set "PIP_CACHE_DIR=%CD%\.pip-cache"
set "TEMP=%CD%\temp"
set "TMP=%CD%\temp"
if not exist "%TEMP%" mkdir "%TEMP%"
echo WMK VISION - Corrigindo dependencias e registrando log...
if not exist .venv\Scripts\python.exe (
 echo ERRO: Ambiente ausente. Execute INSTALAR.cmd.
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt > logs\correcao-dependencias.log 2>&1
if errorlevel 1 (
 echo ERRO: instalacao falhou. Veja logs\correcao-dependencias.log
 type logs\correcao-dependencias.log
 pause
 exit /b 1
)
.venv\Scripts\python.exe -c "import lap, cv2, supervision, ultralytics; print('DEPENDENCIAS OK | lap:',lap.__version__)" >> logs\correcao-dependencias.log 2>&1
if errorlevel 1 (
 echo ERRO: faltou alguma dependencia. Veja logs\correcao-dependencias.log
 type logs\correcao-dependencias.log
 pause
 exit /b 1
)
echo Dependencias corrigidas. Reinicie INICIAR.cmd.
pause
