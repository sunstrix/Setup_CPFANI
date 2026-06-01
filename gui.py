"""
gui.py — Interface Gráfica Corporativa Setup CP Fani
Engenheiro Sênior: Gemini & Sunstrix — Versão 6.0.0.0
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
from datetime import datetime

# Importação dos Módulos Refatorados
from modules.mod_privileges import is_admin, elevate_process, check_privilege_and_report
from modules.mod_config import _log, apply_cpfani_branding, remove_agressive_bloatware, apply_security_lgpd, configurar_compartilhamento_rede
from modules.mod_instalar import install_office_redundant, install_onlyoffice_redundant

class SetupGui:
    def __init__(self, root):
        self.root = root
        self.load_configs()
        
        # Configuração da Janela
        self.version = self.config_v.get("project_info", {}).get("version", "6.0")
        self.root.title(f"Setup CP Fani — v{self.version}")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        
        self.admin_mode = is_admin()
        self.setup_ui()
        check_privilege_and_report()

    def load_configs(self):
        """Carrega as configurações centralizadas."""
        try:
            with open("config_version.json", "r", encoding="utf-8") as f:
                self.config_v = json.load(f)
            with open("settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Falha ao carregar arquivos de configuração: {e}")
            sys.exit(1)

    def setup_ui(self):
        """Constrói a interface visual."""
        # Frame de Status de Privilégio
        status_color = "#d4edda" if self.admin_mode else "#fff3cd"
        status_text = "MODO ADMINISTRADOR (SISTEMA)" if self.admin_mode else "MODO USUÁRIO (PERFIL APENAS)"
        
        self.status_frame = tk.Frame(self.root, bg=status_color, pady=5)
        self.status_frame.pack(fill="x")
        
        tk.Label(self.status_frame, text=status_text, bg=status_color, font=("Arial", 10, "bold")).pack()
        
        if not self.admin_mode:
            tk.Button(self.status_frame, text="SOLICITAR ELEVAÇÃO UAC", command=elevate_process, bg="#ffc107").pack(pady=5)

        # Container Principal
        self.main_frame = tk.Frame(self.root, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        # Seção 1: Branding e Visual
        tk.Label(self.main_frame, text="1. Personalização e Branding", font=("Arial", 12, "bold")).pack(anchor="w")
        self.btn_branding = ttk.Button(self.main_frame, text="Aplicar Wallpaper, Tema e LockScreen", command=self.run_branding)
        self.btn_branding.pack(fill="x", pady=5)

        # Seção 2: Otimização e Bloatware
        tk.Label(self.main_frame, text="2. Sistema e Segurança", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,0))
        self.btn_bloat = ttk.Button(self.main_frame, text="Remover Bloatwares e Aplicar LGPD", command=self.run_security)
        self.btn_bloat.pack(fill="x", pady=5)

        # Seção 3: Rede e Compartilhamento (Novo)
        tk.Label(self.main_frame, text="3. Rede e Impressoras", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,0))
        self.btn_network = ttk.Button(self.main_frame, text="Configurar Rede Local e SMB Sem Senha", command=self.run_network)
        self.btn_network.pack(fill="x", pady=5)

        # Seção 4: Instalação Redundante (Novo)
        tk.Label(self.main_frame, text="4. Suítes de Escritório (Redundante)", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10,0))
        self.btn_office = ttk.Button(self.main_frame, text="Instalar Microsoft Office 365 (ODT/Choco/Winget)", command=self.run_office)
        self.btn_office.pack(fill="x", pady=5)
        self.btn_only = ttk.Button(self.main_frame, text="Instalar OnlyOffice Desktop", command=self.run_onlyoffice)
        self.btn_only.pack(fill="x", pady=5)

        # Log de Saída em tempo real
        tk.Label(self.main_frame, text="Log de Execução:", font=("Arial", 10)).pack(anchor="w", pady=(15,0))
        self.log_text = tk.Text(self.main_frame, height=10, bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9))
        self.log_text.pack(fill="both", pady=5)

    def update_log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)
        self.root.update()

    # --- Funções de Disparo (Wrappers com Threads para não travar a GUI) ---

    def run_branding(self):
        def task():
            self.update_log("Iniciando personalização...")
            apply_cpfani_branding(self.settings["user_preferences"]["taskbar_alignment"])
            self.update_log("Branding finalizado.")
        threading.Thread(target=task).start()

    def run_security(self):
        if not self.admin_mode:
            messagebox.showwarning("Aviso", "Remoção de Bloatware requer modo Administrador.")
            return
        def task():
            self.update_log("Limpando sistema...")
            remove_agressive_bloatware(self.config_v["software_lists"]["bloatware_to_remove"])
            apply_security_lgpd()
            self.update_log("Otimização de sistema concluída.")
        threading.Thread(target=task).start()

    def run_network(self):
        if not self.admin_mode:
            messagebox.showwarning("Aviso", "Configuração de rede requer modo Administrador.")
            return
        def task():
            self.update_log("Configurando descoberta de rede...")
            configurar_compartilhamento_rede()
            self.update_log("Rede configurada para compartilhamento transparente.")
        threading.Thread(target=task).start()

    def run_office(self):
        def task():
            self.update_log("Iniciando instalação redundante do Office...")
            if install_office_redundant():
                self.update_log("Microsoft Office instalado com sucesso!")
            else:
                self.update_log("FALHA CRÍTICA na instalação do Office.")
        threading.Thread(target=task).start()

    def run_onlyoffice(self):
        def task():
            self.update_log("Iniciando instalação do OnlyOffice...")
            if install_onlyoffice_redundant():
                self.update_log("OnlyOffice instalado com sucesso!")
            else:
                self.update_log("Falha ao instalar OnlyOffice.")
        threading.Thread(target=task).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = SetupGui(root)
    root.mainloop()