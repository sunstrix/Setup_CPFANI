# -*- coding: utf-8 -*-
"""atualizar_projeto.py - V1.0
Atualizador diario silencioso do Setup_CPFANI.
Executado pela task CPFANI_AtualizarProjeto (SYSTEM, Session 0, sem janelas).
ASCII - sem acentos.
"""
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime

REPO_DIR = r"C:\Scripts\Setup_CPFANI"
REMOTE_URL = "https://github.com/sunstrix/Setup_CPFANI.git"
BRANCH = "main"
SCRIPT_DIR = os.environ.get("SCRIPT_DIR", r"C:\Scripts")
LOG_DIR = os.path.join(SCRIPT_DIR, "Logs")
LOG_FILE = os.path.join(LOG_DIR, "atualizar_projeto.log")
CREATION_FLAGS_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _log(msg, level="INFO"):
    line = "[%s] [%s] %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, msg)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def _rotate_log():
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1048576:
            old = LOG_FILE + ".old"
            if os.path.exists(old):
                os.remove(old)
            os.rename(LOG_FILE, old)
    except Exception:
        pass


def _run(cmd, timeout=120):
    try:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        return subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=CREATION_FLAGS_NO_WINDOW,
            encoding="utf-8",
            errors="replace",
            env=env
        )
    except Exception as e:
        _log("Erro ao executar %s: %s" % (os.path.basename(cmd[0]), e), "ERRO")
        return None


def _find_git():
    g = shutil.which("git")
    if g:
        return g
    for c in (r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files (x86)\Git\cmd\git.exe"):
        if os.path.exists(c):
            return c
    return None


def _fix_safe_directory(git):
    """Evita 'dubious ownership' quando a task roda como SYSTEM e o repo e de outro usuario."""
    try:
        repo_norm = REPO_DIR.replace("\\", "/")
        chk = _run([git, "config", "--system", "--get-all", "safe.directory"], timeout=30)
        existing = []
        if chk and chk.returncode == 0 and chk.stdout:
            existing = [x.strip().replace("\\", "/") for x in chk.stdout.splitlines()]
        if repo_norm not in existing:
            _run([git, "config", "--system", "--add", "safe.directory", repo_norm], timeout=30)
            _log("safe.directory adicionado para %s" % repo_norm, "INFO")
    except Exception as e:
        _log("Aviso ao configurar safe.directory: %s" % e, "AVISO")


def main():
    _rotate_log()
    _log("=== Verificacao diaria iniciada ===")

    git = _find_git()
    if not git:
        _log("Git nao encontrado. Abortando.", "ERRO")
        return 1

    _fix_safe_directory(git)

    if not os.path.exists(os.path.join(REPO_DIR, ".git")):
        _log("Repositorio ausente em %s. Clonando..." % REPO_DIR, "INFO")
        r = _run([git, "clone", "--depth", "1", REMOTE_URL, REPO_DIR], timeout=600)
        if r and r.returncode == 0:
            _log("Clone concluido.", "OK")
            return 0
        _log("Falha no clone: %s" % (r.stderr.strip() if r and r.stderr else "timeout/erro"), "ERRO")
        return 1

    r = _run([git, "-C", REPO_DIR, "fetch", "--quiet", "origin", BRANCH], timeout=300)
    if not r or r.returncode != 0:
        _log("Falha no fetch (sem conexao com GitHub?): %s" % (r.stderr.strip() if r and r.stderr else "timeout/erro"), "AVISO")
        return 1

    head = _run([git, "-C", REPO_DIR, "rev-parse", "HEAD"], timeout=30)
    remote = _run([git, "-C", REPO_DIR, "rev-parse", "origin/" + BRANCH], timeout=30)
    if not head or not remote:
        _log("Falha ao comparar revisoes.", "ERRO")
        return 1

    h = (head.stdout or "").strip()
    rm = (remote.stdout or "").strip()

    if h == rm:
        _log("Projeto ja atualizado (rev %s). Nada a fazer." % h[:8], "OK")
        return 0

    _log("Atualizacao disponivel (%s -> %s). Aplicando pull --ff-only..." % (h[:8], rm[:8]), "INFO")
    r = _run([git, "-C", REPO_DIR, "pull", "--ff-only", "--quiet", "origin", BRANCH], timeout=600)
    if r and r.returncode == 0:
        _log("Projeto atualizado com sucesso para rev %s." % rm[:8], "OK")
        return 0

    _log("pull --ff-only falhou (ha modificacoes locais no repo?). RC=%s" % (r.returncode if r else "timeout"), "AVISO")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _log("ERRO CRITICO: %s" % e, "ERRO")
        _log(traceback.format_exc(), "ERRO")
        sys.exit(1)