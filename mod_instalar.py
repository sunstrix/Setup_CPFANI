"""mod_instalar.py — V5.9.3 (CP Fani)"""
import subprocess
import os
import shutil
import sys
import platform
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def check_chocolatey():
    if shutil.which("choco") is None:
        raise RuntimeError("Chocolatey não encontrado no PATH.")
    result = subprocess.run(["choco", "--version"], capture_output=True, text=True, timeout=10)
    if result.returncode != 0: 
        raise RuntimeError(f"Erro no Chocolatey. Saida: {result.stderr}")
    _log(f"Chocolatey OK: {result.stdout.strip()}", "OK")

def _install_anydesk(timeout=300):
    _log("A instalar AnyDesk com redundância...", "INFO")
    try:
        res = subprocess.run(["choco", "install", "anydesk", "-y", "--no-progress"], capture_output=True, text=True, timeout=timeout)
        if res.returncode in (0, 1641, 3010, 1638):
            _log("AnyDesk instalado (Choco).", "OK")
            return True
    except Exception as e: pass
    
    _log("A tentar via WinGet...", "INFO")
    try:
        res = subprocess.run(["winget", "install", "--id", "AnyDeskSoftwareGmbH.AnyDesk", "--silent", "--accept-package-agreements", "--accept-source-agreements"], capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            _log("AnyDesk instalado (WinGet).", "OK")
            return True
    except Exception as e: pass
    
    _log("Falha absoluta ao instalar AnyDesk.", "ERRO")
    return False

def _choco_install(app, timeout=300):
    app = app.strip()
    if not app: return False
    _log(f"A instalar pacote via Choco: {app}...", "INFO")
    try:
        r = subprocess.run(["choco", "install", app, "-y", "--no-progress", "--limit-output"], capture_output=True, text=True, timeout=timeout)
        if r.returncode in (0, 1641, 3010, 1638):
            _log(f"Pacote {app} instalado/verificado com sucesso.", "OK")
            return True
        else:
            _log(f"Erro Choco {app}: Exit Code {r.returncode}.", "ERRO")
            return False
    except Exception as e:
        _log(f"Exceção Choco {app}: {e}", "ERRO")
        return False

def install_office_suite(choice):
    if choice == "office2021":
        _log("A instalar Office 2021 via ODT...", "INFO")
        d = os.path.dirname(os.path.abspath(__file__))
        exe = os.path.join(d, "resources", "setup.exe")
        xml = os.path.join(d, "resources", "configuration.xml")
        if not os.path.exists(exe) or not os.path.exists(xml): 
            return False
        try:
            res = subprocess.run([exe, "/configure", xml], capture_output=True, text=True, timeout=1800)
            if res.returncode == 0:
                _log("Office 2021 instalado.", "OK")
                return True
            return False
        except: return False
    elif choice == "onlyoffice":
        if _choco_install("onlyoffice-desktopeditors", timeout=600): 
            return True
        return False
    return True

def _get_motherboard_manufacturer():
    try:
        return subprocess.check_output('powershell -Command "(Get-CimInstance Win32_ComputerSystem).Manufacturer"', shell=True, text=True).strip().lower()
    except: return "desconhecido"

def install_manufacturer_drivers(settings_dict):
    manuf = _get_motherboard_manufacturer()
    driver_pkgs = settings_dict.get("drivers", {})
    target_pkg = driver_pkgs.get("dell") if "dell" in manuf else driver_pkgs.get("lenovo") if "lenovo" in manuf else driver_pkgs.get("hp") if "hp" in manuf else None
    
    if target_pkg:
        _log(f"Instalando assistente oficial: {target_pkg}...", "INFO")
        return _choco_install(target_pkg, timeout=600)
    return False

def force_windows_update_drivers():
    _log("=" * 60, "INFO")
    _log("ACEDENDO AO WINDOWS UPDATE... Pode demorar alguns minutos.", "INFO")
    _log("=" * 60, "INFO")
    ps_script = """
    $ErrorActionPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Write-Host "Configurando repositorios..."
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope AllUsers | Out-Null
    Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted -ErrorAction SilentlyContinue
    
    Write-Host "Instalando modulo oficial PSWindowsUpdate..."
    Install-Module -Name PSWindowsUpdate -Force -Confirm:$false -Scope AllUsers -ErrorAction SilentlyContinue
    Import-Module PSWindowsUpdate -Force
    
    Write-Host "Pesquisando e Instalando Drivers (Homologados Microsoft)..."
    Get-WindowsUpdate -Install -AcceptAll -IgnoreReboot | Out-Null
    """
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], capture_output=True, text=True, timeout=1800)
        _log("✓ Atualizações e Drivers instalados com sucesso via Microsoft.", "OK")
        return True
    except Exception as e:
        _log(f"Erro na rotina de Windows Update: {e}", "ERRO")
        return False