"""
core/projectes_manager.py
Gestor centralitzat de dades per a Projectes d'Obra i Manteniment.
Persistència híbrida:
 - Supabase: taula 'app_config', id = 9
 - Fallback local: data/projectes_manteniment.json
Totes les dates en pantalla segueixen estrictament el format DD/MM/AAAA.
"""

import os
import io
import json
import copy
import base64
import threading
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from PIL import Image, ImageOps

_CURR_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_CURR_DIR, ".."))
PROJECTES_FILE = os.path.join(PROJECT_ROOT, "data", "projectes_manteniment.json")
PROVEIDORS_FILE = os.path.join(PROJECT_ROOT, "data", "proveidors_projectes.json")
CONFIG_ID_PROJECTES = 11

_IN_MEMORY_PROJECTES: Optional[List[Dict[str, Any]]] = None

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

def load_projectes(force_reload: bool = False) -> List[Dict[str, Any]]:
    """Carrega la llista de projectes prioritzant la sessió actual i Supabase (font de veritat al núvol), amb fallback local."""
    global _IN_MEMORY_PROJECTES

    # 1. Comprovar si ja s'han carregat els projectes en aquesta sessió de Streamlit
    if not force_reload:
        try:
            import streamlit as st
            if (
                hasattr(st, "session_state")
                and st.session_state.get("projectes_loaded_from_cloud", False)
                and "cached_projectes_list" in st.session_state
            ):
                cached = st.session_state["cached_projectes_list"]
                if isinstance(cached, list):
                    return cached
        except Exception:
            pass

    # 2. Consultar Supabase directament (font de veritat persistent entre reinicis, PC i mòbil/núvol)
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
        if res.data and len(res.data) > 0 and res.data[0].get("config_json") is not None:
            cfg = res.data[0]["config_json"]
            if isinstance(cfg, list):
                valid_projs = [p for p in cfg if _is_valid_project(p)]
                _IN_MEMORY_PROJECTES = valid_projs
                _save_local(valid_projs)
                try:
                    import streamlit as st
                    if hasattr(st, "session_state"):
                        st.session_state["cached_projectes_list"] = valid_projs
                        st.session_state["projectes_loaded_from_cloud"] = True
                except Exception:
                    pass
                return valid_projs
    except Exception as e:
        print(f"⚠️ [ProjectesManager] Error carregant de Supabase, utilitzant fallback local: {e}")

    # 3. Fallback: memòria de procés o fitxer JSON local (només si no hi ha connexió amb el núvol)
    if _IN_MEMORY_PROJECTES is not None and len(_IN_MEMORY_PROJECTES) > 0:
        return _IN_MEMORY_PROJECTES

    if os.path.exists(PROJECTES_FILE):
        try:
            with open(PROJECTES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    valid = [p for p in data if _is_valid_project(p)]
                    _IN_MEMORY_PROJECTES = valid
                    try:
                        import streamlit as st
                        if hasattr(st, "session_state"):
                            st.session_state["cached_projectes_list"] = valid
                    except Exception:
                        pass
                    return valid
        except Exception:
            pass

    return []

def save_projectes(projectes: List[Dict[str, Any]]) -> bool:
    """Desa la llista de projectes de manera síncrona a Supabase (núvol) i actualitza la sessió i còpia local."""
    global _IN_MEMORY_PROJECTES
    valid_projs = [p for p in projectes if _is_valid_project(p)]
    
    # 1. Actualitzar immediatament la memòria de sessió
    _IN_MEMORY_PROJECTES = valid_projs
    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            st.session_state["cached_projectes_list"] = valid_projs
            st.session_state["projectes_loaded_from_cloud"] = True
    except Exception:
        pass

    # 2. Guardar còpia de seguretat local al disc
    _save_local(valid_projs)

    # 3. Desar de forma síncrona a Supabase perquè no es perdi mai cap canvi en tancar o reiniciar
    role = "admin"
    try:
        import streamlit as st
        if hasattr(st, "session_state") and "role" in st.session_state:
            role = st.session_state.get("role", "admin")
    except Exception:
        role = "admin"

    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client(role)
        supabase.table("app_config").upsert({
            "id": CONFIG_ID_PROJECTES,
            "config_json": valid_projs
        }).execute()
        return True
    except Exception as e:
        print(f"⚠️ [ProjectesManager] Error desant a Supabase: {e}")
        try:
            import streamlit as st
            st.error(f"⚠️ No s'han pogut desar els canvis al núvol (Supabase): {e}")
        except Exception:
            pass
        return False

# ==========================================
# COMPRESSIÓ D'IMATGES (PIL)
# ==========================================

def compress_image_b64(img_input: Any, max_dim: int = 1280, quality: int = 80) -> str:
    """Comprimeix i redimensiona imatges (bytes, fitxer o string data URL base64) per estalviar espai.
    Converteix fotos de 10-20 MB a ~100-200 KB, evitant caigudes de WebSocket o límits de càrrega."""
    if not img_input:
        return ""
    try:
        raw_bytes = None
        if isinstance(img_input, str):
            if img_input.startswith("data:image"):
                if "," in img_input:
                    _, b64_part = img_input.split(",", 1)
                    raw_bytes = base64.b64decode(b64_part)
                else:
                    return img_input
            elif img_input.startswith("http://") or img_input.startswith("https://"):
                # URL externa, no cal comprimir
                return img_input
            elif os.path.exists(img_input):
                with open(img_input, "rb") as f:
                    raw_bytes = f.read()
            else:
                return img_input
        elif hasattr(img_input, "read"):
            img_input.seek(0)
            raw_bytes = img_input.read()
            try:
                img_input.seek(0)
            except Exception:
                pass
        elif isinstance(img_input, bytes):
            raw_bytes = img_input

        if not raw_bytes:
            return img_input if isinstance(img_input, str) else ""

        img = Image.open(io.BytesIO(raw_bytes))

        # Respectar orientació EXIF de fotos preses amb mòbil
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Convertir a RGB si té canal Alpha (RGBA) o paleta (P)
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
            bg.paste(img, mask=mask)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Redimensionar si supera la mida màxima
        w, h = img.size
        if max(w, h) > max_dim:
            if w > h:
                new_w = max_dim
                new_h = int(h * (max_dim / w))
            else:
                new_h = max_dim
                new_w = int(w * (max_dim / h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        out_io = io.BytesIO()
        img.save(out_io, format="JPEG", quality=quality, optimize=True)
        comp_b64 = base64.b64encode(out_io.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{comp_b64}"
    except Exception as e:
        print(f"⚠️ Error comprimint imatge: {e}")
        if isinstance(img_input, str):
            return img_input
        return ""

def _save_local(data: List[Dict[str, Any]]):
    """Guarda al disc de forma atòmica per evitar fitxers corruptes si hi ha un tall."""
    try:
        os.makedirs(os.path.dirname(PROJECTES_FILE), exist_ok=True)
        tmp_file = PROJECTES_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, PROJECTES_FILE)
    except Exception as e:
        print(f"⚠️ Error desant fitxer local de projectes: {e}")

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
    provs = [p for p in PROVEIDORS_DEFECTE if "Afegir un altre" not in p and not p.startswith("➕")]
    # 1. Carregar des de fitxer persistent de memòria
    if os.path.exists(PROVEIDORS_FILE):
        try:
            with open(PROVEIDORS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, list):
                    for sp in saved:
                        s_clean = str(sp).strip()
                        if s_clean and s_clean not in provs and "Afegir un altre" not in s_clean and not s_clean.startswith("➕") and s_clean not in ("-", "Altre"):
                            provs.append(s_clean)
        except Exception:
            pass

    # 2. Extreure proveïdors de tots els projectes existents
    try:
        projectes = load_projectes()
        for p in projectes:
            for m in p.get("materials", []):
                mp = str(m.get("proveidor", "")).strip()
                if mp and mp not in ("-", "Altre") and "Afegir un altre" not in mp and not mp.startswith("➕") and mp not in provs:
                    provs.append(mp)
    except Exception:
        pass

    return provs

def add_proveidor_memoria(nou_prov: str) -> List[str]:
    """Afegeix un nou proveïdor a la memòria persistent perquè quedi sempre disponible."""
    clean = str(nou_prov).strip()
    if not clean or clean in ("-", "Altre") or "Afegir un altre" in clean or clean.startswith("➕"):
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
            if material.get("imatge"):
                material["imatge"] = compress_image_b64(material["imatge"], max_dim=600, quality=80)
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
                    if "imatge" in fields and fields["imatge"]:
                        fields["imatge"] = compress_image_b64(fields["imatge"], max_dim=600, quality=80)
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

def marcar_fase_estat(project_id: str, fase_id: str, estat_o_completada: Any) -> bool:
    """Marca directament l'estat d'una fase ('Completada', 'En curs', 'Pendent' o bool True/False)."""
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for f in p.get("fases", []):
                if f.get("id") == fase_id:
                    if estat_o_completada is True or estat_o_completada == "Completada":
                        f["estat"] = "Completada"
                        for t in f.get("tasques", []):
                            t["feta"] = True
                        if p.get("estat") == "Pendent":
                            p["estat"] = "En curs"
                    elif estat_o_completada == "En curs":
                        f["estat"] = "En curs"
                        # Si el projecte està Pendent, activar-lo automàticament a En curs
                        if p.get("estat") == "Pendent":
                            p["estat"] = "En curs"
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
                                if p.get("estat") == "Pendent":
                                    p["estat"] = "En curs"
                            elif any_done:
                                f["estat"] = "En curs"
                                if p.get("estat") == "Pendent":
                                    p["estat"] = "En curs"
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

def delete_subtasca(project_id: str, fase_id: str, tasca_id: str) -> bool:
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            for f in p.get("fases", []):
                if f.get("id") == fase_id:
                    f["tasques"] = [t for t in f.get("tasques", []) if t.get("id") != tasca_id]
                    # Actualitzar l'estat de la fase segons les subtasques restants
                    if f["tasques"]:
                        all_done = all(x.get("feta", False) for x in f["tasques"])
                        any_done = any(x.get("feta", False) for x in f["tasques"])
                        if all_done:
                            f["estat"] = "Completada"
                        elif any_done:
                            f["estat"] = "En curs"
                        else:
                            f["estat"] = "Pendent"
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

def delete_xat_missatge(project_id: str, index: int) -> bool:
    """Elimina un missatge concret del xat pel seu índex (ex: per treure un missatge d'error)."""
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            xat = p.get("xat_ia", [])
            if 0 <= index < len(xat):
                xat.pop(index)
                return save_projectes(projectes)
    return False

# ==========================================
# GALERIA DE FOTOS I PLÀNOL
# ==========================================

def add_projecte_foto(project_id: str, tipus: str, data_url_or_path: str, descripcio: str = "") -> bool:
    projectes = load_projectes()
    comp_path = compress_image_b64(data_url_or_path, max_dim=1280, quality=80)
    for p in projectes:
        if p.get("id") == project_id:
            p.setdefault("fotos", [])
            f_id = f"f_{len(p['fotos']) + 1}_{int(datetime.now().timestamp())}"
            p["fotos"].append({
                "id": f_id,
                "tipus": tipus,  # "abans", "durant", "despres", "altre"
                "data": datetime.now().strftime("%d/%m/%Y"),
                "path": comp_path,
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
                p["planol"]["preview_png"] = compress_image_b64(preview_png, max_dim=1280, quality=80)
            if canvas_data is not None:
                p["planol"]["canvas_data"] = canvas_data
            if background_image is not None:
                p["planol"]["background_image"] = compress_image_b64(background_image, max_dim=1280, quality=80)
            p["planol"]["data_actualitzacio"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            return save_projectes(projectes)
    return False

# ==========================================
# DISSENY DE MOBLES I DESPECEJAMENT MD
# ==========================================

def get_moble_md(project_id: str) -> Optional[Dict[str, Any]]:
    """Retorna les dades del disseny de moble MD guardades al projecte."""
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            return p.get("moble_md")
    return None

def save_moble_md(project_id: str, moble_data: Dict[str, Any]) -> bool:
    """Guarda o actualitza el disseny de moble MD d'un projecte."""
    projectes = load_projectes()
    for p in projectes:
        if p.get("id") == project_id:
            p["moble_md"] = moble_data
            p["moble_md"]["data_actualitzacio"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            return save_projectes(projectes)
    return False
