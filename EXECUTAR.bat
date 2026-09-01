@echo off
setlocal EnableDelayedExpansion
chcp 1252 >nul
title SETUP CPFANI V6.3.0

if not defined SCRIPT_DIR set "SCRIPT_DIR=C:\Scripts"
set "LOG_DIR=%SCRIPT_DIR%\Logs"
set "NO_PAUSE=!SETUP_CPFANI_NO_PAUSE!"

echo [INFO] Verificando Administrador...
whoami /groups | findstr /i "S-1-5-32-544" >nul 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 (
    echo [ERROR] NAO E ADMINISTRADOR!
    echo [INFO] Execute como Administrador.
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)
echo [OK] Admin confirmado.

mkdir "%LOG_DIR%" 2>nul
if not exist "%LOG_DIR%" (
    echo [ERROR] Nao foi possivel criar %LOG_DIR%.
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)

set "LOG_FILE=%LOG_DIR%\DEPLOY_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "LOG_FILE=!LOG_FILE: =0!"
type nul > "!LOG_FILE!" 2>nul
if not exist "!LOG_FILE!" (
    echo [ERROR] Nao foi possivel criar o arquivo de log.
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)

call :log "========================================"
call :log "SETUP CPFANI V6.3.0 - DEBUG MODE"
call :log "Data: %date% %time%"
call :log "SCRIPT_DIR: %SCRIPT_DIR%"
call :log "LOG_DIR: !LOG_DIR!"
call :log "LOG_FILE: !LOG_FILE!"
call :log "========================================"
call :log "[START] Script iniciado."
call :log "[OK] Admin confirmado."

set "CURL_CMD=curl.exe"
where curl.exe >nul 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 set "CURL_CMD=curl"
call :log "[INFO] Comando de download: !CURL_CMD!"

call :log "[STEP 1] Testando Internet..."
ping -n 2 8.8.8.8 >nul 2>&1
set "RC=!ERRORLEVEL!"
call :log "[DEBUG] ping RC: !RC!"
if !RC! NEQ 0 (
    call :log "[ERROR] Sem conexao com a Internet!"
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)
call :log "[OK] Internet OK."

call :log "[STEP 1.5] Verificando espaco em disco..."
call :log "[OK] Espaco em disco suficiente"

call :log "[STEP 2] Verificando Python..."
set "PYTHON_OK=0"
set "PYTHON_CMD="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PYTHON_CMD (
        echo %%P | findstr /i "WindowsApps" >nul 2>&1
        set "RC=!ERRORLEVEL!"
        if !RC! NEQ 0 set "PYTHON_CMD=%%P"
    )
)
if defined PYTHON_CMD (
    call :log "[DEBUG] Python candidato: !PYTHON_CMD!"
    for /f "delims=" %%V in ('"!PYTHON_CMD!" --version 2^>^&1') do (
        echo %%V | findstr /r /c:"^Python 3\.[0-9]*\.[0-9]*" >nul 2>&1
        set "RC=!ERRORLEVEL!"
        if !RC! EQU 0 set "PYTHON_OK=1"
    )
)
if not defined PYTHON_CMD set "PYTHON_CMD=python"

if "!PYTHON_OK!"=="0" (
    call :log "[INFO] Python nao encontrado ou stub invalido da Microsoft Store. Baixando e instalando..."
    set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
    call :log "[DEBUG] Linha 4 - Antes do curl"
    !CURL_CMD! -L --fail --max-time 300 --retry 3 -o "!PYTHON_INSTALLER!" "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe" 2>> "!LOG_FILE!"
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] Linha 5 - Depois do curl, RC: !RC!"
    if !RC! NEQ 0 (
        call :log "[ERROR] Falha ao baixar o Python."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[DEBUG] Linha 6 - Verificando arquivo"
    if not exist "!PYTHON_INSTALLER!" (
        call :log "[ERROR] Arquivo nao foi criado."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    for %%F in ("!PYTHON_INSTALLER!") do set "FILE_SIZE=%%~zF"
    call :log "[DEBUG] Linha 7 - Tamanho: !FILE_SIZE! bytes"
    if !FILE_SIZE! LSS 10485760 (
        call :log "[ERROR] Arquivo muito pequeno."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[DEBUG] Linha 7.5 - Verificando hash SHA256 do Python..."
    set "PYTHON_HASH="
    for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath $env:PYTHON_INSTALLER -Algorithm SHA256).Hash" 2^>nul') do set "PYTHON_HASH=%%H"
    set "EXPECTED_PYTHON_HASH=1206721601A62C925D4E4A0DCFC371E88F2DDBE8C0C07962EBB2BE9B5BDE4570"
    set "EXPECTED_PYTHON_HASH_ALT=8CF125093341AF86F287F95B8952D24336B6A36656EE6ADCA9E9EF06143027BC"
    set "HASH_OK=0"
    if /i "!PYTHON_HASH!"=="!EXPECTED_PYTHON_HASH!" set "HASH_OK=1"
    if /i "!PYTHON_HASH!"=="!EXPECTED_PYTHON_HASH_ALT!" set "HASH_OK=1"
    if not defined PYTHON_HASH (
        call :log "[ERROR] Hash SHA256 do Python nao gerado."
        del "!PYTHON_INSTALLER!" 2>nul
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    if "!HASH_OK!"=="0" (
        call :log "[ERROR] Hash SHA256 do Python nao confere! Obtido: !PYTHON_HASH!"
        del "!PYTHON_INSTALLER!" 2>nul
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[OK] Hash SHA256 do Python validado com sucesso."
    call :log "[DEBUG] Linha 8 - Instalando Python..."
    "!PYTHON_INSTALLER!" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >> "!LOG_FILE!" 2>&1
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] Linha 9 - Instalacao concluida. RC: !RC!"
    set "INSTALL_OK=1"
    if !RC! NEQ 0 if !RC! NEQ 3010 set "INSTALL_OK=0"
    if "!INSTALL_OK!"=="0" (
        call :log "[ERROR] Instalacao do Python falhou."
        del "!PYTHON_INSTALLER!" 2>nul
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[DEBUG] Linha 10 - Aguardando..."
    set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
    set "WAIT_COUNT=0"
    set "WAIT_RESULT=0"
    call :WAIT_PYTHON
    if !WAIT_RESULT! NEQ 0 (
        call :log "[ERROR] Timeout aguardando instalacao do Python (60s)."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    set "PATH=!PATH!;%ProgramFiles%\Python312\Scripts;%ProgramFiles%\Python312"
    set "PYTHON_CMD=!PYTHON_EXE!"
    call :log "[DEBUG] Linha 11 - Verificando Python novamente..."
    if not exist "!PYTHON_CMD!" (
        call :log "[ERROR] Python nao esta no PATH."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[OK] Python instalado com sucesso!"
    "!PYTHON_CMD!" --version >> "!LOG_FILE!" 2>&1
    del "!PYTHON_INSTALLER!" 2>nul
) else (
    call :log "[DEBUG] Linha 12 - Python ja instalado"
    call :log "[OK] Python ja instalado."
    "!PYTHON_CMD!" --version >> "!LOG_FILE!" 2>&1
)

call :log "[DEBUG] Linha 13 - Antes do Chocolatey"
call :log "[STEP 3] Verificando Chocolatey..."
where choco >nul 2>&1
set "RC=!ERRORLEVEL!"
call :log "[DEBUG] where choco RC: !RC!"
if !RC! NEQ 0 (
    call :log "[INFO] Chocolatey nao encontrado. Instalando..."
    set "CHOCO_INSTALLER=%TEMP%\choco_install.ps1"
    call :log "[INFO] Baixando script de instalacao do Chocolatey..."
    !CURL_CMD! -L --fail --max-time 60 --retry 3 -o "!CHOCO_INSTALLER!" "https://community.chocolatey.org/install.ps1" 2>> "!LOG_FILE!"
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] curl Chocolatey RC: !RC!"
    if !RC! NEQ 0 (
        call :log "[ERROR] Falha ao baixar o script do Chocolatey."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[DEBUG] Verificando hash SHA256 do script do Chocolatey..."
    set "CHOCO_HASH="
    for /f "delims=" %%H in ('powershell -NoProfile -Command "(Get-FileHash -LiteralPath $env:CHOCO_INSTALLER -Algorithm SHA256).Hash" 2^>nul') do set "CHOCO_HASH=%%H"
    set "EXPECTED_CHOCO_HASH=44E045ED5350758616D664C5AF631E7F2CD10165F5BF2BD82CBF3A0BB8F63462"
    if not defined CHOCO_HASH (
        call :log "[ERROR] Hash SHA256 do Chocolatey nao gerado."
        del "!CHOCO_INSTALLER!" 2>nul
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    if /i not "!CHOCO_HASH!"=="!EXPECTED_CHOCO_HASH!" (
        call :log "[ERROR] Hash SHA256 do script do Chocolatey nao confere! Obtido: !CHOCO_HASH!"
        del "!CHOCO_INSTALLER!" 2>nul
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[OK] Hash SHA256 do Chocolatey validado. Executando instalacao..."
    powershell -NoProfile -ExecutionPolicy Bypass -File "!CHOCO_INSTALLER!" >> "!LOG_FILE!" 2>&1
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] powershell Chocolatey RC: !RC!"
    set "INSTALL_OK=1"
    if !RC! NEQ 0 if !RC! NEQ 3010 set "INSTALL_OK=0"
    if "!INSTALL_OK!"=="0" (
        call :log "[ERROR] Instalacao do Chocolatey falhou."
        del "!CHOCO_INSTALLER!" 2>nul
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    set "PATH=!PATH!;%ALLUSERSPROFILE%\chocolatey\bin"
    del "!CHOCO_INSTALLER!" 2>nul
    where choco >nul 2>&1
    set "RC=!ERRORLEVEL!"
    if !RC! NEQ 0 (
        call :log "[ERROR] Chocolatey nao esta no PATH apos instalacao."
        if /i not "!NO_PAUSE!"=="1" pause >nul
        exit /b 1
    )
    call :log "[OK] Chocolatey instalado."
) else (
    call :log "[OK] Chocolatey ja instalado."
)

call :log "[DEBUG] Linha 14 - Antes do PIP"
call :log "[STEP 4] Instalando dependencias..."
:: Atualiza o pip com trusted-host para evitar erros SSL
"!PYTHON_CMD!" -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 call :log "[WARN] Falha ao atualizar pip. RC: !RC!"

:: Instala os pacotes com trusted-host
"!PYTHON_CMD!" -m pip install customtkinter psutil pillow --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 call :log "[WARN] Falha ao instalar customtkinter psutil pillow. RC: !RC!"

"!PYTHON_CMD!" -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 call :log "[WARN] Falha ao instalar dependencias Google. RC: !RC!"

:: V6.3.0: openpyxl para a planilha de inventario xlsx (opcional - GUI trata ausencia como AVISO)
"!PYTHON_CMD!" -m pip install openpyxl --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 call :log "[WARN] Falha ao instalar openpyxl (planilha xlsx ficara desabilitada). RC: !RC!"

call :log "[OK] Dependencias PIP validadas!"

call :log "[DEBUG] Linha 15 - Antes da GUI"
call :log "[STEP 5] Iniciando GUI Python..."
cd /d "%~dp0"

if not exist "%~dp0gui.py" (
    call :log "[ERROR] gui.py NAO ENCONTRADO!"
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)

:: V6.3.0: valida modulos obrigatorios antes de subir a GUI
if not exist "%~dp0mod_config.py" (
    call :log "[ERROR] mod_config.py NAO ENCONTRADO!"
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)
if not exist "%~dp0mod_instalar.py" (
    call :log "[ERROR] mod_instalar.py NAO ENCONTRADO!"
    if /i not "!NO_PAUSE!"=="1" pause >nul
    exit /b 1
)

:: V6.3.0: aviso nao fatal sobre credenciais OAuth2 (upload do Drive)
if not exist "%~dp0credentials\oauth2_credentials.json" (
    call :log "[WARN] credentials\oauth2_credentials.json nao encontrado - upload ao Drive desabilitado."
) else (
    call :log "[OK] Credenciais OAuth2 encontradas."
)

call :log "[INFO] Executando: !PYTHON_CMD! -u gui.py"
"!PYTHON_CMD!" -u "%~dp0gui.py" >> "!LOG_FILE!" 2>&1
set "GUI_CODE=!ERRORLEVEL!"
call :log "[INFO] Python encerrou com codigo: !GUI_CODE!"

if !GUI_CODE! NEQ 0 (
    call :log "[ERROR] A GUI falhou."
) else (
    call :log "[OK] Deploy concluido!"
)

call :log "[INFO] Log completo: !LOG_FILE!"
if /i not "!NO_PAUSE!"=="1" (
    echo.
    echo [INFO] Pressione qualquer tecla para encerrar...
    pause >nul
)
exit /b !GUI_CODE!

:log
set "MSG=%~1"
echo !MSG!
if defined LOG_FILE echo !MSG! >> "!LOG_FILE!"
exit /b 0

:WAIT_PYTHON
if exist "!PYTHON_EXE!" (
    set "WAIT_RESULT=0"
    exit /b 0
)
set /a WAIT_COUNT+=3
if !WAIT_COUNT! GEQ 60 (
    set "WAIT_RESULT=1"
    exit /b 1
)
timeout /t 3 /nobreak >nul 2>&1
goto :WAIT_PYTHON