import os
import json
import copy
import re
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

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
            records = df.to_dict(orient='records')
            for r in records:
                if "subtasques" in r and isinstance(r["subtasques"], str):
                    try:
                        r["subtasques"] = json.loads(r["subtasques"])
                    except Exception:
                        r["subtasques"] = []
                if "subtasques_template" in r and isinstance(r["subtasques_template"], str):
                    try:
                        r["subtasques_template"] = json.loads(r["subtasques_template"])
                    except Exception:
                        r["subtasques_template"] = []
            return records
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
            if isinstance(r_copy.get("subtasques"), list):
                r_copy["subtasques"] = json.dumps(r_copy["subtasques"], ensure_ascii=False) if r_copy["subtasques"] else ""
            if isinstance(r_copy.get("subtasques_template"), list):
                r_copy["subtasques_template"] = json.dumps(r_copy["subtasques_template"], ensure_ascii=False) if r_copy["subtasques_template"] else ""
            records_csv.append(r_copy)
        df = pd.DataFrame(records_csv)
        cols_order = ["idManteniment", "dataAlta", "dataManteniment", "diesAvis", "feina", "tipus", "alertaA", "recurrencia", "acompliment", "observacions", "subtasques", "subtasques_template"]
        for c in cols_order:
            if c not in df.columns:
                df[c] = ""
        df = df[cols_order]
        df.to_csv(REGISTRE_CSV, sep=';', index=False, encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error desant localment {REGISTRE_CSV}: {e}")
        return False

def compute_recurring_dates(
    start_date: date,
    freq_type: str,
    custom_interval: int = 1,
    custom_unit: str = "Dies",
    end_mode: str = "vegades",
    occurrences: int = 1,
    until_date: date = None,
    max_limit: int = 60
) -> list:
    """
    Calcula la llista d'objectes date per a una tasca de manteniment periòdica.
    """
    if freq_type in ["Puntual (una sola vegada)", "Puntual", "Cap"]:
        return [start_date]
        
    dates = []
    count = max(1, min(int(occurrences), max_limit))
    
    for i in range(max_limit):
        if freq_type == "Cada dia":
            d = start_date + timedelta(days=i)
        elif freq_type == "Cada setmana":
            d = start_date + timedelta(weeks=i)
        elif freq_type == "Cada 2 setmanes (quinzenal)":
            d = start_date + timedelta(weeks=2 * i)
        elif freq_type == "Cada mes":
            d = start_date + relativedelta(months=i)
        elif freq_type == "Cada 2 mesos":
            d = start_date + relativedelta(months=2 * i)
        elif freq_type == "Cada 3 mesos (trimestral)":
            d = start_date + relativedelta(months=3 * i)
        elif freq_type == "Cada 6 mesos (semestral)":
            d = start_date + relativedelta(months=6 * i)
        elif freq_type == "Cada any":
            d = start_date + relativedelta(years=i)
        elif "Personalitzat" in freq_type:
            step = max(1, int(custom_interval))
            if custom_unit == "Dies":
                d = start_date + timedelta(days=step * i)
            elif custom_unit == "Setmanes":
                d = start_date + timedelta(weeks=step * i)
            elif custom_unit == "Mesos":
                d = start_date + relativedelta(months=step * i)
            elif custom_unit == "Anys":
                d = start_date + relativedelta(years=step * i)
            else:
                d = start_date + timedelta(days=step * i)
        else:
            d = start_date + timedelta(days=i)
            
        if end_mode == "data" and until_date:
            if d > until_date:
                break
            dates.append(d)
        else:
            dates.append(d)
            if len(dates) >= count:
                break
                
    return dates if dates else [start_date]

def compute_recurring_dates_for_year(
    start_date: date,
    freq_type: str,
    custom_interval: int = 1,
    custom_unit: str = "Dies",
    target_year: int = 2026
) -> list:
    """
    Calcula totes les dates d'ocurrència d'una sèrie que cauen dins de target_year (fins a 31/12/target_year).
    """
    year_start = date(target_year, 1, 1)
    year_end = date(target_year, 12, 31)
    
    # Ajustar data inicial a target_year
    if start_date.year != target_year:
        try:
            curr_d = date(target_year, start_date.month, min(start_date.day, 28))
        except Exception:
            curr_d = year_start
    else:
        curr_d = start_date

    dates = []
    
    if freq_type in ["Puntual (una sola vegada)", "Puntual", "Cap"]:
        if year_start <= curr_d <= year_end:
            return [curr_d]
        return [date(target_year, curr_d.month, min(curr_d.day, 28))]

    if freq_type == "Cada any":
        if year_start <= curr_d <= year_end:
            return [curr_d]
        return [date(target_year, curr_d.month, min(curr_d.day, 28))]

    i = 0
    max_steps = 370
    while curr_d <= year_end and i < max_steps:
        if curr_d >= year_start:
            dates.append(curr_d)
            
        i += 1
        if freq_type == "Cada dia":
            curr_d = curr_d + timedelta(days=1)
        elif freq_type == "Cada setmana":
            curr_d = curr_d + timedelta(weeks=1)
        elif freq_type == "Cada 2 setmanes (quinzenal)":
            curr_d = curr_d + timedelta(weeks=2)
        elif freq_type == "Cada mes":
            curr_d = curr_d + relativedelta(months=1)
        elif freq_type == "Cada 2 mesos":
            curr_d = curr_d + relativedelta(months=2)
        elif freq_type == "Cada 3 mesos (trimestral)":
            curr_d = curr_d + relativedelta(months=3)
        elif freq_type == "Cada 6 mesos (semestral)":
            curr_d = curr_d + relativedelta(months=6)
        elif "Personalitzat" in freq_type:
            step = max(1, int(custom_interval))
            if custom_unit == "Dies":
                curr_d = curr_d + timedelta(days=step)
            elif custom_unit == "Setmanes":
                curr_d = curr_d + timedelta(weeks=step)
            elif custom_unit == "Mesos":
                curr_d = curr_d + relativedelta(months=step)
            elif custom_unit == "Anys":
                break
            else:
                curr_d = curr_d + timedelta(days=step)
        else:
            curr_d = curr_d + timedelta(days=1)
            
    return dates if dates else [curr_d]

def filter_subtasks_for_occurrence(subtasks_template: list, occ_idx: int, occ_date: date, last_assigned: dict) -> list:
    """
    Determina quines subtasques de la plantilla s'han d'activar per a una data concreta (occ_date)
    segons la cadència de cadascuna (sempre, per cicles o per mesos).
    """
    active_subtasks = []
    if not subtasks_template or not isinstance(subtasks_template, list):
        return active_subtasks
        
    for sub_idx, sub_tpl in enumerate(subtasks_template):
        if not isinstance(sub_tpl, dict):
            continue
        sub_titol = sub_tpl.get("titol", "").strip()
        if not sub_titol:
            continue
        sub_id = sub_tpl.get("id", f"sub_{sub_idx+1}")
        cad_tip = sub_tpl.get("cadencia_tipus", "sempre")
        cad_val = int(sub_tpl.get("cadencia_valor", 1))
        
        applies = False
        if cad_tip == "sempre":
            applies = True
        elif cad_tip == "repeticions":
            if occ_idx % max(1, cad_val) == 0:
                applies = True
        elif cad_tip == "mesos":
            last_d = last_assigned.get(sub_id)
            if last_d is None:
                applies = True
                last_assigned[sub_id] = occ_date
            else:
                target_d = last_d + relativedelta(months=cad_val)
                if occ_date >= (target_d - timedelta(days=7)):
                    applies = True
                    last_assigned[sub_id] = occ_date
        else:
            applies = True
            
        if applies:
            active_subtasks.append({
                "id": sub_id,
                "titol": sub_titol,
                "cadencia": sub_tpl.get("cadencia", ""),
                "fet": False
            })
            
    return active_subtasks

def add_manteniment_tasks_batch(task_data: dict, dates: list, send_to_calendar: bool = False, freq_label: str = "") -> list:
    """
    Afegeix una o múltiples tasques de manteniment (sèrie periòdica o puntual).
    Retorna la llista de tasques creades.
    """
    tasks = load_registre_manteniment()
    next_id = max([int(t.get("idManteniment", 0)) for t in tasks if str(t.get("idManteniment", "")).isdigit()] + [0]) + 1
    total_dates = len(dates)
    serie_id = f"ser_{int(datetime.now().timestamp())}" if total_dates > 1 else ""
    created_tasks = []
    
    feina = task_data.get("feina", "").strip()
    obs = task_data.get("observacions", "").strip()
    tip = task_data.get("tipus", "Manteniment")
    desc_curta = feina if feina else obs
    tit_base = f"[{tip}] {desc_curta[:35]}..." if len(desc_curta) > 35 else f"[{tip}] {desc_curta or 'Tasca de manteniment'}"
    alerta_raw = task_data.get("alertaA", ["Tothom"])
    alerta_str = ", ".join(alerta_raw) if isinstance(alerta_raw, list) else str(alerta_raw)
    dies_av = task_data.get("diesAvis", 2)
    
    subtasks_tpl = task_data.get("subtasques_template", [])
    if not subtasks_tpl and task_data.get("subtasques"):
        subtasks_tpl = task_data.get("subtasques")
    last_assigned_subtasks = {}
    
    for idx, d in enumerate(dates):
        t_item = dict(task_data)
        t_item["idManteniment"] = next_id
        t_item["dataAlta"] = datetime.now().strftime("%d/%m/%Y")
        t_item["dataManteniment"] = d.strftime("%d/%m/%Y")
        t_item.setdefault("diesAvis", dies_av)
        t_item.setdefault("feina", feina)
        t_item.setdefault("tipus", tip)
        t_item.setdefault("alertaA", alerta_raw)
        t_item.setdefault("acompliment", "No")
        t_item.setdefault("observacions", obs)
        
        # Assignar subtasques que corresponen a aquesta ocurrència segons la seva cadència
        active_subtasks = filter_subtasks_for_occurrence(subtasks_tpl, idx, d, last_assigned_subtasks)
        t_item["subtasques"] = active_subtasks
        t_item["subtasques_template"] = subtasks_tpl
        
        if serie_id:
            t_item["serie_id"] = serie_id
            t_item["recurrencia"] = f"{freq_label} ({idx + 1}/{total_dates})"
        else:
            t_item["recurrencia"] = ""
            
        # Enviar a calendari si s'ha sol·licitat
        if send_to_calendar:
            try:
                from core.calendar_manager import add_event
                iso_date = d.strftime("%Y-%m-%d")
                cal_desc = f"Tasca de Manteniment #{next_id}\nFeina: {feina}\nTipus: {tip}\nAlerta a: {alerta_str}\nAvís amb {dies_av} dies d'antelació"
                if serie_id:
                    cal_desc += f"\nSèrie: {freq_label} ({idx + 1}/{total_dates})"
                if active_subtasks:
                    cal_desc += "\n\nSubtasques previstes:\n" + "\n".join([f"- [ ] {s['titol']}" for s in active_subtasks])
                if obs:
                    cal_desc += f"\n\nObservacions:\n{obs}"
                    
                tit = tit_base
                if total_dates > 1:
                    tit = f"{tit_base} ({idx + 1}/{total_dates})"
                    
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
                    t_item["calendar_event_id"] = ev["id"]
            except Exception as err:
                print("Error enviant al calendari:", err)
                
        tasks.append(t_item)
        created_tasks.append(t_item)
        next_id += 1
        
    save_registre_manteniment(tasks)
    return created_tasks
    return created_tasks

def add_manteniment_task(task_data: dict, send_to_calendar: bool = False) -> dict:
    """Afegeix una tasca de manteniment puntual."""
    d_prev = task_data.get("dataManteniment", "")
    d_obj = datetime.today().date()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            d_obj = datetime.strptime(d_prev, fmt).date()
            break
        except Exception:
            pass
    res = add_manteniment_tasks_batch(task_data, [d_obj], send_to_calendar=send_to_calendar)
    return res[0] if res else task_data

def parse_task_recurrence(rec_str: str) -> tuple:
    """
    Analitza la cadena de recurrència com 'Cada setmana (1/4)' o 'Cada 15 dies (2/6)'
    Retorna (freq_type, interval, unit, count).
    """
    if not rec_str:
        return "Puntual (una sola vegada)", 1, "Dies", 1
        
    s = str(rec_str).strip()
    count = 4
    m_count = re.search(r'\((\d+)/(\d+)\)', s)
    if m_count:
        count = int(m_count.group(2))
        
    s_low = s.lower()
    if "cada dia" in s_low:
        return "Cada dia", 1, "Dies", count
    if "cada 2 setmanes" in s_low or "quinzenal" in s_low:
        return "Cada 2 setmanes (quinzenal)", 2, "Setmanes", count
    if "cada setmana" in s_low:
        return "Cada setmana", 1, "Setmanes", count
    if "cada 2 mesos" in s_low:
        return "Cada 2 mesos", 2, "Mesos", count
    if "cada 3 mesos" in s_low or "trimestral" in s_low:
        return "Cada 3 mesos (trimestral)", 3, "Mesos", count
    if "cada 6 mesos" in s_low or "semestral" in s_low:
        return "Cada 6 mesos (semestral)", 6, "Mesos", count
    if "cada mes" in s_low:
        return "Cada mes", 1, "Mesos", count
    if "cada any" in s_low:
        return "Cada any", 1, "Anys", count
        
    m_cust = re.search(r'cada\s+(\d+)\s+(dia|dies|setmana|setmanes|mes|mesos|any|anys)', s_low)
    if m_cust:
        step = int(m_cust.group(1))
        unit_str = m_cust.group(2)
        if "dia" in unit_str: unit = "Dies"
        elif "setmana" in unit_str: unit = "Setmanes"
        elif "mes" in unit_str: unit = "Mesos"
        else: unit = "Anys"
        return "Personalitzat...", step, unit, count
        
    return "Puntual (una sola vegada)", 1, "Dies", 1

def _sync_single_task_calendar(task: dict, send_to_calendar: bool):
    """Crea o actualitza l'esdeveniment a l'agenda per a una sola tasca."""
    if not send_to_calendar:
        return
    try:
        from core.calendar_manager import add_event, update_event
        ev_id = task.get("calendar_event_id")
        d_raw = task.get("dataManteniment", "")
        iso_date = ""
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                iso_date = datetime.strptime(d_raw, fmt).strftime("%Y-%m-%d")
                break
            except Exception:
                pass
        if not iso_date:
            iso_date = datetime.today().strftime("%Y-%m-%d")
            
        feina = task.get("feina", "").strip()
        obs = task.get("observacions", "").strip()
        tip = task.get("tipus", "Manteniment")
        desc_curta = feina if feina else obs
        tit = f"[{tip}] {desc_curta[:35]}..." if len(desc_curta) > 35 else f"[{tip}] {desc_curta}"
        alerta_raw = task.get("alertaA", ["Tothom"])
        alerta_str = ", ".join(alerta_raw) if isinstance(alerta_raw, list) else str(alerta_raw)
        dies_av = task.get("diesAvis", 2)
        rec = task.get("recurrencia", "")
        
        cal_desc = f"Tasca de Manteniment #{task.get('idManteniment')}\nFeina: {feina}\nTipus: {tip}\nAlerta a: {alerta_str}\nAvís amb {dies_av} dies d'antelació"
        if rec:
            cal_desc += f"\nSèrie: {rec}"
        if obs:
            cal_desc += f"\n\nObservacions:\n{obs}"
            
        if ev_id:
            update_event(ev_id, {
                "title": tit,
                "date": iso_date,
                "time": "09:00",
                "category": "Llar",
                "description": cal_desc,
                "assigned_to": alerta_str,
                "notify": True
            })
        else:
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
                task["calendar_event_id"] = ev["id"]
    except Exception as e:
        print("Error sync calendar:", e)

def update_manteniment_task_with_recurrence(
    task_id: int,
    updated_fields: dict,
    new_dates: list,
    freq_label: str = "",
    regenerate_future: bool = False,
    send_to_calendar: bool = False
) -> bool:
    """
    Actualitza una tasca existent i opcionalment regenera les properes ocurrències de la sèrie.
    """
    tasks = load_registre_manteniment()
    curr_idx = -1
    for i, t in enumerate(tasks):
        if int(t.get("idManteniment", -1)) == int(task_id):
            curr_idx = i
            break
            
    if curr_idx == -1:
        return False
        
    curr_task = tasks[curr_idx]
    old_serie_id = curr_task.get("serie_id", "")
    
    # 1. Si s'ha triat Puntual (new_dates té 1 sol element)
    if len(new_dates) <= 1:
        updated_fields["recurrencia"] = ""
        updated_fields["serie_id"] = ""
        curr_task.update(updated_fields)
        
        # Si demanat, eliminar futures tasques pendents de l'antiga sèrie
        if old_serie_id and regenerate_future:
            try:
                from core.calendar_manager import delete_event
            except Exception:
                delete_event = None
                
            tasks_to_keep = []
            for t in tasks:
                if t.get("serie_id") == old_serie_id and int(t.get("idManteniment", -1)) != int(task_id):
                    is_done = str(t.get("acompliment", "No")).strip().lower() in ["sí", "si", "true"]
                    if not is_done:
                        cal_ev = t.get("calendar_event_id")
                        if cal_ev and delete_event:
                            try:
                                delete_event(cal_ev)
                            except Exception:
                                pass
                        continue
                tasks_to_keep.append(t)
            tasks = tasks_to_keep
            
        _sync_single_task_calendar(curr_task, send_to_calendar)
        save_registre_manteniment(tasks)
        return True

    # 2. Si s'ha triat una sèrie periòdica (len(new_dates) > 1)
    serie_id = old_serie_id if (old_serie_id and regenerate_future) else f"ser_{int(datetime.now().timestamp())}"
    total_dates = len(new_dates)
    
    # Si cal regenerar futures tasques de la sèrie antiga
    if old_serie_id and regenerate_future:
        try:
            from core.calendar_manager import delete_event
        except Exception:
            delete_event = None
            
        tasks_to_keep = []
        for t in tasks:
            if t.get("serie_id") == old_serie_id and int(t.get("idManteniment", -1)) != int(task_id):
                is_done = str(t.get("acompliment", "No")).strip().lower() in ["sí", "si", "true"]
                if not is_done:
                    cal_ev = t.get("calendar_event_id")
                    if cal_ev and delete_event:
                        try:
                            delete_event(cal_ev)
                        except Exception:
                            pass
                    continue
            tasks_to_keep.append(t)
        tasks = tasks_to_keep
        
        # Localitzar de nou curr_idx
        for i, t in enumerate(tasks):
            if int(t.get("idManteniment", -1)) == int(task_id):
                curr_idx = i
                break
        curr_task = tasks[curr_idx]

    # Actualitzar la tasca actual amb la primera data
    updated_fields["dataManteniment"] = new_dates[0].strftime("%d/%m/%Y")
    updated_fields["serie_id"] = serie_id
    updated_fields["recurrencia"] = f"{freq_label} (1/{total_dates})"
    curr_task.update(updated_fields)
    _sync_single_task_calendar(curr_task, send_to_calendar)

    # Generar les següents tasques de la sèrie (new_dates[1:])
    if regenerate_future and len(new_dates) > 1:
        next_id = max([int(t.get("idManteniment", 0)) for t in tasks if str(t.get("idManteniment", "")).isdigit()] + [0]) + 1
        feina = curr_task.get("feina", "").strip()
        obs = curr_task.get("observacions", "").strip()
        tip = curr_task.get("tipus", "Manteniment")
        tit_base = f"[{tip}] {feina[:35]}..." if len(feina) > 35 else f"[{tip}] {feina or 'Tasca'}"
        alerta_raw = curr_task.get("alertaA", ["Tothom"])
        alerta_str = ", ".join(alerta_raw) if isinstance(alerta_raw, list) else str(alerta_raw)
        dies_av = curr_task.get("diesAvis", 2)
        subtasks_tpl = curr_task.get("subtasques_template", [])
        last_assigned_subtasks = {}
        # Regla per a la data 0 (curr_task)
        _ = filter_subtasks_for_occurrence(subtasks_tpl, 0, new_dates[0], last_assigned_subtasks)
        
        try:
            from core.calendar_manager import add_event
        except Exception:
            add_event = None

        for idx, d in enumerate(new_dates[1:], start=2):
            new_t = dict(curr_task)
            new_t["idManteniment"] = next_id
            new_t["dataAlta"] = datetime.now().strftime("%d/%m/%Y")
            new_t["dataManteniment"] = d.strftime("%d/%m/%Y")
            new_t["acompliment"] = "No"
            new_t["serie_id"] = serie_id
            new_t["recurrencia"] = f"{freq_label} ({idx}/{total_dates})"
            new_t["calendar_event_id"] = None
            
            # Subtasques per a aquesta data
            active_subs = filter_subtasks_for_occurrence(subtasks_tpl, idx - 1, d, last_assigned_subtasks)
            new_t["subtasques"] = active_subs
            new_t["subtasques_template"] = subtasks_tpl
            
            if send_to_calendar and add_event:
                try:
                    iso_date = d.strftime("%Y-%m-%d")
                    cal_desc = f"Tasca de Manteniment #{next_id}\nFeina: {feina}\nTipus: {tip}\nAlerta a: {alerta_str}\nAvís amb {dies_av} dies d'antelació\nSèrie: {freq_label} ({idx}/{total_dates})"
                    if active_subs:
                        cal_desc += "\n\nSubtasques previstes:\n" + "\n".join([f"- [ ] {s['titol']}" for s in active_subs])
                    if obs:
                        cal_desc += f"\n\nObservacions:\n{obs}"
                    tit = f"{tit_base} ({idx}/{total_dates})"
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
                        new_t["calendar_event_id"] = ev["id"]
                except Exception as err:
                    print("Error calendar:", err)
                    
            tasks.append(new_t)
            next_id += 1

    save_registre_manteniment(tasks)
    return True

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
            new_val = "No" if curr in ["sí", "si", "true"] else "Sí"
            tasks[i]["acompliment"] = new_val
            # Si es marca com a Sí, marcar totes les subtasques com a fetes
            if new_val == "Sí" and "subtasques" in tasks[i] and isinstance(tasks[i]["subtasques"], list):
                for s in tasks[i]["subtasques"]:
                    s["fet"] = True
            save_registre_manteniment(tasks)
            return True
    return False

def toggle_subtask_acompliment(task_id: int, sub_id: str) -> bool:
    """Commuta l'estat d'acompliment d'una subtasca específica."""
    tasks = load_registre_manteniment()
    for i, t in enumerate(tasks):
        if int(t.get("idManteniment", -1)) == int(task_id):
            subtasques = t.get("subtasques", [])
            for s in subtasques:
                if str(s.get("id")) == str(sub_id):
                    s["fet"] = not s.get("fet", False)
                    break
            # Si totes les subtasques estan fetes, commuta la tasca principal a Sí
            if subtasques and all(s.get("fet", False) for s in subtasques):
                tasks[i]["acompliment"] = "Sí"
            save_registre_manteniment(tasks)
            return True
    return False

def get_recurring_task_templates(existing_tasks: list = None) -> list:
    """
    Retorna la llista de plantilles de tasques periòdiques (templates).
    Extreu les sèries existents a existing_tasks i les combina amb plantilles recomanades predeterminades.
    """
    if existing_tasks is None:
        existing_tasks = load_registre_manteniment()

    templates = []
    seen_feines = set()

    # 1. Extreure de les tasques existents que tenen recurrència o sèrie
    for t in existing_tasks:
        feina = str(t.get("feina", "")).strip()
        rec_str = str(t.get("recurrencia", "")).strip()
        serie_id = str(t.get("serie_id", "")).strip()
        
        if feina and (rec_str or serie_id) and feina.lower() not in seen_feines:
            seen_feines.add(feina.lower())
            freq_guess, int_guess, unit_guess, _ = parse_task_recurrence(rec_str)
            sub_tpl = t.get("subtasques_template", [])
            if not sub_tpl and t.get("subtasques"):
                sub_tpl = [
                    {
                        "id": s.get("id", f"sub_{k+1}"),
                        "titol": s.get("titol", ""),
                        "cadencia": s.get("cadencia", "A cada repetició"),
                        "cadencia_tipus": "sempre",
                        "cadencia_valor": 1
                    }
                    for k, s in enumerate(t.get("subtasques", []))
                ]
                
            d_raw = str(t.get("dataManteniment", "")).strip()
            d_obj = datetime.today().date()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    d_obj = datetime.strptime(d_raw, fmt).date()
                    break
                except Exception:
                    pass
                    
            templates.append({
                "feina": feina,
                "tipus": t.get("tipus", "Feina casa"),
                "diesAvis": int(t.get("diesAvis", 2)),
                "alertaA": t.get("alertaA", ["Tothom"]),
                "freq_type": freq_guess,
                "custom_interval": int_guess,
                "custom_unit": unit_guess,
                "subtasques_template": sub_tpl,
                "observacions": t.get("observacions", ""),
                "def_month": d_obj.month,
                "def_day": d_obj.day
            })

    # 2. Plantilles recomanades per defecte (si no existeixen ja)
    DEFAULT_RECOMMENDED = [
        {
            "feina": "Canvi llençols",
            "tipus": "Feina casa",
            "diesAvis": 2,
            "alertaA": ["Tothom"],
            "freq_type": "Personalitzat...",
            "custom_interval": 15,
            "custom_unit": "Dies",
            "def_month": 1,
            "def_day": 5,
            "subtasques_template": [
                {
                    "id": "sub_1",
                    "titol": "Rentar protector de llençols",
                    "cadencia": "Cada 6 mesos",
                    "cadencia_tipus": "mesos",
                    "cadencia_valor": 6
                }
            ],
            "observacions": "Canvi de roba de llit de totes les habitacions."
        },
        {
            "feina": "Neteja general",
            "tipus": "Feina casa",
            "diesAvis": 2,
            "alertaA": ["Tothom"],
            "freq_type": "Cada setmana",
            "custom_interval": 1,
            "custom_unit": "Setmanes",
            "def_month": 1,
            "def_day": 3,
            "subtasques_template": [],
            "observacions": "Aspirador, pols i fregar tota la casa."
        },
        {
            "feina": "Netejar filtres aire condicionat",
            "tipus": "Manteniment",
            "diesAvis": 5,
            "alertaA": ["Tothom"],
            "freq_type": "Cada 6 mesos (semestral)",
            "custom_interval": 6,
            "custom_unit": "Mesos",
            "def_month": 5,
            "def_day": 15,
            "subtasques_template": [],
            "observacions": "Desmuntar splits, aspirar i rentar filtres amb aigua tèbia abans d'estiu i hivern."
        },
        {
            "feina": "Purgar radiadors",
            "tipus": "Manteniment",
            "diesAvis": 5,
            "alertaA": ["Tothom"],
            "freq_type": "Cada any",
            "custom_interval": 1,
            "custom_unit": "Anys",
            "def_month": 10,
            "def_day": 15,
            "subtasques_template": [],
            "observacions": "Purgar tots els radiadors de la casa abans d'encendre la calefacció a la tardor."
        },
        {
            "feina": "Revisar pressió i caldera",
            "tipus": "Manteniment",
            "diesAvis": 3,
            "alertaA": ["Tothom"],
            "freq_type": "Cada 6 mesos (semestral)",
            "custom_interval": 6,
            "custom_unit": "Mesos",
            "def_month": 4,
            "def_day": 10,
            "subtasques_template": [],
            "observacions": "Comprovar manòmetre de pressió (entre 1.2 i 1.5 bar)."
        },
        {
            "feina": "Descalcificar cafetera / electrodomèstics",
            "tipus": "Manteniment",
            "diesAvis": 2,
            "alertaA": ["Tothom"],
            "freq_type": "Cada 3 mesos (trimestral)",
            "custom_interval": 3,
            "custom_unit": "Mesos",
            "def_month": 1,
            "def_day": 20,
            "subtasques_template": [],
            "observacions": "Cicle de descalcificació amb producte específic."
        },
        {
            "feina": "Netejar filtre rentadora / rentaplats",
            "tipus": "Manteniment",
            "diesAvis": 2,
            "alertaA": ["Tothom"],
            "freq_type": "Cada 3 mesos (trimestral)",
            "custom_interval": 3,
            "custom_unit": "Mesos",
            "def_month": 2,
            "def_day": 1,
            "subtasques_template": [],
            "observacions": "Buidar filtre inferior de la rentadora i netejar braços i filtre del rentaplats."
        },
        {
            "feina": "Netejar vidres",
            "tipus": "Feina casa",
            "diesAvis": 2,
            "alertaA": ["Tothom"],
            "freq_type": "Cada 2 mesos",
            "custom_interval": 2,
            "custom_unit": "Mesos",
            "def_month": 2,
            "def_day": 15,
            "subtasques_template": [],
            "observacions": "Vidres de menjador, habitacions i terrassa."
        }
    ]

    for rec in DEFAULT_RECOMMENDED:
        if rec["feina"].lower() not in seen_feines:
            templates.append(rec)
            seen_feines.add(rec["feina"].lower())

    return templates
