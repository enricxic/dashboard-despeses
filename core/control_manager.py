"""
core/control_manager.py
Motor central del mòdul '🛡️ Control':
- 3 nivells de protecció per mòdul:
  * blindat: Bloquejat. Cap modificació permesa sense consentiment i desbloqueig explícit.
  * vigilat: Funcionament sense tancar. Modificacions vigilades amb còpia de seguretat automàtica i proves.
  * obert:   Nova construcció. Canvis lliures amb punts de control i rollback fàcil.
- Registre SHA-256 normalitzat (LF) a data/control_registry.json (+ sincronització opcional a Supabase id=12).
- Gestor de còpies de seguretat i restauració a data/control_backups/ (no pujat a Git).
- Verificació per a hook pre-commit de Git i execució de tests de regressió.
"""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_CURR_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_CURR_DIR, ".."))
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "data", "control_registry.json")
BACKUPS_ROOT = os.path.join(PROJECT_ROOT, "data", "control_backups")
CONFIG_ID_CONTROL = 12
MAX_BACKUPS_PER_MODULE = 20

LEVEL_BLINDAT = "blindat"
LEVEL_VIGILAT = "vigilat"
LEVEL_OBERT = "obert"

VALID_LEVELS = (LEVEL_BLINDAT, LEVEL_VIGILAT, LEVEL_OBERT)

LEVEL_META: Dict[str, Dict[str, str]] = {
    LEVEL_BLINDAT: {
        "icon": "🔒",
        "label": "Blindat (Bloquejat)",
        "short": "Blindat",
        "color": "#ef4444",
        "desc": "Mòdul verificat i tancat. Bloqueja qualsevol modificació o commit sense consentiment i desbloqueig explícit.",
    },
    LEVEL_VIGILAT: {
        "icon": "🛡️",
        "label": "Vigilat (En funcionament)",
        "short": "Vigilat",
        "color": "#f59e0b",
        "desc": "En ús però pendent d'acabar. Permet canvis vigilats generant còpia de seguretat automàtica i passant comprovacions.",
    },
    LEVEL_OBERT: {
        "icon": "🔓",
        "label": "Obert (Nova construcció)",
        "short": "Obert",
        "color": "#10b981",
        "desc": "En construcció. Canvis oberts amb punts de control (snapshots) i comprovació sintàctica per poder tornar enrere.",
    },
}

# Definició canònica de mòduls i agrupació inicial sol·licitada
DEFAULT_MODULES: Dict[str, Dict[str, Any]] = {
    # === GRUP 1: BLINDAT ===
    "compres": {
        "name": "Compres Super",
        "icon": "🛒",
        "level": LEVEL_BLINDAT,
        "files": ["modules/compres.py"],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Entrada manual amb càlcul en viu de TOTAL LÍNIA (manual_tot_linea_disp)",
            "Commit natiu d'inputs numèrics amb Enter i botó Entrar línia (cb_add_ticket_line)",
            "Pujada de fitxer i càmera posterior al mòbil",
        ],
    },
    "economic": {
        "name": "Econòmic",
        "icon": "📈",
        "level": LEVEL_BLINDAT,
        "files": ["modules/economic.py"],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Càrrega ràpida reutilitzant cau central de core/db.py (sense DBTracker local)",
            "Pestanyes Ingrés/Despesa, Previsions, Inversions, Estalvis i Xat IA",
        ],
    },
    "cotxe": {
        "name": "Cotxe",
        "icon": "🚗",
        "level": LEVEL_BLINDAT,
        "files": ["modules/cotxe.py"],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Validació estricta d'odòmetre (contador_val > last_km)",
            "Km i rutes, repostatge, manteniment i consum",
        ],
    },
    "dashboard": {
        "name": "Dashboard",
        "icon": "📊",
        "level": LEVEL_BLINDAT,
        "files": ["modules/dashboard.py"],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Resum general KPI i gràfiques sense excepcions",
        ],
    },
    # === GRUP 2: VIGILAT (FUNCIONAMENT SENSE TANCAR) ===
    "llum_aigua": {
        "name": "Llum i Aigua",
        "icon": "💡",
        "level": LEVEL_VIGILAT,
        "files": [
            "modules/llum_aigua.py",
            "core/llum_manager.py",
            "core/aigua_manager.py",
        ],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Preus PVPC horaris, estudi solar PVGIS, factures llum (id=9) i aigua (id=10)",
        ],
    },
    "admin": {
        "name": "Configuració",
        "icon": "⚙️",
        "level": LEVEL_VIGILAT,
        "files": [
            "modules/admin.py",
            "core/config_manager.py",
        ],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Persistència de configuració global a Supabase (app_config id=2)",
        ],
    },
    "manteniment": {
        "name": "Manteniment",
        "icon": "🛠️",
        "level": LEVEL_VIGILAT,
        "files": [
            "modules/manteniment.py",
            "modules/projectes_ui.py",
            "modules/canvas_planol.py",
            "modules/canvas_electric.py",
            "core/manteniment_manager.py",
            "core/projectes_manager.py",
            "core/ai_projectes.py",
        ],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Projectes: Supabase prioritari sobre JSON i desat síncron (id=11)",
            "Visualització de fotos via bytes (decode_image_for_st)",
            "Editor gràfic de plànol col·lapsat per defecte (expanded=False)",
        ],
    },
    "menjar": {
        "name": "Menjar",
        "icon": "🍽️",
        "level": LEVEL_VIGILAT,
        "files": [
            "modules/menjar.py",
            "core/harness.py",
            "core/validator.py",
        ],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Menú setmanal, receptes, mise en place i validador nutricional",
        ],
    },
    "core_compartit": {
        "name": "Nucli Compartit (App & BD)",
        "icon": "🧱",
        "level": LEVEL_VIGILAT,
        "files": [
            "app.py",
            "core/db.py",
            "core/auth.py",
            "core/alerts.py",
        ],
        "depends_on": [],
        "contracts": [
            "Canvis aquí afecten els mòduls Blindats: requereixen còpia i proves transversals",
        ],
    },
    "control": {
        "name": "Control i Protecció",
        "icon": "🛡️",
        "level": LEVEL_VIGILAT,
        "files": [
            "modules/control.py",
            "core/control_manager.py",
            "scripts/check_control.py",
        ],
        "depends_on": [],
        "contracts": [
            "Protecció de mòduls per nivells, backups i proves de regressió",
        ],
    },
    # === GRUP 3: OBERT (NOVA CONSTRUCCIÓ) ===
    "calendari": {
        "name": "Calendari",
        "icon": "📅",
        "level": LEVEL_OBERT,
        "files": [
            "modules/calendari.py",
            "core/calendar_manager.py",
            "core/google_calendar_api.py",
        ],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Agenda, esdeveniments i sincronització Google Calendar",
        ],
    },
    "medicacio": {
        "name": "Medicació",
        "icon": "💊",
        "level": LEVEL_OBERT,
        "files": [
            "modules/medicacio.py",
            "core/medication_manager.py",
        ],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Preses d'avui, plans de medicació i notificacions",
        ],
    },
    "seguretat": {
        "name": "Seguretat",
        "icon": "📹",
        "level": LEVEL_OBERT,
        "files": ["modules/seguretat.py"],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Càmeres i alertes de seguretat",
        ],
    },
    "domotica": {
        "name": "Domòtica",
        "icon": "📶",
        "level": LEVEL_OBERT,
        "files": ["modules/domotica.py"],
        "depends_on": ["core_compartit"],
        "contracts": [
            "Integració Home Assistant",
        ],
    },
}


def _now_str() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def _normalize_rel(rel_path: str) -> str:
    return rel_path.replace("\\", "/").lstrip("./")


def _abs_path(rel_path: str) -> str:
    return os.path.join(PROJECT_ROOT, *_normalize_rel(rel_path).split("/"))


def compute_bytes_sha256(raw: bytes) -> str:
    """Calcula SHA-256 normalitzant salts de línia CRLF -> LF per evitar falsos positius Windows/Linux."""
    normalized = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def compute_file_sha256(rel_path: str) -> Optional[str]:
    abs_p = _abs_path(rel_path)
    if not os.path.isfile(abs_p):
        return None
    with open(abs_p, "rb") as f:
        return compute_bytes_sha256(f.read())


def _run_git(args: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)


def is_git_available() -> bool:
    return os.path.exists(os.path.join(PROJECT_ROOT, ".git"))


def get_git_head_short() -> str:
    if not is_git_available():
        return "sense-git"
    rc, out, _ = _run_git(["rev-parse", "--short", "HEAD"])
    return out.strip() if rc == 0 else "desconegut"


def get_git_head_bytes(rel_path: str) -> Optional[bytes]:
    if not is_git_available():
        return None
    norm = _normalize_rel(rel_path)
    try:
        proc = subprocess.run(
            ["git", "show", f"HEAD:{norm}"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout
    except Exception:
        pass
    return None


def _sync_registry_to_supabase(registry: Dict[str, Any]) -> bool:
    """Desat opcional al núvol (app_config id=12) quan hi ha sessió Streamlit / Supabase disponible."""
    try:
        from core.db import get_supabase_client
        role = "admin"
        try:
            import streamlit as st
            if st.session_state.get("is_offline"):
                return False
            role = st.session_state.get("role", "admin")
        except Exception:
            pass
        supabase = get_supabase_client(role)
        if not supabase:
            return False
        supabase.table("app_config").upsert(
            {"id": CONFIG_ID_CONTROL, "config_json": registry}
        ).execute()
        return True
    except Exception:
        return False


def _append_audit(registry: Dict[str, Any], action: str, mod_id: str, detail: str, user: str = "admin") -> None:
    log = registry.setdefault("audit_log", [])
    log.insert(
        0,
        {
            "timestamp": _now_str(),
            "action": action,
            "module": mod_id,
            "detail": detail,
            "user": user,
            "git_head": get_git_head_short(),
        },
    )
    del log[100:]


def build_initial_registry() -> Dict[str, Any]:
    modules_data: Dict[str, Dict[str, Any]] = {}
    now = _now_str()
    head = get_git_head_short()
    for mod_id, cfg in DEFAULT_MODULES.items():
        hashes: Dict[str, str] = {}
        for rel in cfg["files"]:
            h = compute_file_sha256(rel)
            if h is not None:
                hashes[_normalize_rel(rel)] = h
        modules_data[mod_id] = {
            "name": cfg["name"],
            "icon": cfg["icon"],
            "level": cfg["level"],
            "files": [_normalize_rel(p) for p in cfg["files"]],
            "depends_on": list(cfg.get("depends_on", [])),
            "contracts": list(cfg.get("contracts", [])),
            "verified_hashes": hashes,
            "verified_at": now,
            "verified_commit": head,
            "verified_by": "admin",
            "unlocked_until": None,
            "unlock_reason": "",
        }
    reg = {
        "version": 1,
        "updated_at": now,
        "modules": modules_data,
        "audit_log": [
            {
                "timestamp": now,
                "action": "INIT",
                "module": "global",
                "detail": "Registre inicial creat amb els 3 nivells (Blindat / Vigilat / Obert)",
                "user": "admin",
                "git_head": head,
            }
        ],
    }
    return reg


def load_registry() -> Dict[str, Any]:
    if not os.path.exists(REGISTRY_PATH):
        reg = build_initial_registry()
        save_registry(reg, sync_cloud=False)
        return reg
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            reg = json.load(f)
    except Exception:
        reg = build_initial_registry()
        save_registry(reg, sync_cloud=False)
        return reg

    # Completar mòduls nous definits al codi que encara no constin al JSON
    changed = False
    mods = reg.setdefault("modules", {})
    now = _now_str()
    head = get_git_head_short()
    for mod_id, cfg in DEFAULT_MODULES.items():
        if mod_id not in mods:
            hashes = {}
            for rel in cfg["files"]:
                h = compute_file_sha256(rel)
                if h is not None:
                    hashes[_normalize_rel(rel)] = h
            mods[mod_id] = {
                "name": cfg["name"],
                "icon": cfg["icon"],
                "level": cfg["level"],
                "files": [_normalize_rel(p) for p in cfg["files"]],
                "depends_on": list(cfg.get("depends_on", [])),
                "contracts": list(cfg.get("contracts", [])),
                "verified_hashes": hashes,
                "verified_at": now,
                "verified_commit": head,
                "verified_by": "admin",
                "unlocked_until": None,
                "unlock_reason": "",
            }
            changed = True
    if changed:
        save_registry(reg, sync_cloud=False)
    return reg


def save_registry(registry: Dict[str, Any], sync_cloud: bool = True) -> bool:
    registry["updated_at"] = _now_str()
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    if sync_cloud:
        _sync_registry_to_supabase(registry)
    return True


def is_unlock_active(mod_entry: Dict[str, Any]) -> bool:
    until_str = mod_entry.get("unlocked_until")
    if not until_str:
        return False
    try:
        until_dt = datetime.strptime(until_str, "%d/%m/%Y %H:%M:%S")
        return datetime.now() <= until_dt
    except Exception:
        return False


def evaluate_module(registry: Dict[str, Any], mod_id: str) -> Dict[str, Any]:
    mod_entry = registry["modules"][mod_id]
    verified = mod_entry.get("verified_hashes", {})
    changed_files: List[str] = []
    missing_files: List[str] = []
    current_hashes: Dict[str, str] = {}

    for rel in mod_entry.get("files", []):
        norm = _normalize_rel(rel)
        cur_h = compute_file_sha256(norm)
        if cur_h is None:
            missing_files.append(norm)
        else:
            current_hashes[norm] = cur_h
            exp_h = verified.get(norm)
            if exp_h != cur_h:
                changed_files.append(norm)

    unlocked = is_unlock_active(mod_entry)
    level = mod_entry.get("level", LEVEL_OBERT)

    if missing_files:
        state = "MISSING"
    elif changed_files:
        state = "MODIFICAT_AUTORITZAT" if (level == LEVEL_BLINDAT and unlocked) else "MODIFICAT"
    elif level == LEVEL_BLINDAT and unlocked:
        state = "DESBLOQUEJAT"
    else:
        state = "OK"

    return {
        "module_id": mod_id,
        "name": mod_entry.get("name", mod_id),
        "icon": mod_entry.get("icon", "📦"),
        "level": level,
        "state": state,
        "unlocked": unlocked,
        "unlocked_until": mod_entry.get("unlocked_until"),
        "unlock_reason": mod_entry.get("unlock_reason", ""),
        "changed_files": changed_files,
        "missing_files": missing_files,
        "current_hashes": current_hashes,
        "verified_at": mod_entry.get("verified_at", ""),
        "verified_commit": mod_entry.get("verified_commit", ""),
    }


def evaluate_all_modules(registry: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    if registry is None:
        registry = load_registry()
    return {mod_id: evaluate_module(registry, mod_id) for mod_id in registry.get("modules", {})}


def get_dependents(registry: Dict[str, Any], target_mod_id: str) -> List[str]:
    dependents = []
    for mid, m in registry.get("modules", {}).items():
        if target_mod_id in m.get("depends_on", []):
            dependents.append(mid)
    return dependents


def find_modules_for_file(registry: Dict[str, Any], rel_path: str) -> List[str]:
    norm = _normalize_rel(rel_path)
    matched = []
    for mod_id, entry in registry.get("modules", {}).items():
        if norm in [_normalize_rel(p) for p in entry.get("files", [])]:
            matched.append(mod_id)
    return matched


def _prune_old_backups(mod_id: str) -> None:
    mod_dir = os.path.join(BACKUPS_ROOT, mod_id)
    if not os.path.isdir(mod_dir):
        return
    entries = sorted(
        [d for d in os.listdir(mod_dir) if os.path.isdir(os.path.join(mod_dir, d))],
        reverse=True,
    )
    for old in entries[MAX_BACKUPS_PER_MODULE:]:
        shutil.rmtree(os.path.join(mod_dir, old), ignore_errors=True)


def create_backup_snapshot(
    mod_id: str,
    reason: str = "manual",
    source: str = "auto",
    registry: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Crea una còpia de seguretat dels fitxers d'un mòdul a data/control_backups/<mod_id>/.
    - source='head': prioritzarà la versió neta de git HEAD (ideal abans de confirmar canvis).
    - source='disk': desarà la versió actual al disc.
    - source='auto': per cada fitxer, si existeix a git HEAD i difereix del disc sense haver estat desat, usa HEAD si es demana, o disc per snapshots manuals.
    """
    if registry is None:
        registry = load_registry()
    mod_entry = registry["modules"].get(mod_id)
    if not mod_entry:
        return None

    safe_reason = re.sub(r"[^a-zA-Z0-9_-]+", "_", reason.strip().lower())[:36] or "backup"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_dir = os.path.join(BACKUPS_ROOT, mod_id, f"{stamp}_{safe_reason}")
    os.makedirs(snap_dir, exist_ok=True)

    saved_files: Dict[str, Dict[str, str]] = {}
    for rel in mod_entry.get("files", []):
        norm = _normalize_rel(rel)
        raw_bytes: Optional[bytes] = None
        used_source = "disk"

        if source == "head":
            raw_bytes = get_git_head_bytes(norm)
            if raw_bytes is not None:
                used_source = "git_head"

        if raw_bytes is None:
            abs_p = _abs_path(norm)
            if os.path.isfile(abs_p):
                with open(abs_p, "rb") as f:
                    raw_bytes = f.read()
                used_source = "disk"

        if raw_bytes is None:
            continue

        dest_p = os.path.join(snap_dir, *norm.split("/"))
        os.makedirs(os.path.dirname(dest_p), exist_ok=True)
        with open(dest_p, "wb") as f:
            f.write(raw_bytes)
        saved_files[norm] = {
            "sha256": compute_bytes_sha256(raw_bytes),
            "source": used_source,
        }

    if not saved_files:
        shutil.rmtree(snap_dir, ignore_errors=True)
        return None

    manifest = {
        "module_id": mod_id,
        "module_name": mod_entry.get("name", mod_id),
        "level": mod_entry.get("level", LEVEL_OBERT),
        "created_at": _now_str(),
        "reason": reason,
        "git_head": get_git_head_short(),
        "files": saved_files,
    }
    with open(os.path.join(snap_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    _prune_old_backups(mod_id)
    return snap_dir


def list_backup_snapshots(mod_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not os.path.isdir(BACKUPS_ROOT):
        return []
    snapshots: List[Dict[str, Any]] = []
    target_mods = [mod_id] if mod_id else sorted(os.listdir(BACKUPS_ROOT))
    for mid in target_mods:
        mod_dir = os.path.join(BACKUPS_ROOT, mid)
        if not os.path.isdir(mod_dir):
            continue
        for folder in sorted(os.listdir(mod_dir), reverse=True):
            snap_dir = os.path.join(mod_dir, folder)
            man_path = os.path.join(snap_dir, "manifest.json")
            if os.path.isfile(man_path):
                try:
                    with open(man_path, "r", encoding="utf-8") as f:
                        man = json.load(f)
                    man["snapshot_dir"] = snap_dir
                    man["folder_name"] = folder
                    snapshots.append(man)
                except Exception:
                    pass
    snapshots.sort(key=lambda x: x.get("folder_name", ""), reverse=True)
    return snapshots


def restore_backup_snapshot(snapshot_dir: str, user: str = "admin") -> Tuple[bool, str, List[str]]:
    man_path = os.path.join(snapshot_dir, "manifest.json")
    if not os.path.isfile(man_path):
        return False, "No s'ha trobat manifest.json dins la còpia de seguretat.", []
    with open(man_path, "r", encoding="utf-8") as f:
        man = json.load(f)

    mod_id = man.get("module_id")
    registry = load_registry()
    if mod_id in registry.get("modules", {}):
        create_backup_snapshot(mod_id, reason="pre_restore_auto", source="disk", registry=registry)

    restored: List[str] = []
    for norm in man.get("files", {}).keys():
        src_p = os.path.join(snapshot_dir, *norm.split("/"))
        if os.path.isfile(src_p):
            dest_p = _abs_path(norm)
            os.makedirs(os.path.dirname(dest_p), exist_ok=True)
            shutil.copy2(src_p, dest_p)
            restored.append(norm)

    if mod_id in registry.get("modules", {}):
        _append_audit(
            registry,
            "RESTORE",
            mod_id,
            f"Restaurada còpia del {man.get('created_at', '?')} ({man.get('reason', '')})",
            user=user,
        )
        save_registry(registry)
    return True, f"Restaurats {len(restored)} fitxers de '{mod_id}'.", restored


def run_syntax_check(files: List[str]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for rel in files:
        norm = _normalize_rel(rel)
        if not norm.endswith(".py"):
            continue
        abs_p = _abs_path(norm)
        if not os.path.isfile(abs_p):
            errors.append(f"Fitxer inexistent: {norm}")
            continue
        try:
            py_compile.compile(abs_p, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"Error de sintaxi a {norm}: {e}")
    return len(errors) == 0, errors


def run_fast_contracts(mod_ids: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
    """
    Validacions estàtiques ultra-ràpides (<0.3s) per protegir invariants crítics
    dels mòduls sense haver d'esperar l'arrencada completa de Streamlit.
    """
    registry = load_registry()
    targets = mod_ids or list(registry.get("modules", {}).keys())
    issues: List[str] = []

    for mid in targets:
        entry = registry["modules"].get(mid)
        if not entry:
            continue
        ok_syn, syn_errs = run_syntax_check(entry.get("files", []))
        if not ok_syn:
            issues.extend(syn_errs)

        if mid == "compres":
            p = _abs_path("modules/compres.py")
            if os.path.isfile(p):
                txt = Path(p).read_text(encoding="utf-8", errors="replace")
                if 'key="manual_tot_linea_disp"' not in txt:
                    issues.append("Compres Super: falta clau estable key='manual_tot_linea_disp' a TOTAL LÍNIA.")
                if "isSelectboxInput" not in txt or "updateLiveTotal" not in txt:
                    issues.append("Compres Super: falta lògica de càlcul en viu (updateLiveTotal) o protecció d'Enter natiu.")
                if "def cb_add_ticket_line" not in txt:
                    issues.append("Compres Super: ha desaparegut cb_add_ticket_line().")

        elif mid == "economic":
            p = _abs_path("modules/economic.py")
            if os.path.isfile(p):
                txt = Path(p).read_text(encoding="utf-8", errors="replace")
                if "ensure_session_dfs" not in txt and "get_supabase_client" not in txt:
                    issues.append("Econòmic: falta integració de dades de core/db.py.")

        elif mid == "cotxe":
            p = _abs_path("modules/cotxe.py")
            if os.path.isfile(p):
                txt = Path(p).read_text(encoding="utf-8", errors="replace")
                if "contador_val" not in txt and "last_km" not in txt:
                    issues.append("Cotxe: falta validació estricta d'odòmetre (contador_val / last_km).")

        elif mid == "manteniment":
            p_mgr = _abs_path("core/projectes_manager.py")
            p_cnv = _abs_path("modules/canvas_planol.py")
            if os.path.isfile(p_mgr):
                txt = Path(p_mgr).read_text(encoding="utf-8", errors="replace")
                if "def decode_image_for_st" not in txt:
                    issues.append("Manteniment/Projectes: falta decode_image_for_st() per renderitzar imatges.")
            if os.path.isfile(p_cnv):
                txt_cnv = Path(p_cnv).read_text(encoding="utf-8", errors="replace")
                if "expanded=False" not in txt_cnv:
                    issues.append("Manteniment/Projectes: l'editor gràfic de plànol ha d'estar col·lapsat (expanded=False).")

    return len(issues) == 0, issues


def unlock_module(mod_id: str, reason: str, hours: int = 24, user: str = "admin") -> Tuple[bool, str]:
    reason = reason.strip()
    if not reason:
        return False, "Cal indicar un motiu explícit per autoritzar el desbloqueig."
    registry = load_registry()
    if mod_id not in registry["modules"]:
        return False, f"Mòdul '{mod_id}' desconegut."

    # Fer còpia de seguretat abans de tocar un mòdul blindat/vigilat
    create_backup_snapshot(mod_id, reason="pre_unlock", source="head", registry=registry)

    until_dt = datetime.now() + timedelta(hours=max(1, int(hours)))
    until_str = until_dt.strftime("%d/%m/%Y %H:%M:%S")
    mod_entry = registry["modules"][mod_id]
    mod_entry["unlocked_until"] = until_str
    mod_entry["unlock_reason"] = reason
    _append_audit(registry, "UNLOCK", mod_id, f"Autoritzat fins {until_str}. Motiu: {reason}", user=user)
    save_registry(registry)
    return True, f"Mòdul '{mod_entry['name']}' desbloquejat fins {until_str} (còpia de seguretat creada)."


def seal_module(mod_id: str, notes: str = "", user: str = "admin", run_checks: bool = True) -> Tuple[bool, str]:
    registry = load_registry()
    if mod_id not in registry["modules"]:
        return False, f"Mòdul '{mod_id}' desconegut."

    mod_entry = registry["modules"][mod_id]
    if run_checks:
        ok, issues = run_fast_contracts([mod_id])
        if not ok:
            return False, "No es pot segellar perquè hi ha errors:\n- " + "\n- ".join(issues)

    # Còpia de seguretat prèvia al nou segellat
    create_backup_snapshot(mod_id, reason="verified_seal", source="disk", registry=registry)

    new_hashes: Dict[str, str] = {}
    for rel in mod_entry.get("files", []):
        norm = _normalize_rel(rel)
        h = compute_file_sha256(norm)
        if h is None:
            return False, f"Falta el fitxer '{norm}'."
        new_hashes[norm] = h

    mod_entry["verified_hashes"] = new_hashes
    mod_entry["verified_at"] = _now_str()
    mod_entry["verified_commit"] = get_git_head_short()
    mod_entry["verified_by"] = user
    mod_entry["unlocked_until"] = None
    mod_entry["unlock_reason"] = ""
    detail = "Versió verificada i segellada"
    if notes.strip():
        detail += f" ({notes.strip()})"
    _append_audit(registry, "SEAL", mod_id, detail, user=user)
    save_registry(registry)
    return True, f"Mòdul '{mod_entry['name']}' verificat i segellat correctament."


def set_module_level(mod_id: str, new_level: str, user: str = "admin") -> Tuple[bool, str]:
    if new_level not in VALID_LEVELS:
        return False, f"Nivell invàlid: {new_level}"
    registry = load_registry()
    if mod_id not in registry["modules"]:
        return False, f"Mòdul '{mod_id}' desconegut."
    mod_entry = registry["modules"][mod_id]
    old_level = mod_entry.get("level")
    if old_level == new_level:
        return True, "El mòdul ja té aquest nivell."
    mod_entry["level"] = new_level
    if new_level != LEVEL_BLINDAT:
        mod_entry["unlocked_until"] = None
        mod_entry["unlock_reason"] = ""
    _append_audit(registry, "LEVEL_CHANGE", mod_id, f"{old_level} -> {new_level}", user=user)
    save_registry(registry)
    return True, f"Nivell canviat de '{old_level}' a '{new_level}'."


def get_git_diff_summary(files: List[str]) -> str:
    if not is_git_available() or not files:
        return ""
    norm_files = [_normalize_rel(f) for f in files]
    rc, out, _ = _run_git(["diff", "HEAD", "--"] + norm_files)
    if rc == 0 and out.strip():
        return out
    rc2, out2, _ = _run_git(["diff", "--cached", "--"] + norm_files)
    return out2 if rc2 == 0 else ""


def get_recent_git_log(limit: int = 12, files: Optional[List[str]] = None) -> List[Dict[str, str]]:
    if not is_git_available():
        return []
    args = ["log", f"-n{limit}", "--pretty=format:%h|%ad|%s", "--date=format:%d/%m/%Y %H:%M"]
    if files:
        args.append("--")
        args.extend([_normalize_rel(f) for f in files])
    rc, out, _ = _run_git(args)
    if rc != 0 or not out.strip():
        return []
    rows = []
    for line in out.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            rows.append({"commit": parts[0], "date": parts[1], "message": parts[2]})
    return rows


def run_smoke_tests_subprocess(mod_id: Optional[str] = None, full_apptest: bool = False) -> Tuple[bool, str]:
    """Executa la bateria de tests de regressió en subprocés per evitar conflictes de ScriptRunContext."""
    script_path = os.path.join(PROJECT_ROOT, "scripts", "check_control.py")
    cmd = [sys.executable, script_path, "test"]
    if mod_id:
        cmd.extend(["--module", mod_id])
    if full_apptest:
        cmd.append("--full")
    else:
        cmd.append("--fast")
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180 if full_apptest else 30,
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return proc.returncode == 0, output.strip()
    except Exception as e:
        return False, f"Error executant tests: {e}"


def check_staged_changes(staged_files: List[str]) -> Tuple[bool, List[str], List[str]]:
    """
    Avalua els fitxers preparats (git staged) segons els 3 nivells:
    Retorna (allowed, messages, warnings).
    """
    registry = load_registry()
    touched_modules: Dict[str, List[str]] = {}
    for f in staged_files:
        norm = _normalize_rel(f)
        if norm in ("data/control_registry.json", "DOCUMENTACIO_PROJECTE.md"):
            continue
        owners = find_modules_for_file(registry, norm)
        for mid in owners:
            touched_modules.setdefault(mid, []).append(norm)

    if not touched_modules:
        return True, ["Cap fitxer de mòdul registrat modificat."], []

    errors: List[str] = []
    warnings: List[str] = []
    messages: List[str] = []

    # 1. Revisar per nivell
    for mid, files in touched_modules.items():
        entry = registry["modules"][mid]
        level = entry.get("level", LEVEL_OBERT)
        name = entry.get("name", mid)

        if level == LEVEL_BLINDAT:
            if not is_unlock_active(entry):
                errors.append(
                    f"[BLINDAT] '{name}' ({mid}) modificat sense consentiment ({', '.join(files)}).\n"
                    f"  -> Per autoritzar un canvi conscient executa:\n"
                    f"     python scripts/check_control.py unlock {mid} --motiu \"Explica el motiu\"\n"
                    f"  -> O desbloqueja'l temporalment des del mòdul Control de l'app."
                )
            else:
                create_backup_snapshot(mid, reason="pre_commit_blindat", source="head", registry=registry)
                ok, issues = run_fast_contracts([mid])
                if not ok:
                    errors.extend([f"[BLINDAT '{name}'] {iss}" for iss in issues])
                else:
                    messages.append(f"[BLINDAT '{name}'] Desbloqueig actiu fins {entry.get('unlocked_until')}; còpia feta i contractes OK.")

        elif level == LEVEL_VIGILAT:
            snap = create_backup_snapshot(mid, reason="pre_commit_vigilat", source="head", registry=registry)
            ok, issues = run_fast_contracts([mid])
            if not ok:
                errors.extend([f"[VIGILAT '{name}'] {iss}" for iss in issues])
            else:
                snap_info = os.path.basename(snap) if snap else "sense canvis previs"
                messages.append(f"[VIGILAT '{name}'] Canvi vigilat OK. Còpia creada ({snap_info}).")

            # Si s'ha tocat el nucli compartit, verificar també tots els mòduls Blindats dependents!
            deps = get_dependents(registry, mid)
            blind_deps = [d for d in deps if registry["modules"][d].get("level") == LEVEL_BLINDAT]
            if blind_deps:
                warnings.append(
                    f"ATENCIÓ: Has modificat '{name}', que afecta mòduls BLINDATS: "
                    + ", ".join(registry["modules"][d]["name"] for d in blind_deps)
                )
                ok_dep, dep_issues = run_fast_contracts(blind_deps)
                if not ok_dep:
                    errors.extend([f"[IMPACTE BLINDAT] {iss}" for iss in dep_issues])
                else:
                    messages.append("Verificació transversal sobre mòduls BLINDATS dependents: OK.")

        else:  # LEVEL_OBERT
            snap = create_backup_snapshot(mid, reason="pre_commit_obert", source="head", registry=registry)
            ok, syn_errs = run_syntax_check(files)
            if not ok:
                errors.extend([f"[OBERT '{name}'] {err}" for err in syn_errs])
            else:
                snap_info = os.path.basename(snap) if snap else "inicial"
                messages.append(f"[OBERT '{name}'] Punt de control creat ({snap_info}) i sintaxi OK.")

    return len(errors) == 0, (errors if errors else messages), warnings
