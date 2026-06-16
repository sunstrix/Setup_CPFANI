"""gui.py — V5.9.5.2 (Edição CP Fani: Interface Estabilizada e Seletor Windows Hello)"""
import customtkinter as ctk
from tkinter import messagebox
import threading
import json
import os
import sys
import shutil
import subprocess
import urllib.request
import ssl
import re
import time
import traceback
import socket
import hashlib
import atexit
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO DE ENCODING PARA EVITAR CRASHES
# ============================================================
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors='replace')
        sys.stderr.reconfigure(encoding="utf-8", errors='replace')
    except Exception:
        pass

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[AVISO] PIL não encontrado. Logo não será exibido.", flush=True)

# ============================================================
# SISTEMA DE LOCK PARA PREVENIR EXECUÇÃO MÚLTIPLA
# ============================================================
LOCK_FILE = os.path.join(os.path.dirname(__file__), ".setup_lock")
LOCK_MAX_AGE_SECONDS = 300  # 5 minutos — lock órfão é considerado stale

def acquire_lock():
    """Adquire lock para prevenir execução múltipla. Detecta lock órfão por timestamp."""
    try:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read().strip().split('|')
                    pid = int(content[0])
                    lock_time = float(content[1]) if len(content) > 1 else 0
            except Exception:
                pid = 0
                lock_time = 0

            # Se o lock tem mais de 5 minutos, considera órfão
            if lock_time > 0 and (time.time() - lock_time) > LOCK_MAX_AGE_SECONDS:
                print(f"[AVISO] Lock órfão detectado (idade: {time.time() - lock_time:.0f}s). Substituindo.", flush=True)
            else:
                # Verifica se o processo ainda está ativo
                if sys.platform == "win32" and pid > 0:
                    try:
                        result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                            capture_output=True, text=True, timeout=5,
                            encoding='utf-8', errors='replace',
                            creationflags=0x08000000
                        )
                        if str(pid) in result.stdout:
                            return False, pid
                    except Exception:
                        pass

        # Cria lock file com PID e timestamp
        with open(LOCK_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{os.getpid()}|{time.time()}")
        atexit.register(release_lock)
        return True, os.getpid()
    except Exception as e:
        print(f"[AVISO] Falha ao adquirir lock: {e}", flush=True)
        return True, os.getpid()  # Continua mesmo se falhar

def release_lock():
    """Libera lock do arquivo com tratamento de permissão"""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except PermissionError:
        print("[AVISO] Sem permissão para remover lock file.", flush=True)
    except Exception:
        pass

# ============================================================
# SISTEMA DE NOTIFICAÇÃO WINDOWS (MANTIDO COM MELHORIAS)
# ============================================================
def show_windows_toast(title, message):
    """Exibe notificação nativa do Windows com escape XML completo"""
    # Escapa caracteres especiais para PowerShell E XML
    def _xml_escape(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    
    title_escaped = _xml_escape(title)
    message_escaped = _xml_escape(message)
    
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.ContentType = WindowsRuntime] | Out-Null

    $appId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
    $template = @"
    <toast>
        <visual>
            <binding template="ToastText02">
                <text id="1">{title_escaped}</text>
                <text id="2">{message_escaped}</text>
            </binding>
        </visual>
    </toast>
"@
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
    """
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"[AVISO] Falha ao exibir notificação: {e}", flush=True)

# ============================================================
# VALIDAÇÃO DE PRÉ-REQUISITOS (NOVO)
# ============================================================
def validate_prerequisites():
    """Valida pré-requisitos antes de iniciar o deploy"""
    errors = []
    warnings = []
    
    # 1. Verifica privilégios administrativos
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            errors.append("Privilégios administrativos necessários")
    except Exception as e:
        warnings.append(f"Falha ao verificar admin: {e}")
    
    # 2. Verifica conectividade com internet (HTTPS)
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
    except Exception:
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request("https://www.google.com", method="HEAD")
            urllib.request.urlopen(req, timeout=10, context=ctx)
        except Exception:
            errors.append("Sem conectividade com a internet")
    
    # 3. Verifica espaço em disco (mínimo 500MB) no disco C:
    try:
        free_space = shutil.disk_usage("C:\\").free
        if free_space < 500 * 1024 * 1024:
            errors.append(f"Espaço em disco insuficiente: {free_space / (1024*1024):.0f}MB disponíveis")
    except Exception as e:
        warnings.append(f"Falha ao verificar espaço em disco: {e}")
    
    # 4. Verifica versão do Python
    try:
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            errors.append(f"Python 3.8+ necessário (atual: {python_version.major}.{python_version.minor})")
    except Exception as e:
        warnings.append(f"Falha ao verificar versão do Python: {e}")
    
    # 5. Verifica se módulos existem
    required_modules = ['mod_config.py', 'mod_instalar.py']
    script_dir = os.path.dirname(__file__)
    for module in required_modules:
        if not os.path.exists(os.path.join(script_dir, module)):
            errors.append(f"Módulo obrigatório não encontrado: {module}")
    
    # 6. Verifica integridade dos módulos (NOVO)
    for module in required_modules:
        module_path = os.path.join(script_dir, module)
        if os.path.exists(module_path):
            try:
                size = os.path.getsize(module_path)
                if size < 100:
                    errors.append(f"Módulo {module} parece corrompido ({size} bytes)")
            except Exception as e:
                warnings.append(f"Falha ao verificar integridade de {module}: {e}")
    
    return errors, warnings

# ============================================================
# IMPORTAÇÃO DE MÓDULOS COM VALIDAÇÃO
# ============================================================
try:
    import mod_config
    import mod_instalar
    
    # Valida se módulos têm funções essenciais
    required_functions = {
        'mod_config': ['apply_cpfani_branding', 'apply_security_lgpd', 'apply_firewall_rules'],
        'mod_instalar': ['_choco_install', 'install_office_suite']
    }
    
    for module_name, functions in required_functions.items():
        module = sys.modules[module_name]
        for func in functions:
            if not hasattr(module, func):
                print(f"[AVISO] Função {func} não encontrada em {module_name}", flush=True)
    
except ImportError as e:
    print(f"[ERRO CRÍTICO] Falha ao importar módulos: {e}", flush=True)
    print("Certifique-se de que mod_config.py e mod_instalar.py estão no mesmo diretório.", flush=True)
    sys.exit(1)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

# ============================================================
# VALIDAÇÃO DE SCHEMA DO SETTINGS.JSON (NOVO)
# ============================================================
def validate_settings_schema(settings):
    """Valida estrutura do settings.json"""
    if not isinstance(settings, dict):
        return False, "Settings deve ser um dicionário"
    
    # Valida estrutura básica
    if 'apps' in settings:
        if not isinstance(settings['apps'], dict):
            return False, "'apps' deve ser um dicionário"
        if 'choco' in settings['apps']:
            if not isinstance(settings['apps']['choco'], list):
                return False, "'apps.choco' deve ser uma lista"
    
    if 'bloatware_remove' in settings:
        if not isinstance(settings['bloatware_remove'], list):
            return False, "'bloatware_remove' deve ser uma lista"
    
    return True, "OK"

def load_settings():
    """Carrega configurações do settings.json com fallback seguro"""
    # REMOVIDO: lightshot (mantido apenas flameshot)
    default_settings = {
        "apps": {
            "choco": ["googlechrome", "anydesk", "flameshot", "sharex", "7zip", "winrar"]
        },
        "bloatware_remove": ["Microsoft.ZuneVideo", "Microsoft.WindowsFeedbackHub"]
    }
    
    if not os.path.exists(SETTINGS_PATH):
        print(f"[INFO] settings.json não encontrado. Usando configurações padrão.", flush=True)
        return default_settings
    
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8", errors='replace') as f:
            settings = json.load(f)
            
            # Valida schema
            is_valid, message = validate_settings_schema(settings)
            if not is_valid:
                print(f"[ERRO] settings.json com schema inválido: {message}. Usando padrão.", flush=True)
                return default_settings
            
            print(f"[OK] Configurações carregadas de {SETTINGS_PATH}", flush=True)
            return settings
    except json.JSONDecodeError as e:
        print(f"[ERRO] settings.json corrompido: {e}. Usando padrão.", flush=True)
        return default_settings
    except Exception as e:
        print(f"[ERRO] Falha ao ler settings.json: {e}. Usando padrão.", flush=True)
        return default_settings

SETTINGS = load_settings()

# ============================================================
# SISTEMA DE BACKUP DE CONFIGURAÇÕES (NOVO)
# ============================================================
def backup_configurations():
    """Cria backup das configurações atuais antes de aplicar mudanças"""
    try:
        backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"settings_backup_{timestamp}.json")
        
        if os.path.exists(SETTINGS_PATH):
            shutil.copy2(SETTINGS_PATH, backup_file)
            print(f"[OK] Backup criado: {backup_file}", flush=True)
            return backup_file
        return None
    except Exception as e:
        print(f"[AVISO] Falha ao criar backup: {e}", flush=True)
        return None

class CPFani_GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Setup Automatizado CP Fani — V5.9.5.2")
        self.geometry("740x800")
        self.resizable(True, True)
        self.configure(fg_color="#121212")
        
        # ============================================================
        # VALIDAÇÃO DE LOCK (NOVO)
        # ============================================================
        self.lock_acquired, self.lock_pid = acquire_lock()
        if not self.lock_acquired:
            print(f"[ERRO] Outra instância já está executando (PID: {self.lock_pid})", flush=True)
            messagebox.showerror("Erro", f"Outra instância do setup já está executando.\nPID: {self.lock_pid}")
            sys.exit(1)
        
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # ============================================================
        # LOG DE VARIÁVEIS DE AMBIENTE (NOVO)
        # ============================================================
        self.log("=== VARIÁVEIS DE AMBIENTE ===", "INFO")
        self.log(f"Python: {sys.version}", "INFO")
        self.log(f"Plataforma: {sys.platform}", "INFO")
        self.log(f"Diretório: {os.path.dirname(__file__)}", "INFO")
        self.log(f"Usuário: {os.getenv('USERNAME', 'N/A')}", "INFO")
        self.log(f"Computador: {os.getenv('COMPUTERNAME', 'N/A')}", "INFO")
        self.log("=============================", "INFO")

    def _on_closing(self):
        """Tratamento seguro para fechamento da janela"""
        if messagebox.askokcancel("Sair", "Deseja realmente sair do setup?"):
            self.log("Interface fechada pelo usuário.", "INFO")
            release_lock()  # Libera lock ao fechar
            self.destroy()

    def _build_ui(self):
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header_frame.pack(pady=10, fill="x")
        
        if HAS_PIL:
            logo_path = os.path.join(os.path.dirname(__file__), "resources", "logo_cpfani.png")
            if os.path.exists(logo_path):
                try:
                    img = Image.open(logo_path)
                    logo_img = ctk.CTkImage(img, size=(160, 50)) 
                    logo_label = ctk.CTkLabel(header_frame, image=logo_img, text="")
                    logo_label.pack(pady=(0, 10))
                except Exception as e:
                    self.log(f"Aviso: Falha ao carregar logo: {e}", "AVISO")
            else:
                self.log(f"Aviso: Logo não encontrado em {logo_path}", "AVISO")
        
        ctk.CTkLabel(header_frame, text="SETUP AUTOMATIZADO CP FANI", font=("Segoe UI", 20, "bold"), text_color="#3a86ff").pack()
        ctk.CTkLabel(header_frame, text="v5.9.5.2  |  Gestão de Endpoints (Adaptação Dinâmica)", font=("Segoe UI", 11), text_color="#666666").pack()

        # 1. INTERFACE
        ui_frame = ctk.CTkFrame(self.main_scroll, fg_color="#1e1e1e", corner_radius=8)
        ui_frame.pack(padx=20, pady=5, fill="x")
        ctk.CTkLabel(ui_frame, text="1. Interface e Estética", font=("", 12, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.bar_var = ctk.StringVar(value="nenhum")
        ctk.CTkRadioButton(ui_frame, text="Manter Atual", variable=self.bar_var, value="nenhum").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkRadioButton(ui_frame, text="Esquerda", variable=self.bar_var, value="left").grid(row=1, column=1, padx=20, pady=5, sticky="w")
        ctk.CTkRadioButton(ui_frame, text="Centro", variable=self.bar_var, value="center").grid(row=1, column=2, padx=20, pady=5, sticky="w")

        # 2. SEGURANÇA
        sec_frame = ctk.CTkFrame(self.main_scroll, fg_color="#1e1e1e", corner_radius=8)
        sec_frame.pack(padx=20, pady=5, fill="x")
        ctk.CTkLabel(sec_frame, text="2. Segurança e Privacidade", font=("", 12, "bold")).pack(anchor="w", padx=10)
        
        self.sec_lgpd = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sec_frame, text="Políticas de Privacidade/LGPD + Sincronizar NTP.br", variable=self.sec_lgpd).pack(anchor="w", padx=10, pady=4)
        
        self.sec_hello = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sec_frame, text="Desabilitar Windows Hello, Biometria e Tela de Boas-Vindas", variable=self.sec_hello).pack(anchor="w", padx=10, pady=4)
        
        self.sec_firewall = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sec_frame, text="Firewall: Restringir SMB/RPC apenas à Rede Local (Whitelist)", variable=self.sec_firewall).pack(anchor="w", padx=10, pady=4)
        self.sec_bloatware = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sec_frame, text="Remoção Agressiva de Bloatware (AllUsers)", variable=self.sec_bloatware).pack(anchor="w", padx=10, pady=4)

        # 3. AUTOMAÇÃO LOGON
        tasks_frame = ctk.CTkFrame(self.main_scroll, fg_color="#1e1e1e", corner_radius=8)
        tasks_frame.pack(padx=20, pady=5, fill="x")
        ctk.CTkLabel(tasks_frame, text="3. Automação no Logon e Resiliência", font=("", 12, "bold")).pack(anchor="w", padx=10)
        self.task_manutencao = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tasks_frame, text="Agendar manutenção de rede (DHCP)", variable=self.task_manutencao).pack(anchor="w", padx=10, pady=2)
        self.task_instalar = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tasks_frame, text="Agendar atualizador de software", variable=self.task_instalar).pack(anchor="w", padx=10, pady=2)
        self.task_reinicio = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tasks_frame, text="Agendar Reinício Diário automático (21:00)", variable=self.task_reinicio).pack(anchor="w", padx=10, pady=2)
        self.task_watchdog = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tasks_frame, text='Ativar "Self-Healing" (Auto-Cura / Vigilância de Fundo)', variable=self.task_watchdog).pack(anchor="w", padx=10, pady=2)

        # 4. SOFTWARES E OFFICE
        sw_frame = ctk.CTkFrame(self.main_scroll, fg_color="#1e1e1e", corner_radius=8)
        sw_frame.pack(padx=20, pady=5, fill="x")
        
        sw_header = ctk.CTkFrame(sw_frame, fg_color="transparent")
        sw_header.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(sw_header, text="4. Softwares e Office", font=("", 12, "bold")).pack(side="left")
        
        btn_none = ctk.CTkButton(sw_header, text="Limpar Todos", font=("", 10), width=80, height=22, fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.select_none_apps)
        btn_none.pack(side="right", padx=2)
        btn_all = ctk.CTkButton(sw_header, text="Selecionar Todos", font=("", 10), width=95, height=22, fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.select_all_apps)
        btn_all.pack(side="right", padx=2)
        
        grid_frame = ctk.CTkFrame(sw_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)

        self.apps_to_install = SETTINGS.get("apps", {}).get("choco", [])
        self.app_vars = {}
        for i, app in enumerate(self.apps_to_install):
            v = ctk.BooleanVar(value=True)
            self.app_vars[app] = v
            ctk.CTkCheckBox(grid_frame, text=app.capitalize(), variable=v).grid(row=i//3, column=i%3, padx=10, pady=4, sticky="w")
            
        office_frame = ctk.CTkFrame(sw_frame, fg_color="transparent")
        office_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.office_var = ctk.StringVar(value="nenhum")
        ctk.CTkRadioButton(office_frame, text="Nenhum Office", variable=self.office_var, value="nenhum").grid(row=0, column=0, padx=10, sticky="w")
        ctk.CTkRadioButton(office_frame, text="Office 2021", variable=self.office_var, value="office2021").grid(row=0, column=1, padx=10, sticky="w")
        ctk.CTkRadioButton(office_frame, text="OnlyOffice", variable=self.office_var, value="onlyoffice").grid(row=0, column=2, padx=10, sticky="w")

        # 5. GESTÃO DE DRIVERS
        driver_frame = ctk.CTkFrame(self.main_scroll, fg_color="#1e1e1e", corner_radius=8)
        driver_frame.pack(padx=20, pady=5, fill="x")
        ctk.CTkLabel(driver_frame, text="5. Gestão de Drivers", font=("", 12, "bold")).pack(anchor="w", padx=10)
        self.driver_var = ctk.StringVar(value="nenhum")
        ctk.CTkRadioButton(driver_frame, text="Ignorar", variable=self.driver_var, value="nenhum").pack(anchor="w", padx=10, pady=2)
        ctk.CTkRadioButton(driver_frame, text="Fabricante (Dell/HP/Lenovo)", variable=self.driver_var, value="fabricante").pack(anchor="w", padx=10, pady=2)
        ctk.CTkRadioButton(driver_frame, text="Windows Update (Forçar Instalação)", variable=self.driver_var, value="wu").pack(anchor="w", padx=10, pady=2")

        # STATUS E PROGRESSO
        status_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        status_frame.pack(padx=20, pady=(10, 0), fill="x")
        
        self.status_label = ctk.CTkLabel(status_frame, text="A aguardar...", text_color="#00dd77", font=("", 12, "bold"))
        self.status_label.pack(side="left")
        
        self.progress_text = ctk.CTkLabel(status_frame, text="0%", font=("", 12, "bold"))
        self.progress_text.pack(side="right")

        self.progress = ctk.CTkProgressBar(self.main_scroll, mode="determinate", height=10, progress_color="#3a86ff")
        self.progress.pack(fill="x", padx=20, pady=5)
        self.progress.set(0)
        
        self.current_app_label = ctk.CTkLabel(self.main_scroll, text="", font=("", 11), text_color="#aaaaaa")
        self.current_app_label.pack(anchor="w", padx=20)

        self.log_area = ctk.CTkTextbox(self.main_scroll, fg_color="#0a0a0a", text_color="#00ff88", font=("Consolas", 11), height=120)
        self.log_area.pack(padx=20, pady=10, fill="both", expand=True)
        self.log_area.configure(state="disabled")

        self.btn_run = ctk.CTkButton(self.main_scroll, text="▶ EXECUTAR DEPLOY", font=("", 14, "bold"), height=40, command=self.start_deploy)
        self.btn_run.pack(pady=10, padx=20, fill="x")

    def select_all_apps(self):
        for var in self.app_vars.values():
            var.set(True)
        self.log("Todos os softwares foram marcados.")

    def select_none_apps(self):
        for var in self.app_vars.values():
            var.set(False)
        self.log("Todos os softwares foram desmarcados.")

    def log(self, msg, level="INFO"):
        """Sistema de log robusto com timestamp e nível"""
        ts = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{ts}] [{level}] {msg}"
        print(log_msg, flush=True)
        
        # Formatação colorida para a interface
        if level == "ERRO":
            formatted_msg = f"[{ts}] [ERRO] {msg}\n"
        elif level == "OK":
            formatted_msg = f"[{ts}] [OK] {msg}\n"
        elif level == "AVISO":
            formatted_msg = f"[{ts}] [AVISO] {msg}\n"
        else:
            formatted_msg = f"[{ts}] {msg}\n"
        
        self.after(0, self._log_safe, formatted_msg)

    def _log_safe(self, linha):
        """Inserção segura de log na interface"""
        try:
            self.log_area.configure(state="normal")
            self.log_area.insert("end", linha)
            self.log_area.see("end")
            self.log_area.configure(state="disabled")
        except Exception as e:
            print(f"[ERRO] Falha ao inserir log na UI: {e}", flush=True)

    def update_status(self, text, progress_value=None, current_app_text=None):
        """Atualiza status, progresso e aplicativo atual na interface"""
        try:
            self.status_label.configure(text=text)
            if progress_value is not None:
                progress_normalized = max(0, min(100, progress_value)) / 100
                self.progress.set(progress_normalized)
                self.progress_text.configure(text=f"{int(progress_value)}%")
            if current_app_text is not None:
                self.current_app_label.configure(text=current_app_text)
            self.update_idletasks()
        except Exception as e:
            self.log(f"Erro ao atualizar status: {e}", "ERRO")

    def _download_with_validation(self, url, dest_path, min_size_mb=1, max_retries=3, timeout=300, expected_checksum=None):
        """Download robusto com validação de tamanho, retry logic e SSL"""
        ssl_context = ssl.create_default_context()
        
        for attempt in range(1, max_retries + 1):
            try:
                self.log(f"Tentativa {attempt}/{max_retries}: Baixando {os.path.basename(dest_path)}...")
                
                # Cria diretório se não existir
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Download com timeout separado: connection=30s, read=timeout
                start_time = time.time()
                req = urllib.request.Request(url, method='GET')
                with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                    with open(dest_path, 'wb') as out_file:
                        shutil.copyfileobj(response, out_file)
                elapsed = time.time() - start_time
                
                # Validação de tamanho
                file_size = os.path.getsize(dest_path)
                min_size_bytes = min_size_mb * 1024 * 1024
                
                if file_size < min_size_bytes:
                    self.log(f"Arquivo muito pequeno ({file_size} bytes < {min_size_bytes} bytes). Removendo...", "AVISO")
                    os.remove(dest_path)
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    else:
                        return False
                
                # CÁLCULO E VALIDAÇÃO DE CHECKSUM
                self.log(f"Calculando checksum SHA256...")
                sha256_hash = hashlib.sha256()
                with open(dest_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                checksum = sha256_hash.hexdigest()
                
                if expected_checksum and checksum.lower() != expected_checksum.lower():
                    self.log(f"Checksum SHA256 NÃO corresponde! Esperado: {expected_checksum[:16]}... Obtido: {checksum[:16]}...", "ERRO")
                    os.remove(dest_path)
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    else:
                        return False
                
                self.log(f"SHA256: {checksum[:16]}...", "INFO")
                self.log(f"✓ Download concluído: {file_size / (1024*1024):.2f} MB em {elapsed:.1f}s", "OK")
                return True
                
            except Exception as e:
                self.log(f"Falha na tentativa {attempt}: {e}", "ERRO")
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except:
                        pass
                if attempt < max_retries:
                    time.sleep(3)
        
        return False

    def install_smart_flameshot(self):
        """Instalação inteligente do Flameshot comparando versões"""
        self.log("Analisando repositórios do Flameshot (Chocolatey vs GitHub v13.3.0)...")
        choco_version = "0.0.0"
        
        try:
            res = subprocess.run(
                ["choco", "info", "flameshot", "--limit-output"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
                encoding='utf-8',
                errors='replace'
            )
            if res.returncode == 0 and res.stdout:
                parts = res.stdout.strip().split('|')
                if len(parts) >= 2:
                    choco_version = parts[1]
                    self.log(f"Versão Chocolatey detectada: {choco_version}")
        except subprocess.TimeoutExpired:
            self.log("Timeout ao consultar Chocolatey. Continuando...", "AVISO")
        except Exception as e:
            self.log(f"Erro ao consultar Chocolatey: {e}", "AVISO")
        
        self.log(f"Disponível no Chocolatey: {choco_version}  |  Disponível no GitHub: 13.3.0")
        
        def _version_to_list(v_str):
            return [int(x) for x in re.findall(r'\d+', v_str)]
            
        v_choco = _version_to_list(choco_version) if choco_version != "0.0.0" else [0, 0, 0]
        v_github = [13, 3, 0]
        
        if v_github >= v_choco:
            self.log("A versão v13.3.0 do GitHub é a mais atual ou idêntica. Iniciando download via MSI...")
            msi_url = "https://github.com/flameshot-org/flameshot/releases/download/v13.3.0/Flameshot-13.3.0-win64.msi"
            temp_msi = r"C:\Users\Public\Downloads\Flameshot-13.3.0-win64.msi"
            
            if self._download_with_validation(msi_url, temp_msi, min_size_mb=5, max_retries=3):
                try:
                    self.log("Executando instalação silenciosa do MSI corporativo...")
                    install_res = subprocess.run(
                        ["msiexec", "/i", temp_msi, "/qn", "/norestart"],
                        capture_output=True,
                        timeout=120,
                        creationflags=0x08000000,
                        encoding='utf-8',
                        errors='replace'
                    )
                    
                    if install_res.returncode in [0, 3010]:
                        self.log("✓ Flameshot v13.3.0 instalado via GitHub MSI com sucesso.", "OK")
                        # Limpa arquivo temporário
                        try:
                            os.remove(temp_msi)
                        except:
                            pass
                        return True
                    else:
                        self.log(f"MSI retornou código {install_res.returncode}", "AVISO")
                except subprocess.TimeoutExpired:
                    self.log("Timeout na instalação do MSI", "ERRO")
                except Exception as e:
                    self.log(f"Erro na instalação do MSI: {e}", "ERRO")
                
                # Limpa arquivo em caso de erro
                try:
                    if os.path.exists(temp_msi):
                        os.remove(temp_msi)
                except:
                    pass
            
            self.log("Fallback: Instalando via Chocolatey...", "AVISO")
        else:
            self.log("O pacote do Chocolatey é mais recente. Direcionando para o gerenciador...")
            
        return mod_instalar._choco_install("flameshot")

    def start_deploy(self):
        """Inicia o processo de deploy com confirmação"""
        # VALIDAÇÃO DE PRÉ-REQUISITOS
        self.log("Validando pré-requisitos...")
        errors, warnings = validate_prerequisites()
        
        if warnings:
            for warning in warnings:
                self.log(f"⚠ {warning}", "AVISO")
        
        if errors:
            error_msg = "Pré-requisitos não atendidos:\n\n" + "\n".join(f"• {e}" for e in errors)
            self.log(f"ERRO: {error_msg}", "ERRO")
            messagebox.showerror("Erro de Pré-requisitos", error_msg)
            return
        
        self.log("✓ Todos os pré-requisitos atendidos", "OK")
        
        # BACKUP DE CONFIGURAÇÕES
        self.log("Criando backup de configurações...")
        backup_file = backup_configurations()
        if backup_file:
            self.log(f"✓ Backup criado: {os.path.basename(backup_file)}", "OK")
        
        if not messagebox.askyesno("Confirmar", "Iniciar provisionamento (Modo Infiltrado + Self-Healing)?"): 
            return
        
        self.btn_run.configure(state="disabled", text="⏳ EXECUTANDO...")
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")
        
        # Inicia thread com tratamento de exceções
        thread = threading.Thread(target=self._safe_work, daemon=True)
        thread.start()

    def _safe_work(self):
        """Wrapper seguro para _work com captura de exceções não tratadas"""
        try:
            self._work()
        except Exception as e:
            self.log(f"ERRO CRÍTICO NÃO TRATADO: {str(e)}", "ERRO")
            self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
            self.after(0, self._finalizar, ["Crítico-NãoTratado"])

    def _work(self):
        """Lógica principal de deploy com tratamento robusto de erros"""
        erros = []
        start_time = time.time()
        
        try:
            self.log("► Iniciando Deploy (Modo Infiltrado)...")
            self.log(f"Configurações carregadas: {len(SETTINGS.get('apps', {}).get('choco', []))} apps definidos")
            
            selected_apps = [app for app, v in self.app_vars.items() if v.get()]
            self.log(f"Aplicativos selecionados para instalação: {len(selected_apps)}")
            
            # Cálculo de tarefas totais
            total_tasks = 4  # Interface, Segurança, Agendamentos, Startup
            total_tasks += len(selected_apps)
            if self.office_var.get() != "nenhum": total_tasks += 1
            if self.driver_var.get() != "nenhum": total_tasks += 1
            if self.task_watchdog.get(): total_tasks += 1
            total_tasks += 1  # Snapshot
            
            completed = 0

            # 1. INTERFACE E BRANDING
            self.update_status("► Aplicando Interface e Branding...", (completed / total_tasks) * 100, "")
            try:
                self.log("Aplicando branding CP Fani...")
                result = mod_config.apply_cpfani_branding(self.bar_var.get())
                if result is False:
                    self.log("Função apply_cpfani_branding retornou False", "AVISO")
                self.log("✓ Branding aplicado com sucesso", "OK")
            except Exception as e:
                self.log(f"Falha ao aplicar branding: {e}", "ERRO")
                self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                erros.append("Branding")
            completed += 1

            # 2. SEGURANÇA E LGPD
            self.update_status("► Aplicando Segurança e LGPD...", (completed / total_tasks) * 100, "")
            try:
                self.log("Aplicando políticas de segurança...")
                result = mod_config.apply_security_lgpd(
                    apply_lgpd=self.sec_lgpd.get(),
                    disable_hello=self.sec_hello.get()
                )
                if result is False:
                    self.log("Função apply_security_lgpd retornou False", "AVISO")
                
                if self.sec_firewall.get():
                    self.log("Configurando regras de firewall...")
                    result = mod_config.apply_firewall_rules()
                    if result is False:
                        self.log("Função apply_firewall_rules retornou False", "AVISO")
                
                if self.sec_bloatware.get():
                    self.log("Removendo bloatware...")
                    result = mod_config.remove_agressive_bloatware(SETTINGS.get("bloatware_remove", []))
                    if result is False:
                        self.log("Função remove_agressive_bloatware retornou False", "AVISO")
                
                self.log("✓ Segurança aplicada com sucesso", "OK")
            except Exception as e:
                self.log(f"Falha ao aplicar segurança: {e}", "ERRO")
                self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                erros.append("Segurança")
            completed += 1

            # 3. AGENDAMENTOS
            self.update_status("► Agendando Tarefas...", (completed / total_tasks) * 100, "")
            try:
                self.log("Configurando agendamentos...")
                if self.task_reinicio.get():
                    self.log("Agendando reinício diário...")
                    result = mod_config.schedule_daily_reboot()
                    if result is False:
                        self.log("Função schedule_daily_reboot retornou False", "AVISO")
                if self.task_manutencao.get():
                    self.log("Agendando manutenção de rede...")
                    result = mod_config.schedule_manutencao_rede()
                    if result is False:
                        self.log("Função schedule_manutencao_rede retornou False", "AVISO")
                if self.task_instalar.get():
                    self.log("Agendando atualizador...")
                    result = mod_config.schedule_instalar_tudo()
                    if result is False:
                        self.log("Função schedule_instalar_tudo retornou False", "AVISO")
                self.log("✓ Agendamentos configurados", "OK")
            except Exception as e:
                self.log(f"Falha ao configurar agendamentos: {e}", "ERRO")
                self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                erros.append("Agendamentos")
            completed += 1
            
            # 4. SELF-HEALING
            if self.task_watchdog.get():
                self.update_status("► Instalando Motor de Auto-Cura...", (completed / total_tasks) * 100, "Injetando Watchdog...")
                try:
                    self.log("Configurando self-healing...")
                    result = mod_config.setup_self_healing()
                    if result is False:
                        self.log("Função setup_self_healing retornou False", "AVISO")
                    self.log("✓ Self-healing ativado", "OK")
                except Exception as e:
                    self.log(f"Falha ao configurar self-healing: {e}", "ERRO")
                    self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                    erros.append("Self-Healing")
                completed += 1

            # 5. INSTALAÇÃO DE SOFTWARES
            for idx, app in enumerate(selected_apps, 1):
                self.update_status(
                    f"► Instalando software ({idx}/{len(selected_apps)})",
                    (completed / total_tasks) * 100,
                    f"Processando {app.capitalize()}..."
                )
                
                try:
                    if app == "flameshot":
                        self.log(f"Instalando Flameshot (smart install)...")
                        success = self.install_smart_flameshot()
                    else:
                        self.log(f"Instalando {app} via Chocolatey...")
                        success = mod_instalar._choco_install(app)
                    
                    if success:
                        self.log(f"✓ {app.capitalize()} instalado com sucesso", "OK")
                    else:
                        self.log(f"✗ Falha ao instalar {app}", "ERRO")
                        erros.append(app)
                except Exception as e:
                    self.log(f"Erro crítico ao instalar {app}: {e}", "ERRO")
                    self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                    erros.append(app)
                
                completed += 1
            
            # 6. STARTUP GLOBAL
            self.update_status("► Configurando arranque global...", (completed / total_tasks) * 100, "Configurando ferramentas de suporte...")
            try:
                self.log("Configurando aplicativos de startup...")
                result = mod_config.set_apps_to_startup_all_users()
                if result is False:
                    self.log("Função set_apps_to_startup_all_users retornou False", "AVISO")
                self.log("✓ Startup configurado", "OK")
            except Exception as e:
                self.log(f"Falha ao configurar startup: {e}", "ERRO")
                self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                erros.append("Startup Global")
            completed += 1
            
            # 7. OFFICE
            if self.office_var.get() != "nenhum":
                self.update_status("► Instalando Office...", (completed / total_tasks) * 100, f"Instalando {self.office_var.get()}")
                try:
                    self.log(f"Instalando {self.office_var.get()}...")
                    success = mod_instalar.install_office_suite(self.office_var.get())
                    if not success:
                        self.log(f"Falha ao instalar {self.office_var.get()}", "ERRO")
                        erros.append("Office")
                    else:
                        self.log("✓ Office instalado", "OK")
                except Exception as e:
                    self.log(f"Erro ao instalar Office: {e}", "ERRO")
                    self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                    erros.append("Office")
                completed += 1

            # 8. DRIVERS
            if self.driver_var.get() != "nenhum":
                self.update_status("► Instalando Drivers...", (completed / total_tasks) * 100, f"Modo: {self.driver_var.get()}")
                try:
                    if self.driver_var.get() == "fabricante":
                        self.log("Instalando drivers do fabricante...")
                        success = mod_instalar.install_manufacturer_drivers(SETTINGS)
                        if not success:
                            self.log("Falha ao instalar drivers do fabricante", "ERRO")
                            erros.append("Drivers Fabricante")
                        else:
                            self.log("✓ Drivers do fabricante instalados", "OK")
                    elif self.driver_var.get() == "wu":
                        self.log("Forçando Windows Update para drivers...")
                        success = mod_instalar.force_windows_update_drivers()
                        if not success:
                            self.log("Falha ao forçar Windows Update", "ERRO")
                            erros.append("Windows Update")
                        else:
                            self.log("✓ Windows Update executado", "OK")
                except Exception as e:
                    self.log(f"Erro ao instalar drivers: {e}", "ERRO")
                    self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                    erros.append("Drivers")
                completed += 1

            # 9. SNAPSHOT
            self.update_status("► Gerando snapshot de hardware...", (completed / total_tasks) * 100, "")
            try:
                self.log("Gerando snapshot de hardware...")
                result = mod_config.generate_full_snapshot()
                if result is False:
                    self.log("Função generate_full_snapshot retornou False", "AVISO")
                self.log("✓ Snapshot gerado", "OK")
            except Exception as e:
                self.log(f"Falha ao gerar snapshot: {e}", "ERRO")
                self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
                erros.append("Snapshot")
            completed += 1

            elapsed_time = time.time() - start_time
            self.log(f"Deploy concluído em {elapsed_time:.1f} segundos")

        except Exception as e: 
            self.log(f"ERRO CRÍTICO: {str(e)}", "ERRO")
            self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
            erros.append("Crítico")
        finally: 
            self.after(0, self._finalizar, erros)

    def _finalizar(self, erros):
        """Finaliza o deploy e exibe resultados"""
        try:
            self.progress.set(1.0)
            self.progress_text.configure(text="100%")
            self.current_app_label.configure(text="")
            self.btn_run.configure(state="normal", text="▶ EXECUTAR DEPLOY")
            
            if erros:
                self.update_status(f"⚠ Concluído com {len(erros)} alerta(s)", 100)
                self.log(f"Deploy concluído com {len(erros)} erro(s): {', '.join(erros)}", "AVISO")
                show_windows_toast("Aviso no Provisionamento", f"Problemas com: {', '.join(erros)}.")
            else:
                self.update_status("✓ Setup finalizado com sucesso!", 100)
                self.log("✓ Deploy concluído sem erros!", "OK")
                show_windows_toast("CP Fani - Sucesso", "Provisionamento concluído com sucesso!")
                
            if messagebox.askyesno("Reiniciar Computador", "O provisionamento do computador foi concluído com sucesso.\n\nDeseja reiniciar o computador agora para aplicar todas as diretivas de teclado de forma definitiva?"):
                self.log("Forçando reinício imediato do sistema operacional...", "INFO")
                subprocess.Popen(
                    ["shutdown", "/r", "/t", "5", "/f"],
                    creationflags=0x08000000,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception as e:
            self.log(f"Erro ao finalizar: {e}", "ERRO")
            self.log(f"Stack trace: {traceback.format_exc()}", "ERRO")
        finally:
            # LIBERA LOCK AO FINALIZAR
            release_lock()

if __name__ == "__main__":
    try:
        Path(r"C:\Scripts\Logs").mkdir(parents=True, exist_ok=True)
        app = CPFani_GUI()
        app.mainloop()
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao iniciar interface: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        input("Pressione ENTER para sair...")
        sys.exit(1)
    finally:
        # Garante liberação do lock mesmo em crash não tratado
        release_lock()