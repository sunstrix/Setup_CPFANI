"""mod_instalar.py — V5.9.3 (CP Fani)"""
import subprocess
import os
import shutil
import sys
import platform
import time
from datetime import datetime

# Configuração de encoding para evitar crashes em caracteres especiais
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors='replace')
        sys.stderr.reconfigure(encoding="utf-8", errors='replace')
    except Exception:
        pass

def _log(msg, level="INFO"):
    """Sistema de log com timestamp e nível"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg, flush=True)

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

def check_chocolatey():
    """Verifica se Chocolatey está instalado e funcional"""
    _log("Verificando Chocolatey...", "INFO")
    
    if shutil.which("choco") is None:
        _log("Chocolatey não encontrado no PATH", "ERRO")
        raise RuntimeError("Chocolatey não encontrado no PATH.")
    
    result = _safe_subprocess_run(["choco", "--version"], timeout=15)
    
    if not result:
        _log("Falha ao executar choco --version", "ERRO")
        raise RuntimeError("Erro ao executar Chocolatey.")
    
    if result.returncode != 0:
        _log(f"Chocolatey retornou código {result.returncode}", "ERRO")
        raise RuntimeError(f"Erro no Chocolatey. Saida: {result.stderr}")
    
    version = result.stdout.strip()
    _log(f"Chocolatey OK: {version}", "OK")
    return True

def _install_anydesk(timeout=300):
    """Instala AnyDesk com fallback para múltiplos métodos"""
    _log("A instalar AnyDesk com redundância...", "INFO")
    
    # Tentativa 1: Chocolatey
    _log("Tentativa 1/3: Instalando via Chocolatey...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["choco", "install", "anydesk", "-y", "--no-progress"],
            timeout=timeout
        )
        
        if res and res.returncode in (0, 1641, 3010, 1638):
            _log("✓ AnyDesk instalado via Chocolatey", "OK")
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
            return True
        else:
            _log(f"WinGet retornou código {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Exceção no WinGet: {e}", "AVISO")
    
    # Tentativa 3: Download direto (fallback final)
    _log("Tentativa 3/3: Download direto do site oficial...", "INFO")
    try:
        import urllib.request
        
        anydesk_url = "https://download.anydesk.com/AnyDesk.exe"
        temp_path = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "AnyDesk_Install.exe")
        
        _log(f"Baixando AnyDesk de {anydesk_url}...")
        urllib.request.urlretrieve(anydesk_url, temp_path)
        
        # Validação de tamanho (deve ser maior que 1MB)
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1048576:
            _log("Executando instalador silencioso...", "INFO")
            res = _safe_subprocess_run(
                [temp_path, "--install", "--silent", "--start-with-win"],
                timeout=timeout
            )
            
            if res and res.returncode == 0:
                _log("✓ AnyDesk instalado via download direto", "OK")
                # Limpa arquivo temporário
                try:
                    os.remove(temp_path)
                except:
                    pass
                return True
            else:
                _log(f"Instalador retornou código {res.returncode if res else 'None'}", "AVISO")
        else:
            _log("Arquivo baixado é muito pequeno ou não existe", "ERRO")
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        _log(f"Exceção no download direto: {e}", "AVISO")
    
    _log("✗ Falha absoluta ao instalar AnyDesk após 3 tentativas", "ERRO")
    return False

def _choco_install(app, timeout=300, max_retries=2):
    """Instala pacote via Chocolatey com retry logic"""
    app = app.strip()
    if not app:
        _log("Nome de pacote vazio", "ERRO")
        return False
    
    _log(f"A instalar pacote via Choco: {app}...", "INFO")
    
    for attempt in range(1, max_retries + 1):
        _log(f"Tentativa {attempt}/{max_retries} para {app}", "INFO")
        
        try:
            r = _safe_subprocess_run(
                ["choco", "install", app, "-y", "--no-progress", "--limit-output"],
                timeout=timeout
            )
            
            if r and r.returncode in (0, 1641, 3010, 1638):
                _log(f"✓ Pacote {app} instalado/verificado com sucesso", "OK")
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

def install_office_suite(choice):
    """Instala suíte Office conforme escolha do usuário"""
    _log(f"Instalando Office: {choice}", "INFO")
    
    if choice == "office2021":
        _log("A instalar Office 2021 via ODT...", "INFO")
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
        if exe_size < 1048576:  # Mínimo 1MB
            _log(f"Arquivo setup.exe muito pequeno ({exe_size} bytes)", "ERRO")
            return False
        
        _log(f"Executando setup.exe com configuration.xml (pode demorar até 30 minutos)...", "INFO")
        try:
            res = _safe_subprocess_run([exe, "/configure", xml], timeout=1800)
            
            if res and res.returncode == 0:
                _log("✓ Office 2021 instalado com sucesso", "OK")
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
        if _choco_install("onlyoffice-desktopeditors", timeout=600):
            _log("✓ OnlyOffice instalado com sucesso", "OK")
            return True
        _log("✗ Falha ao instalar OnlyOffice", "ERRO")
        return False
    
    _log(f"Escolha de Office inválida: {choice}", "AVISO")
    return True

def _get_motherboard_manufacturer():
    """Obtém fabricante da placa-mãe via PowerShell"""
    _log("Detectando fabricante do hardware...", "INFO")
    try:
        # CORREÇÃO: removido shell=True para usar lista de argumentos corretamente
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_ComputerSystem).Manufacturer'],
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

def install_manufacturer_drivers(settings_dict):
    """Instala drivers oficiais do fabricante (Dell/HP/Lenovo)"""
    _log("Instalando assistente de drivers do fabricante...", "INFO")
    
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

def force_windows_update_drivers():
    """Força atualização de drivers via Windows Update"""
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
    Write-Host "Processo concluido."
    """
    
    try:
        _log("Executando script PowerShell para Windows Update...", "INFO")
        _log("Este processo pode demorar até 30 minutos dependendo da quantidade de atualizações", "INFO")
        
        res = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            timeout=1800  # 30 minutos
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