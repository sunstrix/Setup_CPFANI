# -*- coding: ascii -*-
"""mod_instalar.py - V5.9.4 (CP Fani)"""
import subprocess
import os
import shutil
import sys
import platform
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CREATION_FLAGS_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _log(msg, level="INFO"):
    """Sistema de log com timestamp e nivel"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{ts}] [{level}] {msg}"
    print(log_msg, flush=True)


def _get_install_dir():
    """Obtem diretorio de instaladores com fallback seguro"""
    base = os.environ.get("SCRIPT_DIR", "").strip()
    if not base:
        base = os.getcwd()

    candidates = [
        os.path.join(base, "Installers"),
        os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "Setup_CPFANI_Installers")
    ]

    for candidate in candidates:
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except Exception:
            continue

    return os.environ.get("TEMP", r"C:\Windows\Temp")


INSTALL_DIR = _get_install_dir()


def _get_file_sha256(file_path, chunk_size=65536):
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest().upper()
    except Exception as e:
        _log(f"Erro ao calcular SHA256 de {file_path}: {e}", "ERRO")
        return None


def _verify_sha256(file_path, expected_sha256):
    if not expected_sha256:
        _log("Hash SHA256 esperado nao informado.", "AVISO")
        return False

    actual = _get_file_sha256(file_path)
    if not actual:
        return False

    if actual.upper() != expected_sha256.strip().upper():
        _log(f"Hash SHA256 invalido para {file_path}. Esperado: {expected_sha256}, Obtido: {actual}", "ERRO")
        return False

    _log(f"[OK] Hash SHA256 validado: {file_path}", "OK")
    return True


def _get_expected_installer_sha256(file_name, env_key=None):
    """Obtem hash esperado por ambiente ou sidecar .sha256"""
    if env_key:
        env_value = os.environ.get(f"CPFANI_{env_key}_SHA256", "").strip().upper()
        if env_value:
            return env_value

    base_env = os.path.basename(file_name).upper().replace(".", "_").replace("-", "_")
    env_value = os.environ.get(f"CPFANI_{base_env}_SHA256", "").strip().upper()
    if env_value:
        return env_value

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sidecar = os.path.join(script_dir, "resources", f"{os.path.basename(file_name)}.sha256")

    if os.path.exists(sidecar):
        try:
            with open(sidecar, "r", encoding="ascii", errors="ignore") as f:
                content = f.read().strip().split()[0].upper()
                if content:
                    return content
        except Exception as e:
            _log(f"Erro ao ler sidecar de hash {sidecar}: {e}", "AVISO")

    return ""


def _download_installer_with_hash(url, dest_path, min_size_mb=1, max_retries=3, timeout=300, expected_sha256=None):
    """Download robusto com validacao de tamanho e SHA256 obrigatorio"""
    if not expected_sha256:
        _log("Hash SHA256 esperado nao informado. Download bloqueado por integridade.", "ERRO")
        return False

    for attempt in range(1, max_retries + 1):
        try:
            _log(f"Tentativa {attempt}/{max_retries}: Baixando {os.path.basename(dest_path)}...")
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            start_time = time.time()
            urllib.request.urlretrieve(url, dest_path)
            elapsed = time.time() - start_time

            file_size = os.path.getsize(dest_path)
            min_size_bytes = min_size_mb * 1024 * 1024

            if file_size < min_size_bytes:
                _log(f"Arquivo muito pequeno ({file_size} bytes < {min_size_bytes} bytes). Removendo...", "AVISO")
                try:
                    os.remove(dest_path)
                except Exception as e:
                    _log(f"Falha ao remover arquivo corrompido: {e}", "AVISO")

                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return False

            if not _verify_sha256(dest_path, expected_sha256):
                try:
                    os.remove(dest_path)
                except Exception as e:
                    _log(f"Falha ao remover arquivo com hash invalido: {e}", "AVISO")

                if attempt < max_retries:
                    time.sleep(2)
                    continue
                return False

            _log(f"[OK] Download concluido: {file_size / (1024*1024):.2f} MB em {elapsed:.1f}s", "OK")
            return True
        except Exception as e:
            _log(f"Falha na tentativa {attempt}: {e}", "ERRO")

            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception as e_rem:
                    _log(f"Falha ao remover arquivo parcial: {e_rem}", "AVISO")

            if attempt < max_retries:
                time.sleep(3)

    return False


def _safe_subprocess_run(cmd, timeout=300, shell=False, capture_output=True, **kwargs):
    """Execucao segura de subprocessos com timeout e tratamento de erros"""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture_output,
            timeout=timeout,
            creationflags=CREATION_FLAGS_NO_WINDOW,
            encoding="utf-8",
            errors="replace",
            **kwargs
        )
        return result
    except subprocess.TimeoutExpired:
        cmd_str = cmd if isinstance(cmd, str) else " ".join([str(x) for x in cmd])
        _log(f"Timeout ({timeout}s) ao executar comando: {cmd_str}", "AVISO")
        return None
    except Exception as e:
        _log(f"Erro ao executar subprocesso: {e}", "ERRO")
        return None


def check_chocolatey():
    """Verifica se Chocolatey esta instalado e funcional"""
    _log("Verificando Chocolatey...", "INFO")

    if shutil.which("choco") is None:
        _log("Chocolatey nao encontrado no PATH", "ERRO")
        raise RuntimeError("Chocolatey nao encontrado no PATH.")

    result = _safe_subprocess_run(["choco", "--version"], timeout=15)
    if not result:
        _log("Falha ao executar choco --version", "ERRO")
        raise RuntimeError("Erro ao executar Chocolatey.")

    if result.returncode != 0:
        _log(f"Chocolatey retornou codigo {result.returncode}", "ERRO")
        raise RuntimeError(f"Erro no Chocolatey. Saida: {result.stderr}")

    version = result.stdout.strip()
    _log(f"Chocolatey OK: {version}", "OK")
    return True


def _winget_install(app, timeout=300):
    """Instala pacote via winget com fallback (usado quando Chocolatey falha)"""
    app = app.strip()
    _log(f"Tentando instalar {app} via winget (fallback)...", "INFO")

    winget_map = {
        "googlechrome": "Google.Chrome",
        "anydesk": "AnyDeskSoftwareGmbH.AnyDesk",
        "rustdesk": "RustDesk.RustDesk",
        "7zip": "7zip.7zip",
        "flameshot": "Flameshot.Flameshot",
        "teamviewer": "TeamViewer.TeamViewer",
        "vlc": "VideoLAN.VLC",
        "winrar": "RARLab.WinRAR",
        "vcredist-all": "Microsoft.VCRedist.2015+.x64",
        "ditto": "Ditto.Ditto",
        "sharex": "ShareX.ShareX",
        "notepadplusplus": "Notepad++.Notepad++",
        "powertoys": "Microsoft.PowerToys",
        "firefox": "Mozilla.Firefox",
        "adobereader": "Adobe.Acrobat.Reader.64-bit",
        "paint.net": "dotPDN.Paint.NET",
        "dellcommandupdate": "Dell.CommandUpdate",
        "lenovo-system-update": "Lenovo.SystemUpdate",
        "hp-support-assistant": "HP.SupportAssistant",
        "onlyoffice-desktopeditors": "ONLYOFFICE.DesktopEditors",
    }

    winget_id = winget_map.get(app, app)
    _log(f"Usando winget ID: {winget_id}", "INFO")

    check = _safe_subprocess_run(["winget", "--version"], timeout=10)
    if check is None or check.returncode != 0:
        _log("winget nao disponivel. Pulando fallback.", "AVISO")
        return False

    result = _safe_subprocess_run(
        ["winget", "install", "--id", winget_id, "--silent", "--accept-package-agreements", "--accept-source-agreements"],
        timeout=timeout
    )

    if result and result.returncode == 0:
        _log(f"[OK] {app} instalado com sucesso via winget", "OK")
        return True

    _log(f"winget falhou para {app} com codigo {result.returncode if result else 'None'}", "AVISO")
    return False


def _install_anydesk(timeout=300):
    """Instala AnyDesk com fallback para multiplos metodos"""
    _log("Instalando AnyDesk com redundancia...", "INFO")

    _log("Tentativa 1/3: Instalando via Chocolatey...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["choco", "install", "anydesk", "-y", "--no-progress"],
            timeout=timeout
        )
        if res and res.returncode in (0, 1641, 3010, 1638):
            _log("[OK] AnyDesk instalado via Chocolatey", "OK")
            return True

        _log(f"Chocolatey retornou codigo {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Excecao no Chocolatey: {e}", "AVISO")

    _log("Tentativa 2/3: Instalando via WinGet...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["winget", "install", "--id", "AnyDeskSoftwareGmbH.AnyDesk", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            timeout=timeout
        )
        if res and res.returncode == 0:
            _log("[OK] AnyDesk instalado via WinGet", "OK")
            return True

        _log(f"WinGet retornou codigo {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Excecao no WinGet: {e}", "AVISO")

    _log("Tentativa 3/3: Download direto do site oficial...", "INFO")
    try:
        anydesk_url = "https://download.anydesk.com/AnyDesk.exe"
        temp_path = os.path.join(INSTALL_DIR, "AnyDesk_Install.exe")
        expected_hash = _get_expected_installer_sha256("AnyDesk.exe", "ANYDESK")

        if not expected_hash:
            _log("Hash SHA256 do AnyDesk nao configurado. Use CPFANI_ANYDESK_SHA256 ou resources/AnyDesk.exe.sha256. Pulando download direto.", "AVISO")
        else:
            _log(f"Baixando AnyDesk de {anydesk_url}...")
            if _download_installer_with_hash(
                anydesk_url,
                temp_path,
                min_size_mb=1,
                max_retries=3,
                timeout=timeout,
                expected_sha256=expected_hash
            ):
                _log("Executando instalador silencioso...", "INFO")
                res = _safe_subprocess_run(
                    [temp_path, "--install", "--silent", "--start-with-win"],
                    timeout=timeout
                )

                if res and res.returncode == 0:
                    _log("[OK] AnyDesk instalado via download direto", "OK")
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                    return True

                _log(f"Instalador retornou codigo {res.returncode if res else 'None'}", "AVISO")

                try:
                    os.remove(temp_path)
                except Exception:
                    pass
    except Exception as e:
        _log(f"Excecao no download direto: {e}", "AVISO")

    _log("[ERRO] Falha absoluta ao instalar AnyDesk apos 3 tentativas", "ERRO")
    return False


def _install_rustdesk(timeout=300):
    """Instala RustDesk com fallback para multiplos metodos"""
    _log("Instalando RustDesk com redundancia...", "INFO")

    _log("Tentativa 1/3: Instalando via Chocolatey...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["choco", "install", "rustdesk", "-y", "--no-progress"],
            timeout=timeout
        )
        if res and res.returncode in (0, 1641, 3010, 1638):
            _log("[OK] RustDesk instalado via Chocolatey", "OK")
            return True

        _log(f"Chocolatey retornou codigo {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Excecao no Chocolatey: {e}", "AVISO")

    _log("Tentativa 2/3: Instalando via WinGet...", "INFO")
    try:
        res = _safe_subprocess_run(
            ["winget", "install", "--id", "RustDesk.RustDesk", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
            timeout=timeout
        )
        if res and res.returncode == 0:
            _log("[OK] RustDesk instalado via WinGet", "OK")
            return True

        _log(f"WinGet retornou codigo {res.returncode if res else 'None'}", "AVISO")
    except Exception as e:
        _log(f"Excecao no WinGet: {e}", "AVISO")

    _log("AVISO: Instalacao silenciosa via download direto nao implementada para RustDesk - usar Chocolatey/WinGet", "AVISO")
    _log("[ERRO] Falha absoluta ao instalar RustDesk apos 3 tentativas", "ERRO")
    return False


def _choco_install(app, timeout=300, max_retries=2):
    """Instala pacote via Chocolatey com retry logic, com fallback para winget"""
    app = app.strip()
    if not app:
        _log("Nome de pacote vazio", "ERRO")
        return False

    _log(f"Instalando pacote via Choco: {app}...", "INFO")

    for attempt in range(1, max_retries + 1):
        _log(f"Tentativa {attempt}/{max_retries} para {app}", "INFO")
        try:
            r = _safe_subprocess_run(
                ["choco", "install", app, "-y", "--no-progress", "--limit-output"],
                timeout=timeout
            )

            if r and r.returncode in (0, 1641, 3010, 1638):
                _log(f"[OK] Pacote {app} instalado/verificado com sucesso", "OK")
                return True

            exit_code = r.returncode if r else "None"
            _log(f"Erro Choco {app}: Exit Code {exit_code}", "AVISO")

            if attempt < max_retries:
                _log("Aguardando 5 segundos antes de nova tentativa...", "INFO")
                time.sleep(5)
        except Exception as e:
            _log(f"Excecao Choco {app}: {e}", "AVISO")
            if attempt < max_retries:
                _log("Aguardando 5 segundos antes de nova tentativa...", "INFO")
                time.sleep(5)

    _log(f"Todas as tentativas via Chocolatey falharam para {app}. Tentando winget...", "AVISO")
    if _winget_install(app, timeout=timeout):
        return True

    _log(f"[ERRO] Falha ao instalar {app} (Chocolatey e winget)", "ERRO")
    return False


def install_office_suite(choice):
    """Instala suite Office conforme escolha do usuario"""
    _log(f"Instalando Office: {choice}", "INFO")

    if choice == "office2021":
        _log("Instalando Office 2021 via ODT...", "INFO")
        d = os.path.dirname(os.path.abspath(__file__))
        exe = os.path.join(d, "resources", "setup.exe")
        xml = os.path.join(d, "resources", "configuration.xml")

        if not os.path.exists(exe):
            _log(f"Arquivo nao encontrado: {exe}", "ERRO")
            return False

        if not os.path.exists(xml):
            _log(f"Arquivo nao encontrado: {xml}", "ERRO")
            return False

        exe_size = os.path.getsize(exe)
        if exe_size < 1048576:
            _log(f"Arquivo setup.exe muito pequeno ({exe_size} bytes)", "ERRO")
            return False

        expected_hash = _get_expected_installer_sha256("setup.exe", "OFFICE_SETUP")
        if expected_hash:
            if not _verify_sha256(exe, expected_hash):
                _log("Hash SHA256 do setup.exe invalido. Instalacao do Office bloqueada.", "ERRO")
                return False
        else:
            _log("Hash SHA256 do setup.exe nao configurado. Validacao de integridade incompleta.", "AVISO")

        _log("Executando setup.exe com configuration.xml (pode demorar ate 30 minutos)...", "INFO")
        try:
            res = _safe_subprocess_run([exe, "/configure", xml], timeout=1800)
            if res and res.returncode == 0:
                _log("[OK] Office 2021 instalado com sucesso", "OK")
                return True

            exit_code = res.returncode if res else "None"
            _log(f"Office retornou codigo {exit_code}", "ERRO")
            return False
        except Exception as e:
            _log(f"Excecao ao instalar Office: {e}", "ERRO")
            return False

    elif choice == "onlyoffice":
        _log("Instalando OnlyOffice via Chocolatey...", "INFO")
        if _choco_install("onlyoffice-desktopeditors", timeout=600):
            _log("[OK] OnlyOffice instalado com sucesso", "OK")
            return True

        _log("[ERRO] Falha ao instalar OnlyOffice", "ERRO")
        return False

    _log(f"Escolha de Office invalida: {choice}", "AVISO")
    return True


def _get_motherboard_manufacturer():
    """Obtem fabricante da placa-mae via PowerShell"""
    _log("Detectando fabricante do hardware...", "INFO")
    try:
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Manufacturer"],
            timeout=15
        )

        if result and result.stdout:
            manufacturer = result.stdout.strip().lower()
            _log(f"Fabricante detectado: {manufacturer}", "OK")
            return manufacturer

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
        _log(f"Fabricante nao suportado: {manuf}", "AVISO")
        return False

    if not target_pkg:
        _log("Pacote de drivers nao configurado no settings.json", "ERRO")
        return False

    _log(f"Instalando assistente oficial: {target_pkg}...", "INFO")
    if _choco_install(target_pkg, timeout=600):
        _log(f"[OK] {target_pkg} instalado com sucesso", "OK")
        return True

    _log(f"[ERRO] Falha ao instalar {target_pkg}", "ERRO")
    return False


def force_windows_update_drivers():
    """Forca atualizacao de drivers via Windows Update"""
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
        _log("Este processo pode demorar ate 30 minutos dependendo da quantidade de atualizacoes", "INFO")
        res = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            timeout=1800
        )

        if res and res.returncode == 0:
            _log("[OK] Atualizacoes e Drivers instalados com sucesso via Microsoft", "OK")
            if res.stdout:
                _log(f"Saida: {res.stdout[:200]}...", "INFO")
            return True

        exit_code = res.returncode if res else "None"
        _log(f"Windows Update retornou codigo {exit_code}", "AVISO")

        if res and res.stderr:
            _log(f"Erros: {res.stderr[:200]}...", "AVISO")

        return True
    except Exception as e:
        _log(f"Erro na rotina de Windows Update: {e}", "ERRO")
        return False