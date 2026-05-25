"""mod_config.py — V5.9.3.4 (Edição Infiltrado: Whitelist, Self-Healing, Choque no Shell PrintScreen)"""
import winreg
import subprocess
import os
import ctypes
import time
import platform
import urllib.request
import shutil
import sys
from pathlib import Path
from datetime import datetime
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

# ====================================================================
# LÓGICA DO INFILTRADO: DETEÇÃO DE CROSS-ELEVATION (UAC CROSSING)
# ====================================================================
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
        sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_script], text=True, timeout=10).strip()
        return sid if sid.startswith("S-1-5-") else None
    except: return None

def set_reg_active_user(path, name, value, rtype=winreg.REG_SZ):
    sid = _get_active_user_sid()
    if sid:
        full_path = f"{sid}\\{path}"
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_USERS, full_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
            winreg.SetValueEx(key, name, 0, rtype, value)
            winreg.CloseKey(key)
            return True
        except: pass
    return set_reg(winreg.HKEY_CURRENT_USER, path, name, value, rtype)

def delete_reg_active_user(path, name):
    sid = _get_active_user_sid()
    if sid:
        full_path = f"{sid}\\{path}"
        try:
            key = winreg.OpenKey(winreg.HKEY_USERS, full_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
        except: pass
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except: pass
# ====================================================================

# --- LÓGICA DO SELF-HEALING (CÃO DE GUARDA) ---
def setup_self_healing():
    _log("=" * 60, "INFO")
    _log("INSTALANDO CAO DE GUARDA (SELF-HEALING)...", "INFO")
    script_dir = r"C:\Scripts"
    os.makedirs(script_dir, exist_ok=True)
    
    ps_path = os.path.join(script_dir, "cpfani_watchdog.ps1")
    vbs_path = os.path.join(script_dir, "cpfani_watchdog_launcher.vbs")
    
    ps_content = r"""$officialWp = "C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"

try {
    Add-Type -TypeDefinition @"
    using System;
    using System.Runtime.InteropServices;
    public class WpUpdater {
        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
        public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
    }
"@ -ErrorAction SilentlyContinue
} catch {}

while ($true) {
    try {
        $explorers = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'"
        if ($explorers) {
            foreach ($exp in $explorers) {
                $owner = $exp.GetOwner()
                if ($owner.User) {
                    $user = $owner.Domain + "\" + $owner.User
                    $ntAccount = New-Object System.Security.Principal.NTAccount($user)
                    $sid = $ntAccount.Translate([System.Security.Principal.SecurityIdentifier]).Value
                    
                    $regPath = "Registry::HKEY_USERS\$sid\Control Panel\Desktop"
                    if (Test-Path $regPath) {
                        $currentWp = (Get-ItemProperty -Path $regPath -Name Wallpaper -ErrorAction SilentlyContinue).Wallpaper
                        if ($currentWp -ne $officialWp -and (Test-Path $officialWp)) {
                            Set-ItemProperty -Path $regPath -Name Wallpaper -Value $officialWp
                            [WpUpdater]::SystemParametersInfo(20, 0, $officialWp, 3) | Out-Null
                        }
                    }
                }
            }
        }
        
        $ad = Get-Service -Name "AnyDesk" -ErrorAction SilentlyContinue
        if ($ad -and $ad.Status -ne 'Running') {
            Start-Service -Name "AnyDesk" -ErrorAction SilentlyContinue
        }
    } catch {}
    Start-Sleep -Seconds 10
}
"""
    
    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(ps_content)
        
    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps_path}""", 0, False'
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)
        
    cmd = f'schtasks /create /tn "CPFANI_Watchdog" /tr "wscript.exe \\"{vbs_path}\\"" /sc onlogon /ru "SYSTEM" /rl highest /f'
    subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    subprocess.Popen(f'wscript.exe "{vbs_path}"', shell=True)
    
    _log("✓ Self-Healing (Watchdog) ativo e agendado.", "OK")
    return True

def set_reg(root, path, name, value, rtype=winreg.REG_SZ):
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
        winreg.SetValueEx(key, name, 0, rtype, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        _log(f"[REG ERROR] Falha ao setar {path}\\{name}: {e}", "AVISO")
        return False

def get_reg(root, path, name):
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        value, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return value
    except:
        return None

def sync_time_ntp():
    _log("Sincronizando relógio do sistema com ntp.br...", "INFO")
    try:
        cmds = [
            'w32tm /config /manualpeerlist:"a.ntp.br b.ntp.br c.ntp.br" /syncfromflags:manual /reliable:YES /update',
            'net stop w32time',
            'net start w32time',
            'w32tm /resync /force'
        ]
        for cmd in cmds:
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
        _log("✓ Horário sincronizado com ntp.br.", "OK")
        return True
    except Exception as e:
        _log(f"Falha ao sincronizar NTP: {e}", "AVISO")
        return False

def schedule_daily_reboot():
    _log("Agendando reinício diário automático para as 21:00...", "INFO")
    try:
        task_cmd = 'shutdown.exe /r /f /t 60 /c "Reinicio diario automatico CP Fani"'
        cmd = f'schtasks /create /tn "CPFANI_ReinicioDiario" /tr "{task_cmd}" /sc daily /st 21:00 /ru "SYSTEM" /rl highest /f'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            _log("✓ Reinício diário agendado com sucesso (21:00).", "OK")
            return True
        return False
    except Exception as e:
        _log(f"Erro ao agendar reinício: {e}", "AVISO")
        return False

def _restart_explorer():
    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True)
    time.sleep(2)
    subprocess.Popen("explorer.exe")

def set_apps_to_startup_all_users():
    _log("Configurando apps para abrir no login de TODOS os utilizadores (HKLM)...", "INFO")
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    os.makedirs(startup_path, exist_ok=True)
    
    # --- REDUNDÂNCIA FLAMESHOT / PRINTSCREEN (NÍVEL 7: CHOQUE NO SHELL) ---
    _log("Nivel 7: Forcando libertacao da tecla PrintScreen e reiniciando shell...", "INFO")
    try:
        # 1. Registo Utilizador Atual e Default
        set_reg_active_user(r"Control Panel\Keyboard", "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\TabletPC", "DisableSnippingTool", 1, winreg.REG_DWORD)
        
        subprocess.run(["reg", "load", r"HKU\TempDefaultUser", r"C:\Users\Default\NTUSER.DAT"], capture_output=True)
        set_reg(winreg.HKEY_USERS, r"TempDefaultUser\Control Panel\Keyboard", "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD)
        subprocess.run(["reg", "unload", r"HKU\TempDefaultUser"], capture_output=True)
        
        # 2. Desinstalacao Agressiva
        ps_nuke_snipping = """
        $ErrorActionPreference = 'SilentlyContinue'
        Get-AppxPackage -AllUsers *ScreenSketch* | Remove-AppxPackage -AllUsers
        Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -match 'ScreenSketch'} | Remove-AppxProvisionedPackage -Online
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_nuke_snipping], capture_output=True)
        
        # 3. Mata processos teimosos
        subprocess.run(["taskkill", "/f", "/im", "SnippingTool.exe"], capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "ScreenClippingHost.exe"], capture_output=True)
        subprocess.run(["taskkill", "/f", "/im", "flameshot.exe"], capture_output=True) # Mata flameshot se ja estiver aberto sem a tecla
        
        # 4. CHOQUE NO SHELL: Reinicia o Explorer para forcar o Windows a ler o registo novo e largar a tecla da RAM
        _restart_explorer()
        
        # 5. Acorda o Flameshot agora que o caminho esta livre
        flameshot_exe = r"C:\Program Files\Flameshot\bin\flameshot.exe"
        if not os.path.exists(flameshot_exe): flameshot_exe = r"C:\Program Files\Flameshot\flameshot.exe"
        if os.path.exists(flameshot_exe):
            subprocess.Popen([flameshot_exe])
            
    except Exception as e:
        _log(f"Aviso no Nivel 7 PrintScreen: {e}", "AVISO")
    # ----------------------------------------------------------------------
    
    apps = {
        "flameshot.lnk": [r"C:\Program Files\Flameshot\bin\flameshot.exe", r"C:\Program Files\Flameshot\flameshot.exe"],
        "anydesk.lnk": [r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe", r"C:\Program Files\AnyDesk\AnyDesk.exe"],
        "teamviewer.lnk": [r"C:\Program Files\TeamViewer\TeamViewer.exe", r"C:\Program Files (x86)\TeamViewer\TeamViewer.exe"]
    }
    
    for link, paths in apps.items():
        exe_found = None
        for p in paths:
            if os.path.exists(p):
                exe_found = p
                break
        
        if exe_found:
            target = os.path.join(startup_path, link)
            cmd = f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\'{target}\');$s.TargetPath=\'{exe_found}\';$s.Save()"'
            subprocess.run(cmd, shell=True, capture_output=True)
            _log(f"✓ {link} configurado no Startup Global.", "OK")

def apply_default_user_profile(bar_alignment):
    _log("=" * 60, "INFO")
    _log("INJETANDO DEFINICOES GLOBAIS NO DEFAULT USER PROFILE (NTUSER.DAT)...", "INFO")
    _log("=" * 60, "INFO")
    try:
        subprocess.run(["reg", "load", r"HKU\TempDefaultUser", r"C:\Users\Default\NTUSER.DAT"], capture_output=True, check=True)
        
        path_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        set_reg(winreg.HKEY_USERS, f"TempDefaultUser\\{path_theme}", "SystemUsesLightTheme", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_USERS, f"TempDefaultUser\\{path_theme}", "AppsUseLightTheme", 0, winreg.REG_DWORD)
        
        if bar_alignment != "nenhum":
            val = 0 if bar_alignment == "left" else 1
            set_reg(winreg.HKEY_USERS, r"TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAl", val, winreg.REG_DWORD)
        
        set_reg(winreg.HKEY_USERS, r"TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarDa", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_USERS, r"TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", 0, winreg.REG_DWORD)
        
        try:
            key = winreg.OpenKey(winreg.HKEY_USERS, r"TempDefaultUser\Software\Microsoft\Office\16.0\Common\SignIn", 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteValue(key, "SignInOptions")
            winreg.CloseKey(key)
        except: pass

        subprocess.run(["reg", "unload", r"HKU\TempDefaultUser"], capture_output=True, check=True)
        _log("✓ Definições Globais injetadas no Molde do Windows.", "OK")
        return True
    except Exception as e:
        _log(f"✗ Falha ao manipular NTUSER.DAT: {e}", "ERRO")
        subprocess.run(["reg", "unload", r"HKU\TempDefaultUser"], capture_output=True)
        return False

def remove_agressive_bloatware(bloatware_list):
    _log("=" * 60, "INFO")
    _log("PURGANDO BLOATWARE AGRESSIVAMENTE...", "INFO")
    _log("=" * 60, "INFO")
    success_count = 0
    for app in bloatware_list:
        try:
            cmd_user = f"Get-AppxPackage -AllUsers *{app}* | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"
            cmd_prov = f"Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", f"{cmd_user}; {cmd_prov}"], capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                success_count += 1
        except Exception as e:
            _log(f"Falha ao remover {app}: {e}", "AVISO")
    _log(f"✓ Purga de Bloatware concluída. {success_count} pacotes processados globalmente.", "OK")
    return True

def apply_cpfani_branding(bar_alignment):
    _log("INICIANDO BRANDING CORPORATIVO...", "INFO")
    sync_time_ntp()
    path_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    
    set_reg_active_user(path_theme, "SystemUsesLightTheme", 0, winreg.REG_DWORD)
    set_reg_active_user(path_theme, "AppsUseLightTheme", 0, winreg.REG_DWORD)
    
    apply_cpfani_wallpaper_redundant()
    apply_cpfani_lockscreen_redundant()

    if bar_alignment != "nenhum":
        val = 0 if bar_alignment == "left" else 1
        set_reg_active_user(r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAl", val, winreg.REG_DWORD)
        
    apply_default_user_profile(bar_alignment)

def _get_image_path(local_path, urls, temp_name):
    if os.path.exists(local_path): return local_path
    for i, url in enumerate(urls, 1):
        try:
            public_temp = r"C:\Users\Public\Downloads"
            os.makedirs(public_temp, exist_ok=True)
            temp_path = os.path.join(public_temp, temp_name)
            urllib.request.urlretrieve(url, temp_path)
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 10000: return temp_path
        except Exception as e:
            _log(f"Falha no download URL {i}: {e}", "AVISO")
    return None

def _set_wallpaper_api(image_path):
    try: ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3); return True
    except Exception as e: return False

def _set_wallpaper_registry(image_path):
    try:
        set_reg_active_user(r"Control Panel\Desktop", "Wallpaper", image_path, winreg.REG_SZ)
        set_reg_active_user(r"Control Panel\Desktop", "WallpaperStyle", "10", winreg.REG_SZ)
        set_reg_active_user(r"Control Panel\Desktop", "TileWallpaper", "0", winreg.REG_SZ)
        return True
    except Exception as e: return False

def _set_wallpaper_system_dir(image_path):
    try:
        sys_dir = Path(r"C:\Windows\Web\Wallpaper\Windows")
        sys_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(f'takeown /f "{sys_dir}" /r /d s', shell=True, capture_output=True)
        subprocess.run(f'icacls "{sys_dir}" /grant Administradores:F /t', shell=True, capture_output=True)
        
        for name in ["img0.jpg", "wallpaper.jpg", "cpfani_wallpaper.jpg"]: 
            shutil.copy2(image_path, str(sys_dir / name))
        return True
    except Exception as e: return False

def _set_wallpaper_powershell(image_path):
    try:
        ps_script = f"""
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class Wallpaper {{
            [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
            private static extern int SystemParametersInfo (int uAction, int uParam, string lpvParam, int fuWinIni);
            public static void SetWallpaper(string path) {{ SystemParametersInfo(20, 0, path, 3); }}
        }}
        "@
        [Wallpaper]::SetWallpaper('{image_path}')
        """
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception as e: return False

def _set_wallpaper_gpo(image_path):
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "Wallpaper", image_path, winreg.REG_SZ)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "WallpaperStyle", "10", winreg.REG_SZ)
        subprocess.run(["gpupdate", "/force", "/wait:0"], capture_output=True, timeout=30)
        return True
    except Exception as e: return False

def apply_cpfani_wallpaper_redundant():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://i.postimg.cc/vmhHRdrh/SUPRIMENTOS-(4)-upscayl-3x-digital-art-4x.png",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]
    target_path = _get_image_path(local_wp, urls, "cpfani_wp.png")
    if not target_path: return False
    
    success_count = sum([_set_wallpaper_api(target_path), _set_wallpaper_registry(target_path), _set_wallpaper_system_dir(target_path), _set_wallpaper_powershell(target_path), _set_wallpaper_gpo(target_path)])
    return success_count >= 3

def _set_lockscreen_registry(image_path):
    try: set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", image_path, winreg.REG_SZ); return True
    except Exception as e: return False

def _disable_spotlight(image_path):
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableWindowsSpotlightOnLockScreen", 1, winreg.REG_DWORD)
        set_reg_active_user(r"Software\Microsoft\Windows\CurrentVersion\Lock Screen", "RotatingLockScreenEnabled", 0, winreg.REG_DWORD)
        return True
    except Exception as e: return False

def _set_lockscreen_system_dir(image_path):
    try:
        screen_dirs = [Path(r"C:\Windows\Web\Screen"), Path(r"C:\Windows\System32\drivers\etc\lockscreen")]
        for screen_dir in screen_dirs:
            try:
                screen_dir.mkdir(parents=True, exist_ok=True)
                for name in ["lockscreen_cpfani.jpg", "lockscreen.jpg", "img0.jpg"]: shutil.copy2(image_path, str(screen_dir / name))
            except Exception as e: pass
        return True
    except Exception as e: return False

def _set_lockscreen_powershell(image_path):
    try:
        ps_script = f"""
        $RegPath = "HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Personalization"
        if(!(Test-Path $RegPath)) {{ New-Item -Path $RegPath -Force | Out-Null }}
        New-ItemProperty -Path $RegPath -Name "LockScreenImage" -Value '{image_path}' -PropertyType String -Force | Out-Null
        """
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=15)
        return result.returncode == 0
    except Exception as e: return False

def apply_cpfani_lockscreen_redundant():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://i.postimg.cc/vmhHRdrh/SUPRIMENTOS-(4)-upscayl-3x-digital-art-4x.png",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]
    target_path = _get_image_path(local_wp, urls, "cpfani_ls.png")
    if not target_path: return False
    
    success_count = sum([_set_lockscreen_registry(target_path), _disable_spotlight(target_path), _set_lockscreen_system_dir(target_path), _set_lockscreen_powershell(target_path)])
    return success_count >= 3

def disable_windows_hello_redundant():
    _log("=" * 60, "INFO")
    _log("DESABILITANDO TELA DE BOAS-VINDAS E WINDOWS HELLO...", "INFO")
    _log("=" * 60, "INFO")
    success_count = 0
    
    try:
        set_reg_active_user(r"Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", 0, winreg.REG_DWORD)
        set_reg_active_user(r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-310093Enabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableWindowsConsumerFeatures", 1, winreg.REG_DWORD)
        success_count += 1
        _log("[1/10] SCOOBE bloqueado.", "OK")
    except Exception as e: _log(f"[1/10] Erro SCOOBE: {e}", "AVISO")

    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "DisablePostLogonProvisioning", 1, winreg.REG_DWORD)
        success_count += 1
        _log("[2/10] PassportForWork bloqueado.", "OK")
    except Exception as e: _log(f"[2/10] Erro Passport: {e}", "AVISO")

    try:
        ps_script = """
        $ErrorActionPreference = 'SilentlyContinue'
        foreach($provider in @(
            'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{D6886603-9D2F-4E8D-8669-F6D169F26379}',
            'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{BEC09FE1-6EC3-4FFF-B6B7-BE1AC9B767CA}',
            'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{cb82b75d-653b-4f3b-b2d6-2bda6e68a60a}'
        )) { Remove-Item $provider -Force -ErrorAction SilentlyContinue }
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=15)
        success_count += 1
        _log("[3/10] Credential Providers removidos.", "OK")
    except Exception as e: _log(f"[3/10] Erro Providers: {e}", "AVISO")
    
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "Biometric", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "UseCertificateForOnPrem", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "PIN", 0, winreg.REG_DWORD)
        success_count += 1
        _log("[4/10] GPO Hello Forçada.", "OK")
    except Exception as e: _log(f"[4/10] Erro GPO Hello: {e}", "AVISO")
    
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WbioSrvc", "Start", 4, winreg.REG_DWORD)
        subprocess.run(["net", "stop", "WbioSrvc"], capture_output=True, timeout=10)
        subprocess.run(["sc", "config", "WbioSrvc", "start=disabled"], capture_output=True, timeout=10)
        success_count += 1
        _log("[5/10] Servico WbioSrvc parado.", "OK")
    except Exception as e: _log(f"[5/10] Erro WbioSrvc: {e}", "AVISO")
    
    try:
        ps_script = """
        $ErrorActionPreference = 'SilentlyContinue'
        Remove-Item 'HKCU:\\Software\\Microsoft\\Windows NT\\CurrentVersion\\PasswordLess' -Force -Recurse
        Remove-Item 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\HolographicShell\\FirstRun' -Force -Recurse
        Remove-Item 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Holographic' -Force -Recurse
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=10)
        success_count += 1
        _log("[6/10] HKCU limpo (O Infiltrado atua via Registry direto para outros profiles).", "OK")
    except Exception as e: _log(f"[6/10] Erro HKCU: {e}", "AVISO")
    
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "DisablePostLogonProvisioning", 1, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "PreferredUserNameField", "0", winreg.REG_SZ)
        success_count += 1
        _log("[7/10] Provisionamento desabilitado.", "OK")
    except Exception as e: _log(f"[7/10] Erro Provisionamento: {e}", "AVISO")
    
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Biometrics\Facial\NIST", "Template Protection", 1, winreg.REG_DWORD)
        subprocess.run(["powershell", "-NoProfile", "-Command", "Disable-WindowsOptionalFeature -Online -FeatureName 'Windows-Hello-Face' -NoRestart"], capture_output=True, timeout=30)
        success_count += 1
        _log("[8/10] Face ID removido.", "OK")
    except Exception as e: _log(f"[8/10] Erro Face ID: {e}", "AVISO")
    
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\CredUI", "DisablePasswordReveal", 1, winreg.REG_DWORD)
        success_count += 1
        _log("[9/10] Senha forcada no CredUI.", "OK")
    except Exception as e: _log(f"[9/10] Erro CredUI: {e}", "AVISO")
    
    try:
        ps_nuclear = """
        $ErrorActionPreference = 'SilentlyContinue'
        $providers = @(
            'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{D6886603-9D2F-4E8D-8669-F6D169F26379}',
            'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{BEC09FE1-6EC3-4FFF-B6B7-BE1AC9B767CA}',
            'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Authentication\\Credential Providers\\{cb82b75d-653b-4f3b-b2d6-2bda6e68a60a}'
        )
        foreach($provider in $providers) { if(Test-Path $provider) { Remove-Item $provider -Force -Recurse } }
        $HelloPath = 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Hello for Business'
        if(!(Test-Path $HelloPath)) { New-Item -Path $HelloPath -Force | Out-Null }
        New-ItemProperty -Path $HelloPath -Name 'Biometric' -Value 0 -PropertyType DWORD -Force | Out-Null
        New-ItemProperty -Path $HelloPath -Name 'PIN' -Value 0 -PropertyType DWORD -Force | Out-Null
        New-ItemProperty -Path $HelloPath -Name 'UseCertificateForOnPrem' -Value 0 -PropertyType DWORD -Force | Out-Null
        New-ItemProperty -Path $HelloPath -Name 'DisablePostLogonProvisioning' -Value 1 -PropertyType DWORD -Force | Out-Null
        $PassportPath = 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\PassportForWork'
        if(!(Test-Path $PassportPath)) { New-Item -Path $PassportPath -Force | Out-Null }
        New-ItemProperty -Path $PassportPath -Name 'Enabled' -Value 0 -PropertyType DWORD -Force | Out-Null
        New-ItemProperty -Path $PassportPath -Name 'DisablePostLogonProvisioning' -Value 1 -PropertyType DWORD -Force | Out-Null
        gpupdate /force /wait:0 2>&1 | Out-Null
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_nuclear], capture_output=True, text=True, timeout=30)
        success_count += 1
        _log("[10/10] Script Nuclear aplicado e GPO atualizada.", "OK")
    except Exception as e: _log(f"[10/10] Erro Nuclear: {e}", "AVISO")
    
    return success_count >= 8

def remove_widgets_taskbar():
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableNewsAndInterests", 0, winreg.REG_DWORD)
        subprocess.run(["net", "stop", "WidgetService"], capture_output=True, timeout=10)
        subprocess.run(["sc", "config", "WidgetService", "start=disabled"], capture_output=True, timeout=10)
    except Exception as e: pass
        
    try:
        ps_script = """
        $explorer = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1
        if ($explorer) {
            $user = $explorer.GetOwner().Domain + "\\" + $explorer.GetOwner().User
            $sid = (New-Object System.Security.Principal.NTAccount($user)).Translate([System.Security.Principal.SecurityIdentifier]).Value
            $RegPath = "Registry::HKEY_USERS\\$sid\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced"
            if(!(Test-Path $RegPath)) { New-Item -Path $RegPath -Force | Out-Null }
            New-ItemProperty -Path $RegPath -Name "TaskbarDa" -Value 0 -PropertyType DWORD -Force | Out-Null
        }
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=10)
    except Exception as e: pass
        
    _log("Widgets e Taskbar limpos (Injeção Dinâmica).", "OK")

def apply_security_lgpd():
    _log("Aplicando politicas de Seguranca e LGPD...", "INFO")
    set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD)
    set_reg_active_user(r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", 0, winreg.REG_DWORD)
    
    set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin", "autoWorkplaceJoin", 0, winreg.REG_DWORD)
    delete_reg_active_user(r"Software\Microsoft\Office\16.0\Common\SignIn", "SignInOptions")

    disable_windows_hello_redundant()
    remove_widgets_taskbar()

def apply_firewall_rules():
    _log("Aplicando regras de Firewall (Modo Whitelist Local)...", "INFO")
    
    antigas = ["CPFANI-Block-SMB-In", "CPFANI-Block-RPC-In", "CPFANI-Block-SMB-Out"]
    for regra in antigas:
        subprocess.run(f'netsh advfirewall firewall delete rule name="{regra}"', shell=True, capture_output=True)
        
    subprocess.run('netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes profile=private,domain', shell=True, capture_output=True)
    subprocess.run('netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=No profile=public', shell=True, capture_output=True)

    regras_whitelist = [
        'netsh advfirewall firewall add rule name="CPFANI-Allow-SMB-Local-In" dir=in action=allow protocol=TCP localport=445 remoteip=LocalSubnet,20.191.1.0/24 profile=any',
        'netsh advfirewall firewall add rule name="CPFANI-Allow-RPC-Local-In" dir=in action=allow protocol=TCP localport=135 remoteip=LocalSubnet,20.191.1.0/24 profile=any',
        'netsh advfirewall firewall add rule name="CPFANI-Allow-SMB-Local-Out" dir=out action=allow protocol=TCP remoteport=445 remoteip=LocalSubnet,20.191.1.0/24 profile=any'
    ]
    for cmd in regras_whitelist:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            _log(f"Falha regra Firewall Whitelist: {res.stderr}", "AVISO")
            
    _log("Firewall configurado com Whitelist para Impressoras/Rede Local.", "OK")

def _safe_copy_to_scripts(filename):
    source = os.path.join(os.path.dirname(__file__), filename)
    target = os.path.join("C:\\Scripts", filename)
    if os.path.exists(source):
        os.makedirs("C:\\Scripts", exist_ok=True)
        shutil.copy2(source, target)
    return target

def schedule_manutencao_rede():
    target_path = _safe_copy_to_scripts("manutencao_rede.bat")
    cmd = f'schtasks /create /tn "CPFANI_ManutencaoRede" /tr "\"{target_path}\"" /sc onlogon /rl highest /f'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        _log("Manutencao de Rede agendada.", "OK")
        return True
    _log(f"Erro agendar Manutencao de Rede: {res.stderr}", "AVISO")
    return False

def schedule_instalar_tudo():
    target_path = _safe_copy_to_scripts("instalar_tudo.ps1")
    cmd_run = f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File "{target_path}"'
    cmd = f'schtasks /create /tn "CPFANI_InstalarTudo" /tr "{cmd_run}" /sc onlogon /rl highest /f'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        _log("Atualizador de Softwares agendado.", "OK")
        return True
    _log(f"Erro agendar Instalador: {res.stderr}", "AVISO")
    return False

def _get_hardware_info():
    info = {}
    try:
        info["Nome_Computador"] = os.environ.get("COMPUTERNAME", platform.node())
        model = subprocess.check_output('powershell -Command "(Get-CimInstance Win32_ComputerSystem).Model"', shell=True, text=True).strip()
        info["Modelo_Sistema"] = model if model else "N/A"
        cpu = subprocess.check_output('powershell -Command "(Get-CimInstance Win32_Processor).Name"', shell=True, text=True).strip()
        info["Processador"] = cpu if cpu else "N/A"
        ram_raw = subprocess.check_output('powershell -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"', shell=True, text=True).strip()
        try:
            if ram_raw.isdigit(): info["Memoria_RAM"] = f"{round(int(ram_raw) / (1024**3), 1)} GB"
            else: info["Memoria_RAM"] = "N/A"
        except ValueError: info["Memoria_RAM"] = "N/A"
        os_name = subprocess.check_output('powershell -Command "(Get-CimInstance Win32_OperatingSystem).Caption"', shell=True, text=True).strip()
        info["Windows"] = os_name if os_name else "N/A"
        serial = subprocess.check_output('powershell -Command "(Get-CimInstance Win32_BIOS).SerialNumber"', shell=True, text=True).strip()
        info["Serial_BIOS"] = serial if serial else "N/A"
    except Exception as e:
        _log(f"Erro ao coletar hardware: {e}", "AVISO")
        if not info: info = {k: "N/A" for k in ["Nome_Computador", "Modelo_Sistema", "Processador", "Memoria_RAM", "Windows", "Serial_BIOS"]}
    return info

def _get_anydesk_id():
    exe_paths = [r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe", r"C:\Program Files\AnyDesk\AnyDesk.exe"]
    for exe in exe_paths:
        if os.path.exists(exe):
            try:
                result = subprocess.run([exe, "--get-id"], capture_output=True, text=True, timeout=10)
                if result.stdout.strip().isdigit(): return result.stdout.strip()
            except: pass
    return "AnyDesk não instalado"

def _get_teamviewer_id():
    tv_paths = [r"SOFTWARE\WOW6432Node\TeamViewer", r"SOFTWARE\TeamViewer"]
    for path in tv_paths:
        val = get_reg(winreg.HKEY_LOCAL_MACHINE, path, "ClientID")
        if val: return str(val)
    return "TeamViewer não instalado"

def generate_full_snapshot():
    hw = _get_hardware_info()
    pc_name = hw.get("Nome_Computador", "UNKNOWN")
    pc_name_clean = "".join(c for c in pc_name if c.isalnum() or c in ('-', '_'))
    log_path = Path(f"C:/Scripts/CPFANI_Hardware_Snapshot_{pc_name_clean}.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("   SNAPSHOT CP FANI V5.9.3 (Edição Infiltrado + Self-Healing)\n")
        f.write(f"   Gerado em: {ts}\n")
        f.write("=" * 60 + "\n\n")
        f.write("[HARDWARE]\n")
        for k in ["Nome_Computador", "Modelo_Sistema", "Processador", "Memoria_RAM", "Windows", "Serial_BIOS"]:
            f.write(f"  {k: <20}: {hw.get(k, 'N/A')}\n")
        f.write("\n[SUPORTE]\n")
        f.write(f"  AnyDesk    : {_get_anydesk_id()}\n")
        f.write(f"  TeamViewer : {_get_teamviewer_id()}\n")
        f.write("\n" + "=" * 60 + "\n")
    _log(f"Snapshot gerado em {log_path}", "OK")
    return str(log_path)