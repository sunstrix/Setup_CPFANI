"""mod_config.py — V5.9.5.5 (Edição CP Fani: Desativação do PrtSc Nativo, Liberação Win+G, Isolamento do OneDrive e Reset de Cache)"""
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
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")[cite: 2]
    print(f"[{ts}] [{level}] {msg}", flush=True)[cite: 2]

def _apply_to_all_real_users():
    _log("Varrendo todos os perfis de usuários para desativar o atalho nativo do PrtSc...", "INFO")[cite: 2]
    
    # 1. Força a desativação diretamente no HKCU do processo atual
    try:[cite: 2]
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", 0, winreg.KEY_SET_VALUE) as hkcu_key:[cite: 2]
            winreg.SetValueEx(hkcu_key, "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD, 0)[cite: 2]
        _log("✓ Chave desativada com sucesso no HKCU do usuário corrente.", "OK")[cite: 2]
    except Exception as e:[cite: 2]
        _log(f"Aviso ao setar HKCU direto: {e}", "AVISO")[cite: 2]

    # 2. Varre todas as colmeias de perfis carregadas no sistema (SIDs)
    try:[cite: 2]
        profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"[cite: 2]
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profiles_key) as root_key:[cite: 2]
            i = 0[cite: 2]
            while True:[cite: 2]
                try:[cite: 2]
                    sid = winreg.EnumKey(root_key, i)[cite: 2]
                    i += 1[cite: 2]
                    if not sid.startswith("S-1-5-21-"):[cite: 2]
                        continue[cite: 2]
                    
                    try:[cite: 2]
                        # Desativa o interruptor de captura nativa das configurações do Windows
                        cmd_keyboard = ["reg", "add", f"HKU\\{sid}\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"][cite: 2]
                        subprocess.run(cmd_keyboard, capture_output=True, creationflags=0x08000000)[cite: 2]
                        
                        # Desativa a sincronização de acessibilidade que costuma reativar o botão sozinho
                        cmd_sync = ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"][cite: 2]
                        subprocess.run(cmd_sync, capture_output=True, creationflags=0x08000000)[cite: 2]
                        
                        # Remove ganchos secundários de ferramentas de nuvem concorrentes no perfil (OneDrive removido daqui)
                        subprocess.run(["reg", "add", f"HKU\\{sid}\\Software\\Dropbox\\Client", "/v", "CapturePrintScreen", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
                        
                        # Garante a configuração interna do Flameshot para este usuário
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{profiles_key}\\{sid}") as p_key:[cite: 2]
                            profile_path, _ = winreg.QueryValueEx(p_key, "ProfileImagePath")[cite: 2]
                            profile_path = os.path.expandvars(profile_path)[cite: 2]
                            if profile_path and "System32" not in profile_path:[cite: 2]
                                fs_dir = os.path.join(profile_path, "AppData", "Roaming", "flameshot")[cite: 2]
                                os.makedirs(fs_dir, exist_ok=True)[cite: 2]
                                fs_ini = os.path.join(fs_dir, "flameshot.ini")[cite: 2]
                                shortcut_block = "[Shortcuts]\ntakeScreenshot=Print\n"[cite: 2]
                                content = f"[General]\n\n{shortcut_block}"[cite: 2]
                                if os.path.exists(fs_ini):[cite: 2]
                                    with open(fs_ini, 'r', encoding='utf-8') as f: content = f.read()[cite: 2]
                                    content = re.sub(r"UsePrintScreen=.*?\n", "", content, flags=re.IGNORECASE)[cite: 2]
                                    if "[Shortcuts]" in content:[cite: 2]
                                        content = re.sub(r"takeScreenshot=.*", "takeScreenshot=Print", content)[cite: 2]
                                    else: content += f"\n{shortcut_block}"[cite: 2]
                                with open(fs_ini, 'w', encoding='utf-8') as f: f.write(content)[cite: 2]
                                
                    except Exception as e:[cite: 2]
                        _log(f"Aviso ao processar SID {sid}: {e}", "AVISO")[cite: 2]
                except OSError:[cite: 2]
                    break[cite: 2]
    except Exception as e:[cite: 2]
        _log(f"Falha na varredura global de SIDs: {e}", "AVISO")[cite: 2]

def _get_active_user_sid():
    ps_script = """
    $explorer = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1
    if ($explorer) {
        $owner = $explorer.GetOwner()
        $user = $owner.Domain + "\\" + $owner.User
        $ntAccount = New-Object System.Security.Principal.NTAccount($user)
        $sid = $ntAccount.Translate([System.Security.Principal.SecurityIdentifier]).Value
        Write-Output $sid
    }
    """
    try:
        sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_script], text=True, timeout=10, creationflags=0x08000000).strip()[cite: 2]
        return sid if sid.startswith("S-1-5-") else None[cite: 2]
    except: return None[cite: 2]

def setup_self_healing():
    _log("=" * 60, "INFO")[cite: 2]
    _log("INSTALANDO CAO DE GUARDA (SELF-HEALING)...", "INFO")[cite: 2]
    script_dir = r"C:\Scripts"[cite: 2]
    os.makedirs(script_dir, exist_ok=True)[cite: 2]
    
    ps_path = os.path.join(script_dir, "cpfani_watchdog.ps1")[cite: 2]
    vbs_path = os.path.join(script_dir, "cpfani_watchdog_launcher.vbs")[cite: 2]
    
    ps_content = r"""$officialWp = "C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
while ($true) {
    try {
        $explorers = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'"
        if ($explorers) {
            foreach ($exp in $explorers) {
                $owner = $exp.GetOwner()
                if ($owner.User) {
                    $user = $owner.Domain + "\" + $owner.User
                    $sid = (New-Object System.Security.Principal.NTAccount($user)).Translate([System.Security.Principal.SecurityIdentifier]).Value
                    $regPath = "Registry::HKEY_USERS\$sid\Control Panel\Desktop"
                    if (Test-Path $regPath) {
                        $currentWp = (Get-ItemProperty -Path $regPath -Name Wallpaper -ErrorAction SilentlyContinue).Wallpaper
                        if ($currentWp -ne $officialWp -and (Test-Path $officialWp)) {
                            Set-ItemProperty -Path $regPath -Name Wallpaper -Value $officialWp
                        }
                    }
                }
            }
        }
        $ad = Get-Service -Name "AnyDesk" -ErrorAction SilentlyContinue
        if ($ad -and $ad.Status -ne 'Running') { Start-Service -Name "AnyDesk" -ErrorAction SilentlyContinue }
    } catch {}
    Start-Sleep -Seconds 10
}
"""[cite: 2]
    with open(ps_path, "w", encoding="utf-8") as f: f.write(ps_content)[cite: 2]
    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps_path}""", 0, False'[cite: 2]
    with open(vbs_path, "w", encoding="utf-8") as f: f.write(vbs_content)[cite: 2]
        
    subprocess.run(f'schtasks /create /tn "CPFANI_Watchdog" /tr "wscript.exe \\"{vbs_path}\\"" /sc onlogon /ru "SYSTEM" /rl highest /f', shell=True, capture_output=True, creationflags=0x08000000)[cite: 2]
    subprocess.Popen(f'wscript.exe "{vbs_path}"', shell=True, creationflags=0x08000000)[cite: 2]
    _log("✓ Self-Healing (Watchdog) ativo e agendado.", "OK")[cite: 2]
    return True[cite: 2]

def set_reg(root, path, name, value, rtype=winreg.REG_SZ):
    try:[cite: 2]
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE)[cite: 2]
        winreg.SetValueEx(key, name, 0, rtype, value)[cite: 2]
        winreg.CloseKey(key)[cite: 2]
        return True[cite: 2]
    except: return False[cite: 2]

def sync_time_ntp():
    try:[cite: 2]
        cmds = ['w32tm /config /manualpeerlist:"a.ntp.br b.ntp.br c.ntp.br" /syncfromflags:manual /reliable:YES /update', 'net stop w32time', 'net start w32time', 'w32tm /resync /force'][cite: 2]
        for cmd in cmds: subprocess.run(cmd, shell=True, capture_output=True, creationflags=0x08000000)[cite: 2]
        _log("✓ Horário synchronized com ntp.br.", "OK")[cite: 2]
    except: pass[cite: 2]

def schedule_daily_reboot():
    try:[cite: 2]
        task_cmd = 'shutdown.exe /r /f /t 60 /c "Reinicio diario automatico CP Fani"'[cite: 2]
        subprocess.run(f'schtasks /create /tn "CPFANI_ReinicioDiario" /tr "{task_cmd}" /sc daily /st 21:00 /ru "SYSTEM" /rl highest /f', shell=True, capture_output=True, creationflags=0x08000000)[cite: 2]
    except: pass[cite: 2]

def set_apps_to_startup_all_users():
    _log("Configurando apps para abrir no login de TODOS os utilizadores (HKLM)...", "INFO")[cite: 2]
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"[cite: 2]
    os.makedirs(startup_path, exist_ok=True)[cite: 2]
    
    _log("Nivel 11: Sanando cache do Explorer e aplicando bloqueio do painel...", "INFO")[cite: 2]
    try:
        # Finaliza processos concorrentes (OneDrive removido completamente da purga)
        subprocess.run(["taskkill", "/f", "/im", "SnippingTool.exe"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["taskkill", "/f", "/im", "ScreenClippingHost.exe"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["taskkill", "/f", "/im", "flameshot.exe"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["taskkill", "/f", "/im", "sharex.exe"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, creationflags=0x08000000)[cite: 2]
        time.sleep(1.5)[cite: 2]
        
        # 1. Configura as GPOs administrativas locais para bloquear interceptações nativas (GPO OneDrive removida daqui)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\TabletPC", "DisableSnippingTool", 1, winreg.REG_DWORD)[cite: 2]
        
        # Desativa a Xbox Game Bar para libertar o atalho Win + G globalmente[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0, winreg.REG_DWORD)[cite: 2]
        sid = _get_active_user_sid()[cite: 2]
        if sid:[cite: 2]
            subprocess.run(["reg", "add", f"HKU\\{sid}\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR", "/v", "AppCaptureEnabled", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
            subprocess.run(["reg", "add", f"HKU\\{sid}\\System\\GameConfigStore", "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        
        # 2. Redireciona chamadas nativas remanescentes para o subsistema neutro rundll32 (Silêncio total)
        ifeo = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo}\\SnippingTool.exe", "Debugger", "rundll32.exe")[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo}\\ScreenClippingHost.exe", "Debugger", "rundll32.exe")[cite: 2]
        
        # 3. Aplica a alteração da hotkey em todos os registros de usuários
        _apply_to_all_real_users()[cite: 2]
        
        # 4. Devolve o ambiente gráfico imediatamente ao operador
        subprocess.Popen(["explorer.exe"], creationflags=0x08000000)[cite: 2]
        _log("✓ Interface do Windows Explorer reativada com sucesso.", "OK")[cite: 2]
        
    except Exception as e:[cite: 2]
        _log(f"Aviso no Mapeamento Geral Nível 11: {e}", "AVISO")[cite: 2]
    
    apps = {
        "flameshot.lnk": [r"C:\Program Files\Flameshot\bin\flameshot.exe", r"C:\Program Files\Flameshot\flameshot.exe"],[cite: 2]
        "sharex.lnk": [r"C:\Program Files\ShareX\ShareX.exe", r"C:\Program Files (x86)\ShareX\ShareX.exe"],[cite: 2]
        "anydesk.lnk": [r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe", r"C:\Program Files\AnyDesk\AnyDesk.exe"],[cite: 2]
        "teamviewer.lnk": [r"C:\Program Files\TeamViewer\TeamViewer.exe", r"C:\Program Files (x86)\TeamViewer\TeamViewer.exe"][cite: 2]
    }
    
    for link, paths in apps.items():[cite: 2]
        exe_found = None[cite: 2]
        for p in paths:[cite: 2]
            if os.path.exists(p): exe_found = p; break[cite: 2]
        if exe_found:[cite: 2]
            target = os.path.join(startup_path, link)[cite: 2]
            subprocess.run(f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\'{target}\');$s.TargetPath=\'{exe_found}\';$s.Save()"', shell=True, capture_output=True, creationflags=0x08000000)[cite: 2]

def apply_default_user_profile(bar_alignment):
    try:[cite: 2]
        subprocess.run(["reg", "load", r"HKU\TempDefaultUser", r"C:\Users\Default\NTUSER.DAT"], capture_output=True, check=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        if bar_alignment != "nenhum":[cite: 2]
            val = "0" if bar_alignment == "left" else "1"[cite: 2]
            subprocess.run(["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", val, "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["reg", "add", r"HKU\TempDefaultUser\Control Panel\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        subprocess.run(["reg", "unload", r"HKU\TempDefaultUser"], capture_output=True, check=True, creationflags=0x08000000)[cite: 2]
    except: pass[cite: 2]

def remove_agressive_bloatware(bloatware_list):
    for app in bloatware_list:[cite: 2]
        try:[cite: 2]
            cmd_user = f"Get-AppxPackage -AllUsers *{app}* | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"[cite: 2]
            cmd_prov = f"Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue"[cite: 2]
            subprocess.run(["powershell", "-NoProfile", "-Command", f"{cmd_user}; {cmd_prov}"], capture_output=True, text=True, timeout=15, creationflags=0x08000000)[cite: 2]
        except: pass[cite: 2]
    return True[cite: 2]

def apply_cpfani_branding(bar_alignment):
    _log("INICIANDO BRANDING CORPORATIVO...", "INFO")[cite: 2]
    sync_time_ntp()[cite: 2]
    path_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"[cite: 2]
    try:[cite: 2]
        sid = _get_active_user_sid()[cite: 2]
        if sid:[cite: 2]
            subprocess.run(["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
            subprocess.run(["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
    except: pass[cite: 2]
    apply_cpfani_wallpaper_redundant()[cite: 2]
    apply_cpfani_lockscreen_redundant()[cite: 2]
    if bar_alignment != "nenhum":[cite: 2]
        val = 0 if bar_alignment == "left" else 1[cite: 2]
        try:[cite: 2]
            sid = _get_active_user_sid()[cite: 2]
            if sid: subprocess.run(["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", str(val), "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        except: pass[cite: 2]
    apply_default_user_profile(bar_alignment)[cite: 2]

def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    _log("Aplicando politicas de Securitárias e LGPD...", "INFO")[cite: 2]
    sid = _get_active_user_sid()[cite: 2]
    if apply_lgpd:[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD)[cite: 2]
        if sid: subprocess.run(["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager", "/v", "SubscribedContent-338389Enabled", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin", "autoWorkplaceJoin", 0, winreg.REG_DWORD)[cite: 2]
    if disable_hello: disable_windows_hello_redundant()[cite: 2]
    remove_widgets_taskbar()[cite: 2]

def _get_image_path(local_path, urls, temp_name):
    if os.path.exists(local_path): return local_path[cite: 2]
    for url in urls:[cite: 2]
        try:[cite: 2]
            public_temp = r"C:\Users\Public\Downloads"; os.makedirs(public_temp, exist_ok=True)[cite: 2]
            temp_path = os.path.join(public_temp, temp_name); urllib.request.urlretrieve(url, temp_path)[cite: 2]
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 10000: return temp_path[cite: 2]
        except: pass[cite: 2]
    return None[cite: 2]

def apply_cpfani_wallpaper_redundant():
    script_dir = os.path.dirname(os.path.abspath(__file__)); local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")[cite: 2]
    urls = ["https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G", "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"][cite: 2]
    target_path = _get_image_path(local_wp, urls, "cpfani_wp.png")[cite: 2]
    if not target_path: return False[cite: 2]
    try: ctypes.windll.user32.SystemParametersInfoW(20, 0, target_path, 3)[cite: 2]
    except: pass[cite: 2]

def apply_cpfani_lockscreen_redundant():
    script_dir = os.path.dirname(os.path.abspath(__file__)); local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")[cite: 2]
    urls = ["https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G"][cite: 2]
    target_path = _get_image_path(local_wp, urls, "cpfani_ls.png")[cite: 2]
    if not target_path: return False[cite: 2]
    set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", target_path, winreg.REG_SZ)[cite: 2]

def disable_windows_hello_redundant():
    try:[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD)[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "Biometric", 0, winreg.REG_DWORD)[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WbioSrvc", "Start", 4, winreg.REG_DWORD)[cite: 2]
    except: pass[cite: 2]

def remove_widgets_taskbar():
    try:[cite: 2]
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD)[cite: 2]
        sid = _get_active_user_sid()[cite: 2]
        if sid: subprocess.run(["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\FileExplorer", "/v", "TaskbarDa", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True, creationflags=0x08000000)[cite: 2]
    except: pass[cite: 2]

def apply_firewall_rules():
    try: subprocess.run('netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes profile=private,domain', shell=True, capture_output=True, creationflags=0x08000000)[cite: 2]
    except: pass[cite: 2]

def schedule_manutencao_rede(): return True[cite: 2]
def schedule_instalar_tudo(): return True[cite: 2]
def _get_hardware_info(): return {"Nome_Computador": os.environ.get("COMPUTERNAME", platform.node())}[cite: 2]

def generate_full_snapshot():
    hw = _get_hardware_info(); pc_name = hw.get("Nome_Computador", "UNKNOWN")[cite: 2]
    log_path = Path(f"C:/Scripts/CPFANI_Hardware_Snapshot_{pc_name}.txt"); log_path.parent.mkdir(parents=True, exist_ok=True)[cite: 2]
    with open(log_path, "w", encoding="utf-8") as f: f.write(f"SNAPSHOT CP FANI\nPC: {pc_name}\n")[cite: 2]
    return str(log_path)[cite: 2]