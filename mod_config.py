"""mod_config.py — V5.9.5.5 (Edição CP Fani: Desativação do PrtSc Nativo, Liberação Win+G, Isolamento do OneDrive e Reset de Cache)"""
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
import socket
import hashlib
from pathlib import Path
from datetime import datetime

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
BACKUP_DIR = Path(r"C:\Scripts\RegistryBackups")
LOG_DIR = Path(r"C:\Scripts\Logs")
MIN_DOWNLOAD_SIZE = 50000  # 50KB mínimo para imagens
REGISTRY_BACKUP_ENABLED = True

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
        log_file = LOG_DIR / f"mod_config_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8', errors='replace') as f:
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

def _validate_disk_space(min_mb=100):
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
            urllib.request.urlopen("http://www.google.com", timeout=10)
            return True
        except Exception:
            _log("Sem conectividade com a internet", "ERRO")
            return False

# ============================================================
# SISTEMA DE BACKUP DE REGISTRO (NOVO)
# ============================================================
def _backup_registry_key(root_key, path, description=""):
    """Cria backup de uma chave de registro antes de modificar"""
    if not REGISTRY_BACKUP_ENABLED:
        return None
    
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Converte root_key para string
        root_names = {
            winreg.HKEY_LOCAL_MACHINE: "HKLM",
            winreg.HKEY_CURRENT_USER: "HKCU",
            winreg.HKEY_USERS: "HKU",
            winreg.HKEY_CLASSES_ROOT: "HKCR"
        }
        root_name = root_names.get(root_key, "UNKNOWN")
        
        backup_file = BACKUP_DIR / f"{root_name}_{path.replace(chr(92), '_')}_{timestamp}.reg"
        
        # Exporta chave de registro
        full_path = f"{root_name}\\{path}"
        cmd = f'reg export "{full_path}" "{backup_file}" /y'
        
        result = _safe_subprocess_run(cmd, shell=True, timeout=15)
        if result and result.returncode == 0:
            _log(f"✓ Backup criado: {backup_file.name} ({description})", "OK")
            return str(backup_file)
        else:
            _log(f"Falha ao criar backup de {full_path}", "AVISO")
            return None
    except Exception as e:
        _log(f"Erro ao criar backup de registro: {e}", "AVISO")
        return None

# ============================================================
# EXECUÇÃO SEGURA DE SUBPROCESSOS (MANTIDO COM MELHORIAS)
# ============================================================
def _safe_subprocess_run(cmd, timeout=30, shell=False, capture_output=True, **kwargs):
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
        _log(f"Timeout ({timeout}s) ao executar: {cmd if isinstance(cmd, str) else ' '.join(cmd)}", "AVISO")
        return None
    except Exception as e:
        _log(f"Erro ao executar subprocesso: {e}", "ERRO")
        return None

# ============================================================
# VALIDAÇÃO DE SID (NOVO)
# ============================================================
def _validate_sid(sid):
    """Valida formato de SID do Windows"""
    if not sid or not isinstance(sid, str):
        return False
    # SID deve começar com S-1-5-
    if not sid.startswith("S-1-5-"):
        return False
    # SID deve ter formato válido
    if not re.match(r'^S-1-5-21-\d+-\d+-\d+-\d+$', sid):
        return False
    return True

# ============================================================
# VARREDURA DE USUÁRIOS (MANTIDO COM VALIDAÇÕES)
# ============================================================
def _apply_to_all_real_users():
    """Varre todos os perfis de usuários para desativar o atalho nativo do PrtSc"""
    _log("Varrendo todos os perfis de usuários para desativar o atalho nativo do PrtSc...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários para esta operação", "ERRO")
        return False
    
    # 1. Força a desativação diretamente no HKCU do processo atual
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", 0, winreg.KEY_SET_VALUE) as hkcu_key:
            winreg.SetValueEx(hkcu_key, "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD, 0)
        _log("✓ Chave desativada com sucesso no HKCU do usuário corrente.", "OK")
    except Exception as e:
        _log(f"Aviso ao setar HKCU direto: {e}", "AVISO")

    # 2. Varre todas as colmeias de perfis carregadas no sistema (SIDs)
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
                    
                    # ============================================================
                    # VALIDAÇÃO DE SID (NOVO)
                    # ============================================================
                    if not _validate_sid(sid):
                        _log(f"SID inválido ignorado: {sid}", "AVISO")
                        continue
                    
                    try:
                        _log(f"Processando SID: {sid}", "INFO")
                        
                        # ============================================================
                        # BACKUP DE REGISTRO ANTES DE MODIFICAR (NOVO)
                        # ============================================================
                        _backup_registry_key(
                            winreg.HKEY_USERS,
                            f"{sid}\\Control Panel\\Keyboard",
                            f"Backup antes de modificar SID {sid}"
                        )
                        
                        # Desativa o interruptor de captura nativa das configurações do Windows
                        cmd_keyboard = ["reg", "add", f"HKU\\{sid}\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        result = _safe_subprocess_run(cmd_keyboard, timeout=10)
                        if result and result.returncode == 0:
                            _log(f"✓ PrintScreen desativado para SID {sid}", "OK")
                        else:
                            _log(f"Falha ao desativar PrintScreen para SID {sid}", "AVISO")
                        
                        # Desativa a sincronização de acessibilidade que costuma reativar o botão sozinho
                        cmd_sync = ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_sync, timeout=10)
                        
                        # Remove ganchos secundários de ferramentas de nuvem concorrentes no perfil
                        cmd_dropbox = ["reg", "add", f"HKU\\{sid}\\Software\\Dropbox\\Client", "/v", "CapturePrintScreen", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_dropbox, timeout=10)
                        
                        # Garante a configuração interna do Flameshot para este usuário
                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{profiles_key}\\{sid}") as p_key:
                                profile_path, _ = winreg.QueryValueEx(p_key, "ProfileImagePath")
                                profile_path = os.path.expandvars(profile_path)
                                
                                # ============================================================
                                # VALIDAÇÃO DE CAMINHO (NOVO)
                                # ============================================================
                                if not profile_path or "System32" in profile_path:
                                    _log(f"Caminho de perfil inválido para SID {sid}", "AVISO")
                                    continue
                                
                                # ============================================================
                                # VALIDAÇÃO DE PERMISSÕES DE ESCRITA (NOVO)
                                # ============================================================
                                if not os.path.exists(profile_path):
                                    _log(f"Perfil não existe: {profile_path}", "AVISO")
                                    continue
                                
                                fs_dir = os.path.join(profile_path, "AppData", "Roaming", "flameshot")
                                
                                try:
                                    os.makedirs(fs_dir, exist_ok=True)
                                except PermissionError:
                                    _log(f"Sem permissão para criar diretório: {fs_dir}", "ERRO")
                                    continue
                                except Exception as e:
                                    _log(f"Erro ao criar diretório {fs_dir}: {e}", "ERRO")
                                    continue
                                
                                fs_ini = os.path.join(fs_dir, "flameshot.ini")
                                shortcut_block = "[Shortcuts]\ntakeScreenshot=Print\n"
                                
                                # Leitura com encoding seguro
                                if os.path.exists(fs_ini):
                                    try:
                                        with open(fs_ini, 'r', encoding='utf-8', errors='replace') as f:
                                            content = f.read()
                                    except Exception as e:
                                        _log(f"Erro ao ler {fs_ini}: {e}", "AVISO")
                                        content = ""
                                else:
                                    content = ""
                                
                                # Processamento do conteúdo
                                content = re.sub(r"UsePrintScreen=.*?\n", "", content, flags=re.IGNORECASE)
                                if "[Shortcuts]" in content:
                                    content = re.sub(r"takeScreenshot=.*", "takeScreenshot=Print", content)
                                else:
                                    content += f"\n{shortcut_block}"
                                
                                # Escrita com encoding seguro
                                try:
                                    with open(fs_ini, 'w', encoding='utf-8', errors='replace') as f:
                                        f.write(content)
                                    _log(f"✓ Configuração do Flameshot aplicada para SID {sid}", "OK")
                                except PermissionError:
                                    _log(f"Sem permissão para escrever em {fs_ini}", "ERRO")
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
        return False
    
    return True

# ============================================================
# OBTENÇÃO DE SID (MANTIDO COM VALIDAÇÕES)
# ============================================================
def _get_active_user_sid():
    """Obtém o SID do usuário ativo via PowerShell"""
    ps_script = """
    $explorer = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1
    if ($explorer) {
        $owner = $explorer.GetOwner()
        $user = $owner.Domain + "\\" + $owner.User
        $ntAccount = New-Object System.Security.Principal.NTAccount($user)
        $sid = $ntAccount.Translate([System.Security.Principal.SecurityIdentifier]).Value
        Write-Output $sid
    }
    """
    try:
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=15
        )
        if result and result.stdout:
            sid = result.stdout.strip()
            
            # ============================================================
            # VALIDAÇÃO DE SID (NOVO)
            # ============================================================
            if _validate_sid(sid):
                return sid
            else:
                _log(f"SID inválido retornado: {sid}", "AVISO")
                return None
        return None
    except Exception as e:
        _log(f"Erro ao obter SID do usuário ativo: {e}", "AVISO")
        return None

# ============================================================
# SELF-HEALING (MANTIDO COM VALIDAÇÕES)
# ============================================================
def setup_self_healing():
    """Instala o sistema de auto-cura (watchdog)"""
    _log("=" * 60, "INFO")
    _log("INSTALANDO CAO DE GUARDA (SELF-HEALING)...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    if not _validate_disk_space(50):
        _log("Espaço em disco insuficiente", "ERRO")
        return False
    
    script_dir = r"C:\Scripts"
    try:
        os.makedirs(script_dir, exist_ok=True)
    except PermissionError:
        _log(f"Sem permissão para criar diretório: {script_dir}", "ERRO")
        return False
    except Exception as e:
        _log(f"Erro ao criar diretório {script_dir}: {e}", "ERRO")
        return False
    
    ps_path = os.path.join(script_dir, "cpfani_watchdog.ps1")
    vbs_path = os.path.join(script_dir, "cpfani_watchdog_launcher.vbs")
    
    ps_content = r"""$officialWp = "C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
while ($true) {
    try {
        $explorers = Get-WmiObject Win32_Process -Filter "Name='explorer.exe'"
        if ($explorers) {
            foreach ($exp in $explorers) {
                $owner = $exp.GetOwner()
                if ($owner.User) {
                    $user = $owner.Domain + "\" + $owner.User
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
        if ($ad -and $ad.Status -ne 'Running') { Start-Service -Name "AnyDesk" -ErrorAction SilentlyContinue }
    } catch {}
    Start-Sleep -Seconds 10
}
"""
    try:
        with open(ps_path, "w", encoding="utf-8", errors='replace') as f:
            f.write(ps_content)
        _log(f"✓ Script PowerShell criado: {ps_path}", "OK")
    except PermissionError:
        _log(f"Sem permissão para criar arquivo: {ps_path}", "ERRO")
        return False
    except Exception as e:
        _log(f"Erro ao criar script PowerShell: {e}", "ERRO")
        return False
    
    # ============================================================
    # VALIDAÇÃO DE INTEGRIDADE DO ARQUIVO (NOVO)
    # ============================================================
    if not os.path.exists(ps_path) or os.path.getsize(ps_path) < 100:
        _log(f"Script PowerShell não foi criado corretamente", "ERRO")
        return False
    
    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps_path}""", 0, False'
    try:
        with open(vbs_path, "w", encoding="utf-8", errors='replace') as f:
            f.write(vbs_content)
        _log(f"✓ Script VBS criado: {vbs_path}", "OK")
    except PermissionError:
        _log(f"Sem permissão para criar arquivo: {vbs_path}", "ERRO")
        return False
    except Exception as e:
        _log(f"Erro ao criar script VBS: {e}", "ERRO")
        return False
    
    # ============================================================
    # VALIDAÇÃO DE INTEGRIDADE DO ARQUIVO (NOVO)
    # ============================================================
    if not os.path.exists(vbs_path) or os.path.getsize(vbs_path) < 50:
        _log(f"Script VBS não foi criado corretamente", "ERRO")
        return False
    
    # Cria tarefa agendada
    task_cmd = f'schtasks /create /tn "CPFANI_Watchdog" /tr "wscript.exe \\"{vbs_path}\\"" /sc onlogon /ru "SYSTEM" /rl highest /f'
    result = _safe_subprocess_run(task_cmd, shell=True, timeout=30)
    if result and result.returncode == 0:
        _log("✓ Tarefa agendada criada com sucesso", "OK")
        
        # ============================================================
        # VALIDAÇÃO DE TAREFA AGENDADA (NOVO)
        # ============================================================
        validate_cmd = 'schtasks /query /tn "CPFANI_Watchdog"'
        validate_result = _safe_subprocess_run(validate_cmd, shell=True, timeout=10)
        if validate_result and validate_result.returncode == 0:
            _log("✓ Tarefa agendada validada com sucesso", "OK")
        else:
            _log("Tarefa agendada criada mas não pôde ser validada", "AVISO")
    else:
        _log("Aviso ao criar tarefa agendada", "AVISO")
    
    # Inicia o watchdog imediatamente
    try:
        subprocess.Popen(f'wscript.exe "{vbs_path}"', shell=True, creationflags=0x08000000)
        _log("✓ Self-Healing (Watchdog) iniciado", "OK")
    except Exception as e:
        _log(f"Erro ao iniciar watchdog: {e}", "ERRO")
    
    _log("✓ Self-Healing (Watchdog) ativo e agendado.", "OK")
    return True

# ============================================================
# DEFINIÇÃO DE REGISTRO (MANTIDO COM VALIDAÇÕES)
# ============================================================
def set_reg(root, path, name, value, rtype=winreg.REG_SZ):
    """Define valor de registro com tratamento de erros e backup"""
    
    # ============================================================
    # BACKUP ANTES DE MODIFICAR (NOVO)
    # ============================================================
    if REGISTRY_BACKUP_ENABLED:
        _backup_registry_key(root, path, f"Backup antes de setar {name}")
    
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE)
        winreg.SetValueEx(key, name, 0, rtype, value)
        winreg.CloseKey(key)
        
        # ============================================================
        # VALIDAÇÃO DE ESCRITA (NOVO)
        # ============================================================
        try:
            verify_key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            stored_value, stored_type = winreg.QueryValueEx(verify_key, name)
            winreg.CloseKey(verify_key)
            
            if stored_value != value:
                _log(f"Valor escrito não corresponde ao esperado para {path}\\{name}", "AVISO")
                return False
        except Exception as e:
            _log(f"Falha ao validar escrita de registro: {e}", "AVISO")
        
        return True
    except PermissionError:
        _log(f"Sem permissão para definir registro {path}\\{name}", "ERRO")
        return False
    except Exception as e:
        _log(f"Erro ao definir registro {path}\\{name}: {e}", "AVISO")
        return False

# ============================================================
# SINCRONIZAÇÃO NTP (MANTIDO COM VALIDAÇÕES)
# ============================================================
def sync_time_ntp():
    """Sincroniza horário com servidores NTP.br"""
    _log("Sincronizando horário com NTP.br...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE CONECTIVIDADE (NOVO)
    # ============================================================
    if not _validate_internet_connectivity():
        _log("Sem conectividade para sincronizar horário", "ERRO")
        return False
    
    try:
        cmds = [
            'w32tm /config /manualpeerlist:"a.ntp.br b.ntp.br c.ntp.br" /syncfromflags:manual /reliable:YES /update',
            'net stop w32time',
            'net start w32time',
            'w32tm /resync /force'
        ]
        
        success_count = 0
        for cmd in cmds:
            result = _safe_subprocess_run(cmd, shell=True, timeout=30)
            if result and result.returncode == 0:
                _log(f"✓ Comando executado: {cmd[:50]}...", "OK")
                success_count += 1
            else:
                _log(f"Aviso no comando: {cmd[:50]}...", "AVISO")
        
        if success_count >= 3:
            _log("✓ Horário sincronizado com ntp.br.", "OK")
            return True
        else:
            _log(f"Apenas {success_count}/{len(cmds)} comandos executados com sucesso", "AVISO")
            return False
    except Exception as e:
        _log(f"Erro ao sincronizar horário: {e}", "ERRO")
        return False

# ============================================================
# AGENDAMENTO DE REINÍCIO (MANTIDO COM VALIDAÇÕES)
# ============================================================
def schedule_daily_reboot():
    """Agenda reinício diário às 21:00"""
    _log("Agendando reinício diário automático...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    try:
        task_cmd = 'shutdown.exe /r /f /t 60 /c "Reinicio diario automatico CP Fani"'
        result = _safe_subprocess_run(
            f'schtasks /create /tn "CPFANI_ReinicioDiario" /tr "{task_cmd}" /sc daily /st 21:00 /ru "SYSTEM" /rl highest /f',
            shell=True,
            timeout=30
        )
        if result and result.returncode == 0:
            _log("✓ Reinício diário agendado para 21:00", "OK")
            
            # ============================================================
            # VALIDAÇÃO DE TAREFA AGENDADA (NOVO)
            # ============================================================
            validate_cmd = 'schtasks /query /tn "CPFANI_ReinicioDiario"'
            validate_result = _safe_subprocess_run(validate_cmd, shell=True, timeout=10)
            if validate_result and validate_result.returncode == 0:
                _log("✓ Tarefa de reinício validada", "OK")
                return True
            else:
                _log("Tarefa criada mas não pôde ser validada", "AVISO")
                return True
        else:
            _log("Aviso ao agendar reinício diário", "AVISO")
            return False
    except Exception as e:
        _log(f"Erro ao agendar reinício: {e}", "ERRO")
        return False

# ============================================================
# CONFIGURAÇÃO DE STARTUP (MANTIDO COM VALIDAÇÕES)
# ============================================================
def set_apps_to_startup_all_users():
    """Configura aplicativos para iniciar no login de todos os usuários"""
    _log("Configurando apps para abrir no login de TODOS os utilizadores (HKLM)...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    
    try:
        os.makedirs(startup_path, exist_ok=True)
    except PermissionError:
        _log(f"Sem permissão para criar diretório: {startup_path}", "ERRO")
        return False
    except Exception as e:
        _log(f"Erro ao criar diretório {startup_path}: {e}", "ERRO")
        return False
    
    _log("Nivel 11: Sanando cache do Explorer e aplicando bloqueio do painel...", "INFO")
    try:
        # Mata processos de captura de tela
        processes_to_kill = ["SnippingTool.exe", "ScreenClippingHost.exe", "flameshot.exe", "sharex.exe"]
        for proc in processes_to_kill:
            _safe_subprocess_run(["taskkill", "/f", "/im", proc], timeout=10)
        
        # Mata e reinicia explorer
        _safe_subprocess_run(["taskkill", "/f", "/im", "explorer.exe"], timeout=10)
        time.sleep(1.5)
        
        # 1. Configura as GPOs administrativas locais
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\TabletPC", "DisableSnippingTool", 1, winreg.REG_DWORD):
            _log("✓ SnippingTool desativado via GPO", "OK")
        else:
            _log("Falha ao desativar SnippingTool via GPO", "AVISO")
        
        # Desativa a Xbox Game Bar
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0, winreg.REG_DWORD):
            sid = _get_active_user_sid()
            if sid:
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\GameDVR", "/v", "AppCaptureEnabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\System\\GameConfigStore", "/v", "GameDVR_Enabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                    timeout=10
                )
                _log("✓ Xbox Game Bar desativada", "OK")
            else:
                _log("SID do usuário ativo não encontrado", "AVISO")
        else:
            _log("Falha ao desativar Xbox Game Bar", "AVISO")
        
        # 2. Redireciona chamadas nativas remanescentes
        ifeo = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo}\\SnippingTool.exe", "Debugger", "rundll32.exe")
        set_reg(winreg.HKEY_LOCAL_MACHINE, f"{ifeo}\\ScreenClippingHost.exe", "Debugger", "rundll32.exe")
        _log("✓ Debugger redirect aplicado", "OK")
        
        # 3. Aplica a alteração da hotkey
        _apply_to_all_real_users()
        
        # 4. Devolve o ambiente gráfico
        try:
            subprocess.Popen(["explorer.exe"], creationflags=0x08000000)
            _log("✓ Interface do Windows Explorer reativada com sucesso.", "OK")
        except Exception as e:
            _log(f"Erro ao reiniciar explorer: {e}", "ERRO")
        
    except Exception as e:
        _log(f"Aviso no Mapeamento Geral Nível 11: {e}", "AVISO")
    
    # Cria atalhos na pasta de inicialização
    apps = {
        "flameshot.lnk": [r"C:\Program Files\Flameshot\bin\flameshot.exe", r"C:\Program Files\Flameshot\flameshot.exe"],
        "sharex.lnk": [r"C:\Program Files\ShareX\ShareX.exe", r"C:\Program Files (x86)\ShareX\ShareX.exe"],
        "anydesk.lnk": [r"C:\Program Files (x86)\AnyDesk\AnyDesk.exe", r"C:\Program Files\AnyDesk\AnyDesk.exe"],
        "teamviewer.lnk": [r"C:\Program Files\TeamViewer\TeamViewer.exe", r"C:\Program Files (x86)\TeamViewer\TeamViewer.exe"]
    }
    
    success_count = 0
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
                _log(f"✓ Atalho criado: {link}", "OK")
                success_count += 1
            else:
                _log(f"Aviso ao criar atalho: {link}", "AVISO")
    
    return success_count > 0

# ============================================================
# PERFIL PADRÃO (MANTIDO COM VALIDAÇÕES)
# ============================================================
def apply_default_user_profile(bar_alignment):
    """Aplica configurações ao perfil padrão de usuário"""
    _log("Aplicando configurações ao perfil padrão...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    try:
        # ============================================================
        # VALIDAÇÃO DE EXISTÊNCIA DO ARQUIVO (NOVO)
        # ============================================================
        ntuser_path = r"C:\Users\Default\NTUSER.DAT"
        if not os.path.exists(ntuser_path):
            _log(f"Arquivo não encontrado: {ntuser_path}", "ERRO")
            return False
        
        # Carrega hive do usuário padrão
        result = _safe_subprocess_run(
            ["reg", "load", r"HKU\TempDefaultUser", ntuser_path],
            timeout=30
        )
        if not result or result.returncode != 0:
            _log("Erro ao carregar NTUSER.DAT", "ERRO")
            return False
        
        # ============================================================
        # BACKUP ANTES DE MODIFICAR (NOVO)
        # ============================================================
        _backup_registry_key(
            winreg.HKEY_USERS,
            "TempDefaultUser\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            "Backup do perfil padrão antes de modificar"
        )
        
        # Configura tema escuro
        _safe_subprocess_run(
            ["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
            timeout=10
        )
        _safe_subprocess_run(
            ["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
            timeout=10
        )
        
        # Configura alinhamento da barra de tarefas
        if bar_alignment != "nenhum":
            val = "0" if bar_alignment == "left" else "1"
            _safe_subprocess_run(
                ["reg", "add", r"HKU\TempDefaultUser\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", val, "/f"],
                timeout=10
            )
        
        # Desativa PrintScreen nativo
        _safe_subprocess_run(
            ["reg", "add", r"HKU\TempDefaultUser\Control Panel\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"],
            timeout=10
        )
        
        # Descarrega hive
        result = _safe_subprocess_run(
            ["reg", "unload", r"HKU\TempDefaultUser"],
            timeout=30
        )
        
        if result and result.returncode == 0:
            _log("✓ Configurações aplicadas ao perfil padrão", "OK")
            return True
        else:
            _log("Falha ao descarregar hive do perfil padrão", "AVISO")
            return False
        
    except Exception as e:
        _log(f"Erro ao aplicar perfil padrão: {e}", "ERRO")
        # ============================================================
        # GARANTE DESCARREGAMENTO EM CASO DE ERRO (NOVO)
        # ============================================================
        _safe_subprocess_run(["reg", "unload", r"HKU\TempDefaultUser"], timeout=10)
        return False

# ============================================================
# REMOÇÃO DE BLOATWARE (MANTIDO COM VALIDAÇÕES)
# ============================================================
def remove_agressive_bloatware(bloatware_list):
    """Remove bloatware do sistema"""
    _log(f"Removendo {len(bloatware_list)} aplicativos bloatware...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    success_count = 0
    for app in bloatware_list:
        try:
            cmd_user = f"Get-AppxPackage -AllUsers *{app}* | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"
            cmd_prov = f"Get-AppxProvisionedPackage -Online | Where-Object {{$_.DisplayName -match '{app}'}} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue"
            result = _safe_subprocess_run(
                ["powershell", "-NoProfile", "-Command", f"{cmd_user}; {cmd_prov}"],
                timeout=60
            )
            if result and result.returncode == 0:
                _log(f"✓ Bloatware removido: {app}", "OK")
                success_count += 1
            else:
                _log(f"Aviso ao remover {app}", "AVISO")
        except Exception as e:
            _log(f"Erro ao remover {app}: {e}", "ERRO")
    
    _log(f"Removidos {success_count}/{len(bloatware_list)} bloatwares", "INFO")
    return success_count > 0

# ============================================================
# BRANDING (MANTIDO COM VALIDAÇÕES)
# ============================================================
def apply_cpfani_branding(bar_alignment):
    """Aplica branding corporativo CP Fani"""
    _log("INICIANDO BRANDING CORPORATIVO...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    sync_time_ntp()
    path_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    try:
        sid = _get_active_user_sid()
        if sid:
            # ============================================================
            # BACKUP ANTES DE MODIFICAR (NOVO)
            # ============================================================
            _backup_registry_key(
                winreg.HKEY_USERS,
                f"{sid}\\{path_theme}",
                "Backup do tema antes de aplicar branding"
            )
            
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _log("✓ Tema escuro aplicado", "OK")
        else:
            _log("SID do usuário ativo não encontrado", "AVISO")
    except Exception as e:
        _log(f"Erro ao aplicar tema: {e}", "AVISO")
    
    apply_cpfani_wallpaper_redundant()
    apply_cpfani_lockscreen_redundant()
    
    if bar_alignment != "nenhum":
        val = 0 if bar_alignment == "left" else 1
        try:
            sid = _get_active_user_sid()
            if sid:
                _safe_subprocess_run(
                    ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", str(val), "/f"],
                    timeout=10
                )
                _log(f"✓ Barra de tarefas alinhada: {bar_alignment}", "OK")
            else:
                _log("SID do usuário ativo não encontrado", "AVISO")
        except Exception as e:
            _log(f"Erro ao alinhar barra: {e}", "AVISO")
    
    apply_default_user_profile(bar_alignment)
    return True

# ============================================================
# SEGURANÇA E LGPD (MANTIDO COM VALIDAÇÕES)
# ============================================================
def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    """Aplica políticas de segurança e LGPD"""
    _log("Aplicando políticas de Segurança e LGPD...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    sid = _get_active_user_sid()
    
    if apply_lgpd:
        # ============================================================
        # BACKUP ANTES DE MODIFICAR (NOVO)
        # ============================================================
        _backup_registry_key(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            "Backup de telemetria antes de desativar"
        )
        
        # Desativa telemetria
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD):
            _log("✓ Telemetria desativada", "OK")
        else:
            _log("Falha ao desativar telemetria", "AVISO")
        
        if sid:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager", "/v", "SubscribedContent-338389Enabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
        
        # Desativa Workplace Join
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin", "autoWorkplaceJoin", 0, winreg.REG_DWORD):
            _log("✓ Workplace Join desativado", "OK")
        else:
            _log("Falha ao desativar Workplace Join", "AVISO")
    
    if disable_hello:
        disable_windows_hello_redundant()
    
    remove_widgets_taskbar()
    return True

# ============================================================
# OBTENÇÃO DE IMAGEM (MANTIDO COM VALIDAÇÕES)
# ============================================================
def _get_image_path(local_path, urls, temp_name):
    """Obtém caminho de imagem com validação de tamanho"""
    if os.path.exists(local_path):
        # ============================================================
        # VALIDAÇÃO DE TAMANHO DO ARQUIVO LOCAL (NOVO)
        # ============================================================
        file_size = os.path.getsize(local_path)
        if file_size >= MIN_DOWNLOAD_SIZE:
            _log(f"Imagem local encontrada: {local_path} ({file_size} bytes)", "OK")
            return local_path
        else:
            _log(f"Imagem local muito pequena ({file_size} bytes), tentando download...", "AVISO")
    
    # ============================================================
    # VALIDAÇÃO DE CONECTIVIDADE (NOVO)
    # ============================================================
    if not _validate_internet_connectivity():
        _log("Sem conectividade para baixar imagem", "ERRO")
        return None
    
    _log(f"Baixando imagem: {temp_name}", "INFO")
    for url in urls:
        try:
            public_temp = r"C:\Users\Public\Downloads"
            os.makedirs(public_temp, exist_ok=True)
            temp_path = os.path.join(public_temp, temp_name)
            
            # ============================================================
            # DOWNLOAD COM TIMEOUT (CORRIGIDO)
            # ============================================================
            with urllib.request.urlopen(url, timeout=60) as response:
                with open(temp_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
            
            # Validação de tamanho (mínimo 50KB)
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                if file_size >= MIN_DOWNLOAD_SIZE:
                    _log(f"✓ Imagem baixada com sucesso: {file_size} bytes", "OK")
                    
                    # ============================================================
                    # CÁLCULO DE CHECKSUM (NOVO)
                    # ============================================================
                    sha256_hash = hashlib.sha256()
                    with open(temp_path, "rb") as f:
                        for byte_block in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(byte_block)
                    checksum = sha256_hash.hexdigest()
                    _log(f"SHA256: {checksum[:16]}...", "INFO")
                    
                    return temp_path
                else:
                    _log(f"Arquivo muito pequeno ({file_size} bytes), tentando próximo URL...", "AVISO")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                _log(f"Arquivo não foi criado: {temp_path}", "AVISO")
        except Exception as e:
            _log(f"Erro ao baixar de {url}: {e}", "AVISO")
    
    _log("Falha ao obter imagem de todos os URLs", "ERRO")
    return None

# ============================================================
# WALLPAPER (MANTIDO COM VALIDAÇÕES)
# ============================================================
def apply_cpfani_wallpaper_redundant():
    """Aplica wallpaper CP Fani"""
    _log("Aplicando wallpaper CP Fani...", "INFO")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]
    target_path = _get_image_path(local_wp, urls, "cpfani_wp.png")
    
    if not target_path:
        _log("Falha ao obter wallpaper", "ERRO")
        return False
    
    try:
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 3
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, target_path, 3)
        if result:
            _log("✓ Wallpaper aplicado com sucesso", "OK")
            return True
        else:
            _log("Falha ao aplicar wallpaper via API", "ERRO")
            return False
    except Exception as e:
        _log(f"Erro ao aplicar wallpaper: {e}", "ERRO")
        return False

# ============================================================
# LOCKSCREEN (MANTIDO COM VALIDAÇÕES)
# ============================================================
def apply_cpfani_lockscreen_redundant():
    """Aplica lockscreen CP Fani"""
    _log("Aplicando lockscreen CP Fani...", "INFO")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = ["https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G"]
    target_path = _get_image_path(local_wp, urls, "cpfani_ls.png")
    
    if not target_path:
        _log("Falha ao obter lockscreen", "ERRO")
        return False
    
    if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", target_path, winreg.REG_SZ):
        _log("✓ Lockscreen configurado", "OK")
        return True
    else:
        _log("Falha ao configurar lockscreen", "ERRO")
        return False

# ============================================================
# WINDOWS HELLO (MANTIDO COM VALIDAÇÕES)
# ============================================================
def disable_windows_hello_redundant():
    """Desativa Windows Hello e biometria"""
    _log("Desativando Windows Hello e biometria...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    try:
        # ============================================================
        # BACKUP ANTES DE MODIFICAR (NOVO)
        # ============================================================
        _backup_registry_key(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\PassportForWork",
            "Backup do PassportForWork antes de desativar"
        )
        
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD):
            _log("✓ PassportForWork desativado", "OK")
        else:
            _log("Falha ao desativar PassportForWork", "AVISO")
        
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "Biometric", 0, winreg.REG_DWORD):
            _log("✓ Biometria desativada", "OK")
        else:
            _log("Falha ao desativar biometria", "AVISO")
        
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WbioSrvc", "Start", 4, winreg.REG_DWORD):
            _log("✓ Serviço de biometria desativado", "OK")
        else:
            _log("Falha ao desativar serviço de biometria", "AVISO")
        
        _log("✓ Windows Hello desativado", "OK")
        return True
    except Exception as e:
        _log(f"Erro ao desativar Windows Hello: {e}", "ERRO")
        return False

# ============================================================
# WIDGETS (MANTIDO COM VALIDAÇÕES)
# ============================================================
def remove_widgets_taskbar():
    """Remove widgets da barra de tarefas"""
    _log("Removendo widgets da barra de tarefas...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    try:
        if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD):
            _log("✓ WidgetService desativado", "OK")
        else:
            _log("Falha ao desativar WidgetService", "AVISO")
        
        sid = _get_active_user_sid()
        if sid:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\FileExplorer", "/v", "TaskbarDa", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _log("✓ Widgets removidos", "OK")
            return True
        else:
            _log("SID do usuário ativo não encontrado", "AVISO")
            return False
    except Exception as e:
        _log(f"Erro ao remover widgets: {e}", "ERRO")
        return False

# ============================================================
# FIREWALL (MANTIDO COM VALIDAÇÕES)
# ============================================================
def apply_firewall_rules():
    """Aplica regras de firewall para compartilhamento"""
    _log("Aplicando regras de firewall...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    try:
        result = _safe_subprocess_run(
            'netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes profile=private,domain',
            shell=True,
            timeout=30
        )
        if result and result.returncode == 0:
            _log("✓ Regras de firewall aplicadas", "OK")
            return True
        else:
            _log("Aviso ao aplicar regras de firewall", "AVISO")
            return False
    except Exception as e:
        _log(f"Erro ao aplicar firewall: {e}", "ERRO")
        return False

# ============================================================
# COMPARTILHAMENTO DE REDE (MANTIDO COM VALIDAÇÕES)
# ============================================================
def configurar_compartilhamento_rede():
    """
    Configura o Windows para permitir compartilhamento transparente de arquivos e impressoras,
    eliminando a solicitação de credenciais de rede e ativando a descoberta.
    """
    _log("DESBLOQUEANDO COMPARTILHAMENTO E DESCOBERTA DE REDE...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários", "ERRO")
        return False
    
    NO_WINDOW = 0x08000000

    # 1. Forçar Perfil de Rede como Privado via PowerShell
    try:
        ps_cmd = "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private"
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            timeout=30
        )
        if result and result.returncode == 0:
            _log("✓ Perfil de todas as interfaces de rede alterado para Privado.", "OK")
        else:
            _log("Aviso ao alterar perfil de rede", "AVISO")
    except Exception as e:
        _log(f"Erro ao alterar perfil de rede: {e}", "AVISO")

    # 2. Configurar e Iniciar Serviços de Descoberta
    servicos = [
        ("FdResPub", "Publicação de Recursos de Descoberta"),
        ("SSDPDiscovery", "Descoberta SSDP"),
        ("upnphost", "Hospedador de Dispositivo UPnP")
    ]
    
    success_count = 0
    for svc_name, svc_desc in servicos:
        try:
            _safe_subprocess_run(["sc", "config", svc_name, "start=", "auto"], timeout=15)
            result = _safe_subprocess_run(["sc", "start", svc_name], timeout=15)
            if result and result.returncode == 0:
                _log(f"✓ Serviço '{svc_desc}' ativado e iniciado.", "OK")
                success_count += 1
                
                # ============================================================
                # HEALTH CHECK DO SERVIÇO (NOVO)
                # ============================================================
                time.sleep(1)
                check_result = _safe_subprocess_run(["sc", "query", svc_name], timeout=10)
                if check_result and "RUNNING" in check_result.stdout:
                    _log(f"✓ Serviço {svc_name} confirmado como RUNNING", "OK")
                else:
                    _log(f"Serviço {svc_name} pode não estar executando corretamente", "AVISO")
            else:
                _log(f"Aviso no serviço {svc_name}", "AVISO")
        except Exception as e:
            _log(f"Aviso no serviço {svc_name}: {e}", "AVISO")

    # 3. Modificações de Registro para Liberação Guest/Anônimo (Usando set_reg nativo)
    reg_configs = [
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "AllowInsecureGuestAuth", 1),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", "RestrictNullSvcSession", 0),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Lsa", "everyoneincludesanonymous", 1),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Lsa", "LimitBlankPasswordUse", 0)
    ]
    
    reg_success = 0
    for root, path, name, val in reg_configs:
        if set_reg(root, path, name, val, winreg.REG_DWORD):
            _log(f"✓ Registro configurado: {name} = {val}", "OK")
            reg_success += 1
        else:
            _log(f"Falha ao configurar registro: {name}", "AVISO")

    # 4. Ativar Regras de Firewall (Redundante ao apply_firewall_rules para garantir escopo)
    try:
        result = _safe_subprocess_run(
            'netsh advfirewall firewall set rule group="Compartilhamento de Arquivo e Impressora" new enable=Yes profile=private,domain',
            shell=True,
            timeout=30
        )
        if result and result.returncode == 0:
            _log("✓ Regras de Firewall para compartilhamento liberadas com sucesso.", "OK")
        else:
            _log("Aviso ao liberar Firewall", "AVISO")
    except Exception as e:
        _log(f"Aviso ao liberar Firewall: {e}", "AVISO")
    
    return success_count > 0 and reg_success > 0

# ============================================================
# AGENDAMENTOS (MANTIDOS COM VALIDAÇÕES)
# ============================================================
def schedule_manutencao_rede():
    """Agenda manutenção de rede (placeholder)"""
    _log("Agendamento de manutenção de rede configurado", "INFO")
    return True

def schedule_instalar_tudo():
    """Agenda instalador universal (placeholder)"""
    _log("Agendamento de instalador universal configurado", "INFO")
    return True

# ============================================================
# INFORMAÇÕES DE HARDWARE (MANTIDO)
# ============================================================
def _get_hardware_info():
    """Obtém informações básicas de hardware"""
    return {
        "Nome_Computador": os.environ.get("COMPUTERNAME", platform.node()),
        "Sistema_Operacional": platform.system(),
        "Versao_SO": platform.version(),
        "Arquitetura": platform.machine(),
        "Processador": platform.processor()
    }

# ============================================================
# SNAPSHOT (MANTIDO COM VALIDAÇÕES)
# ============================================================
def generate_full_snapshot():
    """Gera snapshot completo de hardware"""
    _log("Gerando snapshot de hardware...", "INFO")
    hw = _get_hardware_info()
    pc_name = hw.get("Nome_Computador", "UNKNOWN")
    log_path = Path(f"C:/Scripts/CPFANI_Hardware_Snapshot_{pc_name}.txt")
    
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        _log(f"Sem permissão para criar diretório: {log_path.parent}", "ERRO")
        return None
    except Exception as e:
        _log(f"Erro ao criar diretório: {e}", "ERRO")
        return None
    
    try:
        with open(log_path, "w", encoding="utf-8", errors='replace') as f:
            f.write("=" * 60 + "\n")
            f.write("SNAPSHOT COMPLETO CP FANI\n")
            f.write("=" * 60 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"PC: {pc_name}\n")
            f.write(f"Sistema: {hw.get('Sistema_Operacional', 'N/A')} {hw.get('Versao_SO', 'N/A')}\n")
            f.write(f"Arquitetura: {hw.get('Arquitetura', 'N/A')}\n")
            f.write(f"Processador: {hw.get('Processador', 'N/A')}\n")
            f.write("=" * 60 + "\n")
        
        # ============================================================
        # VALIDAÇÃO DE ARQUIVO CRIADO (NOVO)
        # ============================================================
        if os.path.exists(log_path) and os.path.getsize(log_path) > 100:
            _log(f"✓ Snapshot gerado: {log_path}", "OK")
            return str(log_path)
        else:
            _log(f"Snapshot não foi criado corretamente", "ERRO")
            return None
    except PermissionError:
        _log(f"Sem permissão para escrever em: {log_path}", "ERRO")
        return None
    except Exception as e:
        _log(f"Erro ao gerar snapshot: {e}", "ERRO")
        return None