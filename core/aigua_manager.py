import os
import json
import pandas as pd
from datetime import datetime, date

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "consum_aigua.json")
CSV_FILE = os.path.join(PROJECT_ROOT, "csv", "consum_aigua.csv")
PDF_DIR = os.path.join(PROJECT_ROOT, "PDF", "Factures_Aigua")

CONFIG_ID = 10  # ID reservat a Supabase app_config

def load_factures_aigua() -> list:
    """Carrega les factures d'aigua des de Supabase (id=10) o fallback local."""
    try:
        from core.db import get_supabase_client
        import streamlit as st
        role = st.session_state.get("role", "guest") if "role" in st.session_state else "guest"
        supabase = get_supabase_client(role)
        res = supabase.table("app_config").select("config_json").eq("id", CONFIG_ID).execute()
        if res.data and len(res.data) > 0 and res.data[0].get("config_json"):
            cfg = res.data[0]["config_json"]
            if isinstance(cfg, list):
                return cfg
    except Exception as e:
        print(f"Nota: Carregant factures aigua des de fallback local ({e})")

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Error llegint {DATA_FILE}: {e}")

    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error llegint {CSV_FILE}: {e}")

    return []

def save_factures_aigua(records: list) -> bool:
    """Desa les factures d'aigua a Supabase, JSON local i CSV."""
    success = True
    try:
        from core.db import get_supabase_client
        import streamlit as st
        role = st.session_state.get("role", "admin") if "role" in st.session_state else "admin"
        supabase = get_supabase_client(role)
        supabase.table("app_config").upsert({
            "id": CONFIG_ID,
            "config_json": records
        }).execute()
    except Exception as e:
        print(f"Error desant factures aigua a Supabase: {e}")
        success = False

    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error desant factures aigua a JSON: {e}")
        success = False

    try:
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
        if records:
            df = pd.DataFrame(records)
            df.to_csv(CSV_FILE, index=False, encoding="utf-8")
        else:
            pd.DataFrame(columns=[
                "id", "dataFactura", "periodeInici", "periodeFi", "mesAny",
                "importTotal", "m3Consum", "lecturaAnterior", "lecturaActual",
                "comercialitzadora", "pdfFitxer", "observacions"
            ]).to_csv(CSV_FILE, index=False, encoding="utf-8")
    except Exception as e:
        print(f"Error exportant factures aigua a CSV: {e}")

    return success

def add_factura_aigua(
    data_factura: str,
    periode_inici: str,
    periode_fi: str,
    mes_any: str,
    import_total: float,
    m3_consum: float,
    lectura_anterior: float = 0.0,
    lectura_actual: float = 0.0,
    comercialitzadora: str = "Aigües de Girona",
    pdf_fitxer: str = "",
    observacions: str = ""
) -> dict:
    """Afegeix una nova factura d'aigua."""
    records = load_factures_aigua()
    max_id = 0
    for r in records:
        try:
            cid = int(r.get("id", 0))
            if cid > max_id:
                max_id = cid
        except (ValueError, TypeError):
            pass
    new_id = max_id + 1
    new_factura = {
        "id": new_id,
        "dataFactura": str(data_factura).strip(),
        "periodeInici": str(periode_inici).strip(),
        "periodeFi": str(periode_fi).strip(),
        "mesAny": str(mes_any).strip(),
        "importTotal": round(float(import_total), 2),
        "m3Consum": round(float(m3_consum), 2),
        "lecturaAnterior": round(float(lectura_anterior), 2),
        "lecturaActual": round(float(lectura_actual), 2),
        "comercialitzadora": str(comercialitzadora).strip(),
        "pdfFitxer": str(pdf_fitxer).strip(),
        "observacions": str(observacions).strip()
    }
    records.append(new_factura)
    save_factures_aigua(records)
    return new_factura

def update_factura_aigua(factura_id: int, updated_fields: dict) -> bool:
    """Actualitza una factura d'aigua existent."""
    records = load_factures_aigua()
    found = False
    for r in records:
        if int(r.get("id", 0)) == int(factura_id):
            r.update(updated_fields)
            found = True
            break
    if found:
        return save_factures_aigua(records)
    return False

def delete_factura_aigua(factura_id: int) -> bool:
    """Elimina una factura d'aigua."""
    records = load_factures_aigua()
    initial_len = len(records)
    records = [r for r in records if int(r.get("id", 0)) != int(factura_id)]
    if len(records) < initial_len:
        return save_factures_aigua(records)
    return False
