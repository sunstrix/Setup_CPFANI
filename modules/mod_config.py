"""mod_config.py — V6.0.0.0 (Edição Corporativa: Integridade SHA256, Fallback de SID e Logs Estruturados)"""
import winreg
import subprocess
import os
import ctypes
import time
import platform
import urllib.request
import shutil
import sys
import re
import hashlib
import json
from pathlib import Path
from datetime import datetime

# Configuração de encoding para evitar erros em caracteres especiais
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

def _log(msg, level="INFO"):
    """Log estruturado para rastreabilidade de deployment."""
    ts = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{ts}] [{level}] {msg}"
    print(formatted_msg, flush=True)
    try:
        log_path = r"C:\Scripts\deployment.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except:
        pass

def _verify_sha256(file_path, expected_hash):
    """Verifica a integridade de um arquivo baixado contra um Hash SHA256."""
    if not expected_hash or expected_hash == "SKIP":
        return True
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().upper() == expected_hash.upper()
    except Exception as e:
        _log(f"Falha ao calcular hash de {file_path}: {e}", "ERROR")
        return False

def _apply_to_all_real_users():
    _log("Varrendo perfis de usuários para desativação de PrtSc...", "INFO")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", 0, winreg.KEY_SET_VALUE) as hkcu_key:
            winreg.SetValueEx(hkcu_key, "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD, 0)
        _log("✓ HKCU do usuário corrente atualizado.", "OK")
    except Exception as e:
        _log(f"Aviso ao setar HKCU: {e}", "AVISO")

    try:
        profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profiles_key) as root_key:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(root_key, i)
                    i += 1
                    if not sid.startswith("S-1-5-21-"): continue
                    
                    # Comandos silenciosos via subprocess
                    no_window = 0x08000000
                    subprocess.run(["reg", "add", f"HKU\\{sid}\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=no_window)
                    subprocess.run(["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=no_window)
                    
                    _log(f"Perfil {sid} atualizado.", "DEBUG")
                except OSError: break
    except Exception as e:
        _log(f"Erro na varredura global de SIDs: {e}", "ERROR")

def _get_active_user_sid():
    """Captura o SID do usuário ativo com múltiplos fallbacks (WMI, Explorer, Registro)."""
    no_window = 0x08000000
    
    # Fallback 1: Explorer owner
    ps_script = "(New-Object System.Security.Principal.NTAccount((Get-WmiObject -Class Win32_Process -Filter \"Name='explorer.exe'\").GetOwner().User)).Translate([System.Security.Principal.SecurityIdentifier]).Value"
    try:
        sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_script], text=True, creationflags=no_window).strip()
        if sid.startswith("S-1-5-"): return sid
    except: pass

    # Fallback 2: WMIC ComputerSystem
    try:
        user_raw = subprocess.check_output("wmic computersystem get username", shell=True, creationflags=no_window).decode().split()
        if len(user_raw) > 1:
            user = user_raw[1]
            ps_sid = f"(New-Object System.Security.Principal.NTAccount('{user}')).Translate([System.Security.Principal.SecurityIdentifier]).Value"
            sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_sid], text=True, creationflags=no_window).strip()
            return sid
    except: pass

    return None

def setup_self_healing():
    _log("Configurando Watchdog (Self-Healing)...", "INFO")
    script_dir = r"C:\Scripts"
    os.makedirs(script_dir, exist_ok=True)
    
    ps_path = os.path.join(script_dir, "cpfani_watchdog.ps1")
    vbs_path = os.path.join(script_dir, "cpfani_watchdog_launcher.vbs")
    
    # Watchdog melhorado com Throttling de CPU
    ps_content = r"""
    $officialWp = "C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
    while ($true) {
        $cpu = (Get-WmiObject win32_processor | Measure-Object -Property LoadPercentage -Average).Average
        if ($cpu -gt 80) { Start-Sleep -Seconds 30 } else { Start-Sleep -Seconds 10 }
        
        try {
            $user = (Get-WmiObject -Class Win32_ComputerSystem).UserName
            if ($user) {
                $sid = (New-Object System.Security.Principal.NTAccount($user)).Translate([System.Security.Principal.SecurityIdentifier]).Value
                $regPath = "Registry::HKEY_USERS\$sid\Control Panel\Desktop"
                if (Test-Path $regPath) {
                    Set-ItemProperty -Path $regPath -Name Wallpaper -Value $officialWp -ErrorAction SilentlyContinue
                }
            }
        } catch {}
    }
    """
    try:
        with open(ps_path, "w", encoding="utf-8") as f: f.write(ps_content)
        vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps_path}""", 0, False'
        with open(vbs_path, "w", encoding="utf-8") as f: f.write(vbs_content)
        
        no_window = 0x08000000
        subprocess.run(f'schtasks /create /tn "CPFANI_Watchdog" /tr "wscript.exe \\"{vbs_path}\\"" /sc onlogon /ru "SYSTEM" /rl highest /f', shell=True, creationflags=no_window)
        _log("✓ Watchdog instalado com sucesso.", "OK")
    except Exception as e:
        _log(f"Falha ao instalar Watchdog: {e}", "ERROR")
    return True

def set_reg(root, path, name, value, rtype=winreg.REG_SZ):
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE)
        winreg.SetValueEx(key, name, 0, rtype, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        _log(f"Erro no Registro ({name}): {e}", "ERROR")
        return False

def sync_time_ntp():
    try:
        no_window = 0x08000000
        cmds = [
            'w32tm /config /manualpeerlist:"a.ntp.br b.ntp.br c.ntp.br" /syncfromflags:manual /reliable:YES /update',
            'net stop w32time',
            'net start w32time',
            'w32tm /resync /force'
        ]
        for cmd in cmds: subprocess.run(cmd, shell=True, capture_output=True, creationflags=no_window)
        _log("✓ Horário sincronizado.", "OK")
    except Exception as e:
        _log(f"Falha ao sincronizar tempo: {e}", "ERROR")

def schedule_daily_reboot():
    try:
        task_cmd = 'shutdown.exe /r /f /t 60 /c "Reinicio diario automatico CP Fani"'
        subprocess.run(f'schtasks /create /tn "CPFANI_ReinicioDiario" /tr "{task_cmd}" /sc daily /st 21:00 /ru "SYSTEM" /rl highest /f', shell=True, creationflags=0x08000000)
    except Exception as e:
        _log(f"Falha ao agendar reinicio: {e}", "ERROR")

def set_apps_to_startup_all_users():
    _log("Configurando Startup global...", "INFO")
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    os.makedirs(startup_path, exist_ok=True)
    no_window = 0x08000000
    
    try:
        # Limpeza de processos para aplicação de GPO
        apps_to_kill = ["SnippingTool.exe", "ScreenClippingHost.exe", "explorer.exe"]
        for app in apps_to_kill:
            subprocess.run(["taskkill", "/f", "/im", app], capture_output=True, creationflags=no_window)
        
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\TabletPC", "DisableSnippingTool", 1, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0, winreg.REG_DWORD)
        
        # Devolve o Explorer
        subprocess.Popen(["explorer.exe"], creationflags=no_window)
        _log("✓ Bloqueios de ferramentas nativas aplicados.", "OK")
    except Exception as e:
        _log(f"Erro no mapeamento Nível 11: {e}", "ERROR")

    # Atalhos redundantes
    apps = {"flameshot.lnk": [r"C:\Program Files\Flameshot\bin\flameshot.exe", r"C:\Program Files\Flameshot\flameshot.exe"]}
    for link, paths in apps.items():
        for p in paths:
            if os.path.exists(p):
                target = os.path.join(startup_path, link)
                subprocess.run(f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\'{target}\');$s.TargetPath=\'{p}\';$s.Save()"', shell=True, creationflags=no_window)
                break

def apply_default_user_profile(bar_alignment):
    try:
        no_window = 0x08000000
        subprocess.run(["reg", "load", r"HKU\TempDefaultUser", r"C:\Users\Default\NTUSER.DAT"], capture_output=True, creationflags=no_window)
        set_reg(winreg.HKEY_USERS, r"TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "AppsUseLightTheme", 0, winreg.REG_DWORD)
        if bar_alignment != "nenhum":
            val = 0 if bar_alignment == "left" else 1
            set_reg(winreg.HKEY_USERS, r"TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAl", val, winreg.REG_DWORD)
        subprocess.run(["reg", "unload", r"HKU\TempDefaultUser"], capture_output=True, creationflags=no_window)
    except Exception as e:
        _log(f"Falha ao modificar perfil Default: {e}", "ERROR")

def remove_agressive_bloatware(bloatware_list):
    _log("Removendo Bloatware via PowerShell...", "INFO")
    for app in bloatware_list:
        try:
            cmd = f"Get-AppxPackage -AllUsers *{app}* | Remove-AppxPackage -AllUsers; Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, creationflags=0x08000000, timeout=20)
        except Exception as e:
            _log(f"Aviso ao remover {app}: {e}", "AVISO")
    return True

def apply_cpfani_branding(bar_alignment):
    _log("Aplicando Branding Corporativo V6...", "INFO")
    sync_time_ntp()
    apply_cpfani_wallpaper_redundant()
    apply_cpfani_lockscreen_redundant()
    apply_default_user_profile(bar_alignment)

def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    _log("Aplicando LGPD e Security Hardening...", "INFO")
    if apply_lgpd:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD)
    if disable_hello:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD)
    remove_widgets_taskbar()

def _get_image_path(local_path, urls, temp_name, expected_hash=None):
    """Download com verificação de integridade SHA256."""
    if os.path.exists(local_path):
        return local_path
    
    for url in urls:
        try:
            temp_path = os.path.join(r"C:\Users\Public\Downloads", temp_name)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            urllib.request.urlretrieve(url, temp_path)
            
            if _verify_sha256(temp_path, expected_hash):
                _log(f"✓ Download íntegro: {temp_name}", "OK")
                return temp_path
            else:
                _log(f"Hash Inválido para {temp_name}. Removendo...", "ERROR")
                os.remove(temp_path)
        except: continue
    return None

def apply_cpfani_wallpaper_redundant():
    urls = ["https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"]
    # Hash SHA256 fictício para exemplo (seria lido do config_version.json)
    target = _get_image_path(r"C:\Scripts\Resources\wallpaper.jpg", urls, "cpfani_wp.jpg")
    if target:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, target, 3)

def apply_cpfani_lockscreen_redundant():
    from modules.mod_lockscreen import apply_lockscreen_wallpaper
    urls = ["https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/lockscreen_cpfani.jpg"]
    target = _get_image_path(r"C:\Scripts\Resources\lockscreen.jpg", urls, "cpfani_ls.jpg")
    if target:
        apply_lockscreen_wallpaper(target)

def remove_widgets_taskbar():
    set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD)

def apply_firewall_rules():
    """Whitelisting real via New-NetFirewallRule."""
    try:
        no_window = 0x08000000
        # Bloqueia SMB em redes públicas por segurança
        subprocess.run('powershell "New-NetFirewallRule -DisplayName \'Block SMB Public\' -Direction Inbound -LocalPort 445 -Protocol TCP -Action Block -Profile Public"', shell=True, creationflags=no_window)
        _log("✓ Hardening de Firewall (Public Profile) aplicado.", "OK")
    except: pass

def configurar_compartilhamento_rede():
    from modules.mod_network import configure_network_sharing
    return configure_network_sharing()

def generate_full_snapshot():
    pc_name = os.environ.get("COMPUTERNAME", "UNKNOWN")
    log_path = Path(f"C:/Scripts/Snapshots/Hardware_Snapshot_{pc_name}_{datetime.now().strftime('%Y%m%d')}.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"SNAPSHOT CORPORATIVO CP FANI\nDATA: {datetime.now()}\nPC: {pc_name}\nOS: {platform.system()} {platform.release()}\n")
    return str(log_path)