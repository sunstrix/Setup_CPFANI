@echo off
setlocal EnableDelayedExpansion
title Manutencao de Rede - Forca DHCP (V7.1)
color 0B

:: ==================================================
:: CONFIGURACAO DO LOG
:: ==================================================
set "LOG_DIR=C:\Scripts\Logs"
set "LOG_FILE=%LOG_DIR%\manutencao_rede.log"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

:: Testa permissao de escrita no diretorio de logs
echo test > "%LOG_DIR%\write_test.tmp" 2>nul
if !errorLevel! NEQ 0 (
    echo [ERRO] Sem permissao de escrita em %LOG_DIR%
    pause
    exit /b 1
)
del "%LOG_DIR%\write_test.tmp" 2>nul

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

call :log "=========================================="
call :log " INICIO DA MANUTENCAO DE REDE V7.1"
call :log " Correcao: Forca IP Manual -> DHCP"
call :log " Modo: Log Detalhado (Raw Output)"
call :log "=========================================="

net session >nul 2>&1
if !errorLevel! neq 0 (
    call :log "ERRO: Execute como administrador!"
    pause
    exit /b 1
)
call :log "[OK] Privilegios administrativos confirmados."

call :log "[1/8] Verificando conectividade atual..."
ping -n 1 -w 1000 8.8.8.8 >> "%LOG_FILE%" 2>&1
if !errorlevel! equ 0 (
    call :log "[OK] Internet detectada."
) else (
    call :log "[AVISO] Sem internet. Iniciando rotina de correcao..."
)

call :log "[2/8] Verificando adaptadores de rede ativos..."
powershell -NoProfile -Command "$adapters = Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' }; if ($adapters) { Write-Host ('OK|' + ($adapters | Measure-Object).Count) } else { Write-Host 'NONE'; exit 1 }" > "%TEMP%\net_check.tmp" 2>&1
set "NET_CHECK=!errorLevel!"
type "%TEMP%\net_check.tmp" >> "%LOG_FILE%" 2>&1
del "%TEMP%\net_check.tmp" 2>nul

if !NET_CHECK! neq 0 (
    call :log "[AVISO] Nenhum adaptador de rede fisico ativo detectado. Tentando correcao generica..."
)

call :log "[3/8] Forcando IP e DNS para Automatico (DHCP)..."
powershell -NoProfile -Command "try { $adapters = Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' }; if (-not $adapters) { Write-Host 'Nenhum adaptador ativo'; exit 0 } ; $adapters | ForEach-Object { Set-NetIPInterface -InterfaceIndex $_.ifIndex -Dhcp Enabled -ErrorAction Stop; Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses -ErrorAction Stop }; Write-Host 'DHCP_OK'; exit 0 } catch { Write-Host ('ERRO: ' + $_.Exception.Message); exit 1 }" > "%TEMP%\dhcp_out.tmp" 2>&1
set "DHCP_CODE=!errorLevel!"
type "%TEMP%\dhcp_out.tmp" >> "%LOG_FILE%" 2>&1
del "%TEMP%\dhcp_out.tmp" 2>nul

if !DHCP_CODE! neq 0 (
    call :log "[AVISO] Possivel erro ao configurar DHCP. Verifique o log acima."
) else (
    call :log "[OK] DHCP configurado com sucesso nos adaptadores ativos."
)

call :log "[4/8] Limpando cache DNS e renovando IP..."
ipconfig /flushdns >> "%LOG_FILE%" 2>&1
call :log "    -> Liberando IP atual..."
ipconfig /release >> "%LOG_FILE%" 2>&1
timeout /t 2 /nobreak >nul
call :log "    -> Renovando IP via DHCP..."
ipconfig /renew >> "%LOG_FILE%" 2>&1

call :log "[5/8] Configurando DNS padrao (Gateway ER605: 20.191.1.1)..."
powershell -NoProfile -Command "try { $adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq 'Up' }; if (-not $adapters) { exit 0 } ; $adapters | ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses ('20.191.1.1') -ErrorAction Stop }; exit 0 } catch { exit 1 }" > "%TEMP%\dns_out.tmp" 2>&1
set "DNS_CODE=!errorLevel!"
type "%TEMP%\dns_out.tmp" >> "%LOG_FILE%" 2>&1
del "%TEMP%\dns_out.tmp" 2>nul

if !DNS_CODE! neq 0 (
    call :log "[AVISO] Falha ao configurar DNS 20.191.1.1. Verifique adaptadores."
) else (
    call :log "[OK] DNS configurado: 20.191.1.1"
)

call :log "[6/8] Verificando integridade..."
ipconfig | findstr /i "IPv4" >> "%LOG_FILE%" 2>&1
if !errorlevel! neq 0 (
    call :log "[AVISO] Nenhum endereco IPv4 encontrado. Verifique a conexao."
) else (
    call :log "[OK] Endereco IPv4 detectado."
)

call :log "[7/8] Testando conectividade final..."
ping -n 2 -w 1000 20.191.1.1 >> "%LOG_FILE%" 2>&1
if !errorlevel! equ 0 (
    call :log "[OK] Gateway (ER605) alcancavel."
) else (
    call :log "[ERRO] Falha de comunicacao com o Gateway 20.191.1.1."
)

call :log "[8/8] Testando DNS..."
ping -n 1 -w 1000 www.google.com >> "%LOG_FILE%" 2>&1
if !errorlevel! equ 0 (
    call :log "[OK] Resolucao DNS funcionando."
) else (
    call :log "[ERRO] Falha na resolucao DNS."
)

call :log "[9/9] Exibindo configuracao final..."
ipconfig /all >> "%LOG_FILE%" 2>&1

call :log "=========================================="
call :log " MANUTENCAO CONCLUIDA."
call :log " Log completo: %LOG_FILE%"
call :log "=========================================="

echo.
echo Manutencao concluida. Log salvo em: %LOG_FILE%
pause