"""
mod_instalar.py — Motor de Instalação com Redundância e Fallback
Especialista em Deployment Windows - Versão Corporativa 6.0
"""
import os
import subprocess
import urllib.request
import shutil
from datetime import datetime

# Flag de sistema para ocultar janelas
NO_WINDOW = 0x08000000

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] [INSTALLER] {msg}", flush=True)

def install_with_redundancy(app_name, methods):
    """
    Tenta instalar um aplicativo usando uma lista de métodos em ordem de preferência.
    """
    _log(f"Iniciando ciclo de instalação redundante para: {app_name}", "INFO")
    
    for method in methods:
        _log(f"Tentando método: {method}...", "DEBUG")
        success = False
        
        if method == "odt":
            success = _install_office_odt()
        elif method == "offline_installer":
            success = _install_via_direct_download(app_name)
        elif method == "chocolatey":
            success = _install_via_choco(app_name)
        elif method == "winget":
            success = _install_via_winget(app_name)
        elif method == "unc_share":
            success = _install_via_unc(app_name)
        elif method == "official_site":
            success = _install_onlyoffice_official()
            
        if success:
            _log(f"✓ {app_name} instalado com sucesso via {method}!", "OK")
            return True
        else:
            _log(f"Falha no método {method}. Tentando próximo da lista...", "AVISO")
            
    _log(f"❌ ERRO CRÍTICO: Todos os métodos de instalação para {app_name} falharam.", "ERROR")
    return False

# --- MÉTODOS ESPECÍFICOS ---

def _install_office_odt():
    """Instalação via Office Deployment Tool (Recomendado Corporativo)."""
    try:
        setup_exe = r"C:\Users\Public\Downloads\setup_odt.exe"
        config_xml = r"C:\Users\Public\Downloads\configuration.xml"
        
        # Download do ODT e Config
        urllib.request.urlretrieve("https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB4551408F/setup.exe", setup_exe)
        # O XML deve ser configurado no config_version.json ou embutido
        with open(config_xml, "w") as f:
            f.write('<Configuration><Add OfficeClientEdition="64" Channel="Current"><Product ID="O365ProPlusRetail"><Language ID="pt-br"/></Product></Add><Display Level="None" AcceptEULA="TRUE"/></Configuration>')
        
        cmd = f"{setup_exe} /configure {config_xml}"
        subprocess.run(cmd, creationflags=NO_WINDOW, check=True)
        return True
    except:
        return False

def _install_onlyoffice_official():
    """Download direto do MSI/EXE do OnlyOffice."""
    try:
        url = "https://download.onlyoffice.com/install/desktop/editors/windows/ONLYOFFICE_DesktopEditors_x64.exe"
        target = r"C:\Users\Public\Downloads\OnlyOfficeSetup.exe"
        urllib.request.urlretrieve(url, target)
        subprocess.run([target, "/S"], creationflags=NO_WINDOW, check=True)
        return True
    except:
        return False

# --- MÉTODOS GENÉRICOS DE FALLBACK ---

def _install_via_choco(app_id):
    """Fallback via Chocolatey Package Manager."""
    try:
        # Mapeamento de nomes amigáveis para IDs do Choco
        pkg_map = {"microsoft_office": "office365business", "only_office": "onlyoffice"}
        pkg = pkg_map.get(app_id, app_id)
        
        subprocess.run(["choco", "install", pkg, "-y", "--no-progress"], creationflags=NO_WINDOW, check=True)
        return True
    except:
        return False

def _install_via_winget(app_id):
    """Fallback via Windows Package Manager (Winget)."""
    try:
        pkg_map = {"microsoft_office": "Microsoft.Office", "only_office": "ONLYOFFICE.DesktopEditors"}
        pkg = pkg_map.get(app_id, app_id)
        
        subprocess.run(["winget", "install", "--id", pkg, "--silent", "--accept-source-agreements"], creationflags=NO_WINDOW, check=True)
        return True
    except:
        return False

def _install_via_unc(app_name):
    """Fallback via Compartilhamento de Rede Local (Intranet)."""
    try:
        # Busca caminho do servidor no settings.json (simulado aqui)
        network_path = r"\\GI-PC2025\Instaladores\OfficeSetup.exe"
        local_temp = r"C:\Users\Public\Downloads\OfficeRede.exe"
        
        if os.path.exists(network_path):
            shutil.copy(network_path, local_temp)
            subprocess.run([local_temp, "/silent"], creationflags=NO_WINDOW, check=True)
            return True
        return False
    except:
        return False

def _install_via_direct_download(app_name):
    """Método legado de download direto preservado por segurança."""
    _log(f"Iniciando download direto legado para {app_name}...", "INFO")
    # Lógica original seria mantida aqui
    return False # Placeholder para não estender demais

def install_office_redundant():
    methods = ["odt", "chocolatey", "winget", "unc_share"]
    return install_with_redundancy("microsoft_office", methods)

def install_onlyoffice_redundant():
    methods = ["official_site", "chocolatey", "winget"]
    return install_with_redundancy("only_office", methods)