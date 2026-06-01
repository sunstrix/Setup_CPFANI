@echo off
setlocal enabledelayedexpansion
title CPFANI - Manutencao de Rede e Impressoras V6

:: Cores ANSI
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"

echo ============================================================
echo      MANUTENCAO DE REDE E IMPRESSORAS - CP FANI V6
echo ============================================================

:: 1. Verificacao de Privilegios
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [%RED%ERRO%RESET%] Este script precisa ser executado como ADMINISTRADOR.
    pause
    exit /b
)

echo [%GREEN%INFO%RESET%] Iniciando reparo de rede e compartilhamentos...

:: 2. Reset de Pilha TCP/IP e DNS
echo [%YELLOW%1/5%RESET%] Resetando protocolos e cache DNS...
ipconfig /flushdns >nul
ipconfig /registerdns >nul
ipconfig /release >nul
ipconfig /renew >nul
netsh int ip reset >nul
netsh winsock reset >nul

:: 3. Forcar Perfil de Rede Privada (via PowerShell)
echo [%YELLOW%2/5%RESET%] Forcando Perfil de Rede 'Privado'...
powershell -NoProfile -Command "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private"

:: 4. Manutencao de Servicos de Impressao e Descoberta
echo [%YELLOW%3/5%RESET%] Reiniciando servicos de Impressao e Rede...
:: Spooler (Impressao), FdResPub (Descoberta), LanmanServer (Compartilhamento)
set "SERVICES=Spooler FdResPub LanmanServer SSDPDiscovery upnphost"
for %%S in (%SERVICES%) do (
    sc config %%S start= auto >nul
    net stop %%S /y >nul 2>&1
    net start %%S /y >nul
    echo    - Servico %%S: OK
)

:: 5. Liberacao de Compartilhamento no Firewall (Netsh)
echo [%YELLOW%4/5%RESET%] Abrindo regras de compartilhamento no Firewall...
netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes >nul
netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes >nul
netsh advfirewall firewall set rule group="Descoberta de Rede" new enable=Yes >nul

:: 6. Limpeza de Mapeamentos de Rede Presos
echo [%YELLOW%5/5%RESET%] Limpando conexoes de rede persistentes...
net use * /delete /y >nul 2>&1

:: 7. Habilitar Suporte a Impressoras WSD e SMB (Registro)
echo [%GREEN%INFO%RESET%] Ajustando politicas de registro para impressoras...
reg add "HKLM\Software\Policies\Microsoft\Windows NT\Printers" /v "ForceNetPrinters" /t REG_DWORD /d 1 /f >nul
reg add "HKLM\System\CurrentControlSet\Control\Print" /v "DisableRemoteSpooler" /t REG_DWORD /d 0 /f >nul

echo ============================================================
echo [%GREEN%SUCESSO%RESET%] Manutencao concluida! 
echo A maquina esta pronta para compartilhar arquivos e impressoras.
echo ============================================================
timeout /t 5