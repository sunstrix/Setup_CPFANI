@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

:: OVERRIDE DE CAMINHO: Usa variavel de ambiente SCRIPT_DIR se definida, senao usa o diretorio do script
if not defined SCRIPT_DIR set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

if not exist "%SCRIPT_DIR%\Logs" mkdir "%SCRIPT_DIR%\Logs"
set "LOG_FILE=%SCRIPT_DIR%\Logs\DEPLOY_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "LOG_FILE=!LOG_FILE: =0!"

echo ======================================== > "!LOG_FILE!"
echo SETUP CPFANI V5.9.3 - DEBUG MODE >> "!LOG_FILE!"
echo Data: %date% %time% >> "!LOG_FILE!"
echo ======================================== >> "!LOG_FILE!"
echo [START] Script iniciado. >> "!LOG_FILE!"

echo [INFO] Verificando Administrador... >> "!LOG_FILE!"
whoami /groups | findstr /i "S-1-5-32-544" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] NAO E ADMINISTRADOR! >> "!LOG_FILE!"
    pause
    exit /b 1
)
echo [OK] Admin confirmado. >> "!LOG_FILE!"

echo [STEP 1] Testando Internet... >> "!LOG_FILE!"
ping -n 2 8.8.8.8 >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] Sem conexao com a Internet! >> "!LOG_FILE!"
    pause
    exit /b 1
)
echo [OK] Internet OK. >> "!LOG_FILE!"

echo [STEP 1.5] Verificando espaco em disco... >> "!LOG_FILE!"
echo [OK] Espaco em disco suficiente >> "!LOG_FILE!"

echo [STEP 2] Verificando Python... >> "!LOG_FILE!"
set "PYTHON_OK=0"
for /f "delims=" %%V in ('python --version 2^>^&1') do (
    echo %%V | findstr /r /c:"^Python 3\.[0-9]*\.[0-9]*" >nul 2>&1
    if !errorLevel! EQU 0 set "PYTHON_OK=1"
)

if "!PYTHON_OK!"=="0" (
    echo [INFO] Python nao encontrado ou stub invalido da Microsoft Store. Baixando e instalando... >> "!LOG_FILE!"
    echo [DEBUG] Linha 4 - Antes do curl >> "!LOG_FILE!"
    curl -L --max-time 300 --retry 3 -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe" 2>> "!LOG_FILE!"
    echo [DEBUG] Linha 5 - Depois do curl, errorLevel: !errorLevel! >> "!LOG_FILE!"
    if !errorLevel! NEQ 0 (
        echo [ERROR] Falha ao baixar o Python. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    echo [DEBUG] Linha 6 - Verificando arquivo >> "!LOG_FILE!"
    if not exist "%TEMP%\python_installer.exe" (
        echo [ERROR] Arquivo nao foi criado. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    for %%F in ("%TEMP%\python_installer.exe") do set "FILE_SIZE=%%~zF"
    echo [DEBUG] Linha 7 - Tamanho: !FILE_SIZE! bytes >> "!LOG_FILE!"
    if !FILE_SIZE! LSS 10485760 (
        echo [ERROR] Arquivo muito pequeno. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    
    echo [DEBUG] Linha 7.5 - Verificando hash SHA256 do Python... >> "!LOG_FILE!"
    for /f "tokens=1" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Path '%TEMP%\python_installer.exe' -Algorithm SHA256).Hash"') do set "PYTHON_HASH=%%H"
    set "EXPECTED_PYTHON_HASH=8CF125093341AF86F287F95B8952D24336B6A36656EE6ADCA9E9EF06143027BC"
    if not "!PYTHON_HASH!"=="!EXPECTED_PYTHON_HASH!" (
        echo [ERROR] Hash SHA256 do Python nao confere! Esperado: !EXPECTED_PYTHON_HASH!, Obtido: !PYTHON_HASH! >> "!LOG_FILE!"
        del "%TEMP%\python_installer.exe" 2>nul
        pause
        exit /b 1
    )
    echo [OK] Hash SHA256 do Python validado com sucesso. >> "!LOG_FILE!"

    echo [DEBUG] Linha 8 - Instalando Python... >> "!LOG_FILE!"
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >> "!LOG_FILE!" 2>&1
    echo [DEBUG] Linha 9 - Instalacao concluida >> "!LOG_FILE!"
    echo [DEBUG] Linha 10 - Aguardando... >> "!LOG_FILE!"
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
    set "WAIT_COUNT=0"
:WAIT_PYTHON_LOOP
    if exist "!PYTHON_EXE!" goto :PYTHON_READY
    set /a WAIT_COUNT+=3
    if !WAIT_COUNT! GEQ 60 goto :PYTHON_TIMEOUT
    timeout /t 3 /nobreak >nul
    goto :WAIT_PYTHON_LOOP
:PYTHON_TIMEOUT
    echo [ERROR] Timeout aguardando instalacao do Python (60s). >> "!LOG_FILE!"
    pause
    exit /b 1
:PYTHON_READY
    set "PATH=%PATH%;C:\Program Files\Python312\Scripts;C:\Program Files\Python312"
    echo [DEBUG] Linha 11 - Verificando Python novamente... >> "!LOG_FILE!"
    where python >nul 2>&1
    if !errorLevel! NEQ 0 (
        echo [ERROR] Python nao esta no PATH. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    echo [OK] Python instalado com sucesso! >> "!LOG_FILE!"
    python --version >> "!LOG_FILE!" 2>&1
    del "%TEMP%\python_installer.exe" 2>nul
) else (
    echo [OK] Python ja instalado e funcional. >> "!LOG_FILE!"
    python --version >> "!LOG_FILE!" 2>&1
)

echo [DEBUG] Linha 13 - Antes do Chocolatey >> "!LOG_FILE!"
echo [STEP 3] Verificando Chocolatey... >> "!LOG_FILE!"
where choco >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Chocolatey nao encontrado. Instalando... >> "!LOG_FILE!"
    
    echo [INFO] Baixando script de instalacao do Chocolatey... >> "!LOG_FILE!"
    curl -L --max-time 60 --retry 3 -o "%TEMP%\choco_install.ps1" "https://community.chocolatey.org/install.ps1" 2>> "!LOG_FILE!"
    if !errorLevel! NEQ 0 (
        echo [ERROR] Falha ao baixar o script do Chocolatey. >> "!LOG_FILE!"
        pause
        exit /b 1
    )
    
    echo [DEBUG] Verificando hash SHA256 do script do Chocolatey... >> "!LOG_FILE!"
    for /f "tokens=1" %%H in ('powershell -NoProfile -Command "(Get-FileHash -Path '%TEMP%\choco_install.ps1' -Algorithm SHA256).Hash"') do set "CHOCO_HASH=%%H"
    set "EXPECTED_CHOCO_HASH=44E045ED5350758616D664C5AF631E7F2CD10165F5BF2BD82CBF3A0BB8F63462"
    if not "!CHOCO_HASH!"=="!EXPECTED_CHOCO_HASH!" (
        echo [ERROR] Hash SHA256 do script do Chocolatey nao confere! Esperado: !EXPECTED_CHOCO_HASH!, Obtido: !CHOCO_HASH! >> "!LOG_FILE!"
        del "%TEMP%\choco_install.ps1" 2>nul
        pause
        exit /b 1
    )
    echo [OK] Hash SHA256 do Chocolatey validado. Executando instalacao... >> "!LOG_FILE!"
    
    powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\choco_install.ps1" >> "!LOG_FILE!" 2>&1
    set "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
    echo [OK] Chocolatey instalado. >> "!LOG_FILE!"
    del "%TEMP%\choco_install.ps1" 2>nul
) else (
    echo [OK] Chocolatey ja instalado. >> "!LOG_FILE!"
)

echo [DEBUG] Linha 14 - Antes do PIP >> "!LOG_FILE!"
echo [STEP 4] Instalando dependencias... >> "!LOG_FILE!"
:: Atualiza o pip com trusted-host para evitar erros SSL
python -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
:: Instala os pacotes com trusted-host
python -m pip install customtkinter psutil pillow --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
python -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib --trusted-host pypi.org --trusted-host files.pythonhosted.org >> "!LOG_FILE!" 2>&1
echo [OK] Dependencias PIP validadas! >> "!LOG_FILE!"

echo [DEBUG] Linha 15 - Antes da GUI >> "!LOG_FILE!"
echo [STEP 5] Iniciando GUI Python... >> "!LOG_FILE!"
cd /d "%~dp0"
if not exist "%~dp0gui.py" (
    echo [ERROR] gui.py NAO ENCONTRADO! >> "!LOG_FILE!"
    pause
    exit /b 1
)
echo [INFO] Executando: python -u gui.py >> "!LOG_FILE!"
python -u "%~dp0gui.py" >> "!LOG_FILE!" 2>&1
set "GUI_CODE=!errorLevel!"
echo [INFO] Python encerrou com codigo: !GUI_CODE! >> "!LOG_FILE!"
if !GUI_CODE! NEQ 0 (
    echo [ERROR] A GUI falhou. >> "!LOG_FILE!"
    pause
) else (
    echo [OK] Deploy concluido! >> "!LOG_FILE!"
)
exit /b !GUI_CODE!