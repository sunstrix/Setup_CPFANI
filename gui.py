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

# ============================================================
# NOVAS FUNÇÕES: INVENTÁRIO GB — MONITORES (LIDOS DO SNAPSHOT DE HARDWARE)
# ============================================================

def _parse_monitors_from_hardware_snapshot(content):
    """
    Extrai dados de monitores do conteúdo do snapshot de hardware.
    Retorna lista de dicionários com 'Modelo' e 'Serial' de cada monitor.
    """
    monitors = []
    
    try:
        # Procura pela seção de monitores
        if "PERIFÉRICOS — MONITORES" not in content:
            return monitors
        
        # Extrai a seção de monitores
        start_idx = content.find("PERIFÉRICOS — MONITORES")
        monitor_section = content[start_idx:]
        
        # Regex para encontrar monitores
        # Padrão: Monitor X:\n  Modelo        : <modelo>\n  Nº de Série   : <serial>
        monitor_pattern = r'Monitor\s+(\d+):\s*\n\s*Modelo\s*:\s*(.*?)\s*\n\s*Nº de Série\s*:\s*(.*?)(?=\n\s*Monitor|\n=|$)'
        matches = re.findall(monitor_pattern, monitor_section, re.DOTALL)
        
        for match in matches:
            monitor_num = match[0]
            modelo = match[1].strip()
            serial = match[2].strip()
            
            if modelo or serial:
                monitors.append({
                    'Numero_Monitor': int(monitor_num),
                    'Modelo': modelo if modelo else 'N/A',
                    'Serial': serial if serial else 'N/A'
                })
    
    except Exception as e:
        print(f"[AVISO] Erro ao parsear monitores do snapshot: {e}", flush=True)
    
    return monitors

def _read_monitors_from_hardware_snapshots():
    """
    Lê todos os arquivos CPFANI_Hardware_Snapshot_*.txt da pasta do Google Drive
    e extrai dados de monitores para popular a planilha
    """
    monitors_data = []
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload
        import pickle
        import io
        
        credentials_path = os.path.join(os.path.dirname(__file__), "credentials", "oauth2_credentials.json")
        if not os.path.exists(credentials_path):
            print("[AVISO] Credenciais OAuth2 não encontradas. Não é possível ler snapshots do Drive.", flush=True)
            return monitors_data
        
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = None
        
        token_path = os.path.join(os.path.dirname(__file__), "credentials", "token.pickle")
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        service = build('drive', 'v3', credentials=creds)
        
        FOLDER_ID = "1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d"
        query = f"name contains 'CPFANI_Hardware_Snapshot_' and '{FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        for file in files:
            try:
                request = service.files().get_media(fileId=file['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8')
                
                # Extrai nome do PC do conteúdo
                pc_name_match = re.search(r'Nome_Computador\s*:\s*(.*?)\s*\n', content)
                pc_name = pc_name_match.group(1) if pc_name_match else 'UNKNOWN'
                
                # Extrai data do snapshot
                date_match = re.search(r'Gerado em:\s*(.*?)\s*\n', content)
                snapshot_date = date_match.group(1) if date_match else 'N/A'
                
                # Extrai monitores
                monitors = _parse_monitors_from_hardware_snapshot(content)
                
                for monitor in monitors:
                    monitors_data.append({
                        'Nome_PC': pc_name,
                        'Data_Snapshot': snapshot_date,
                        'Numero_Monitor': monitor['Numero_Monitor'],
                        'Modelo': monitor['Modelo'],
                        'Serial': monitor['Serial']
                    })
            
            except Exception as e:
                print(f"[AVISO] Erro ao processar arquivo {file['name']}: {e}", flush=True)
                continue
        
        print(f"[OK] {len(monitors_data)} registros de monitores lidos dos snapshots de hardware", flush=True)
        
    except ImportError:
        print("[AVISO] Bibliotecas do Google Drive não instaladas.", flush=True)
    except HttpError as e:
        print(f"[ERRO] Erro na API do Google Drive: {e}", flush=True)
    except Exception as e:
        print(f"[ERRO] Erro ao ler snapshots de hardware: {e}", flush=True)
    
    return monitors_data

def _create_inventory_spreadsheet_with_monitors():
    """
    Cria/atualiza a planilha de inventário GB com a nova aba 'Periféricos - Monitores'
    Dados extraídos diretamente dos snapshots de hardware (sem snapshot separado)
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        
        # Lê dados de monitores dos snapshots de hardware
        monitors_data = _read_monitors_from_hardware_snapshots()
        
        if not monitors_data:
            print("[AVISO] Nenhum dado de monitores encontrado. Planilha não será atualizada.", flush=True)
            return False
        
        # Nome do arquivo da planilha
        spreadsheet_path = os.path.join(mod_config.SCRIPT_DIR, "CPFANI_Inventario_GB.xlsx")
        
        # Cria ou abre a planilha
        if os.path.exists(spreadsheet_path):
            wb = openpyxl.load_workbook(spreadsheet_path)
        else:
            wb = openpyxl.Workbook()
            # Remove aba padrão se existir
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]
        
        # Remove aba existente se já existir (para atualizar)
        if "Periféricos - Monitores" in wb.sheetnames:
            del wb["Periféricos - Monitores"]
        
        # Cria nova aba
        ws = wb.create_sheet("Periféricos - Monitores")
        
        # Cabeçalhos
        headers = ["Nome do PC", "Data do Snapshot", "Nº do Monitor", "Modelo", "Nº de Série"]
        ws.append(headers)
        
        # Formata cabeçalhos
        header_fill = PatternFill(start_color="3a86ff", end_color="3a86ff", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Adiciona dados
        for item in monitors_data:
            ws.append([
                item['Nome_PC'],
                item['Data_Snapshot'],
                item['Numero_Monitor'],
                item['Modelo'],
                item['Serial']
            ])
        
        # Ajusta largura das colunas
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 30
        ws.column_dimensions['E'].width = 25
        
        # Salva planilha
        wb.save(spreadsheet_path)
        print(f"[OK] Planilha de inventário atualizada com {len(monitors_data)} monitores: {spreadsheet_path}", flush=True)
        
        return True
    
    except ImportError:
        print("[ERRO] openpyxl não instalado. Instale com: pip install openpyxl", flush=True)
        return False
    except Exception as e:
        print(f"[ERRO] Falha ao criar planilha de inventário: {e}", flush=True)
        return False

# ============================================================
# NOVAS FUNÇÕES: INVENTÁRIO GB — IMPRESSORAS (LIDAS DO SNAPSHOT DE HARDWARE)
# ============================================================

def _parse_printers_from_hardware_snapshot(content):
    """
    Extrai dados de impressoras do conteúdo do snapshot de hardware.
    Retorna lista de dicionários com dados de cada impressora.
    """
    printers = []
    
    try:
        # Procura pela seção de impressoras
        if "PERIFÉRICOS — IMPRESSORAS" not in content:
            return printers
        
        # Extrai a seção de impressoras
        start_idx = content.find("PERIFÉRICOS — IMPRESSORAS")
        printer_section = content[start_idx:]
        
        # Regex para encontrar impressoras
        # Padrão: Impressora X:\n  Nome: ...\n  Status: ...\n  Porta: ...\n  Driver: ...\n  Compartilhada: ...\n  (IP: ...)\n  (Modelo (SNMP): ...)\n  (Serial (SNMP): ...)
        printer_pattern = r'Impressora\s+\d+:\s*\n(.*?)(?=\n\s*Impressora|\n=|$)'
        matches = re.findall(printer_pattern, printer_section, re.DOTALL)
        
        for match in matches:
            printer_data = {}
            
            # Extrai cada campo
            nome_match = re.search(r'Nome\s*:\s*(.*?)\s*\n', match)
            porta_match = re.search(r'Porta\s*:\s*(.*?)\s*\n', match)
            driver_match = re.search(r'Driver\s*:\s*(.*?)\s*\n', match)
            ip_match = re.search(r'IP\s*:\s*(.*?)\s*\n', match)
            modelo_match = re.search(r'Modelo \(SNMP\)\s*:\s*(.*?)\s*\n', match)
            serial_match = re.search(r'Serial \(SNMP\)\s*:\s*(.*?)\s*\n', match)
            
            printer_data['Nome'] = nome_match.group(1).strip() if nome_match else 'N/A'
            printer_data['Porta'] = porta_match.group(1).strip() if porta_match else 'N/A'
            printer_data['Driver'] = driver_match.group(1).strip() if driver_match else 'N/A'
            printer_data['IP'] = ip_match.group(1).strip() if ip_match else 'N/A'
            printer_data['Modelo_SNMP'] = modelo_match.group(1).strip() if modelo_match else 'N/A'
            printer_data['Serial_SNMP'] = serial_match.group(1).strip() if serial_match else 'N/A'
            
            printers.append(printer_data)
    
    except Exception as e:
        print(f"[AVISO] Erro ao parsear impressoras do snapshot: {e}", flush=True)
    
    return printers

def _read_printers_from_hardware_snapshots():
    """
    Lê todos os arquivos CPFANI_Hardware_Snapshot_*.txt da pasta do Google Drive
    e extrai dados de impressoras para popular a planilha
    """
    printers_data = []
    
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload
        import pickle
        import io
        
        credentials_path = os.path.join(os.path.dirname(__file__), "credentials", "oauth2_credentials.json")
        if not os.path.exists(credentials_path):
            print("[AVISO] Credenciais OAuth2 não encontradas. Não é possível ler snapshots do Drive.", flush=True)
            return printers_data
        
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = None
        
        token_path = os.path.join(os.path.dirname(__file__), "credentials", "token.pickle")
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        service = build('drive', 'v3', credentials=creds)
        
        FOLDER_ID = "1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d"
        query = f"name contains 'CPFANI_Hardware_Snapshot_' and '{FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        for file in files:
            try:
                request = service.files().get_media(fileId=file['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8')
                
                # Extrai nome do PC do conteúdo
                pc_name_match = re.search(r'Nome_Computador\s*:\s*(.*?)\s*\n', content)
                pc_name = pc_name_match.group(1) if pc_name_match else 'UNKNOWN'
                
                # Extrai data do snapshot
                date_match = re.search(r'Gerado em:\s*(.*?)\s*\n', content)
                snapshot_date = date_match.group(1) if date_match else 'N/A'
                
                # Extrai impressoras
                printers = _parse_printers_from_hardware_snapshot(content)
                
                for printer in printers:
                    printers_data.append({
                        'Nome_PC': pc_name,
                        'Data_Snapshot': snapshot_date,
                        'Nome_Impressora': printer['Nome'],
                        'Porta': printer['Porta'],
                        'Driver': printer['Driver'],
                        'IP': printer['IP'],
                        'Modelo_SNMP': printer['Modelo_SNMP'],
                        'Serial_SNMP': printer['Serial_SNMP']
                    })
            
            except Exception as e:
                print(f"[AVISO] Erro ao processar arquivo {file['name']}: {e}", flush=True)
                continue
        
        print(f"[OK] {len(printers_data)} registros de impressoras lidos dos snapshots de hardware", flush=True)
        
    except ImportError:
        print("[AVISO] Bibliotecas do Google Drive não instaladas.", flush=True)
    except HttpError as e:
        print(f"[ERRO] Erro na API do Google Drive: {e}", flush=True)
    except Exception as e:
        print(f"[ERRO] Erro ao ler snapshots de hardware: {e}", flush=True)
    
    return printers_data

def _create_inventory_spreadsheet_with_printers():
    """
    Cria/atualiza a planilha de inventário GB com a nova aba 'Periféricos - Impressoras'
    Dados extraídos diretamente dos snapshots de hardware
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        
        # Lê dados de impressoras dos snapshots de hardware
        printers_data = _read_printers_from_hardware_snapshots()
        
        if not printers_data:
            print("[AVISO] Nenhum dado de impressoras encontrado. Planilha não será atualizada.", flush=True)
            return False
        
        # Nome do arquivo da planilha
        spreadsheet_path = os.path.join(mod_config.SCRIPT_DIR, "CPFANI_Inventario_GB.xlsx")
        
        # Cria ou abre a planilha
        if os.path.exists(spreadsheet_path):
            wb = openpyxl.load_workbook(spreadsheet_path)
        else:
            wb = openpyxl.Workbook()
            # Remove aba padrão se existir
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]
        
        # Remove aba existente se já existir (para atualizar)
        if "Periféricos - Impressoras" in wb.sheetnames:
            del wb["Periféricos - Impressoras"]
        
        # Cria nova aba
        ws = wb.create_sheet("Periféricos - Impressoras")
        
        # Cabeçalhos
        headers = ["Nome do PC", "Data do Snapshot", "Nome Impressora", "Porta", "Driver", "IP", "Modelo (SNMP)", "Serial (SNMP)"]
        ws.append(headers)
        
        # Formata cabeçalhos
        header_fill = PatternFill(start_color="ff6b6b", end_color="ff6b6b", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Adiciona dados
        for item in printers_data:
            ws.append([
                item['Nome_PC'],
                item['Data_Snapshot'],
                item['Nome_Impressora'],
                item['Porta'],
                item['Driver'],
                item['IP'],
                item['Modelo_SNMP'],
                item['Serial_SNMP']
            ])
        
        # Ajusta largura das colunas
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 25
        ws.column_dimensions['E'].width = 30
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 25
        ws.column_dimensions['H'].width = 25
        
        # Salva planilha
        wb.save(spreadsheet_path)
        print(f"[OK] Planilha de inventário atualizada com {len(printers_data)} impressoras: {spreadsheet_path}", flush=True)
        
        return True
    
    except ImportError:
        print("[ERRO] openpyxl não instalado. Instale com: pip install openpyxl", flush=True)
        return False
    except Exception as e:
        print(f"[ERRO] Falha ao criar planilha de inventário: {e}", flush=True)
        return False

class CPFani_GUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Setup Automatizado CP Fani — V5.9.5")
        self.geometry("740x800")
        self.resizable(True, True)
        self.configure(fg_color="#121212")
        self.local_snapshot = "Não informado"
        self.usuario_snapshot = "Não informado"
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

        # ============================================================
        # 6. MANUTENÇÃO E LIMPEZA (KUDU)
        # ============================================================
        kudu_frame = ctk.CTkFrame(self.main_scroll, fg_color="#1e1e1e", corner_radius=8)
        kudu_frame.pack(padx=20, pady=5, fill="x")
        
        kudu_header = ctk.CTkFrame(kudu_frame, fg_color="transparent")
        kudu_header.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(kudu_header, text="6. Manutenção e Limpeza (Kudu)", font=("", 12, "bold")).pack(side="left")
        
        btn_kudu_oneclick = ctk.CTkButton(
            kudu_header, text="One‑Click Clean", font=("", 10), width=100, height=22,
            fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.select_all_kudu_actions
        )
        btn_kudu_oneclick.pack(side="right", padx=2)
        
        # Checkboxes para cada ação do Kudu
        self.kudu_system = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="System Cleaner (temporários, logs, caches)", variable=self.kudu_system).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_app = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="App Cleaner (resíduos de apps desinstalados)", variable=self.kudu_app).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_gaming = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="Gaming Cleaner (caches de jogos e shaders)", variable=self.kudu_gaming).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_registry = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="Registry Cleaner (entradas quebradas/órfãs)", variable=self.kudu_registry).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_network = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="Network Cleanup (DNS, Wi-Fi, ARP)", variable=self.kudu_network).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_debloat = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="Debloater (fallback – lista interna do Kudu)", variable=self.kudu_debloat).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_drivers = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="Driver Manager (limpeza de drivers obsoletos)", variable=self.kudu_drivers).pack(anchor="w", padx=20, pady=2)
        
        self.kudu_services = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(kudu_frame, text="Service Manager (otimização de serviços Windows)", variable=self.kudu_services).pack(anchor="w", padx=20, pady=2)

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

    def select_all_kudu_actions(self):
        """Marca todas as ações do Kudu (One‑Click Clean)"""
        self.kudu_system.set(True)
        self.kudu_app.set(True)
        self.kudu_gaming.set(True)
        self.kudu_registry.set(True)
        self.kudu_network.set(True)
        self.kudu_debloat.set(True)
        self.kudu_drivers.set(True)
        self.kudu_services.set(True)
        self.log("Todas as ações de limpeza Kudu foram marcadas.", "INFO")

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

    def _coletar_dados_snapshot(self):
        """Abre janela modal para coletar local e usuário para o snapshot"""
        # Lista de locais
        locais = [
            "BPCS – LOJA",
            "4830 – MATRIZ",
            "4842 – METRÓPOLE",
            "5152 – CORAÇÃO",
            "6105 – ASSAI",
            "6106 – DIREITA",
            "6110 – AROUCHE",
            "8001 – DOM JOSÉ",
            "12055 – SÃO BENTO",
            "11576 – D'AVÓ",
            "12605 – COOP",
            "12645 – LIGHT",
            "20371 – METRÔ LUZ",
            "21502 – BB_SBC",
            "23000 – OUTLET",
            "12056 – MARECHAL",
            "14120 – ARPEL SBC",
            "14353 – ARPEL SP",
            "23379 – Piraporinha"
        ]

        # Janela modal
        dialog = ctk.CTkToplevel(self)
        dialog.title("Dados do Snapshot")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Centralizar na tela
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 200
        y = (dialog.winfo_screenheight() // 2) - 125
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="Selecione o Local:", font=("", 12, "bold")).pack(pady=(20, 5))
        var_local = ctk.StringVar(value=locais[0])
        option_menu = ctk.CTkOptionMenu(dialog, values=locais, variable=var_local, width=300)
        option_menu.pack(pady=5)

        ctk.CTkLabel(dialog, text="Nome do Usuário:", font=("", 12, "bold")).pack(pady=(15, 5))
        entry_usuario = ctk.CTkEntry(dialog, width=300, placeholder_text="Digite o nome do usuário")
        entry_usuario.pack(pady=5)
        entry_usuario.focus_set()

        def confirmar():
            self.local_snapshot = var_local.get()
            self.usuario_snapshot = entry_usuario.get().strip() or "Não informado"
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar, width=100).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", command=dialog.destroy, width=100, fg_color="#555555").pack(side="left", padx=10)

        self.wait_window(dialog)

    def _work(self):
        """Lógica principal de deploy com tratamento robusto de erros"""
        erros = []
        start_time = time.time()
        
        try:
            self.log("► Iniciando Deploy (Modo Infiltrado)...")
            self.log(f"Configurações carregadas: {len(SETTINGS.get('apps', {}).get('choco', []))} apps definidos")
            
            selected_apps = [app for app, v in self.app_vars.items() if v.get()]
            self.log(f"Aplicativos selecionados para instalação: {len(selected_apps)}")
            
            # Verifica quais ações do Kudu estão selecionadas
            kudu_actions = []
            if self.kudu_system.get(): kudu_actions.append('system')
            if self.kudu_app.get(): kudu_actions.append('app')
            if self.kudu_gaming.get(): kudu_actions.append('gaming')
            if self.kudu_registry.get(): kudu_actions.append('registry')
            if self.kudu_network.get(): kudu_actions.append('network')
            if self.kudu_debloat.get(): kudu_actions.append('debloat')
            if self.kudu_drivers.get(): kudu_actions.append('drivers')
            if self.kudu_services.get(): kudu_actions.append('services')
            has_kudu_actions = len(kudu_actions) > 0
            
            # Coleta dados do snapshot ANTES de começar as tarefas
            self._coletar_dados_snapshot()
            
            # Cálculo de tarefas totais
            total_tasks = 4  # Interface, Segurança, Agendamentos, Startup
            total_tasks += len(selected_apps)
            if self.office_var.get() != "nenhum": total_tasks += 1
            if self.driver_var.get() != "nenhum": total_tasks += 1
            if self.task_watchdog.get(): total_tasks += 1
            if has_kudu_actions: total_tasks += 1
            total_tasks += 3  # Snapshot + Planilha Monitores + Planilha Impressoras
            
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

            # ============================================================
            # 9. MANUTENÇÃO E LIMPEZA KUDU
            # ============================================================
            if has_kudu_actions:
                self.update_status(
                    "► Executando limpeza Kudu...",
                    (completed / total_tasks) * 100,
                    "Kudu: " + ", ".join(kudu_actions)
                )
                try:
                    self.log(f"Iniciando limpeza Kudu com ações: {', '.join(kudu_actions)}")
                    try:
                        result = mod_config.run_kudu_cleanup(kudu_actions)
                        if result.get("success", False):
                            self.log("✓ Limpeza Kudu concluída com sucesso.", "OK")
                        else:
                            failed_actions = [act for act, res in result.get("results", {}).items() if not res]
                            if failed_actions:
                                self.log(f"Ações Kudu com falha: {', '.join(failed_actions)}", "AVISO")
                                erros.extend([f"Kudu-{act}" for act in failed_actions])
                            else:
                                self.log("Kudu concluído com sucesso parcial.", "AVISO")
                    except AttributeError:
                        self.log("Função run_kudu_cleanup não encontrada no mod_config. Verifique a integração.", "ERRO")
                        erros.append("Kudu (função não encontrada)")
                    except Exception as e:
                        self.log(f"Erro ao executar Kudu: {e}", "ERRO")
                        erros.append("Kudu")
                except Exception as e:
                    self.log(f"Erro crítico na etapa Kudu: {e}", "ERRO")
                    erros.append("Kudu-Crítico")
                completed += 1

            # 10. SNAPSHOT DE HARDWARE (COM MONITORES E IMPRESSORAS INCLUSOS)
            self.update_status("► Gerando snapshot de hardware...", (completed / total_tasks) * 100, "")
            try:
                self.log("Gerando snapshot de hardware (incluindo monitores e impressoras)...")
                # Passa os dados coletados
                mod_config.generate_full_snapshot(
                    local=self.local_snapshot,
                    usuario=self.usuario_snapshot
                )
                self.log("✓ Snapshot de hardware gerado com dados de monitores e impressoras", "OK")
            except Exception as e:
                self.log(f"Falha ao gerar snapshot de hardware: {e}", "ERRO")
                erros.append("Snapshot Hardware")
            completed += 1

            # 11. PLANILHA DE INVENTÁRIO GB — MONITORES
            self.update_status("► Atualizando planilha de inventário GB (Monitores)...", (completed / total_tasks) * 100, "Processando monitores...")
            try:
                self.log("Atualizando planilha de inventário GB com dados de monitores...")
                if _create_inventory_spreadsheet_with_monitors():
                    self.log("✓ Planilha de inventário atualizada com aba de monitores", "OK")
                else:
                    self.log("Falha ao atualizar planilha de inventário (monitores)", "AVISO")
                    erros.append("Planilha Monitores")
            except Exception as e:
                self.log(f"Falha ao atualizar planilha de inventário (monitores): {e}", "ERRO")
                erros.append("Planilha Monitores")
            completed += 1

            # 12. PLANILHA DE INVENTÁRIO GB — IMPRESSORAS
            self.update_status("► Atualizando planilha de inventário GB (Impressoras)...", (completed / total_tasks) * 100, "Processando impressoras...")
            try:
                self.log("Atualizando planilha de inventário GB com dados de impressoras...")
                if _create_inventory_spreadsheet_with_printers():
                    self.log("✓ Planilha de inventário atualizada com aba de impressoras", "OK")
                else:
                    self.log("Falha ao atualizar planilha de inventário (impressoras)", "AVISO")
                    erros.append("Planilha Impressoras")
            except Exception as e:
                self.log(f"Falha ao atualizar planilha de inventário (impressoras): {e}", "ERRO")
                erros.append("Planilha Impressoras")
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