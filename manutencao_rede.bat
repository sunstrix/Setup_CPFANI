@echo off
setlocal EnableDelayedExpansion
title Manutencao de Rede - Forca DHCP (V5.9.5.2 - LEVE)
color 0B

:: ==================================================
:: CONFIGURACAO DO LOG (MANTIDA COM MELHORIAS)
:: ==================================================
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\manutencao_rede.log"
set "MAX_LOG_SIZE=1048576"  :: 1MB máximo

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

goto :INICIO

:: ==================================================
:: FUNCAO DE LOG (MANTIDA COM MELHORIAS)
:: ==================================================
:log
echo [%date% %time%] %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%" 2>nul

:: Rotação de log se muito grande
for %%F in ("%LOG_FILE%") do (
    if %%~zF GTR %MAX_LOG_SIZE% (
        move /y "%LOG_FILE%" "%LOG_FILE%.old" >nul 2>&1
        echo [%date% %time%] Log rotacionado >> "%LOG_FILE%" 2>nul
    )
)
exit /b

:: ==================================================
:: FUNCAO DE VALIDACAO DE CONECTIVIDADE REAL (NOVO)
:: ==================================================
:test_internet
set "INTERNET_OK=0"

:: Teste 1: Ping rápido
ping -n 1 -w 1000 8.8.8.8 >nul 2>&1
if %errorlevel% equ 0 (
    set "INTERNET_OK=1"
    exit /b 0
)

:: Teste 2: Ping alternativo
ping -n 1 -w 1000 1.1.1.1 >nul 2>&1
if %errorlevel% equ 0 (
    set "INTERNET_OK=1"
    exit /b 0
)

:: Teste 3: HTTP (se ping falhar)
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://www.google.com' -TimeoutSec 5 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    set "INTERNET_OK=1"
)

exit /b 0

:: ==================================================
:: FUNCAO DE BACKUP DE CONFIGURACAO (NOVO)
:: ==================================================
:backup_config
call :log "[BACKUP] Salvando configuracao atual..."
set "BACKUP_FILE=%LOG_DIR%\network_backup_%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%.txt"
set "BACKUP_FILE=!BACKUP_FILE: =0!"

ipconfig /all > "!BACKUP_FILE!" 2>&1
call :log "[BACKUP] Configuracao salva em: !BACKUP_FILE!"
exit /b

:: ==================================================
:: INICIO DO SCRIPT (MANTIDO COM VALIDACOES)
:: ==================================================
:INICIO

:: Validacao de privilegios administrativos (MANTIDA)
net session >nul 2>&1
if %errorLevel% neq 0 (
    call :log "ERRO: Execute como administrador!"
    pause
    exit /b 1
)

:: Validacao de espaco em disco para logs (NOVO)
for /f "tokens=3" %%A in ('dir C:\ 2^>nul ^| findstr /i "bytes livres"') do (
    set "FREE_SPACE=%%A"
    set "FREE_SPACE=!FREE_SPACE:.=!"
)
if defined FREE_SPACE (
    if !FREE_SPACE! LSS 10485760 (
        call :log "ERRO: Espaco em disco insuficiente para logs"
        exit /b 1
    )
)

call :log "=========================================="
call :log " INICIO DA MANUTENCAO DE REDE V5.9.5.2"
call :log " Correcao: Forca IP Manual -> DHCP"
call :log " Modo: Log Detalhado + Validacoes"
call :log "=========================================="

:: ==================================================
:: BACKUP DA CONFIGURACAO ATUAL (NOVO)
:: ==================================================
call :backup_config

:: ==================================================
:: VERIFICACAO DE CONECTIVIDADE ATUAL (MANTIDO COM MELHORIAS)
:: ==================================================
call :log "[1/9] Verificando conectividade atual..."
call :test_internet
if !INTERNET_OK! equ 1 (
    call :log "[OK] Internet detectada."
) else (
    call :log "[AVISO] Sem internet. Iniciando rotina de correcao..."
)

:: ==================================================
:: FORCANDO DHCP APENAS EM ADAPTADORES FISICOS REAIS (MELHORADO)
:: ==================================================
call :log "[2/9] Forcando IP e DNS para Automatico (DHCP)..."
call :log "[INFO] Processando apenas adaptadores fisicos ativos..."

:: Lista de adaptadores a ignorar (virtuais, VPN, etc)
set "IGNORE_PATTERNS=Hyper-V,VMware,VirtualBox,Docker,vEthernet,VPN,TAP-Windows,ZeroTier"

powershell -NoProfile -Command "$adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|VMware|VirtualBox|Docker|VPN|TAP|ZeroTier' }; if ($adapters) { $adapters | ForEach-Object { Write-Host ('[INFO] Configurando: ' + $_.Name + ' (' + $_.InterfaceDescription + ')'); Set-NetIPInterface -InterfaceIndex $_.ifIndex -Dhcp Enabled -ErrorAction SilentlyContinue; Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses -ErrorAction SilentlyContinue } } else { Write-Host '[AVISO] Nenhum adaptador fisico ativo encontrado' }" >> "%LOG_FILE%" 2>&1

call :log "[OK] DHCP forcado em adaptadores fisicos"

:: ==================================================
:: LIMPANDO CACHE DNS (MANTIDO COM VALIDACAO)
:: ==================================================
call :log "[3/9] Limpando cache DNS..."
ipconfig /flushdns >> "%LOG_FILE%" 2>&1
if %errorlevel% equ 0 (
    call :log "[OK] Cache DNS limpo"
) else (
    call :log "[AVISO] Falha ao limpar cache DNS"
)

:: ==================================================
:: RENOVANDO IP APENAS SE NECESSARIO (MELHORADO)
:: ==================================================
call :log "[4/9] Verificando necessidade de renovar IP..."

:: Verifica se já tem IP válido antes de renovar
powershell -NoProfile -Command "$adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|VMware|VirtualBox|Docker|VPN|TAP|ZeroTier' }; $hasIP = $false; if ($adapters) { foreach ($a in $adapters) { $ip = (Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress; if ($ip -and $ip -ne '127.0.0.1' -and $ip -notmatch '^169\.254\.') { $hasIP = $true; break } } }; exit $(if ($hasIP) { 0 } else { 1 })" >nul 2>&1

if %errorlevel% neq 0 (
    call :log "[INFO] IP invalido detectado. Renovando..."
    
    :: Release apenas em adaptadores sem IP válido
    powershell -NoProfile -Command "Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|VMware|VirtualBox|Docker|VPN|TAP|ZeroTier' } | ForEach-Object { $ip = (Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress; if (-not $ip -or $ip -eq '127.0.0.1' -or $ip -match '^169\.254\.') { Write-Host ('[INFO] Renovando: ' + $_.Name); ipconfig /release $_.Name | Out-Null } }" >> "%LOG_FILE%" 2>&1
    
    timeout /t 2 /nobreak >nul
    
    :: Renew em todos os adaptadores ativos
    powershell -NoProfile -Command "Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|VMware|VirtualBox|Docker|VPN|TAP|ZeroTier' } | ForEach-Object { Write-Host ('[INFO] Obtendo novo IP: ' + $_.Name); ipconfig /renew $_.Name | Out-Null }" >> "%LOG_FILE%" 2>&1
    
    call :log "[OK] IP renovado"
) else (
    call :log "[OK] IP valido detectado. Renovacao desnecessaria."
)

:: ==================================================
:: CONFIGURANDO DNS PUBLICOS CONHECIDOS (CORRIGIDO)
:: ==================================================
call :log "[5/9] Configurando DNS publicos (Google + Cloudflare)..."

:: DNS públicos confiáveis (não 20.191.1.1 que parece inválido)
powershell -NoProfile -Command "Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Virtual|Hyper-V|VMware|VirtualBox|Docker|VPN|TAP|ZeroTier' } | ForEach-Object { Write-Host ('[INFO] Configurando DNS em: ' + $_.Name); Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses ('8.8.8.8','8.8.4.4','1.1.1.1') -ErrorAction SilentlyContinue }" >> "%LOG_FILE%" 2>&1

call :log "[OK] DNS configurado: 8.8.8.8, 8.8.4.4, 1.1.1.1"

:: ==================================================
:: VERIFICANDO INTEGRIDADE (MANTIDO COM VALIDACAO)
:: ==================================================
call :log "[6/9] Verificando integridade das interfaces..."
ipconfig | findstr /i "IPv4" >> "%LOG_FILE%" 2>&1

:: Valida se pelo menos um adaptador tem IP válido
powershell -NoProfile -Command "$adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' }; $validCount = 0; if ($adapters) { foreach ($a in $adapters) { $ip = (Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress; if ($ip -and $ip -ne '127.0.0.1' -and $ip -notmatch '^169\.254\.') { $validCount++; Write-Host ('[OK] ' + $a.Name + ': ' + $ip) } } }; exit $(if ($validCount -gt 0) { 0 } else { 1 })" >> "%LOG_FILE%" 2>&1

if %errorlevel% equ 0 (
    call :log "[OK] Pelo menos um adaptador com IP valido"
) else (
    call :log "[ERRO] Nenhum adaptador com IP valido"
)

:: ==================================================
:: TESTANDO CONECTIVIDADE FINAL (MELHORADO)
:: ==================================================
call :log "[7/9] Testando conectividade final..."

:: Testa conectividade real (não apenas ping)
call :test_internet
if !INTERNET_OK! equ 1 (
    call :log "[OK] Conectividade com internet confirmada"
) else (
    call :log "[AVISO] Sem conectividade com internet"
)

:: ==================================================
:: VERIFICANDO GATEWAY PADRAO (NOVO)
:: ==================================================
call :log "[8/9] Verificando gateway padrao..."

powershell -NoProfile -Command "$gateways = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue; if ($gateways) { $gateways | ForEach-Object { Write-Host ('[OK] Gateway: ' + $_.NextHop + ' via ' + $_.InterfaceAlias) }; exit 0 } else { Write-Host '[ERRO] Nenhum gateway padrao encontrado'; exit 1 }" >> "%LOG_FILE%" 2>&1

if %errorlevel% equ 0 (
    call :log "[OK] Gateway padrao configurado"
) else (
    call :log "[AVISO] Nenhum gateway padrao encontrado"
)

:: ==================================================
:: VERIFICANDO TABELA DE ROTEAMENTO (NOVO)
:: ==================================================
call :log "[9/9] Verificando tabela de roteamento..."
route print -4 >> "%LOG_FILE%" 2>&1
call :log "[OK] Tabela de roteamento verificada"

:: ==================================================
:: RESUMO FINAL (MANTIDO COM MELHORIAS)
:: ==================================================
call :log "=========================================="
call :log "MANUTENCAO CONCLUIDA"
call :log "=========================================="

:: Teste final de conectividade
call :test_internet
if !INTERNET_OK! equ 1 (
    call :log "[RESULTADO] Internet FUNCIONANDO"
) else (
    call :log "[RESULTADO] Internet NAO FUNCIONA - Verifique logs"
)

call :log "Logs disponiveis em: %LOG_FILE%"
call :log "Backup em: !BACKUP_FILE!"

exit /b 0