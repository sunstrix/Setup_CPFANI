# -*- coding: ascii -*-
import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent
GUI = BASE / "gui.py"
MOD = BASE / "mod_config.py"


def backup(path):
    if path.exists():
        shutil.copy2(path, str(path) + ".bak_drive")
        print(f"[OK] Backup criado: {path}.bak_drive")
    else:
        print(f"[ERRO] Arquivo nao encontrado: {path}")


backup(GUI)
backup(MOD)

if not GUI.exists() or not MOD.exists():
    raise SystemExit("[ERRO] Um dos arquivos nao foi encontrado.")

gui_text = GUI.read_text(encoding="utf-8", errors="replace")
mod_text = MOD.read_text(encoding="utf-8", errors="replace")


NEW_GUI_FUNC = r'''def _get_google_drive_service_and_snapshot_files():
    """
    Retorna (service, files) ja autenticado, ou (None, []) em caso de falha.
    Centraliza a logica de autenticacao OAuth2 e a busca dos arquivos
    CPFANI_Hardware_Snapshot* na pasta do Google Drive.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        import pickle

        credentials_path = os.path.join(os.path.dirname(__file__), "credentials", "oauth2_credentials.json")
        token_path = os.path.join(os.path.dirname(__file__), "credentials", "token.pickle")

        print(f"[INFO] Drive read: credenciais em {credentials_path}", flush=True)
        print(f"[INFO] Drive read: token em {token_path}", flush=True)

        if not os.path.exists(credentials_path):
            print("[AVISO] Credenciais OAuth2 nao encontradas. Nao e possivel ler snapshots do Drive.", flush=True)
            return None, []

        SCOPES = ["https://www.googleapis.com/auth/drive"]
        required_scopes = set(SCOPES)
        creds = None

        if os.path.exists(token_path):
            try:
                with open(token_path, "rb") as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"[ERRO] Falha ao ler token.pickle: {e}. Token sera recriado.", flush=True)
                creds = None

        if creds is not None:
            current_scopes = set(getattr(creds, "scopes", []) or [])
            if current_scopes and not required_scopes.issubset(current_scopes):
                print("[AVISO] Token atual nao possui escopo completo de Drive. Reautenticando...", flush=True)
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("[OK] Token OAuth2 renovado com sucesso.", flush=True)
                except Exception as e:
                    print(f"[ERRO] Falha ao renovar token OAuth2: {e}. Reautenticando...", flush=True)
                    creds = None

            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                print("[OK] Autenticacao OAuth2 concluida.", flush=True)

            try:
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)
            except Exception as e:
                print(f"[ERRO] Falha ao salvar token.pickle: {e}", flush=True)

        service = build("drive", "v3", credentials=creds)
        FOLDER_ID = "1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d"

        try:
            folder = service.files().get(fileId=FOLDER_ID, fields="id, name, capabilities").execute()
            print(f"[OK] Pasta do Drive acessivel: {folder.get('name')}", flush=True)
        except HttpError as e:
            print(f"[ERRO] Erro ao acessar pasta do Drive {FOLDER_ID}: {e}", flush=True)
            print("[AVISO] Verifique se a conta autenticada tem permissao na pasta.", flush=True)
            return None, []

        query = f"name contains 'CPFANI_Hardware_Snapshot_' and '{FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])
        return service, files
    except ImportError as e:
        print(f"[ERRO] Bibliotecas do Google Drive nao instaladas ou falha ao importar: {e}", flush=True)
        traceback.print_exc()
        return None, []
    except HttpError as e:
        print(f"[ERRO] Erro na API do Google Drive: {e}", flush=True)
        traceback.print_exc()
        return None, []
    except Exception as e:
        print(f"[ERRO] Erro ao conectar ao Google Drive: {e}", flush=True)
        traceback.print_exc()
        return None, []

'''


NEW_MOD_BLOCK = r'''        SCOPES = ['https://www.googleapis.com/auth/drive']
        token_path = os.path.join(os.path.dirname(__file__), "credentials", "token.pickle")

        _log(f"Drive upload: credenciais em {credentials_path}", "INFO")
        _log(f"Drive upload: token em {token_path}", "INFO")

        required_scopes = set(SCOPES)
        creds = None

        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                _log(f"Falha ao ler token.pickle: {e}. Token sera recriado.", "ERRO")
                creds = None

        if creds is not None:
            current_scopes = set(getattr(creds, "scopes", []) or [])
            if current_scopes and not required_scopes.issubset(current_scopes):
                _log("Token atual nao possui escopo completo de Drive. Reautenticando...", "AVISO")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    _log("[OK] Token OAuth2 renovado com sucesso.", "OK")
                except Exception as e:
                    _log(f"Falha ao renovar token OAuth2: {e}. Reautenticando...", "ERRO")
                    creds = None

            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                _log("[OK] Autenticacao OAuth2 concluida.", "OK")

            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                _log(f"Falha ao salvar token.pickle: {e}", "ERRO")

        service = build('drive', 'v3', credentials=creds)
        FOLDER_ID = "1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d"

        try:
            folder = service.files().get(fileId=FOLDER_ID, fields="id, name, capabilities").execute()
            _log(f"[OK] Pasta do Drive acessivel: {folder.get('name')}", "OK")
        except HttpError as e:
            _log(f"Erro ao acessar pasta do Drive {FOLDER_ID}: {e}", "ERRO")
            _log("Verifique se a conta autenticada tem permissao na pasta.", "AVISO")
            return str(local_path)
'''


NEW_MOD_IMPORT_EXCEPT = r'''    except ImportError as e:
        _log(f"Bibliotecas do Google Drive (OAuth2) nao instaladas ou falha ao importar: {e}", "ERRO")
        _log(traceback.format_exc(), "ERRO")
        _log("Instale com: python -m pip install google-api-python-client google-auth-oauthlib google-auth-httplib2", "INFO")
        return str(local_path)
'''


NEW_MOD_HTTP_EXCEPT = r'''    except HttpError as e:
        _log(f"Erro na API do Google Drive: {e}", "ERRO")
        _log(traceback.format_exc(), "ERRO")
    except Exception as e:
        _log(f"Erro ao enviar para o Google Drive: {e}", "ERRO")
        _log(traceback.format_exc(), "ERRO")
    return str(local_path)
'''


# ==================================================
# GUI.PY
# ==================================================

gui_func_pattern = re.compile(
    r"def _get_google_drive_service_and_snapshot_files\(\):.*?(?=\ndef get_google_drive_service_and_snapshot_files\(\):)",
    re.DOTALL
)

gui_text, n_gui_func = gui_func_pattern.subn(
    lambda m: NEW_GUI_FUNC + "\n",
    gui_text,
    count=1
)

gui_text, n_gui_dirname = re.subn(
    r"os\.path\.dirname\(\s*file\s*\)",
    "os.path.dirname(__file__)",
    gui_text
)

gui_text, n_gui_main = re.subn(
    r"if\s+name\s*==\s*[\"']main[\"']\s*:",
    "if __name__ == \"__main__\":",
    gui_text
)


# ==================================================
# MOD_CONFIG.PY
# ==================================================

mod_scope_pattern = re.compile(
    r"        SCOPES = \[[^\]]*drive\.file[^\]]*\].*?        FOLDER_ID = [\"']1EldWrM7U2tP4SPoGczMJyNdIIIcCsX3d[\"']\n",
    re.DOTALL
)

mod_text, n_mod_scope = mod_scope_pattern.subn(
    lambda m: NEW_MOD_BLOCK + "\n",
    mod_text,
    count=1
)

mod_import_except_pattern = re.compile(
    r"    except ImportError:.*?        return str\(local_path\)\n(?=    except HttpError)",
    re.DOTALL
)

mod_text, n_mod_import = mod_import_except_pattern.subn(
    lambda m: NEW_MOD_IMPORT_EXCEPT + "\n",
    mod_text,
    count=1
)

mod_http_except_pattern = re.compile(
    r"    except HttpError as e:.*?    return str\(local_path\)\n(?=\ndef )",
    re.DOTALL
)

mod_text, n_mod_http = mod_http_except_pattern.subn(
    lambda m: NEW_MOD_HTTP_EXCEPT + "\n",
    mod_text,
    count=1
)

mod_text, n_mod_dirname = re.subn(
    r"os\.path\.dirname\(\s*file\s*\)",
    "os.path.dirname(__file__)",
    mod_text
)


# ==================================================
# SALVAR
# ==================================================

GUI.write_text(gui_text, encoding="utf-8")
MOD.write_text(mod_text, encoding="utf-8")

print("[RESUMO]")
print(f"gui.py: funcao Drive substituida: {n_gui_func}")
print(f"gui.py: dirname(file) corrigido: {n_gui_dirname}")
print(f"gui.py: __main__ corrigido: {n_gui_main}")
print(f"mod_config.py: bloco Drive substituido: {n_mod_scope}")
print(f"mod_config.py: except ImportError melhorado: {n_mod_import}")
print(f"mod_config.py: except HttpError melhorado: {n_mod_http}")
print(f"mod_config.py: dirname(file) corrigido: {n_mod_dirname}")

if n_gui_func == 0:
    print("[AVISO] Nao encontrei a funcao _get_google_drive_service_and_snapshot_files no gui.py.")

if n_mod_scope == 0:
    print("[AVISO] Nao encontrei o bloco SCOPES drive.file no mod_config.py.")

print("[OK] Patch aplicado.")