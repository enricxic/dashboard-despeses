"""
core/projectes_manager.py
Gestor centralitzat de dades per a Projectes d'Obra i Manteniment.
Persistència híbrida:
 - Supabase: taula 'app_config', id = 9
 - Fallback local: data/projectes_manteniment.json
Totes les dates en pantalla segueixen estrictament el format DD/MM/AAAA.
"""

import os
import json
import copy
from datetime import datetime, date
from typing import List, Dict, Optional, Any

_CURR_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_CURR_DIR, ".."))
PROJECTES_FILE = os.path.join(PROJECT_ROOT, "data", "projectes_manteniment.json")
PROVEIDORS_FILE = os.path.join(PROJECT_ROOT, "data", "proveidors_projectes.json")
CONFIG_ID_PROJECTES = 11

PROVEIDORS_DEFECTE = [
    "Obramat",
    "Leroy Merlin",
    "Bauhaus",
    "Brico Depôt",
    "Ferreteria de barri",
    "Amazon",
    "Internet",
    "Altre"
]

# ==========================================
# UTILITATS DE FORMAT DE DATA (DD/MM/AAAA)
# ==========================================

def format_date_cat(d: Any) -> str:
    """Converteix qualsevol data (date, datetime o string ISO) a format català DD/MM/AAAA."""
    if not d:
        return ""
    if isinstance(d, (datetime, date)):
        return d.strftime("%d/%m/%Y")
    d_str = str(d).strip()
    # Si ja té format DD/MM/AAAA
    if len(d_str) == 10 and d_str[2] == "/" and d_str[5] == "/":
        return d_str
    # Si té format YYYY-MM-DD
    if len(d_str) >= 10 and d_str[4] == "-" and d_str[7] == "-":
        try:
            parts = d_str[:10].split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            return d_str
    return d_str

def parse_date_cat(d_str: Any) -> Optional[date]:
    """Parseja un string en format DD/MM/AAAA o YYYY-MM-DD a objecte date de Python."""
    if not d_str:
        return None
    if isinstance(d_str, (datetime, date)):
        return d_str if isinstance(d_str, date) else d_str.date()
    s = str(d_str).strip()
    # Format DD/MM/AAAA
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception:
            pass
    # Format YYYY-MM-DD
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    return None

def to_iso_date(d: Any) -> str:
    """Retorna un string ISO YYYY-MM-DD a partir de date, datetime o DD/MM/AAAA."""
    dt = parse_date_cat(d)
    if dt:
        return dt.strftime("%Y-%m-%d")
    return ""

# ==========================================
# CÀRREGA I DESAT HÍBRID
# ==========================================

def _is_valid_project(p: Any) -> bool:
    """Verifica que l'objecte sigui un projecte real i no un apunt d'altres mòduls."""
    if not isinstance(p, dict):
        return False
    # Descarta apunts de consum elèctric o aigua que haguessin entrat per col·lisió
    if "kwhTotal" in p or "mesAny" in p or "comercialitzadora" in p or "m3" in p:
        return False
    # Un projecte vàlid té nom, id de projecte o llistes de materials/fases
    if p.get("nom") or str(p.get("id", "")).startswith("proj_") or "materials" in p or "fases" in p:
        return True
    return False

def load_projectes() -> List[Dict[str, Any]]:
    """Carrega la llista de projectes des de Supabase (id=9) o fallback local."""
    # 1. Intentar carregar de Supabase
    try:
        from core.db import get_supabase_client
        role = "guest"
        try:
            import streamlit as st
            if hasattr(st, "session_state") and "role" in st.session_state:
                role = st.session_state.get("role", "guest")
        except Exception:
            role = "guest"
        supabase = get_supabase_client(role)
        res = supabase.table("app_config").select("config_json").eq("id", CONFIG_ID_PROJECTES).execute()
        if res.data and len(res.data) > 0 and res.data[0].get("config_json"):
            cfg = res.data[0]["config_json"]
            if isinstance(cfg, list):
                valid_projs = [p for p in cfg if _is_valid_project(p)]
                _save_local(valid_projs)
                return valid_projs
    except Exception:
        pass

    # 2. Fallback local: fitxer JSON
    if os.path.exists(PROJECTES_FILE):
        try:
            with open(PROJECTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [p for p in data if _is_valid_project(p)]
        except Exception:
            pass

    return []

def save_projectes(projectes: List[Dict[str, Any]]) -> bool:
    """Desa la llista de projectes tant a local com a Supabase."""
    valid_projs = [p for p in projectes if _is_valid_project(p)]
    # 1. Sempre desar a fitxer local
    _save_local(valid_projs)

    # 2. Replicar a Supabase
    try:
        from core.db import get_supabase_client
        role = "authenticated"
        try:
            import streamlit as st
            if hasattr(st, "session_state") and "role" in st.session_state:
                role = st.session_state.get("role", "authenticated")
        except Exception:
            role = "authenticated"
        supabase = get_supabase_client(role)
        supabase.table("app_config").upsert({
            "id": CONFIG_ID_PROJECTES,
            "config_json": [p for p in projectes if _is_valid_project(p)]
            
        }).execute()
        return True
    except Exception:
        return False

def _save_local(data: List[Dict[str, Any]]):
    try:
        os.makedirs(os.path.dirname(PROJECTES_FILE), exist_ok=True)
        with open(PROJECTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ==========================================
# OPERACIONS DE GESTIÓ DE PROJECTE
# ==========================================

def get_projecte(project_id: str) -> Optional[Dict[str, Any]]:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            return p
    return None

def add_projecte(projecte: Dict[str, Any]) -> bool:
    projectes = load_projectes()
    if not projecte.get("id"):
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        projecte["id"] = f"proj_{now_str}"
    
    # Defaults
    projecte.setdefault("materials", [])
    projecte.setdefault("fases", [])
    projecte.setdefault("fotos", [])
    projecte.setdefault("xat_ia", [])
    projecte.setdefault("planol", {"canvas_data": None, "preview_png": None, "background_image": None})
    projecte.setdefault("estat", "Planificació")
    
    projectes.append(projecte)
    return save_projectes(projectes)

def update_projecte(project_id: str, fields: Dict[str, Any]) -> bool:
    projectes = load_projectes()
    updated = False
    for i, p in enumerate(projectes):
        if p.get("id") == project_id:
            projectes[i].update(fields)
            updated = True
            break
    if updated:
        return save_projectes(projectes)
    return False

def delete_projecte(project_id: str) -> bool:
    projectes = load_projectes()
    new_list = [p for p in projectes if p.get("id") != project_id]
    if len(new_list) != len(projectes):
        return save_projectes(new_list)
    return False

# ==========================================
# GESTIÓ DE PROVEÏDORS EN MEMÒRIA
# ==========================================

def get_llista_proveidors() -> List[str]:
    """Retorna la llista consolidada de proveïdors (per defecte + afegits en memòria + utilitzats en materials)."""
    provs = list(PROVEIDORS_DEFECTE)
    # 1. Carregar des de fitxer persistent de memòria
    if os.path.exists(PROVEIDORS_FILE):
        try:
            with open(PROVEIDORS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, list):
                    for sp in saved:
                        s_clean = str(sp).strip()
                        if s_clean and s_clean not in provs:
                            provs.append(s_clean)
        except Exception:
            pass

    # 2. Extreure proveïdors de tots els projectes existents
    try:
        projectes = load_projectes()
        for p in projectes:
            for m in p.get("materials", []):
                mp = str(m.get("proveidor", "")).strip()
                if mp and mp not in ("-", "Altre") and mp not in provs:
                    provs.append(mp)
    except Exception:
        pass

    return provs

def add_proveidor_memoria(nou_prov: str) -> List[str]:
    """Afegeix un nou proveïdor a la memòria persistent perquè quedi sempre disponible."""
    clean = str(nou_prov).strip()
    if not clean or clean in ("-", "Altre"):
        return get_llista_proveidors()

    current_saved = []
    if os.path.exists(PROVEIDORS_FILE):
        try:
            with open(PROVEIDORS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    current_saved = [str(x).strip() for x in data if str(x).strip()]
        except Exception:
            current_saved = []

    if clean not in current_saved:
        current_saved.append(clean)
        try:
            os.makedirs(os.path.dirname(PROVEIDORS_FILE), exist_ok=True)
            with open(PROVEIDORS_FILE, "w", encoding="utf-8") as f:
                json.dump(current_saved, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return get_llista_proveidors()

# ==========================================
# GESTIÓ DE MATERIALS
# ==========================================

def add_material(project_id: str, material: Dict[str, Any]) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p.setdefault("materials", [])
            if not material.get("id"):
                material["id"] = f"mat_{len(p['materials']) + 1}_{int(datetime.now().timestamp())}"
            material.setdefault("comprat", False)
            material.setdefault("en_stock", False)
            if material.get("en_stock"):
                material["preu_real"] = 0.0
                material["comprat"] = False
            prov = str(material.get("proveidor", "")).strip()
            if prov and prov not in ("-", "Altre"):
                add_proveidor_memoria(prov)
            p["materials"].append(material)
            return save_projectes(projectes)
    return False

def update_material(project_id: str, material_id: str, fields: Dict[str, Any]) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for m in p.get("materials", []):
                if m.get("id") == material_id:
                    m.update(fields)
                    if m.get("en_stock"):
                        m["preu_real"] = 0.0
                        m["comprat"] = False
                    prov = str(m.get("proveidor", "")).strip()
                    if prov and prov not in ("-", "Altre"):
                        add_proveidor_memoria(prov)
                    return save_projectes(projectes)
    return False

def delete_material(project_id: str, material_id: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p["materials"] = [m for m in p.get("materials", []) if m.get("id") != material_id]
            return save_projectes(projectes)
    return False

# ==========================================
# GESTIÓ DE FASES I SUBTASQUES
# ==========================================

def add_fase(project_id: str, fase: Dict[str, Any]) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p.setdefault("fases", [])
            if not fase.get("id"):
                fase["id"] = f"fase_{len(p['fases']) + 1}_{int(datetime.now().timestamp())}"
            fase.setdefault("estat", "Pendent")
            fase.setdefault("tasques", [])
            p["fases"].append(fase)
            return save_projectes(projectes)
    return False

def update_fase(project_id: str, fase_id: str, fields: Dict[str, Any]) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for f in p.get("fases", []):
                if f.get("id") == fase_id:
                    f.update(fields)
                    return save_projectes(projectes)
    return False

def delete_fase(project_id: str, fase_id: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p["fases"] = [f for f in p.get("fases", []) if f.get("id") != fase_id]
            return save_projectes(projectes)
    return False

def marcar_fase_estat(project_id: str, fase_id: str, completada: bool) -> bool:
    """Marca directament una fase com a acabada (i totes les seves subtasques) o la reobre com a pendent."""
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for f in p.get("fases", []):
                if f.get("id") == fase_id:
                    if completada:
                        f["estat"] = "Completada"
                        for t in f.get("tasques", []):
                            t["feta"] = True
                    else:
                        f["estat"] = "Pendent"
                        for t in f.get("tasques", []):
                            t["feta"] = False
                    return save_projectes(projectes)
    return False

def toggle_subtasca(project_id: str, fase_id: str, tasca_id: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for f in p.get("fases", []):
                if f.get("id") == fase_id:
                    for t in f.get("tasques", []):
                        if t.get("id") == tasca_id:
                            t["feta"] = not t.get("feta", False)
                            # Actualitzar l'estat de la fase automàticament
                            all_done = all(x.get("feta", False) for x in f.get("tasques", []))
                            any_done = any(x.get("feta", False) for x in f.get("tasques", []))
                            if all_done and len(f.get("tasques", [])) > 0:
                                f["estat"] = "Completada"
                            elif any_done:
                                f["estat"] = "En curs"
                            else:
                                f["estat"] = "Pendent"
                            return save_projectes(projectes)
    return False

def add_subtasca_a_fase(project_id: str, fase_id: str, titol: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for f in p.get("fases", []):
                if f.get("id") == fase_id:
                    f.setdefault("tasques", [])
                    t_id = f"t_{len(f['tasques']) + 1}_{int(datetime.now().timestamp())}"
                    f["tasques"].append({"id": t_id, "titol": titol, "feta": False})
                    return save_projectes(projectes)
    return False

def calcular_progres_projecte(projecte: Dict[str, Any]) -> float:
    """Retorna el percentatge de progrés (0.0 a 100.0) calculat sobre les tasques de totes les fases."""
    fases = projecte.get("fases", [])
    if not fases:
        return 0.0
    total_tasques = 0
    tasques_fetes = 0
    for f in fases:
        tasks = f.get("tasques", [])
        if tasks:
            total_tasques += len(tasks)
            tasques_fetes += sum(1 for t in tasks if t.get("feta", False))
        else:
            # Si la fase no té subtasques, es compta la fase sencera
            total_tasques += 1
            if f.get("estat") == "Completada":
                tasques_fetes += 1
    if total_tasques == 0:
        return 0.0
    return round((tasques_fetes / total_tasques) * 100.0, 1)

# ==========================================
# ASSISTENT IA I XAT
# ==========================================

def add_xat_missatge(project_id: str, role: str, text: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p.setdefault("xat_ia", [])
            p["xat_ia"].append({
                "role": role,
                "text": text,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            return save_projectes(projectes)
    return False

def clear_xat_projecte(project_id: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p["xat_ia"] = []
            return save_projectes(projectes)
    return False

# ==========================================
# GALERIA DE FOTOS I PLÀNOL
# ==========================================

def add_projecte_foto(project_id: str, tipus: str, data_url_or_path: str, descripcio: str = "") -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p.setdefault("fotos", [])
            f_id = f"f_{len(p['fotos']) + 1}_{int(datetime.now().timestamp())}"
            p["fotos"].append({
                "id": f_id,
                "tipus": tipus,  # "abans", "durant", "despres", "altre"
                "data": datetime.now().strftime("%d/%m/%Y"),
                "path": data_url_or_path,
                "descripcio": descripcio
            })
            return save_projectes(projectes)
    return False

def delete_projecte_foto(project_id: str, foto_id: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p["fotos"] = [f for f in p.get("fotos", []) if f.get("id") != foto_id]
            return save_projectes(projectes)
    return False

def save_planol_projecte(project_id: str, preview_png: str, canvas_data: Any = None, background_image: Optional[str] = None) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p.setdefault("planol", {})
            if preview_png:
                p["planol"]["preview_png"] = preview_png
            if canvas_data is not None:
                p["planol"]["canvas_data"] = canvas_data
            if background_image is not None:
                p["planol"]["background_image"] = background_image
            p["planol"]["data_actualitzacio"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            return save_projectes(projectes)
    return False
