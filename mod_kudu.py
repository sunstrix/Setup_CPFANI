"""mod_kudu.py — Integração com o utilitário Kudu (limpeza e otimização)
   Versão: 1.0.2
   Projeto: Setup_CPFANI
   Licença: MIT
"""
import os
import sys
import subprocess
import urllib.request
import shutil
import tempfile
import zipfile
import json
from datetime import datetime
from pathlib import Path

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
# URLs alternativas para download
KUDU_URL_LATEST = "https://github.com/adventdevinc/kudu/releases/latest/download/kudu-win-x64.exe"
KUDU_URL_V1 = "https://github.com/adventdevinc/kudu/releases/download/v1.0.0/kudu-win-x64.exe"
KUDU_API_URL = "https://api.github.com/repos/adventdevinc/kudu/releases/latest"

def _log(msg, level="INFO"):
    """Sistema de log com timestamp e nível"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{ts}] [{level}] [KUDU] {msg}"
    print(log_msg, flush=True)
    # Também tenta escrever em um log específico
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

def ensure_kudu():
    r"""Garante que o executável do Kudu esteja disponível em C:\Scripts\kudu.exe"""
    if os.path.exists(KUDU_EXE):
        _log("Kudu já está presente.", "INFO")
        return True

    _log("Kudu não encontrado. Iniciando download...", "INFO")
    os.makedirs(SCRIPT_DIR, exist_ok=True)

    # Lista de URLs para tentar
    urls_to_try = [
        KUDU_URL_LATEST,
        KUDU_URL_V1,
    ]

    for url in urls_to_try:
        try:
            _log(f"Tentando baixar de {url}...", "INFO")
            urllib.request.urlretrieve(url, KUDU_EXE)
            # Verifica se o arquivo é válido (tamanho > 1MB)
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

    # Fallback: usar API do GitHub para obter URL do asset
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
                # Procura por qualquer executável que contenha "win" ou "x64" no nome
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

    _log("Falha ao baixar o Kudu. Verifique sua conexão e tente novamente.", "ERRO")
    return False

def _run_kudu(args):
    """Executa o Kudu com os argumentos fornecidos e retorna (sucesso, saída)"""
    if not ensure_kudu():
        return False, "Kudu não disponível"

    cmd = [KUDU_EXE, "--cli"] + args
    _log(f"Executando: {' '.join(cmd)}", "INFO")
    result = _safe_subprocess_run(cmd, timeout=600)  # 10 minutos para limpezas grandes
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

def kudu_system_clean():
    """Limpa arquivos temporários, logs, caches do sistema"""
    _log("Iniciando System Cleaner...", "INFO")
    success, output = _run_kudu(["--system", "--clean"])
    if success:
        _log("System Cleaner concluído.", "OK")
    else:
        _log("System Cleaner falhou.", "ERRO")
    return success

def kudu_app_clean():
    """Remove dados residuais de aplicativos desinstalados"""
    _log("Iniciando App Cleaner...", "INFO")
    success, output = _run_kudu(["--app", "--clean"])
    if success:
        _log("App Cleaner concluído.", "OK")
    else:
        _log("App Cleaner falhou.", "ERRO")
    return success

def kudu_gaming_clean():
    """Limpa caches de launchers de jogos e shaders GPU"""
    _log("Iniciando Gaming Cleaner...", "INFO")
    success, output = _run_kudu(["--gaming", "--clean"])
    if success:
        _log("Gaming Cleaner concluído.", "OK")
    else:
        _log("Gaming Cleaner falhou.", "ERRO")
    return success

def kudu_registry_clean():
    """Remove entradas de registro quebradas ou órfãs"""
    _log("Iniciando Registry Cleaner...", "INFO")
    success, output = _run_kudu(["--registry", "--clean"])
    if success:
        _log("Registry Cleaner concluído.", "OK")
    else:
        _log("Registry Cleaner falhou.", "ERRO")
    return success

def kudu_network_cleanup():
    """Limpa DNS, perfis Wi-Fi, cache ARP e outras configurações de rede"""
    _log("Iniciando Network Cleanup...", "INFO")
    success, output = _run_kudu(["--network", "--clean"])
    if success:
        _log("Network Cleanup concluído.", "OK")
    else:
        _log("Network Cleanup falhou.", "ERRO")
    return success

def kudu_debloat(use_defaults=True):
    """Remove bloatware do Windows. Se use_defaults for False, usa a lista personalizada do settings.json? Mas aqui usamos a lista do Kudu.
       Para fallback, podemos integrar com a nossa lista.
       O Kudu --debloat usa sua própria lista interna de bloatware.
    """
    _log("Iniciando Debloater (Kudu)...", "INFO")
    success, output = _run_kudu(["--debloat", "--clean"])
    if success:
        _log("Debloat concluído.", "OK")
    else:
        _log("Debloat falhou.", "ERRO")
    return success

# ============================================================
# FUNÇÕES DE GERENCIAMENTO DE DRIVERS (COMPLETAS)
# ============================================================

def kudu_driver_scan():
    """
    Analisa drivers desatualizados e pacotes obsoletos.
    Modo scan apenas — NÃO faz alterações no sistema.
    Retorna (bool, dict) com resultados da análise.
    """
    _log("Iniciando análise de drivers (Kudu)...", "INFO")
    success, output = _run_kudu(["--drivers", "--scan"])
    if success:
        _log("Análise de drivers concluída.", "OK")
        # Tenta parsear o output se for JSON
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
    """
    Analisa, baixa e instala atualizações de drivers, removendo pacotes obsoletos.
    Ação completa: scan + update + cleanup.
    """
    _log("Iniciando atualização de drivers (Kudu)...", "INFO")
    _log("Esta operação pode demorar alguns minutos.", "INFO")
    success, output = _run_kudu(["--drivers", "--update"])
    if success:
        _log("✓ Drivers atualizados com sucesso.", "OK")
        return True
    else:
        _log("Falha ao atualizar drivers.", "ERRO")
        return False

def kudu_driver_cleanup():
    """Remove apenas pacotes de drivers obsoletos (sem instalar novos)"""
    _log("Iniciando limpeza de drivers obsoletos (Kudu)...", "INFO")
    success, output = _run_kudu(["--drivers", "--clean"])
    if success:
        _log("✓ Drivers obsoletos removidos.", "OK")
        return True
    else:
        _log("Falha ao remover drivers obsoletos.", "ERRO")
        return False

# Mantida para compatibilidade com código existente (apenas limpeza)
def kudu_driver_manager():
    """Limpa drivers obsoletos e pode ajudar a resolver conflitos (alias para kudu_driver_cleanup)"""
    _log("Iniciando Driver Manager (limpeza)...", "INFO")
    return kudu_driver_cleanup()

# ============================================================
# SERVIÇOS E OUTRAS FUNÇÕES
# ============================================================

def kudu_service_manager():
    """Otimiza serviços do Windows desativando os desnecessários.
       O Kudu aplica uma lista de otimizações baseadas em boas práticas.
       A lista de otimizações inclui: desativar Print Spooler se não houver impressora,
       desativar Serviços de Fax, desativar Xbox Live Networking (se não jogar),
       desativar Windows Search (se não usar), etc.
       Consulte a documentação oficial para a lista completa.
    """
    _log("Iniciando Service Manager (Otimização)...", "INFO")
    success, output = _run_kudu(["--services", "--optimize"])
    if success:
        _log("Service Manager concluído.", "OK")
    else:
        _log("Service Manager falhou.", "ERRO")
    return success

def kudu_one_click_clean():
    """
    Executa uma limpeza completa de todas as categorias.
    Inclui System, App, Gaming, Registry, Network, Debloat, Drivers (update) e Services.
    """
    _log("Iniciando One‑Click Clean (todas as categorias)...", "INFO")
    _log("Atualização de drivers incluída (pode demorar alguns minutos).", "INFO")
    success, output = _run_kudu(["--all", "--clean"])
    if success:
        _log("One‑Click Clean concluído.", "OK")
    else:
        _log("One‑Click Clean falhou.", "ERRO")
    return success

# Função para obter a lista de otimizações de serviços (apenas informativa)
def get_service_optimizations_list():
    """Retorna uma lista descritiva das otimizações que o Kudu aplica em serviços."""
    return [
        "Desativa o serviço Print Spooler se nenhuma impressora estiver conectada.",
        "Desativa o serviço de Fax (Fax Service) se não utilizado.",
        "Desativa os serviços do Xbox Live Networking (XblAuthManager, XblGameSave, XboxNetApiSvc) se não houver jogos instalados.",
        "Desativa o serviço de Busca do Windows (Windows Search) se o usuário não usar a pesquisa de arquivos.",
        "Desativa o serviço de Tempo (Windows Time) se não precisar de sincronização NTP.",
        "Desativa o serviço de Assinatura de Controle Remoto (Remote Registry) por segurança.",
        "Desativa o serviço de Compartilhamento de Rede (Server) se não houver compartilhamento de arquivos.",
        "Desativa o serviço de Cliente de Compartilhamento (Workstation) se não houver acesso a recursos de rede.",
        "Desativa o serviço de Gerenciamento de Dispositivos Móveis (DMWappushService) se não houver MDM.",
        "E outras otimizações padrão para melhorar desempenho e segurança."
    ]