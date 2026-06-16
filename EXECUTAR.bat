@echo off
setlocal EnableDelayedExpansion
title Setup Automatizado CP Fani

REM ============================================================
REM CONFIGURACAO INICIAL E VALIDACOES
REM ============================================================

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\executar.log"
set "VERSION=V5.9.5.2"
set "PYTHON_TIMEOUT=300"
set "MAX_RETRIES=2"

REM ============================================================
REM FUNCAO: OBTER DATA/HORA NO FORMATO ISO (USANDO POWERSHELL)
REM ============================================================
for /f "usebackq delims=" %%a in (`powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) do set "CURRENT_DATETIME=%%a"
set "mydate=%CURRENT_DATETIME:~0,10%"
set "mytime=%CURRENT_DATETIME:~11,8%"

REM ============================================================
REM CRIAR DIRETORIO DE LOGS COM VALIDACAO
REM ============================================================
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%" 2>nul
    if !errorLevel! NEQ 0 (
        echo [ERRO CRITICO] Nao foi possivel criar diretorio de logs: %LOG_DIR%
        echo [ERRO CRITICO] Execute como Administrador e verifique permissoes.
        pause
        exit /b 1
    )
)

REM Teste de escrita no diretorio de logs
echo. > "%LOG_DIR%\write_test.tmp" 2>nul
if not exist "%LOG_DIR%\write_test.tmp" (
    echo [ERRO CRITICO] Sem permissao de escrita em %LOG_DIR%.
    echo [ERRO CRITICO] Verifique permissoes ou execute como Administrador.
    pause
    exit /b 1
)
del "%LOG_DIR%\write_test.tmp" 2>nul

REM ============================================================
REM INICIALIZAR LOG FILE
REM ============================================================
echo ======================================== > "%LOG_FILE%"
echo EXECUCAO PRINCIPAL - SETUP CP FANI %VERSION% >> "%LOG_FILE%"
echo Data/Hora: %mydate% %mytime% >> "%LOG_FILE%"
echo Diretorio do Script: %SCRIPT_DIR% >> "%LOG_FILE%"
echo Versao Batch: Windows %OS% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

REM ============================================================
REM VERIFICAR PRIVILEGIOS ADMINISTRATIVOS
REM ============================================================
echo [INFO] Verificando privilegios administrativos...
echo [INFO] Verificando privilegios administrativos... >> "%LOG_FILE%"

net session >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Este script REQUER privilegios administrativos (Admin). >> "%LOG_FILE%"
    echo [ERRO] Este script REQUER privilegios administrativos (Admin).
    echo [DICA] Clique com botao direito ^> "Executar como administrador"
    pause
    exit /b 1
)
echo [OK] Administrador confirmado. >> "%LOG_FILE%"
echo [OK] Administrador confirmado.

REM ============================================================
REM VERIFICAR SE PYTHON ESTA INSTALADO E VALIDAR VERSAO >= 3.8
REM ============================================================
echo [INFO] Verificando instalacao do Python... >> "%LOG_FILE%"
python --version >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Python nao encontrado no PATH. >> "%LOG_FILE%"
    echo [ERRO] Python nao encontrado no PATH.
    echo [DICA] Instale Python 3.8+ de https://www.python.org
    echo [DICA] Certifique-se de marcar "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

REM Capturar versão e verificar se >= 3.8
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo [OK] Python encontrado: %PYTHON_VERSION% >> "%LOG_FILE%"
echo [OK] Python encontrado: %PYTHON_VERSION%

REM Validar versão minima (3.8)
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Versao do Python e inferior a 3.8 (encontrado: %PYTHON_VERSION%). >> "%LOG_FILE%"
    echo [ERRO] Versao do Python e inferior a 3.8 (encontrado: %PYTHON_VERSION%).
    echo [DICA] Atualize o Python para a versao 3.8 ou superior.
    pause
    exit /b 1
)
echo [OK] Versao do Python >= 3.8 confirmada. >> "%LOG_FILE%"

REM ============================================================
REM VALIDAR ARQUIVOS ESSENCIAIS DO PROJETO
REM ============================================================
echo [INFO] Validando arquivos essenciais do projeto... >> "%LOG_FILE%"
echo [INFO] Validando arquivos essenciais do projeto...

set "VALIDATION_FAILED=0"

if not exist "%SCRIPT_DIR%\gui.py" (
    echo [ERRO] Arquivo gui.py nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo gui.py nao encontrado.
    set "VALIDATION_FAILED=1"
)

if not exist "%SCRIPT_DIR%\instalar_pre_requisitos.bat" (
    echo [ERRO] Arquivo instalar_pre_requisitos.bat nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo instalar_pre_requisitos.bat nao encontrado.
    set "VALIDATION_FAILED=1"
)

if not exist "%SCRIPT_DIR%\mod_config.py" (
    echo [ERRO] Arquivo mod_config.py nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo mod_config.py nao encontrado.
    set "VALIDATION_FAILED=1"
)

REM Nova validação: mod_instalar.py
if not exist "%SCRIPT_DIR%\mod_instalar.py" (
    echo [ERRO] Arquivo mod_instalar.py nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo mod_instalar.py nao encontrado.
    set "VALIDATION_FAILED=1"
)

REM Nova validação: settings.json
if not exist "%SCRIPT_DIR%\settings.json" (
    echo [ERRO] Arquivo settings.json nao encontrado em %SCRIPT_DIR% >> "%LOG_FILE%"
    echo [ERRO] Arquivo settings.json nao encontrado.
    set "VALIDATION_FAILED=1"
)

REM Verificar tamanho do gui.py
set "GUI_SIZE=0"
for %%F in ("%SCRIPT_DIR%\gui.py") do set "GUI_SIZE=%%~zF"
if !GUI_SIZE! LSS 500 (
    echo [ERRO] gui.py parece estar corrompido ou vazio (!GUI_SIZE! bytes). >> "%LOG_FILE%"
    echo [ERRO] gui.py corrompido ou muito pequeno (!GUI_SIZE! bytes).
    set "VALIDATION_FAILED=1"
)

if !VALIDATION_FAILED! NEQ 0 (
    echo [ERRO] Validacao de arquivos FALHOU. >> "%LOG_FILE%"
    echo [ERRO] Reinstale o projeto completamente.
    pause
    exit /b 1
)

echo [OK] Arquivos essenciais validados (gui.py: !GUI_SIZE! bytes). >> "%LOG_FILE%"
echo [OK] Arquivos essenciais validados.

REM ============================================================
REM VERIFICAR/INSTALAR PRE-REQUISITOS
REM ============================================================
echo [INFO] Verificando/Instalando pre-requisitos... >> "%LOG_FILE%"
echo [INFO] Verificando/Instalando pre-requisitos...

call "%SCRIPT_DIR%\instalar_pre_requisitos.bat"
set "PRE_REQ_CODE=!errorLevel!"

if !PRE_REQ_CODE! NEQ 0 (
    echo [ERRO] Falha na instalacao dos pre-requisitos. Codigo: !PRE_REQ_CODE! >> "%LOG_FILE%"
    echo [ERRO] Falha na instalacao dos pre-requisitos. Codigo: !PRE_REQ_CODE!
    echo [DICA] Verifique o log: %LOG_FILE%
    pause
    exit /b !PRE_REQ_CODE!
)

echo [OK] Pre-requisitos validados com sucesso. >> "%LOG_FILE%"
echo [OK] Pre-requisitos validados com sucesso.

REM ============================================================
REM INICIAR INTERFACE GRAFICA COM RETRY E TIMEOUT
REM ============================================================
echo [INFO] Iniciando interface grafica... >> "%LOG_FILE%"
echo [INFO] Iniciando interface grafica...

cd /d "%SCRIPT_DIR%"

set "RETRY_COUNT=0"
set "GUI_CODE=1"

:RETRY_GUI
if !RETRY_COUNT! GEQ !MAX_RETRIES! (
    echo [ERRO] Maximas tentativas de execucao da GUI atingidas (!MAX_RETRIES!). >> "%LOG_FILE%"
    echo [ERRO] Nao foi possivel executar a interface grafica.
    goto GUI_FAILED
)

set /a "RETRY_COUNT+=1"
echo [INFO] Tentativa !RETRY_COUNT! de !MAX_RETRIES! para iniciar a GUI... >> "%LOG_FILE%"

REM Mantendo a linha original de execução, mas adicionando também a saída no console via type (opcional)
echo [INFO] Executando: python -u "%SCRIPT_DIR%\gui.py" >> "%LOG_FILE%"
python -u "%SCRIPT_DIR%\gui.py" >> "%LOG_FILE%" 2>&1
set "GUI_CODE=!errorLevel!"

REM Exibe a última linha do log para acompanhamento em tempo real (não substitui o redirecionamento)
if exist "%LOG_FILE%" (
    for /f "delims=" %%L in ('type "%LOG_FILE%" ^| findstr /c:"GUI encerrada"') do echo %%L
)

echo [INFO] GUI encerrada com codigo de saida: !GUI_CODE! >> "%LOG_FILE%"
echo [INFO] GUI encerrada com codigo de saida: !GUI_CODE!

if !GUI_CODE! NEQ 0 (
    if !RETRY_COUNT! LSS !MAX_RETRIES! (
        echo [AVISO] GUI falhou. Tentando novamente em 3 segundos... >> "%LOG_FILE%"
        echo [AVISO] GUI falhou. Tentando novamente...
        timeout /t 3 /nobreak >nul
        goto RETRY_GUI
    )
)

REM ============================================================
REM TRATAMENTO DE SUCESSO/ERRO
REM ============================================================
if !GUI_CODE! NEQ 0 (
    :GUI_FAILED
    echo [ERRO] A interface grafica falhou. Codigo: !GUI_CODE! >> "%LOG_FILE%"
    echo [ERRO] A interface grafica falhou. Codigo: !GUI_CODE!
    echo [DICA] Verifique o log completo: %LOG_FILE%
    echo [DICA] Tente executar em modo Compatibilidade ou verifique Python
    pause
) else (
    echo [OK] Setup concluido com sucesso! >> "%LOG_FILE%"
    echo [OK] Setup concluido com sucesso!
)

REM ============================================================
REM FINALIZAR LOG
REM ============================================================
echo ======================================== >> "%LOG_FILE%"
echo FIM DA EXECUCAO - Codigo: !GUI_CODE! >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

exit /b !GUI_CODE!