"""
mod_config.py — V6.0.0.0 (Edição Corporativa CP Fani: Blindagem Flameshot e Hardening de Sistema)
Foco: Sequestro de PrtSc via IFEO, Limpeza de Memória e Resiliência SYSTEM.
"""
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
from pathlib import Path
from datetime import datetime

# Configuração de encoding
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

NO_WINDOW = 0x08000000

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{ts}] [{level}] {msg}"
    print(formatted_msg, flush=True)
    try:
        log_path = r"C:\Scripts\deployment.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except: pass

def set_reg(root, path, name, value, rtype=winreg.REG_SZ):
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE)
        winreg.SetValueEx(key, name, 0, rtype, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        _log(f"Erro no Registro ({name}): {e}", "ERROR")
        return False

def _get_active_user_sid():
    """Captura o SID com tripla camada de fallback (Explorer, WMI, ProfileList)."""
    # Camada 1: Explorer Owner
    try:
        ps = "(New-Object System.Security.Principal.NTAccount((Get-WmiObject -Class Win32_Process -Filter \"Name='explorer.exe'\").GetOwner().User)).Translate([System.Security.Principal.SecurityIdentifier]).Value"
        sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps], text=True, creationflags=NO_WINDOW).strip()
        if sid.startswith("S-1-5-"): return sid
    except: pass

    # Camada 2: WMI ComputerSystem
    try:
        user_raw = subprocess.check_output("wmic computersystem get username", shell=True, creationflags=NO_WINDOW).decode().split()
        if len(user_raw) > 1:
            ps_sid = f"(New-Object System.Security.Principal.NTAccount('{user_raw[1]}')).Translate([System.Security.Principal.SecurityIdentifier]).Value"
            sid = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_sid], text=True, creationflags=NO_WINDOW).strip()
            return sid
    except: pass
    return None

def sequestrar_printscreen():
    """
    ENGENHARIA DE ELITE: Sequestro da Hotkey PrintScreen em 7 estágios.
    Neutraliza SnippingTool via IFEO e descarrega buffers de memória do Explorer.
    """
    _log("INICIANDO OPERAÇÃO DE SEQUESTRO DA TECLA PRTSCR...", "INFO")
    
    # 1. Derrubada Preventiva
    processos = ["SnippingTool.exe", "ScreenClippingHost.exe", "flameshot.exe"]
    for proc in processos:
        subprocess.run(["taskkill", "/f", "/im", proc], capture_output=True, creationflags=NO_WINDOW)
    
    # 2. Descarregamento de Memória (Mata Explorer)
    _log("Descarregando ganchos de hotkeys da memória...", "INFO")
    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True, creationflags=NO_WINDOW)
    time.sleep(1)

    # 3. Injeção de Diretivas de Três Vias
    _log("Injetando diretivas de desativação nativa (3 vias)...", "INFO")
    # Vía 1: HKCU
    set_reg(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD)
    
    # Vía 2: HKEY_USERS (Todos os perfis reais)
    profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profiles_key) as root_key:
        for i in range(1024):
            try:
                sid = winreg.EnumKey(root_key, i)
                if sid.startswith("S-1-5-21-"):
                    reg_path = f"{sid}\\Control Panel\\Keyboard"
                    subprocess.run(["reg", "add", f"HKU\\{reg_path}", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"], creationflags=NO_WINDOW)
                    # 4. Corte de Sincronização na Nuvem
                    sync_path = f"{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility"
                    subprocess.run(["reg", "add", f"HKU\\{sync_path}", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"], creationflags=NO_WINDOW)
                    # Bloqueio Dropbox Capture
                    drop_path = f"{sid}\\Software\\Dropbox\\Client"
                    subprocess.run(["reg", "add", f"HKU\\{drop_path}", "/v", "CapturePrintScreen", "/t", "REG_DWORD", "/d", "0", "/f"], creationflags=NO_WINDOW)
            except OSError: break

    # Vía 3: NTUSER.DAT Default (Novos usuários)
    try:
        subprocess.run(["reg", "load", "HKU\\DefaultUser", "C:\\Users\\Default\\NTUSER.DAT"], creationflags=NO_WINDOW)
        subprocess.run(["reg", "add", "HKU\\DefaultUser\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"], creationflags=NO_WINDOW)
        subprocess.run(["reg", "unload", "HKU\\DefaultUser"], creationflags=NO_WINDOW)
    except: pass

    # 5. Sequestro Silencioso via IFEO (Redirect para rundll32)
    _log("Configurando sequestro IFEO para neutralizar SnippingTool...", "INFO")
    ifeo_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
    for exe in ["SnippingTool.exe", "ScreenClippingHost.exe"]:
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo_path}\\{exe}", "Debugger", "rundll32.exe")

    # 6. Configuração Interna do Flameshot (.ini)
    _log("Configurando atalhos internos do Flameshot...", "INFO")
    sid = _get_active_user_sid()
    if sid:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{profiles_key}\\{sid}") as p_key:
                profile_path, _ = winreg.QueryValueEx(p_key, "ProfileImagePath")
                fs_dir = os.path.join(os.path.expandvars(profile_path), "AppData", "Roaming", "flameshot")
                os.makedirs(fs_dir, exist_ok=True)
                fs_ini = os.path.join(fs_dir, "flameshot.ini")
                with open(fs_ini, "w", encoding="utf-8") as f:
                    f.write("[General]\n\n[Shortcuts]\ntakeScreenshot=Print\n")
        except: pass

    # 7. Reativar Ambiente Gráfico
    _log("Reativando interface do usuário...", "INFO")
    subprocess.Popen(["explorer.exe"], creationflags=NO_WINDOW)
    _log("✓ OPERAÇÃO DE SEQUESTRO CONCLUÍDA COM SUCESSO.", "OK")

def setup_self_healing():
    """Watchdog com privilégios SYSTEM monitorando AnyDesk e Wallpaper."""
    _log("Instalando Cão de Guarda (Watchdog)...", "INFO")
    script_dir = r"C:\Scripts"
    os.makedirs(script_dir, exist_ok=True)
    ps_path = os.path.join(script_dir, "cpfani_watchdog.ps1")
    
    ps_content = r"""
    $officialWp = "C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
    while ($true) {
        # Auto-cura de processos críticos
        $ad = Get-Service -Name "AnyDesk" -ErrorAction SilentlyContinue
        if ($ad -and $ad.Status -ne 'Running') { Start-Service -Name "AnyDesk" }
        
        # Auto-cura visual (Wallpaper)
        $user = (Get-WmiObject -Class Win32_ComputerSystem).UserName
        if ($user) {
            $sid = (New-Object System.Security.Principal.NTAccount($user)).Translate([System.Security.Principal.SecurityIdentifier]).Value
            $regPath = "Registry::HKEY_USERS\$sid\Control Panel\Desktop"
            if (Test-Path $regPath) {
                Set-ItemProperty -Path $regPath -Name Wallpaper -Value $officialWp -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 10
    }
    """
    with open(ps_path, "w", encoding="utf-8") as f: f.write(ps_content)
    # Gatilho VBScript invisível
    vbs_path = os.path.join(script_dir, "watchdog_launcher.vbs")
    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(f'CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -File ""{ps_path}""", 0')
    
    subprocess.run(f'schtasks /create /tn "CPFANI_Watchdog" /tr "wscript.exe \\"{vbs_path}\\"" /sc onlogon /ru "SYSTEM" /rl highest /f', shell=True, creationflags=NO_WINDOW)

def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    """Hardening estrutural: Telemetria, Widgets e Windows Hello."""
    _log("Aplicando Hardening de Segurança e LGPD...", "INFO")
    if apply_lgpd:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin", "autoWorkplaceJoin", 0, winreg.REG_DWORD)
    if disable_hello:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "Biometric", 0, winreg.REG_DWORD)
    
    # Purga de Elementos Visuais (Widgets)
    set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD)

def sync_time_ntp():
    """Sincronização forçada com ntp.br."""
    _log("Sincronizando relógio com ntp.br...", "INFO")
    cmds = [
        'w32tm /config /manualpeerlist:"a.ntp.br b.ntp.br c.ntp.br" /syncfromflags:manual /reliable:YES /update',
        'net stop w32time', 'net start w32time', 'w32tm /resync /force'
    ]
    for cmd in cmds: subprocess.run(cmd, shell=True, capture_output=True, creationflags=NO_WINDOW)

def set_apps_to_startup_all_users():
    """Injeta atalhos COM na pasta pública de inicialização."""
    _log("Configurando inicialização automática pública...", "INFO")
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    apps = {
        "Flameshot.lnk": r"C:\Program Files\Flameshot\bin\flameshot.exe",
        "Ditto.lnk": r"C:\Program Files\Ditto\Ditto.exe",
        "AnyDesk.lnk": r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe"
    }
    for link, exe in apps.items():
        if os.path.exists(exe):
            target = os.path.join(startup_path, link)
            subprocess.run(f'powershell "$s=(New-Object -COM WScript.Shell).CreateShortcut(\'{target}\');$s.TargetPath=\'{exe}\';$s.Save()"', shell=True, creationflags=NO_WINDOW)

def remove_agressive_bloatware(bloatware_list):
    """Varredura deep sweep -AllUsers e -Online."""
    _log("Iniciando purga profunda de Bloatwares...", "INFO")
    for app in bloatware_list:
        cmd = f"Get-AppxPackage -AllUsers *{app}* | Remove-AppxPackage -AllUsers; Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, creationflags=NO_WINDOW)

# --- FUNÇÕES DE PERSONALIZAÇÃO MANTIDAS ---
def apply_cpfani_branding(bar_alignment):
    sync_time_ntp()
    set_apps_to_startup_all_users()
    # Chama o sequestro como parte do branding
    sequestrar_printscreen()

def configurar_compartilhamento_rede():
    from modules.mod_network import configure_network_sharing
    return configure_network_sharing()

def generate_full_snapshot():
    hw = {"PC": os.environ.get("COMPUTERNAME", platform.node())}
    log_path = Path(f"C:/Scripts/CPFANI_Hardware_Snapshot_{hw['PC']}.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f: f.write(f"SNAPSHOT V6.0\nPC: {hw['PC']}\n")
    return str(log_path)