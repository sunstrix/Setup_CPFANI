"""
Interface Gráfica Profissional para Setup CPFANI - Midnight Chrome Edition
Versão: 6.0.0.0
Dependências: pip install customtkinter pillow
Gerar executável: pyinstaller --onefile --windowed --uac-admin --icon=app.ico gui.py
"""

import os
import sys
import json
import threading
import subprocess
import ctypes
import time
from datetime import datetime
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image

# --- TENTATIVA DE IMPORTAÇÃO DOS MÓDULOS DE BACKEND ---
# Caso o arquivo seja executado isoladamente, os fallbacks garantem que a UI funcione.
try:
    from modules.mod_privileges import is_admin, elevate_process
    from modules.mod_instalar import (
        install_office_redundant, install_onlyoffice_redundant,
        install_python_if_missing, install_chrome, install_anydesk, install_winrar,
        remove_bloatwares
    )
    from modules.mod_otimizacao import disable_telemetry, optimize_performance, clean_temp_files
    from modules.mod_seguranca import apply_firewall_whitelist, block_smb_ports_public, block_windows_hello, disable_scoobe
    from modules.mod_personalizacao import apply_wallpaper, apply_lockscreen_wallpaper, apply_company_logo
    from modules.mod_automacao import enable_watchdog, schedule_reboot, schedule_software_update, run_network_maintenance, run_sfc_dism
except ImportError:
    # Dummies para demonstração funcional caso os módulos não estejam presentes
    def is_admin(): return ctypes.windll.shell32.IsUserAnAdmin() != 0
    def elevate_process(): 
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    # Criar dummies genéricos para as demais funções
    def dummy_func(*args, **kwargs): time.sleep(1); return True

# --- CONFIGURAÇÕES VISUAIS ---
COLOR_BLACK = "#000000"
COLOR_BG_DARK = "#0A0F1A"
COLOR_CHROME_BLUE = "#00BFFF"
COLOR_HOVER_BLUE = "#1E90FF"
COLOR_TEXT = "#E0E0E0"
COLOR_SUCCESS = "#2EB872"
COLOR_ERROR = "#F03738"
COLOR_WARNING = "#FFBC11"
COLOR_INFO = "#00BFFF"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações de Janela
        self.title("Setup CPFANI - Ferramenta Corporativa")
        self.geometry("1000x750")
        self.configure(fg_color=COLOR_BLACK)
        
        # Variáveis de Controle
        self.config_path = "gui_config.json"
        self.is_executing = False
        self.stop_event = threading.Event()
        self.checkbox_vars = {} # {tab_name: {task_id: var}}
        
        # Carregar Configurações e UI
        self.load_settings()
        self.setup_ui()
        self.log_message("Sistema Midnight Chrome iniciado.", "INFO")

    def setup_ui(self):
        """Constrói a interface principal."""
        # 1. Header Frame (Modo de Execução)
        self.header_frame = ctk.CTkFrame(self, fg_color=COLOR_BG_DARK, corner_radius=0, height=80)
        self.header_frame.pack(fill="x", side="top")
        
        self.mode_var = ctk.StringVar(value=self.settings.get("last_mode", "user"))
        
        # Título e Status Admin
        self.admin_status_lbl = ctk.CTkLabel(
            self.header_frame, text="🛡️ Verificando Privilégios...", 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.admin_status_lbl.pack(side="right", padx=30)
        self.update_admin_indicator()

        mode_lbl = ctk.CTkLabel(self.header_frame, text="Modo de Execução:", font=ctk.CTkFont(size=14, weight="bold"))
        mode_lbl.pack(side="left", padx=(30, 10))

        self.rb_admin = ctk.CTkRadioButton(
            self.header_frame, text="Administrador (Global)", 
            variable=self.mode_var, value="admin", border_color=COLOR_CHROME_BLUE, hover_color=COLOR_HOVER_BLUE
        )
        self.rb_admin.pack(side="left", padx=10)

        self.rb_user = ctk.CTkRadioButton(
            self.header_frame, text="Usuário (Perfil)", 
            variable=self.mode_var, value="user", border_color=COLOR_CHROME_BLUE, hover_color=COLOR_HOVER_BLUE
        )
        self.rb_user.pack(side="left", padx=10)

        if not is_admin():
            self.btn_elevate = ctk.CTkButton(
                self.header_frame, text="Elevar e Continuar", width=120, height=28,
                fg_color=COLOR_ERROR, hover_color="#B22222", command=self.request_elevation
            )
            self.btn_elevate.pack(side="left", padx=20)

        # 2. Tabview (Abas de Categorias)
        self.tabview = ctk.CTkTabview(
            self, fg_color=COLOR_BG_DARK, border_color=COLOR_CHROME_BLUE, border_width=1,
            segmented_button_selected_color=COLOR_CHROME_BLUE, segmented_button_unselected_color=COLOR_BLACK,
            segmented_button_selected_hover_color=COLOR_HOVER_BLUE
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        # Definição dos Dados das Abas
        self.tabs_data = {
            "Instalação": {
                "icon": "📦",
                "tasks": [
                    ("inst_office", "Instalar Microsoft Office (com redundância)"),
                    ("inst_onlyoffice", "Instalar Only Office (com redundância)"),
                    ("inst_python", "Instalar Python (se ausente)"),
                    ("inst_chrome", "Instalar Google Chrome"),
                    ("inst_anydesk", "Instalar AnyDesk"),
                    ("inst_winrar", "Instalar WinRAR")
                ]
            },
            "Otimização e Limpeza": {
                "icon": "🧹",
                "tasks": [
                    ("opt_bloat", "Remover Bloatwares (apps pré-instalados)"),
                    ("opt_telemetry", "Desativar Telemetria e coleta de dados (LGPD)"),
                    ("opt_perf", "Otimizar desempenho do sistema"),
                    ("opt_temp", "Limpar arquivos temporários e cache")
                ]
            },
            "Privacidade e Segurança": {
                "icon": "🔒",
                "tasks": [
                    ("sec_firewall", "Aplicar Firewall Inteligente (Whitelist)"),
                    ("sec_smb", "Bloquear portas SMB/RPC para redes públicas"),
                    ("sec_hello", "Bloquear Windows Hello (biometria/PIN)"),
                    ("sec_scoobe", "Desativar telas de configuração inicial (SCOOBE)")
                ]
            },
            "Personalização": {
                "icon": "🎨",
                "tasks": [
                    ("pers_wallpaper", "Aplicar wallpaper corporativo (área de trabalho)"),
                    ("pers_lock", "Aplicar wallpaper na tela de bloqueio (corrigido)"),
                    ("pers_logo", "Inserir logotipo da empresa no sistema")
                ]
            },
            "Automação e Manutenção": {
                "icon": "⚙️",
                "tasks": [
                    ("auto_watch", "Ativar Watchdog (auto-cura a cada 10s)"),
                    ("auto_reboot", "Agendar reinicialização automática"),
                    ("auto_upd", "Agendar atualização silenciosa de softwares"),
                    ("auto_net", "Executar manutenção de rede (DNS/IP)"),
                    ("auto_sfc", "Executar diagnóstico SFC / DISM")
                ]
            }
        }

        # Criar Abas e Checkboxes
        for tab_name, data in self.tabs_data.items():
            self.tabview.add(tab_name)
            self.checkbox_vars[tab_name] = {}
            
            # Header da Aba
            header = ctk.CTkFrame(self.tabview.tab(tab_name), fg_color="transparent")
            header.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(
                header, text=f"{data['icon']} {tab_name}", 
                font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_CHROME_BLUE
            ).pack(side="left")

            # Botões de Massa
            ctk.CTkButton(
                header, text="✓ Selecionar Tudo", width=100, height=24, font=ctk.CTkFont(size=11),
                fg_color="transparent", border_color=COLOR_CHROME_BLUE, border_width=1,
                command=lambda t=tab_name: self.mass_select(t, True)
            ).pack(side="right", padx=5)
            
            ctk.CTkButton(
                header, text="✗ Desmarcar Tudo", width=100, height=24, font=ctk.CTkFont(size=11),
                fg_color="transparent", border_color="#555", border_width=1,
                command=lambda t=tab_name: self.mass_select(t, False)
            ).pack(side="right", padx=5)

            # Checkboxes
            for task_id, task_label in data['tasks']:
                # Tenta recuperar estado salvo ou default False
                saved_state = self.settings.get("tasks", {}).get(task_id, False)
                var = ctk.BooleanVar(value=saved_state)
                self.checkbox_vars[tab_name][task_id] = var
                
                cb = ctk.CTkCheckBox(
                    self.tabview.tab(tab_name), text=task_label, variable=var,
                    border_color="#555", fg_color=COLOR_CHROME_BLUE, hover_color=COLOR_HOVER_BLUE
                )
                cb.pack(anchor="w", padx=30, pady=6)

        # 3. Barra de Progresso
        self.prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.prog_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.prog_frame, progress_color=COLOR_CHROME_BLUE, fg_color="#222")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 10))
        
        self.prog_label = ctk.CTkLabel(self.prog_frame, text="0%", font=ctk.CTkFont(size=12))
        self.prog_label.pack(side="right")

        # 4. Área de Log
        self.log_area = ctk.CTkTextbox(
            self, height=180, fg_color="#050505", border_color=COLOR_CHROME_BLUE, 
            border_width=1, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_area.pack(fill="both", padx=20, pady=10)
        self.log_area.configure(state="disabled")

        # Botões de Log
        log_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_btn_frame.pack(fill="x", padx=20)
        
        ctk.CTkButton(log_btn_frame, text="📋 Copiar Log", width=100, height=24, command=self.copy_log).pack(side="left", padx=5)
        ctk.CTkButton(log_btn_frame, text="💾 Salvar Log", width=100, height=24, command=self.save_log).pack(side="left", padx=5)

        # 5. Ação Principal
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=20, pady=20)

        self.btn_run = ctk.CTkButton(
            self.action_frame, text="🚀 EXECUTAR TAREFAS SELECIONADAS", 
            height=50, font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLOR_CHROME_BLUE, text_color=COLOR_BLACK, hover_color=COLOR_HOVER_BLUE,
            command=self.start_execution
        )
        self.btn_run.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            self.action_frame, text="❌ Cancelar", width=120, height=50,
            fg_color="#444", hover_color=COLOR_ERROR, command=self.request_stop, state="disabled"
        )
        self.btn_cancel.pack(side="right")

    # --- LÓGICA DE PERSISTÊNCIA ---

    def load_settings(self):
        """Carrega preferências do gui_config.json."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.settings = json.load(f)
                    # Restaurar geometria
                    geo = self.settings.get("geometry")
                    if geo: self.geometry(geo)
            except: self.settings = {}
        else:
            self.settings = {}

    def save_settings(self):
        """Salva preferências ao fechar ou executar."""
        tasks_state = {}
        for tab in self.checkbox_vars:
            for tid, var in self.checkbox_vars[tab].items():
                tasks_state[tid] = var.get()
        
        self.settings = {
            "last_mode": self.mode_var.get(),
            "tasks": tasks_state,
            "geometry": self.geometry()
        }
        with open(self.config_path, 'w') as f:
            json.dump(self.settings, f, indent=4)

    # --- MÉTODOS AUXILIARES UI ---

    def update_admin_indicator(self):
        if is_admin():
            self.admin_status_lbl.configure(text="🛡️ Privilégios de admin ativos", text_color=COLOR_SUCCESS)
        else:
            self.admin_status_lbl.configure(text="⚠️ Modo Usuário (Limitado)", text_color=COLOR_WARNING)

    def mass_select(self, tab_name, state):
        for var in self.checkbox_vars[tab_name].values():
            var.set(state)

    def log_message(self, message, level="INFO"):
        """Adiciona mensagem formatada à caixa de log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {"SUCCESS": "🟢", "ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵"}
        colors = {"SUCCESS": COLOR_SUCCESS, "ERROR": COLOR_ERROR, "WARNING": COLOR_WARNING, "INFO": COLOR_INFO}
        
        self.log_area.configure(state="normal")
        idx = self.log_area.index("end")
        self.log_area.insert("end", f"[{timestamp}] {icons.get(level, '')} {message}\n")
        
        # Aplicar cor à linha
        line_start = f"{float(idx):.1f}"
        self.log_area.tag_add(level, line_start, f"{line_start} lineend")
        self.log_area.tag_config(level, foreground=colors.get(level, "#FFF"))
        
        self.log_area.see("end")
        self.log_area.configure(state="disabled")
        self.update_idletasks()

    def request_elevation(self):
        elevate_process()
        sys.exit()

    # --- MOTOR DE EXECUÇÃO (THREADING) ---

    def start_execution(self):
        if self.is_executing: return
        
        # Coletar tarefas marcadas
        self.queue = []
        for tab in self.checkbox_vars:
            for tid, var in self.checkbox_vars[tab].items():
                if var.get():
                    self.queue.append(tid)

        if not self.queue:
            messagebox.showwarning("Aviso", "Nenhuma tarefa selecionada!")
            return

        self.is_executing = True
        self.stop_event.clear()
        self.btn_run.configure(state="disabled", text="⏳ Executando...")
        self.btn_cancel.configure(state="normal")
        self.save_settings()
        
        threading.Thread(target=self.execute_engine, daemon=True).start()

    def request_stop(self):
        self.stop_event.set()
        self.log_message("Solicitação de cancelamento enviada...", "WARNING")

    def execute_engine(self):
        """Executa as tarefas da fila sequencialmente."""
        total = len(self.queue)
        for i, task_id in enumerate(self.queue):
            if self.stop_event.is_set():
                self.after(0, lambda: self.log_message("Execução interrompida pelo usuário.", "ERROR"))
                break

            self.after(0, lambda t=task_id: self.log_message(f"Iniciando: {t}...", "INFO"))
            
            # Mapeamento Task_ID -> Função de Backend
            success = self.run_task_by_id(task_id)
            
            if success:
                self.after(0, lambda t=task_id: self.log_message(f"Concluído: {t}", "SUCCESS"))
            else:
                self.after(0, lambda t=task_id: self.log_message(f"Falha ao executar: {t}", "ERROR"))

            # Atualizar Progresso
            progress = (i + 1) / total
            self.after(0, lambda p=progress: self.update_progress(p))

        self.after(0, self.finish_execution)

    def run_task_by_id(self, tid):
        """Mapeia o ID da checkbox para a função real."""
        # Se os módulos não existirem, o app usa 'dummy_func' definida no topo
        backend_map = {
            "inst_office": globals().get('install_office_redundant', dummy_func),
            "inst_onlyoffice": globals().get('install_onlyoffice_redundant', dummy_func),
            "inst_python": globals().get('install_python_if_missing', dummy_func),
            "inst_chrome": globals().get('install_chrome', dummy_func),
            "inst_anydesk": globals().get('install_anydesk', dummy_func),
            "inst_winrar": globals().get('install_winrar', dummy_func),
            "opt_bloat": globals().get('remove_bloatwares', dummy_func),
            "opt_telemetry": globals().get('disable_telemetry', dummy_func),
            "opt_perf": globals().get('optimize_performance', dummy_func),
            "opt_temp": globals().get('clean_temp_files', dummy_func),
            "sec_firewall": globals().get('apply_firewall_whitelist', dummy_func),
            "sec_smb": globals().get('block_smb_ports_public', dummy_func),
            "sec_hello": globals().get('block_windows_hello', dummy_func),
            "sec_scoobe": globals().get('disable_scoobe', dummy_func),
            "pers_wallpaper": globals().get('apply_wallpaper', dummy_func),
            "pers_lock": globals().get('apply_lockscreen_wallpaper', dummy_func),
            "pers_logo": globals().get('apply_company_logo', dummy_func),
            "auto_watch": globals().get('enable_watchdog', dummy_func),
            "auto_reboot": globals().get('schedule_reboot', dummy_func),
            "auto_upd": globals().get('schedule_software_update', dummy_func),
            "auto_net": globals().get('run_network_maintenance', dummy_func),
            "auto_sfc": globals().get('run_sfc_dism', dummy_func),
        }
        
        func = backend_map.get(tid, dummy_func)
        try:
            return func()
        except Exception as e:
            self.after(0, lambda m=str(e): self.log_message(f"Erro técnico: {m}", "ERROR"))
            return False

    def update_progress(self, val):
        self.progress_bar.set(val)
        self.prog_label.configure(text=f"{int(val*100)}%")

    def finish_execution(self):
        self.is_executing = False
        self.btn_run.configure(state="normal", text="🚀 EXECUTAR TAREFAS SELECIONADAS")
        self.btn_cancel.configure(state="disabled")
        messagebox.showinfo("Sucesso", "Ciclo de tarefas finalizado!")

    def copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_area.get("1.0", "end"))
        messagebox.showinfo("Log", "Log copiado para a área de transferência!")

    def save_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Arquivo de Texto", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_area.get("1.0", "end"))
            messagebox.showinfo("Sucesso", f"Log salvo em: {path}")

if __name__ == "__main__":
    # Garante que o DPI da tela seja respeitado no Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = App()
    
    # Ao fechar a janela, salva as configurações
    app.protocol("WM_DELETE_WINDOW", lambda: [app.save_settings(), app.destroy()])
    
    app.mainloop()