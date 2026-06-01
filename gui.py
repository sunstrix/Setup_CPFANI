"""
gui.py — Interface Gráfica Profissional Setup CP Fani
Engenheiro Sênior: Gemini & Sunstrix — Versão 6.0.0.0

Instruções de Instalação:
    pip install customtkinter pillow loguru

Instruções para gerar Executável (PyInstaller):
    pyinstaller --onefile --windowed --uac-admin --icon=app.ico --add-data "config_version.json;." --add-data "settings.json;." gui.py
"""

import os
import sys
import json
import threading
import subprocess
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image

# Tenta importar módulos de backend. Se falhar, usa placeholders para manter integridade.
try:
    from modules.mod_privileges import is_admin, elevate_process, run_as_admin_task
    from modules.mod_config import apply_cpfani_branding, remove_agressive_bloatware, apply_security_lgpd, setup_self_healing, apply_firewall_rules
    from modules.mod_network import configure_network_sharing
    from modules.mod_lockscreen import apply_lockscreen_wallpaper
    from modules.mod_instalar import install_office_redundant, install_onlyoffice_redundant
except ImportError:
    # Placeholders para evitar crash caso módulos não estejam na pasta /modules
    def is_admin(): return False
    def elevate_process(): pass
    def _log(m, l): print(f"[{l}] {m}")

# Configurações Globais de Design
ctk.set_appearance_mode("System")  # Mantém sincronia com Windows (Dark/Light)
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Carregar Configurações ---
        self.settings_path = Path("settings.json")
        self.config_v_path = Path("config_version.json")
        self.load_configs()

        # --- Janela Principal ---
        self.title(f"CP Fani - Setup Corporativo Automático")
        self.geometry("950x720")
        self.minsize(850, 650)
        
        # --- Variáveis de Controle ---
        self.is_running = False
        self.stop_event = threading.Event()
        self.admin_status = is_admin()
        
        # Layout de Grid (Sidebar + Main)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_panel()
        self.setup_log_panel()

        self.update_admin_indicator()

    def load_configs(self):
        """Carrega arquivos JSON com fallbacks robustos."""
        default_settings = {
            "user_preferences": {"theme": "dark", "taskbar_alignment": "left"},
            "automation_settings": {"apply_lgpd_policies": True}
        }
        try:
            if self.settings_path.exists():
                self.settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
            else:
                self.settings = default_settings
            
            if self.config_v_path.exists():
                self.config_v = json.loads(self.config_v_path.read_text(encoding="utf-8"))
            else:
                self.config_v = {"project_info": {"version": "6.0.0.0"}}
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")
            self.settings = default_settings

    def setup_sidebar(self):
        """Constrói a barra lateral de status e opções globais."""
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CP FANI", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=(20, 10))
        
        self.version_label = ctk.CTkLabel(self.sidebar_frame, text=f"v{self.config_v['project_info']['version']}", font=ctk.CTkFont(size=12))
        self.version_label.pack(pady=(0, 20))

        # Indicador de Privilégios
        self.admin_indicator = ctk.CTkLabel(self.sidebar_frame, text="MODO USUÁRIO", fg_color="transparent", text_color="#fbc02d")
        self.admin_indicator.pack(pady=10, padx=20, fill="x")

        self.btn_elevate = ctk.CTkButton(self.sidebar_frame, text="Elevar para Admin", command=self.request_elevation, 
                                        fg_color="#d32f2f", hover_color="#b71c1c")
        if not self.admin_status:
            self.btn_elevate.pack(pady=10, padx=20)

        # Seletor de Tema
        self.theme_label = ctk.CTkLabel(self.sidebar_frame, text="Tema da Interface:", anchor="w")
        self.theme_label.pack(pady=(20, 0), padx=20, fill="x")
        self.theme_option = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"], command=self.change_appearance_mode)
        self.theme_option.pack(pady=10, padx=20)

    def setup_main_panel(self):
        """Painel central com a lista de tarefas (Checkboxes)."""
        self.main_frame = ctk.CTkScrollableFrame(self, label_text="Painel de Tarefas Disponíveis")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 20), pady=(20, 10))

        # Dicionário de tarefas vinculadas a flags
        self.task_vars = {}
        tasks = [
            ("instalar_python", "Instalar Python (se ausente)", True),
            ("instalar_office", "Instalar MS Office 365 (Redundante)", True),
            ("instalar_onlyoffice", "Instalar OnlyOffice Desktop", False),
            ("remover_bloatware", "Remover Apps Indesejados (Bloatware)", True),
            ("config_rede", "Configurar Rede Local e Impressoras", True),
            ("wallpaper_desktop", "Aplicar Wallpaper da Empresa", True),
            ("wallpaper_lock", "Aplicar Wallpaper na Tela de Bloqueio", True),
            ("firewall_hardening", "Aplicar Regras de Firewall (Segurança)", True),
            ("self_healing", "Ativar Cão de Guarda (Watchdog)", True)
        ]

        for key, label, default in tasks:
            var = tk.BooleanVar(value=default)
            cb = ctk.CTkCheckBox(self.main_frame, text=label, variable=var)
            cb.pack(anchor="w", padx=20, pady=10)
            self.task_vars[key] = var

    def setup_log_panel(self):
        """Área inferior para barra de progresso e terminal de log."""
        self.bottom_frame = ctk.CTkFrame(self, height=250)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=(10, 20))

        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=(10, 5))
        self.progress_bar.set(0)

        self.log_area = ctk.CTkTextbox(self.bottom_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_area.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tags de cores para o log
        self.log_area._textbox.tag_config("INFO", foreground="#2196f3")
        self.log_area._textbox.tag_config("SUCCESS", foreground="#4caf50")
        self.log_area._textbox.tag_config("WARNING", foreground="#ffeb3b")
        self.log_area._textbox.tag_config("ERROR", foreground="#f44336")

        self.btn_run = ctk.CTkButton(self.bottom_frame, text="EXECUTAR TAREFAS SELECIONADAS", 
                                    height=40, font=ctk.CTkFont(size=14, weight="bold"),
                                    command=self.start_execution_thread)
        self.btn_run.pack(side="right", padx=20, pady=10)

        self.btn_cancel = ctk.CTkButton(self.bottom_frame, text="Cancelar", command=self.cancel_tasks,
                                       fg_color="gray", state="disabled")
        self.btn_cancel.pack(side="right", padx=10, pady=10)

    # --- Lógica de Interface ---

    def write_log(self, message, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{ts}] ", "DEFAULT")
        self.log_area.insert("end", f"[{level}] {message}\n", level)
        self.log_area.see("end")

    def update_admin_indicator(self):
        if self.admin_status:
            self.admin_indicator.configure(text="MODO ADMINISTRADOR", text_color="#66bb6a")
        else:
            self.admin_indicator.configure(text="MODO USUÁRIO (LIMITADO)", text_color="#ffa726")

    def change_appearance_mode(self, mode):
        ctk.set_appearance_mode(mode)
        self.settings["user_preferences"]["theme"] = mode.lower()
        self.save_settings()

    def save_settings(self):
        self.settings_path.write_text(json.dumps(self.settings, indent=4), encoding="utf-8")

    def request_elevation(self):
        if elevate_process():
            self.destroy()

    # --- Lógica de Execução Assíncrona ---

    def start_execution_thread(self):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.btn_run.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        threading.Thread(target=self.task_engine, daemon=True).start()

    def cancel_tasks(self):
        self.stop_event.set()
        self.write_log("Solicitando cancelamento das tarefas...", "WARNING")

    def task_engine(self):
        """Motor principal que itera sobre as tarefas selecionadas."""
        selected_tasks = [k for k, v in self.task_vars.items() if v.get()]
        total = len(selected_tasks)
        if total == 0:
            self.write_log("Nenhuma tarefa selecionada.", "WARNING")
            self.finish_execution()
            return

        for i, task_key in enumerate(selected_tasks):
            if self.stop_event.is_set():
                self.write_log("Processo interrompido pelo usuário.", "ERROR")
                break
            
            progress = (i + 1) / total
            self.after(0, lambda p=progress: self.progress_bar.set(p))

            # Execução Dinâmica
            self.execute_single_task(task_key)

        self.write_log("=== Ciclo de Configuração Finalizado ===", "SUCCESS")
        self.after(0, self.finish_execution)

    def execute_single_task(self, key):
        """Mapeia chaves da UI para funções reais de backend."""
        self.write_log(f"Iniciando: {key.replace('_', ' ').title()}...", "INFO")
        
        try:
            if key == "instalar_office":
                install_office_redundant()
            elif key == "instalar_onlyoffice":
                install_onlyoffice_redundant()
            elif key == "config_rede":
                if self.admin_status: configure_network_sharing()
                else: self.write_log("Pulei Rede: Requer Admin", "WARNING")
            elif key == "wallpaper_desktop":
                apply_cpfani_branding(self.settings["user_preferences"]["taskbar_alignment"])
            elif key == "wallpaper_lock":
                # Assume que a imagem já foi baixada pelo mod_config
                img_path = r"C:\Scripts\Resources\lockscreen.jpg"
                if os.path.exists(img_path): apply_lockscreen_wallpaper(img_path)
            elif key == "remover_bloatware":
                remove_agressive_bloatware(self.config_v["software_lists"]["bloatware_to_remove"])
            elif key == "firewall_hardening":
                apply_firewall_rules()
            elif key == "self_healing":
                setup_self_healing()
            
            self.write_log(f"Tarefa {key} concluída.", "SUCCESS")
        except Exception as e:
            self.write_log(f"Erro em {key}: {str(e)}", "ERROR")

    def finish_execution(self):
        self.is_running = False
        self.btn_run.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        messagebox.showinfo("Sucesso", "Todas as tarefas foram processadas. Verifique o log para detalhes.")

if __name__ == "__main__":
    app = App()
    app.mainloop()