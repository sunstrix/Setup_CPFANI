"""mod_instalar.py — V5.9.5.2 (CP Fani)"""
import subprocess
import os
import shutil
import sys
import platform
import time
import socket
import hashlib
import ctypes
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE ENCODING PARA EVITAR CRASHES
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors='replace')
        sys.stderr.reconfigure(encoding="utf-8", errors='replace')
    except Exception:
        pass

# ============================================================
# CONSTANTES GLOBAIS
# ============================================================
LOG_DIR = Path(r"C:\Scripts\Logs")
MIN_EXECUTABLE_SIZE = 1048576  # 1MB mínimo para executáveis
MIN_DOWNLOAD_SIZE = 5242880    # 5MB mínimo para downloads
INSTALLATION_TIMEOUT = 1800    # 30 minutos para instalações
DOWNLOAD_TIMEOUT = 300         # 5 minutos para downloads

# ============================================================
# SISTEMA DE LOG APRIMORADO
# ============================================================
def _log(msg, level="INFO", context=None):
    """Sistema de log com timestamp, nível e contexto opcional"""
    ts = datetime.now().strftime("%H:%M:%S")
    if context:
        log_msg = f"[{ts}] [{level}] [{context}] {msg}"
    else:
        log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg, flush=True)
    
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"mod_instalar_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding="utf-8", errors='replace') as f:
            f.write(f"{log_msg}\n")
    except Exception:
        pass

# ============================================================
# VALIDAÇÃO DE PRÉ-REQUISITOS
# ============================================================
def _validate_admin_privileges():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            _log("Privilégios administrativos não detectados!", "ERRO")
            return False
        return True
    except Exception as e:
        _log(f"Falha ao verificar privilégios: {e}", "AVISO")
        return True

def _validate_disk_space(min_mb=500):
    try:
        free_space = shutil.disk_usage("C:\\").free
        if free_space < min_mb * 1024 * 1024:
            _log(f"Espaço em disco insuficiente: {free_space / (1024*1024):.0f}MB disponíveis", "ERRO")
            return False
        return True
    except Exception as e:
        _log(f"Falha ao verificar espaço em disco: {e}", "AVISO")
        return True

def _validate_internet_connectivity():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except Exception:
        try:
            import urllib.request
            urllib.request.urlopen("http://www.google.com", timeout=10)
            return True
        except Exception:
            _log("Sem conectividade com a internet", "ERRO")
            return False

def _validate_system_architecture():
    try:
        arch = platform.machine().lower()
        if arch in ['amd64', 'x86_64']:
            return 'x64'
        elif arch in ['arm64', 'aarch64']:
            return 'arm64'
        return 'unknown'
    except Exception:
        return 'unknown'

# ============================================================
# EXECUÇÃO SEGURA DE SUBPROCESSOS
# ============================================================
def _safe_subprocess_run(cmd, timeout=300, shell=False, capture_output=True, **kwargs):
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture_output,
            timeout=timeout,
            creationflags=0x08000000,
            encoding='utf-8',
            errors='replace',
            **kwargs
        )
        return result
    except subprocess.TimeoutExpired:
        _log(f"Timeout ({timeout}s) ao executar comando", "AVISO")
        return None
    except Exception as e:
        _log(f"Erro ao executar subprocesso: {e}", "ERRO")
        return None

# ============================================================
# VALIDAÇÃO DE INTEGRIDADE DE ARQUIVO
# ============================================================
def _validate_file_integrity(file_path, min_size=MIN_EXECUTABLE_SIZE, calculate_hash=False):
    try:
        if not os.path.exists(file_path):
            return False, None
        
        file_size = os.path.getsize(file_path)
        if file_size < min_size:
            return False, None
        
        if calculate_hash:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return True, sha256_hash.hexdigest()
        
        return True, None
    except Exception:
        return False, None

# ============================================================
# HEALTH CHECK PÓS-INSTALAÇÃO
# ============================================================
def _post_install_health_check(app_name, executable_paths=None):
    _log(f"Executando health check pós-instalação: {app_name}", "INFO")
    
    if executable_paths:
        for exe_path in executable_paths:
            if os.path.exists(exe_path):
                is_valid, _ = _validate_file_integrity(exe_path, min_size=MIN_EXECUTABLE_SIZE)
                if is_valid:
                    _log(f"✓ Executável encontrado e válido: {exe_path}", "OK")
                    return True
    
    try:
        result = _safe_subprocess_run(["where", app_name], timeout=10)
        if result and result.returncode == 0:
            _log(f"✓ {app_name} encontrado no PATH", "OK")
            return True
    except Exception:
        pass
    
    try:
        result = _safe_subprocess_run(["sc", "query", app_name], timeout=10)
        if result and "RUNNING" in result.stdout:
            _log(f"✓ Serviço {app_name} está rodando", "OK")
            return True
    except Exception:
        pass
    
    _log(f"Health check inconclusivo para {app_name}", "AVISO")
    return True

# ============================================================
# INSTALAÇÃO VIA CHOCOLATEY
# ============================================================
def _choco_install(app, timeout=300, max_retries=2):
    app = app.strip()
    if not app:
        return False
    
    _log(f"A instalar pacote via Choco: {app}...", "INFO")
    
    if not _validate_admin_privileges():
        return False
    
    if not _validate_internet_connectivity():
        return False
    
    for attempt in range(1, max_retries + 1):
        _log(f"Tentativa {attempt}/{max_retries} para {app}", "INFO")
        
        try:
            r = _safe_subprocess_run(
                ["choco", "install", app, "-y", "--no-progress", "--limit-output"],
                timeout=timeout
            )
            
            if r and r.returncode in (0, 1641, 3010, 1638):
                _log(f"✓ Pacote {app} instalado/verificado com sucesso", "OK")
                _post_install_health_check(app)
                return True
            else:
                exit_code = r.returncode if r else 'None'
                _log(f"Erro Choco {app}: Exit Code {exit_code}", "AVISO")
                
                if attempt < max_retries:
                    time.sleep(5)
        except Exception as e:
            _log(f"Exceção Choco {app}: {e}", "AVISO")
            if attempt < max_retries:
                time.sleep(5)
    
    _log(f"✗ Falha ao instalar {app} após {max_retries} tentativas", "ERRO")
    return False

# ============================================================
# INSTALAÇÃO DE DRIVERS DO FABRICANTE (COM FALLBACK INTELIGENTE)
# ============================================================
def install_manufacturer_drivers(settings_dict):
    """Instala drivers oficiais do fabricante com estratégia de fallback"""
    _log("Instalando assistente de drivers do fabricante...", "INFO")
    
    if not _validate_admin_privileges():
        return False
    
    if not _validate_disk_space(500):
        return False
    
    manuf = _get_motherboard_manufacturer()
    _log(f"Fabricante detectado: {manuf}", "INFO")
    
    driver_pkgs = settings_dict.get("drivers", {})
    
    # Estratégia para DELL
    if "dell" in manuf:
        target_pkg = driver_pkgs.get("dell")
        _log("Detectado Dell, usando pacote Dell", "INFO")
        if _choco_install(target_pkg, timeout=600):
            _log(f"✓ {target_pkg} instalado com sucesso", "OK")
            return True
        else:
            _log(f"⚠ Falha ao instalar {target_pkg}. O Windows Update fornecerá os drivers.", "AVISO")
            return True  # Não bloqueia o fluxo
            
    # Estratégia para LENOVO
    elif "lenovo" in manuf:
        target_pkg = driver_pkgs.get("lenovo")
        _log("Detectado Lenovo, usando pacote Lenovo", "INFO")
        if _choco_install(target_pkg, timeout=600):
            _log(f"✓ {target_pkg} instalado com sucesso", "OK")
            return True
        else:
            _log(f"⚠ Falha ao instalar {target_pkg}. O Windows Update fornecerá os drivers.", "AVISO")
            return True
            
    # Estratégia para HP (COM FALLBACK INTELIGENTE)
    elif "hp" in manuf or "hewlett" in manuf:
        _log("Detectado HP, aplicando estratégia de instalação inteligente...", "INFO")
        target_pkg = driver_pkgs.get("hp", "hp-support-assistant")
        fallback_pkg = "hp-client-management-script-library"  # Alternativa CLI oficial e mais estável da HP
        
        # 1. Tenta o pacote principal
        if _choco_install(target_pkg, timeout=600):
            _log(f"✓ {target_pkg} instalado com sucesso", "OK")
            return True
        else:
            _log(f"⚠ {target_pkg} falhou (comum em ferramentas de fabricante). Tentando alternativa moderna...", "AVISO")
            # 2. Tenta o fallback
            if _choco_install(fallback_pkg, timeout=600):
                _log(f"✓ {fallback_pkg} instalado com sucesso (Alternativa HP)", "OK")
                return True
            else:
                # 3. Se tudo falhar, degrada graciosamente. O Windows Update é o fallback final.
                _log(f"⚠ Ferramentas de driver HP não puderam ser instaladas via Choco. O Windows Update cuidará disso.", "AVISO")
                return True  # Retorna True para não bloquear o fluxo
                
    else:
        _log(f"Fabricante '{manuf}' não possui pacote específico configurado. Pulando...", "AVISO")
        return True  # Não é erro, apenas não há pacote específico

def _get_motherboard_manufacturer():
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_ComputerSystem).Manufacturer'],
            shell=True,
            timeout=15
        )
        if result and result.stdout:
            return result.stdout.strip().lower()
        return "desconhecido"
    except Exception:
        return "desconhecido"

# ============================================================
# WINDOWS UPDATE
# ============================================================
def force_windows_update_drivers():
    _log("=" * 60, "INFO")
    _log("ACESSANDO AO WINDOWS UPDATE... Pode demorar alguns minutos.", "INFO")
    _log("=" * 60, "INFO")
    
    if not _validate_admin_privileges():
        return False
    
    if not _validate_internet_connectivity():
        return False
    
    if not _validate_disk_space(2000):
        return False
    
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
    Write-Host "Processo concluido."
    """
    
    try:
        _log("Executando script PowerShell para Windows Update...", "INFO")
        res = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            timeout=INSTALLATION_TIMEOUT
        )
        
        if res and res.returncode == 0:
            _log("✓ Atualizações e Drivers instalados com sucesso via Microsoft", "OK")
            return True
        else:
            _log(f"Windows Update retornou código {res.returncode if res else 'None'}", "AVISO")
            return True  # Mesmo com código diferente de 0, pode ter instalado parcialmente
    except Exception as e:
        _log(f"Erro na rotina de Windows Update: {e}", "ERRO")
        return False

# ============================================================
# INSTALAÇÃO DO OFFICE
# ============================================================
def install_office_suite(choice):
    _log(f"Instalando Office: {choice}", "INFO")
    
    if not _validate_admin_privileges():
        return False
    
    if choice == "office2021":
        if not _validate_disk_space(5000):
            return False
        
        d = os.path.dirname(os.path.abspath(__file__))
        exe = os.path.join(d, "resources", "setup.exe")
        xml = os.path.join(d, "resources", "configuration.xml")
        
        if not os.path.exists(exe) or not os.path.exists(xml):
            _log("Arquivos de instalação do Office não encontrados", "ERRO")
            return False
        
        try:
            res = _safe_subprocess_run([exe, "/configure", xml], timeout=INSTALLATION_TIMEOUT)
            if res and res.returncode == 0:
                _log("✓ Office 2021 instalado com sucesso", "OK")
                return True
            else:
                _log(f"Office retornou código {res.returncode if res else 'None'}", "ERRO")
                return False
        except Exception as e:
            _log(f"Exceção ao instalar Office: {e}", "ERRO")
            return False
            
    elif choice == "onlyoffice":
        if not _validate_disk_space(1000):
            return False
        
        if _choco_install("onlyoffice-desktopeditors", timeout=600):
            _log("✓ OnlyOffice instalado com sucesso", "OK")
            return True
        _log("✗ Falha ao instalar OnlyOffice", "ERRO")
        return False
    
    return True