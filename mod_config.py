# -*- coding: ascii -*-
"""mod_config.py - V6.0.1 (Edicao CP Fani: PrintScreenKeyForSnippingEnabled adicionado)"""
import winreg
import subprocess
import os
import ctypes
import time
import platform
import urllib.request
import shutil
import sys
import re
import traceback
import hashlib
import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = os.environ.get("SCRIPT_DIR", r"C:\Scripts")

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


def _safe_subprocess_run(cmd, timeout=30, shell=False, capture_output=True, **kwargs):
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
        _log(f"Timeout ({timeout}s) ao executar: {cmd_str}", "AVISO")
        return None
    except Exception as e:
        _log(f"Erro ao executar subprocesso: {e}", "ERRO")
        return None


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


def _write_hash_sidecar(file_path, expected_hash=None):
    file_hash = expected_hash if expected_hash else _get_file_sha256(file_path)
    if not file_hash:
        return None

    sidecar = file_path + ".sha256"
    try:
        with open(sidecar, "w", encoding="ascii", errors="replace") as f:
            f.write(file_hash.strip().upper() + "\n")
        return file_hash.strip().upper()
    except Exception as e:
        _log(f"Erro ao escrever sidecar de hash {sidecar}: {e}", "ERRO")
        return None


def _get_expected_wallpaper_sha256():
    env_hash = os.environ.get("CPFANI_WALLPAPER_SHA256", "").strip().upper()
    if env_hash:
        return env_hash

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sidecar = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg.sha256")
    if os.path.exists(sidecar):
        try:
            with open(sidecar, "r", encoding="ascii", errors="ignore") as f:
                content = f.read().strip().split()[0].upper()
                return content
        except Exception as e:
            _log(f"Erro ao ler sidecar de hash do wallpaper: {e}", "AVISO")

    return ""


def _get_all_user_sids():
    """Obtem todos os SIDs de usuarios reais do sistema (exclui SIDs do sistema)"""
    sids = []
    try:
        profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profiles_key) as root_key:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(root_key, i)
                    i += 1
                    if sid.startswith("S-1-5-21-"):
                        sids.append(sid)
                except OSError:
                    break
    except Exception as e:
        _log(f"Erro ao obter SIDs: {e}", "AVISO")
    return sids


def _get_active_user_sid():
    """Obtem o SID do usuario ativo via PowerShell"""
    ps_script = r'''
$explorer = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1
if ($explorer) {
    $ownerInfo = Invoke-CimMethod -InputObject $explorer -MethodName GetOwner
    $user = $ownerInfo.Domain + "\" + $ownerInfo.User
    $ntAccount = New-Object System.Security.Principal.NTAccount($user)
    $sid = $ntAccount.Translate([System.Security.Principal.SecurityIdentifier]).Value
    Write-Output $sid
}
'''
    try:
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=15
        )
        if result and result.stdout:
            sid = result.stdout.strip()
            return sid if sid.startswith("S-1-5-") else None
        return None
    except Exception as e:
        _log(f"Erro ao obter SID do usuario ativo: {e}", "AVISO")
        return None


def _get_target_sids(prefer_active=True):
    sids = []
    if prefer_active:
        active = _get_active_user_sid()
        if active:
            sids.append(active)

    if not sids:
        sids = _get_all_user_sids()
        if sids:
            _log("SID ativo nao encontrado. Aplicando fallback para todos os SIDs reais.", "INFO")

    unique = []
    seen = set()
    for sid in sids:
        if sid and sid not in seen:
            seen.add(sid)
            unique.append(sid)
    return unique


def _apply_to_all_real_users():
    """Varre todos os perfis de usuarios para desativar o atalho nativo do PrtSc"""
    _log("Varrendo todos os perfis de usuarios para desativar o atalho nativo do PrtSc...", "INFO")

    printscreen_values = (
        "PrintScreenKeyForSnippingToolEnabled",
        "PrintScreenKeyForSnippingEnabled"
    )

    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", 0, winreg.KEY_SET_VALUE) as hkcu_key:
            for value_name in printscreen_values:
                winreg.SetValueEx(hkcu_key, value_name, 0, winreg.REG_DWORD, 0)
        _log("[OK] Chaves PrintScreen desativadas com sucesso no HKCU do usuario corrente.", "OK")
    except Exception as e:
        _log(f"Aviso ao setar HKCU direto: {e}", "AVISO")

    try:
        profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profiles_key) as root_key:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(root_key, i)
                    i += 1
                    if not sid.startswith("S-1-5-21-"):
                        continue

                    try:
                        _log(f"Processando SID: {sid}", "INFO")

                        for value_name in printscreen_values:
                            cmd_keyboard = [
                                "reg", "add",
                                f"HKU\\{sid}\\Control Panel\\Keyboard",
                                "/v", value_name,
                                "/t", "REG_DWORD",
                                "/d", "0",
                                "/f"
                            ]
                            _safe_subprocess_run(cmd_keyboard, timeout=10)

                        cmd_sync = [
                            "reg", "add",
                            f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility",
                            "/v", "Enabled",
                            "/t", "REG_DWORD",
                            "/d", "0",
                            "/f"
                        ]
                        _safe_subprocess_run(cmd_sync, timeout=10)

                        cmd_dropbox = [
                            "reg", "add",
                            f"HKU\\{sid}\\Software\\Dropbox\\Client",
                            "/v", "CapturePrintScreen",
                            "/t", "REG_DWORD",
                            "/d", "0",
                            "/f"
                        ]
                        _safe_subprocess_run(cmd_dropbox, timeout=10)

                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{profiles_key}\\{sid}") as p_key:
                                profile_path, _ = winreg.QueryValueEx(p_key, "ProfileImagePath")
                                profile_path = os.path.expandvars(profile_path)
                                if profile_path and "System32" not in profile_path:
                                    fs_dir = os.path.join(profile_path, "AppData", "Roaming", "flameshot")
                                    os.makedirs(fs_dir, exist_ok=True)
                                    fs_ini = os.path.join(fs_dir, "flameshot.ini")
                                    shortcut_block = "[Shortcuts]\ntakeScreenshot=Print\n"

                                    if os.path.exists(fs_ini):
                                        try:
                                            with open(fs_ini, "r", encoding="utf-8", errors="replace") as f:
                                                content = f.read()
                                        except Exception as e:
                                            _log(f"Erro ao ler {fs_ini}: {e}", "AVISO")
                                            content = ""
                                    else:
                                        content = ""

                                    content = re.sub(r"UsePrintScreen=.*?\n", "", content, flags=re.IGNORECASE)
                                    if "[Shortcuts]" in content:
                                        content = re.sub(r"takeScreenshot=.*", "takeScreenshot=Print", content)
                                    else:
                                        content += f"\n{shortcut_block}"

                                    try:
                                        with open(fs_ini, "w", encoding="utf-8", errors="replace") as f:
                                            f.write(content)
                                        _log(f"[OK] Configuracao do Flameshot aplicada para SID {sid}", "OK")
                                    except Exception as e:
                                        _log(f"Erro ao escrever {fs_ini}: {e}", "ERRO")
                        except Exception as e:
                            _log(f"Erro ao processar perfil do SID {sid}: {e}", "AVISO")
                    except Exception as e:
                        _log(f"Aviso ao processar SID {sid}: {e}", "AVISO")
                except OSError:
                    break
    except Exception as e:
        _log(f"Falha na varredura global de SIDs: {e}", "AVISO")


def setup_self_healing():
    """Instala o sistema de auto-cura (watchdog)"""
    _log("=" * 60, "INFO")
    _log("INSTALANDO CAO DE GUARDA (SELF-HEALING)...", "INFO")

    script_dir = SCRIPT_DIR
    os.makedirs(script_dir, exist_ok=True)

    ps_path = os.path.join(script_dir, "cpfani_watchdog.ps1")
    vbs_path = os.path.join(script_dir, "cpfani_watchdog_launcher.vbs")

    ps_content = r'''$officialWp = "C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
while ($true) {
    try {
        $explorers = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'"
        if ($explorers) {
            foreach ($exp in $explorers) {
                $ownerInfo = Invoke-CimMethod -InputObject $exp -MethodName GetOwner
                if ($ownerInfo.User) {
                    $user = $ownerInfo.Domain + "\" + $ownerInfo.User
                    $sid = (New-Object System.Security.Principal.NTAccount($user)).Translate([System.Security.Principal.SecurityIdentifier]).Value
                    $regPath = "Registry::HKEY_USERS\$sid\Control Panel\Desktop"
                    if (Test-Path $regPath) {
                        $currentWp = (Get-ItemProperty -Path $regPath -Name Wallpaper -ErrorAction SilentlyContinue).Wallpaper
                        if ($currentWp -ne $officialWp -and (Test-Path $officialWp)) {
                            Set-ItemProperty -Path $regPath -Name Wallpaper -Value $officialWp
                        }
                    }
                }
            }
        }

        $ad = Get-Service -Name "AnyDesk" -ErrorAction SilentlyContinue
        if ($ad -and $ad.Status -ne 'Running') {
            Start-Service -Name "AnyDesk" -ErrorAction SilentlyContinue
        }
    } catch {}

    Start-Sleep -Seconds 10
}
'''

    try:
        with open(ps_path, "w", encoding="ascii", errors="replace") as f:
            f.write(ps_content)
        _log(f"[OK] Script PowerShell criado: {ps_path}", "OK")
    except Exception as e:
        _log(f"Erro ao criar script PowerShell: {e}", "ERRO")
        return False

    ps_hash = _write_hash_sidecar(ps_path)
    if not ps_hash:
        _log("Erro ao criar hash sidecar do script PowerShell.", "ERRO")
        return False

    if not _verify_sha256(ps_path, ps_hash):
        _log("Integridade do script PowerShell invalida antes do agendamento.", "ERRO")
        return False

    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps_path}""", 0, False'

    try:
        with open(vbs_path, "w", encoding="ascii", errors="replace") as f:
            f.write(vbs_content)
        _log(f"[OK] Script VBS criado: {vbs_path}", "OK")
    except Exception as e:
        _log(f"Erro ao criar script VBS: {e}", "ERRO")
        return False

    vbs_hash = _write_hash_sidecar(vbs_path)
    if not vbs_hash:
        _log("Erro ao criar hash sidecar do script VBS.", "ERRO")
        return False

    if not _verify_sha256(vbs_path, vbs_hash):
        _log("Integridade do script VBS invalida antes do agendamento.", "ERRO")
        return False

    task_args = [
        "schtasks", "/create",
        "/tn", "CPFANI_Watchdog",
        "/tr", f'wscript.exe "{vbs_path}"',
        "/sc", "onlogon",
        "/ru", "SYSTEM",
        "/rl", "highest",
        "/f"
    ]
    result = _safe_subprocess_run(task_args, shell=False, timeout=30)
    if result and result.returncode == 0:
        _log("[OK] Tarefa agendada criada com sucesso", "OK")
    else:
        _log("Aviso ao criar tarefa agendada", "AVISO")

    check_ps = "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | Where-Object { $_.CommandLine -like '*cpfani_watchdog.ps1*' } | Measure-Object | Select-Object -ExpandProperty Count"
    check_result = _safe_subprocess_run(["powershell", "-NoProfile", "-Command", check_ps], shell=False, timeout=15)

    already_running = False
    try:
        if check_result and check_result.stdout and int(check_result.stdout.strip()) > 0:
            already_running = True
    except Exception:
        already_running = False

    if already_running:
        _log("Watchdog ja esta em execucao - nao sera iniciada uma segunda instancia.", "INFO")
    else:
        if not _verify_sha256(ps_path, ps_hash) or not _verify_sha256(vbs_path, vbs_hash):
            _log("Integridade invalida antes de iniciar o watchdog.", "ERRO")
            return False

        try:
            subprocess.Popen(f'wscript.exe "{vbs_path}"', shell=True, creationflags=CREATION_FLAGS_NO_WINDOW)
            _log("[OK] Self-Healing (Watchdog) iniciado", "OK")
        except Exception as e:
            _log(f"Erro ao iniciar watchdog: {e}", "ERRO")

    _log("[OK] Self-Healing (Watchdog) ativo e agendado.", "OK")
    return True


def set_reg(root, path, name, value, rtype=winreg.REG_SZ):
    """Define valor de registro com tratamento de erros"""
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE)
        winreg.SetValueEx(key, name, 0, rtype, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        _log(f"Erro ao definir registro {path}\\{name}: {e}", "AVISO")
        return False


def sync_time_ntp():
    """Sincroniza horario com servidores NTP.br"""
    _log("Sincronizando horario com NTP.br...", "INFO")
    try:
        cmds = [
            'w32tm /config /manualpeerlist:"a.ntp.br b.ntp.br c.ntp.br" /syncfromflags:manual /reliable:YES /update',
            'net stop w32time',
            'net start w32time',
            'w32tm /resync /force'
        ]
        for cmd in cmds:
            result = _safe_subprocess_run(cmd, shell=True, timeout=30)
            if result and result.returncode == 0:
                _log(f"[OK] Comando executado: {cmd[:50]}...", "OK")
            else:
                _log(f"Aviso no comando: {cmd[:50]}...", "AVISO")
        _log("[OK] Horario sincronizado com ntp.br.", "OK")
    except Exception as e:
        _log(f"Erro ao sincronizar horario: {e}", "ERRO")


def schedule_daily_reboot():
    """Agenda reinicio diario automatico as 21:00"""
    _log("Agendando reinicio diario automatico...", "INFO")
    try:
        shutdown_cmd = 'shutdown.exe /r /f /t 60 /c "Reinicio diario automatico CP Fani"'
        task_args = [
            "schtasks", "/create",
            "/tn", "CPFANI_ReinicioDiario",
            "/tr", shutdown_cmd,
            "/sc", "daily",
            "/st", "21:00",
            "/ru", "SYSTEM",
            "/rl", "highest",
            "/f"
        ]
        result = _safe_subprocess_run(task_args, shell=False, timeout=30)
        if result and result.returncode == 0:
            _log("[OK] Reinicio diario agendado para 21:00", "OK")
        else:
            _log("Aviso ao agendar reinicio diario", "AVISO")
    except Exception as e:
        _log(f"Erro ao agendar reinicio: {e}", "ERRO")


def set_apps_to_startup_all_users():
    """Configura aplicativos para iniciar no login de todos os usuarios"""
    _log("Configurando apps para abrir no login de TODOS os utilizadores (HKLM)...", "INFO")
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    os.makedirs(startup_path, exist_ok=True)

    _log("Nivel 11: Sanando cache do Explorer e aplicando bloqueio do painel...", "INFO")
    try:
        processes_to_kill = ["SnippingTool.exe", "ScreenClippingHost.exe", "flameshot.exe", "sharex.exe"]
        for proc in processes_to_kill:
            _safe_subprocess_run(["taskkill", "/f", "/im", proc], timeout=10)

        _safe_subprocess_run(["taskkill", "/f", "/im", "explorer.exe"], timeout=10)
        time.sleep(1.5)

        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\TabletPC", "DisableSnippingTool", 1, winreg.REG_DWORD)
        _log("[OK] SnippingTool desativado via GPO", "OK")

        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0, winreg.REG_DWORD)

        target_sids = _get_target_sids()
        if target_sids:
            for sid in target_sids:
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR", "/v", "AppCaptureEnabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\System\\GameConfigStore", "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
            _log("[OK] Xbox Game Bar desativada", "OK")
        else:
            _log("Nenhum SID disponivel para desativar Xbox Game Bar.", "AVISO")

        ifeo = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo}\\SnippingTool.exe", "Debugger", "rundll32.exe")
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo}\\ScreenClippingHost.exe", "Debugger", "rundll32.exe")
        _log("[OK] Debugger redirect aplicado", "OK")

        _apply_to_all_real_users()

        try:
            subprocess.Popen(["explorer.exe"], creationflags=CREATION_FLAGS_NO_WINDOW)
            _log("[OK] Interface do Windows Explorer reativada com sucesso.", "OK")
        except Exception as e:
            _log(f"Erro ao reiniciar explorer: {e}", "ERRO")
    except Exception as e:
        _log(f"Aviso no Mapeamento Geral Nivel 11: {e}", "AVISO")

    apps = {
        "flameshot.lnk": [r"C:\Program Files\Flameshot\bin\flameshot.exe", r"C:\Program Files\Flameshot\flameshot.exe"],
        "sharex.lnk": [r"C:\Program Files\ShareX\ShareX.exe", r"C:\Program Files (x86)\ShareX\ShareX.exe"],
        "anydesk.lnk": [r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe", r"C:\Program Files\AnyDesk\AnyDesk.exe"],
        "teamviewer.lnk": [r"C:\Program Files\TeamViewer\TeamViewer.exe", r"C:\Program Files (x86)\TeamViewer\TeamViewer.exe"]
    }

    for link, paths in apps.items():
        exe_found = None
        for p in paths:
            if os.path.exists(p):
                exe_found = p
                break

        if exe_found:
            target = os.path.join(startup_path, link)
            ps_cmd = f'$s=(New-Object -COM WScript.Shell).CreateShortcut(\'{target}\');$s.TargetPath=\'{exe_found}\';$s.Save()'
            result = _safe_subprocess_run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                timeout=15
            )
            if result and result.returncode == 0:
                _log(f"[OK] Atalho criado: {link}", "OK")
            else:
                _log(f"Aviso ao criar atalho: {link}", "AVISO")


def apply_default_user_profile(bar_alignment):
    """Aplica configuracoes ao perfil padrao de usuario"""
    _log("Aplicando configuracoes ao perfil padrao...", "INFO")

    hive_path = r"HKU\TempDefaultUser"
    default_dat = r"C:\Users\Default\NTUSER.DAT"

    printscreen_values = (
        "PrintScreenKeyForSnippingToolEnabled",
        "PrintScreenKeyForSnippingEnabled"
    )

    try:
        _safe_subprocess_run(["reg", "unload", hive_path], timeout=30)
        time.sleep(1)

        result = _safe_subprocess_run(["reg", "load", hive_path, default_dat], timeout=30)
        if not result or result.returncode != 0:
            _log("Erro ao carregar NTUSER.DAT", "ERRO")
            _safe_subprocess_run(["reg", "unload", hive_path], timeout=30)
            return

        try:
            _safe_subprocess_run(
                ["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _safe_subprocess_run(
                ["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )

            if bar_alignment != "nenhum":
                val = "0" if bar_alignment == "left" else "1"
                _safe_subprocess_run(
                    ["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", val, "/f"],
                    timeout=10
                )

            for value_name in printscreen_values:
                _safe_subprocess_run(
                    ["reg", "add", r"HKU\TempDefaultUser\Control Panel\Keyboard", "/v", value_name, "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
        finally:
            _safe_subprocess_run(["reg", "unload", hive_path], timeout=30)

        _log("[OK] Configuracoes aplicadas ao perfil padrao", "OK")
    except Exception as e:
        _log(f"Erro ao aplicar perfil padrao: {e}", "ERRO")
        _safe_subprocess_run(["reg", "unload", hive_path], timeout=30)


def remove_agressive_bloatware(bloatware_list):
    """Remove bloatware do sistema"""
    _log(f"Removendo {len(bloatware_list)} aplicativos bloatware...", "INFO")

    for app in bloatware_list:
        try:
            cmd_user = f"Get-AppxPackage -AllUsers {app} | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"
            cmd_prov = f"Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue"
            result = _safe_subprocess_run(
                ["powershell", "-NoProfile", "-Command", f"{cmd_user}; {cmd_prov}"],
                timeout=60
            )
            if result and result.returncode == 0:
                _log(f"[OK] Bloatware removido: {app}", "OK")
            else:
                _log(f"Aviso ao remover {app}", "AVISO")
        except Exception as e:
            _log(f"Erro ao remover {app}: {e}", "ERRO")

    return True


def apply_cpfani_branding(bar_alignment):
    """Aplica branding corporativo CP Fani com redundancia para todos os usuarios"""
    _log("INICIANDO BRANDING CORPORATIVO...", "INFO")

    sync_time_ntp()

    path_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"

    try:
        target_sids = _get_target_sids()
        if target_sids:
            for sid in target_sids:
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
            _log("[OK] Tema escuro aplicado para usuario(s) alvo", "OK")
        else:
            _log("Nenhum SID disponivel para aplicar tema.", "AVISO")
    except Exception as e:
        _log(f"Erro ao aplicar tema: {e}", "AVISO")

    apply_cpfani_wallpaper_redundant()
    apply_cpfani_lockscreen_redundant()

    if bar_alignment != "nenhum":
        val = 0 if bar_alignment == "left" else 1
        try:
            target_sids = _get_target_sids()
            if target_sids:
                for sid in target_sids:
                    reg_path = f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced"
                    _safe_subprocess_run(
                        ["reg", "add", reg_path, "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", str(val), "/f"],
                        timeout=10
                    )
                _log(f"[OK] Barra de tarefas alinhada: {bar_alignment}", "OK")
        except Exception as e:
            _log(f"Erro ao alinhar barra: {e}", "AVISO")

    apply_default_user_profile(bar_alignment)

    _log("Aplicando configuracoes de tema escuro, wallpaper e lockscreen para TODOS os usuarios (redundancia)...", "INFO")
    _apply_dark_theme_to_all_users()
    _apply_wallpaper_to_all_users()
    _apply_lockscreen_to_all_users()


def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    """Aplica politicas de Seguranca e LGPD"""
    _log("Aplicando politicas de Seguranca e LGPD...", "INFO")

    target_sids = _get_target_sids()

    if apply_lgpd:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD)
        _log("[OK] Telemetria desativada", "OK")

        if target_sids:
            for sid in target_sids:
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager", "/v", "SubscribedContent-338389Enabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )

        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin", "autoWorkplaceJoin", 0, winreg.REG_DWORD)
        _log("[OK] Workplace Join desativado", "OK")

    if disable_hello:
        disable_windows_hello_redundant()
        remove_widgets_taskbar()


def _get_image_path(local_path, urls, temp_name, expected_sha256=None):
    """Obtem caminho de imagem com validacao de tamanho e hash"""
    if os.path.exists(local_path):
        _log(f"Imagem local encontrada: {local_path}", "OK")
        if expected_sha256:
            if _verify_sha256(local_path, expected_sha256):
                return local_path
            _log("Imagem local com hash invalido. Tentando download.", "AVISO")
        else:
            return local_path

    if not expected_sha256:
        _log("Hash SHA256 esperado nao configurado para imagem. Use CPFANI_WALLPAPER_SHA256 ou resources/wallpaper_cpfani.jpg.sha256.", "ERRO")
        return None

    _log(f"Baixando imagem: {temp_name}", "INFO")

    for url in urls:
        try:
            public_temp = r"C:\Users\Public\Downloads"
            os.makedirs(public_temp, exist_ok=True)
            temp_path = os.path.join(public_temp, temp_name)

            urllib.request.urlretrieve(url, temp_path)

            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 10000:
                if _verify_sha256(temp_path, expected_sha256):
                    _log(f"[OK] Imagem baixada com sucesso: {os.path.getsize(temp_path)} bytes", "OK")
                    return temp_path

                _log("Hash SHA256 invalido apos download.", "ERRO")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            else:
                _log("Arquivo muito pequeno, tentando proximo URL...", "AVISO")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            _log(f"Erro ao baixar de {url}: {e}", "AVISO")

    _log("Falha ao obter imagem de todos os URLs", "ERRO")
    return None


def apply_cpfani_wallpaper_redundant():
    """Aplica wallpaper CP Fani e copia para diretorio de wallpapers do Windows"""
    _log("Aplicando wallpaper CP Fani...", "INFO")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]

    expected_hash = _get_expected_wallpaper_sha256()
    target_path = _get_image_path(local_wp, urls, "cpfani_wp.png", expected_hash)

    if not target_path:
        _log("Falha ao obter wallpaper", "ERRO")
        return False

    try:
        windows_wp_dir = r"C:\Windows\Web\Wallpaper\Windows"
        os.makedirs(windows_wp_dir, exist_ok=True)
        windows_wp_path = os.path.join(windows_wp_dir, "cpfani_wallpaper.jpg")
        shutil.copy2(target_path, windows_wp_path)
        _log(f"[OK] Wallpaper copiado para {windows_wp_path}", "OK")
    except Exception as e:
        _log(f"Erro ao copiar wallpaper para Windows: {e}", "AVISO")

    try:
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, target_path, 3)
        if result:
            _log("[OK] Wallpaper aplicado com sucesso via API", "OK")
            return True

        _log("Falha ao aplicar wallpaper via API", "ERRO")
        return False
    except Exception as e:
        _log(f"Erro ao aplicar wallpaper: {e}", "ERRO")
        return False


def apply_cpfani_lockscreen_redundant():
    """Aplica lockscreen CP Fani e forca a imagem via GPO + PersonalizationCSP"""
    _log("Aplicando lockscreen CP Fani...", "INFO")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]

    expected_hash = _get_expected_wallpaper_sha256()
    target_path = _get_image_path(local_wp, urls, "cpfani_ls.png", expected_hash)

    if not target_path:
        _log("Falha ao obter lockscreen", "ERRO")
        return False

    windows_wp_dir = r"C:\Windows\Web\Wallpaper\Windows"
    windows_wp_path = os.path.join(windows_wp_dir, "cpfani_wallpaper.jpg")

    try:
        os.makedirs(windows_wp_dir, exist_ok=True)
        if not os.path.exists(windows_wp_path):
            shutil.copy2(target_path, windows_wp_path)
            _log(f"[OK] Wallpaper copiado para {windows_wp_path} (lockscreen)", "OK")
    except Exception as e:
        _log(f"Erro ao copiar wallpaper para Windows (lockscreen): {e}", "AVISO")

    if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", windows_wp_path, winreg.REG_SZ):
        _log("[OK] Lockscreen configurado via GPO (HKLM)", "OK")
    else:
        _log("Falha ao configurar lockscreen via GPO", "AVISO")

    try:
        csp_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP"

        if set_reg(winreg.HKEY_LOCAL_MACHINE, csp_path, "LockScreenImageStatus", 1, winreg.REG_DWORD):
            _log("[OK] LockScreenImageStatus configurado via PersonalizationCSP", "OK")
        else:
            _log("Falha ao configurar LockScreenImageStatus via PersonalizationCSP", "AVISO")

        if set_reg(winreg.HKEY_LOCAL_MACHINE, csp_path, "LockScreenImagePath", windows_wp_path, winreg.REG_SZ):
            _log("[OK] LockScreenImagePath configurado via PersonalizationCSP", "OK")
        else:
            _log("Falha ao configurar LockScreenImagePath via PersonalizationCSP", "AVISO")

        if set_reg(winreg.HKEY_LOCAL_MACHINE, csp_path, "LockScreenImageUrl", windows_wp_path, winreg.REG_SZ):
            _log("[OK] LockScreenImageUrl configurado via PersonalizationCSP", "OK")
        else:
            _log("Falha ao configurar LockScreenImageUrl via PersonalizationCSP", "AVISO")
    except Exception as e:
        _log(f"Erro ao configurar PersonalizationCSP: {e}", "AVISO")

    if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "NoChangingLockScreen", 1, winreg.REG_DWORD):
        _log("[OK] Bloqueio de alteracao da tela de bloqueio ativado", "OK")
    else:
        _log("Falha ao ativar bloqueio de alteracao da tela de bloqueio", "AVISO")

    return True


def disable_windows_hello_redundant():
    """Desativa Windows Hello e biometria"""
    _log("Desativando Windows Hello e biometria...", "INFO")
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "Biometric", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WbioSrvc", "Start", 4, winreg.REG_DWORD)
        _log("[OK] Windows Hello desativado", "OK")
    except Exception as e:
        _log(f"Erro ao desativar Windows Hello: {e}", "ERRO")


def remove_widgets_taskbar():
    """Remove widgets da barra de tarefas"""
    _log("Removendo widgets da barra de tarefas...", "INFO")
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD)

        target_sids = _get_target_sids()
        if target_sids:
            for sid in target_sids:
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\FileExplorer", "/v", "TaskbarDa", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
            _log("[OK] Widgets removidos", "OK")
        else:
            _log("Nenhum SID disponivel para remover widgets.", "AVISO")
    except Exception as e:
        _log(f"Erro ao remover widgets: {e}", "ERRO")


def apply_firewall_rules():
    """Aplica regras de firewall para compartilhamento"""
    _log("Aplicando regras de firewall...", "INFO")
    try:
        result = _safe_subprocess_run(
            'netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes profile=private,domain',
            shell=True,
            timeout=30
        )
        if result and result.returncode == 0:
            _log("[OK] Regras de firewall aplicadas", "OK")
        else:
            _log("Aviso ao aplicar regras de firewall", "AVISO")
    except Exception as e:
        _log(f"Erro ao aplicar firewall: {e}", "ERRO")


def configurar_compartilhamento_rede():
    """
    Configura o Windows para permitir compartilhamento transparente de arquivos e impressoras,
    eliminando a solicitacao de credenciais de rede e ativando a descoberta.
    """
    _log("DESBLOQUEANDO COMPARTILHAMENTO E DESCOBERTA DE REDE...", "INFO")

    try:
        ps_cmd = "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private"
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            timeout=30
        )
        if result and result.returncode == 0:
            _log("[OK] Perfil de todas as interfaces de rede alterado para Privado.", "OK")
        else:
            _log("Aviso ao alterar perfil de rede", "AVISO")
    except Exception as e:
        _log(f"Erro ao alterar perfil de rede: {e}", "AVISO")

    servicos = [
        ("FdResPub", "Publicacao de Recursos de Descoberta"),
        ("SSDPDiscovery", "Descoberta SSDP"),
        ("upnphost", "Hospedador de Dispositivo UPnP")
    ]

    for svc_name, svc_desc in servicos:
        try:
            _safe_subprocess_run(["sc", "config", svc_name, "start=", "auto"], timeout=15)
            result = _safe_subprocess_run(["sc", "start", svc_name], timeout=15)
            if result and result.returncode == 0:
                _log(f"[OK] Servico '{svc_desc}' ativado e iniciado.", "OK")
            else:
                _log(f"Aviso no servico {svc_name}", "AVISO")
        except Exception as e:
            _log(f"Aviso no servico {svc_name}: {e}", "AVISO")

    reg_configs = [
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "AllowInsecureGuestAuth", 1),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", "RestrictNullSvcSession", 0),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Lsa", "everyoneincludesanonymous", 1),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Lsa", "LimitBlankPasswordUse", 0)
    ]

    for root, path, name, val in reg_configs:
        if set_reg(root, path, name, val, winreg.REG_DWORD):
            _log(f"[OK] Registro configurado: {name} = {val}", "OK")
        else:
            _log(f"Falha ao configurar registro: {name}", "AVISO")

    try:
        result = _safe_subprocess_run(
            'netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes profile=private,domain',
            shell=True,
            timeout=30
        )
        if result and result.returncode == 0:
            _log("[OK] Regras de Firewall para compartilhamento liberadas com sucesso.", "OK")
        else:
            _log("Aviso ao liberar Firewall", "AVISO")
    except Exception as e:
        _log(f"Aviso ao liberar Firewall: {e}", "AVISO")


def schedule_manutencao_rede():
    """Agenda a execucao diaria do manutencao_rede.bat de forma oculta."""
    _log("Agendando manutencao de rede (execucao oculta)...", "INFO")

    script_dir = SCRIPT_DIR
    bat_path = os.path.join(script_dir, "manutencao_rede.bat")
    vbs_path = os.path.join(script_dir, "cpfani_manutencao_rede_launcher.vbs")

    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run """{bat_path}""", 0, False'

    try:
        with open(vbs_path, "w", encoding="ascii", errors="replace") as f:
            f.write(vbs_content)
    except Exception as e:
        _log(f"Erro ao criar VBS de manutencao de rede: {e}", "ERRO")
        return False

    task_args = [
        "schtasks", "/create",
        "/tn", "CPFANI_ManutencaoRede",
        "/tr", f'wscript.exe "{vbs_path}"',
        "/sc", "daily",
        "/st", "08:00",
        "/ru", "SYSTEM",
        "/rl", "highest",
        "/f"
    ]

    result = _safe_subprocess_run(task_args, shell=False, timeout=30)
    if result and result.returncode == 0:
        _log("[OK] Tarefa de manutencao de rede criada/atualizada com sucesso (execucao oculta).", "OK")
        return True

    _log("Aviso ao criar tarefa de manutencao de rede", "AVISO")
    return False


def schedule_instalar_tudo():
    """Agenda a execucao do instalar_tudo.ps1 de forma oculta."""
    _log("Agendando atualizador de software (execucao oculta)...", "INFO")

    script_dir = SCRIPT_DIR
    ps1_path = os.path.join(script_dir, "instalar_tudo.ps1")
    vbs_path = os.path.join(script_dir, "cpfani_instalar_tudo_launcher.vbs")

    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps1_path}""", 0, False'

    try:
        with open(vbs_path, "w", encoding="ascii", errors="replace") as f:
            f.write(vbs_content)
    except Exception as e:
        _log(f"Erro ao criar VBS do instalador universal: {e}", "ERRO")
        return False

    task_args = [
        "schtasks", "/create",
        "/tn", "CPFANI_InstalarTudo",
        "/tr", f'wscript.exe "{vbs_path}"',
        "/sc", "onlogon",
        "/ru", "SYSTEM",
        "/rl", "highest",
        "/f"
    ]

    result = _safe_subprocess_run(task_args, shell=False, timeout=30)
    if result and result.returncode == 0:
        _log("[OK] Tarefa do instalador universal criada/atualizada com sucesso (execucao oculta).", "OK")
        return True

    _log("Aviso ao criar tarefa do instalador universal", "AVISO")
    return False


def check_and_remove_legacy_apps(app_names):
    """
    Verifica se algum dos nomes em app_names esta instalado, consultando as chaves de desinstalacao do Registro,
    e remove silenciosamente cada instalacao encontrada.
    Retorna um dict {nome_procurado: bool_removido_com_sucesso}.
    """
    _log(f"Verificando aplicativos legados para remocao: {app_names}", "INFO")

    resultado = {app: False for app in app_names}

    uninstall_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for root, base_path in uninstall_roots:
        try:
            with winreg.OpenKey(root, base_path) as base_key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(base_key, i)
                        i += 1

                        try:
                            with winreg.OpenKey(base_key, subkey_name) as subkey:
                                try:
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                except FileNotFoundError:
                                    continue

                                for app in app_names:
                                    if app.lower() in display_name.lower() and not resultado[app]:
                                        try:
                                            uninstall_string, _ = winreg.QueryValueEx(subkey, "UninstallString")
                                        except FileNotFoundError:
                                            continue

                                        if not uninstall_string:
                                            continue

                                        _log(f"Encontrado: {display_name}. Executando desinstalacao silenciosa...", "INFO")

                                        silent_cmd = uninstall_string
                                        if "msiexec" in uninstall_string.lower():
                                            silent_cmd = uninstall_string.replace("/I", "/X").replace("/i", "/x") + " /qn /norestart"
                                        else:
                                            silent_cmd = f'{uninstall_string} /S'

                                        unres = _safe_subprocess_run(silent_cmd, shell=True, timeout=120)
                                        if unres and unres.returncode in (0, 3010):
                                            _log(f"[OK] {display_name} removido com sucesso.", "OK")
                                            resultado[app] = True
                                        else:
                                            _log(f"Aviso: desinstalacao de {display_name} retornou codigo {unres.returncode if unres else 'None'}", "AVISO")
                        except Exception:
                            continue
                    except OSError:
                        break
        except Exception as e:
            _log(f"Erro ao varrer {base_path}: {e}", "AVISO")

    for app, removido in resultado.items():
        if not removido:
            _log(f"{app} nao encontrado no sistema (ou ja removido anteriormente).", "INFO")

    return resultado


def _get_hardware_info():
    """Obtem informacoes basicas de hardware (legado)"""
    return {
        "Nome_Computador": os.environ.get("COMPUTERNAME", platform.node()),
        "Sistema_Operacional": platform.system(),
        "Versao_SO": platform.version(),
        "Arquitetura": platform.machine(),
        "Processador": platform.processor()
    }


def _get_system_model():
    """Obtem o modelo do sistema via WMI"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_ComputerSystem).Model'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    return "Desconhecido"


def _get_processor_name():
    """Obtem o nome do processador via WMI"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_Processor).Name'],
            timeout=10
        )
        if result and result.stdout:
            return ' '.join(result.stdout.strip().split())
    except Exception:
        pass
    return "Desconhecido"


def _get_total_ram():
    """Obtem a memoria RAM total em GB"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', '[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip() + " GB"
    except Exception:
        pass
    return "Desconhecido"


def _get_windows_version():
    """Obtem a versao e edicao do Windows"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_OperatingSystem).Caption'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    return platform.system() + " " + platform.release()


def _get_bios_serial():
    """Obtem o numero de serie da BIOS"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', '(Get-CimInstance Win32_BIOS).SerialNumber'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    return "Desconhecido"


def _get_monitor_info():
    """
    Obtem informacoes de todos os monitores conectados via WMI (WmiMonitorID).
    Retorna uma lista de dicionarios com 'Modelo' e 'Numero_de_Serie' de cada monitor.
    Suporta multiplos monitores por PC.
    """
    monitors = []

    try:
        ps_script = r'''
Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID | ForEach-Object {
    [PSCustomObject]@{
        Modelo = [System.Text.Encoding]::ASCII.GetString([byte[]]($_.UserFriendlyName | Where-Object { $_ -ne 0 }))
        Numero_de_Serie = [System.Text.Encoding]::ASCII.GetString([byte[]]($_.SerialNumberID | Where-Object { $_ -ne 0 }))
    }
} | ConvertTo-Json
'''
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            timeout=15
        )

        if result and result.stdout and result.stdout.strip():
            data = json.loads(result.stdout)
            if data is None:
                data = []
            if isinstance(data, dict):
                data = [data]

            for item in data:
                modelo = str(item.get('Modelo', '')).strip()
                serial = str(item.get('Numero_de_Serie', '')).strip()

                if modelo or serial:
                    monitors.append({
                        'Modelo': modelo if modelo else 'Desconhecido',
                        'Numero_de_Serie': serial if serial else 'N/A'
                    })
    except Exception as e:
        _log(f"Erro ao obter informacoes dos monitores: {e}", "AVISO")

    if not monitors:
        _log("Nenhum monitor detectado ou erro na consulta WMI.", "AVISO")

    return monitors


def _get_printer_info():
    """
    Obtem informacoes de todas as impressoras instaladas no sistema.
    Para impressoras de rede (com IP), tenta consultar via SNMP para obter modelo e serial reais.
    Retorna uma lista de dicionarios com dados de cada impressora.
    """
    printers = []

    try:
        ps_script = """
        Get-Printer | Select-Object Name, PrinterStatus, PortName, DriverName, Shared | ConvertTo-Json
        """
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            timeout=20
        )

        if result and result.stdout and result.stdout.strip():
            printers_data = json.loads(result.stdout)
            if printers_data is None:
                printers_data = []
            if isinstance(printers_data, dict):
                printers_data = [printers_data]

            for printer in printers_data:
                printer_info = {
                    'Nome': printer.get('Name', 'N/A'),
                    'Status': printer.get('PrinterStatus', 'N/A'),
                    'Porta': printer.get('PortName', 'N/A'),
                    'Driver': printer.get('DriverName', 'N/A'),
                    'Compartilhada': 'Sim' if printer.get('Shared') else 'Nao',
                    'Modelo_SNMP': 'N/A',
                    'Serial_SNMP': 'N/A',
                    'IP': 'N/A'
                }

                port_name = printer.get('PortName', '')
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', port_name)
                if ip_match:
                    ip = ip_match.group(1)
                    printer_info['IP'] = ip

                    snmp_result = _query_printer_snmp(ip)
                    if snmp_result:
                        printer_info['Modelo_SNMP'] = snmp_result.get('Modelo', 'N/A')
                        printer_info['Serial_SNMP'] = snmp_result.get('Serial', 'N/A')

                printers.append(printer_info)
    except Exception as e:
        _log(f"Erro ao obter informacoes das impressoras: {e}", "AVISO")

    if not printers:
        _log("Nenhuma impressora detectada.", "AVISO")

    return printers


def _query_printer_snmp(ip):
    """
    Consulta impressora via SNMP para obter modelo e numero de serie reais.
    Retorna dicionario com 'Modelo' e 'Serial' ou None em caso de falha.
    """
    try:
        ps_script = f'''
$IP = "{ip}"
try {{
    $snmp = New-Object -ComObject "olePrn.OleSNMP"
    $snmp.Open($IP, "public", 2, 3000)

    $Modelo = $snmp.Get(".1.3.6.1.2.1.25.3.2.1.3.1")
    $Serial = $snmp.Get(".1.3.6.1.2.1.43.5.1.1.17.1")

    if ($Modelo -and $Serial) {{
        Write-Output "$Modelo|$Serial"
    }}
}} catch {{
}}
'''
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            timeout=10
        )

        if result and result.stdout:
            output = result.stdout.strip()
            if '|' in output:
                parts = output.split('|')
                if len(parts) == 2:
                    return {
                        'Modelo': parts[0].strip(),
                        'Serial': parts[1].strip().upper()
                    }
    except Exception as e:
        _log(f"Erro ao consultar SNMP para IP {ip}: {e}", "AVISO")

    return None


def _get_network_adapters():
    """
    Obtem informacoes de todos os adaptadores de rede via Get-NetAdapter.
    Retorna uma lista de dicionarios com 'Nome', 'Descricao', 'MacAddress' e 'Status' de cada adaptador.
    """
    adapters = []

    try:
        ps_script = """
        Get-NetAdapter | Select-Object Name, InterfaceDescription, MacAddress, Status | ConvertTo-Json
        """
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            timeout=15
        )

        if result and result.stdout and result.stdout.strip():
            adapters_data = json.loads(result.stdout)
            if adapters_data is None:
                adapters_data = []
            if isinstance(adapters_data, dict):
                adapters_data = [adapters_data]

            for adapter in adapters_data:
                adapters.append({
                    'Nome': adapter.get('Name', 'N/A'),
                    'Descricao': adapter.get('InterfaceDescription', 'N/A'),
                    'MacAddress': adapter.get('MacAddress', 'N/A'),
                    'Status': adapter.get('Status', 'N/A')
                })
    except Exception as e:
        _log(f"Erro ao obter informacoes dos adaptadores de rede: {e}", "AVISO")

    if not adapters:
        _log("Nenhum adaptador de rede detectado.", "AVISO")

    return adapters


def _get_unique_id():
    """
    Obtem um identificador unico para o PC.
    Prioridade:
    1. MAC Address do primeiro adaptador de rede ativo (Status = Up)
    2. Fallback para ProcessorId
    Retorna string com o identificador (MAC sem separadores ou ProcessorId).
    """
    try:
        adapters = _get_network_adapters()
        for adapter in adapters:
            if adapter.get('Status') == 'Up' and adapter.get('MacAddress') != 'N/A':
                mac_clean = adapter['MacAddress'].replace('-', '').replace(':', '').upper()
                if mac_clean and len(mac_clean) >= 10:
                    _log(f"[OK] Identificador unico (MAC): {mac_clean}", "OK")
                    return mac_clean
    except Exception as e:
        _log(f"Erro ao obter MAC Address: {e}. Usando fallback.", "AVISO")

    _log("Nenhum adaptador ativo encontrado. Usando ProcessorId como fallback.", "AVISO")
    return _get_processor_id()


def _get_processor_id():
    """
    Obtem o ProcessorId da CPU via WMI (Get-CimInstance Win32_Processor).
    Este identificador e unico para cada processador e nao se repete
    em maquinas chinesas como o UUID.
    """
    try:
        ps_script = "(Get-CimInstance Win32_Processor).ProcessorId"
        result = _safe_subprocess_run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            timeout=10
        )
        if result and result.stdout:
            proc_id = result.stdout.strip()
            if proc_id and len(proc_id) > 5:
                return proc_id
    except Exception as e:
        _log(f"Erro ao obter ProcessorId via PowerShell: {e}", "AVISO")

    _log("Nao foi possivel obter o ProcessorId. Usando 'ID_NAO_DISPONIVEL'.", "ERRO")
    return "ID_NAO_DISPONIVEL"


def _get_anydesk_id():
    """Obtem o ID do AnyDesk do registro (suporte a multiplas versoes e arquiteturas)"""
    registry_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\AnyDesk"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\AnyDesk"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\AnyDesk"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\AnyDesk"),
    ]
    value_names = ["AdvertisedID", "ClientID"]

    for root, path in registry_paths:
        try:
            with winreg.OpenKey(root, path) as key:
                for val_name in value_names:
                    try:
                        value, _ = winreg.QueryValueEx(key, val_name)
                        if value:
                            return str(value).strip()
                    except FileNotFoundError:
                        continue
                    except Exception:
                        continue
        except FileNotFoundError:
            continue
        except Exception:
            continue

    try:
        anydesk_paths = [
            r"C:\Program Files\AnyDesk\AnyDesk.exe",
            r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe"
        ]
        for exe in anydesk_paths:
            if os.path.exists(exe):
                result = _safe_subprocess_run([exe, "--get-id"], timeout=10)
                if result and result.returncode == 0 and result.stdout:
                    return result.stdout.strip()
                break
    except Exception:
        pass

    try:
        ps_script = r'''
$paths = @("$env:ProgramData\AnyDesk\ad.trace", "$env:ProgramData\AnyDesk\service.conf")
foreach ($p in $paths) {
    if (Test-Path $p) {
        $content = Get-Content $p -ErrorAction SilentlyContinue
        if ($content) {
            $id = $content | Select-String -Pattern '^[0-9]+$'
            if ($id) { return $id.Matches.Value }
        }
    }
}
return $null
'''
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=10
        )
        if result and result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass

    return "N/A"


def _get_teamviewer_id():
    """Obtem o ID do TeamViewer do registro (suporte a multiplas versoes)"""
    versions = ["15", "14", "13", "12", "11", "10"]

    registry_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\TeamViewer\Version{}"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\TeamViewer\Version{}"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\TeamViewer\Version{}"),
        (winreg.HKEY_CURRENT_USER, r"Software\TeamViewer"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\TeamViewer"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\TeamViewer"),
    ]
    value_names = ["ClientID", "ClientID_64", "DeviceID", "DeviceID_64"]

    for root, path_template in registry_paths:
        if "{}" in path_template:
            for ver in versions:
                path = path_template.format(ver)
                try:
                    with winreg.OpenKey(root, path) as key:
                        for val_name in value_names:
                            try:
                                value, _ = winreg.QueryValueEx(key, val_name)
                                if value:
                                    return str(value).strip()
                            except FileNotFoundError:
                                continue
                            except Exception:
                                continue
                except FileNotFoundError:
                    continue
                except Exception:
                    continue
        else:
            try:
                with winreg.OpenKey(root, path_template) as key:
                    for val_name in value_names:
                        try:
                            value, _ = winreg.QueryValueEx(key, val_name)
                            if value:
                                return str(value).strip()
                        except FileNotFoundError:
                            continue
                        except Exception:
                            continue
            except FileNotFoundError:
                continue
            except Exception:
                continue

    try:
        ps_script = r'''
$id = $null

$configPath = "$env:ProgramData\TeamViewer\TeamViewer15_Config\TeamViewer.ini"
if (Test-Path $configPath) {
    $lines = Get-Content $configPath -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match 'ClientID=(\d+)') {
            $id = $matches[1]
            break
        }
    }
}

if (-not $id) {
    $configPath2 = "$env:ProgramData\TeamViewer\TeamViewer.ini"
    if (Test-Path $configPath2) {
        $lines = Get-Content $configPath2 -ErrorAction SilentlyContinue
        foreach ($line in $lines) {
            if ($line -match 'ClientID=(\d+)') {
                $id = $matches[1]
                break
            }
        }
    }
}

if (-not $id) {
    try {
        $id = (Get-CimInstance -Class Win32_Product | Where-Object { $_.Name -match 'TeamViewer' }).IdentifyingNumber
        if ($id) { $id = $id -replace '.*(\d+)$', '$1' }
    } catch {}
}

if ($id) { return $id } else { return $null }
'''
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=10
        )
        if result and result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass

    return "N/A"


def run_snapshot_only(local=None, usuario=None):
    """
    Funcao publica para gerar apenas o snapshot de hardware (sem deploy).
    Pode ser chamada diretamente pelo botao "Gerar Snapshot" no GUI.
    Retorna caminho do arquivo local ou None em caso de erro.
    """
    _log("=" * 60, "INFO")
    _log("INICIANDO GERACAO DE SNAPSHOT (MODO ISOLADO)...", "INFO")
    _log("=" * 60, "INFO")

    result = generate_full_snapshot(local=local, usuario=usuario)

    if result:
        _log("[OK] Snapshot gerado com sucesso!", "OK")
    else:
        _log("[ERRO] Falha ao gerar snapshot.", "ERRO")

    return result


def generate_full_snapshot(local=None, usuario=None):
    """
    Gera snapshot completo de hardware com ID unico baseado no MAC Address (com fallback para ProcessorId).
    Parametros:
    local (str): codigo e nome do local (ex: "14120 - ARPEL SBC")
    usuario (str): nome do usuario
    Retorna: caminho do arquivo local ou None em caso de erro.
    """
    _log("Gerando snapshot de hardware...", "INFO")

    unique_id = _get_unique_id()

    file_name = f"CPFANI_Hardware_Snapshot_{unique_id}.txt"
    local_path = Path(SCRIPT_DIR) / file_name
    local_path.parent.mkdir(parents=True, exist_ok=True)

    pc_name = os.environ.get("COMPUTERNAME", "UNKNOWN")
    modelo = _get_system_model()
    processador = _get_processor_name()
    memoria = _get_total_ram()
    windows = _get_windows_version()
    bios_serial = _get_bios_serial()
    anydesk_id = _get_anydesk_id()
    teamviewer_id = _get_teamviewer_id()

    monitores = _get_monitor_info()
    impressoras = _get_printer_info()
    adaptadores = _get_network_adapters()

    local_str = local if local else "Nao informado"
    usuario_str = usuario if usuario else "Nao informado"
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    monitores_section = ""
    if monitores:
        monitores_section = "\n============================================================\n PERIFERICOS - MONITORES\n============================================================\n"
        for idx, monitor in enumerate(monitores, 1):
            monitores_section += f" Monitor {idx}:\n"
            monitores_section += f"   Modelo          : {monitor['Modelo']}\n"
            monitores_section += f"   Numero_de_Serie : {monitor['Numero_de_Serie']}\n\n"
        monitores_section += "============================================================\n"
    else:
        monitores_section = "\n============================================================\n PERIFERICOS - MONITORES\n============================================================\n Nenhum monitor detectado.\n============================================================\n"

    impressoras_section = ""
    if impressoras:
        impressoras_section = "\n============================================================\n PERIFERICOS - IMPRESSORAS\n============================================================\n"
        for idx, printer in enumerate(impressoras, 1):
            impressoras_section += f" Impressora {idx}:\n"
            impressoras_section += f"   Nome          : {printer['Nome']}\n"
            impressoras_section += f"   Status        : {printer['Status']}\n"
            impressoras_section += f"   Porta         : {printer['Porta']}\n"
            impressoras_section += f"   Driver        : {printer['Driver']}\n"
            impressoras_section += f"   Compartilhada : {printer['Compartilhada']}\n"

            if printer['IP'] != 'N/A':
                impressoras_section += f"   IP            : {printer['IP']}\n"
                if printer['Modelo_SNMP'] != 'N/A':
                    impressoras_section += f"   Modelo (SNMP) : {printer['Modelo_SNMP']}\n"
                if printer['Serial_SNMP'] != 'N/A':
                    impressoras_section += f"   Serial (SNMP) : {printer['Serial_SNMP']}\n"

            impressoras_section += "\n"
        impressoras_section += "============================================================\n"
    else:
        impressoras_section = "\n============================================================\n PERIFERICOS - IMPRESSORAS\n============================================================\n Nenhuma impressora detectada.\n============================================================\n"

    adaptadores_section = ""
    if adaptadores:
        adaptadores_section = "\n============================================================\n ADAPTADORES DE REDE\n============================================================\n"
        for idx, adapter in enumerate(adaptadores, 1):
            adaptadores_section += f" Adaptador {idx}:\n"
            adaptadores_section += f"   Nome        : {adapter['Nome']}\n"
            adaptadores_section += f"   Descricao   : {adapter['Descricao']}\n"
            adaptadores_section += f"   MAC Address : {adapter['MacAddress']}\n"
            adaptadores_section += f"   Status      : {adapter['Status']}\n\n"
        adaptadores_section += "============================================================\n"
    else:
        adaptadores_section = "\n============================================================\n ADAPTADORES DE REDE\n============================================================\n Nenhum adaptador detectado.\n============================================================\n"

    content = f"""
============================================================
SNAPSHOT CP FANI V5.9.3 (Edicao Infiltrado + Self-Healing)
Gerado em: {now}

[ID]
Local : {local_str}
Usuario : {usuario_str}

[HARDWARE]
Nome_Computador     : {pc_name}
Modelo_Sistema      : {modelo}
Processador         : {processador}
Memoria_RAM         : {memoria}
Windows             : {windows}
BIOS_Serial         : {bios_serial}
ID (MAC/Proc)       : {unique_id}

[SUPORTE]
AnyDesk    : {anydesk_id}
TeamViewer : {teamviewer_id}
{monitores_section}{impressoras_section}{adaptadores_section}
"""

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        _log(f"[OK] Snapshot local gerado: {local_path}", "OK")
    except Exception as e:
        _log(f"Erro ao gerar snapshot local: {e}", "ERRO")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        import pickle

        credentials_path = os.path.join(os.path.dirname(__file__), "credentials", "oauth2_credentials.json")
        if not os.path.exists(credentials_path):
            _log("Arquivo de credenciais OAuth2 nao encontrado. Pulando upload.", "AVISO")
            return str(local_path)

        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), "credentials", "token.pickle")

        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        service = build('drive', 'v3', credentials=creds)
        FOLDER_ID = "1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d"

        drive_file_name = file_name
        query = f"name='{drive_file_name}' and '{FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])

        media = MediaFileUpload(str(local_path), mimetype='text/plain')

        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
            _log("[OK] Snapshot atualizado no Google Drive (arquivo existente substituido)", "OK")
        else:
            file_metadata = {
                'name': drive_file_name,
                'parents': [FOLDER_ID]
            }
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            _log("[OK] Snapshot enviado para o Google Drive (novo arquivo criado)", "OK")

        return str(local_path)
    except ImportError:
        _log("Bibliotecas do Google Drive (OAuth2) nao instaladas. Pulando upload.", "AVISO")
        _log("Para ativar o upload, instale: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2", "INFO")
        return str(local_path)
    except HttpError as e:
        _log(f"Erro na API do Google Drive: {e}", "ERRO")
    except Exception as e:
        _log(f"Erro ao enviar para o Google Drive: {e}", "ERRO")

    return str(local_path)


def _apply_dark_theme_to_all_users():
    """Aplica tema escuro para todos os usuarios via GPO e HKCU"""
    _log("Aplicando tema escuro para todos os usuarios...", "INFO")

    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "SystemUsesLightTheme", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "AppsUseLightTheme", 0, winreg.REG_DWORD)
        _log("[OK] Tema escuro configurado via GPO (HKLM)", "OK")
    except Exception as e:
        _log(f"Erro ao configurar tema escuro via GPO: {e}", "AVISO")

    sids = _get_all_user_sids()
    if not sids:
        _log("Nenhum SID de usuario encontrado para aplicar tema escuro.", "AVISO")
        return

    for sid in sids:
        try:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _log(f"[OK] Tema escuro aplicado para SID {sid}", "OK")
        except Exception as e:
            _log(f"Erro ao aplicar tema escuro para SID {sid}: {e}", "AVISO")


def _ensure_wallpaper_image():
    r"""Garante que a imagem do wallpaper/lockscreen exista em C:\Windows\Web\Wallpaper\Windows"""
    target_path = r"C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
    expected_hash = _get_expected_wallpaper_sha256()

    if os.path.exists(target_path):
        if not expected_hash or _verify_sha256(target_path, expected_hash):
            return target_path
        _log("Imagem existente com hash invalido. Tentando obter nova copia.", "AVISO")

    _log("Imagem do wallpaper nao encontrada no diretorio do Windows. Tentando obter...", "INFO")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]

    img_path = _get_image_path(local_wp, urls, "cpfani_wallpaper.jpg", expected_hash)

    if img_path:
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(img_path, target_path)
            _log(f"[OK] Imagem copiada para {target_path}", "OK")
            return target_path
        except Exception as e:
            _log(f"Erro ao copiar imagem: {e}", "ERRO")
    else:
        _log("Falha ao obter a imagem do wallpaper.", "ERRO")

    return None


def _apply_wallpaper_to_all_users():
    """Aplica wallpaper para todos os usuarios via GPO e HKCU"""
    _log("Aplicando wallpaper para todos os usuarios...", "INFO")

    wallpaper_path = _ensure_wallpaper_image()
    if not wallpaper_path:
        _log("Wallpaper nao disponivel. Pulando aplicacao.", "ERRO")
        return

    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "Wallpaper", wallpaper_path, winreg.REG_SZ)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "WallpaperStyle", "2", winreg.REG_SZ)
        _log("[OK] Wallpaper configurado via GPO (HKLM)", "OK")
    except Exception as e:
        _log(f"Erro ao configurar wallpaper via GPO: {e}", "AVISO")

    sids = _get_all_user_sids()
    if not sids:
        _log("Nenhum SID de usuario encontrado para aplicar wallpaper.", "AVISO")
        return

    for sid in sids:
        try:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Control Panel\\Desktop", "/v", "Wallpaper", "/t", "REG_SZ", "/d", wallpaper_path, "/f"],
                timeout=10
            )
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Control Panel\\Desktop", "/v", "WallpaperStyle", "/t", "REG_SZ", "/d", "2", "/f"],
                timeout=10
            )
            _log(f"[OK] Wallpaper aplicado para SID {sid}", "OK")
        except Exception as e:
            _log(f"Erro ao aplicar wallpaper para SID {sid}: {e}", "AVISO")


def _apply_lockscreen_to_all_users():
    """Aplica lockscreen para todos os usuarios via GPO + PersonalizationCSP (com bloqueio)"""
    _log("Aplicando lockscreen para todos os usuarios...", "INFO")

    lockscreen_path = _ensure_wallpaper_image()
    if not lockscreen_path:
        _log("Imagem do lockscreen nao disponivel. Pulando aplicacao.", "ERRO")
        return

    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", lockscreen_path, winreg.REG_SZ)
        _log("[OK] Lockscreen configurado via GPO (HKLM)", "OK")
    except Exception as e:
        _log(f"Erro ao configurar lockscreen via GPO: {e}", "AVISO")

    try:
        csp_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP"

        if set_reg(winreg.HKEY_LOCAL_MACHINE, csp_path, "LockScreenImageStatus", 1, winreg.REG_DWORD):
            _log("[OK] LockScreenImageStatus configurado via PersonalizationCSP", "OK")
        else:
            _log("Falha ao configurar LockScreenImageStatus via PersonalizationCSP", "AVISO")

        if set_reg(winreg.HKEY_LOCAL_MACHINE, csp_path, "LockScreenImagePath", lockscreen_path, winreg.REG_SZ):
            _log("[OK] LockScreenImagePath configurado via PersonalizationCSP", "OK")
        else:
            _log("Falha ao configurar LockScreenImagePath via PersonalizationCSP", "AVISO")

        if set_reg(winreg.HKEY_LOCAL_MACHINE, csp_path, "LockScreenImageUrl", lockscreen_path, winreg.REG_SZ):
            _log("[OK] LockScreenImageUrl configurado via PersonalizationCSP", "OK")
        else:
            _log("Falha ao configurar LockScreenImageUrl via PersonalizationCSP", "AVISO")
    except Exception as e:
        _log(f"Erro ao configurar PersonalizationCSP: {e}", "AVISO")

    try:
        _safe_subprocess_run("gpupdate /force", shell=True, timeout=60)
        _log("[OK] Politica de grupo atualizada (gpupdate /force)", "OK")
    except Exception as e:
        _log(f"Erro ao executar gpupdate: {e}", "AVISO")

    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "NoChangingLockScreen", 1, winreg.REG_DWORD)
        _log("[OK] Bloqueio de alteracao da tela de bloqueio ativado", "OK")
    except Exception as e:
        _log(f"Erro ao ativar bloqueio de alteracao: {e}", "AVISO")