#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de stress para run_jarvis_message.py.
Executa N vezes seguidas e verifica que todas finalizam com código 0 e em tempo aceitável.
Uso: python scripts/stress_run_jarvis_message.py [--runs 30] [--max-seconds 5]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Diretório jarvis (parent do diretório scripts/)
JARVIS_DIR = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description="Stress run_jarvis_message")
    ap.add_argument("--runs", type=int, default=30, help="Número de execuções (default 30)")
    ap.add_argument("--max-seconds", type=float, default=5.0, help="Tempo máximo por execução em segundos (default 5)")
    ap.add_argument("--message", default="oi", help="Mensagem a enviar (default oi)")
    ap.add_argument("--sender", default="user", help="Sender (default user)")
    args = ap.parse_args()

    script = JARVIS_DIR / "run_jarvis_message.py"
    if not script.exists():
        print(f"Erro: {script} não encontrado", file=sys.stderr)
        sys.exit(1)

    cmd = [
        sys.executable,
        str(script),
        "--message", args.message,
        "--sender", args.sender,
    ]
    ok = 0
    slow = []
    failed = []

    print(f"Rodando {args.runs} execuções (máx {args.max_seconds}s cada), cwd={JARVIS_DIR}")
    for i in range(args.runs):
        t0 = time.perf_counter()
        r = subprocess.run(
            cmd,
            cwd=str(JARVIS_DIR),
            capture_output=True,
            timeout=args.max_seconds + 5,
        )
        elapsed = time.perf_counter() - t0
        if r.returncode == 0:
            ok += 1
            if elapsed > args.max_seconds:
                slow.append((i + 1, elapsed))
        else:
            failed.append((i + 1, r.returncode, (r.stderr or b"").decode(errors="replace")[-500:]))

    print(f"\nResultado: {ok}/{args.runs} ok")
    if slow:
        print(f"  Lentas (> {args.max_seconds}s): {len(slow)}")
        for run_id, sec in slow[:10]:
            print(f"    run {run_id}: {sec:.2f}s")
        if len(slow) > 10:
            print(f"    ... e mais {len(slow) - 10}")
    if failed:
        print(f"  Falhas: {len(failed)}")
        for run_id, code, tail in failed[:5]:
            print(f"    run {run_id} exit={code}")
            print(f"      stderr tail: {tail[:200]!r}")
        if len(failed) > 5:
            print(f"    ... e mais {len(failed) - 5}")
        sys.exit(1)
    if slow and len(slow) == args.runs:
        print("  Aviso: todas as execuções foram lentas")
    print("  OK: todas finalizaram em tempo aceitável.")
    sys.exit(0)


if __name__ == "__main__":
    main()
