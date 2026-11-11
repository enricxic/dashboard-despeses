"""
scripts/check_control.py
Eina de línia de comandes i verificador pre-commit del mòdul '🛡️ Control'.

Ús habitual:
  python scripts/check_control.py --staged
  python scripts/check_control.py status
  python scripts/check_control.py unlock compres --motiu "Corregir bug" --hores 24
  python scripts/check_control.py seal compres --notes "Verificat a producció"
  python scripts/check_control.py backup manteniment --motiu "Abans de reforma UI"
  python scripts/check_control.py test --fast
  python scripts/check_control.py test --module compres --full
"""

import argparse
import os
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.control_manager import (
    LEVEL_META,
    build_initial_registry,
    check_staged_changes,
    create_backup_snapshot,
    evaluate_all_modules,
    load_registry,
    save_registry,
    seal_module,
    unlock_module,
)


def _get_staged_files():
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def cmd_staged() -> int:
    staged = _get_staged_files()
    if not staged:
        print("[Control] Cap fitxer preparat per a commit.")
        return 0

    allowed, messages, warnings = check_staged_changes(staged)
    for w in warnings:
        print(f"[AVÍS CONTROL] {w}")
    for m in messages:
        prefix = "[BLOCAT]" if not allowed else "[OK]"
        print(f"{prefix} {m}")

    if not allowed:
        print("\nCommit aturat per la política de protecció de mòduls '🛡️ Control'.")
        return 1
    return 0


def cmd_status() -> int:
    reg = load_registry()
    statuses = evaluate_all_modules(reg)
    for mid, st_info in statuses.items():
        meta = LEVEL_META.get(st_info["level"], {})
        icon = meta.get("short", st_info["level"]).upper()
        chg = f" | canvis: {', '.join(st_info['changed_files'])}" if st_info["changed_files"] else ""
        unl = f" | desbloquejat fins {st_info['unlocked_until']}" if st_info["unlocked"] else ""
        print(f"- {mid:15s} [{icon:7s}] estat={st_info['state']}{chg}{unl}")
    return 0


def cmd_test(module: str = "", full: bool = False) -> int:
    env = os.environ.copy()
    if module:
        env["CONTROL_TEST_MODULE"] = module
    if full:
        env["CONTROL_FULL_APPTEST"] = "1"
    test_file = os.path.join(PROJECT_ROOT, "tests", "smoke", "test_modules_smoke.py")
    proc = subprocess.run([sys.executable, test_file], cwd=PROJECT_ROOT, env=env)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificador Control de Mòduls")
    parser.add_argument("--staged", action="store_true", help="Valida els fitxers staged per a Git pre-commit")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Mostra l'estat de tots els mòduls")
    sub.add_parser("init", help="Regenera el registre base data/control_registry.json")

    p_unlock = sub.add_parser("unlock", help="Desbloqueja temporalment un mòdul blindat")
    p_unlock.add_argument("module")
    p_unlock.add_argument("--motiu", required=True)
    p_unlock.add_argument("--hores", type=int, default=24)

    p_seal = sub.add_parser("seal", help="Verifica i segella el hash actual d'un mòdul")
    p_seal.add_argument("module")
    p_seal.add_argument("--notes", default="")

    p_bak = sub.add_parser("backup", help="Crea una còpia de seguretat manual d'un mòdul")
    p_bak.add_argument("module")
    p_bak.add_argument("--motiu", default="manual_cli")

    p_test = sub.add_parser("test", help="Executa les proves de regressió")
    p_test.add_argument("--module", default="")
    p_test.add_argument("--fast", action="store_true")
    p_test.add_argument("--full", action="store_true")

    args = parser.parse_args()
    if args.staged:
        return cmd_staged()
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "init":
        reg = build_initial_registry()
        save_registry(reg, sync_cloud=False)
        print("Registre inicialitzat a data/control_registry.json")
        return 0
    if args.cmd == "unlock":
        ok, msg = unlock_module(args.module, args.motiu, hours=args.hores)
        print(msg)
        return 0 if ok else 1
    if args.cmd == "seal":
        ok, msg = seal_module(args.module, notes=args.notes)
        print(msg)
        return 0 if ok else 1
    if args.cmd == "backup":
        snap = create_backup_snapshot(args.module, reason=args.motiu, source="disk")
        print(f"Còpia creada: {snap}" if snap else "No s'ha pogut crear la còpia.")
        return 0 if snap else 1
    if args.cmd == "test":
        return cmd_test(module=args.module, full=args.full)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
