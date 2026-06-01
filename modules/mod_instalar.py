"""
mod_instalar.py — Smart-Installer Corporativo v6.0
Engenharia de Elite: Instalação MSI v13.3.0 (Flameshot) + Redundância Office/OnlyOffice.
"""
import os
import subprocess
import urllib.request
import shutil
import time
from datetime import datetime

# Flag de sistema para ocultar janelas de console
NO_WINDOW = 0x08000000

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{ts}] [{level}] [INSTALLER] {msg}"
    print(formatted_msg, flush=True)
    try:
        log_path = r"C:\Scripts\deployment.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except: pass

def install_essential_apps(apps_list):
    """
    Instala os 10 apps essenciais. 
    Tratamento especial para o Flameshot (Smart-Installer MSI).
    """
    _log(f"Iniciando implantação de {len(apps_list)} aplicativos...", "INFO")
    
    for app in apps_list:
        if app.lower() == "flameshot":
            _install_flameshot_smart()
        else:
            _log(f"Instalando: {app}", "INFO")
            if not _install_via_choco(app):
                _log(f"Choco falhou para {app}. Tentando Winget...", "AVISO")
                if _install_via_winget(app):
                    _log(f"✓ {app} instalado via Winget.", "OK")
                else:
                    _log(f"❌ Falha crítica: {app} indisponível.", "ERROR")
            else:
                _log(f"✓ {app} instalado via Chocolatey.", "OK")

def _install_flameshot_smart():
    """
    SMART-INSTALLER FLAMESHOT:
    1. Valida versão v13.3.0 oficial.
    2. Download MSI Direto (GitHub/Servidores Oficiais).
    3. msiexec /i /qn /norestart.
    4. Fallback para Chocolatey se o MSI falhar.
    """
    _log("Iniciando Smart-Installer Flameshot (MSI Corporativo)...", "INFO")
    msi_url = "https://github.com/flameshot-org/flameshot/releases/download/v13.3.0/flameshot-13.3.0-win64.msi"
    msi_path = r"C:\Users\Public\Downloads\flameshot_setup.msi"
    
    # 1. Tentar Instalação MSI Oficial
    try:
        _log("Baixando Flameshot v13.3.0 MSI...", "INFO")
        urllib.request.urlretrieve(msi_url, msi_path)
        
        _log("Executando instalação silenciosa MSI...", "INFO")
        # msiexec /i <path> /qn /norestart
        cmd = f"msiexec.exe /i \"{msi_path}\" /qn /norestart"
        subprocess.run(cmd, shell=True, creationflags=NO_WINDOW, check=True)
        _log("✓ Flameshot v13.3.0 instalado com sucesso via MSI.", "OK")
        return True
    except Exception as e:
        _log(f"Falha na instalação MSI do Flameshot: {e}. Tentando fallback...", "AVISO")
    
    # 2. Fallback: Chocolatey
    if _install_via_choco("flameshot"):
        _log("✓ Flameshot instalado via Chocolatey (Fallback).", "OK")
        return True
        
    _log("❌ ERRO: Todas as tentativas de instalação do Flameshot falharam.", "ERROR")
    return False

def install_with_redundancy(app_name, methods):
    """Motor de redundância multinível para suítes de escritório."""
    _log(f"Iniciando ciclo redundante para: {app_name}", "INFO")
    
    for method in methods:
        _log(f"Tentando método: {method}...", "DEBUG")
        success = False
        
        if method == "odt":
            success = _install_office_odt()
        elif method == "chocolatey":
            success = _install_via_choco(app_name)
        elif method == "winget":
            success = _install_via_winget(app_name)
        elif method == "official_site":
            success = _install_onlyoffice_official()
        elif method == "unc_share":
            success = _install_via_unc(app_name)
            
        if success:
            _log(f"✓ {app_name} instalado com sucesso via {method}!", "OK")
            return True
        _log(f"Método {method} falhou.", "AVISO")
            
    return False

# --- MÉTODOS DE SUPORTE ---

def _install_via_choco(app_id):
    """Instalação silenciosa via Chocolatey."""
    pkg_map = {"microsoft_office": "office365business", "only_office": "onlyoffice-desktopeditors"}
    pkg = pkg_map.get(app_id, app_id)
    try:
        subprocess.run(["choco", "install", pkg, "-y", "--no-progress"], 
                       creationflags=NO_WINDOW, check=True, capture_output=True)
        return True
    except: return False

def _install_via_winget(app_id):
    """Instalação silenciosa via Winget."""
    pkg_map = {
        "googlechrome": "Google.Chrome", "anydesk": "AnyDesk.AnyDesk", 
        "7zip": "7zip.7zip", "flameshot": "Flameshot.Flameshot",
        "teamviewer": "TeamViewer.TeamViewer", "vlc": "VideoLAN.VLC",
        "winrar": "RARLab.WinRAR", "ditto": "ScottBrose.Ditto",
        "sharex": "ShareX.ShareX", "microsoft_office": "Microsoft.Office",
        "only_office": "ONLYOFFICE.DesktopEditors"
    }
    pkg = pkg_map.get(app_id, app_id)
    try:
        subprocess.run(["winget", "install", "--id", pkg, "--silent", "--accept-source-agreements"], 
                       creationflags=NO_WINDOW, check=True, capture_output=True)
        return True
    except: return False

def _install_office_odt():
    """Instalação via ODT."""
    try:
        setup_exe = r"C:\Users\Public\Downloads\setup_odt.exe"
        config_xml = r"C:\Users\Public\Downloads\configuration.xml"
        url_odt = "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB4551408F/setup.exe"
        urllib.request.urlretrieve(url_odt, setup_exe)
        xml_content = '<Configuration><Add OfficeClientEdition="64" Channel="Current"><Product ID="O365ProPlusRetail"><Language ID="pt-br"/></Product></Add><Display Level="None" AcceptEULA="TRUE"/></Configuration>'
        with open(config_xml, "w") as f: f.write(xml_content)
        subprocess.run([setup_exe, "/configure", config_xml], creationflags=NO_WINDOW, check=True)
        return True
    except: return False

def _install_onlyoffice_official():
    """Instalação oficial OnlyOffice."""
    try:
        url = "https://download.onlyoffice.com/install/desktop/editors/windows/ONLYOFFICE_DesktopEditors_x64.exe"
        target = r"C:\Users\Public\Downloads\OnlyOfficeSetup.exe"
        urllib.request.urlretrieve(url, target)
        subprocess.run([target, "/S"], creationflags=NO_WINDOW, check=True)
        return True
    except: return False

def _install_via_unc(app_name):
    """Instalação via Rede Local."""
    path = f"\\\\GI-PC2025\\Instaladores\\{app_name}_setup.exe"
    if os.path.exists(path):
        try:
            local_path = os.path.join(r"C:\Users\Public\Downloads", os.path.basename(path))
            shutil.copy(path, local_path)
            subprocess.run([local_path, "/verysilent"], creationflags=NO_WINDOW, check=True)
            return True
        except: return False
    return False

def install_office_redundant():
    return install_with_redundancy("microsoft_office", ["odt", "chocolatey", "winget", "unc_share"])

def install_onlyoffice_redundant():
    return install_with_redundancy("only_office", ["official_site", "chocolatey", "winget"])