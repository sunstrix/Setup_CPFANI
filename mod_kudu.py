"""mod_kudu.py — Integração com o utilitário Kudu (limpeza e otimização)
   Versão: 1.0.3
   Projeto: Setup_CPFANI
   Licença: MIT
"""
import os
import sys
import subprocess
import urllib.request
import json
from datetime import datetime

# Configuração de encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors='replace')
        sys.stderr.reconfigure(encoding="utf-8", errors='replace')
    except Exception:
        pass

# Constantes
SCRIPT_DIR = r"C:\Scripts"
KUDU_EXE = os.path.join(SCRIPT_DIR, "kudu.exe")
KUDU_URL_LATEST = "https://github.com/adventdevinc/kudu/releases/latest/download/kudu-win-x64.exe"
KUDU_URL_V1 = "https://github.com/adventdevinc/kudu/releases/download/v1.0.0/kudu-win-x64.exe"
KUDU_API_URL = "https://api.github.com/repos/adventdevinc/kudu/releases/latest"

# Cache de falha para evitar repetir download
_KUDU_DOWNLOAD_FAILED = False

def _log(msg, level="INFO"):
    """Sistema de log com timestamp e nível"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{ts}] [{level}] [KUDU] {msg}"
    print(log_msg, flush=True)
    try:
        log_dir = SCRIPT_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "kudu_integration.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception:
        pass

def _safe_subprocess_run(cmd, timeout=300, shell=False, capture_output=True, **kwargs):
    """Execução segura de subprocessos com timeout"""
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

def _install_via_winget():
    """Tenta instalar o Kudu via winget (fallback)"""
    _log("Tentando instalar Kudu via winget...", "INFO")
    try:
        # Verifica se winget está disponível
        check = _safe_subprocess_run(["winget", "--version"], timeout=10)
        if check is None or check.returncode != 0:
            _log("winget não disponível.", "AVISO")
            return False
        
        # Tenta instalar o Kudu (supondo que o id seja 'Kudu' ou similar)
        result = _safe_subprocess_run(
            ["winget", "install", "--id", "Kudu", "--silent", "--accept-package-agreements"],
            timeout=300
        )
        if result and result.returncode == 0:
            _log("Kudu instalado via winget com sucesso.", "OK")
            # Verifica se o executável foi instalado em algum lugar comum
            possible_paths = [
                r"C:\Program Files\Kudu\kudu.exe",
                r"C:\Program Files (x86)\Kudu\kudu.exe",
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Kudu", "kudu.exe")
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    # Copia para o diretório padrão
                    shutil.copy2(p, KUDU_EXE)
                    _log(f"Executável copiado de {p} para {KUDU_EXE}", "OK")
                    return True
            # Se não encontrou, tenta localizar no PATH
            which = _safe_subprocess_run(["where", "kudu"], timeout=10)
            if which and which.returncode == 0 and which.stdout.strip():
                path_found = which.stdout.strip().split('\n')[0]
                shutil.copy2(path_found, KUDU_EXE)
                _log(f"Executável copiado de {path_found} para {KUDU_EXE}", "OK")
                return True
            _log("Kudu instalado via winget, mas executável não localizado.", "ERRO")
            return False
        else:
            _log("Falha ao instalar via winget.", "ERRO")
            return False
    except Exception as e:
        _log(f"Exceção no winget: {e}", "ERRO")
        return False

def ensure_kudu():
    """Garante que o executável do Kudu esteja disponível em C:\Scripts\kudu.exe"""
    global _KUDU_DOWNLOAD_FAILED

    if os.path.exists(KUDU_EXE):
        return True

    if _KUDU_DOWNLOAD_FAILED:
        _log("Download do Kudu já falhou anteriormente nesta execução. Pulando.", "AVISO")
        return False

    _log("Kudu não encontrado. Iniciando download...", "INFO")
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    # Lista de URLs para tentar
    urls_to_try = [KUDU_URL_LATEST, KUDU_URL_V1]
    for url in urls_to_try:
        try:
            _log(f"Tentando baixar de {url}...", "INFO")
            urllib.request.urlretrieve(url, KUDU_EXE)
            if os.path.getsize(KUDU_EXE) > 1024 * 1024:
                _log("Kudu baixado com sucesso.", "OK")
                os.chmod(KUDU_EXE, 0o755)
                return True
            else:
                _log("Arquivo muito pequeno, removendo...", "ERRO")
                os.remove(KUDU_EXE)
        except Exception as e:
            _log(f"Erro no download: {e}", "AVISO")
            continue

    # Fallback via API do GitHub
    try:
        _log("Tentando obter URL via API do GitHub...", "INFO")
        req = urllib.request.Request(
            KUDU_API_URL,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Setup_CPFANI/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            assets = data.get("assets", [])
            for asset in assets:
                if asset["name"].endswith(".exe") and ("win" in asset["name"].lower() or "x64" in asset["name"].lower()):
                    download_url = asset["browser_download_url"]
                    _log(f"Baixando de {download_url}...", "INFO")
                    urllib.request.urlretrieve(download_url, KUDU_EXE)
                    if os.path.getsize(KUDU_EXE) > 1024 * 1024:
                        _log("Kudu baixado via API com sucesso.", "OK")
                        os.chmod(KUDU_EXE, 0o755)
                        return True
                    else:
                        os.remove(KUDU_EXE)
                        _log("Arquivo baixado via API é muito pequeno.", "ERRO")
                    break
    except Exception as e:
        _log(f"Erro na API do GitHub: {e}", "ERRO")

    # Fallback via winget
    _log("Tentando fallback via winget...", "INFO")
    if _install_via_winget():
        return True

    _KUDU_DOWNLOAD_FAILED = True
    _log("Falha ao baixar o Kudu. Verifique sua conexão e tente novamente.", "ERRO")
    return False

def _run_kudu(args):
    """Executa o Kudu com os argumentos fornecidos e retorna (sucesso, saída)"""
    if not ensure_kudu():
        return False, "Kudu não disponível"

    cmd = [KUDU_EXE, "--cli"] + args
    _log(f"Executando: {' '.join(cmd)}", "INFO")
    result = _safe_subprocess_run(cmd, timeout=600)
    if result is None:
        return False, "Subprocesso falhou"
    if result.returncode == 0:
        _log("Comando executado com sucesso.", "OK")
        return True, result.stdout
    else:
        _log(f"Comando retornou código {result.returncode}", "ERRO")
        if result.stderr:
            _log(f"Erro: {result.stderr[:200]}", "AVISO")
        return False, result.stderr

# ------------------------------------------------------------
# Funções de limpeza (System, App, Gaming, Registry, Network, Debloat)
# ------------------------------------------------------------
def kudu_system_clean():
    _log("Iniciando System Cleaner...", "INFO")
    success, _ = _run_kudu(["--system", "--clean"])
    if success:
        _log("System Cleaner concluído.", "OK")
    else:
        _log("System Cleaner falhou.", "ERRO")
    return success

def kudu_app_clean():
    _log("Iniciando App Cleaner...", "INFO")
    success, _ = _run_kudu(["--app", "--clean"])
    if success:
        _log("App Cleaner concluído.", "OK")
    else:
        _log("App Cleaner falhou.", "ERRO")
    return success

def kudu_gaming_clean():
    _log("Iniciando Gaming Cleaner...", "INFO")
    success, _ = _run_kudu(["--gaming", "--clean"])
    if success:
        _log("Gaming Cleaner concluído.", "OK")
    else:
        _log("Gaming Cleaner falhou.", "ERRO")
    return success

def kudu_registry_clean():
    _log("Iniciando Registry Cleaner...", "INFO")
    success, _ = _run_kudu(["--registry", "--clean"])
    if success:
        _log("Registry Cleaner concluído.", "OK")
    else:
        _log("Registry Cleaner falhou.", "ERRO")
    return success

def kudu_network_cleanup():
    _log("Iniciando Network Cleanup...", "INFO")
    success, _ = _run_kudu(["--network", "--clean"])
    if success:
        _log("Network Cleanup concluído.", "OK")
    else:
        _log("Network Cleanup falhou.", "ERRO")
    return success

def kudu_debloat(use_defaults=True):
    _log("Iniciando Debloater (Kudu)...", "INFO")
    success, _ = _run_kudu(["--debloat", "--clean"])
    if success:
        _log("Debloat concluído.", "OK")
    else:
        _log("Debloat falhou.", "ERRO")
    return success

# ------------------------------------------------------------
# Gerenciamento de Drivers
# ------------------------------------------------------------
def kudu_driver_scan():
    _log("Iniciando análise de drivers (Kudu)...", "INFO")
    success, output = _run_kudu(["--drivers", "--scan"])
    if success:
        _log("Análise de drivers concluída.", "OK")
        try:
            if output and output.strip().startswith('{'):
                data = json.loads(output)
                return True, data
        except:
            pass
        return True, {"raw": output}
    else:
        _log("Análise de drivers falhou.", "ERRO")
        return False, {"error": output}

def kudu_driver_update():
    _log("Iniciando atualização de drivers (Kudu)...", "INFO")
    _log("Esta operação pode demorar alguns minutos.", "INFO")
    success, _ = _run_kudu(["--drivers", "--update"])
    if success:
        _log("✓ Drivers atualizados com sucesso.", "OK")
    else:
        _log("Falha ao atualizar drivers.", "ERRO")
    return success

def kudu_driver_cleanup():
    _log("Iniciando limpeza de drivers obsoletos (Kudu)...", "INFO")
    success, _ = _run_kudu(["--drivers", "--clean"])
    if success:
        _log("✓ Drivers obsoletos removidos.", "OK")
    else:
        _log("Falha ao remover drivers obsoletos.", "ERRO")
    return success

def kudu_driver_manager():
    """Alias para kudu_driver_cleanup (mantido para compatibilidade)"""
    _log("Iniciando Driver Manager (limpeza)...", "INFO")
    return kudu_driver_cleanup()

# ------------------------------------------------------------
# Serviços e One-Click
# ------------------------------------------------------------
def kudu_service_manager():
    _log("Iniciando Service Manager (Otimização)...", "INFO")
    success, _ = _run_kudu(["--services", "--optimize"])
    if success:
        _log("Service Manager concluído.", "OK")
    else:
        _log("Service Manager falhou.", "ERRO")
    return success

def kudu_one_click_clean():
    _log("Iniciando One‑Click Clean (todas as categorias)...", "INFO")
    _log("Atualização de drivers incluída (pode demorar alguns minutos).", "INFO")
    success, _ = _run_kudu(["--all", "--clean"])
    if success:
        _log("One‑Click Clean concluído.", "OK")
    else:
        _log("One‑Click Clean falhou.", "ERRO")
    return success

def get_service_optimizations_list():
    return [
        "Desativa o serviço Print Spooler se nenhuma impressora estiver conectada.",
        "Desativa o serviço de Fax (Fax Service) se não utilizado.",
        "Desativa os serviços do Xbox Live Networking se não houver jogos.",
        "Desativa o serviço de Busca do Windows (Windows Search) se não usado.",
        "Desativa o serviço de Tempo (Windows Time) se não precisar de NTP.",
        "Desativa o serviço de Assinatura de Controle Remoto (Remote Registry) por segurança.",
        "Desativa o serviço de Compartilhamento de Rede (Server) se não houver compartilhamento.",
        "Desativa o serviço de Cliente de Compartilhamento (Workstation) se não houver acesso a rede.",
        "Desativa o serviço de Gerenciamento de Dispositivos Móveis (DMWappushService) se não houver MDM.",
        "E outras otimizações padrão para melhorar desempenho e segurança."
    ]