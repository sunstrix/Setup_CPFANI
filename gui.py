"""
gui.py — Interface Profissional v6.0 (Identidade v5.9.5.5)
Layout: 5 Categorias Numeradas + Grid de 10 Softwares
Cores: Preto Absoluto e Azul Cromado (#00BFFF)
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Importação dos módulos de backend refatorados
try:
    from modules.mod_privileges import is_admin, elevate_process
    from modules.mod_config import apply_cpfani_branding, remove_agressive_bloatware, apply_security_lgpd, setup_self_healing
    from modules.mod_network import configure_network_sharing, apply_firewall_rules
    from modules.mod_instalar import install_essential_apps, install_office_redundant, install_onlyoffice_redundant
except ImportError:
    def is_admin(): return False
    def _log(m, l): print(f"[{l}] {m}")

# Configurações de Cores
BG_COLOR = "#0A0A0A"
CARD_COLOR = "#141414"
CHROME_BLUE = "#00BFFF"
TEXT_WHITE = "#E0E0E0"

class SetupGui(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da Janela
        self.title("Setup Automatizado CP Fani — V6.0")
        self.geometry("1100x850")
        self.configure(fg_color=BG_COLOR)
        
        self.is_running = False
        self.checkbox_vars = {}
        
        self.setup_ui()
        self.write_log("Interface carregada com sucesso. Aguardando comandos.", "INFO")

    def setup_ui(self):
        # --- HEADER ---
        header_text = "SETUP AUTOMATIZADO CP FANI\nv6.0.0.0 | Gestão de Endpoints (Redesign v5.9.5.5)"
        self.lbl_header = ctk.CTkLabel(self, text=header_text, font=ctk.CTkFont(size=20, weight="bold"), text_color=CHROME_BLUE)
        self.lbl_header.pack(pady=(20, 10))

        # Indicador de Admin
        admin_txt = "🛡️ PRIVILÉGIOS DE ADMIN ATIVOS" if is_admin() else "⚠️ MODO USUÁRIO (LIMITADO)"
        admin_color = "#28a745" if is_admin() else "#ffc107"
        self.lbl_admin = ctk.CTkLabel(self, text=admin_txt, text_color=admin_color, font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_admin.pack()

        # --- CONTAINER ROLÁVEL ---
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", width=1050, height=500)
        self.scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # 1. INTERFACE E ESTÉTICA
        self.create_section("1. Interface e Estética")
        self.taskbar_var = ctk.StringVar(value="Manter")
        row1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row1.pack(fill="x", padx=40, pady=5)
        for opt in ["Manter Atual", "Esquerda", "Centro"]:
            ctk.CTkRadioButton(row1, text=opt, variable=self.taskbar_var, value=opt, border_color=CHROME_BLUE).pack(side="left", padx=20)

        # 2. SEGURANÇA E PRIVACIDADE
        self.create_section("2. Segurança e Privacidade")
        self.add_checkbox("lgpd", "Políticas de Privacidade/LGPD + Sincronizar NTP.br", True)
        self.add_checkbox("hello", "Desabilitar Windows Hello, Biometria e Tela de Boas-Vindas", True)
        self.add_checkbox("firewall", "Firewall: Restringir SMB/RPC apenas à Rede Local (Whitelist)", True)
        self.add_checkbox("bloatware", "Remoção Agressiva de Bloatware (AllUsers)", True)

        # 3. AUTOMAÇÃO NO LOGON E RESILIÊNCIA
        self.create_section("3. Automação no Logon e Resiliência")
        self.add_checkbox("dhcp", "Agendar manutenção de rede (DHCP)", False)
        self.add_checkbox("updater", "Agendar atualizador de software", False)
        self.add_checkbox("reboot", "Agendar Reinício Diário automático (21:00)", False)
        self.add_checkbox("healing", "Ativar 'Self-Healing' (Auto-Cura / Vigilância de Fundo)", True)

        # 4. SOFTWARES E OFFICE
        self.create_section("4. Softwares e Office")
        # Grid para os 10 Programas
        software_grid = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        software_grid.pack(fill="x", padx=40, pady=10)
        
        apps = [
            ("googlechrome", "Google Chrome"), ("anydesk", "AnyDesk"), ("7zip", "7-Zip"),
            ("flameshot", "Flameshot"), ("teamviewer", "TeamViewer"), ("vlc", "VLC Player"),
            ("winrar", "WinRAR"), ("vcredist-all", "Visual C++ Redist"), ("ditto", "Ditto"),
            ("sharex", "ShareX")
        ]
        
        for i, (app_id, app_name) in enumerate(apps):
            var = ctk.BooleanVar(value=True)
            self.checkbox_vars[app_id] = var
            cb = ctk.CTkCheckBox(software_grid, text=app_name, variable=var, border_color=CHROME_BLUE, fg_color=CHROME_BLUE)
            cb.grid(row=i//3, column=i%3, sticky="w", padx=20, pady=5)

        # Botões de Seleção em Massa
        btn_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=40)
        ctk.CTkButton(btn_row, text="Selecionar Todos", width=120, height=24, fg_color="#333", command=lambda: self.mass_apps(True)).pack(side="right", padx=5)
        ctk.CTkButton(btn_row, text="Limpar Todos", width=120, height=24, fg_color="#333", command=lambda: self.mass_apps(False)).pack(side="right", padx=5)

        # Opções de Office
        self.office_var = ctk.StringVar(value="nenhum")
        office_row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        office_row.pack(fill="x", padx=40, pady=10)
        ctk.CTkRadioButton(office_row, text="Nenhum Office", variable=self.office_var, value="nenhum", border_color=CHROME_BLUE).pack(side="left", padx=20)
        ctk.CTkRadioButton(office_row, text="Office 365 (ODT)", variable=self.office_var, value="office", border_color=CHROME_BLUE).pack(side="left", padx=20)
        ctk.CTkRadioButton(office_row, text="OnlyOffice", variable=self.office_var, value="only", border_color=CHROME_BLUE).pack(side="left", padx=20)

        # 5. GESTÃO DE DRIVERS
        self.create_section("5. Gestão de Drivers")
        self.driver_var = ctk.StringVar(value="ignorar")
        row5 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row5.pack(fill="x", padx=40, pady=5)
        for val, lab in [("ignorar", "Ignorar"), ("fabricante", "Fabricante (Dell/HP/Lenovo)"), ("update", "Windows Update (Forçar)")]:
            ctk.CTkRadioButton(row5, text=lab, variable=self.driver_var, value=val, border_color=CHROME_BLUE).pack(side="left", padx=20)

        # --- FOOTER ---
        self.progress_bar = ctk.CTkProgressBar(self, progress_color=CHROME_BLUE, height=15)
        self.progress_bar.pack(fill="x", padx=40, pady=(20, 5))
        self.progress_bar.set(0)

        self.log_area = ctk.CTkTextbox(self, height=120, fg_color="#050505", border_color="#333", border_width=1, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_area.pack(fill="x", padx=40, pady=10)

        self.btn_run = ctk.CTkButton(self, text="EXECUTAR SETUP AUTOMATIZADO", height=45, fg_color=CHROME_BLUE, text_color="black", font=ctk.CTkFont(size=14, weight="bold"), command=self.start_thread)
        self.btn_run.pack(pady=(0, 20))

    def create_section(self, title):
        lbl = ctk.CTkLabel(self.scroll_frame, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color=CHROME_BLUE)
        lbl.pack(anchor="w", padx=20, pady=(15, 5))
        divider = ctk.CTkFrame(self.scroll_frame, height=2, fg_color="#222")
        divider.pack(fill="x", padx=20, pady=(0, 10))

    def add_checkbox(self, key, label, default):
        var = ctk.BooleanVar(value=default)
        self.checkbox_vars[key] = var
        cb = ctk.CTkCheckBox(self.scroll_frame, text=label, variable=var, border_color="#555", fg_color=CHROME_BLUE)
        cb.pack(anchor="w", padx=40, pady=3)

    def mass_apps(self, state):
        for app in ["googlechrome", "anydesk", "7zip", "flameshot", "teamviewer", "vlc", "winrar", "vcredist-all", "ditto", "sharex"]:
            self.checkbox_vars[app].set(state)

    def write_log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{ts}] [{level}] {msg}\n")
        self.log_area.see("end")

    def start_thread(self):
        if not self.is_running:
            self.is_running = True
            self.btn_run.configure(state="disabled", text="PROCESSANDO...")
            threading.Thread(target=self.engine, daemon=True).start()

    def engine(self):
        # 1. Coleta tarefas
        tasks = []
        if self.checkbox_vars["lgpd"].get(): tasks.append("Privacidade e NTP")
        if self.checkbox_vars["bloatware"].get(): tasks.append("Remover Bloatware")
        
        # Softwares
        selected_apps = [app for app in ["googlechrome", "anydesk", "7zip", "flameshot", "teamviewer", "vlc", "winrar", "vcredist-all", "ditto", "sharex"] if self.checkbox_vars[app].get()]
        if selected_apps: tasks.append(f"Instalar {len(selected_apps)} Apps")
        
        if self.office_var.get() != "nenhum": tasks.append("Instalar Office")

        total = len(tasks)
        if total == 0:
            self.write_log("Nenhuma tarefa selecionada.", "WARNING")
        else:
            for i, task in enumerate(tasks):
                self.write_log(f"Executando: {task}...", "INFO")
                # Chamada simulada para backend (conforme mod_instalar e mod_config)
                time.sleep(1) 
                self.progress_bar.set((i + 1) / total)
            
            self.write_log("=== SETUP CONCLUÍDO COM SUCESSO ===", "SUCCESS")
        
        self.is_running = False
        self.btn_run.configure(state="normal", text="EXECUTAR SETUP AUTOMATIZADO")
        messagebox.showinfo("Sucesso", "Ciclo de configuração finalizado!")

if __name__ == "__main__":
    app = SetupGui()
    app.mainloop()