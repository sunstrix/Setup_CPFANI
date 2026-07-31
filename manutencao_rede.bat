$path = Join-Path $PWD "manutencao_rede.bat"
if (Test-Path $path) { Copy-Item $path "$path.bak" -Force }

$batContent = @'
@echo off
setlocal EnableDelayedExpansion
chcp 1252 >nul
title Manutencao de Rede - Forca DHCP (V7.3)
color 0B

:: ==================================================
:: CONFIGURACAO DO LOG
:: ==================================================
if not defined SCRIPT_DIR set "SCRIPT_DIR=C:\Scripts"
set "LOG_DIR=%SCRIPT_DIR%\Logs"

mkdir "%LOG_DIR%" 2>nul
if not exist "%LOG_DIR%" (
    set "LOG_DIR=C:\Logs\Rede"
    mkdir "!LOG_DIR!" 2>nul
)

if not exist "!LOG_DIR!" (
    echo [ERRO] Nao foi possivel criar pasta de logs.
    pause
    exit /b 1
)

set "LOG_FILE=!LOG_DIR!\manutencao_rede.log"
set "MAX_RETRIES=3"
set "RETRY_DELAY=3"
set "FAIL_COUNT=0"

goto :INICIO

:: ==================================================
:: FUNCAO DE LOG
:: ==================================================
:log
echo [%date% %time%] %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%"
exit /b 0

:: ==================================================
:: FUNCAO DE EXECUCAO COM VALIDACAO E RETENTATIVA
:: ==================================================
:run_cmd
set "LAST_RC=0"
set "ATTEMPT=0"

:run_cmd_retry
set /a ATTEMPT+=1
call :log "Executando: %STEP_DESC% (tentativa !ATTEMPT!/!MAX_RETRIES!)"

!CMD_TO_RUN! >> "%LOG_FILE%" 2>&1
set "LAST_RC=!ERRORLEVEL!"

if !LAST_RC! EQU 0 (
    call :log "[OK] %STEP_DESC% executado com sucesso."
    exit /b 0
)

call :log "[ERRO] %STEP_DESC% falhou com codigo !LAST_RC!."

if !ATTEMPT! LSS !MAX_RETRIES! (
    call :log "[INFO] Aguardando !RETRY_DELAY! segundos para nova tentativa..."
    timeout /t !RETRY_DELAY! /nobreak >nul 2>&1
    goto :run_cmd_retry
)

call :log "[ERRO] %STEP_DESC% falhou apos !MAX_RETRIES! tentativas."
exit /b !LAST_RC!

:: ==================================================
:: INICIO DO SCRIPT
:: ==================================================
:INICIO
net session >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    call :log "ERRO: Execute como administrador!"
    pause
    exit /b 1
)

call :log "=========================================="
call :log " INICIO DA MANUTENCAO DE REDE V7.3"
call :log " Correcao: Forca IP Manual -> DHCP"
call :log " Modo: Log Detalhado + Validacao + Retry"
call :log "=========================================="

call :log "[1/9] Verificando conectividade atual..."
set "STEP_DESC=[1/9] Ping inicial para 8.8.8.8"
set "CMD_TO_RUN=ping -n 1 -w 1000 8.8.8.8"
call :run_cmd
if !LAST_RC! EQU 0 (
    call :log "[OK] Internet detectada."
) else (
    call :log "[AVISO] Sem internet. Iniciando rotina de correcao..."
)

call :log "[2/9] Forcando IP e DNS para Automatico (DHCP)..."
set "STEP_DESC=[2/9] Forcar DHCP via PowerShell"
set "CMD_TO_RUN=powershell -NoProfile -Command "Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | ForEach-Object { Set-NetIPInterface -InterfaceIndex $_.ifIndex -Dhcp Enabled; Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }""
call :run_cmd
if !LAST_RC! NEQ 0 set /a FAIL_COUNT+=1

call :log "[3/9] Limpando cache DNS e renovando IP..."
set "STEP_DESC=[3/9] ipconfig /flushdns"
set "CMD_TO_RUN=ipconfig /flushdns"
call :run_cmd
if !LAST_RC! NEQ 0 set /a FAIL_COUNT+=1

set "STEP_DESC=[3/9] ipconfig /release"
set "CMD_TO_RUN=ipconfig /release *"
call :run_cmd
if !LAST_RC! NEQ 0 call :log "[AVISO] ipconfig /release retornou erro. Isso pode ser normal em interfaces sem DHCP."

set "STEP_DESC=[3/9] Aguardando antes do renew"
set "CMD_TO_RUN=ping -n 4 127.0.0.1"
call :run_cmd

set "STEP_DESC=[3/9] ipconfig /renew"
set "CMD_TO_RUN=ipconfig /renew *"
call :run_cmd
if !LAST_RC! NEQ 0 set /a FAIL_COUNT+=1

call :log "[4/9] Forcando perfil de rede para Privado..."
set "STEP_DESC=[4/9] Set-NetConnectionProfile Private"
set "CMD_TO_RUN=powershell -NoProfile -Command "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private""
call :run_cmd
if !LAST_RC! EQU 0 (
    call :log "[OK] Perfil de rede forcado para Privado com sucesso."
) else (
    call :log "[AVISO] Falha ao forcar perfil de rede para Privado."
    set /a FAIL_COUNT+=1
)

call :log "[5/9] Configurando DNS primario (1.1.1.1) e secundario (8.8.8.8)..."
set "STEP_DESC=[5/9] Set-DnsClientServerAddress 1.1.1.1 e 8.8.8.8"
set "CMD_TO_RUN=powershell -NoProfile -Command "Get-NetAdapter -Physical -ErrorAction SilentlyContinue | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses ('1.1.1.1','8.8.8.8') -ErrorAction SilentlyContinue }""
call :run_cmd
if !LAST_RC! EQU 0 (
    call :log "[OK] DNS configurado: 1.1.1.1 e 8.8.8.8"
) else (
    call :log "[AVISO] Falha ao configurar DNS."
    set /a FAIL_COUNT+=1
)

call :log "[6/9] Verificando integridade..."
set "STEP_DESC=[6/9] ipconfig | findstr IPv4"
set "CMD_TO_RUN=ipconfig | findstr /i "IPv4""
call :run_cmd
if !LAST_RC! NEQ 0 call :log "[AVISO] Nenhum endereco IPv4 listado."

call :log "[7/9] Testando conectividade final com o gateway (20.191.1.1)..."
set "STEP_DESC=[7/9] Ping gateway 20.191.1.1"
set "CMD_TO_RUN=ping -n 2 -w 1000 20.191.1.1"
call :run_cmd
if !LAST_RC! EQU 0 (
    call :log "[OK] Gateway (20.191.1.1) alcancavel."
) else (
    call :log "[ERRO] Falha de comunicacao com o Gateway."
    set /a FAIL_COUNT+=1
)

call :log "[8/9] Validando configuracoes finais..."
set "STEP_DESC=[8/9] net use"
set "CMD_TO_RUN=net use"
call :run_cmd
if !LAST_RC! NEQ 0 call :log "[AVISO] net use retornou erro."

set "STEP_DESC=[8/9] netsh interface ip show config"
set "CMD_TO_RUN=netsh interface ip show config"
call :run_cmd
if !LAST_RC! EQU 0 (
    call :log "[OK] Configuracoes validadas com sucesso."
) else (
    call :log "[AVISO] Falha ao validar configuracoes com netsh."
    set /a FAIL_COUNT+=1
)

call :log "[9/9] Manutencao de rede concluida."
if !FAIL_COUNT! GTR 0 (
    call :log "[AVISO] Manutencao concluida com !FAIL_COUNT! falha(s) registrada(s)."
) else (
    call :log "[OK] Manutencao concluida sem falhas."
)

exit /b 0
'@

$batContent = $batContent -replace "`r`n", "`n"
$batContent = $batContent -replace "`n", "`r`n"
[System.IO.File]::WriteAllText($path, $batContent, [System.Text.Encoding]::ASCII)

Write-Host "manutencao_rede.bat salvo com sucesso." -ForegroundColor Green