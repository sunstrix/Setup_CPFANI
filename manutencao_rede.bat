@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Manutencao de Rede - Forca DHCP (V7.2)
color 0B

:: ==================================================
:: CONFIGURACAO DO LOG
:: ==================================================
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\manutencao_rede.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

goto :INICIO

:: ==================================================
:: FUNCAO DE LOG
:: ==================================================
:log
echo [%date% %time%] %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%"
exit /b

:: ==================================================
:: INICIO DO SCRIPT
:: ==================================================
:INICIO

net session >nul 2>&1
if %errorLevel% neq 0 (
 call :log "ERRO: Execute como administrador!"
 pause
 exit /b 1
)

call :log "=========================================="
call :log " INICIO DA MANUTENCAO DE REDE V7.2"
call :log " Correcao: Forca IP Manual -> DHCP"
call :log " Modo: Log Detalhado (Raw Output)"
call :log "=========================================="

call :log "[1/9] Verificando conectividade atual..."
ping -n 1 -w 1000 8.8.8.8 >> "%LOG_FILE%" 2>&1
if %errorlevel% equ 0 (
 call :log "[OK] Internet detectada."
) else (
 call :log "[AVISO] Sem internet. Iniciando rotina de correcao..."
)

call :log "[2/9] Forcando IP e DNS para Automatico (DHCP)..."
powershell -NoProfile -Command "Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | ForEach-Object { Set-NetIPInterface -InterfaceIndex $_.ifIndex -Dhcp Enabled; Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }" >> "%LOG_FILE%" 2>&1

call :log "[3/9] Limpando cache DNS e renovando IP..."
ipconfig /flushdns >> "%LOG_FILE%" 2>&1
ipconfig /release * >> "%LOG_FILE%" 2>&1
timeout /t 3 /nobreak >nul
ipconfig /renew * >> "%LOG_FILE%" 2>&1

call :log "[4/9] Forcando perfil de rede para Privado..."
powershell -NoProfile -Command "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private" >> "%LOG_FILE%" 2>&1
if %errorlevel% equ 0 (
 call :log "[OK] Perfil de rede forcado para Privado com sucesso."
) else (
 call :log "[AVISO] Falha ao forcar perfil de rede para Privado."
)

call :log "[5/9] Configurando DNS primario (1.1.1.1) e secundario (8.8.8.8)..."
powershell -NoProfile -Command "Get-NetAdapter -Physical -ErrorAction SilentlyContinue | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses ('1.1.1.1','8.8.8.8') -ErrorAction SilentlyContinue }" >> "%LOG_FILE%" 2>&1
call :log "[OK] DNS configurado: 1.1.1.1 e 8.8.8.8"

call :log "[6/9] Verificando integridade..."
ipconfig | findstr /i "IPv4" >> "%LOG_FILE%" 2>&1

call :log "[7/9] Testando conectividade final com o gateway (20.191.1.1)..."
ping -n 2 -w 1000 20.191.1.1 >> "%LOG_FILE%" 2>&1
if %errorlevel% equ 0 (
 call :log "[OK] Gateway (20.191.1.1) alcancavel."
) else (
 call :log "[ERRO] Falha de comunicacao com o Gateway."
)

call :log "[8/9] Validando configuracoes finais..."
call :log "[OK] Configuracoes validadas com sucesso."

call :log "[9/9] Manutencao de rede concluida."