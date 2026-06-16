@echo off
setlocal EnableDelayedExpansion
title Setup Automatizado CP Fani

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\executar.log"
set "VERSION=V5.9.5.2"

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
    if !errorLevel! NEQ 0 (
        echo [ERRO CRITICO] Nao foi possivel criar diretorio de logs: %LOG_DIR%
        echo [ERRO CRITICO] Execute como Administrador e verifique permissoes.
        pause
        exit /b 1
    )
)

echo. > "%LOG_DIR%\write_test.tmp" 2>nul
if not exist "%LOG_DIR%\write_test.tmp" (
    echo [ERRO CRITICO] Sem permissao de escrita em %LOG_DIR%.
    pause
    exit /b 1
)
del "%LOG_DIR%\write_test.tmp" 2>nul

echo ======================================== > "%LOG_FILE%"
echo EXECUCAO PRINCIPAL - SETUP CP FANI %VERSION% >> "%LOG_FILE%"
echo Data: %date% %time% >> "%LOG_FILE%"
echo Diretorio do Script: %SCRIPT_DIR% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

echo [INFO] Verificando privilegios administrativos...
echo [INFO] Verificando privilegios administrativos... >> "%LOG_FILE%"

net session >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Este script requer privilegios administrativos. >> "%LOG_FILE%"
    echo [ERRO] Execute como Administrador.
    pause
    exit /b 1
)
echo [OK] Administrador confirmado. >> "%LOG_FILE%"
echo [OK] Administrador confirmado.

echo [INFO] Validando arquivos essenciais do projeto...
echo [INFO] Validando arquivos essenciais do projeto... >> "%LOG_FILE%"

if not exist "%SCRIPT_DIR%\gui.py" (
    echo [ERRO] Arquivo gui.py nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo gui.py nao encontrado. Verifique se todos os arquivos do projeto estao presentes.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%\instalar_pre_requisitos.bat" (
    echo [ERRO] Arquivo instalar_pre_requisitos.bat nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo instalar_pre_requisitos.bat nao encontrado.
    pause
    exit /b 1
)

set "GUI_SIZE=0"
for %%F in ("%SCRIPT_DIR%\gui.py") do set "GUI_SIZE=%%~zF"
if !GUI_SIZE! LSS 100 (
    echo [ERRO] gui.py parece estar corrompido ou vazio (!GUI_SIZE! bytes). >> "%LOG_FILE%"
    echo [ERRO] gui.py corrompido. Reinstale o projeto.
    pause
    exit /b 1
)

echo [OK] Arquivos essenciais validados. >> "%LOG_FILE%"
echo [OK] Arquivos essenciais validados.

echo [INFO] Verificando/Instalando pre-requisitos...
echo [INFO] Verificando/Instalando pre-requisitos... >> "%LOG_FILE%"

call "%SCRIPT_DIR%\instalar_pre_requisitos.bat"
set "PRE_REQ_CODE=!errorLevel!"

if !PRE_REQ_CODE! NEQ 0 (
    echo [ERRO] Falha na instalacao dos pre-requisitos. Codigo: !PRE_REQ_CODE! >> "%LOG_FILE%"
    echo [ERRO] Falha na instalacao dos pre-requisitos. Verifique o log: %LOG_FILE%
    pause
    exit /b !PRE_REQ_CODE!
)

echo [OK] Pre-requisitos validados com sucesso. >> "%LOG_FILE%"
echo [OK] Pre-requisitos validados com sucesso.

echo [INFO] Iniciando interface grafica...
echo [INFO] Iniciando interface grafica... >> "%LOG_FILE%"

cd /d "%SCRIPT_DIR%"

echo [INFO] Executando: python -u "%SCRIPT_DIR%\gui.py" >> "%LOG_FILE%"
python -u "%SCRIPT_DIR%\gui.py" >> "%LOG_FILE%" 2>&1
set "GUI_CODE=!errorLevel!"

echo [INFO] GUI encerrada com codigo de saida: !GUI_CODE! >> "%LOG_FILE%"

if !GUI_CODE! NEQ 0 (
    echo [ERRO] A interface grafica falhou. Codigo: !GUI_CODE! >> "%LOG_FILE%"
    echo [ERRO] A interface grafica falhou. Verifique o log: %LOG_FILE%
    pause
) else (
    echo [OK] Setup concluido com sucesso! >> "%LOG_FILE%"
    echo [OK] Setup concluido com sucesso!
)

echo ======================================== >> "%LOG_FILE%"
echo FIM DA EXECUCAO - Codigo: !GUI_CODE! >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

exit /b !GUI_CODE!