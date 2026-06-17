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
import time
import traceback
from datetime import datetime
from pathlib import Path

# Configuração de encoding para evitar crashes em caracteres especiais
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

def show_windows_toast(title, message):
    """Exibe notificação nativa do Windows"""
    # Escapa caracteres especiais para evitar erros no PowerShell
    title_escaped = title.replace('"', '`"').replace("'", "`'")
    message_escaped = message.replace('"', '`"').replace("'", "`'")
    
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

try:
    import mod_config
    import mod_instalar
except ImportError as e:
    print(f"[ERRO CRÍTICO] Falha ao importar módulos: {e}", flush=True)
    print("Certifique-se de que mod_config.py e mod_instalar.py estão no mesmo diretório.", flush=True)
    sys.exit(1)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

def load_settings():
    """Carrega configurações do settings.json com fallback seguro"""
    default_settings = {
        "apps": {
            "choco": ["googlechrome", "anydesk", "flameshot", "sharex", "7zip", "lightshot"]
        },
        "bloatware_remove": ["Microsoft.ZuneVideo", "Microsoft.WindowsFeedbackHub"]
    }
    
    if not os.path.exists(SETTINGS_PATH):
        print(f"[INFO] settings.json não encontrado. Usando configurações padrão.", flush=True)
        return default_settings
    
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8", errors='replace') as f:
            settings = json.load(f)
            print(f"[OK] Configurações carregadas de {SETTINGS_PATH}", flush=True)
            return settings
    except json.JSONDecodeError as e:
        print(f"[ERRO] settings.json corrompido: {e}. Usando padrão.", flush=True)
        return default_settings
    except Exception as e:
        print(f"[ERRO] Falha ao ler settings.json: {e}. Usando padrão.", flush=True)
        return default_settings

SETTINGS = load_settings()

class CPFani_GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Setup Automatizado CP Fani — V5.9.5")
        self.geometry("740x800")
        self.resizable(True, True)
        self.configure(fg_color="#121212")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """Tratamento seguro para fechamento da janela"""
        if messagebox.askokcancel("Sair", "Deseja realmente sair do setup?"):
            self.log("Interface fechada pelo usuário.", "INFO")
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

    def _download_with_validation(self, url, dest_path, min_size_mb=1, max_retries=3, timeout=300):
        """Download robusto com validação de tamanho e retry logic"""
        for attempt in range(1, max_retries + 1):
            try:
                self.log(f"Tentativa {attempt}/{max_retries}: Baixando {os.path.basename(dest_path)}...")
                
                # Cria diretório se não existir
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Download com timeout
                start_time = time.time()
                urllib.request.urlretrieve(url, dest_path)
                elapsed = time.time() - start_time
                
                # Validação de tamanho
                file_size = os.path.getsize(dest_path)
                min_size_bytes = min_size_mb * 1024 * 1024
                
                if file_size < min_size_bytes:
                    self.log(f"Arquivo muito pequeno ({file_size} bytes < {min_size_bytes} bytes). Removendo...", "AVISO")
                    try:
                        os.remove(dest_path)
                    except Exception as e:
                        self.log(f"Falha ao remover arquivo corrompido: {e}", "AVISO")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    else:
                        return False
                
                self.log(f"✓ Download concluído: {file_size / (1024*1024):.2f} MB em {elapsed:.1f}s", "OK")
                return True
                
            except Exception as e:
                self.log(f"Falha na tentativa {attempt}: {e}", "ERRO")
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception as e_rem:
                        self.log(f"Falha ao remover arquivo parcial: {e_rem}", "AVISO")
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
                        except Exception as e:
                            self.log(f"Falha ao remover {temp_msi}: {e}", "AVISO")
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
                except Exception as e:
                    self.log(f"Falha ao remover {temp_msi}: {e}", "AVISO")
            
            self.log("Fallback: Instalando via Chocolatey...", "AVISO")
        else:
            self.log("O pacote do Chocolatey é mais recente. Direcionando para o gerenciador...")
            
        return mod_instalar._choco_install("flameshot")

    def start_deploy(self):
        """Inicia o processo de deploy com confirmação"""
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
                mod_config.apply_cpfani_branding(self.bar_var.get())
                self.log("✓ Branding aplicado com sucesso", "OK")
            except Exception as e:
                self.log(f"Falha ao aplicar branding: {e}", "ERRO")
                erros.append("Branding")
            completed += 1

            # 2. SEGURANÇA E LGPD
            self.update_status("► Aplicando Segurança e LGPD...", (completed / total_tasks) * 100, "")
            try:
                self.log("Aplicando políticas de segurança...")
                mod_config.apply_security_lgpd(
                    apply_lgpd=self.sec_lgpd.get(),
                    disable_hello=self.sec_hello.get()
                )
                
                if self.sec_firewall.get():
                    self.log("Configurando regras de firewall...")
                    mod_config.apply_firewall_rules()
                
                if self.sec_bloatware.get():
                    self.log("Removendo bloatware...")
                    mod_config.remove_agressive_bloatware(SETTINGS.get("bloatware_remove", []))
                
                self.log("✓ Segurança aplicada com sucesso", "OK")
            except Exception as e:
                self.log(f"Falha ao aplicar segurança: {e}", "ERRO")
                erros.append("Segurança")
            completed += 1

            # 3. AGENDAMENTOS
            self.update_status("► Agendando Tarefas...", (completed / total_tasks) * 100, "")
            try:
                self.log("Configurando agendamentos...")
                if self.task_reinicio.get():
                    self.log("Agendando reinício diário...")
                    mod_config.schedule_daily_reboot()
                if self.task_manutencao.get():
                    self.log("Agendando manutenção de rede...")
                    mod_config.schedule_manutencao_rede()
                if self.task_instalar.get():
                    self.log("Agendando atualizador...")
                    mod_config.schedule_instalar_tudo()
                self.log("✓ Agendamentos configurados", "OK")
            except Exception as e:
                self.log(f"Falha ao configurar agendamentos: {e}", "ERRO")
                erros.append("Agendamentos")
            completed += 1
            
            # 4. SELF-HEALING
            if self.task_watchdog.get():
                self.update_status("► Instalando Motor de Auto-Cura...", (completed / total_tasks) * 100, "Injetando Watchdog...")
                try:
                    self.log("Configurando self-healing...")
                    mod_config.setup_self_healing()
                    self.log("✓ Self-healing ativado", "OK")
                except Exception as e:
                    self.log(f"Falha ao configurar self-healing: {e}", "ERRO")
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
                    erros.append(app)
                
                completed += 1
            
            # 6. STARTUP GLOBAL
            self.update_status("► Configurando arranque global...", (completed / total_tasks) * 100, "Configurando ferramentas de suporte...")
            try:
                self.log("Configurando aplicativos de startup...")
                mod_config.set_apps_to_startup_all_users()
                self.log("✓ Startup configurado", "OK")
            except Exception as e:
                self.log(f"Falha ao configurar startup: {e}", "ERRO")
                erros.append("Startup Global")
            completed += 1
            
            # 7. OFFICE
            if self.office_var.get() != "nenhum":
                self.update_status("► Instalando Office...", (completed / total_tasks) * 100, f"Instalando {self.office_var.get()}")
                try:
                    self.log(f"Instalando {self.office_var.get()}...")
                    if not mod_instalar.install_office_suite(self.office_var.get()):
                        self.log(f"Falha ao instalar {self.office_var.get()}", "ERRO")
                        erros.append("Office")
                    else:
                        self.log("✓ Office instalado", "OK")
                except Exception as e:
                    self.log(f"Erro ao instalar Office: {e}", "ERRO")
                    erros.append("Office")
                completed += 1

            # 8. DRIVERS
            if self.driver_var.get() != "nenhum":
                self.update_status("► Instalando Drivers...", (completed / total_tasks) * 100, f"Modo: {self.driver_var.get()}")
                try:
                    if self.driver_var.get() == "fabricante":
                        self.log("Instalando drivers do fabricante...")
                        if not mod_instalar.install_manufacturer_drivers(SETTINGS):
                            self.log("Falha ao instalar drivers do fabricante", "ERRO")
                            erros.append("Drivers Fabricante")
                        else:
                            self.log("✓ Drivers do fabricante instalados", "OK")
                    elif self.driver_var.get() == "wu":
                        self.log("Forçando Windows Update para drivers...")
                        if not mod_instalar.force_windows_update_drivers():
                            self.log("Falha ao forçar Windows Update", "ERRO")
                            erros.append("Windows Update")
                        else:
                            self.log("✓ Windows Update executado", "OK")
                except Exception as e:
                    self.log(f"Erro ao instalar drivers: {e}", "ERRO")
                    erros.append("Drivers")
                completed += 1

            # 9. SNAPSHOT
            self.update_status("► Gerando snapshot de hardware...", (completed / total_tasks) * 100, "")
            try:
                self.log("Gerando snapshot de hardware...")
                mod_config.generate_full_snapshot()
                self.log("✓ Snapshot gerado", "OK")
            except Exception as e:
                self.log(f"Falha ao gerar snapshot: {e}", "ERRO")
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