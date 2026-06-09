@echo off
:: Forca o modo de expansao de variaveis atrasadas
setlocal EnableDelayedExpansion

:: ==========================================
:: 1. CONFIGURACAO DE LOG IMEDIATA
:: ==========================================
:: Cria pasta de logs se nao existir
if not exist "C:\Scripts\Logs" mkdir "C:\Scripts\Logs"

:: Gera nome do arquivo de log usando data/hora simples (sem WMIC)
set "LOG_FILE=C:\Scripts\Logs\DEPLOY_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
:: Substitui espacos por zeros no horario (ex: 9:05 vira 0905)
set "LOG_FILE=!LOG_FILE: =0!"

:: Escreve cabecalho NO ARQUIVO imediatamente
(
echo ========================================
echo SETUP CP FANI V5.9.3 - INFILTRADO + SELF-HEALING
echo Data: %date% %time%
echo Arquivo Log: !LOG_FILE!
echo ========================================
) > "!LOG_FILE!"

:: ==========================================
:: 2. CHECK ADMIN
:: ==========================================
echo [START] Script iniciado. >> "!LOG_FILE!"
echo [INFO] Verificando Administrador... >> "!LOG_FILE!"

whoami /groups | findstr /i "S-1-5-32-544" >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] NAO E ADMINISTRADOR! >> "!LOG_FILE!"
    echo.
    echo ERRO CRITICO: Este script requer privilegios de Administrador.
    echo Por favor, clique com o botao direito e selecione "Executar como Administrador".
    pause
    exit /b 1
)
echo [OK] Admin confirmado. >> "!LOG_FILE!"

:: ==========================================
:: 3. TESTE DE INTERNET
:: ==========================================
echo [STEP 1] Testando Internet... >> "!LOG_FILE!"
ping -n 2 8.8.8.8 >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [ERROR] Sem conexao com a Internet! >> "!LOG_FILE!"
    echo ERRO: O computador precisa de internet para baixar o Python e os programas.
    pause
    exit /b 1
)
echo [OK] Internet OK. >> "!LOG_FILE!"

:: ==========================================
:: 4. VERIFICACAO DE ESPACO EM DISCO
:: ==========================================
echo [STEP 1.5] Verificando espaco em disco... >> "!LOG_FILE!"
for /f "tokens=3" %%a in ('dir c:\ ^| findstr /i "bytes livres"') do set "FREE_SPACE=%%a"
set "FREE_SPACE=!FREE_SPACE:.=!"
set "FREE_SPACE=!FREE_SPACE: =!"
if !FREE_SPACE! LSS 1073741824 (
    echo [WARNING] Espaco em disco baixo: menos de 1GB livre >> "!LOG_FILE!"
    echo AVISO: Espaco em disco pode ser insuficiente para instalacoes.
    echo Espaco livre atual: !FREE_SPACE! bytes
    choice /C SN /M "Deseja continuar mesmo assim?"
    if !errorLevel! EQU 2 (
        echo [INFO] Operacao cancelada pelo usuario >> "!LOG_FILE!"
        exit /b 0
    )
) else (
    echo [OK] Espaco em disco suficiente >> "!LOG_FILE!"
)

:: ==========================================
:: 5. INSTALACAO DO PYTHON
:: ==========================================
echo [STEP 2] Verificando Python... >> "!LOG_FILE!"
python --version >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Python nao encontrado. Baixando e instalando... >> "!LOG_FILE!"
    
    :: Tentativa de download com retry e validacao
    set "DOWNLOAD_SUCCESS=0"
    for /L %%i in (1,1,3) do (
        if !DOWNLOAD_SUCCESS! EQU 0 (
            echo [INFO] Tentativa %%i de 3: Baixando Python... >> "!LOG_FILE!"
            curl -L --max-time 300 --retry 3 -o "%TEMP%\python_installer.exe" "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe" 2>> "!LOG_FILE!"
            
            if !errorLevel! EQU 0 (
                :: Validacao de tamanho do arquivo (deve ser maior que 10MB)
                for %%F in ("%TEMP%\python_installer.exe") do set "FILE_SIZE=%%~zF"
                if !FILE_SIZE! GTR 10485760 (
                    set "DOWNLOAD_SUCCESS=1"
                    echo [OK] Download concluido. Tamanho: !FILE_SIZE! bytes >> "!LOG_FILE!"
                ) else (
                    echo [WARNING] Arquivo muito pequeno (!FILE_SIZE! bytes). Tentando novamente... >> "!LOG_FILE!"
                    del "%TEMP%\python_installer.exe" 2>nul
                )
            ) else (
                echo [ERROR] Falha no download. Tentativa %%i falhou. >> "!LOG_FILE!"
            )
        )
    )
    
    if !DOWNLOAD_SUCCESS! EQU 0 (
        echo [ERROR] Falha ao baixar o Python apos 3 tentativas. >> "!LOG_FILE!"
        echo ERRO: Nao foi possivel baixar o instalador do Python.
        echo Verifique sua conexao com a internet e tente novamente.
        pause
        exit /b 1
    )
    
    echo [INFO] Instalando Python silenciosamente... >> "!LOG_FILE!"
    "%TEMP%\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >> "!LOG_FILE!" 2>&1
    
    :: Atualiza a variavel PATH local para a sessao atual do CMD
    set "PATH=%PATH%;C:\Program Files\Python312\Scripts\;C:\Program Files\Python312\"
    
    :: Aguarda um momento para o PATH ser atualizado
    timeout /t 3 /nobreak >nul
    
    python --version >nul 2>&1
    if !errorLevel! NEQ 0 (
        echo [ERROR] Falha na instalacao do Python. >> "!LOG_FILE!"
        echo ERRO: Python foi instalado mas nao esta acessivel.
        echo Tente reiniciar o computador e executar o script novamente.
        pause
        exit /b 1
    )
    echo [OK] Python instalado com sucesso! >> "!LOG_FILE!"
    
    :: Limpa o instalador
    del "%TEMP%\python_installer.exe" 2>nul
) else (
    echo [OK] Python ja instalado. >> "!LOG_FILE!"
    python --version >> "!LOG_FILE!" 2>&1
)

:: ==========================================
:: 6. INSTALACAO DO CHOCOLATEY
:: ==========================================
echo [STEP 3] Verificando Chocolatey... >> "!LOG_FILE!"
choco --version >nul 2>&1
if !errorLevel! NEQ 0 (
    echo [INFO] Chocolatey nao encontrado. Instalando... >> "!LOG_FILE!"
    
    :: Instala Chocolatey com validacao
    powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" >> "!LOG_FILE!" 2>&1
    
    if !errorLevel! NEQ 0 (
        echo [ERROR] Falha na instalacao do Chocolatey >> "!LOG_FILE!"
        echo AVISO: Chocolatey nao pode ser instalado. Continuando sem ele...
    ) else (
        set "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
        echo [OK] Chocolatey instalado. >> "!LOG_FILE!"
    )
) else (
    echo [OK] Chocolatey ja instalado. >> "!LOG_FILE!"
    choco --version >> "!LOG_FILE!" 2>&1
)

:: ==========================================
:: 7. DEPENDENCIAS DO PYTHON (PIP)
:: ==========================================
echo [STEP 4] Validacao final de dependencias... >> "!LOG_FILE!"
echo [INFO] Instalando bibliotecas graficas e dependencias (customtkinter, psutil, pillow)... >> "!LOG_FILE!"

:: Atualiza pip primeiro
python -m pip install --upgrade pip >> "!LOG_FILE!" 2>&1
if !errorLevel! NEQ 0 (
    echo [WARNING] Falha ao atualizar pip. Tentando continuar... >> "!LOG_FILE!"
)

:: Instala dependencias com retry
set "PIP_SUCCESS=0"
for /L %%i in (1,1,2) do (
    if !PIP_SUCCESS! EQU 0 (
        echo [INFO] Tentativa %%i de instalar dependencias PIP... >> "!LOG_FILE!"
        python -m pip install customtkinter psutil pillow >> "!LOG_FILE!" 2>&1
        if !errorLevel! EQU 0 (
            set "PIP_SUCCESS=1"
            echo [OK] Dependencias instaladas com sucesso >> "!LOG_FILE!"
        ) else (
            echo [WARNING] Falha na tentativa %%i. Tentando novamente... >> "!LOG_FILE!"
        )
    )
)

if !PIP_SUCCESS! EQU 0 (
    echo [ERROR] Falha ao instalar dependencias PIP apos 2 tentativas >> "!LOG_FILE!"
    echo AVISO: Algumas funcionalidades podem nao funcionar corretamente.
) else (
    echo [OK] Dependencias PIP validadas com sucesso! >> "!LOG_FILE!"
)

:: ==========================================
:: 8. EXECUTAR GUI
:: ==========================================
echo [STEP 5] Iniciando GUI Python... >> "!LOG_FILE!"
cd /d "%~dp0"

if not exist "%~dp0gui.py" (
    echo [ERROR] gui.py NAO ENCONTRADO em %~dp0 >> "!LOG_FILE!"
    echo ERRO: Arquivo gui.py nao encontrado.
    echo Verifique se todos os arquivos do projeto estao presentes.
    pause
    exit /b 1
)

echo [INFO] Executando: python -u gui.py >> "!LOG_FILE!"
echo [INFO] Redirecionando saida para log... >> "!LOG_FILE!"
echo. >> "!LOG_FILE!"
echo ========================================== >> "!LOG_FILE!"
echo SAIDA DO GUI.PY >> "!LOG_FILE!"
echo ========================================== >> "!LOG_FILE!"
echo. >> "!LOG_FILE!"

python -u "%~dp0gui.py" >> "!LOG_FILE!" 2>&1
set "GUI_CODE=!errorLevel!"

echo. >> "!LOG_FILE!"
echo ========================================== >> "!LOG_FILE!"
echo [INFO] Python encerrou com codigo: !GUI_CODE! >> "!LOG_FILE!"

if !GUI_CODE! NEQ 0 (
    echo [ERROR] A GUI falhou ou foi encerrada com erro. >> "!LOG_FILE!"
    echo.
    echo ERRO: A interface grafica encontrou um problema.
    echo Verifique o log em: !LOG_FILE!
    pause
) else (
    echo [OK] Execucao do deploy concluida. >> "!LOG_FILE!"
    echo.
    echo ========================================
    echo DEPLOY CONCLUIDO COM SUCESSO!
    echo ========================================
    echo Log salvo em: !LOG_FILE!
    timeout /t 5 /nobreak >nul
)
exit /b !GUI_CODE!