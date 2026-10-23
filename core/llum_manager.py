import os
import json
import re
import urllib.request
import pandas as pd
from datetime import datetime, date

# Rutes del projecte
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "consum_llum.json")
CSV_FILE = os.path.join(PROJECT_ROOT, "csv", "consum_llum.csv")
PDF_DIR = os.path.join(PROJECT_ROOT, "PDF", "Factures_Llum")

CONFIG_ID = 9  # ID reservat a Supabase app_config

# Festius nacionals espanyols típics (fixos)
FESTIUS_FIXOS = {
    (1, 1),   # Cap d'any
    (1, 6),   # Reis
    (5, 1),   # Treball
    (8, 15),  # Assumpció
    (10, 12), # Festa Nacional
    (11, 1),  # Tots Sants
    (12, 6),  # Constitució
    (12, 8),  # Immaculada
    (12, 25), # Nadal
}

def get_tram_horari(dt: datetime = None) -> tuple:
    """
    Retorna el tram horari segons la regulació elèctrica 2.0TD (Espanya peninsular).
    Trams:
      - Valle (Vall): Caps de setmana, festius nacionals, i de 00:00 a 08:00 en feiners.
      - Llano (Pla): Feiners de 08:00 a 10:00, de 14:00 a 18:00 i de 22:00 a 24:00.
      - Punta (Punta): Feiners de 10:00 a 14:00 i de 18:00 a 22:00.
    Retorna una tupla: (codi, etiqueta, color_hex).
    """
    if dt is None:
        dt = datetime.now()
        
    weekday = dt.weekday()  # 0=Dilluns, 6=Diumenge
    month, day = dt.month, dt.day
    hour = dt.hour
    
    # Cap de setmana o festiu fix
    if weekday in (5, 6) or (month, day) in FESTIUS_FIXOS:
        return "Valle", "🟢 Vall", "#10b981"
        
    # Feiners segons l'hora
    if 0 <= hour < 8:
        return "Valle", "🟢 Vall", "#10b981"
    elif (8 <= hour < 10) or (14 <= hour < 18) or (22 <= hour < 24):
        return "Llano", "🟡 Pla", "#f59e0b"
    else:  # 10..14 i 18..22
        return "Punta", "🔴 Punta", "#ef4444"


def get_tram_for_hour(hour: int, weekday: int = 0) -> tuple:
    """Retorna el tram horari per a una hora concreta (0..23) i dia de la setmana."""
    if weekday in (5, 6):
        return "Valle", "🟢 Vall", "#10b981"
    if 0 <= hour < 8:
        return "Valle", "🟢 Vall", "#10b981"
    elif (8 <= hour < 10) or (14 <= hour < 18) or (22 <= hour < 24):
        return "Llano", "🟡 Pla", "#f59e0b"
    else:
        return "Punta", "🔴 Punta", "#ef4444"


def fetch_preu_llum_tarifaluzhora() -> dict:
    """
    Extreu el preu de la llum horari d'avui fent web scraping a tarifaluzhora.es.
    Si falla, retorna None per permetre fallback a l'API de Red Eléctrica (REE).
    """
    url = "https://tarifaluzhora.es"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ca,es,en;q=0.9"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=7) as res:
            html = res.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error scraping tarifaluzhora.es: {e}")
        return None
        
    now = datetime.now()
    cur_weekday = now.weekday()
    cur_hour = now.hour
    
    # Preu mitjà
    preu_mitja = None
    m_avg = re.search(r'precio medio de la luz.+?es de\s*([\d,]+)\s*€/kWh', html, re.I)
    if m_avg:
        preu_mitja = float(m_avg.group(1).replace(",", "."))
        
    # Hora més barata
    hora_barata = None
    m_cheap = re.search(r'm[áa]s barata ser[áa] de\s*(\d{1,2}-\d{1,2}h)[^€\d]*([\d,]+)\s*€/kWh', html, re.I)
    if m_cheap:
        hora_barata = {
            "slot": m_cheap.group(1),
            "preu": float(m_cheap.group(2).replace(",", "."))
        }
        
    # Hora més cara
    hora_cara = None
    m_exp = re.search(r'm[áa]s cara ser[áa] de\s*(\d{1,2}-\d{1,2}h)[^€\d]*([\d,]+)\s*€/kWh', html, re.I)
    if m_exp:
        hora_cara = {
            "slot": m_exp.group(1),
            "preu": float(m_exp.group(2).replace(",", "."))
        }
        
    # 24 hores
    raw_slots = re.findall(r'(\d{2}-\d{2}h)[^€\d]*([\d,]+)\s*€/kWh', html)
    hours_map = {}
    for slot, val in raw_slots:
        if slot not in hours_map:
            hours_map[slot] = float(val.replace(",", "."))
            
    if len(hours_map) < 20:
        # Menys de 20 hores trobades, scraping incomplet
        return None
        
    hores_list = []
    preu_actual = None
    slot_actual = f"{cur_hour:02d}-{(cur_hour+1):02d}h"
    
    for h in range(24):
        slot = f"{h:02d}-{(h+1):02d}h"
        pr = hours_map.get(slot, 0.0)
        tram_codi, tram_label, tram_color = get_tram_for_hour(h, cur_weekday)
        is_current = (h == cur_hour)
        if is_current:
            preu_actual = pr
            
        hores_list.append({
            "hora": h,
            "slot": slot,
            "preu": pr,
            "tram": tram_codi,
            "tram_label": tram_label,
            "tram_color": tram_color,
            "actual": is_current
        })
        
    # Si no hem trobat hora barata o cara per text, la calculem nosaltres
    if not hora_barata and hores_list:
        min_item = min(hores_list, key=lambda x: x["preu"])
        hora_barata = {"slot": min_item["slot"], "preu": min_item["preu"]}
    if not hora_cara and hores_list:
        max_item = max(hores_list, key=lambda x: x["preu"])
        hora_cara = {"slot": max_item["slot"], "preu": max_item["preu"]}
    if preu_mitja is None and hores_list:
        preu_mitja = round(sum(x["preu"] for x in hores_list) / len(hores_list), 4)
        
    tram_act, tram_act_lbl, tram_act_col = get_tram_horari(now)
    
    return {
        "data": now.strftime("%d/%m/%Y"),
        "font": "tarifaluzhora.es (PVPC)",
        "preu_mitja": preu_mitja,
        "hora_barata": hora_barata,
        "hora_cara": hora_cara,
        "hores": hores_list,
        "slot_actual": slot_actual,
        "preu_actual": preu_actual,
        "tram_actual": tram_act,
        "tram_actual_label": tram_act_lbl,
        "tram_actual_color": tram_act_col,
        "actualitzat_a": now.strftime("%H:%M:%S")
    }


def fetch_preu_llum_ree_fallback() -> dict:
    """
    Fallback a l'API pública de Red Eléctrica de España (REE) apidatos.ree.es.
    Tarifa PVPC (Preu Voluntari Petit Consumidor).
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    url = f"https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date={today_str}T00:00&end_date={today_str}T23:59&time_trunc=hour"
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DashboardApp/1.0", "Accept": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode("utf-8"))
            
        included = data.get("included", [])
        pvpc_values = []
        for item in included:
            if "PVPC" in item.get("type", "") or "PVPC" in item.get("attributes", {}).get("title", ""):
                pvpc_values = item.get("attributes", {}).get("values", [])
                break
                
        if not pvpc_values and included:
            pvpc_values = included[0].get("attributes", {}).get("values", [])
            
        if not pvpc_values:
            return None
            
        cur_hour = now.hour
        cur_weekday = now.weekday()
        hores_list = []
        preu_actual = None
        
        for idx, val in enumerate(pvpc_values[:24]):
            h = idx
            # L'API de REE sol donar el preu en €/MWh -> dividir per 1000 per tenir €/kWh
            raw_val = float(val.get("value", 0.0))
            pr_kwh = round(raw_val / 1000.0 if raw_val > 5.0 else raw_val, 4)
            slot = f"{h:02d}-{(h+1):02d}h"
            tram_codi, tram_label, tram_color = get_tram_for_hour(h, cur_weekday)
            is_cur = (h == cur_hour)
            if is_cur:
                preu_actual = pr_kwh
            hores_list.append({
                "hora": h,
                "slot": slot,
                "preu": pr_kwh,
                "tram": tram_codi,
                "tram_label": tram_label,
                "tram_color": tram_color,
                "actual": is_cur
            })
            
        if not hores_list:
            return None
            
        min_item = min(hores_list, key=lambda x: x["preu"])
        max_item = max(hores_list, key=lambda x: x["preu"])
        avg_pr = round(sum(x["preu"] for x in hores_list) / len(hores_list), 4)
        tram_act, tram_act_lbl, tram_act_col = get_tram_horari(now)
        
        return {
            "data": now.strftime("%d/%m/%Y"),
            "font": "Red Eléctrica de España (REE)",
            "preu_mitja": avg_pr,
            "hora_barata": {"slot": min_item["slot"], "preu": min_item["preu"]},
            "hora_cara": {"slot": max_item["slot"], "preu": max_item["preu"]},
            "hores": hores_list,
            "slot_actual": f"{cur_hour:02d}-{(cur_hour+1):02d}h",
            "preu_actual": preu_actual,
            "tram_actual": tram_act,
            "tram_actual_label": tram_act_lbl,
            "tram_actual_color": tram_act_col,
            "actualitzat_a": now.strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"Error fallback REE: {e}")
        return None


CONFIG_ACUM_FILE = os.path.join(PROJECT_ROOT, "data", "acumuladors_config.json")

def load_acumuladors_config() -> dict:
    """Carrega la configuració d'hores i franges dels acumuladors."""
    defaults = {
        "hores_4000w": 5,
        "hores_2000w": 3,
        "franja_2000w": "migdia"
    }
    if os.path.exists(CONFIG_ACUM_FILE):
        try:
            with open(CONFIG_ACUM_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    defaults.update(saved)
        except Exception as e:
            print(f"Error llegint configuració acumuladors: {e}")
    return defaults

def save_acumuladors_config(cfg: dict) -> bool:
    """Desa la configuració dels acumuladors per mantenir-la en memòria persistent."""
    try:
        os.makedirs(os.path.dirname(CONFIG_ACUM_FILE), exist_ok=True)
        with open(CONFIG_ACUM_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error desant configuració acumuladors: {e}")
        return False

def calcular_finestra_acumuladors(hores_list: list, durada_hores: int = 5, franja: str = "nit", nomes_nit: bool = None) -> dict:
    """
    Calcula la finestra òptima per a la càrrega d'acumuladors de calor elèctrics.
    Franges disponibles:
      - 'nit': 00:00 a 08:00 h (Vall, potència de 5,5 kW, per a acumulador 4000W)
      - 'migdia': 11:00 a 19:00 h (Pla / Solar dip, 4,4 kW, per a acumulador 2000W)
      - 'dia': 08:00 a 24:00 h
      - 'tot': 00:00 a 24:00 h
    """
    if not hores_list:
        return {}

    if nomes_nit is not None:
        franja = "nit" if nomes_nit else "tot"

    if franja == "nit":
        candidats = [h for h in hores_list if 0 <= h.get("hora", 0) <= 7]
        pot_disp = 5.5
    elif franja == "migdia":
        candidats = [h for h in hores_list if 11 <= h.get("hora", 0) <= 18]
        pot_disp = 4.4
    elif franja == "dia":
        candidats = [h for h in hores_list if 8 <= h.get("hora", 0) <= 23]
        pot_disp = 4.4
    else:
        candidats = hores_list
        pot_disp = 4.4

    durada = min(durada_hores, len(candidats))
    if durada <= 0:
        return {}

    # 1. Finestra contínua més econòmica
    millor_sublist = None
    millor_avg = 9999.0

    for i in range(len(candidats) - durada + 1):
        finestra = candidats[i:i + durada]
        avg = sum(h["preu"] for h in finestra) / durada
        if avg < millor_avg:
            millor_avg = avg
            millor_sublist = finestra

    # 2. Hores individuals més barates
    hores_indiv = sorted(candidats, key=lambda x: x["preu"])[:durada]
    avg_indiv = sum(h["preu"] for h in hores_indiv) / durada if hores_indiv else 0.0

    # 3. Mitjana general de referència (de tot el dia)
    global_avg = sum(h["preu"] for h in hores_list) / len(hores_list) if hores_list else 0.0
    estalvi_pct = 0.0
    if global_avg > 0 and millor_avg < 9999.0:
        estalvi_pct = round(((global_avg - millor_avg) / global_avg) * 100, 1)

    res = {
        "durada_hores": durada,
        "franja": franja,
        "nomes_nit": (franja == "nit"),
        "potencia_disponible_kw": pot_disp,
        "global_avg": round(global_avg, 4),
        "estalvi_percent": estalvi_pct
    }

    if millor_sublist:
        h_inici = millor_sublist[0]["hora"]
        h_fi = millor_sublist[-1]["hora"] + 1
        res["millor_finestra"] = {
            "hora_inici": h_inici,
            "hora_fi": h_fi,
            "rang_text": f"De {h_inici:02d}:00h a {h_fi:02d}:00h",
            "preu_mitja": round(millor_avg, 4),
            "hores": millor_sublist
        }
    else:
        res["millor_finestra"] = None

    res["hores_individuals"] = {
        "preu_mitja": round(avg_indiv, 4),
        "hores": hores_indiv
    }

    return res


def get_preu_llum_avui() -> dict:
    """
    Funció principal que obté les dades de preu de la llum.
    Prioritat:
      1. tarifaluzhora.es
      2. REE apidatos.ree.es (Fallback)
    """
    res = fetch_preu_llum_tarifaluzhora()
    if res:
        return res
    res_ree = fetch_preu_llum_ree_fallback()
    if res_ree:
        return res_ree
    return None


# =========================================================================
# GESTIÓ DE FACTURES I HISTÒRIC DE CONSUMS
# =========================================================================

def load_factures_llum() -> list:
    """
    Carrega la llista de factures de la llum des de Supabase (id=9 a app_config).
    Fallback 1: data/consum_llum.json
    Fallback 2: csv/consum_llum.csv
    """
    # 1. Supabase
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
        print(f"Nota: Carregant factures llum des de fallback local ({e})")

    # 2. Fitxer JSON local
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"Error llegint {DATA_FILE}: {e}")

    # 3. Fitxer CSV local
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error llegint {CSV_FILE}: {e}")

    return []


def save_factures_llum(records: list) -> bool:
    """
    Desa les factures de la llum a Supabase (id=9 a app_config),
    al fitxer JSON local data/consum_llum.json i al fitxer CSV csv/consum_llum.csv.
    """
    success = True
    
    # 1. Supabase
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
        print(f"Error desant factures llum a Supabase: {e}")
        success = False

    # 2. JSON Local
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error desant factures llum a JSON: {e}")
        success = False

    # 3. CSV Local
    try:
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
        if records:
            df = pd.DataFrame(records)
            df.to_csv(CSV_FILE, index=False, encoding="utf-8")
        else:
            pd.DataFrame(columns=[
                "id", "dataFactura", "periodeInici", "periodeFi", "mesAny",
                "importTotal", "kwhPunta", "kwhLlano", "kwhValle", "kwhTotal",
                "potenciaDia", "potenciaNit", "comercialitzadora", "pdfFitxer", "observacions"
            ]).to_csv(CSV_FILE, index=False, encoding="utf-8")
    except Exception as e:
        print(f"Error exportant factures llum a CSV: {e}")

    return success


def add_factura_llum(
    data_factura: str,
    periode_inici: str,
    periode_fi: str,
    mes_any: str,
    import_total: float,
    kwh_punta: float,
    kwh_llano: float,
    kwh_valle: float,
    potencia_dia: float = 4.4,
    potencia_nit: float = 5.5,
    comercialitzadora: str = "Energía XXI (Bono Social)",
    pdf_fitxer: str = "",
    observacions: str = ""
) -> dict:
    """Afegeix una nova factura de la llum i la desa."""
    records = load_factures_llum()
    
    max_id = 0
    for r in records:
        try:
            cid = int(r.get("id", 0))
            if cid > max_id:
                max_id = cid
        except (ValueError, TypeError):
            pass
            
    new_id = max_id + 1
    kwh_total = round(float(kwh_punta) + float(kwh_llano) + float(kwh_valle), 2)
    
    new_factura = {
        "id": new_id,
        "dataFactura": str(data_factura).strip(),
        "periodeInici": str(periode_inici).strip(),
        "periodeFi": str(periode_fi).strip(),
        "mesAny": str(mes_any).strip(),
        "importTotal": round(float(import_total), 2),
        "kwhPunta": round(float(kwh_punta), 2),
        "kwhLlano": round(float(kwh_llano), 2),
        "kwhValle": round(float(kwh_valle), 2),
        "kwhTotal": kwh_total,
        "potenciaDia": round(float(potencia_dia), 2),
        "potenciaNit": round(float(potencia_nit), 2),
        "comercialitzadora": str(comercialitzadora).strip(),
        "pdfFitxer": str(pdf_fitxer).strip(),
        "observacions": str(observacions).strip()
    }
    
    records.append(new_factura)
    save_factures_llum(records)
    return new_factura


def update_factura_llum(factura_id: int, updated_fields: dict) -> bool:
    """Actualitza una factura existent."""
    records = load_factures_llum()
    found = False
    
    for r in records:
        if int(r.get("id", 0)) == int(factura_id):
            r.update(updated_fields)
            # Recalcular total si s'han tocat els kWh
            if any(k in updated_fields for k in ["kwhPunta", "kwhLlano", "kwhValle"]):
                r["kwhTotal"] = round(
                    float(r.get("kwhPunta", 0.0)) +
                    float(r.get("kwhLlano", 0.0)) +
                    float(r.get("kwhValle", 0.0)),
                    2
                )
            found = True
            break
            
    if found:
        return save_factures_llum(records)
    return False


def delete_factura_llum(factura_id: int) -> bool:
    """Elimina una factura pel seu ID."""
    records = load_factures_llum()
    initial_len = len(records)
    records = [r for r in records if int(r.get("id", 0)) != int(factura_id)]
    
    if len(records) < initial_len:
        return save_factures_llum(records)
    return False
