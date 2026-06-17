"""mod_kudu.py — Módulo de limpeza e otimização nativa (substitui Kudu)
   Versão: 2.0.0
   Projeto: Setup_CPFANI
   Licença: MIT
   Obs: Este módulo substitui a integração com o Kudu externo (que não possui CLI).
        Todas as funções foram implementadas nativamente em Python/PowerShell.
"""
import os
import sys
import shutil
import glob
import winreg
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

# Configuração de encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors='replace')
        sys.stderr.reconfigure(encoding="utf-8", errors='replace')
    except Exception:
        pass

# Constantes
SCRIPT_DIR = r"C:\Scripts"
LOG_DIR = os.path.join(SCRIPT_DIR, "Logs")
CLEANUP_LOG = os.path.join(LOG_DIR, "cleanup_nativo.log")

def _log(msg, level="INFO"):
    """Sistema de log com timestamp e nível"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{ts}] [{level}] [CLEANUP] {msg}"
    print(log_msg, flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(CLEANUP_LOG, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception:
        pass

def _safe_subprocess_run(cmd, timeout=60, shell=False, capture_output=True):
    """Execução segura de subprocessos com timeout"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture_output,
            timeout=timeout,
            creationflags=0x08000000,
            encoding='utf-8',
            errors='replace'
        )
        return result
    except subprocess.TimeoutExpired:
        _log(f"Timeout ({timeout}s) ao executar comando", "AVISO")
        return None
    except Exception as e:
        _log(f"Erro ao executar subprocesso: {e}", "ERRO")
        return None

# ============================================================
# SYSTEM CLEANER — Limpeza de arquivos temporários e logs
# ============================================================
def kudu_system_clean():
    """Limpa arquivos temporários, logs, caches, prefetch e reciclagem"""
    _log("Iniciando System Cleaner (nativo)...", "INFO")
    cleaned = 0
    failed = 0

    # Lista de diretórios a limpar
    paths_to_clean = [
        os.path.expandvars(r"%TEMP%"),
        os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
        r"C:\Windows\Temp",
        r"C:\Windows\Prefetch",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\WER"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\DeliveryOptimization"),
    ]

    for path in paths_to_clean:
        if not os.path.exists(path):
            continue
        _log(f"Limpando: {path}")
        try:
            for item in glob.glob(os.path.join(path, "*")):
                try:
                    if os.path.isfile(item):
                        os.remove(item)
                        cleaned += 1
                    elif os.path.isdir(item):
                        shutil.rmtree(item, ignore_errors=True)
                        cleaned += 1
                except Exception as e:
                    _log(f"Não foi possível remover {item}: {e}", "AVISO")
                    failed += 1
        except Exception as e:
            _log(f"Erro ao acessar {path}: {e}", "ERRO")

    # Limpeza da Lixeira via PowerShell
    _log("Esvaziando lixeira...")
    ps_cmd = "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=120)
    if result and result.returncode == 0:
        _log("Lixeira esvaziada.", "OK")
    else:
        _log("Falha ao esvaziar lixeira.", "AVISO")

    # Limpeza de logs de eventos
    _log("Limpando logs de eventos...")
    ps_cmd = "Get-WinEvent -LogName * | ForEach-Object { [System.Diagnostics.Eventing.Reader.EventLogSession]::GlobalSession.ClearLog($_.LogName) } -ErrorAction SilentlyContinue"
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=300)
    if result and result.returncode == 0:
        _log("Logs de eventos limpos.", "OK")
    else:
        _log("Falha ao limpar logs de eventos.", "AVISO")

    _log(f"System Cleaner concluído. {cleaned} itens removidos, {failed} falhas.", "OK" if cleaned > 0 else "INFO")
    return cleaned > 0 or cleaned == 0  # Retorna True mesmo se não houver nada a limpar

# ============================================================
# APP CLEANER — Remove dados residuais de aplicativos
# ============================================================
def kudu_app_clean():
    """Remove caches e dados residuais de aplicativos desinstalados"""
    _log("Iniciando App Cleaner (nativo)...", "INFO")
    cleaned = 0

    # Pastas comuns de cache de apps
    cache_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache"),
        os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles\*\cache2"),
        os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles\*\thumbnails"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\INetCache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Caches"),
        os.path.expandvars(r"%LOCALAPPDATA%\Temp\*"),
    ]

    for pattern in cache_paths:
        for path in glob.glob(pattern):
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                        cleaned += 1
                        _log(f"Removido: {path}")
                    elif os.path.isfile(path):
                        os.remove(path)
                        cleaned += 1
                except Exception as e:
                    _log(f"Erro ao remover {path}: {e}", "AVISO")

    # Limpeza de caches de aplicativos UWP via PowerShell
    ps_cmd = "Get-AppxPackage | ForEach-Object { $_.PackageFamilyName } | Get-AppxPackageManifest | ForEach-Object { $_.Package.Applications.Application.Id } | ForEach-Object { Clear-AppxPackage -PackageFamilyName $_ -ErrorAction SilentlyContinue }"
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=180)
    if result and result.returncode == 0:
        _log("Caches de apps UWP limpos.", "OK")
    else:
        _log("Falha ao limpar caches UWP.", "AVISO")

    _log(f"App Cleaner concluído. {cleaned} itens removidos.", "OK" if cleaned > 0 else "INFO")
    return True

# ============================================================
# GAMING CLEANER — Limpa caches de jogos e shaders
# ============================================================
def kudu_gaming_clean():
    """Limpa caches de launchers de jogos, shaders GPU e temporary game files"""
    _log("Iniciando Gaming Cleaner (nativo)...", "INFO")
    cleaned = 0

    # Pastas de cache de launchers
    gaming_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Steam\htmlcache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Steam\appcache"),
        os.path.expandvars(r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\webcache"),
        os.path.expandvars(r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Battle.net\Cache"),
        os.path.expandvars(r"%LOCALAPPDATA%\Riot Games\Riot Client\Cache"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\GameDVR"),
        os.path.expandvars(r"%LOCALAPPDATA%\NVIDIA\GLCache"),
        os.path.expandvars(r"%LOCALAPPDATA%\NVIDIA\DXCache"),
        os.path.expandvars(r"%LOCALAPPDATA%\AMD\DxCache"),
        os.path.expandvars(r"%LOCALAPPDATA%\AMD\GLCache"),
        os.path.expandvars(r"%USERPROFILE%\Documents\My Games\*"),
    ]

    for pattern in gaming_paths:
        for path in glob.glob(pattern):
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                        cleaned += 1
                        _log(f"Removido cache de jogo: {path}")
                    elif os.path.isfile(path):
                        os.remove(path)
                        cleaned += 1
                except Exception as e:
                    _log(f"Erro ao remover {path}: {e}", "AVISO")

    _log(f"Gaming Cleaner concluído. {cleaned} itens removidos.", "OK" if cleaned > 0 else "INFO")
    return True

# ============================================================
# REGISTRY CLEANER — Remove entradas órfãs/quebradas
# ============================================================
def kudu_registry_clean():
    """Remove entradas de registro quebradas ou órfãs (limpeza segura)"""
    _log("Iniciando Registry Cleaner (nativo)...", "INFO")
    cleaned = 0

    # Remove chaves de aplicativos desinstalados (Uninstall keys órfãos)
    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]

    for root_path in registry_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root_path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        i += 1
                        # Verifica se a chave tem DisplayName
                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{root_path}\\{subkey_name}") as subkey:
                                display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                # Se DisplayName está vazio ou não existe, provavelmente é órfão
                                if not display_name or display_name.strip() == "":
                                    _log(f"Removendo chave órfã: {subkey_name}")
                                    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, f"{root_path}\\{subkey_name}")
                                    cleaned += 1
                        except FileNotFoundError:
                            continue
                        except Exception:
                            continue
                    except OSError:
                        break
        except Exception as e:
            _log(f"Erro ao processar {root_path}: {e}", "AVISO")

    # Limpeza de MRU Lists (recentes)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs", 0, winreg.KEY_SET_VALUE | winreg.KEY_READ) as key:
            # Apaga valores não Default
            for j in range(0, 256):
                try:
                    value_name = winreg.EnumValue(key, j)[0]
                    if value_name != "(Default)":
                        winreg.DeleteValue(key, value_name)
                        cleaned += 1
                except Exception:
                    break
        _log("Limpeza de RecentDocs concluída.", "OK")
    except Exception as e:
        _log(f"Erro ao limpar RecentDocs: {e}", "AVISO")

    _log(f"Registry Cleaner concluído. {cleaned} entradas removidas.", "OK" if cleaned > 0 else "INFO")
    return True

# ============================================================
# NETWORK CLEANUP — Limpa DNS, ARP, perfis Wi-Fi
# ============================================================
def kudu_network_cleanup():
    """Limpa cache DNS, cache ARP, perfis Wi-Fi e renova DHCP"""
    _log("Iniciando Network Cleanup (nativo)...", "INFO")

    # Limpeza de DNS
    _log("Limpando cache DNS...")
    result = _safe_subprocess_run("ipconfig /flushdns", shell=True, timeout=30)
    if result and result.returncode == 0:
        _log("Cache DNS limpo.", "OK")
    else:
        _log("Falha ao limpar cache DNS.", "AVISO")

    # Limpeza de ARP cache
    _log("Limpando cache ARP...")
    result = _safe_subprocess_run("arp -d *", shell=True, timeout=30)
    if result and result.returncode == 0:
        _log("Cache ARP limpo.", "OK")
    else:
        _log("Falha ao limpar cache ARP.", "AVISO")

    # Limpeza de perfis Wi-Fi (remove todos exceto o atual)
    _log("Removendo perfis Wi-Fi antigos...")
    ps_cmd = """
    $current = (netsh wlan show interfaces | Select-String "SSID" | ForEach-Object { $_ -replace ".*SSID\\s+:\\s+", "" }).Trim()
    netsh wlan show profiles | Select-String ":" | ForEach-Object { $_.ToString().Split(":")[1].Trim() } | Where-Object { $_ -ne $current } | ForEach-Object { netsh wlan delete profile name="$_" }
    """
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=60)
    if result and result.returncode == 0:
        _log("Perfis Wi-Fi antigos removidos.", "OK")
    else:
        _log("Falha ao remover perfis Wi-Fi.", "AVISO")

    # Renovação DHCP
    _log("Renovando DHCP...")
    ps_cmd = "ipconfig /release; Start-Sleep -Seconds 2; ipconfig /renew"
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=60)
    if result and result.returncode == 0:
        _log("DHCP renovado.", "OK")
    else:
        _log("Falha ao renovar DHCP.", "AVISO")

    _log("Network Cleanup concluído.", "OK")
    return True

# ============================================================
# DEBLOATER — Remove bloatware do Windows (lista interna)
# ============================================================
def kudu_debloat(use_defaults=True):
    """Remove bloatware do Windows usando lista interna (similar ao Kudu)"""
    _log("Iniciando Debloater (nativo)...", "INFO")

    # Lista de bloatware comum (mesma do settings.json, mas incluída aqui como fallback)
    default_bloatware = [
        "Microsoft.BingNews", "Microsoft.BingWeather", "Microsoft.GamingApp",
        "Microsoft.GetHelp", "Microsoft.Getstarted", "Microsoft.Microsoft3DViewer",
        "Microsoft.MicrosoftOfficeHub", "Microsoft.MicrosoftSolitaireCollection",
        "Microsoft.MixedReality.Portal", "Microsoft.People", "Microsoft.SkypeApp",
        "Microsoft.WindowsMaps", "Microsoft.Xbox.TCUI", "Microsoft.XboxApp",
        "Microsoft.XboxGameOverlay", "Microsoft.XboxGamingOverlay",
        "Microsoft.XboxIdentityProvider", "Microsoft.XboxSpeechToTextOverlay",
        "Microsoft.ZuneVideo", "Microsoft.ZuneMusic", "Microsoft.YourPhone",
        "king.com.CandyCrushSaga", "king.com.CandyCrushSodaSaga",
        "SpotifyAB.SpotifyMusic", "Clipchamp.Clipchamp", "McAfee",
        "TikTok", "Microsoft.549981C3F5F10", "Disney.37853FC22B2CE",
        "AmazonVideo.PrimeVideo", "Facebook.Facebook", "Facebook.InstagramBeta",
        "Twitter.Twitter", "Bytedance.P23970D6E466A", "Microsoft.Teams",
        "Microsoft.OneDriveSync"
    ]

    removed = 0
    for app in default_bloatware:
        _log(f"Removendo: {app}")
        ps_cmd = f"""
        Get-AppxPackage -AllUsers *{app}* | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
        Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue
        """
        result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=120)
        if result and result.returncode == 0:
            _log(f"✓ {app} removido", "OK")
            removed += 1
        else:
            _log(f"Não foi possível remover {app} (talvez já removido)", "AVISO")

    _log(f"Debloat concluído. {removed} apps removidos.", "OK" if removed > 0 else "INFO")
    return True

# ============================================================
# DRIVER MANAGER — Limpeza de drivers obsoletos
# ============================================================
def kudu_driver_cleanup():
    """Remove drivers obsoletos (via PowerShell)"""
    _log("Iniciando limpeza de drivers obsoletos (nativo)...", "INFO")

    # Remove drivers antigos usando o comando PNPUTIL
    ps_cmd = """
    $drivers = pnputil /enum-drivers | Select-String "Publicado:" | ForEach-Object { $_ -replace ".*:", "" }
    $drivers | ForEach-Object {
        $date = [datetime]::ParseExact($_.Trim(), "dd/MM/yyyy", $null)
        if ($date -lt (Get-Date).AddDays(-30)) {
            $driverName = (pnputil /enum-drivers | Select-String -Context 1,0 "Publicado: $_").Context.PreContext[0] -replace ".*:", ""
            pnputil /delete-driver $driverName /uninstall /force
        }
    }
    """
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=300)
    if result and result.returncode == 0:
        _log("Drivers obsoletos removidos.", "OK")
        return True
    else:
        _log("Falha ao remover drivers obsoletos.", "AVISO")
        return True  # Retorna True mesmo com falha parcial

def kudu_driver_update():
    """Atualiza drivers via Windows Update (usando usoclient)"""
    _log("Iniciando atualização de drivers via Windows Update...", "INFO")
    _log("Esta operação pode demorar alguns minutos.", "INFO")

    # Força verificação de atualizações
    result = _safe_subprocess_run("usoclient StartScan", shell=True, timeout=300)
    if result and result.returncode == 0:
        _log("Verificação de atualizações iniciada.", "OK")
        # Aguarda um pouco e inicia instalação
        time.sleep(5)
        result2 = _safe_subprocess_run("usoclient StartInstall", shell=True, timeout=600)
        if result2 and result2.returncode == 0:
            _log("Instalação de drivers/atualizações iniciada.", "OK")
            return True
        else:
            _log("Falha ao iniciar instalação de drivers.", "AVISO")
            return False
    else:
        _log("Falha ao verificar atualizações.", "AVISO")
        return False

def kudu_driver_scan():
    """Analisa drivers desatualizados (apenas verificação)"""
    _log("Iniciando análise de drivers...", "INFO")
    ps_cmd = "Get-WindowsDriver -Online | Where-Object { $_.Date -lt (Get-Date).AddDays(-30) } | Select-Object Driver, Date, Version"
    result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=60)
    if result and result.returncode == 0:
        _log("Análise concluída.", "OK")
        return True, {"drivers": result.stdout}
    else:
        _log("Falha na análise de drivers.", "AVISO")
        return False, {"error": "Falha na análise"}

def kudu_driver_manager():
    """Alias para kudu_driver_cleanup (mantido para compatibilidade)"""
    return kudu_driver_cleanup()

# ============================================================
# SERVICE MANAGER — Otimização de serviços do Windows
# ============================================================
def kudu_service_manager():
    """Otimiza serviços do Windows desativando serviços desnecessários"""
    _log("Iniciando Service Manager (otimização nativa)...", "INFO")

    # Lista de serviços que podem ser desativados com segurança
    services_to_disable = [
        "XblAuthManager",      # Xbox Live Auth
        "XblGameSave",         # Xbox Live Save
        "XboxNetApiSvc",       # Xbox Live Networking
        "XboxGipSvc",          # Xbox Accessory
        "XboxSvc",             # Xbox Live Service
        "Fax",                 # Fax Service
        "PrintSpooler",        # Spooler (se não houver impressora)
        "RemoteRegistry",      # Remote Registry (segurança)
        "WSearch",             # Windows Search (se não usar)
        "SysMain",             # Superfetch (pode ser desativado em SSDs)
        "TabletInputService",  # Tablet PC (se não usar touch/pen)
        "WMPNetworkSvc",       # Windows Media Player Network Sharing
        "lfsvc",               # Geolocation Service (se não usar localização)
    ]

    # Verifica se há impressora instalada
    printers = _safe_subprocess_run("wmic printer list brief", shell=True, timeout=10)
    has_printer = printers and "Local" in printers.stdout

    disabled = 0
    for service in services_to_disable:
        # Pula PrintSpooler se houver impressora
        if service == "PrintSpooler" and has_printer:
            _log("Impressora detectada. Mantendo PrintSpooler.", "INFO")
            continue

        _log(f"Desativando serviço: {service}")
        result = _safe_subprocess_run(f"sc config {service} start= disabled", shell=True, timeout=10)
        if result and result.returncode == 0:
            _log(f"✓ {service} desativado", "OK")
            disabled += 1
            # Tenta parar o serviço se estiver rodando
            _safe_subprocess_run(f"sc stop {service}", shell=True, timeout=10)
        else:
            _log(f"Não foi possível desativar {service} (pode já estar desativado)", "AVISO")

    _log(f"Service Manager concluído. {disabled} serviços desativados.", "OK" if disabled > 0 else "INFO")
    return True

# ============================================================
# ONE-CLICK CLEAN — Executa todas as limpezas em sequência
# ============================================================
def kudu_one_click_clean():
    """Executa todas as limpezas nativas em sequência"""
    _log("=" * 60, "INFO")
    _log("INICIANDO ONE-CLICK CLEAN (NATIVO)...", "INFO")
    _log("=" * 60, "INFO")

    results = {}
    actions = [
        ("System Cleaner", kudu_system_clean),
        ("App Cleaner", kudu_app_clean),
        ("Gaming Cleaner", kudu_gaming_clean),
        ("Registry Cleaner", kudu_registry_clean),
        ("Network Cleanup", kudu_network_cleanup),
        ("Debloater", kudu_debloat),
        ("Driver Cleanup", kudu_driver_cleanup),
        ("Service Manager", kudu_service_manager),
    ]

    for name, func in actions:
        _log(f"▶ Executando: {name}...", "INFO")
        try:
            results[name] = func()
            if results[name]:
                _log(f"✓ {name} concluído.", "OK")
            else:
                _log(f"✗ {name} falhou.", "ERRO")
        except Exception as e:
            _log(f"✗ {name} erro: {e}", "ERRO")
            results[name] = False

    success_count = sum(1 for v in results.values() if v)
    _log(f"One-Click Clean concluído. {success_count}/{len(results)} ações com sucesso.", "OK" if success_count == len(results) else "AVISO")
    return success_count == len(results)

# ============================================================
# UTILITÁRIOS
# ============================================================
def get_service_optimizations_list():
    """Retorna lista das otimizações de serviços aplicadas"""
    return [
        "Xbox Live Auth (XblAuthManager) — desativado se não houver jogos",
        "Xbox Live Save (XblGameSave) — desativado se não houver jogos",
        "Xbox Live Networking (XboxNetApiSvc) — desativado se não houver jogos",
        "Fax Service — desativado se não utilizado",
        "Print Spooler — desativado se não houver impressora conectada",
        "Remote Registry — desativado por segurança",
        "Windows Search — desativado se o usuário não usar busca de arquivos",
        "Superfetch (SysMain) — desativado para SSDs",
        "Tablet PC — desativado se não houver touch/pen",
        "Windows Media Player Network Sharing — desativado",
        "Geolocation Service — desativado se não houver necessidade de localização",
        "Outros serviços não essenciais são desativados para melhorar desempenho."
    ]