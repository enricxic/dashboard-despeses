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
