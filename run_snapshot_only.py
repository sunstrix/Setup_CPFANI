#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_snapshot_only.py - V6.1.0
Script independente para gerar apenas o snapshot de hardware do CP Fani.

Objetivo:
- Executar somente o snapshot, sem branding, firewall, bloatware, drivers, office, etc.
- Poder ser executado manualmente ou pela tarefa agendada CPFANI_SnapshotDiario.
- Em modo agendado (--scheduled), nunca abrir navegador para login OAuth2.
- Chamar/atualizar a tarefa agendada quando executado manualmente.

Exemplos:
    python run_snapshot_only.py
    python run_snapshot_only.py --scheduled
    python run_snapshot_only.py --local "14120 - ARPEL SBC" --usuario "Alex"
    python run_snapshot_only.py --interactive
"""

import argparse
import inspect
import os
import sys
import traceback
from datetime import datetime

# Garante que o diretorio do script esteja no sys.path para importar mod_config
SCRIPT_DIR_PATH = os.path.abspath(os.path.dirname(__file__))

if SCRIPT_DIR_PATH not in sys.path:
    sys.path.insert(0, SCRIPT_DIR_PATH)

try:
    import mod_config
except Exception as e:
    print(f"[ERRO CRITICO] Falha ao importar mod_config.py: {e}", flush=True)
    print(traceback.format_exc(), flush=True)
    sys.exit(1)


def _log_console(msg, level="INFO"):
    """Log simples no console com timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def _supports_parameter(func, param_name):
    """Verifica se uma funcao suporta um parametro especifico."""
    try:
        return param_name in inspect.signature(func).parameters
    except Exception:
        return False


def _interpret_snapshot_result(raw_result):
    """
    Interpreta o retorno de generate_full_snapshot().
    Compativel com retorno antigo (caminho string) e retorno novo (tuple).
    """
    path = None
    success = True
    error = None

    try:
        if isinstance(raw_result, tuple):
            if len(raw_result) >= 3:
                path, success, error = raw_result[0], raw_result[1], raw_result[2]
            elif len(raw_result) == 2:
                path, success = raw_result[0], raw_result[1]
            elif len(raw_result) == 1:
                path = raw_result[0]
        else:
            path = raw_result

            if hasattr(mod_config, "get_last_drive_upload_result"):
                try:
                    last = mod_config.get_last_drive_upload_result()
                    if isinstance(last, tuple) and len(last) >= 2:
                        success, error = last[0], last[1]
                except Exception:
                    pass

        if path is None:
            success = False
            if not error:
                error = "Snapshot local nao gerado."

    except Exception as e:
        success = False
        error = f"Erro ao interpretar resultado do snapshot: {e}"

    return path, bool(success), error


def _ensure_snapshot_scheduler(force=False):
    """
    Garante que a tarefa CPFANI_SnapshotDiario exista.
    Se force=True, recria/atualiza a tarefa.
    """
    if not hasattr(mod_config, "setup_snapshot_scheduler"):
        _log_console("mod_config.setup_snapshot_scheduler() nao disponivel.", "AVISO")
        return False

    try:
        need = force

        if not force and hasattr(mod_config, "check_snapshot_scheduler"):
            exists, msg = mod_config.check_snapshot_scheduler()

            if exists:
                _log_console(msg, "INFO")
                need = False
            else:
                _log_console(msg, "AVISO")
                need = True

        if need:
            ok = mod_config.setup_snapshot_scheduler()

            if ok:
                _log_console("[OK] Task CPFANI_SnapshotDiario criada/atualizada.", "OK")
            else:
                _log_console("Falha ao criar/atualizar task CPFANI_SnapshotDiario.", "ERRO")

            return bool(ok)

        return True

    except Exception as e:
        _log_console(f"Erro ao garantir scheduler de snapshot: {e}", "ERRO")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Gera apenas o snapshot de hardware do CP Fani, sem executar o deploy completo."
    )

    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Modo agendado: sem interacao e sem abrir navegador para login OAuth2."
    )

    parser.add_argument(
        "--local",
        default="",
        help="Codigo/nome do local. Se omitido, usa CPFANI_SNAPSHOT_LOCAL ou 'Nao informado'."
    )

    parser.add_argument(
        "--usuario",
        default="",
        help="Nome do usuario. Se omitido, usa CPFANI_SNAPSHOT_USUARIO, USERNAME ou SYSTEM."
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Em execucao manual, permite login interativo do Google Drive. Nao recomendado para tarefa agendada."
    )

    parser.add_argument(
        "--no-scheduler",
        action="store_true",
        help="Nao cria/atualiza a tarefa agendada CPFANI_SnapshotDiario."
    )

    args = parser.parse_args()

    origem = "Agendamento Automatico" if args.scheduled else "Deploy Manual"

    local = args.local.strip() or os.environ.get("CPFANI_SNAPSHOT_LOCAL", "").strip() or None

    usuario = (
        args.usuario.strip()
        or os.environ.get("CPFANI_SNAPSHOT_USUARIO", "").strip()
        or os.environ.get("USERNAME", "").strip()
        or ("SYSTEM" if args.scheduled else None)
    )

    allow_interactive_drive = False

    if args.scheduled:
        allow_interactive_drive = False
        os.environ["CPFANI_SNAPSHOT_NON_INTERACTIVE"] = "1"
    else:
        if args.interactive:
            allow_interactive_drive = True
            os.environ["CPFANI_SNAPSHOT_NON_INTERACTIVE"] = "0"
        else:
            allow_interactive_drive = False
            os.environ["CPFANI_SNAPSHOT_NON_INTERACTIVE"] = "1"

    _log_console("=" * 60)
    _log_console("SNAPSHOT INDEPENDENTE - RUN_SNAPSHOT_ONLY.PY")
    _log_console("=" * 60)
    _log_console(f"Origem: {origem}")
    _log_console(f"Local: {local if local else 'Nao informado'}")
    _log_console(f"Usuario: {usuario if usuario else 'Nao informado'}")
    _log_console(f"Drive interativo: {'Sim' if allow_interactive_drive else 'Nao'}")

    kwargs = {
        "local": local,
        "usuario": usuario
    }

    if _supports_parameter(mod_config.generate_full_snapshot, "origem"):
        kwargs["origem"] = origem

    if _supports_parameter(mod_config.generate_full_snapshot, "allow_interactive_drive"):
        kwargs["allow_interactive_drive"] = allow_interactive_drive

    raw_result = None

    try:
        raw_result = mod_config.generate_full_snapshot(**kwargs)

    except TypeError as e:
        _log_console(f"Novos parametros nao suportados: {e}. Tentando assinatura antiga.", "AVISO")

        try:
            raw_result = mod_config.generate_full_snapshot(local=local, usuario=usuario)
        except Exception as e2:
            _log_console(f"Erro ao gerar snapshot: {e2}", "ERRO")
            _log_console(traceback.format_exc(), "ERRO")
            return 1

    except Exception as e:
        _log_console(f"Erro ao gerar snapshot: {e}", "ERRO")
        _log_console(traceback.format_exc(), "ERRO")
        return 1

    snapshot_path, upload_success, upload_error = _interpret_snapshot_result(raw_result)

    if not snapshot_path:
        _log_console("Falha ao gerar snapshot local.", "ERRO")

        if upload_error:
            _log_console(f"Detalhe: {upload_error}", "ERRO")

        return 1

    _log_console(f"[OK] Snapshot local gerado: {snapshot_path}", "OK")

    if upload_success:
        _log_console("[OK] Snapshot enviado/atualizado no Google Drive.", "OK")
    else:
        _log_console(f"[AVISO] Snapshot salvo localmente sem envio ao Drive.", "AVISO")

        if upload_error:
            _log_console(f"Motivo: {upload_error}", "AVISO")

    if not args.no_scheduler:
        if args.scheduled:
            # Em execucao agendada, apenas garante que a tarefa exista.
            # Evita recriar a tarefa enquanto ela mesma esta em execucao.
            _ensure_snapshot_scheduler(force=False)
        else:
            # Em execucao manual, recria/atualiza para garantir a configuracao vigente.
            _ensure_snapshot_scheduler(force=True)

    _log_console("Execucao finalizada.", "OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("[AVISO] Execucao cancelada pelo usuario.", flush=True)
        sys.exit(130)
    except Exception as e:
        print(f"[ERRO CRITICO] Falha nao tratada: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        sys.exit(1)