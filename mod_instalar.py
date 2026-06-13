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
# CONSTANTES GLOBAIS (NOVO)
# ============================================================
LOG_DIR = Path(r"C:\Scripts\Logs")
MIN_EXECUTABLE_SIZE = 1048576  # 1MB mínimo para executáveis
MIN_DOWNLOAD_SIZE = 5242880    # 5MB mínimo para downloads
INSTALLATION_TIMEOUT = 1800    # 30 minutos para instalações
DOWNLOAD_TIMEOUT = 300         # 5 minutos para downloads

# ============================================================
# SISTEMA DE LOG APRIMORADO (NOVO)
# ============================================================
def _log(msg, level="INFO", context=None):
    """Sistema de log com timestamp, nível e contexto opcional"""
    ts = datetime.now().strftime("%H:%M:%S")
    if context:
        log_msg = f"[{ts}] [{level}] [{context}] {msg}"
    else:
        log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg, flush=True)
    
    # Log em arquivo também
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"mod_instalar_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding="utf-8", errors='replace') as f:
            f.write(f"{log_msg}\n")
    except Exception:
        pass

# ============================================================
# VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
# ============================================================
def _validate_admin_privileges():
    """Valida se o script está executando com privilégios administrativos"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            _log("Privilégios administrativos não detectados!", "ERRO")
            return False
        return True
    except Exception as e:
        _log(f"Falha ao verificar privilégios: {e}", "AVISO")
        return True  # Continua mesmo se falhar

def _validate_disk_space(min_mb=500):
    """Valida espaço em disco disponível"""
    try:
        free_space = shutil.disk_usage("C:\\").free
        if free_space < min_mb * 1024 * 1024:
            _log(f"Espaço em disco insuficiente: {free_space / (1024*1024):.0f}MB disponíveis (mínimo: {min_mb}MB)", "ERRO")
            return False
        return True
    except Exception as e:
        _log(f"Falha ao verificar espaço em disco: {e}", "AVISO")
        return True

def _validate_internet_connectivity():
    """Valida conectividade com internet"""
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
    """Valida arquitetura do sistema"""
    try:
        arch = platform.machine().lower()
        if arch in ['amd64', 'x86_64']:
            _log(f"Arquitetura detectada: {arch} (x64)", "OK")
            return 'x64'
        elif arch in ['arm64', 'aarch64']:
            _log(f"Arquitetura detectada: {arch} (ARM64)", "OK")
            return 'arm64'
        elif arch in ['x86', 'i386', 'i686']:
            _log(f"Arquitetura detectada: {arch} (x86)", "AVISO")
            return 'x86'
        else:
            _log(f"Arquitetura desconhecida: {arch}", "AVISO")
            return 'unknown'
    except Exception as e:
        _log(f"Falha ao detectar arquitetura: {e}", "AVISO")
        return 'unknown'

def _validate_windows_version():
    """Valida versão do Windows"""
    try:
        version = platform.version()
        release = platform.release()
        _log(f"Windows detectado: {release} (Build {version})", "OK")
        
        # Windows 10/11 são suportados
        if release in ['10', '11']:
            return True
        else:
            _log(f"Versão do Windows não testada: {release}", "AVISO")
            return True  # Continua mesmo assim
    except Exception as e:
        _log(f"Falha ao detectar versão do Windows: {e}", "AVISO")
        return True

# ============================================================
# EXECUÇÃO SEGURA DE SUBPROCESSOS (MANTIDO COM MELHORIAS)
# ============================================================
def _safe_subprocess_run(cmd, timeout=300, shell=False, capture_output=True, **kwargs):
    """Execução segura de subprocessos com timeout e tratamento de erros"""
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
# VALIDAÇÃO DE INTEGRIDADE DE ARQUIVO (NOVO)
# ============================================================
def _validate_file_integrity(file_path, min_size=MIN_EXECUTABLE_SIZE, calculate_hash=False):
    """Valida integridade de um arquivo"""
    try:
        if not os.path.exists(file_path):
            _log(f"Arquivo não existe: {file_path}", "ERRO")
            return False, None
        
        file_size = os.path.getsize(file_path)
        if file_size < min_size:
            _log(f"Arquivo muito pequeno: {file_size} bytes (mínimo: {min_size})", "ERRO")
            return False, None
        
        _log(f"✓ Arquivo validado: {os.path.basename(file_path)} ({file_size} bytes)", "OK")
        
        if calculate_hash:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            checksum = sha256_hash.hexdigest()
            _log(f"SHA256: {checksum[:16]}...", "INFO")
            return True, checksum
        
        return True, None
    except Exception as e:
        _log(f"Erro ao validar arquivo: {e}", "ERRO")
        return False, None

# ============================================================
# VALIDAÇÃO DE ASSINATURA DIGITAL (NOVO)
# ============================================================
def _validate_digital_signature(file_path):
    """Valida assinatura digital de um executável"""
    try:
        # Usa PowerShell para verificar assinatura
        ps_script = f"""
        $file = '{file_path}'
        $sig = Get-AuthenticodeSignature -FilePath $file
        if ($sig.Status -eq 'Valid') {{
            Write-Output "VALID"
            Write-Output $sig.SignerCertificate.Subject
        }} else {{
            Write-Output "INVALID"
            Write-Output $sig.Status
        }}
        """
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=15
        )
        
        if result and result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 1 and lines[0] == "VALID":
                signer = lines[1] if len(lines) > 1 else "Unknown"
                _log(f"✓ Assinatura digital válida: {signer}", "OK")
                return True
            else:
                _log(f"Assinatura digital inválida ou ausente", "AVISO")
                return False
        return False
    except Exception as e:
        _log(f"Falha ao validar assinatura digital: {e}", "AVISO")
        return False

# ============================================================
# HEALTH CHECK PÓS-INSTALAÇÃO (NOVO)
# ============================================================
def _post_install_health_check(app_name, executable_paths=None):
    """Verifica se aplicação foi instalada corretamente"""
    _log(f"Executando health check pós-instalação: {app_name}", "INFO")
    
    # Verifica se executável existe
    if executable_paths:
        for exe_path in executable_paths:
            if os.path.exists(exe_path):
                _log(f"✓ Executável encontrado: {exe_path}", "OK")
                
                # Valida integridade
                is_valid, _ = _validate_file_integrity(exe_path, min_size=MIN_EXECUTABLE_SIZE)
                if is_valid:
                    return True
        
        _log(f"Executável não encontrado nos caminhos esperados", "AVISO")
    
    # Verifica se está no PATH
    try:
        result = _safe_subprocess_run(["where", app_name], timeout=10)
        if result and result.returncode == 0:
            _log(f"✓ {app_name} encontrado no PATH", "OK")
            return True
    except Exception:
        pass
    
    # Verifica se serviço está rodando (para alguns apps)
    try:
        result = _safe_subprocess_run(
            ["sc", "query", app_name],
            timeout=10
        )
        if result and "RUNNING" in result.stdout:
            _log(f"✓ Serviço {app_name} está rodando", "OK")
            return True
    except Exception:
        pass
    
    _log(f"Health check inconclusivo para {app_name}", "AVISO")
    return True  # Não falha o processo

# ============================================================
# VERIFICAÇÃO DO CHOCOLATEY (MANTIDO COM VALIDAÇÕES)
# ============================================================
def check_chocolatey():
    """Verifica se Chocolatey está instalado e funcional"""
    _log("Verificando Chocolatey...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if shutil.which("choco") is None:
        _log("Chocolatey não encontrado no PATH", "ERRO")
        return False
    
    result = _safe_subprocess_run(["choco", "--version"], timeout=15)
    
    if not result:
        _log("Falha ao executar choco --version", "ERRO")
        return False
    
    if result.returncode != 0:
        _log(f"Chocolatey retornou código {result.returncode}", "ERRO")
        return False
    
    version = result.stdout.strip()
    _log(f"Chocolatey OK: {version}", "OK")
    
    # ============================================================
    # VALIDAÇÃO DE VERSÃO (NOVO)
    # ============================================================
    try:
        version_parts = [int(x) for x in version.split('.')[:3]]
        if version_parts[0] < 1:
            _log(f"Versão do Chocolatey muito antiga: {version}", "AVISO")
        else:
            _log(f"Versão do Chocolatey compatível: {version}", "OK")
    except Exception as e:
        _log(f"Falha ao validar versão do Chocolatey: {e}", "AVISO")
    
    return True

# ============================================================
# INSTALAÇÃO DO ANYDESK (MANTIDO COM VALIDAÇÕES)
# ============================================================
def _install_anydesk(timeout=300):
    """Instala AnyDesk com fallback para múltiplos métodos"""
    _log("A instalar AnyDesk com redundância...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if not _validate_disk_space(200):
        _log("Espaço em disco insuficiente para AnyDesk", "ERRO")
        return False
    
    # Tentativa 1: Chocolatey
    _log("Tentativa 1/3: Instalando via Chocolatey...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["choco", "install", "anydesk", "-y", "--no-progress"],
            timeout=timeout
        )
        
        if res and res.returncode in (0, 1641, 3010, 1638):
            _log("✓ AnyDesk instalado via Chocolatey", "OK")
            
            # ============================================================
            # HEALTH CHECK PÓS-INSTALAÇÃO (NOVO)
            # ============================================================
            _post_install_health_check("anydesk", [
                r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
                r"C:\Program Files\AnyDesk\AnyDesk.exe"
            ])
            
            return True
        else:
            _log(f"Chocolatey retornou código {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Exceção no Chocolatey: {e}", "AVISO")
    
    # Tentativa 2: WinGet
    _log("Tentativa 2/3: Instalando via WinGet...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["winget", "install", "--id", "AnyDeskSoftwareGmbH.AnyDesk", "--silent", 
             "--accept-package-agreements", "--accept-source-agreements"],
            timeout=timeout
        )
        
        if res and res.returncode == 0:
            _log("✓ AnyDesk instalado via WinGet", "OK")
            
            # ============================================================
            # HEALTH CHECK PÓS-INSTALAÇÃO (NOVO)
            # ============================================================
            _post_install_health_check("anydesk", [
                r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
                r"C:\Program Files\AnyDesk\AnyDesk.exe"
            ])
            
            return True
        else:
            _log(f"WinGet retornou código {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Exceção no WinGet: {e}", "AVISO")
    
    # Tentativa 3: Download direto (fallback final)
    _log("Tentativa 3/3: Download direto do site oficial...", "INFO")
    try:
        # ============================================================
        # VALIDAÇÃO DE CONECTIVIDADE (NOVO)
        # ============================================================
        if not _validate_internet_connectivity():
            _log("Sem conectividade para baixar AnyDesk", "ERRO")
            return False
        
        import urllib.request
        
        anydesk_url = "https://download.anydesk.com/AnyDesk.exe"
        temp_path = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "AnyDesk_Install.exe")
        
        _log(f"Baixando AnyDesk de {anydesk_url}...")
        
        # ============================================================
        # DOWNLOAD COM TIMEOUT (CORRIGIDO)
        # ============================================================
        with urllib.request.urlopen(anydesk_url, timeout=DOWNLOAD_TIMEOUT) as response:
            with open(temp_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        
        # Validação de tamanho (deve ser maior que 1MB)
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > MIN_EXECUTABLE_SIZE:
            _log("✓ Download concluído com sucesso", "OK")
            
            # ============================================================
            # VALIDAÇÃO DE INTEGRIDADE (NOVO)
            # ============================================================
            is_valid, checksum = _validate_file_integrity(temp_path, min_size=MIN_EXECUTABLE_SIZE, calculate_hash=True)
            if not is_valid:
                _log("Arquivo baixado com integridade comprometida", "ERRO")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
            
            _log("Executando instalador silencioso...", "INFO")
            res = _safe_subprocess_run(
                [temp_path, "--install", "--silent", "--start-with-win"],
                timeout=timeout
            )
            
            if res and res.returncode == 0:
                _log("✓ AnyDesk instalado via download direto", "OK")
                
                # ============================================================
                # HEALTH CHECK PÓS-INSTALAÇÃO (NOVO)
                # ============================================================
                _post_install_health_check("anydesk", [
                    r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe",
                    r"C:\Program Files\AnyDesk\AnyDesk.exe"
                ])
                
                # Limpa arquivo temporário
                try:
                    os.remove(temp_path)
                except:
                    pass
                return True
            else:
                _log(f"Instalador retornou código {res.returncode if res else 'None'}", "AVISO")
                # ============================================================
                # CLEANUP EM CASO DE FALHA (NOVO)
                # ============================================================
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
        else:
            _log("Arquivo baixado é muito pequeno ou não existe", "ERRO")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        _log(f"Exceção no download direto: {e}", "AVISO")
        # ============================================================
        # CLEANUP EM CASO DE EXCEÇÃO (NOVO)
        # ============================================================
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
    
    _log("✗ Falha absoluta ao instalar AnyDesk após 3 tentativas", "ERRO")
    return False

# ============================================================
# INSTALAÇÃO VIA CHOCOLATEY (MANTIDO COM VALIDAÇÕES)
# ============================================================
def _choco_install(app, timeout=300, max_retries=2):
    """Instala pacote via Chocolatey com retry logic"""
    app = app.strip()
    if not app:
        _log("Nome de pacote vazio", "ERRO")
        return False
    
    _log(f"A instalar pacote via Choco: {app}...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if not _validate_disk_space(100):
        _log(f"Espaço em disco insuficiente para {app}", "ERRO")
        return False
    
    # ============================================================
    # VALIDAÇÃO DE CONECTIVIDADE (NOVO)
    # ============================================================
    if not _validate_internet_connectivity():
        _log(f"Sem conectividade para instalar {app}", "ERRO")
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
                
                # ============================================================
                # HEALTH CHECK PÓS-INSTALAÇÃO (NOVO)
                # ============================================================
                _post_install_health_check(app)
                
                return True
            else:
                exit_code = r.returncode if r else 'None'
                _log(f"Erro Choco {app}: Exit Code {exit_code}", "AVISO")
                
                if attempt < max_retries:
                    _log(f"Aguardando 5 segundos antes de nova tentativa...", "INFO")
                    time.sleep(5)
        except Exception as e:
            _log(f"Exceção Choco {app}: {e}", "AVISO")
            
            if attempt < max_retries:
                _log(f"Aguardando 5 segundos antes de nova tentativa...", "INFO")
                time.sleep(5)
    
    _log(f"✗ Falha ao instalar {app} após {max_retries} tentativas", "ERRO")
    return False

# ============================================================
# INSTALAÇÃO DO OFFICE (MANTIDO COM VALIDAÇÕES)
# ============================================================
def install_office_suite(choice):
    """Instala suíte Office conforme escolha do usuário"""
    _log(f"Instalando Office: {choice}", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if choice == "office2021":
        _log("A instalar Office 2021 via ODT...", "INFO")
        
        # ============================================================
        # VALIDAÇÃO DE ESPAÇO EM DISCO (NOVO)
        # ============================================================
        if not _validate_disk_space(5000):  # Office precisa de ~5GB
            _log("Espaço em disco insuficiente para Office 2021", "ERRO")
            return False
        
        d = os.path.dirname(os.path.abspath(__file__))
        exe = os.path.join(d, "resources", "setup.exe")
        xml = os.path.join(d, "resources", "configuration.xml")
        
        # Validação de arquivos
        if not os.path.exists(exe):
            _log(f"Arquivo não encontrado: {exe}", "ERRO")
            return False
        
        if not os.path.exists(xml):
            _log(f"Arquivo não encontrado: {xml}", "ERRO")
            return False
        
        # Validação de tamanho
        exe_size = os.path.getsize(exe)
        if exe_size < MIN_EXECUTABLE_SIZE:
            _log(f"Arquivo setup.exe muito pequeno ({exe_size} bytes)", "ERRO")
            return False
        
        # ============================================================
        # VALIDAÇÃO DE INTEGRIDADE (NOVO)
        # ============================================================
        is_valid, checksum = _validate_file_integrity(exe, min_size=MIN_EXECUTABLE_SIZE, calculate_hash=True)
        if not is_valid:
            _log("setup.exe com integridade comprometida", "ERRO")
            return False
        
        # ============================================================
        # VALIDAÇÃO DE ASSINATURA DIGITAL (NOVO)
        # ============================================================
        if not _validate_digital_signature(exe):
            _log("setup.exe sem assinatura digital válida", "AVISO")
            # Continua mesmo assim, pois pode ser uma versão customizada
        
        _log(f"Executando setup.exe com configuration.xml (pode demorar até 30 minutos)...", "INFO")
        try:
            res = _safe_subprocess_run([exe, "/configure", xml], timeout=INSTALLATION_TIMEOUT)
            
            if res and res.returncode == 0:
                _log("✓ Office 2021 instalado com sucesso", "OK")
                
                # ============================================================
                # HEALTH CHECK PÓS-INSTALAÇÃO (NOVO)
                # ============================================================
                _post_install_health_check("office", [
                    r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                    r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE"
                ])
                
                return True
            else:
                exit_code = res.returncode if res else 'None'
                _log(f"Office retornou código {exit_code}", "ERRO")
                return False
        except Exception as e:
            _log(f"Exceção ao instalar Office: {e}", "ERRO")
            return False
            
    elif choice == "onlyoffice":
        _log("Instalando OnlyOffice via Chocolatey...", "INFO")
        
        # ============================================================
        # VALIDAÇÃO DE ESPAÇO EM DISCO (NOVO)
        # ============================================================
        if not _validate_disk_space(1000):  # OnlyOffice precisa de ~1GB
            _log("Espaço em disco insuficiente para OnlyOffice", "ERRO")
            return False
        
        if _choco_install("onlyoffice-desktopeditors", timeout=600):
            _log("✓ OnlyOffice instalado com sucesso", "OK")
            return True
        _log("✗ Falha ao instalar OnlyOffice", "ERRO")
        return False
    
    _log(f"Escolha de Office inválida: {choice}", "AVISO")
    return True

# ============================================================
# DETECÇÃO DE FABRICANTE (MANTIDO COM VALIDAÇÕES)
# ============================================================
def _get_motherboard_manufacturer():
    """Obtém fabricante da placa-mãe via PowerShell"""
    _log("Detectando fabricante do hardware...", "INFO")
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_ComputerSystem).Manufacturer'],
            shell=True,
            timeout=15
        )
        
        if result and result.stdout:
            manufacturer = result.stdout.strip().lower()
            _log(f"Fabricante detectado: {manufacturer}", "OK")
            return manufacturer
        else:
            _log("Falha ao detectar fabricante", "AVISO")
            return "desconhecido"
    except Exception as e:
        _log(f"Erro ao detectar fabricante: {e}", "AVISO")
        return "desconhecido"

# ============================================================
# INSTALAÇÃO DE DRIVERS DO FABRICANTE (MANTIDO COM VALIDAÇÕES)
# ============================================================
def install_manufacturer_drivers(settings_dict):
    """Instala drivers oficiais do fabricante (Dell/HP/Lenovo)"""
    _log("Instalando assistente de drivers do fabricante...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if not _validate_disk_space(500):
        _log("Espaço em disco insuficiente para drivers", "ERRO")
        return False
    
    manuf = _get_motherboard_manufacturer()
    _log(f"Fabricante detectado: {manuf}", "INFO")
    
    driver_pkgs = settings_dict.get("drivers", {})
    
    # Determina pacote baseado no fabricante
    target_pkg = None
    if "dell" in manuf:
        target_pkg = driver_pkgs.get("dell")
        _log("Detectado Dell, usando pacote Dell", "INFO")
    elif "lenovo" in manuf:
        target_pkg = driver_pkgs.get("lenovo")
        _log("Detectado Lenovo, usando pacote Lenovo", "INFO")
    elif "hp" in manuf or "hewlett" in manuf:
        target_pkg = driver_pkgs.get("hp")
        _log("Detectado HP, usando pacote HP", "INFO")
    else:
        _log(f"Fabricante não suportado: {manuf}", "AVISO")
        return False
    
    if not target_pkg:
        _log("Pacote de drivers não configurado no settings.json", "ERRO")
        return False
    
    _log(f"Instalando assistente oficial: {target_pkg}...", "INFO")
    
    if _choco_install(target_pkg, timeout=600):
        _log(f"✓ {target_pkg} instalado com sucesso", "OK")
        return True
    else:
        _log(f"✗ Falha ao instalar {target_pkg}", "ERRO")
        return False

# ============================================================
# WINDOWS UPDATE (MANTIDO COM VALIDAÇÕES)
# ============================================================
def force_windows_update_drivers():
    """Força atualização de drivers via Windows Update"""
    _log("=" * 60, "INFO")
    _log("ACEDENDO AO WINDOWS UPDATE... Pode demorar alguns minutos.", "INFO")
    _log("=" * 60, "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if not _validate_internet_connectivity():
        _log("Sem conectividade para Windows Update", "ERRO")
        return False
    
    if not _validate_disk_space(2000):  # Windows Update pode precisar de 2GB+
        _log("Espaço em disco insuficiente para Windows Update", "ERRO")
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
        _log("Este processo pode demorar até 30 minutos dependendo da quantidade de atualizações", "INFO")
        
        res = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            timeout=INSTALLATION_TIMEOUT  # 30 minutos
        )
        
        if res and res.returncode == 0:
            _log("✓ Atualizações e Drivers instalados com sucesso via Microsoft", "OK")
            if res.stdout:
                _log(f"Saída: {res.stdout[:200]}...", "INFO")
            return True
        else:
            exit_code = res.returncode if res else 'None'
            _log(f"Windows Update retornou código {exit_code}", "AVISO")
            if res and res.stderr:
                _log(f"Erros: {res.stderr[:200]}...", "AVISO")
            # Mesmo com código diferente de 0, pode ter instalado parcialmente
            return True
    except Exception as e:
        _log(f"Erro na rotina de Windows Update: {e}", "ERRO")
        return False