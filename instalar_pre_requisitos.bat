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
:: 0. VALIDACAO DE ESPACO EM DISCO
:: ============================================================
echo [STEP 0] Verificando espaco em disco...
echo [STEP 0] Verificando espaco em disco... >> "!LOG_FILE!"

for /f "tokens=3" %%A in ('dir C:\ 2^>nul ^| findstr /i "bytes livres"') do (
    set "FREE_SPACE=%%A"
    set "FREE_SPACE=!FREE_SPACE:.=!"
)

if not defined FREE_SPACE (
    for /f "tokens=3" %%A in ('dir C:\ 2^>nul ^| findstr /i "bytes free"') do (
        set "FREE_SPACE=%%A"
        set "FREE_SPACE=!FREE_SPACE:.=!"
    )
)

if defined FREE_SPACE (
    if !FREE_SPACE! LSS 524288000 (
        echo [ERRO] Espaco em disco insuficiente! Necessario: 500MB >> "!LOG_FILE!"
        echo [ERRO] Espaco em disco insuficiente! Necessario: 500MB
        pause
        exit /b 1
    )
    echo [OK] Espaco em disco suficiente: !FREE_SPACE! bytes >> "!LOG_FILE!"
    echo [OK] Espaco em disco suficiente.
) else (
    echo [AVISO] Nao foi possivel validar espaco em disco. Continuando... >> "!LOG_FILE!"
    echo [AVISO] Nao foi possivel validar espaco em disco. Continuando...
)

:: ============================================================
:: 1. VERIFICACAO E INSTALACAO DO PYTHON (LOGICA A PROVA DE FALHAS)
:: ============================================================
echo [STEP 1] Verificando Python...
echo [STEP 1] Verificando Python... >> "!LOG_FILE!"

set "PYTHON_OK=0"
set "PYTHON_EXE="

:: 1.1 Verifica caminhos de instalacao padrao primeiro (evita o alias da Store)
:: Versoes suportadas: 3.8 ate 3.13 (conforme settings.json)
for %%V in (313 312 311 310 39 38) do (
    for %%P in (
        "C:\Program Files\Python%%V\python.exe"
        "C:\ProgramData\Python%%V\python.exe"
        "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python%%V\python.exe"
    ) do (
        if exist "%%~P" (
            "%%~P" -c "print('OK')" >nul 2>&1
            if !errorLevel! EQU 0 (
                set "PYTHON_OK=1"
                set "PYTHON_EXE=%%~P"
                echo [OK] Python funcional encontrado em: %%~P
                echo [OK] Python funcional encontrado em: %%~P >> "!LOG_FILE!"
                goto :PYTHON_FOUND
            )
        )
    )
)

:: 1.2 Tenta o Python Launcher oficial (nao sofre do bug da Windows Store)
if !PYTHON_OK! EQU 0 (
    py -c "print('OK')" >nul 2>&1
    if !errorLevel! EQU 0 (
        set "PYTHON_OK=1"
        set "PYTHON_EXE=py"
        echo [OK] Python funcional encontrado via launcher 'py'.
        echo [OK] Python funcional encontrado via launcher 'py'. >> "!LOG_FILE!"
        goto :PYTHON_FOUND
    )
)

:: 1.3 Ultimo recurso: verifica 'where python' mas rejeita se for WindowsApps
if !PYTHON_OK! EQU 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        echo %%i | findstr /i /c:"WindowsApps" >nul
        if !errorLevel! NEQ 0 (
            set "PYTHON_EXE=%%i"
            "%%i" -c "print('OK')" >nul 2>&1
            if !errorLevel! EQU 0 (
                set "PYTHON_OK=1"
                echo [OK] Python funcional encontrado via where: %%i
                echo [OK] Python funcional encontrado via where: %%i >> "!LOG_FILE!"
                goto :PYTHON_FOUND
            )
        )
    )
)

:PYTHON_FOUND
if !PYTHON_OK! EQU 1 (
    echo [OK] Python ja esta instalado e funcional. >> "!LOG_FILE!"
    echo [OK] Python ja esta instalado e funcional.
    goto :CHECK_CHOCO
)

:: ============================================================
:: INSTALACAO DO PYTHON (Se nao foi encontrado nenhum valido)
:: ============================================================
echo [INFO] Python nao encontrado ou invalido. Iniciando download...
echo [INFO] Python nao encontrado ou invalido. Iniciando download... >> "!LOG_FILE!"

:: Remove forcadamente os aliases da Windows Store que causam travamento (HKCU e HKLM)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\AppExecutionAliases\python.exe" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\AppExecutionAliases\python3.exe" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\AppExecutionAliases\python.exe" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\AppExecutionAliases\python3.exe" /f >nul 2>&1

set "PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
set "DOWNLOAD_SUCCESS=0"

echo [INFO] Baixando Python via PowerShell (ate 3 tentativas)...
echo [INFO] Baixando Python via PowerShell (ate 3 tentativas)... >> "!LOG_FILE!"

:: Loop de retry com backoff
for /L %%i in (1,1,3) do (
    if !DOWNLOAD_SUCCESS! EQU 0 (
        echo [INFO] Tentativa de download %%i/3... >> "!LOG_FILE!"
        
        powershell -NoProfile -Command "$ProgressPreference = 'SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing" >> "!LOG_FILE!" 2>&1
        
        if !errorLevel! EQU 0 (
            if exist "%PYTHON_INSTALLER%" (
                for %%F in ("%PYTHON_INSTALLER%") do set "FILE_SIZE=%%~zF"
                if !FILE_SIZE! GEQ 31457280 (
                    set "DOWNLOAD_SUCCESS=1"
                    echo [OK] Download validado: !FILE_SIZE! bytes >> "!LOG_FILE!"
                ) else (
                    echo [AVISO] Arquivo muito pequeno (!FILE_SIZE! bytes). Removendo... >> "!LOG_FILE!"
                    del "%PYTHON_INSTALLER%" 2>nul
                )
            )
        ) else (
            echo [AVISO] Tentativa %%i falhou. Aguardando 5 segundos... >> "!LOG_FILE!"
            timeout /t 5 /nobreak >nul
        )
    )
)

if !DOWNLOAD_SUCCESS! EQU 0 (
    echo [ERRO] Falha no download do Python apos 3 tentativas. >> "!LOG_FILE!"
    echo [ERRO] Falha no download do Python apos 3 tentativas.
    pause
    exit /b 1
)

echo [INFO] Instalando Python (modo silencioso, pode levar alguns minutos)...
echo [INFO] Instalando Python (modo silencioso)... >> "!LOG_FILE!"
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1 AssociateFiles=1 >> "!LOG_FILE!" 2>&1

if !errorLevel! NEQ 0 (
    echo [ERRO] Falha na instalacao do Python. Codigo: !errorLevel! >> "!LOG_FILE!"
    echo [ERRO] Falha na instalacao do Python.
    pause
    exit /b 1
)

del "%PYTHON_INSTALLER%" 2>nul
echo [OK] Python instalado com sucesso. >> "!LOG_FILE!"
echo [OK] Python instalado com sucesso.

:: ============================================================
:: VALIDACAO POS-INSTALACAO DO PYTHON
:: ============================================================
echo [INFO] Validando instalacao do Python...
echo [INFO] Validando instalacao do Python... >> "!LOG_FILE!"

:: Aguarda brevemente para o PATH ser registrado
timeout /t 2 /nobreak >nul

:: Tenta o launcher py primeiro (instalado pelo installer oficial)
py -c "print('OK')" >nul 2>&1
if !errorLevel! EQU 0 (
    set "PYTHON_OK=1"
    set "PYTHON_EXE=py"
    echo [OK] Python validado via launcher 'py' apos instalacao. >> "!LOG_FILE!"
    echo [OK] Python validado via launcher 'py' apos instalacao.
    goto :CHECK_CHOCO
)

:: Fallback: tenta encontrar o python.exe recém-instalado
for %%V in (312 311 310 39 38) do (
    if exist "C:\Program Files\Python%%V\python.exe" (
        "C:\Program Files\Python%%V\python.exe" -c "print('OK')" >nul 2>&1
        if !errorLevel! EQU 0 (
            set "PYTHON_OK=1"
            set "PYTHON_EXE=C:\Program Files\Python%%V\python.exe"
            set "PATH=!PATH!;C:\Program Files\Python%%V\;C:\Program Files\Python%%V\Scripts\"
            echo [OK] Python validado em C:\Program Files\Python%%V\python.exe >> "!LOG_FILE!"
            echo [OK] Python validado em C:\Program Files\Python%%V\python.exe
            goto :CHECK_CHOCO
        )
    )
)

echo [ERRO] Python foi instalado mas nao e possivel executa-lo. Verifique o PATH. >> "!LOG_FILE!"
echo [ERRO] Python foi instalado mas nao e possivel executa-lo. Verifique o PATH.
pause
exit /b 1

:: ============================================================
:: 2. VERIFICACAO E INSTALACAO DO CHOCOLATEY
:: ============================================================
:CHECK_CHOCO
echo [STEP 2] Verificando Chocolatey...
echo [STEP 2] Verificando Chocolatey... >> "!LOG_FILE!"

where choco >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Chocolatey nao encontrado. Instalando...
    echo [INFO] Chocolatey nao encontrado. Instalando... >> "!LOG_FILE!"
    
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://community.chocolatey.org/install.ps1' -OutFile '$env:TEMP\choco_install.ps1' -UseBasicParsing; & '$env:TEMP\choco_install.ps1'" >> "!LOG_FILE!" 2>&1
    
    if !errorLevel! NEQ 0 (
        echo [ERRO] Falha na instalacao do Chocolatey. >> "!LOG_FILE!"
        echo [ERRO] Falha na instalacao do Chocolatey.
        pause
        exit /b 1
    )
    
    :: Atualiza PATH na sessao atual
    set "PATH=!PATH!;%ALLUSERSPROFILE%\chocolatey\bin"
    
    :: Valida se choco realmente funciona agora
    where choco >nul 2>&1
    if !errorLevel! NEQ 0 (
        echo [ERRO] Chocolatey instalado mas nao encontrado no PATH. >> "!LOG_FILE!"
        echo [ERRO] Chocolatey instalado mas nao encontrado no PATH.
        pause
        exit /b 1
    )
    
    echo [OK] Chocolatey instalado e validado com sucesso. >> "!LOG_FILE!"
    echo [OK] Chocolatey instalado e validado com sucesso.
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
%PYTHON_EXE% -m pip install --upgrade pip --no-warn-script-location >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [AVISO] Falha ao atualizar pip (codigo !errorLevel!). Continuando... >> "!LOG_FILE!"
)

echo [INFO] Instalando customtkinter...
%PYTHON_EXE% -m pip install customtkinter --no-warn-script-location >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha ao instalar customtkinter. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [INFO] Instalando psutil...
%PYTHON_EXE% -m pip install psutil --no-warn-script-location >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha ao instalar psutil. >> "!LOG_FILE!"
    pause
    exit /b 1
)

echo [INFO] Instalando pillow...
%PYTHON_EXE% -m pip install pillow --no-warn-script-location >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] Falha ao instalar pillow. >> "!LOG_FILE!"
    pause
    exit /b 1
)

:: ============================================================
:: 3.1 VALIDACAO POS-INSTALACAO DAS DEPENDENCIAS
:: ============================================================
echo [INFO] Validando dependencias instaladas...
echo [INFO] Validando dependencias instaladas... >> "!LOG_FILE!"

%PYTHON_EXE% -c "import customtkinter; print('customtkinter OK')" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] customtkinter instalado mas nao importavel. >> "!LOG_FILE!"
    echo [ERRO] customtkinter instalado mas nao importavel.
    pause
    exit /b 1
)

%PYTHON_EXE% -c "import psutil; print('psutil OK')" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] psutil instalado mas nao importavel. >> "!LOG_FILE!"
    echo [ERRO] psutil instalado mas nao importavel.
    pause
    exit /b 1
)

%PYTHON_EXE% -c "from PIL import Image; print('pillow OK')" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERRO] pillow instalado mas nao importavel. >> "!LOG_FILE!"
    echo [ERRO] pillow instalado mas nao importavel.
    pause
    exit /b 1
)

echo [OK] Todas as dependencias PIP instaladas e validadas com sucesso. >> "!LOG_FILE!"
echo [OK] Todas as dependencias PIP instaladas e validadas com sucesso.

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