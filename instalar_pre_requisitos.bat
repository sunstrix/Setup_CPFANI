@echo off
setlocal EnableDelayedExpansion
title Instalacao de Pre-Requisitos - Setup CP Fani

:: ============================================================
:: CONFIGURACAO DE LOG
:: ============================================================
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\pre_requisitos.log"

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
)

echo ======================================== > "!LOG_FILE!"
echo PRE-REQUISITOS - SETUP CP FANI V5.9.5.2 >> "!LOG_FILE!"
echo Data: %date% %time% >> "!LOG_FILE!"
echo ======================================== >> "!LOG_FILE!"

echo [INFO] Iniciando instalacao de pre-requisitos...
echo [INFO] Log salvo em: !LOG_FILE!

:: ============================================================
:: 1. VERIFICACAO E INSTALACAO DO PYTHON
:: ============================================================
echo [STEP 1] Verificando Python...
echo [STEP 1] Verificando Python... >> "!LOG_FILE!"

:: Remove alias da Windows Store se existir
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\AppExecutionAliases\python.exe" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\AppExecutionAliases\python3.exe" /f >nul 2>&1

python -c "print('OK')" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Python nao encontrado. Iniciando download...
    echo [INFO] Python nao encontrado. Iniciando download... >> "!LOG_FILE!"
    
    set "PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
    
    echo [INFO] Baixando Python via PowerShell... >> "!LOG_FILE!"
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '!PYTHON_URL!' -OutFile '!PYTHON_INSTALLER!' -UseBasicParsing" >> "!LOG_FILE!" 2>&1
    
    if not exist "!PYTHON_INSTALLER!" (
        echo [ERRO] Falha no download do Python. >> "!LOG_FILE!"
        echo [ERRO] Falha no download do Python.
        pause
        exit /b 1
    )
    
    echo [INFO] Instalando Python (modo silencioso)...
    echo [INFO] Instalando Python (modo silencioso)... >> "!LOG_FILE!"
    "!PYTHON_INSTALLER!" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >> "!LOG_FILE!" 2>&1
    
    if !errorLevel! NEQ 0 (
        echo [ERRO] Falha na instalacao do Python. Codigo: !errorLevel! >> "!LOG_FILE!"
        echo [ERRO] Falha na instalacao do Python.
        pause
        exit /b 1
    )
    
    del "!PYTHON_INSTALLER!" 2>nul
    echo [OK] Python instalado com sucesso. >> "!LOG_FILE!"
    echo [OK] Python instalado com sucesso.
    
    :: Atualiza PATH na sessao atual
    set "PATH=!PATH!;C:\Program Files\Python312\;C:\Program Files\Python312\Scripts\"
) else (
    echo [OK] Python ja esta instalado e funcional. >> "!LOG_FILE!"
    echo [OK] Python ja esta instalado e funcional.
)

:: ============================================================
:: 2. VERIFICACAO E INSTALACAO DO CHOCOLATEY
:: ============================================================
echo [STEP 2] Verificando Chocolatey...
echo [STEP 2] Verificando Chocolatey... >> "!LOG_FILE!"

where choco >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Chocolatey nao encontrado. Instalando...
    echo [INFO] Chocolatey nao encontrado. Instalando... >> "!LOG_FILE!"
    
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://community.chocolatey.org/install.ps1' -OutFile '$env:TEMP\choco_install.ps1'; & '$env:TEMP\choco_install.ps1'" >> "!LOG_FILE!" 2>&1
    
    if !errorLevel! NEQ 0 (
        echo [ERRO] Falha na instalacao do Chocolatey. >> "!LOG_FILE!"
        echo [ERRO] Falha na instalacao do Chocolatey.
        pause
        exit /b 1
    )
    
    set "PATH=!PATH!;%ALLUSERSPROFILE%\chocolatey\bin"
    echo [OK] Chocolatey instalado com sucesso. >> "!LOG_FILE!"
    echo [OK] Chocolatey instalado com sucesso.
) else (
    echo [OK] Chocolatey ja esta instalado. >> "!LOG_FILE!"
    echo [OK] Chocolatey ja esta instalado.
)

:: ============================================================
:: 3. INSTALACAO DE DEPENDENCIAS PIP
:: ============================================================
echo [STEP 3] Instalando dependencias PIP...
echo [STEP 3] Instalando dependencias PIP... >> "!LOG_FILE!"

echo [INFO] Atualizando pip...
python -m pip install --upgrade pip >> "!LOG_FILE!" 2>&1

echo [INFO] Instalando customtkinter...
python -m pip install customtkinter >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha ao instalar customtkinter. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [INFO] Instalando psutil...
python -m pip install psutil >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha ao instalar psutil. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [INFO] Instalando pillow...
python -m pip install pillow >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha ao instalar pillow. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [OK] Todas as dependencias PIP instaladas com sucesso. >> "!LOG_FILE!"
echo [OK] Todas as dependencias PIP instaladas com sucesso.

:: ============================================================
:: FINALIZACAO
:: ============================================================
echo ======================================== >> "!LOG_FILE!"
echo PRE-REQUISITOS CONCLUIDOS COM SUCESSO >> "!LOG_FILE!"
echo ======================================== >> "!LOG_FILE!"

echo.
echo [OK] Pre-requisitos instalados com sucesso!
echo [OK] O sistema esta pronto para executar o Setup.
timeout /t 3 /nobreak >nul
exit /b 0