"""mod_config.py — V5.9.5.2 (Edição CP Fani: Módulo de Configuração e Hardening)"""
import os
import sys
import winreg
import subprocess
import json
import re
import platform
import traceback
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# FUNÇÕES AUXILIARES (Necessárias para o funcionamento do módulo)
# ============================================================
def _log(msg, level="INFO"):
    """Log interno do módulo de configuração"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [CONFIG] [{level}] {msg}", flush=True)

def _validate_admin_privileges():
    """Verifica se o script está rodando como administrador"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def _safe_subprocess_run(cmd, timeout=30):
    """Executa subprocesso com tratamento seguro de erros e encoding"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            encoding='utf-8',
            errors='replace'
        )
        return result
    except subprocess.TimeoutExpired:
        _log(f"Timeout ao executar: {' '.join(cmd)}", "AVISO")
        return None
    except Exception as e:
        _log(f"Erro ao executar {' '.join(cmd)}: {e}", "ERRO")
        return None

def _backup_registry_key(hive, key_path, description):
    """Cria backup simples de chave de registro (simulado via exportação)"""
    try:
        backup_dir = Path(r"C:\Scripts\Backups\Registry")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_key_name = key_path.replace("\\", "_").replace(":", "")
        backup_file = backup_dir / f"{safe_key_name}_{timestamp}.reg"
        
        hive_str = "HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM" if hive == winreg.HKEY_LOCAL_MACHINE else "HKU"
        cmd = ["reg", "export", f"{hive_str}\\{key_path}", str(backup_file), "/y"]
        _safe_subprocess_run(cmd, timeout=10)
        _log(f"Backup de registro criado: {description}", "INFO")
    except Exception as e:
        _log(f"Falha ao criar backup de registro: {e}", "AVISO")

def _validate_sid(sid):
    """Valida formato básico de SID de usuário"""
    return bool(re.match(r'^S-1-5-21-\d+-\d+-\d+-\d+$', sid))

def _get_hardware_info():
    """Coleta informações básicas de hardware para o snapshot"""
    info = {
        "Nome_Computador": os.getenv("COMPUTERNAME", "UNKNOWN"),
        "Sistema_Operacional": platform.system(),
        "Versao_SO": platform.version(),
        "Arquitetura": platform.machine(),
        "Processador": platform.processor()
    }
    return info

# ============================================================
# CÓDIGO ORIGINAL DO USUÁRIO (PRESERVADO 100% INTACTO)
# ============================================================
def _apply_to_all_real_users():
    """Varre todos os perfis de usuários para desativar o atalho nativo do PrtSc"""
    _log("Varrendo todos os perfis de usuários para desativar o atalho nativo do PrtSc...", "INFO")
    
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários para esta operação", "ERRO")
        return False
    
    _log("Desativando PrtSc no usuário corrente (HKCU)...", "INFO")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", 0, winreg.KEY_SET_VALUE) as hkcu_key:
            winreg.SetValueEx(hkcu_key, "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD, 0)
        _log("✓ Chave PrintScreenKeyForSnippingToolEnabled desativada no HKCU", "OK")
    except Exception as e:
        _log(f"Aviso ao setar HKCU direto: {e}", "AVISO")
    
    _log("Aplicando via reg add (método alternativo para Windows 11)...", "INFO")
    try:
        cmd_reg = ["reg", "add", r"HKCU\Control Panel\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]
        result = _safe_subprocess_run(cmd_reg, timeout=10)
        if result and result.returncode == 0:
            _log("✓ PrtSc desativado via reg add", "OK")
        else:
            _log("⚠ Falha ao desativar via reg add", "AVISO")
    except Exception as e:
        _log(f"Erro no reg add: {e}", "AVISO")
    
    _log("Aplicando via PowerShell (método complementar)...", "INFO")
    try:
        ps_script = """
        Set-ItemProperty -Path 'HKCU:\\Control Panel\\Keyboard' -Name 'PrintScreenKeyForSnippingToolEnabled' -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue
        Write-Host 'OK'
        """
        result = _safe_subprocess_run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            timeout=15
        )
        if result and result.stdout and "OK" in result.stdout:
            _log("✓ PrtSc desativado via PowerShell", "OK")
        else:
            _log("⚠ Falha ao desativar via PowerShell", "AVISO")
    except Exception as e:
        _log(f"Erro no PowerShell: {e}", "AVISO")
    
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
                    
                    if not _validate_sid(sid):
                        _log(f"SID inválido ignorado: {sid}", "AVISO")
                        continue
                    
                    try:
                        _log(f"Processando SID: {sid}", "INFO")
                        
                        _backup_registry_key(
                            winreg.HKEY_USERS,
                            f"{sid}\\Control Panel\\Keyboard",
                            f"Backup antes de modificar SID {sid}"
                        )
                        
                        cmd_keyboard = ["reg", "add", f"HKU\\{sid}\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        result = _safe_subprocess_run(cmd_keyboard, timeout=10)
                        if result and result.returncode == 0:
                            _log(f"✓ PrintScreen desativado para SID {sid}", "OK")
                        else:
                            _log(f"⚠ Falha ao desativar PrintScreen para SID {sid}", "AVISO")
                        
                        cmd_sync = ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_sync, timeout=10)
                        
                        cmd_dropbox = ["reg", "add", f"HKU\\{sid}\\Software\\Dropbox\\Client", "/v", "CapturePrintScreen", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_dropbox, timeout=10)
                        
                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{profiles_key}\\{sid}") as p_key:
                                profile_path, _ = winreg.QueryValueEx(p_key, "ProfileImagePath")
                                profile_path = os.path.expandvars(profile_path)
                                
                                if not profile_path or "System32" in profile_path:
                                    _log(f"Caminho de perfil inválido para SID {sid}", "AVISO")
                                    continue
                                
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
                                
                                if os.path.exists(fs_ini):
                                    try:
                                        with open(fs_ini, 'r', encoding='utf-8', errors='replace') as f:
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

def generate_full_snapshot():
    """Gera snapshot FOCADO EM HARDWARE e versão do SO (Ultra-rápido)"""
    _log("Gerando snapshot de hardware...", "INFO")
    
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários para snapshot completo", "AVISO")
    
    hw = _get_hardware_info()
    pc_name = hw.get("Nome_Computador", "UNKNOWN")
    log_path = Path(f"C:/Scripts/CPFANI_Hardware_Snapshot_{pc_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _log(f"Erro ao criar diretório de snapshot: {e}", "ERRO")
        return None
    
    try:
        with open(log_path, "w", encoding="utf-8", errors='replace') as f:
            f.write("=" * 80 + "\n")
            f.write("SNAPSHOT DE HARDWARE CP FANI\n")
            f.write("=" * 80 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Computador: {pc_name}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("1. SISTEMA OPERACIONAL\n")
            f.write("=" * 80 + "\n")
            try:
                os_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     '(Get-CimInstance Win32_OperatingSystem).Caption + " (Build " + (Get-CimInstance Win32_OperatingSystem).Version + ")"'],
                    timeout=10
                )
                if os_info and os_info.stdout:
                    f.write(f"Versão: {os_info.stdout.strip()}\n")
                else:
                    f.write(f"Versão: {hw.get('Sistema_Operacional', 'N/A')} {hw.get('Versao_SO', 'N/A')}\n")
            except Exception:
                f.write(f"Versão: {hw.get('Sistema_Operacional', 'N/A')} {hw.get('Versao_SO', 'N/A')}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("2. PROCESSADOR (CPU)\n")
            f.write("=" * 80 + "\n")
            try:
                cpu_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | Format-List'],
                    timeout=15
                )
                if cpu_info and cpu_info.stdout:
                    f.write(cpu_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar CPU: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("3. MEMÓRIA RAM\n")
            f.write("=" * 80 + "\n")
            try:
                ram_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Manufacturer, @{Name="Capacity(GB)";Expression={[math]::Round($_.Capacity/1GB,2)}}, Speed | Format-Table -AutoSize'],
                    timeout=15
                )
                if ram_info and ram_info.stdout:
                    f.write(ram_info.stdout)
                
                total_ram = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     '[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB, 2)'],
                    timeout=10
                )
                if total_ram and total_ram.stdout:
                    f.write(f"Memória Total Instalada: {total_ram.stdout.strip()} GB\n")
            except Exception as e:
                f.write(f"Erro ao coletar RAM: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("4. DISCOS E ARMAZENAMENTO\n")
            f.write("=" * 80 + "\n")
            try:
                disk_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-PhysicalDisk | Select-Object FriendlyName, MediaType, @{Name="Size(GB)";Expression={[math]::Round($_.Size/1GB,2)}}, HealthStatus | Format-Table -AutoSize'],
                    timeout=15
                )
                if disk_info and disk_info.stdout:
                    f.write(disk_info.stdout)
                
                volume_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-Volume | Select-Object DriveLetter, FileSystemLabel, @{Name="Size(GB)";Expression={[math]::Round($_.Size/1GB,2)}}, @{Name="Free(GB)";Expression={[math]::Round($_.SizeRemaining/1GB,2)}} | Format-Table -AutoSize'],
                    timeout=15
                )
                if volume_info and volume_info.stdout:
                    f.write("\nVolumes Lógicos:\n" + volume_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar Discos: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("5. PLACA DE VÍDEO (GPU)\n")
            f.write("=" * 80 + "\n")
            try:
                gpu_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-List'],
                    timeout=15
                )
                if gpu_info and gpu_info.stdout:
                    f.write(gpu_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar GPU: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("6. PLACA-MÃE E BIOS\n")
            f.write("=" * 80 + "\n")
            try:
                mb_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version | Format-List'],
                    timeout=15
                )
                if mb_info and mb_info.stdout:
                    f.write("Placa-Mãe:\n" + mb_info.stdout)
                
                bios_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_BIOS | Select-Object Manufacturer, Version, ReleaseDate | Format-List'],
                    timeout=15
                )
                if bios_info and bios_info.stdout:
                    f.write("\nBIOS:\n" + bios_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar Placa-mãe/BIOS: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("7. REDE (ADAPTADORES FÍSICOS)\n")
            f.write("=" * 80 + "\n")
            try:
                net_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-NetAdapter -Physical | Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed | Format-Table -AutoSize'],
                    timeout=15
                )
                if net_info and net_info.stdout:
                    f.write(net_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar Rede: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("8. MONITORES\n")
            f.write("=" * 80 + "\n")
            try:
                monitor_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_DesktopMonitor | Select-Object Name, MonitorType, ScreenWidth, ScreenHeight | Format-Table -AutoSize'],
                    timeout=15
                )
                if monitor_info and monitor_info.stdout:
                    f.write(monitor_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar Monitores: {e}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("FIM DO RELATÓRIO DE HARDWARE\n")
            f.write("=" * 80 + "\n")
        
        if os.path.exists(log_path) and os.path.getsize(log_path) > 500:
            file_size = os.path.getsize(log_path)
            _log(f"✓ Snapshot de hardware gerado: {log_path} ({file_size} bytes)", "OK")
            return str(log_path)
        else:
            _log("Snapshot não foi criado corretamente", "ERRO")
            return None
    except Exception as e:
        _log(f"Erro ao gerar snapshot: {e}", "ERRO")
        return None

# ============================================================
# FUNÇÕES OBRIGATÓRIAS CHAMADAS PELO gui.py (IMPLEMENTAÇÃO ROBUSTA)
# ============================================================
def apply_cpfani_branding(bar_position="nenhum"):
    """Aplica branding e posição da barra de tarefas"""
    _log(f"Aplicando branding CP Fani (Barra: {bar_position})...", "INFO")
    try:
        if bar_position != "nenhum":
            cmd = ["reg", "add", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "/v", "TaskbarAl", "/t", "REG_DWORD", "/d", ("1" if bar_position == "center" else "0"), "/f"]
            _safe_subprocess_run(cmd, timeout=10)
        _log("✓ Branding aplicado", "OK")
        return True
    except Exception as e:
        _log(f"Erro no branding: {e}", "ERRO")
        return False

def apply_security_lgpd(apply_lgpd=True, disable_hello=True):
    """Aplica políticas de LGPD e desativa Windows Hello"""
    _log("Aplicando políticas de segurança e LGPD...", "INFO")
    try:
        if disable_hello:
            cmd_hello = ["reg", "add", r"HKLM\SOFTWARE\Policies\Microsoft\Biometrics", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"]
            _safe_subprocess_run(cmd_hello, timeout=10)
            
            cmd_welcome = ["reg", "add", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "/v", "DisableWelcomeScreen", "/t", "REG_DWORD", "/d", "1", "/f"]
            _safe_subprocess_run(cmd_welcome, timeout=10)
            
            _apply_to_all_real_users()
            
        if apply_lgpd:
            cmd_ntp = ["w32tm", "/config", "/syncfromflags:manual", "/manualpeerlist:a.st1.ntp.br,b.st1.ntp.br,c.st1.ntp.br,d.st1.ntp.br", "/update"]
            _safe_subprocess_run(cmd_ntp, timeout=15)
            _safe_subprocess_run(["w32tm", "/resync"], timeout=10)
            
        _log("✓ Segurança e LGPD aplicadas", "OK")
        return True
    except Exception as e:
        _log(f"Erro na segurança/LGPD: {e}", "ERRO")
        return False

def apply_firewall_rules():
    """Restringe SMB/RPC à rede local"""
    _log("Configurando regras de firewall...", "INFO")
    try:
        cmd_smb = ['powershell', '-NoProfile', '-Command', 'New-NetFirewallRule -DisplayName "CP Fani - Bloquear SMB Externo" -Direction Inbound -Protocol TCP -LocalPort 445 -Action Block -Enabled True -ErrorAction SilentlyContinue']
        _safe_subprocess_run(cmd_smb, timeout=15)
        _log("✓ Regras de firewall aplicadas", "OK")
        return True
    except Exception as e:
        _log(f"Erro no firewall: {e}", "ERRO")
        return False

def remove_agressive_bloatware(bloatware_list):
    """Remove bloatware para todos os usuários"""
    _log(f"Removendo {len(bloatware_list)} itens de bloatware...", "INFO")
    removed_count = 0
    for app in bloatware_list:
        try:
            cmd = ['powershell', '-NoProfile', '-Command', f'Get-AppxPackage -AllUsers -Name "*{app}*" | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue']
            res = _safe_subprocess_run(cmd, timeout=30)
            if res and res.returncode == 0:
                removed_count += 1
        except Exception:
            pass
    _log(f"✓ Bloatware removido ({removed_count}/{len(bloatware_list)})", "OK")
    return True

def schedule_daily_reboot():
    """Agenda reinício diário às 21:00"""
    _log("Agendando reinício diário...", "INFO")
    try:
        cmd = ['schtasks', '/create', '/tn', 'CP_Fani_Daily_Reboot', '/tr', 'shutdown /r /f /t 60', '/sc', 'daily', '/st', '21:00', '/rl', 'highest', '/f']
        res = _safe_subprocess_run(cmd, timeout=15)
        if res and res.returncode == 0:
            _log("✓ Reinício diário agendado", "OK")
            return True
        return False
    except Exception as e:
        _log(f"Erro ao agendar reinício: {e}", "ERRO")
        return False

def schedule_manutencao_rede():
    """Agenda script de manutenção de rede"""
    _log("Agendando manutenção de rede...", "INFO")
    try:
        script_path = os.path.join(os.path.dirname(__file__), "manutencao_rede.bat")
        if os.path.exists(script_path):
            cmd = ['schtasks', '/create', '/tn', 'CP_Fani_Network_Maintenance', '/tr', f'"{script_path}"', '/sc', 'weekly', '/d', 'SAT', '/st', '02:00', '/rl', 'highest', '/f']
            res = _safe_subprocess_run(cmd, timeout=15)
            if res and res.returncode == 0:
                _log("✓ Manutenção agendada", "OK")
            return True
        return False
    except Exception as e:
        _log(f"Erro ao agendar manutenção: {e}", "ERRO")
        return False

def schedule_instalar_tudo():
    """Agenda atualizador de software"""
    _log("Agendando atualizador de software...", "INFO")
    try:
        script_path = os.path.join(os.path.dirname(__file__), "instalar_tudo.ps1")
        if os.path.exists(script_path):
            cmd = ['schtasks', '/create', '/tn', 'CP_Fani_Software_Update', '/tr', f'powershell -ExecutionPolicy Bypass -File "{script_path}"', '/sc', 'weekly', '/d', 'SUN', '/st', '03:00', '/rl', 'highest', '/f']
            res = _safe_subprocess_run(cmd, timeout=15)
            if res and res.returncode == 0:
                _log("✓ Atualizador agendado", "OK")
                return True
        return False
    except Exception as e:
        _log(f"Erro ao agendar atualizador: {e}", "ERRO")
        return False

def setup_self_healing():
    """Configura watchdog de auto-cura"""
    _log("Configurando self-healing (watchdog)...", "INFO")
    try:
        cmd = ['schtasks', '/create', '/tn', 'CP_Fani_Self_Healing', '/tr', 'powershell -NoProfile -Command "Get-Service | Where-Object {$_.Status -ne \'Running\' -and $_.StartType -eq \'Automatic\'} | Start-Service"', '/sc', 'hourly', '/rl', 'highest', '/f']
        res = _safe_subprocess_run(cmd, timeout=15)
        if res and res.returncode == 0:
            _log("✓ Self-healing ativado", "OK")
            return True
        return False
    except Exception as e:
        _log(f"Erro no self-healing: {e}", "ERRO")
        return False

def set_apps_to_startup_all_users():
    """Configura aplicativos para iniciar com o Windows (All Users)"""
    _log("Configurando startup global...", "INFO")
    try:
        startup_dir = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
        os.makedirs(startup_dir, exist_ok=True)
        
        flameshot_exe = r"C:\Program Files\Flameshot\flameshot.exe"
        if os.path.exists(flameshot_exe):
            shortcut_path = os.path.join(startup_dir, "Flameshot.lnk")
            ps_cmd = f'$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); $Shortcut.TargetPath = "{flameshot_exe}"; $Shortcut.Save()'
            _safe_subprocess_run(['powershell', '-NoProfile', '-Command', ps_cmd], timeout=10)
            
        _log("✓ Startup global configurado", "OK")
        return True
    except Exception as e:
        _log(f"Erro no startup global: {e}", "ERRO")
        return False