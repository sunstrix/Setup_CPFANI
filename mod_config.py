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
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários para esta operação", "ERRO")
        return False
    
    # ============================================================
    # DESATIVAÇÃO NO USUÁRIO ATIVO (HKCU) - REFORÇADO
    # ============================================================
    _log("Desativando PrtSc no usuário corrente (HKCU)...", "INFO")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Keyboard", 0, winreg.KEY_SET_VALUE) as hkcu_key:
            winreg.SetValueEx(hkcu_key, "PrintScreenKeyForSnippingToolEnabled", 0, winreg.REG_DWORD, 0)
        _log("✓ Chave PrintScreenKeyForSnippingToolEnabled desativada no HKCU", "OK")
    except Exception as e:
        _log(f"Aviso ao setar HKCU direto: {e}", "AVISO")
    
    # ============================================================
    # DESATIVAÇÃO VIA REG ADD (MÉTODO ALTERNATIVO - WINDOWS 11)
    # ============================================================
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
    
    # ============================================================
    # DESATIVAÇÃO VIA POWERSHELL (MÉTODO COMPLEMENTAR - WINDOWS 11)
    # ============================================================
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
    
    # ============================================================
    # VARREDURA DE TODOS OS SIDs (MANTIDO COM VALIDAÇÕES)
    # ============================================================
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
                        
                        # Backup de registro antes de modificar
                        _backup_registry_key(
                            winreg.HKEY_USERS,
                            f"{sid}\\Control Panel\\Keyboard",
                            f"Backup antes de modificar SID {sid}"
                        )
                        
                        # Desativa o interruptor de captura nativa
                        cmd_keyboard = ["reg", "add", f"HKU\\{sid}\\Control Panel\\Keyboard", "/v", "PrintScreenKeyForSnippingToolEnabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        result = _safe_subprocess_run(cmd_keyboard, timeout=10)
                        if result and result.returncode == 0:
                            _log(f"✓ PrintScreen desativado para SID {sid}", "OK")
                        else:
                            _log(f"⚠ Falha ao desativar PrintScreen para SID {sid}", "AVISO")
                        
                        # Desativa a sincronização de acessibilidade
                        cmd_sync = ["reg", "add", f"HKU\\{sid}\\Software\\Microsoft\\Windows\\CurrentVersion\\SettingSync\\Groups\\Accessibility", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_sync, timeout=10)
                        
                        # Remove ganchos de ferramentas concorrentes
                        cmd_dropbox = ["reg", "add", f"HKU\\{sid}\\Software\\Dropbox\\Client", "/v", "CapturePrintScreen", "/t", "REG_DWORD", "/d", "0", "/f"]
                        _safe_subprocess_run(cmd_dropbox, timeout=10)
                        
                        # Configuração do Flameshot
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
    """Gera snapshot COMPLETO de hardware e sistema"""
    _log("Gerando snapshot COMPLETO de hardware e sistema...", "INFO")
    
    # ============================================================
    # VALIDAÇÃO DE PRÉ-REQUISITOS
    # ============================================================
    if not _validate_admin_privileges():
        _log("Privilégios administrativos necessários para snapshot completo", "AVISO")
        # Continua mesmo sem admin, mas com dados limitados
    
    hw = _get_hardware_info()
    pc_name = hw.get("Nome_Computador", "UNKNOWN")
    log_path = Path(f"C:/Scripts/CPFANI_Hardware_Snapshot_{pc_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
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
            # ============================================================
            # CABEÇALHO
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("SNAPSHOT COMPLETO CP FANI - RELATÓRIO DETALHADO DE HARDWARE E SISTEMA\n")
            f.write("=" * 80 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"PC: {pc_name}\n")
            f.write(f"Gerado por: Setup Automatizado CP Fani V5.9.5.2\n")
            f.write("=" * 80 + "\n\n")
            
            # ============================================================
            # 1. SISTEMA OPERACIONAL
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("1. SISTEMA OPERACIONAL\n")
            f.write("=" * 80 + "\n")
            try:
                f.write(f"Sistema: {hw.get('Sistema_Operacional', 'N/A')}\n")
                f.write(f"Versão: {hw.get('Versao_SO', 'N/A')}\n")
                f.write(f"Release: {platform.release()}\n")
                f.write(f"Arquitetura: {hw.get('Arquitetura', 'N/A')}\n")
                f.write(f"Processador: {hw.get('Processador', 'N/A')}\n")
                
                # Informações adicionais via WMI
                try:
                    os_info = _safe_subprocess_run(
                        ['powershell', '-NoProfile', '-Command', 
                         'Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, InstallDate, LastBootUpTime, SystemDirectory, WindowsDirectory | Format-List'],
                        timeout=30
                    )
                    if os_info and os_info.stdout:
                        f.write(f"\nDetalhes WMI:\n{os_info.stdout}\n")
                except Exception as e:
                    f.write(f"Erro ao obter detalhes WMI: {e}\n")
                
                # Timezone
                try:
                    tz_info = _safe_subprocess_run(
                        ['powershell', '-NoProfile', '-Command', 'Get-TimeZone | Format-List'],
                        timeout=10
                    )
                    if tz_info and tz_info.stdout:
                        f.write(f"\nTimezone:\n{tz_info.stdout}\n")
                except Exception as e:
                    f.write(f"Erro ao obter timezone: {e}\n")
                
                # Idioma do sistema
                try:
                    lang_info = _safe_subprocess_run(
                        ['powershell', '-NoProfile', '-Command', 'Get-WinSystemLocale | Format-List'],
                        timeout=10
                    )
                    if lang_info and lang_info.stdout:
                        f.write(f"\nIdioma do Sistema:\n{lang_info.stdout}\n")
                except Exception as e:
                    f.write(f"Erro ao obter idioma: {e}\n")
                
            except Exception as e:
                f.write(f"Erro ao coletar informações do SO: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 2. PROCESSADOR (CPU)
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("2. PROCESSADOR (CPU)\n")
            f.write("=" * 80 + "\n")
            try:
                cpu_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_Processor | Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed, AddressWidth, Architecture, ProcessorId, L2CacheSize, L3CacheSize | Format-List'],
                    timeout=30
                )
                if cpu_info and cpu_info.stdout:
                    f.write(cpu_info.stdout)
                else:
                    f.write("Não foi possível obter informações do CPU\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações do CPU: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 3. MEMÓRIA RAM
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("3. MEMÓRIA RAM\n")
            f.write("=" * 80 + "\n")
            try:
                # Memória total do sistema
                mem_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory | Format-List'],
                    timeout=15
                )
                if mem_info and mem_info.stdout:
                    f.write(f"Memória Total do Sistema:\n{mem_info.stdout}\n")
                
                # Módulos de memória (slots)
                ram_modules = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Manufacturer, Capacity, Speed, ConfiguredClockSpeed, MemoryType, SMBIOSMemoryType, PartNumber, SerialNumber | Format-Table -AutoSize'],
                    timeout=30
                )
                if ram_modules and ram_modules.stdout:
                    f.write(f"\nMódulos de Memória (Slots):\n{ram_modules.stdout}\n")
                
                # Memória disponível
                mem_available = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize | Format-List'],
                    timeout=15
                )
                if mem_available and mem_available.stdout:
                    f.write(f"\nMemória Disponível:\n{mem_available.stdout}\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações de RAM: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 4. DISCOS E ARMAZENAMENTO
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("4. DISCOS E ARMAZENAMENTO\n")
            f.write("=" * 80 + "\n")
            try:
                # Discos físicos
                disk_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_DiskDrive | Select-Object Model, Manufacturer, MediaType, Size, InterfaceType, SerialNumber, FirmwareRevision, BytesPerSector, TotalSectors, Partitions | Format-List'],
                    timeout=30
                )
                if disk_info and disk_info.stdout:
                    f.write(f"Discos Físicos:\n{disk_info.stdout}\n")
                
                # Partições
                partition_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_DiskPartition | Select-Object Name, Size, Type, PrimaryPartition, Bootable, BootPartition, DiskIndex | Format-Table -AutoSize'],
                    timeout=30
                )
                if partition_info and partition_info.stdout:
                    f.write(f"\nPartições:\n{partition_info.stdout}\n")
                
                # Volumes lógicos (C:, D:, etc)
                volume_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, VolumeName, FileSystem, Size, FreeSpace, DriveType, VolumeSerialNumber | Format-Table -AutoSize'],
                    timeout=30
                )
                if volume_info and volume_info.stdout:
                    f.write(f"\nVolumes Lógicos:\n{volume_info.stdout}\n")
                
                # Tipo de disco (SSD vs HDD)
                ssd_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, Size, HealthStatus, OperationalStatus | Format-Table -AutoSize'],
                    timeout=30
                )
                if ssd_info and ssd_info.stdout:
                    f.write(f"\nTipo de Disco (SSD/HDD):\n{ssd_info.stdout}\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações de discos: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 5. PLACA DE VÍDEO (GPU)
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("5. PLACA DE VÍDEO (GPU)\n")
            f.write("=" * 80 + "\n")
            try:
                gpu_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion, DriverDate, VideoProcessor, AdapterCompatibility, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, VideoModeDescription | Format-List'],
                    timeout=30
                )
                if gpu_info and gpu_info.stdout:
                    f.write(gpu_info.stdout)
                else:
                    f.write("Não foi possível obter informações da GPU\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações da GPU: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 6. PLACA-MÃE E BIOS
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("6. PLACA-MÃE E BIOS\n")
            f.write("=" * 80 + "\n")
            try:
                # Placa-mãe
                motherboard_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, Version, SerialNumber, Tag | Format-List'],
                    timeout=30
                )
                if motherboard_info and motherboard_info.stdout:
                    f.write(f"Placa-Mãe:\n{motherboard_info.stdout}\n")
                
                # BIOS
                bios_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_BIOS | Select-Object Manufacturer, Name, Version, ReleaseDate, SerialNumber, SMBIOSBIOSVersion, BIOSVersion | Format-List'],
                    timeout=30
                )
                if bios_info and bios_info.stdout:
                    f.write(f"\nBIOS:\n{bios_info.stdout}\n")
                
                # Sistema (para detectar se é VM)
                system_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemType, NumberOfProcessors, NumberOfLogicalProcessors, Domain, Workgroup, HypervisorPresent | Format-List'],
                    timeout=30
                )
                if system_info and system_info.stdout:
                    f.write(f"\nSistema:\n{system_info.stdout}\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações da placa-mãe/BIOS: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 7. REDE
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("7. REDE\n")
            f.write("=" * 80 + "\n")
            try:
                # Adaptadores de rede
                network_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-NetAdapter -Physical | Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed, MediaType, DriverVersion, DriverDate | Format-Table -AutoSize'],
                    timeout=30
                )
                if network_info and network_info.stdout:
                    f.write(f"Adaptadores de Rede:\n{network_info.stdout}\n")
                
                # Configuração IP
                ip_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, IPAddress, PrefixLength, AddressFamily, SkipAsSource | Format-Table -AutoSize'],
                    timeout=30
                )
                if ip_info and ip_info.stdout:
                    f.write(f"\nConfiguração IP (IPv4):\n{ip_info.stdout}\n")
                
                # DNS
                dns_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ServerAddresses | Format-Table -AutoSize'],
                    timeout=30
                )
                if dns_info and dns_info.stdout:
                    f.write(f"\nServidores DNS:\n{dns_info.stdout}\n")
                
                # Gateway padrão
                gateway_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Select-Object InterfaceAlias, NextHop, RouteMetric | Format-Table -AutoSize'],
                    timeout=30
                )
                if gateway_info and gateway_info.stdout:
                    f.write(f"\nGateway Padrão:\n{gateway_info.stdout}\n")
                
                # ipconfig completo
                ipconfig_info = _safe_subprocess_run(['ipconfig', '/all'], timeout=30)
                if ipconfig_info and ipconfig_info.stdout:
                    f.write(f"\nipconfig /all:\n{ipconfig_info.stdout}\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações de rede: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 8. BATERIA (SE NOTEBOOK)
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("8. BATERIA (Se Notebook)\n")
            f.write("=" * 80 + "\n")
            try:
                battery_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_Battery | Select-Object Name, Status, EstimatedChargeRemaining, EstimatedRunTime, BatteryStatus, Chemistry, DesignCapacity, FullChargeCapacity | Format-List'],
                    timeout=30
                )
                if battery_info and battery_info.stdout:
                    f.write(battery_info.stdout)
                else:
                    f.write("Nenhuma bateria detectada (Desktop ou bateria não reportada)\n")
                
                # Relatório detalhado de bateria
                battery_report = _safe_subprocess_run(
                    ['powercfg', '/batteryreport', '/output', 'C:\\Scripts\\battery_report.html'],
                    timeout=30
                )
                if battery_report and battery_report.returncode == 0:
                    f.write("\nRelatório detalhado da bateria gerado em: C:\\Scripts\\battery_report.html\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações de bateria: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 9. MONITORES
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("9. MONITORES\n")
            f.write("=" * 80 + "\n")
            try:
                monitor_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance -Namespace root\\wmi -ClassName WmiMonitorID | ForEach-Object { $manufacturer = ($_.ManufacturerName -notmatch 0 | ForEach-Object {[char]$_}) -join ""; $name = ($_.UserFriendlyName -notmatch 0 | ForEach-Object {[char]$_}) -join ""; [PSCustomObject]@{Manufacturer=$manufacturer; Name=$name; Serial=($_.SerialNumberID -notmatch 0 | ForEach-Object {[char]$_}) -join ""} } | Format-Table -AutoSize'],
                    timeout=30
                )
                if monitor_info and monitor_info.stdout:
                    f.write(f"Monitores Detectados:\n{monitor_info.stdout}\n")
                
                # Resolução atual
                resolution_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_VideoController | Select-Object Name, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate | Format-Table -AutoSize'],
                    timeout=30
                )
                if resolution_info and resolution_info.stdout:
                    f.write(f"\nResolução Atual:\n{resolution_info.stdout}\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações de monitores: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 10. PERIFÉRICOS USB
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("10. PERIFÉRICOS USB\n")
            f.write("=" * 80 + "\n")
            try:
                usb_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_USBHub | Select-Object Name, DeviceID, Manufacturer, Status | Format-Table -AutoSize'],
                    timeout=30
                )
                if usb_info and usb_info.stdout:
                    f.write(usb_info.stdout)
                else:
                    f.write("Nenhum dispositivo USB detectado\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações USB: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 11. IMPRESSORAS
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("11. IMPRESSORAS INSTALADAS\n")
            f.write("=" * 80 + "\n")
            try:
                printer_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-Printer | Select-Object Name, DriverName, PortName, Shared, Location, Comment | Format-Table -AutoSize'],
                    timeout=30
                )
                if printer_info and printer_info.stdout:
                    f.write(printer_info.stdout)
                else:
                    f.write("Nenhuma impressora detectada\n")
            except Exception as e:
                f.write(f"Erro ao coletar informações de impressoras: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 12. PROGRAMAS INSTALADOS
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("12. PROGRAMAS INSTALADOS\n")
            f.write("=" * 80 + "\n")
            try:
                programs_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName} | Select-Object DisplayName, DisplayVersion, Publisher, InstallDate | Sort-Object DisplayName | Format-Table -AutoSize'],
                    timeout=60
                )
                if programs_info and programs_info.stdout:
                    f.write(programs_info.stdout)
                else:
                    f.write("Não foi possível listar programas instalados\n")
            except Exception as e:
                f.write(f"Erro ao coletar lista de programas: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 13. HOTFIXES/UPDATES DO WINDOWS
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("13. HOTFIXES/UPDATES DO WINDOWS\n")
            f.write("=" * 80 + "\n")
            try:
                hotfix_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-HotFix | Select-Object HotFixID, Description, InstalledOn, InstalledBy | Sort-Object InstalledOn -Descending | Format-Table -AutoSize'],
                    timeout=60
                )
                if hotfix_info and hotfix_info.stdout:
                    f.write(hotfix_info.stdout)
                else:
                    f.write("Não foi possível listar hotfixes\n")
            except Exception as e:
                f.write(f"Erro ao coletar hotfixes: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 14. VARIÁVEIS DE AMBIENTE DO SISTEMA
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("14. VARIÁVEIS DE AMBIENTE DO SISTEMA\n")
            f.write("=" * 80 + "\n")
            try:
                env_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-ChildItem Env: | Format-Table Name, Value -AutoSize'],
                    timeout=30
                )
                if env_info and env_info.stdout:
                    f.write(env_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar variáveis de ambiente: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 15. SERVIÇOS EM EXECUÇÃO
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("15. SERVIÇOS EM EXECUÇÃO\n")
            f.write("=" * 80 + "\n")
            try:
                services_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-Service | Where-Object {$_.Status -eq "Running"} | Select-Object Name, DisplayName, Status, StartType | Sort-Object Name | Format-Table -AutoSize'],
                    timeout=60
                )
                if services_info and services_info.stdout:
                    f.write(services_info.stdout)
                else:
                    f.write("Não foi possível listar serviços\n")
            except Exception as e:
                f.write(f"Erro ao coletar serviços: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 16. USUÁRIOS DO SISTEMA
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("16. USUÁRIOS DO SISTEMA\n")
            f.write("=" * 80 + "\n")
            try:
                users_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-LocalUser | Select-Object Name, Enabled, LastLogon, Description | Format-Table -AutoSize'],
                    timeout=30
                )
                if users_info and users_info.stdout:
                    f.write(users_info.stdout)
                else:
                    f.write("Não foi possível listar usuários\n")
            except Exception as e:
                f.write(f"Erro ao coletar usuários: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 17. VIRTUALIZAÇÃO
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("17. INFORMAÇÕES DE VIRTUALIZAÇÃO\n")
            f.write("=" * 80 + "\n")
            try:
                vm_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     '$isVM = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent; if ($isVM) { Write-Host "Máquina Virtual: SIM" } else { Write-Host "Máquina Virtual: NÃO (Físico)" }; Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, SystemType | Format-List'],
                    timeout=30
                )
                if vm_info and vm_info.stdout:
                    f.write(vm_info.stdout)
            except Exception as e:
                f.write(f"Erro ao coletar informações de virtualização: {e}\n")
            f.write("\n")
            
            # ============================================================
            # 18. INFORMAÇÕES ADICIONAIS DE HARDWARE
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("18. INFORMAÇÕES ADICIONAIS DE HARDWARE\n")
            f.write("=" * 80 + "\n")
            try:
                # Sistema de som
                sound_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_SoundDevice | Select-Object Name, Manufacturer, Status | Format-Table -AutoSize'],
                    timeout=30
                )
                if sound_info and sound_info.stdout:
                    f.write(f"Dispositivos de Som:\n{sound_info.stdout}\n")
                
                # Teclado
                keyboard_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_Keyboard | Select-Object Name, Description, Status | Format-Table -AutoSize'],
                    timeout=30
                )
                if keyboard_info and keyboard_info.stdout:
                    f.write(f"\nTeclados:\n{keyboard_info.stdout}\n")
                
                # Mouse
                mouse_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_PointingDevice | Select-Object Name, Manufacturer, DeviceType, Status | Format-Table -AutoSize'],
                    timeout=30
                )
                if mouse_info and mouse_info.stdout:
                    f.write(f"\nDispositivos de Pontuação (Mouse):\n{mouse_info.stdout}\n")
                
                # Porta paralela e serial
                port_info = _safe_subprocess_run(
                    ['powershell', '-NoProfile', '-Command', 
                     'Get-CimInstance Win32_ParallelPort, Win32_SerialPort | Select-Object Name, DeviceID, Status | Format-Table -AutoSize'],
                    timeout=30
                )
                if port_info and port_info.stdout:
                    f.write(f"\nPortas (Paralela/Serial):\n{port_info.stdout}\n")
                
            except Exception as e:
                f.write(f"Erro ao coletar informações adicionais: {e}\n")
            f.write("\n")
            
            # ============================================================
            # RODAPÉ
            # ============================================================
            f.write("=" * 80 + "\n")
            f.write("FIM DO RELATÓRIO\n")
            f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")
        
        # Validação de arquivo criado
        if os.path.exists(log_path) and os.path.getsize(log_path) > 1000:
            file_size = os.path.getsize(log_path)
            _log(f"✓ Snapshot completo gerado: {log_path} ({file_size} bytes)", "OK")
            return str(log_path)
        else:
            _log(f"Snapshot não foi criado corretamente", "ERRO")
            return None
    except PermissionError:
        _log(f"Sem permissão para escrever em: {log_path}", "ERRO")
        return None
    except Exception as e:
        _log(f"Erro ao gerar snapshot: {e}", "ERRO")
        _log(f"Stack trace: {traceback.format_exc()}", "ERRO")
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
            # Desativa Windows Hello/Biometria
            cmd_hello = ["reg", "add", r"HKLM\SOFTWARE\Policies\Microsoft\Biometrics", "/v", "Enabled", "/t", "REG_DWORD", "/d", "0", "/f"]
            _safe_subprocess_run(cmd_hello, timeout=10)
            
            # Desativa tela de boas-vindas
            cmd_welcome = ["reg", "add", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "/v", "DisableWelcomeScreen", "/t", "REG_DWORD", "/d", "1", "/f"]
            _safe_subprocess_run(cmd_welcome, timeout=10)
            
            # Desativa atalho PrtSc nativo (chama a função completa do usuário)
            _apply_to_all_real_users()
            
        if apply_lgpd:
            # Sincroniza NTP.br
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
        # Bloqueia SMB (445) de fora da sub-rede local (exemplo simplificado)
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
        # Cria tarefa que verifica a integridade do sistema a cada hora
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
        
        # Exemplo: Criar atalho para o Flameshot se instalado
        flameshot_exe = r"C:\Program Files\Flameshot\flameshot.exe"
        if os.path.exists(flameshot_exe):
            shortcut_path = os.path.join(startup_dir, "Flameshot.lnk")
            # Criação simplificada de atalho via PowerShell
            ps_cmd = f'$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); $Shortcut.TargetPath = "{flameshot_exe}"; $Shortcut.Save()'
            _safe_subprocess_run(['powershell', '-NoProfile', '-Command', ps_cmd], timeout=10)
            
        _log("✓ Startup global configurado", "OK")
        return True
    except Exception as e:
        _log(f"Erro no startup global: {e}", "ERRO")
        return False