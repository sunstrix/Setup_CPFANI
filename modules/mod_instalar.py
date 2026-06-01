"""
mod_instalar.py — Motor de Instalação Corporativo com Redundância
Suporte total aos 10 apps essenciais da v5.9.5.5 + Redundância Office
Versão Corporativa 6.0.0.0
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
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except:
        pass

def install_essential_apps(apps_list):
    """
    Instala a lista de 10 programas essenciais da v5.9.5.5.
    Lógica: Tenta Chocolatey (Padrão) -> Fallback Winget.
    """
    _log(f"Iniciando instalação de {len(apps_list)} aplicativos essenciais...", "INFO")
    
    for app in apps_list:
        _log(f"Processando: {app}", "INFO")
        # Tenta Chocolatey primeiro
        if not _install_via_choco(app):
            _log(f"Choco falhou para {app}. Tentando fallback via Winget...", "AVISO")
            if _install_via_winget(app):
                _log(f"✓ {app} instalado via Winget.", "OK")
            else:
                _log(f"❌ Falha crítica: {app} não pode ser instalado.", "ERROR")
        else:
            _log(f"✓ {app} instalado via Chocolatey.", "OK")

def install_with_redundancy(app_name, methods):
    """
    Motor de redundância para suítes de escritório (Office e OnlyOffice).
    Tenta os métodos em ordem até obter sucesso.
    """
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
        
        _log(f"Método {method} falhou para {app_name}.", "AVISO")
            
    return False

# --- MÉTODOS DE SUPORTE ---

def _install_via_choco(app_id):
    """Instalação via Chocolatey."""
    # Tradução de IDs se necessário
    pkg_map = {
        "microsoft_office": "office365business", 
        "only_office": "onlyoffice-desktopeditors"
    }
    pkg = pkg_map.get(app_id, app_id)
    try:
        subprocess.run(["choco", "install", pkg, "-y", "--no-progress"], 
                       creationflags=NO_WINDOW, check=True, capture_output=True)
        return True
    except:
        return False

def _install_via_winget(app_id):
    """Instalação via Winget (Windows Package Manager)."""
    # Mapeamento para Winget IDs
    pkg_map = {
        "googlechrome": "Google.Chrome",
        "anydesk": "AnyDesk.AnyDesk",
        "7zip": "7zip.7zip",
        "flameshot": "Flameshot.Flameshot",
        "teamviewer": "TeamViewer.TeamViewer",
        "vlc": "VideoLAN.VLC",
        "winrar": "RARLab.WinRAR",
        "ditto": "ScottBrose.Ditto",
        "sharex": "ShareX.ShareX",
        "microsoft_office": "Microsoft.Office",
        "only_office": "ONLYOFFICE.DesktopEditors"
    }
    pkg = pkg_map.get(app_id, app_id)
    try:
        subprocess.run(["winget", "install", "--id", pkg, "--silent", "--accept-source-agreements"], 
                       creationflags=NO_WINDOW, check=True, capture_output=True)
        return True
    except:
        return False

def _install_office_odt():
    """Instalação via Office Deployment Tool (ODT)."""
    try:
        setup_exe = r"C:\Users\Public\Downloads\setup_odt.exe"
        config_xml = r"C:\Users\Public\Downloads\configuration.xml"
        
        # Download silencioso do motor ODT
        url_odt = "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB4551408F/setup.exe"
        urllib.request.urlretrieve(url_odt, setup_exe)
        
        # Configuração básica XML (Pode ser expandida via config_version.json)
        xml_content = '<Configuration><Add OfficeClientEdition="64" Channel="Current"><Product ID="O365ProPlusRetail"><Language ID="pt-br"/></Product></Add><Display Level="None" AcceptEULA="TRUE"/></Configuration>'
        with open(config_xml, "w") as f: f.write(xml_content)
        
        subprocess.run([setup_exe, "/configure", config_xml], creationflags=NO_WINDOW, check=True)
        return True
    except:
        return False

def _install_onlyoffice_official():
    """Instalação via executável oficial OnlyOffice."""
    try:
        url = "https://download.onlyoffice.com/install/desktop/editors/windows/ONLYOFFICE_DesktopEditors_x64.exe"
        target = r"C:\Users\Public\Downloads\OnlyOfficeSetup.exe"
        urllib.request.urlretrieve(url, target)
        subprocess.run([target, "/S"], creationflags=NO_WINDOW, check=True)
        return True
    except:
        return False

def _install_via_unc(app_name):
    """Fallback via Rede Local (UNC)."""
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
    methods = ["odt", "chocolatey", "winget", "unc_share"]
    return install_with_redundancy("microsoft_office", methods)

def install_onlyoffice_redundant():
    methods = ["official_site", "chocolatey", "winget"]
    return install_with_redundancy("only_office", methods)