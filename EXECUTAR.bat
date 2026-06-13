@echo off
setlocal EnableDelayedExpansion
title Setup Automatizado CP Fani

:: ============================================================
:: CONFIGURACAO DE LOG
:: ============================================================
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\executar.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

echo ======================================== > "!LOG_FILE!"
echo EXECUCAO PRINCIPAL - SETUP CP FANI V5.9.5.2 >> "!LOG_FILE!"
echo Data: %date% %time% >> "!LOG_FILE!"
echo ======================================== >> "!LOG_FILE!"

:: ============================================================
:: 1. VERIFICACAO DE ADMINISTRADOR
:: ============================================================
echo [INFO] Verificando privilegios administrativos...
echo [INFO] Verificando privilegios administrativos... >> "!LOG_FILE!"

whoami /groups | findstr /i "S-1-5-32-544" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Este script requer privilegios administrativos. >> "!LOG_FILE!"
    echo [ERRO] Execute como Administrador.
    pause
    exit /b 1
)
echo [OK] Administrador confirmado. >> "!LOG_FILE!"
echo [OK] Administrador confirmado.

:: ============================================================
:: 2. EXECUCAO DO SCRIPT DE PRE-REQUISITOS
:: ============================================================
echo [INFO] Verificando/Instalando pre-requisitos...
echo [INFO] Verificando/Instalando pre-requisitos... >> "!LOG_FILE!"

:: Chama o script de pre-requisitos. Se ele falhar, o script principal para.
call "%~dp0instalar_pre_requisitos.bat"
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha na instalacao dos pre-requisitos. Verifique o log. >> "!LOG_FILE!"
    echo [ERRO] Falha na instalacao dos pre-requisitos.
    pause
    exit /b 1
)

echo [OK] Pre-requisitos validados com sucesso. >> "!LOG_FILE!"
echo [OK] Pre-requisitos validados com sucesso.

:: ============================================================
:: 3. INICIALIZACAO DA GUI PYTHON
:: ============================================================
echo [INFO] Iniciando interface grafica...
echo [INFO] Iniciando interface grafica... >> "!LOG_FILE!"

cd /d "%~dp0"

if not exist "%~dp0gui.py" (
    echo [ERRO] Arquivo gui.py nao encontrado em %~dp0 >> "!LOG_FILE!"
    echo [ERRO] Arquivo gui.py nao encontrado.
    pause
    exit /b 1
)

echo [INFO] Executando python -u gui.py... >> "!LOG_FILE!"
python -u "%~dp0gui.py" >> "!LOG_FILE!" 2>&1
set "GUI_CODE=!errorLevel!"

echo [INFO] GUI encerrada com codigo: !GUI_CODE! >> "!LOG_FILE!"

if !GUI_CODE! NEQ 0 (
    echo [ERRO] A interface grafica falhou. Verifique o log: !LOG_FILE! >> "!LOG_FILE!"
    echo [ERRO] A interface grafica falhou. Verifique o log.
    pause
) else (
    echo [OK] Setup concluido com sucesso! >> "!LOG_FILE!"
    echo [OK] Setup concluido com sucesso!
)

exit /b !GUI_CODE!