@echo off
setlocal
cd /d "%~dp0"
set "PIP_CACHE_DIR=%CD%\.pip-cache"
set "TEMP=%CD%\temp"
set "TMP=%CD%\temp"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist logs mkdir logs
set "PYTHON=py -3.13"
%PYTHON% --version >nul 2>&1
if errorlevel 1 set "PYTHON=py -3.12"
%PYTHON% --version >nul 2>&1
if errorlevel 1 (echo ERRO: Python 3.12 ou 3.13 nao encontrado. & pause & exit /b 1)
if not exist .venv\Scripts\python.exe %PYTHON% -m venv .venv
if not exist .venv\Scripts\python.exe (echo ERRO: Nao foi possivel criar ambiente virtual. & pause & exit /b 1)
echo Instalando dependencias. Log em logs\instalacao.log
.venv\Scripts\python.exe -m pip install -r requirements.txt > logs\instalacao.log 2>&1
if errorlevel 1 (echo ERRO NA INSTALACAO. Abra logs\instalacao.log & pause & exit /b 1)
echo Instalacao concluida.
call INICIAR.cmd
