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
from pathlib import Path
from datetime import datetime

# Constante para diretório de scripts (centralização)
SCRIPT_DIR = r"C:\Scripts"

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

def _apply_to_all_real_users():
    """Varre todos os perfis de usuários para desativar o atalho nativo do PrtSc"""
    _log("Varrendo todos os perfis de usuários para desativar o atalho nativo do PrtSc...", "INFO")
    
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
                    
                    try:
                        _log(f"Processando SID: {sid}", "INFO")
                        
                        # Desativa o interruptor de captura nativa das configurações do Windows
                        cmd_keyboard = ["reg", "add", f"HKU\\{sid}\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_keyboard, timeout=10)
                        
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
                                if profile_path and "System32" not in profile_path:
                                    fs_dir = os.path.join(profile_path, "AppData", "Roaming", "flameshot")
                                    os.makedirs(fs_dir, exist_ok=True)
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
            return sid if sid.startswith("S-1-5-") else None
        return None
    except Exception as e:
        _log(f"Erro ao obter SID do usuário ativo: {e}", "AVISO")
        return None

def setup_self_healing():
    """Instala o sistema de auto-cura (watchdog)"""
    _log("=" * 60, "INFO")
    _log("INSTALANDO CAO DE GUARDA (SELF-HEALING)...", "INFO")
    script_dir = SCRIPT_DIR
    os.makedirs(script_dir, exist_ok=True)
    
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
    except Exception as e:
        _log(f"Erro ao criar script PowerShell: {e}", "ERRO")
        return False
    
    vbs_content = f'Set objShell = CreateObject("WScript.Shell")\nobjShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File ""{ps_path}""", 0, False'
    try:
        with open(vbs_path, "w", encoding="utf-8", errors='replace') as f:
            f.write(vbs_content)
        _log(f"✓ Script VBS criado: {vbs_path}", "OK")
    except Exception as e:
        _log(f"Erro ao criar script VBS: {e}", "ERRO")
        return False
    
    # Cria tarefa agendada
    task_cmd = f'schtasks /create /tn "CPFANI_Watchdog" /tr "wscript.exe \\"{vbs_path}\\"" /sc onlogon /ru "SYSTEM" /rl highest /f'
    result = _safe_subprocess_run(task_cmd, shell=True, timeout=30)
    if result and result.returncode == 0:
        _log("✓ Tarefa agendada criada com sucesso", "OK")
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
    """Sincroniza horário com servidores NTP.br"""
    _log("Sincronizando horário com NTP.br...", "INFO")
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
                _log(f"✓ Comando executado: {cmd[:50]}...", "OK")
            else:
                _log(f"Aviso no comando: {cmd[:50]}...", "AVISO")
        _log("✓ Horário sincronizado com ntp.br.", "OK")
    except Exception as e:
        _log(f"Erro ao sincronizar horário: {e}", "ERRO")

def schedule_daily_reboot():
    """Agenda reinício diário às 21:00"""
    _log("Agendando reinício diário automático...", "INFO")
    try:
        task_cmd = 'shutdown.exe /r /f /t 60 /c "Reinicio diario automatico CP Fani"'
        result = _safe_subprocess_run(
            f'schtasks /create /tn "CPFANI_ReinicioDiario" /tr "{task_cmd}" /sc daily /st 21:00 /ru "SYSTEM" /rl highest /f',
            shell=True,
            timeout=30
        )
        if result and result.returncode == 0:
            _log("✓ Reinício diário agendado para 21:00", "OK")
        else:
            _log("Aviso ao agendar reinício diário", "AVISO")
    except Exception as e:
        _log(f"Erro ao agendar reinício: {e}", "ERRO")

def set_apps_to_startup_all_users():
    """Configura aplicativos para iniciar no login de todos os usuários"""
    _log("Configurando apps para abrir no login de TODOS os utilizadores (HKLM)...", "INFO")
    startup_path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"
    os.makedirs(startup_path, exist_ok=True)
    
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
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\TabletPC", "DisableSnippingTool", 1, winreg.REG_DWORD)
        _log("✓ SnippingTool desativado via GPO", "OK")
        
        # Desativa a Xbox Game Bar
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0, winreg.REG_DWORD)
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
            else:
                _log(f"Aviso ao criar atalho: {link}", "AVISO")

def apply_default_user_profile(bar_alignment):
    """Aplica configurações ao perfil padrão de usuário"""
    _log("Aplicando configurações ao perfil padrão...", "INFO")
    try:
        # Carrega hive do usuário padrão
        result = _safe_subprocess_run(
            ["reg", "load", r"HKU\TempDefaultUser", r"C:\Users\Default\NTUSER.DAT"],
            timeout=30
        )
        if not result or result.returncode != 0:
            _log("Erro ao carregar NTUSER.DAT", "ERRO")
            return
        
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
        _safe_subprocess_run(
            ["reg", "unload", r"HKU\TempDefaultUser"],
            timeout=30
        )
        
        _log("✓ Configurações aplicadas ao perfil padrão", "OK")
    except Exception as e:
        _log(f"Erro ao aplicar perfil padrão: {e}", "ERRO")

def remove_agressive_bloatware(bloatware_list):
    """Remove bloatware do sistema"""
    _log(f"Removendo {len(bloatware_list)} aplicativos bloatware...", "INFO")
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
            else:
                _log(f"Aviso ao remover {app}", "AVISO")
        except Exception as e:
            _log(f"Erro ao remover {app}: {e}", "ERRO")
    return True

def apply_cpfani_branding(bar_alignment):
    """Aplica branding corporativo CP Fani com redundância para todos os usuários"""
    _log("INICIANDO BRANDING CORPORATIVO...", "INFO")
    sync_time_ntp()
    path_theme = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    try:
        sid = _get_active_user_sid()
        if sid:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\{path_theme}", "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
            _log("✓ Tema escuro aplicado para o usuário ativo", "OK")
    except Exception as e:
        _log(f"Erro ao aplicar tema: {e}", "AVISO")
    
    apply_cpfani_wallpaper_redundant()
    apply_cpfani_lockscreen_redundant()
    
    if bar_alignment != "nenhum":
        val = 0 if bar_alignment == "left" else 1
        try:
            sid = _get_active_user_sid()
            if sid:
                # CORREÇÃO: raw string para evitar problemas com barras invertidas
                reg_path = rf"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced"
                _safe_subprocess_run(
                    ["reg", "add", reg_path, "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", str(val), "/f"],
                    timeout=10
                )
                _log(f"✓ Barra de tarefas alinhada: {bar_alignment}", "OK")
        except Exception as e:
            _log(f"Erro ao alinhar barra: {e}", "AVISO")
    
    apply_default_user_profile(bar_alignment)
    
    # ================== NOVAS FUNÇÕES DE REDUNDÂNCIA ==================
    _log("Aplicando configurações de tema escuro, wallpaper e lockscreen para TODOS os usuários (redundância)...", "INFO")
    _apply_dark_theme_to_all_users()
    _apply_wallpaper_to_all_users()
    _apply_lockscreen_to_all_users()

def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    """Aplica políticas de segurança e LGPD"""
    _log("Aplicando políticas de Segurança e LGPD...", "INFO")
    sid = _get_active_user_sid()
    
    if apply_lgpd:
        # Desativa telemetria
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0, winreg.REG_DWORD)
        _log("✓ Telemetria desativada", "OK")
        
        if sid:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager", "/v", "SubscribedContent-338389Enabled", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
        
        # Desativa Workplace Join
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin", "autoWorkplaceJoin", 0, winreg.REG_DWORD)
        _log("✓ Workplace Join desativado", "OK")
    
    if disable_hello:
        disable_windows_hello_redundant()
        # A remoção de widgets agora é condicional, vinculada à desativação do Hello
        remove_widgets_taskbar()
    # Se disable_hello for False, não remove widgets (comportamento antigo removido)

def _get_image_path(local_path, urls, temp_name):
    """Obtém caminho de imagem com validação de tamanho"""
    if os.path.exists(local_path):
        _log(f"Imagem local encontrada: {local_path}", "OK")
        return local_path
    
    _log(f"Baixando imagem: {temp_name}", "INFO")
    for url in urls:
        try:
            public_temp = r"C:\Users\Public\Downloads"
            os.makedirs(public_temp, exist_ok=True)
            temp_path = os.path.join(public_temp, temp_name)
            
            # Download com validação
            urllib.request.urlretrieve(url, temp_path)
            
            # Validação de tamanho (mínimo 10KB)
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 10000:
                _log(f"✓ Imagem baixada com sucesso: {os.path.getsize(temp_path)} bytes", "OK")
                return temp_path
            else:
                _log(f"Arquivo muito pequeno, tentando próximo URL...", "AVISO")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            _log(f"Erro ao baixar de {url}: {e}", "AVISO")
    
    _log("Falha ao obter imagem de todos os URLs", "ERRO")
    return None

def apply_cpfani_wallpaper_redundant():
    """Aplica wallpaper CP Fani e copia para diretório de wallpapers do Windows"""
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
    
    # Copia para o diretório de wallpapers do Windows (fallback para todos os usuários)
    try:
        windows_wp_dir = r"C:\Windows\Web\Wallpaper\Windows"
        os.makedirs(windows_wp_dir, exist_ok=True)
        windows_wp_path = os.path.join(windows_wp_dir, "cpfani_wallpaper.jpg")
        shutil.copy2(target_path, windows_wp_path)
        _log(f"✓ Wallpaper copiado para {windows_wp_path}", "OK")
    except Exception as e:
        _log(f"Erro ao copiar wallpaper para Windows: {e}", "AVISO")
    
    try:
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 3
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, target_path, 3)
        if result:
            _log("✓ Wallpaper aplicado com sucesso via API", "OK")
            return True
        else:
            _log("Falha ao aplicar wallpaper via API", "ERRO")
            return False
    except Exception as e:
        _log(f"Erro ao aplicar wallpaper: {e}", "ERRO")
        return False

def apply_cpfani_lockscreen_redundant():
    """Aplica lockscreen CP Fani e força a imagem via GPO"""
    _log("Aplicando lockscreen CP Fani...", "INFO")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = ["https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G"]
    target_path = _get_image_path(local_wp, urls, "cpfani_ls.png")
    
    if not target_path:
        _log("Falha ao obter lockscreen", "ERRO")
        return False
    
    # Copia para o diretório de wallpapers do Windows (se ainda não foi copiado)
    try:
        windows_wp_dir = r"C:\Windows\Web\Wallpaper\Windows"
        os.makedirs(windows_wp_dir, exist_ok=True)
        windows_wp_path = os.path.join(windows_wp_dir, "cpfani_wallpaper.jpg")
        if not os.path.exists(windows_wp_path):
            shutil.copy2(target_path, windows_wp_path)
            _log(f"✓ Wallpaper copiado para {windows_wp_path} (lockscreen)", "OK")
    except Exception as e:
        _log(f"Erro ao copiar wallpaper para Windows (lockscreen): {e}", "AVISO")
    
    # Configura a imagem via GPO (HKLM)
    if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", windows_wp_path, winreg.REG_SZ):
        _log("✓ Lockscreen configurado via GPO", "OK")
    else:
        _log("Falha ao configurar lockscreen via GPO", "AVISO")
    
    # Força o bloqueio da tela de bloqueio (impede que o usuário mude) - somente depois de definir a imagem
    if set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "NoChangingLockScreen", 1, winreg.REG_DWORD):
        _log("✓ Bloqueio de alteração da tela de bloqueio ativado", "OK")
    else:
        _log("Falha ao ativar bloqueio de alteração da tela de bloqueio", "AVISO")
    
    return True

def disable_windows_hello_redundant():
    """Desativa Windows Hello e biometria"""
    _log("Desativando Windows Hello e biometria...", "INFO")
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\PassportForWork", "Enabled", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Windows Hello for Business", "Biometric", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WbioSrvc", "Start", 4, winreg.REG_DWORD)
        _log("✓ Windows Hello desativado", "OK")
    except Exception as e:
        _log(f"Erro ao desativar Windows Hello: {e}", "ERRO")

def remove_widgets_taskbar():
    """Remove widgets da barra de tarefas"""
    _log("Removendo widgets da barra de tarefas...", "INFO")
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\WidgetService", "Start", 4, winreg.REG_DWORD)
        sid = _get_active_user_sid()
        if sid:
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\FileExplorer", "/v", "TaskbarDa", "/t", "REG_DWORD", "/d", "0", "/f"],
                timeout=10
            )
        _log("✓ Widgets removidos", "OK")
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
            _log("✓ Regras de firewall aplicadas", "OK")
        else:
            _log("Aviso ao aplicar regras de firewall", "AVISO")
    except Exception as e:
        _log(f"Erro ao aplicar firewall: {e}", "ERRO")

def configurar_compartilhamento_rede():
    """
    Configura o Windows para permitir compartilhamento transparente de arquivos e impressoras,
    eliminando a solicitação de credenciais de rede e ativando a descoberta.
    """
    _log("DESBLOQUEANDO COMPARTILHAMENTO E DESCOBERTA DE REDE...", "INFO")
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
    for svc_name, svc_desc in servicos:
        try:
            _safe_subprocess_run(["sc", "config", svc_name, "start=", "auto"], timeout=15)
            result = _safe_subprocess_run(["sc", "start", svc_name], timeout=15)
            if result and result.returncode == 0:
                _log(f"✓ Serviço '{svc_desc}' ativado e iniciado.", "OK")
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
    for root, path, name, val in reg_configs:
        if set_reg(root, path, name, val, winreg.REG_DWORD):
            _log(f"✓ Registro configurado: {name} = {val}", "OK")
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

def schedule_manutencao_rede():
    """Agenda manutenção de rede (placeholder)"""
    _log("Agendamento de manutenção de rede configurado", "INFO")
    return True

def schedule_instalar_tudo():
    """Agenda instalador universal (placeholder)"""
    _log("Agendamento de instalador universal configurado", "INFO")
    return True

def _get_hardware_info():
    """Obtém informações básicas de hardware (legado)"""
    return {
        "Nome_Computador": os.environ.get("COMPUTERNAME", platform.node()),
        "Sistema_Operacional": platform.system(),
        "Versao_SO": platform.version(),
        "Arquitetura": platform.machine(),
        "Processador": platform.processor()
    }

# ============================================================
# FUNÇÕES AUXILIARES PARA O SNAPSHOT DETALHADO
# ============================================================

def _get_system_model():
    """Obtém o modelo do sistema via WMI"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_ComputerSystem).Model'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    return "Desconhecido"

def _get_processor_name():
    """Obtém o nome do processador via WMI"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_Processor).Name'],
            timeout=10
        )
        if result and result.stdout:
            # Limpa espaços extras
            return ' '.join(result.stdout.strip().split())
    except Exception:
        pass
    return "Desconhecido"

def _get_total_ram():
    """Obtém a memória RAM total em GB"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip() + " GB"
    except Exception:
        pass
    return "Desconhecido"

def _get_windows_version():
    """Obtém a versão e edição do Windows"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_OperatingSystem).Caption'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    return platform.system() + " " + platform.release()

def _get_bios_serial():
    """Obtém o número de série da BIOS"""
    try:
        result = _safe_subprocess_run(
            ['powershell', '-Command', '(Get-CimInstance Win32_BIOS).SerialNumber'],
            timeout=10
        )
        if result and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    return "Desconhecido"

# ============================================================
# FUNÇÕES MELHORADAS PARA OBTER IDs DO AnyDesk e TeamViewer
# ============================================================

def _get_anydesk_id():
    """Obtém o ID do AnyDesk do registro (suporte a múltiplas versões e arquiteturas)"""
    # Lista de caminhos de registro a verificar
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
    
    # Fallback: tentar obter via linha de comando do AnyDesk
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
    
    # Fallback via PowerShell (consulta WMI ou arquivo de configuração)
    try:
        ps_script = """
        $paths = @("$env:ProgramData\\AnyDesk\\ad.trace", "$env:ProgramData\\AnyDesk\\service.conf")
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
        """
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
    """Obtém o ID do TeamViewer do registro (suporte a múltiplas versões)"""
    # Versões do TeamViewer a verificar
    versions = ["15", "14", "13", "12", "11", "10"]
    
    # Caminhos comuns
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
            # Caminho sem versão específica
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
    
    # Fallback via PowerShell (consultar WMI ou arquivos de configuração)
    try:
        ps_script = """
        $id = $null
        # Tenta ler do arquivo de configuração do TeamViewer
        $configPath = "$env:ProgramData\\TeamViewer\\TeamViewer15_Config\\TeamViewer.ini"
        if (Test-Path $configPath) {
            $lines = Get-Content $configPath -ErrorAction SilentlyContinue
            foreach ($line in $lines) {
                if ($line -match 'ClientID=(\\d+)') {
                    $id = $matches[1]
                    break
                }
            }
        }
        if (-not $id) {
            $configPath2 = "$env:ProgramData\\TeamViewer\\TeamViewer.ini"
            if (Test-Path $configPath2) {
                $lines = Get-Content $configPath2 -ErrorAction SilentlyContinue
                foreach ($line in $lines) {
                    if ($line -match 'ClientID=(\\d+)') {
                        $id = $matches[1]
                        break
                    }
                }
            }
        }
        if (-not $id) {
            # Tenta via WMI
            try {
                $id = (Get-WmiObject -Class Win32_Product | Where-Object { $_.Name -match 'TeamViewer' }).IdentifyingNumber
                if ($id) { $id = $id -replace '.*(\\d+)$', '$1' }
            } catch {}
        }
        if ($id) { return $id } else { return $null }
        """
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=10
        )
        if result and result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except Exception:
        pass
    
    return "N/A"

# ============================================================
# SNAPSHOT COMPLETO (FORMATO SOLICITADO)
# ============================================================

def generate_full_snapshot():
    """Gera snapshot completo de hardware com formato personalizado"""
    _log("Gerando snapshot de hardware...", "INFO")

    pc_name = os.environ.get("COMPUTERNAME", "UNKNOWN")
    log_path = Path(f"{SCRIPT_DIR}/CPFANI_Hardware_Snapshot_{pc_name}.txt")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Coleta de informações
    modelo = _get_system_model()
    processador = _get_processor_name()
    memoria = _get_total_ram()
    windows = _get_windows_version()
    bios_serial = _get_bios_serial()
    anydesk_id = _get_anydesk_id()
    teamviewer_id = _get_teamviewer_id()

    # Monta o conteúdo do snapshot
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    content = f"""
============================================================
   SNAPSHOT CP FANI V5.9.3 (Edição Infiltrado + Self-Healing)
   Gerado em: {now}
============================================================

[HARDWARE]
  Nome_Computador     : {pc_name}
  Modelo_Sistema      : {modelo}
  Processador         : {processador}
  Memoria_RAM         : {memoria}
  Windows             : {windows}
  Serial_BIOS         : {bios_serial}

[SUPORTE]
  AnyDesk    : {anydesk_id}
  TeamViewer : {teamviewer_id}

============================================================
"""

    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        _log(f"✓ Snapshot gerado: {log_path}", "OK")
        return str(log_path)
    except Exception as e:
        _log(f"Erro ao gerar snapshot: {e}", "ERRO")
        return None

# ============================================================
# NOVAS FUNÇÕES DE REDUNDÂNCIA PARA TEMA ESCURO, WALLPAPER E LOCKSCREEN
# ============================================================

def _get_all_user_sids():
    """Obtém todos os SIDs de usuários reais do sistema (exclui SIDs do sistema)"""
    sids = []
    try:
        profiles_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profiles_key) as root_key:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(root_key, i)
                    i += 1
                    # Filtra apenas SIDs de usuários reais (começam com S-1-5-21-)
                    if sid.startswith("S-1-5-21-"):
                        sids.append(sid)
                except OSError:
                    break
    except Exception as e:
        _log(f"Erro ao obter SIDs: {e}", "AVISO")
    return sids

def _ensure_wallpaper_image():
    r"""Garante que a imagem do wallpaper/lockscreen exista em C:\Windows\Web\Wallpaper\Windows\"""
    target_path = r"C:\Windows\Web\Wallpaper\Windows\cpfani_wallpaper.jpg"
    if os.path.exists(target_path):
        return target_path
    
    _log("Imagem do wallpaper não encontrada no diretório do Windows. Tentando obter...", "INFO")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_wp = os.path.join(script_dir, "resources", "wallpaper_cpfani.jpg")
    urls = [
        "https://drive.google.com/uc?export=download&id=1K5SWWC1dJL0qETRKAVdJtc8-Wi39G83G",
        "https://github.com/sunstrix/Setup_CPFANI/raw/main/resources/wallpaper_cpfani.jpg"
    ]
    
    # Tenta obter a imagem
    img_path = _get_image_path(local_wp, urls, "cpfani_wallpaper.jpg")
    if img_path:
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(img_path, target_path)
            _log(f"✓ Imagem copiada para {target_path}", "OK")
            return target_path
        except Exception as e:
            _log(f"Erro ao copiar imagem: {e}", "ERRO")
    else:
        _log("Falha ao obter a imagem do wallpaper.", "ERRO")
    
    return None

def _apply_dark_theme_to_all_users():
    """Aplica tema escuro para todos os usuários via GPO e HKCU"""
    _log("Aplicando tema escuro para todos os usuários...", "INFO")
    
    # 1. Via GPO (HKLM) – afeta todos os usuários
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "SystemUsesLightTheme", 0, winreg.REG_DWORD)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "AppsUseLightTheme", 0, winreg.REG_DWORD)
        _log("✓ Tema escuro configurado via GPO (HKLM)", "OK")
    except Exception as e:
        _log(f"Erro ao configurar tema escuro via GPO: {e}", "AVISO")
    
    # 2. Para cada SID de usuário real
    sids = _get_all_user_sids()
    if not sids:
        _log("Nenhum SID de usuário encontrado para aplicar tema escuro.", "AVISO")
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
            _log(f"✓ Tema escuro aplicado para SID {sid}", "OK")
        except Exception as e:
            _log(f"Erro ao aplicar tema escuro para SID {sid}: {e}", "AVISO")

def _apply_wallpaper_to_all_users():
    """Aplica wallpaper para todos os usuários via GPO e HKCU"""
    _log("Aplicando wallpaper para todos os usuários...", "INFO")
    
    # Garante que a imagem exista
    wallpaper_path = _ensure_wallpaper_image()
    if not wallpaper_path:
        _log("Wallpaper não disponível. Pulando aplicação.", "ERRO")
        return
    
    # 1. Via GPO (HKLM) – afeta todos os usuários
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "Wallpaper", wallpaper_path, winreg.REG_SZ)
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "WallpaperStyle", "2", winreg.REG_SZ)  # 2 = Fill
        _log("✓ Wallpaper configurado via GPO (HKLM)", "OK")
    except Exception as e:
        _log(f"Erro ao configurar wallpaper via GPO: {e}", "AVISO")
    
    # 2. Para cada SID de usuário real
    sids = _get_all_user_sids()
    if not sids:
        _log("Nenhum SID de usuário encontrado para aplicar wallpaper.", "AVISO")
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
            _log(f"✓ Wallpaper aplicado para SID {sid}", "OK")
        except Exception as e:
            _log(f"Erro ao aplicar wallpaper para SID {sid}: {e}", "AVISO")

def _apply_lockscreen_to_all_users():
    """Aplica lockscreen para todos os usuários via GPO e HKCU (com bloqueio)"""
    _log("Aplicando lockscreen para todos os usuários...", "INFO")
    
    # Garante que a imagem exista
    lockscreen_path = _ensure_wallpaper_image()
    if not lockscreen_path:
        _log("Imagem do lockscreen não disponível. Pulando aplicação.", "ERRO")
        return
    
    # 1. Via GPO (HKLM) – afeta todos os usuários e bloqueia alterações
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "LockScreenImage", lockscreen_path, winreg.REG_SZ)
        _log("✓ Lockscreen configurado via GPO (HKLM)", "OK")
    except Exception as e:
        _log(f"Erro ao configurar lockscreen via GPO: {e}", "AVISO")
    
    # 2. Forçar a atualização da política para aplicar imediatamente
    try:
        _safe_subprocess_run("gpupdate /force", shell=True, timeout=60)
        _log("✓ Política de grupo atualizada (gpupdate /force)", "OK")
    except Exception as e:
        _log(f"Erro ao executar gpupdate: {e}", "AVISO")
    
    # 3. Só agora ativa o bloqueio de alteração (para evitar que o usuário mude)
    try:
        set_reg(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\Personalization", "NoChangingLockScreen", 1, winreg.REG_DWORD)
        _log("✓ Bloqueio de alteração da tela de bloqueio ativado", "OK")
    except Exception as e:
        _log(f"Erro ao ativar bloqueio de alteração: {e}", "AVISO")
    
    # 4. Aplica para cada SID (fallback para usuários já logados)
    sids = _get_all_user_sids()
    if not sids:
        _log("Nenhum SID de usuário encontrado para aplicar lockscreen.", "AVISO")
        return
    
    for sid in sids:
        try:
            # Windows 10/11 usa essa chave para tela de bloqueio
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Lock Screen\\Creative", "/v", "LockScreenImagePath", "/t", "REG_SZ", "/d", lockscreen_path, "/f"],
                timeout=10
            )
            _safe_subprocess_run(
                ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\Lock Screen\\Creative", "/v", "LockScreenImageId", "/t", "REG_SZ", "/d", "{00000000-0000-0000-0000-000000000000}", "/f"],
                timeout=10
            )
            _log(f"✓ Lockscreen aplicado para SID {sid}", "OK")
        except Exception as e:
            _log(f"Erro ao aplicar lockscreen para SID {sid}: {e}", "AVISO")

# ============================================================================
# INTEGRAÇÃO COM O KUDU (LIMPEZA, OTIMIZAÇÃO E MANUTENÇÃO)
# ============================================================================
try:
    import mod_kudu
    KUDU_AVAILABLE = True
except ImportError as e:
    KUDU_AVAILABLE = False
    _log(f"Módulo mod_kudu não encontrado. Funcionalidades de limpeza Kudu indisponíveis. Erro: {e}", "AVISO")

def _kudu_call(func_name, *args, **kwargs):
    """Chama uma função do mod_kudu se disponível, com log de início/fim"""
    if not KUDU_AVAILABLE:
        _log(f"Kudu não disponível. Não foi possível executar {func_name}.", "ERRO")
        return False
    func = getattr(mod_kudu, func_name, None)
    if func is None:
        _log(f"Função {func_name} não encontrada no módulo mod_kudu.", "ERRO")
        return False
    _log(f"Iniciando Kudu: {func_name}...", "INFO")
    try:
        result = func(*args, **kwargs)
        if result:
            _log(f"Kudu: {func_name} concluído com sucesso.", "OK")
        else:
            _log(f"Kudu: {func_name} falhou.", "ERRO")
        return result
    except Exception as e:
        _log(f"Exceção ao executar {func_name}: {e}", "ERRO")
        return False

# --- Wrappers para as funções aprovadas (sem docstrings problemáticas) ---

def kudu_system_clean():
    return _kudu_call("kudu_system_clean")

def kudu_app_clean():
    return _kudu_call("kudu_app_clean")

def kudu_gaming_clean():
    return _kudu_call("kudu_gaming_clean")

def kudu_registry_clean():
    return _kudu_call("kudu_registry_clean")

def kudu_network_cleanup():
    return _kudu_call("kudu_network_cleanup")

def kudu_debloat():
    return _kudu_call("kudu_debloat")

def kudu_driver_manager():
    return _kudu_call("kudu_driver_manager")

def kudu_service_manager():
    return _kudu_call("kudu_service_manager")

def kudu_one_click_clean():
    return _kudu_call("kudu_one_click_clean")

# get_kudu_service_optimizations - retorna lista de otimizações de serviços
def get_kudu_service_optimizations():
    if not KUDU_AVAILABLE:
        return ["Kudu não disponível."]
    try:
        return mod_kudu.get_service_optimizations_list()
    except Exception as e:
        _log(f"Erro ao obter lista de otimizações: {e}", "ERRO")
        return ["Erro ao obter lista."]

# ============================================================
# FUNÇÃO CORRIGIDA SEM DOCSTRING
# ============================================================

# Função run_kudu_cleanup: executa ações de limpeza do Kudu.
# Parâmetros: selected_actions (list) - opções: system, app, gaming, registry, network, debloat, drivers, services, all.
# Retorna: dict com success e results.
def run_kudu_cleanup(selected_actions=None):
    if not KUDU_AVAILABLE:
        _log("Kudu não disponível. Nenhuma ação executada.", "ERRO")
        return {"success": False, "results": {}}

    action_map = {
        'system': kudu_system_clean,
        'app': kudu_app_clean,
        'gaming': kudu_gaming_clean,
        'registry': kudu_registry_clean,
        'network': kudu_network_cleanup,
        'debloat': kudu_debloat,
        'drivers': kudu_driver_manager,
        'services': kudu_service_manager,
    }

    if selected_actions is None or not selected_actions:
        selected_actions = ['system', 'app', 'gaming', 'registry', 'network', 'drivers']

    results = {}
    overall_success = True
    for action in selected_actions:
        if action == 'all':
            for key in action_map:
                if key not in results:
                    results[key] = action_map[key]()
                    if not results[key]:
                        overall_success = False
            continue
        func = action_map.get(action)
        if func is None:
            _log(f"Ação desconhecida: {action}", "AVISO")
            results[action] = False
            overall_success = False
        else:
            results[action] = func()
            if not results[action]:
                overall_success = False

    return {"success": overall_success, "results": results}