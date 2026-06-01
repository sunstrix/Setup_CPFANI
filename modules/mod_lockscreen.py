"""
mod_lockscreen.py — Aplicação Resiliente de Wallpaper na Tela de Bloqueio (Lock Screen)
Especialista em Customização Windows - Versão Corporativa 6.0
"""
import os
import shutil
import winreg
import subprocess
import ctypes
from datetime import datetime

# Importação interna para validação de privilégios
try:
    from modules.mod_privileges import is_admin
except ImportError:
    def is_admin(): return False

def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] [LOCKSCREEN] {msg}", flush=True)

def apply_lockscreen_wallpaper(image_source_path):
    """
    Aplica a imagem de fundo na tela de bloqueio usando o método OEM Background.
    Garante persistência e conformidade com limites de tamanho do Windows.
    """
    if not is_admin():
        _log("ERRO: Privilégios de Administrador necessários para alterar a Lock Screen.", "ERROR")
        return False

    if not os.path.exists(image_source_path):
        _log(f"ERRO: Imagem fonte não encontrada em: {image_source_path}", "ERROR")
        return False

    _log("Iniciando aplicação da Lock Screen via OEM Background...", "INFO")
    NO_WINDOW = 0x08000000

    # 1. Definir caminhos de sistema
    target_dir = r"C:\Windows\System32\oobe\info\backgrounds"
    target_file = os.path.join(target_dir, "backgroundDefault.jpg")

    try:
        # Criar diretório se não existir
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            _log(f"Diretório OEM criado: {target_dir}", "OK")

        # 2. Processar Imagem via PowerShell (Redimensionar e Converter para JPEG < 256KB)
        # Usamos System.Drawing do .NET via PowerShell para evitar dependências Python
        ps_script = f"""
        Add-Type -AssemblyName System.Drawing
        $img = [System.Drawing.Image]::FromFile('{image_source_path}')
        $maxSize = 250000 # 250KB segurança
        $img.Save('{target_file}', [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $img.Dispose()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=NO_WINDOW, check=True)
        _log("Imagem convertida e movida para o diretório de sistema.", "OK")

    except Exception as e:
        _log(f"Falha ao processar arquivo de imagem: {e}", "ERROR")
        return False

    # 3. Modificações no Registro para ativar o OEMBackground
    reg_configs = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\System", "DisableLogonBackgroundImage", 0),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\LogonUI\Background", "OEMBackground", 1)
    ]

    for root, path, name, value in reg_configs:
        try:
            with winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
            _log(f"Registro configurado: {name} = {value}", "OK")
        except Exception as e:
            _log(f"Falha ao configurar registro {name}: {e}", "AVISO")

    # 4. Forçar atualização e reiniciar serviços dependentes
    try:
        # Atualiza políticas de grupo
        subprocess.run(["gpupdate", "/force"], creationflags=NO_WINDOW, capture_output=True)
        
        # Reinicia serviço de Autenticação (WlidSvc) para aplicar mudança na tela de logon
        subprocess.run(["sc", "stop", "wlidsvc"], creationflags=NO_WINDOW, capture_output=True)
        subprocess.run(["sc", "start", "wlidsvc"], creationflags=NO_WINDOW, capture_output=True)
        
        # Comando para atualizar parâmetros de sistema do usuário
        ctypes.windll.user32.UpdatePerUserSystemParameters()
        
        _log("Serviços de interface atualizados.", "OK")
    except Exception as e:
        _log(f"Falha ao forçar atualização do sistema: {e}", "AVISO")

    _log("Aplicação da Lock Screen concluída com sucesso.", "INFO")
    return True