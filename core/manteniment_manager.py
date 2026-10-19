import os
import json
import copy
from datetime import datetime, date

_CURR_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_CURR_DIR, ".."))
DOCS_FILE = os.path.join(PROJECT_ROOT, "data", "manteniment_docs.json")
PDF_DIR = os.path.join(PROJECT_ROOT, "PDF")

DEFAULT_DOCS = {
    "manuals": [],
    "garanties": []
}

def get_pdf_path(category: str, filename: str) -> str:
    """Retorna la ruta absoluta d'un fitxer PDF segons la categoria."""
    subfolder = "Manuals" if category.lower() in ["manuals", "manual"] else "Garanties"
    return os.path.join(PDF_DIR, subfolder, filename)

def get_pdf_dir(category: str) -> str:
    """Retorna el directori d'una categoria de PDF."""
    subfolder = "Manuals" if category.lower() in ["manuals", "manual"] else "Garanties"
    d = os.path.join(PDF_DIR, subfolder)
    os.makedirs(d, exist_ok=True)
    return d

def load_manteniment_docs() -> dict:
    """
    Carrega el registre de documents PDF des de Supabase (id=7 a app_config).
    Si falla o no hi ha connexió, utilitza el fitxer local data/manteniment_docs.json com a fallback.
    """
    # 1. Intentar carregar de Supabase
    try:
        from core.db import get_supabase_client
        import streamlit as st
        role = st.session_state.get("role", "guest") if "role" in st.session_state else "guest"
        supabase = get_supabase_client(role)
        res = supabase.table("app_config").select("config_json").eq("id", 7).execute()
        if res.data and len(res.data) > 0 and res.data[0].get("config_json"):
            cfg = res.data[0]["config_json"]
            if isinstance(cfg, dict):
                cfg.setdefault("manuals", [])
                cfg.setdefault("garanties", [])
                return cfg
    except Exception as e:
        # Silenciós en cas de no connexió
        pass

    # 2. Fallback: Fitxer local
    if os.path.exists(DOCS_FILE):
        try:
            with open(DOCS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("manuals", [])
                    data.setdefault("garanties", [])
                    return data
        except Exception as e:
            print(f"Error llegint {DOCS_FILE}: {e}")

    return copy.deepcopy(DEFAULT_DOCS)

def save_manteniment_docs(data: dict) -> bool:
    """
    Desa el registre de documents a Supabase (id=7 a app_config) i al fitxer local data/manteniment_docs.json.
    """
    # 1. Desar a Supabase
    try:
        from core.db import get_supabase_client
        import streamlit as st
        role = st.session_state.get("role", "admin") if "role" in st.session_state else "admin"
        supabase = get_supabase_client(role)
        supabase.table("app_config").upsert({
            "id": 7,
            "config_json": data
        }).execute()
    except Exception as e:
        print(f"Error desant documents a Supabase: {e}")

    # 2. Desar localment
    try:
        os.makedirs(os.path.dirname(DOCS_FILE), exist_ok=True)
        with open(DOCS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error desant localment {DOCS_FILE}: {e}")
        return False

def get_page_count(filepath: str) -> int:
    """Obté el nombre de pàgines d'un PDF amb pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(filepath)
        return len(reader.pages)
    except Exception:
        return 0

def sync_pdf_directory() -> tuple:
    """
    Escaneja les carpetes PDF/Manuals i PDF/Garanties al disc dur.
    Si troba PDFs que no estan al registre JSON, els afegeix automàticament.
    Retorna (nous_manuals, noves_garanties).
    """
    docs = load_manteniment_docs()
    changes = False
    new_manuals_count = 0
    new_garanties_count = 0

    # 1. Sincronitzar Manuals
    manuals_dir = get_pdf_dir("Manuals")
    existing_manual_files = {doc.get("fitxer", "") for doc in docs.get("manuals", [])}
    if os.path.exists(manuals_dir):
        for fname in os.listdir(manuals_dir):
            if fname.lower().endswith(".pdf") and fname not in existing_manual_files:
                fpath = os.path.join(manuals_dir, fname)
                pages = get_page_count(fpath)
                base_title = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()
                doc_id = f"man_{int(datetime.now().timestamp() * 1000)}_{len(docs['manuals']) + 1}"
                
                docs["manuals"].append({
                    "id": doc_id,
                    "titol": base_title,
                    "dispositiu": base_title,
                    "marca": "General",
                    "model": "",
                    "ubicacio": "General",
                    "subcategoria": "Equipament",
                    "fitxer": fname,
                    "categoria": "Manuals",
                    "pagines": pages,
                    "descripcio": f"Document detectat automàticament a la carpeta Manuals ({fname}).",
                    "data_afegit": datetime.now().strftime("%d/%m/%Y"),
                    "etiquetes": [w.lower() for w in base_title.split() if len(w) > 2]
                })
                existing_manual_files.add(fname)
                changes = True
                new_manuals_count += 1

    # 2. Sincronitzar Garanties
    garanties_dir = get_pdf_dir("Garanties")
    existing_gar_files = {doc.get("fitxer", "") for doc in docs.get("garanties", [])}
    if os.path.exists(garanties_dir):
        for fname in os.listdir(garanties_dir):
            if fname.lower().endswith(".pdf") and fname not in existing_gar_files:
                fpath = os.path.join(garanties_dir, fname)
                pages = get_page_count(fpath)
                base_title = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()
                doc_id = f"gar_{int(datetime.now().timestamp() * 1000)}_{len(docs['garanties']) + 1}"
                
                docs["garanties"].append({
                    "id": doc_id,
                    "titol": base_title,
                    "dispositiu": base_title,
                    "marca": "General",
                    "model": "",
                    "establiment": "Pendent",
                    "num_factura": "",
                    "ubicacio": "General",
                    "fitxer": fname,
                    "categoria": "Garanties",
                    "pagines": pages,
                    "data_compra": datetime.now().strftime("%d/%m/%Y"),
                    "anys_garantia": 3,
                    "data_venciment": "",
                    "import_compra": 0.0,
                    "descripcio": f"Garantia detectada automàticament a la carpeta Garanties ({fname}).",
                    "data_afegit": datetime.now().strftime("%d/%m/%Y"),
                    "etiquetes": ["garantia"]
                })
                existing_gar_files.add(fname)
                changes = True
                new_garanties_count += 1

    if changes:
        save_manteniment_docs(docs)

    return new_manuals_count, new_garanties_count

def calculate_warranty_status(doc: dict) -> dict:
    """
    Calcula l'estat d'una garantia:
    - data de venciment calculada si no existeix (data_compra + anys_garantia)
    - dies restants
    - estat: 'vigente' (>60d), 'aviso' (0-60d), 'caducada' (<0d), 'indeterminada'
    """
    d_compra_str = doc.get("data_compra", "").strip()
    d_venc_str = doc.get("data_venciment", "").strip()
    anys = doc.get("anys_garantia", 3)

    venc_date = None
    if d_venc_str:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                venc_date = datetime.strptime(d_venc_str, fmt).date()
                break
            except Exception:
                pass

    if not venc_date and d_compra_str:
        compra_date = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                compra_date = datetime.strptime(d_compra_str, fmt).date()
                break
            except Exception:
                pass
        if compra_date:
            try:
                venc_date = compra_date.replace(year=compra_date.year + int(anys))
            except ValueError:
                # Per al 29 de febrer
                venc_date = compra_date.replace(year=compra_date.year + int(anys), day=28)

    today = date.today()
    if venc_date:
        delta = (venc_date - today).days
        formatted_venc = venc_date.strftime("%d/%m/%Y")
        if delta < 0:
            return {
                "estat": "caducada",
                "color": "#ef4444",
                "text": f"Caducada fa {abs(delta)} dies ({formatted_venc})",
                "dies_restants": delta,
                "data_venciment": formatted_venc
            }
        elif delta <= 60:
            return {
                "estat": "aviso",
                "color": "#f59e0b",
                "text": f"A punt de caducar! Falten {delta} dies ({formatted_venc})",
                "dies_restants": delta,
                "data_venciment": formatted_venc
            }
        else:
            return {
                "estat": "vigente",
                "color": "#10b981",
                "text": f"Vigent (falten {delta} dies, fins {formatted_venc})",
                "dies_restants": delta,
                "data_venciment": formatted_venc
            }
    
    return {
        "estat": "indeterminada",
        "color": "#94a3b8",
        "text": "Data no especificada",
        "dies_restants": 9999,
        "data_venciment": d_venc_str or "Sense data"
    }

# =========================================================================
# GESTIÓ DEL REGISTRE DE MANTENIMENT (TASQUES, REPARACIONS I FEINA DE CASA)
# =========================================================================

REGISTRE_FILE = os.path.join(PROJECT_ROOT, "data", "registre_manteniment.json")
REGISTRE_CSV = os.path.join(PROJECT_ROOT, "csv", "manteniment.csv")

def load_registre_manteniment() -> list:
    """
    Carrega la llista de tasques de manteniment des de Supabase (id=8 a app_config).
    Fallback 1: data/registre_manteniment.json
    Fallback 2: csv/manteniment.csv
    """
    # 1. Intentar carregar de Supabase
    try:
        from core.db import get_supabase_client
        import streamlit as st
        role = st.session_state.get("role", "guest") if "role" in st.session_state else "guest"
        supabase = get_supabase_client(role)
        res = supabase.table("app_config").select("config_json").eq("id", 8).execute()
        if res.data and len(res.data) > 0 and res.data[0].get("config_json"):
            cfg = res.data[0]["config_json"]
            if isinstance(cfg, list):
                return cfg
    except Exception:
        pass

    # 2. Fallback: Fitxer JSON local
    if os.path.exists(REGISTRE_FILE):
        try:
            with open(REGISTRE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass

    # 3. Fallback: Fitxer CSV local
    if os.path.exists(REGISTRE_CSV):
        try:
            import pandas as pd
            df = pd.read_csv(REGISTRE_CSV, sep=';', encoding='utf-8')
            return df.to_dict(orient='records')
        except Exception:
            pass

    return []

def save_registre_manteniment(records: list) -> bool:
    """
    Desa les tasques de manteniment a Supabase (id=8 a app_config),
    al fitxer JSON local data/registre_manteniment.json i al fitxer CSV csv/manteniment.csv.
    """
    # 1. Desar a Supabase
    try:
        from core.db import get_supabase_client
        import streamlit as st
        role = st.session_state.get("role", "admin") if "role" in st.session_state else "admin"
        supabase = get_supabase_client(role)
        supabase.table("app_config").upsert({
            "id": 8,
            "config_json": records
        }).execute()
    except Exception as e:
        print(f"Error desant registre manteniment a Supabase: {e}")

    # 2. Desar a JSON local
    try:
        os.makedirs(os.path.dirname(REGISTRE_FILE), exist_ok=True)
        with open(REGISTRE_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error desant localment {REGISTRE_FILE}: {e}")

    # 3. Desar a CSV local
    try:
        import pandas as pd
        os.makedirs(os.path.dirname(REGISTRE_CSV), exist_ok=True)
        records_csv = []
        for r in records:
            r_copy = dict(r)
            if isinstance(r_copy.get("alertaA"), list):
                r_copy["alertaA"] = ", ".join(r_copy["alertaA"])
            records_csv.append(r_copy)
        df = pd.DataFrame(records_csv)
        cols_order = ["idManteniment", "dataAlta", "dataManteniment", "diesAvis", "feina", "tipus", "alertaA", "acompliment", "observacions"]
        for c in cols_order:
            if c not in df.columns:
                df[c] = ""
        df = df[cols_order]
        df.to_csv(REGISTRE_CSV, sep=';', index=False, encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error desant localment {REGISTRE_CSV}: {e}")
        return False

def add_manteniment_task(task_data: dict, send_to_calendar: bool = False) -> dict:
    """Afegeix una nova tasca de manteniment, opcionalment creant l'esdeveniment a l'agenda."""
    tasks = load_registre_manteniment()
    next_id = max([int(t.get("idManteniment", 0)) for t in tasks if str(t.get("idManteniment", "")).isdigit()] + [0]) + 1
    task_data["idManteniment"] = next_id
    if not task_data.get("dataAlta"):
        task_data["dataAlta"] = datetime.now().strftime("%d/%m/%Y")
    task_data.setdefault("diesAvis", 2)
    task_data.setdefault("feina", "")
    task_data.setdefault("acompliment", "No")
    
    # Enviar a calendari si s'ha sol·licitat
    if send_to_calendar:
        try:
            from core.calendar_manager import add_event
            d_prev = task_data.get("dataManteniment", "")
            iso_date = ""
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    iso_date = datetime.strptime(d_prev, fmt).strftime("%Y-%m-%d")
                    break
                except Exception:
                    pass
            if not iso_date:
                iso_date = datetime.now().strftime("%Y-%m-%d")
                
            feina = task_data.get("feina", "").strip()
            obs = task_data.get("observacions", "").strip()
            tip = task_data.get("tipus", "Manteniment")
            desc_curta = feina if feina else obs
            tit = f"[{tip}] {desc_curta[:35]}..." if len(desc_curta) > 35 else f"[{tip}] {desc_curta or 'Tasca de manteniment'}"
            
            alerta_raw = task_data.get("alertaA", "Tothom")
            alerta_str = ", ".join(alerta_raw) if isinstance(alerta_raw, list) else str(alerta_raw)
            dies_av = task_data.get("diesAvis", 2)
            
            cal_desc = f"Tasca de Manteniment #{next_id}\nFeina: {feina}\nTipus: {tip}\nAlerta a: {alerta_str}\nAvís amb {dies_av} dies d'antelació"
            if obs:
                cal_desc += f"\n\nObservacions:\n{obs}"
            
            ev = add_event({
                "title": tit,
                "date": iso_date,
                "time": "09:00",
                "category": "Llar",
                "description": cal_desc,
                "assigned_to": alerta_str,
                "notify": True
            })
            if ev and isinstance(ev, dict) and "id" in ev:
                task_data["calendar_event_id"] = ev["id"]
        except Exception as err:
            print("Error enviant al calendari:", err)

    tasks.append(task_data)
    save_registre_manteniment(tasks)
    return task_data

def update_manteniment_task(task_id: int, updated_fields: dict) -> bool:
    """Actualitza una tasca existent."""
    tasks = load_registre_manteniment()
    for i, t in enumerate(tasks):
        if int(t.get("idManteniment", -1)) == int(task_id):
            tasks[i].update(updated_fields)
            save_registre_manteniment(tasks)
            return True
    return False

def delete_manteniment_task(task_id: int) -> bool:
    """Elimina una tasca del registre."""
    tasks = load_registre_manteniment()
    new_tasks = [t for t in tasks if int(t.get("idManteniment", -1)) != int(task_id)]
    if len(new_tasks) != len(tasks):
        save_registre_manteniment(new_tasks)
        return True
    return False

def toggle_manteniment_acompliment(task_id: int) -> bool:
    """Commuta l'estat d'acompliment entre Sí i No."""
    tasks = load_registre_manteniment()
    for i, t in enumerate(tasks):
        if int(t.get("idManteniment", -1)) == int(task_id):
            curr = str(tasks[i].get("acompliment", "No")).strip().lower()
            tasks[i]["acompliment"] = "No" if curr in ["sí", "si", "true"] else "Sí"
            save_registre_manteniment(tasks)
            return True
    return False
