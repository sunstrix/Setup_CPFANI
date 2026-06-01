@echo off
setlocal enabledelayedexpansion
title Setup CP Fani - Launcher Corporativo V6

:: Cores para o terminal
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "RESET=[0m"

echo ============================================================
echo        LANÇADOR AUTOMATIZADO - SETUP CP FANI V6
echo ============================================================

:: 1. Verificação de privilégios para o log inicial
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [%GREEN%INFO%RESET%] Executando com privilégios de Administrador.
) else (
    echo [%YELLOW%AVISO%RESET%] Executando como Usuário Padrão. Algumas funções de sistema solicitarão UAC.
)

:: 2. Detecção de Python no PATH atual
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [%GREEN%OK%RESET%] Python já está configurado no sistema.
    set "PYTHON_EXE=python"
    goto RUN_APP
)

echo [%YELLOW%AVISO%RESET%] Python não detectado no PATH. Verificando instalações locais...

:: 3. Tentativa de localizar Python em caminhos comuns (Local e Program Files)
set "SEARCH_PATHS="%LocalAppData%\Programs\Python" "%ProgramFiles%\Python" "%ProgramFiles(x86)%\Python""
for %%P in (%SEARCH_PATHS%) do (
    if exist %%P (
        for /f "delims=" %%I in ('dir /b /s "%%~P\python.exe" 2^>nul') do (
            set "PYTHON_EXE=%%I"
            echo [%GREEN%OK%RESET%] Python localizado em: !PYTHON_EXE!
            goto RUN_APP
        )
    )
)

:: 4. Se não encontrou, inicia instalação automática
echo [%RED%ERRO%RESET%] Python não encontrado. Iniciando download do instalador...
set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PY_INSTALLER=%temp%\python_installer.exe"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%PY_URL%', '%PY_INSTALLER%')"

echo [%YELLOW%INFO%RESET%] Instalando Python silenciosamente. Aguarde...
start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

:: Re-verificação imediata após instalação
echo [%YELLOW%INFO%RESET%] Atualizando sessão e re-verificando...
:: Tenta caminhos fixos que o instalador costuma usar
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
) else if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
) else (
    :: Último recurso: tenta chamar pelo nome e torcer para o shell ter atualizado
    set "PYTHON_EXE=python"
)

:RUN_APP
echo [%GREEN%INFO%RESET%] Iniciando Interface Gráfica...
"%PYTHON_EXE%" gui.py

if %errorLevel% neq 0 (
    echo [%RED%ERRO%RESET%] A aplicação encerrou com erro.
    pause
)

echo [%GREEN%SUCESSO%RESET%] Processo finalizado.
pause