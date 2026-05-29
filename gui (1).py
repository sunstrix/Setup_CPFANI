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
import re
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def show_windows_toast(title, message):
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.ContentType = WindowsRuntime] | Out-Null

    $appId = '{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe'
    $template = @"
    <toast>
        <visual>
            <binding template="ToastText02">
                <text id="1">{title}</text>
                <text id="2">{message}</text>
            </binding>
        </visual>
    </toast>
"@
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
    """
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script], creationflags=0x08000000)

import mod_config
import mod_instalar

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")
def load_settings():
    if not os.path.exists(SETTINGS_PATH): 
        return {"apps": {"choco": []}, "bloatware_remove": []}
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f: 
        return json.load(f)

SETTINGS = load_settings()

class CPFani_GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Setup Automatizado CP Fani — V5.9.5")
        self.geometry("740x800")
        self.resizable(True, True)
        self.configure(fg_color="#121212")
        self._build_ui()

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
                    pass
        
        ctk.CTkLabel(header_frame, text="SETUP AUTOMATIZADO CP FANI", font=("Segoe UI", 20, "bold"), text_color="#3a86ff").pack()
        ctk.CTkLabel(header_frame, text="v5.9.5  |  Gestão de Endpoints (Adaptação Dinâmica)", font=("Segoe UI", 11), text_color="#666666").pack()

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
        ctk.CTkRadioButton(driver_frame, text="Windows Update (Forçar Instalação)", variable=self.driver_var, value="wu").pack(anchor="w", padx=10, pady=2)

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
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {msg}", flush=True)
        self.after(0, self._log_safe, f"[{ts}] {msg}\n")

    def _log_safe(self, linha):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", linha)
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def update_status(self, text, progress_value=None, current_app_text=None):
        self.status_label.configure(text=text)
        if progress_value is not None:
            self.progress.set(progress_value / 100)
            self.progress_text.configure(text=f"{int(progress_value)}%")
        if current_app_text is not None:
            self.current_app_label.configure(text=current_app_text)
        self.update_idletasks()

    def install_smart_flameshot(self):
        self.log("Analisando repositórios do Flameshot (Chocolatey vs GitHub v13.3.0)...")
        choco_version = "0.0.0"
        try:
            res = subprocess.run(["choco", "info", "flameshot", "--limit-output"], capture_output=True, text=True, timeout=10, creationflags=0x08000000)
            if res.returncode == 0 and res.stdout:
                parts = res.stdout.strip().split('|')
                if len(parts) >= 2:
                    choco_version = parts[1]
        except:
            pass
        
        self.log(f"Disponível no Chocolatey: {choco_version}  |  Disponível no GitHub: 13.3.0")
        
        def _version_to_list(v_str):
            return [int(x) for x in re.findall(r'\d+', v_str)]
            
        v_choco = _version_to_list(choco_version) if choco_version != "0.0.0" else [0, 0, 0]
        v_github = [13, 3, 0]
        
        if v_github >= v_choco:
            self.log("A versão v13.3.0 do GitHub é a mais atual ou idêntica. Iniciando download via MSI...")
            msi_url = "https://github.com/flameshot-org/flameshot/releases/download/v13.3.0/Flameshot-13.3.0-win64.msi"
            temp_msi = r"C:\Users\Public\Downloads\Flameshot-13.3.0-win64.msi"
            try:
                os.makedirs(os.path.dirname(temp_msi), exist_ok=True)
                urllib.request.urlretrieve(msi_url, temp_msi)
                self.log("Executando instalação silenciosa do MSI corporativo...")
                install_res = subprocess.run(["msiexec", "/i", temp_msi, "/qn", "/norestart"], capture_output=True, creationflags=0x08000000)
                if install_res.returncode in [0, 3010]:
                    self.log("✓ Flameshot v13.3.0 instalado via GitHub MSI com sucesso.", "OK")
                    return True
            except Exception as e:
                self.log(f"Aviso na instalação do MSI: {e}. Executando fallback para o Chocolatey...", "AVISO")
        else:
            self.log("O pacote do Chocolatey é mais recente. Direcionando para o gerenciador...")
            
        return mod_instalar._choco_install("flameshot")

    def start_deploy(self):
        if not messagebox.askyesno("Confirmar", "Iniciar provisionamento (Modo Infiltrado + Self-Healing)?"): 
            return
        self.btn_run.configure(state="disabled", text="A EXECUTAR...")
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        erros = []
        try:
            self.log("► Iniciando Deploy (Modo Infiltrado)...")
            selected_apps = [app for app, v in self.app_vars.items() if v.get()]
            
            total_tasks = 4 
            total_tasks += len(selected_apps)
            total_tasks += 1 
            if self.office_var.get() != "nenhum": total_tasks += 1
            if self.driver_var.get() != "nenhum": total_tasks += 1
            if self.task_watchdog.get(): total_tasks += 1
            
            completed = 0

            self.update_status("► Aplicando Interface e Branding...", (completed / total_tasks) * 100, "")
            try: mod_config.apply_cpfani_branding(self.bar_var.get())
            except: erros.append("Branding")
            completed += 1

            self.update_status("► Aplicando Segurança e LGPD...", (completed / total_tasks) * 100, "")
            try:
                mod_config.apply_security_lgpd(apply_lgpd=self.sec_lgpd.get(), disable_hello=self.sec_hello.get())
                if self.sec_firewall.get(): mod_config.apply_firewall_rules()
                if self.sec_bloatware.get(): mod_config.remove_agressive_bloatware(SETTINGS.get("bloatware_remove", []))
            except: erros.append("Segurança")
            completed += 1

            self.update_status("► Agendando Tarefas...", (completed / total_tasks) * 100, "")
            try:
                if self.task_reinicio.get(): mod_config.schedule_daily_reboot()
                if self.task_manutencao.get(): mod_config.schedule_manutencao_rede()
                if self.task_instalar.get(): mod_config.schedule_instalar_tudo()
            except: erros.append("Agendamentos")
            completed += 1
            
            if self.task_watchdog.get():
                self.update_status("► Instalando Motor de Auto-Cura...", (completed / total_tasks) * 100, "Injetando Watchdog...")
                try: mod_config.setup_self_healing()
                except: erros.append("Self-Healing")
                completed += 1

            for app in selected_apps:
                self.update_status(f"► A instalar software...", (completed / total_tasks) * 100, f"Processando {app.capitalize()}...")
                if app == "flameshot":
                    success = self.install_smart_flameshot()
                else:
                    self.log(f"A instalar {app} via Chocolatey...")
                    success = mod_instalar._choco_install(app)
                
                if not success:
                    erros.append(app)
                completed += 1
            
            self.update_status("► A configurar arranque global...", (completed / total_tasks) * 100, "Configurando ferramentas de suporte...")
            try: mod_config.set_apps_to_startup_all_users()
            except: erros.append("Startup Global")
            completed += 1
            
            if self.office_var.get() != "nenhum":
                self.update_status("► A instalar Office...", (completed / total_tasks) * 100, f"Instalando {self.office_var.get()}")
                if not mod_instalar.install_office_suite(self.office_var.get()):
                    erros.append("Office")
                completed += 1

            if self.driver_var.get() != "nenhum":
                self.update_status("► A instalar Drivers...", (completed / total_tasks) * 100, f"Modo: {self.driver_var.get()}")
                if self.driver_var.get() == "fabricante":
                    if not mod_instalar.install_manufacturer_drivers(SETTINGS):
                        erros.append("Drivers Fabricante")
                elif self.driver_var.get() == "wu":
                    if not mod_instalar.force_windows_update_drivers():
                        erros.append("Windows Update")
                completed += 1

            self.update_status("► A gerar snapshot de hardware...", (completed / total_tasks) * 100, "")
            try: mod_config.generate_full_snapshot()
            except: erros.append("Snapshot")
            completed += 1

        except Exception as e: 
            self.log(f"ERRO CRÍTICO: {str(e)}", "ERRO")
            erros.append("Crítico")
        finally: 
            self.after(0, self._finalizar, erros)

    def _finalizar(self, erros):
        self.progress.set(1.0); self.progress_text.configure(text="100%"); self.current_app_label.configure(text="")
        self.btn_run.configure(state="normal", text="▶ EXECUTAR DEPLOY")
        
        if erros:
            self.update_status(f"⚠ Concluído com {len(erros)} alerta(s)", 100)
            show_windows_toast("Aviso no Provisionamento", f"Problemas com: {', '.join(erros)}.")
        else:
            self.update_status("✓ Setup finalizado com sucesso!", 100)
            show_windows_toast("CP Fani - Sucesso", "Provisionamento concluído com sucesso!")
            
        if messagebox.askyesno("Reiniciar Computador", "O provisionamento do computador foi concluído com sucesso.\n\nDeseja reiniciar o computador agora para aplicar todas as diretivas de teclado de forma definitiva?"):
            self.log("Forçando reinício imediato do sistema operacional...", "INFO")
            subprocess.Popen(["shutdown", "/r", "/t", "5", "/f"], creationflags=0x08000000)

if __name__ == "__main__":
    Path(r"C:\Scripts\Logs").mkdir(parents=True, exist_ok=True)
    app = CPFani_GUI()
    app.mainloop()