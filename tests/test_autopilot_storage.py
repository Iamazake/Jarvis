#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste automatizado: Autopilot + Storage compartilhado entre processos.

Prova que:
  1) ContextManager usa path absoluto determinístico (JARVIS_DATA_DIR ou <repo>/data).
  2) Autopilot ON  → run_jarvis_message.py NÃO retorna "not_in_autopilot".
  3) Autopilot OFF → run_jarvis_message.py retorna reason="not_in_autopilot" (nunca "no_response").
  4) Storage é o MESMO entre este processo e o subprocess (run_jarvis_message.py).

Uso:
  cd jarvis
  python -m tests.test_autopilot_storage
  # ou
  python tests/test_autopilot_storage.py
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# ─── Setup de paths ───
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent  # jarvis/
RUN_SCRIPT = REPO_ROOT / "run_jarvis_message.py"

# Garantir imports do repo
sys.path.insert(0, str(REPO_ROOT))

TEST_JID = "5500000000001@s.whatsapp.net"
TEST_SENDER = "TestBot"
TEST_MESSAGE = "oi teste autopilot"

PYTHON = sys.executable or "python"

passed = 0
failed = 0


def log(status: str, name: str, detail: str = ""):
    symbol = "✅" if status == "PASS" else "❌"
    suffix = f" — {detail}" if detail else ""
    print(f"  {symbol} {name}{suffix}")


def run_subprocess(jid: str, message: str = TEST_MESSAGE, sender: str = TEST_SENDER,
                   env_extra: dict = None, timeout: int = 30):
    """
    Roda run_jarvis_message.py em subprocess e retorna (stdout_json, stderr_text, exit_code).
    Usa JARVIS_DATA_DIR para apontar pro mesmo storage.
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "JARVIS_TIMING_LOG": "0"}
    if env_extra:
        env.update(env_extra)

    args = [PYTHON, str(RUN_SCRIPT), "--message", message]
    if jid:
        args.extend(["--jid", jid])
    args.extend(["--sender", sender])

    proc = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    # Parse primeira linha JSON do stdout (mesma lógica robusta do Node)
    result = None
    for line in stdout.split("\n"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            result = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    return result, stderr, proc.returncode


# ─── Testes ───

def test_1_storage_path_deterministic():
    """ContextManager usa path absoluto, mesmo quando CWD muda."""
    global passed, failed
    from core.context_manager import ContextManager

    original_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    try:
        ctx1 = ContextManager()
        path1 = ctx1.storage_path

        # Mudar CWD para temp e criar outro ContextManager
        os.chdir(tmpdir)
        ctx2 = ContextManager()
        path2 = ctx2.storage_path

        # Voltar ao CWD original ANTES de remover tmpdir
        os.chdir(original_cwd)

        if path1 == path2:
            log("PASS", "storage_path determinístico", f"path={path1}")
            passed += 1
        else:
            log("FAIL", "storage_path determinístico", f"path1={path1} != path2={path2}")
            failed += 1
    except Exception as e:
        log("FAIL", "storage_path determinístico", str(e))
        failed += 1
    finally:
        try:
            os.chdir(original_cwd)
        except Exception:
            pass
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


def test_2_storage_path_shared_with_subprocess():
    """O subprocess usa o mesmo storage_path que este processo."""
    global passed, failed
    from core.context_manager import ContextManager

    ctx = ContextManager()
    our_path = ctx.storage_path

    # Rodar subprocess que imprime o storage_path
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [PYTHON, "-c",
         "import sys; sys.path.insert(0,'.'); "
         "from core.context_manager import ContextManager; "
         "print(ContextManager().storage_path)"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    sub_path = proc.stdout.strip()

    if our_path == sub_path:
        log("PASS", "storage compartilhado com subprocess", f"path={our_path}")
        passed += 1
    else:
        log("FAIL", "storage compartilhado com subprocess",
            f"nosso={our_path} sub={sub_path} stderr={proc.stderr[:200]}")
        failed += 1


def test_3_autopilot_off_returns_not_in_autopilot():
    """Com autopilot OFF para o JID, run_jarvis_message retorna reason=not_in_autopilot."""
    global passed, failed
    from core.context_manager import ContextManager

    ctx = ContextManager()
    ctx.disable_autopilot(TEST_JID)  # returns (bool, removed_info)

    result, stderr, code = run_subprocess(TEST_JID)

    if result is None:
        log("FAIL", "autopilot OFF → not_in_autopilot", f"stdout não é JSON. stderr={stderr[:300]}")
        failed += 1
        return

    reason = result.get("reason", "")
    action = result.get("action", "")

    if action == "ignore" and reason == "not_in_autopilot":
        log("PASS", "autopilot OFF → not_in_autopilot")
        passed += 1
    else:
        log("FAIL", "autopilot OFF → not_in_autopilot",
            f"got action={action} reason={reason} (esperado ignore/not_in_autopilot)")
        failed += 1


def test_4_autopilot_on_does_not_return_not_in_autopilot():
    """Com autopilot ON, run_jarvis_message NÃO retorna not_in_autopilot."""
    global passed, failed
    from core.context_manager import ContextManager

    ctx = ContextManager()
    ctx.enable_autopilot(TEST_JID, display_name="TestBot", tone="profissional", ttl_minutes=5)

    result, stderr, code = run_subprocess(TEST_JID)

    if result is None:
        log("FAIL", "autopilot ON → sem not_in_autopilot", f"stdout não é JSON. stderr={stderr[:300]}")
        failed += 1
        return

    reason = result.get("reason", "")
    action = result.get("action", "")

    if reason == "not_in_autopilot":
        log("FAIL", "autopilot ON → sem not_in_autopilot",
            f"recebeu not_in_autopilot apesar de autopilot estar ON!")
        failed += 1
    else:
        # Aceita reply OU no_response/error (se AI não estiver configurada), mas não not_in_autopilot
        log("PASS", "autopilot ON → sem not_in_autopilot",
            f"action={action} reason={reason}")
        passed += 1

    # Cleanup: desabilitar autopilot do JID de teste
    ctx.disable_autopilot(TEST_JID)  # returns (bool, removed_info)


def test_5_exactly_one_json_per_execution():
    """Garante que stdout tem exatamente 1 linha JSON (nunca duplo)."""
    global passed, failed
    from core.context_manager import ContextManager

    ctx = ContextManager()
    ctx.disable_autopilot(TEST_JID)  # returns (bool, removed_info)

    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "JARVIS_TIMING_LOG": "0"}
    proc = subprocess.run(
        [PYTHON, str(RUN_SCRIPT), "--message", TEST_MESSAGE, "--jid", TEST_JID, "--sender", TEST_SENDER],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    stdout_lines = [l.strip() for l in proc.stdout.strip().split("\n") if l.strip()]
    json_lines = []
    for line in stdout_lines:
        try:
            json.loads(line)
            json_lines.append(line)
        except json.JSONDecodeError:
            pass

    if len(json_lines) == 1:
        log("PASS", "exatamente 1 JSON no stdout", f"json={json_lines[0][:100]}")
        passed += 1
    else:
        log("FAIL", "exatamente 1 JSON no stdout",
            f"encontrado {len(json_lines)} JSONs: {json_lines}")
        failed += 1


def test_6_context_state_persistence():
    """enable_autopilot persiste no context_state.json; disable_autopilot remove."""
    global passed, failed
    tmpdir = tempfile.mkdtemp()
    state_file = Path(tmpdir) / "context_state.json"
    env = {**os.environ, "JARVIS_DATA_DIR": tmpdir, "PYTHONIOENCODING": "utf-8"}
    try:
        # Subprocess com JARVIS_DATA_DIR=tmpdir para enable (path correto no import)
        proc_enable = subprocess.run(
            [PYTHON, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from core.context_manager import ContextManager; "
             "ctx = ContextManager(); "
             "ctx.enable_autopilot('5500000000001@s.whatsapp.net', display_name='TestBot', tone='profissional', ttl_minutes=5)"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc_enable.returncode != 0:
            log("FAIL", "context_state persistência (enable)", proc_enable.stderr or proc_enable.stdout)
            failed += 1
            return
        if not state_file.exists():
            log("FAIL", "context_state persistência (enable)", "arquivo não foi criado")
            failed += 1
            return
        data = json.loads(state_file.read_text(encoding="utf-8"))
        ap = data.get("autopilot_contacts", {})
        key = TEST_JID.strip().lower()
        if key not in ap or not ap[key].get("enabled", True):
            log("FAIL", "context_state persistência (enable)", f"jid não encontrado ou disabled em {list(ap.keys())}")
            failed += 1
            return
        log("PASS", "context_state persistência (enable)", f"jid={key} enabled no arquivo")
        passed += 1

        # Subprocess com JARVIS_DATA_DIR=tmpdir para disable
        subprocess.run(
            [PYTHON, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from core.context_manager import ContextManager; "
             "ctx = ContextManager(); "
             "ctx.disable_autopilot('5500000000001@s.whatsapp.net')"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        data2 = json.loads(state_file.read_text(encoding="utf-8"))
        ap2 = data2.get("autopilot_contacts", {})
        if key in ap2:
            log("FAIL", "context_state persistência (disable)", f"jid ainda em autopilot_contacts: {list(ap2.keys())}")
            failed += 1
        else:
            log("PASS", "context_state persistência (disable)", "jid removido do arquivo")
            passed += 1
    except Exception as e:
        log("FAIL", "context_state persistência", str(e))
        failed += 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_7_non_whatsapp_ctx_none_safe():
    """Quando jid não tem @, ctx=None não causa crash (NameError)."""
    global passed, failed

    result, stderr, code = run_subprocess(jid="", sender="user", message="teste sem jid")

    # Sem JID com @, não é whatsapp → pode ser reply (CLI) ou ignore
    if result is not None:
        reason = result.get("reason", "")
        if reason == "not_in_autopilot":
            # Sem JID com @, não deve cair em whatsapp/autopilot check
            log("FAIL", "ctx=None safe (sem JID)", f"não devia checar autopilot sem JID: reason={reason}")
            failed += 1
        else:
            log("PASS", "ctx=None safe (sem JID)", f"action={result.get('action')} reason={reason}")
            passed += 1
    elif "NameError" in stderr or "ctx" in stderr.lower():
        log("FAIL", "ctx=None safe (sem JID)", f"NameError/crash: {stderr[:300]}")
        failed += 1
    else:
        log("PASS", "ctx=None safe (sem JID)", "executou sem crash")
        passed += 1


# ─── Main ───

def main():
    global passed, failed

    print("=" * 60)
    print("  TESTE: Autopilot Storage & Fluxo")
    print(f"  Python: {PYTHON}")
    print(f"  Repo:   {REPO_ROOT}")
    print(f"  Script: {RUN_SCRIPT}")
    print("=" * 60)
    print()

    tests = [
        test_1_storage_path_deterministic,
        test_2_storage_path_shared_with_subprocess,
        test_3_autopilot_off_returns_not_in_autopilot,
        test_4_autopilot_on_does_not_return_not_in_autopilot,
        test_5_exactly_one_json_per_execution,
        test_6_context_state_persistence,
        test_7_non_whatsapp_ctx_none_safe,
    ]

    for test_fn in tests:
        name = test_fn.__doc__ or test_fn.__name__
        print(f"▶ {name.strip()}")
        try:
            test_fn()
        except Exception as e:
            log("FAIL", test_fn.__name__, f"Exception: {e}")
            failed += 1
        print()

    print("=" * 60)
    total = passed + failed
    print(f"  Resultado: {passed}/{total} PASS, {failed}/{total} FAIL")
    print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
