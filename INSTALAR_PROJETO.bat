@echo off
setlocal EnableDelayedExpansion
chcp 1252 >nul
title INSTALAR PROJETO - SETUP CPFANI (BOOTSTRAP)

REM ============================================================
REM INSTALAR_PROJETO.bat - V1.0
REM 1) Instala o Git (winget -> choco -> download oficial)
REM 2) Baixa o projeto para C:\Scripts\Setup_CPFANI
REM 3) Abre o EXECUTAR.bat
REM ASCII/ANSI - sem acentos
REM ============================================================

echo [INFO] Verificando Administrador...
whoami /groups | findstr /i "S-1-5-32-544" >nul 2>&1
set "RC=!ERRORLEVEL!"
if !RC! NEQ 0 (
    echo [ERROR] NAO E ADMINISTRADOR!
    echo [INFO] Execute como Administrador.
    pause >nul
    exit /b 1
)
echo [OK] Admin confirmado.

if not exist "C:\Scripts" mkdir "C:\Scripts"
if not exist "C:\Scripts\Logs" mkdir "C:\Scripts\Logs"

set "LOG_FILE=C:\Scripts\Logs\BOOTSTRAP_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
set "LOG_FILE=!LOG_FILE: =0!"
type nul > "!LOG_FILE!" 2>nul

call :log "========================================"
call :log "INSTALAR_PROJETO.bat - BOOTSTRAP V1.0"
call :log "Data: %date% %time%"
call :log "========================================"
call :log "[START] Script iniciado."
call :log "[OK] Admin confirmado."

set "REPO_URL=https://github.com/sunstrix/Setup_CPFANI.git"
set "ZIP_URL=https://github.com/sunstrix/Setup_CPFANI/archive/refs/heads/main.zip"
set "DEST=C:\Scripts\Setup_CPFANI"
set "GIT_DIR=C:\Program Files\Git\cmd"

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
    pause >nul
    exit /b 1
)
call :log "[OK] Internet OK."

REM ------------------------------------------------------------
REM STEP 2: VERIFICAR / INSTALAR O GIT
REM ------------------------------------------------------------
call :log "[STEP 2] Verificando Git..."
call :FIND_GIT
if defined GIT_CMD (
    call :log "[OK] Git ja instalado: !GIT_CMD!"
) else (
    call :log "[INFO] Git nao encontrado. Tentando winget..."
    where winget >nul 2>&1
    set "RC=!ERRORLEVEL!"
    if !RC! EQU 0 (
        winget install --exact --id Git.Git --scope machine --silent --disable-interactivity --accept-package-agreements --accept-source-agreements >> "!LOG_FILE!" 2>&1
        set "RC=!ERRORLEVEL!"
        call :log "[DEBUG] winget RC: !RC!"
        if !RC! EQU 0 call :log "[OK] winget concluido."
    ) else (
        call :log "[AVISO] winget nao disponivel."
    )
    call :FIND_GIT
)

if not defined GIT_CMD (
    call :log "[INFO] Tentando Chocolatey..."
    where choco >nul 2>&1
    set "RC=!ERRORLEVEL!"
    if !RC! EQU 0 (
        choco install git -y >> "!LOG_FILE!" 2>&1
        set "RC=!ERRORLEVEL!"
        call :log "[DEBUG] choco RC: !RC!"
        if !RC! EQU 0 call :log "[OK] choco concluido."
    ) else (
        call :log "[AVISO] Chocolatey nao disponivel."
    )
    call :FIND_GIT
)

if not defined GIT_CMD (
    call :log "[INFO] Baixando instalador oficial do Git..."
    set "GIT_INSTALLER=%TEMP%\git_installer.exe"
    !CURL_CMD! -L --fail --max-time 600 --retry 3 -o "!GIT_INSTALLER!" "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe" 2>> "!LOG_FILE!"
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] curl Git RC: !RC!"
    if !RC! NEQ 0 (
        call :log "[ERROR] Falha ao baixar o instalador do Git."
        pause >nul
        exit /b 1
    )
    for %%F in ("!GIT_INSTALLER!") do set "FILE_SIZE=%%~zF"
    call :log "[DEBUG] Tamanho: !FILE_SIZE! bytes"
    if !FILE_SIZE! LSS 41943040 (
        call :log "[ERROR] Instalador do Git muito pequeno."
        del "!GIT_INSTALLER!" 2>nul
        pause >nul
        exit /b 1
    )
    call :log "[INFO] Instalando Git em modo silencioso..."
    "!GIT_INSTALLER!" /VERYSILENT /NORESTART /NOCANCEL /SP- >> "!LOG_FILE!" 2>&1
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] instalador Git RC: !RC!"
    if !RC! NEQ 0 (
        call :log "[ERROR] Instalacao do Git falhou."
        del "!GIT_INSTALLER!" 2>nul
        pause >nul
        exit /b 1
    )
    del "!GIT_INSTALLER!" 2>nul
    call :FIND_GIT
)

if not defined GIT_CMD (
    call :log "[ERROR] Git nao disponivel apos todas as tentativas."
    pause >nul
    exit /b 1
)
"!GIT_CMD!" --version >> "!LOG_FILE!" 2>&1
call :log "[OK] Git pronto: !GIT_CMD!"

REM ------------------------------------------------------------
REM STEP 3: BAIXAR / ATUALIZAR O PROJETO
REM ------------------------------------------------------------
call :log "[STEP 3] Baixando projeto para !DEST!..."
set "PROJ_OK=0"

if exist "!DEST!\.git" (
    call :log "[INFO] Repositorio ja existe. Atualizando (git pull)..."
    "!GIT_CMD!" -C "!DEST!" pull --ff-only >> "!LOG_FILE!" 2>&1
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] git pull RC: !RC!"
    if !RC! EQU 0 set "PROJ_OK=1"
) else (
    if exist "!DEST!" (
        set "BAK=!DEST!_bak_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2!"
        set "BAK=!BAK: =0!"
        call :log "[AVISO] Pasta existe sem .git - movendo para !BAK!..."
        move "!DEST!" "!BAK!" >nul 2>&1
    )
    call :log "[INFO] Clonando repositorio (depth 1)..."
    "!GIT_CMD!" clone --depth 1 "!REPO_URL!" "!DEST!" >> "!LOG_FILE!" 2>&1
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] git clone RC: !RC!"
    if !RC! EQU 0 set "PROJ_OK=1"
)

if "!PROJ_OK!"=="0" (
    call :log "[AVISO] Git falhou. Tentando download do ZIP..."
    set "ZIP_TMP=%TEMP%\setup_cpfani_main.zip"
    set "ZIP_DIR=%TEMP%\setup_cpfani_zip"
    !CURL_CMD! -L --fail --max-time 600 --retry 3 -o "!ZIP_TMP!" "!ZIP_URL!" 2>> "!LOG_FILE!"
    set "RC=!ERRORLEVEL!"
    call :log "[DEBUG] curl ZIP RC: !RC!"
    if !RC! EQU 0 (
        powershell -NoProfile -Command "Expand-Archive -LiteralPath '!ZIP_TMP!' -DestinationPath '!ZIP_DIR!' -Force" >> "!LOG_FILE!" 2>&1
        set "RC=!ERRORLEVEL!"
        call :log "[DEBUG] Expand-Archive RC: !RC!"
        if !RC! EQU 0 (
            robocopy "!ZIP_DIR!\Setup_CPFANI-main" "!DEST!" /E /NFL /NDL /NJH /NJS >> "!LOG_FILE!" 2>&1
            set "RC=!ERRORLEVEL!"
            call :log "[DEBUG] robocopy RC: !RC!"
            if !RC! LSS 8 set "PROJ_OK=1"
        )
        del "!ZIP_TMP!" 2>nul
        rd /s /q "!ZIP_DIR!" >nul 2>&1
    )
)

if "!PROJ_OK!"=="0" (
    call :log "[ERROR] Falha ao baixar o projeto."
    pause >nul
    exit /b 1
)
call :log "[OK] Projeto disponivel em !DEST!"

REM ------------------------------------------------------------
REM STEP 4: ABRIR O EXECUTAR.BAT
REM ------------------------------------------------------------
call :log "[STEP 4] Iniciando EXECUTAR.bat..."
if not exist "!DEST!\EXECUTAR.bat" (
    call :log "[ERROR] EXECUTAR.bat nao encontrado em !DEST!"
    pause >nul
    exit /b 1
)

set "SCRIPT_DIR=C:\Scripts"
cd /d "!DEST!"
call "!DEST!\EXECUTAR.bat"
set "RC=!ERRORLEVEL!"
call :log "[INFO] EXECUTAR.bat encerrou com codigo: !RC!"
call :log "[END] Bootstrap concluido."
exit /b !RC!

REM ============================================================
REM SUBROTINAS
REM ============================================================

:FIND_GIT
set "GIT_CMD="
where git >nul 2>&1
set "RC=!ERRORLEVEL!"
if !RC! EQU 0 (
    set "GIT_CMD=git"
    exit /b 0
)
if exist "!GIT_DIR!\git.exe" (
    set "GIT_CMD=!GIT_DIR!\git.exe"
    set "PATH=!PATH!;!GIT_DIR!"
)
exit /b 0

:log
set "MSG=%~1"
echo !MSG!
if defined LOG_FILE echo !MSG! >> "!LOG_FILE!"
exit /b 0