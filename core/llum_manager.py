import os
import json
import re
import urllib.request
import pandas as pd
from datetime import datetime, date, timedelta

# Rutes del projecte
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CORE_DIR)
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "consum_llum.json")
CSV_FILE = os.path.join(PROJECT_ROOT, "csv", "consum_llum.csv")
PDF_DIR = os.path.join(PROJECT_ROOT, "PDF", "Factures_Llum")
PREUS_DIARIS_FILE = os.path.join(PROJECT_ROOT, "data", "preus_llum_diaris.json")

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

DIES_SETMANA_CA = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
MESOS_ANY_CA = ["gener", "febrer", "març", "abril", "maig", "juny", "juliol", "agost", "setembre", "octubre", "novembre", "desembre"]

def formatar_data_completa_ca(dt: datetime) -> str:
    dia_set = DIES_SETMANA_CA[dt.weekday()]
    mes_nom = MESOS_ANY_CA[dt.month - 1]
    prep = "d'" if mes_nom[0] in "aeiouàèéíòóú" else "de "
    return f"{dia_set}, {dt.day} {prep}{mes_nom} de {dt.year}"


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
    # Detectar data oficial informada al codi HTML
    m_day = re.search(r'data-pvpc-day="(\d{4}-\d{2}-\d{2})"', html)
    if m_day:
        try:
            scraped_dt = datetime.strptime(m_day.group(1), "%Y-%m-%d")
        except Exception:
            scraped_dt = now
    else:
        scraped_dt = now

    is_today = (scraped_dt.date() == now.date())
    cur_weekday = scraped_dt.weekday()
    cur_hour = now.hour if is_today else 12
    
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
        
    tram_act, tram_act_lbl, tram_act_col = get_tram_horari(now) if is_today else ("", "", "")
    
    return {
        "disponible": True,
        "data": scraped_dt.strftime("%d/%m/%Y"),
        "data_iso": scraped_dt.strftime("%Y-%m-%d"),
        "dia_complet": formatar_data_completa_ca(scraped_dt),
        "dia_curt": f"{DIES_SETMANA_CA[scraped_dt.weekday()]} {scraped_dt.strftime('%d/%m')}",
        "es_dema": False,
        "font": "tarifaluzhora.es (PVPC)",
        "preu_mitja": preu_mitja,
        "hora_barata": hora_barata,
        "hora_cara": hora_cara,
        "hores": hores_list,
        "slot_actual": slot_actual if is_today else "",
        "preu_actual": preu_actual if is_today else None,
        "tram_actual": tram_act,
        "tram_actual_label": tram_act_lbl,
        "tram_actual_color": tram_act_col,
        "actualitzat_a": now.strftime("%H:%M:%S")
    }


def fetch_preu_llum_ree(target_dt: datetime = None) -> dict:
    """
    Consulta l'API pública de Red Eléctrica de España (REE) apidatos.ree.es per a una data específica (avui o demà).
    Tarifa PVPC (Preu Voluntari Petit Consumidor).
    """
    if target_dt is None:
        target_dt = datetime.now()
        
    date_str = target_dt.strftime("%Y-%m-%d")
    url = f"https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date={date_str}T00:00&end_date={date_str}T23:59&time_trunc=hour"
    
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
            
        if not pvpc_values or len(pvpc_values) < 20:
            return None
            
        now = datetime.now()
        is_today = (target_dt.date() == now.date())
        cur_hour = now.hour if is_today else -1
        target_weekday = target_dt.weekday()
        hores_list = []
        preu_actual = None
        
        for idx, val in enumerate(pvpc_values[:24]):
            h = idx
            raw_val = float(val.get("value", 0.0))
            pr_kwh = round(raw_val / 1000.0 if raw_val > 5.0 else raw_val, 4)
            slot = f"{h:02d}-{(h+1):02d}h"
            tram_codi, tram_label, tram_color = get_tram_for_hour(h, target_weekday)
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
        tram_act, tram_act_lbl, tram_act_col = get_tram_horari(now) if is_today else ("", "", "")
        
        return {
            "disponible": True,
            "data": target_dt.strftime("%d/%m/%Y"),
            "data_iso": date_str,
            "dia_complet": formatar_data_completa_ca(target_dt),
            "dia_curt": f"{DIES_SETMANA_CA[target_dt.weekday()]} {target_dt.strftime('%d/%m')}",
            "es_dema": not is_today,
            "font": "Red Eléctrica de España (REE)",
            "preu_mitja": avg_pr,
            "hora_barata": {"slot": min_item["slot"], "preu": min_item["preu"]},
            "hora_cara": {"slot": max_item["slot"], "preu": max_item["preu"]},
            "hores": hores_list,
            "slot_actual": f"{cur_hour:02d}-{(cur_hour+1):02d}h" if is_today else "",
            "preu_actual": preu_actual,
            "tram_actual": tram_act,
            "tram_actual_label": tram_act_lbl,
            "tram_actual_color": tram_act_col,
            "actualitzat_a": now.strftime("%H:%M:%S")
        }
    except Exception as e:
        return None

def fetch_preu_llum_ree_fallback() -> dict:
    """Fallback a REE per a avui (manteniment de retrocompatibilitat)."""
    return fetch_preu_llum_ree(datetime.now())

def fetch_preu_llum_dema_tarifaluzhora() -> dict:
    """
    Extreu el preu de la llum horari de demà fent web scraping a tarifaluzhora.es/info/precio-kwh-manana.
    Retorna un diccionari amb les 24h si ja s'han publicat (habitualment a partir de les 20:15h), o None si encara no.
    """
    url = "https://tarifaluzhora.es/info/precio-kwh-manana"
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
        print(f"Error scraping tarifaluzhora.es (demà): {e}")
        return None

    raw_slots = re.findall(r'(\d{1,2}-\d{1,2}h)[^€\d]*([\d,]+)\s*€/kWh', html)
    hours_map = {}
    for slot, val in raw_slots:
        parts = slot.replace("h", "").split("-")
        if len(parts) == 2:
            formatted_slot = f"{int(parts[0]):02d}-{int(parts[1]):02d}h"
        else:
            formatted_slot = slot
        if formatted_slot not in hours_map:
            hours_map[formatted_slot] = float(val.replace(",", "."))

    if len(hours_map) < 20:
        return None

    tomorrow = datetime.now() + timedelta(days=1)
    m_day = re.search(r'data-pvpc-day="(\d{4}-\d{2}-\d{2})"', html)
    if m_day:
        try:
            dema_dt = datetime.strptime(m_day.group(1), "%Y-%m-%d")
        except Exception:
            dema_dt = tomorrow
    else:
        dema_dt = tomorrow

    dema_weekday = dema_dt.weekday()
    hores_list = []
    for h in range(24):
        slot = f"{h:02d}-{(h+1):02d}h"
        pr = hours_map.get(slot, 0.0)
        tram_codi, tram_label, tram_color = get_tram_for_hour(h, dema_weekday)
        hores_list.append({
            "hora": h,
            "slot": slot,
            "preu": pr,
            "tram": tram_codi,
            "tram_label": tram_label,
            "tram_color": tram_color,
            "actual": False
        })

    min_item = min(hores_list, key=lambda x: x["preu"])
    max_item = max(hores_list, key=lambda x: x["preu"])
    avg_pr = round(sum(x["preu"] for x in hores_list) / len(hores_list), 4)

    return {
        "disponible": True,
        "data": dema_dt.strftime("%d/%m/%Y"),
        "data_iso": dema_dt.strftime("%Y-%m-%d"),
        "dia_complet": formatar_data_completa_ca(dema_dt),
        "dia_curt": f"{DIES_SETMANA_CA[dema_dt.weekday()]} {dema_dt.strftime('%d/%m')}",
        "es_dema": True,
        "font": "tarifaluzhora.es (PVPC)",
        "preu_mitja": avg_pr,
        "hora_barata": {"slot": min_item["slot"], "preu": min_item["preu"]},
        "hora_cara": {"slot": max_item["slot"], "preu": max_item["preu"]},
        "hores": hores_list,
        "slot_actual": "",
        "preu_actual": None,
        "tram_actual": "",
        "tram_actual_label": "",
        "tram_actual_color": "",
        "actualitzat_a": datetime.now().strftime("%H:%M:%S")
    }

def get_preu_llum_dema() -> dict:
    """
    Retorna les dades del preu de la llum per a demà.
    Si encara no s'han publicat (habitualment abans de les 20:15h), retorna disponible=False.
    """
    dema_dt = datetime.now() + timedelta(days=1)
    
    # 1. Provar tarifaluzhora.es demà
    res = fetch_preu_llum_dema_tarifaluzhora()
    if res and res.get("hores"):
        save_preu_llum_diari(res)
        return res
        
    # 2. Fallback REE demà
    res_ree = fetch_preu_llum_ree(dema_dt)
    if res_ree and res_ree.get("hores"):
        save_preu_llum_diari(res_ree)
        return res_ree
        
    # 3. Pendent de publicació
    return {
        "disponible": False,
        "data": dema_dt.strftime("%d/%m/%Y"),
        "data_iso": dema_dt.strftime("%Y-%m-%d"),
        "dia_complet": formatar_data_completa_ca(dema_dt),
        "dia_curt": f"{DIES_SETMANA_CA[dema_dt.weekday()]} {dema_dt.strftime('%d/%m')}",
        "hora_publicacio_estimada": "20:15 h",
        "motiu": "pendent_publicacio"
    }

def get_energia_llar_config() -> dict:
    """Retorna la configuració d'energia, acumuladors i estudi solar de la llar."""
    defaults = {
        "potencia_punta_kw": 4.4,
        "potencia_vall_kw": 5.5,
        "acumuladors": [
            {
                "id": "acum_1",
                "nom": "Menjador",
                "zona": "Menjador / Planta Baixa",
                "watts": 4000,
                "franja": "nit",
                "hores_defecte": 5,
                "color": "#fbbf24",
                "icona": "🛋️"
            },
            {
                "id": "acum_2",
                "nom": "Passadís 2a Planta",
                "zona": "Passadís 2a Planta",
                "watts": 2000,
                "franja": "migdia",
                "hores_defecte": 3,
                "color": "#38bdf8",
                "icona": "🪜"
            }
        ],
        "estudi_solar": {
            "municipi": "Arbúcies",
            "comarca": "La Selva, Girona",
            "lat": 41.8167,
            "lon": 2.5167,
            "orientacio_defecte": "ne_pur",
            "orientacio_label": "29° Nord-Est (Teulada actual)",
            "superficie_teulada_m2": 45,
            "watts_panell": 450,
            "descompte_tarifa_pct": 80
        }
    }
    try:
        from core.config_manager import load_app_config
        cfg = load_app_config().get("energia_llar", {})
        if cfg and isinstance(cfg, dict):
            defaults.update(cfg)
    except Exception:
        pass
    return defaults

def save_energia_llar_config(new_cfg: dict) -> bool:
    """Desa la configuració d'energia a config_manager i Supabase."""
    try:
        from core.config_manager import load_app_config, save_app_config
        full_cfg = load_app_config()
        if "energia_llar" not in full_cfg:
            full_cfg["energia_llar"] = {}
        full_cfg["energia_llar"].update(new_cfg)
        return save_app_config(full_cfg)
    except Exception as e:
        print(f"Error desant energia_llar: {e}")
        return False

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


def load_preus_llum_diaris() -> dict:
    """
    Carrega el registre històric complet de preus diaris de la llum (PVPC).
    Retorna un diccionari ordenat per data ISO (YYYY-MM-DD).
    """
    if not os.path.exists(PREUS_DIARIS_FILE):
        return {}
    try:
        with open(PREUS_DIARIS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error carregant {PREUS_DIARIS_FILE}: {e}")
        return {}


def save_preu_llum_diari(res: dict) -> bool:
    """
    Registra automàticament les 24 hores de preus PVPC del dia al fitxer persistent data/preus_llum_diaris.json.
    Evita duplicats, actualitza si hi ha noves dades i manté l'arxiu ordenat per data.
    """
    if not res or not res.get("hores") or len(res["hores"]) < 20:
        return False
        
    data_iso = res.get("data_iso")
    if not data_iso:
        try:
            dt = datetime.strptime(res.get("data", ""), "%d/%m/%Y")
            data_iso = dt.strftime("%Y-%m-%d")
        except Exception:
            data_iso = datetime.now().strftime("%Y-%m-%d")
            
    try:
        records = load_preus_llum_diaris()
        dt_obj = datetime.strptime(data_iso, "%Y-%m-%d")
        
        hores_list = [{
            "hora": h.get("hora"),
            "slot": h.get("slot"),
            "preu": round(float(h.get("preu", 0.0)), 6),
            "tram": h.get("tram", "")
        } for h in res.get("hores", [])]
        
        min_item = min(hores_list, key=lambda x: x["preu"]) if hores_list else {}
        max_item = max(hores_list, key=lambda x: x["preu"]) if hores_list else {}
        avg_pr = res.get("preu_mitja")
        if avg_pr is None and hores_list:
            avg_pr = round(sum(x["preu"] for x in hores_list) / len(hores_list), 6)
            
        records[data_iso] = {
            "data": res.get("data", dt_obj.strftime("%d/%m/%Y")),
            "data_iso": data_iso,
            "dia_setmana": DIES_SETMANA_CA[dt_obj.weekday()],
            "preu_mitja": avg_pr,
            "hora_barata": {"slot": min_item.get("slot", ""), "preu": min_item.get("preu", 0.0)},
            "hora_cara": {"slot": max_item.get("slot", ""), "preu": max_item.get("preu", 0.0)},
            "font": res.get("font", "PVPC"),
            "hores": hores_list,
            "actualitzat_a": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        records_sorted = dict(sorted(records.items()))
        os.makedirs(os.path.dirname(PREUS_DIARIS_FILE), exist_ok=True)
        with open(PREUS_DIARIS_FILE, "w", encoding="utf-8") as f:
            json.dump(records_sorted, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error desant preu llum diari a {PREUS_DIARIS_FILE}: {e}")
        return False


def contrastar_consum_amb_preus_diaris(csv_path: str) -> dict:
    """
    Creua un fitxer CSV de consum horari de la distribuïdora (amb columnes Fecha, Hora, Consumo Wh)
    amb el registre històric de preus diaris data/preus_llum_diaris.json.
    """
    if not os.path.exists(csv_path):
        return {"error": f"Fitxer no trobat: {csv_path}"}
        
    preus_map = load_preus_llum_diaris()
    try:
        df = pd.read_csv(csv_path, skiprows=6, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        c_fecha = [c for c in df.columns if 'Fecha' in c][0]
        c_hora = [c for c in df.columns if 'Hora' in c][0]
        c_wh = [c for c in df.columns if 'Wh' in c][0]
        c_coste = [c for c in df.columns if 'Coste' in c]
        
        df = df[df[c_fecha].astype(str).str.startswith('202')].copy()
        df['Hora'] = pd.to_numeric(df[c_hora], errors='coerce').fillna(0).astype(int)
        df['Wh'] = pd.to_numeric(df[c_wh], errors='coerce').fillna(0)
        
        total_wh = df['Wh'].sum()
        total_kwh = total_wh / 1000.0
        
        total_cost_calc = 0.0
        hores_auditades = 0
        hores_sense_preu = 0
        
        for _, row in df.iterrows():
            f_str = str(row[c_fecha]).strip()
            h_idx = int(row['Hora']) - 1
            wh = float(row['Wh'])
            kwh = wh / 1000.0
            
            day_entry = preus_map.get(f_str)
            if day_entry and len(day_entry.get("hores", [])) > h_idx:
                pr = float(day_entry["hores"][h_idx]["preu"])
                total_cost_calc += kwh * pr
                hores_auditades += 1
            else:
                hores_sense_preu += 1
                
        cost_csv = None
        if c_coste:
            df['Coste_CSV'] = pd.to_numeric(df[c_coste[0]], errors='coerce').fillna(0)
            cost_csv = round(float(df['Coste_CSV'].sum()), 2)
            
        return {
            "total_kwh": round(total_kwh, 3),
            "cost_calculat_pvpc": round(total_cost_calc, 2),
            "cost_informat_csv": cost_csv,
            "hores_auditades": hores_auditades,
            "hores_sense_preu": hores_sense_preu,
            "dates_cobertes": len(df[c_fecha].unique()),
            "coincidencia_exacta": (cost_csv is not None and abs(round(total_cost_calc, 2) - cost_csv) <= 0.05)
        }
    except Exception as e:
        return {"error": f"Error processant contrast: {e}"}


def get_preu_llum_avui() -> dict:
    """
    Funció principal que obté les dades de preu de la llum d'avui.
    Prioritat:
      1. tarifaluzhora.es
      2. REE apidatos.ree.es (Fallback)
    Desa automàticament les 24 hores de preus a data/preus_llum_diaris.json.
    """
    res = fetch_preu_llum_tarifaluzhora()
    if res and res.get("hores"):
        save_preu_llum_diari(res)
        return res
    res_ree = fetch_preu_llum_ree(datetime.now())
    if res_ree and res_ree.get("hores"):
        save_preu_llum_diari(res_ree)
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


# =========================================================================
# MODEL SOLAR FOTOVOLTAIC PER A ARBÚCIES (GIRONA)
# =========================================================================

# Radiació solar mitjana diària mensual (HSP - Hores de Sol Pic a Arbúcies / La Selva)
# Font: PVGIS / Meteocat per a latitud ~41.8°N
HSP_ARBUCIES = {
    1: 2.5,   # Gener
    2: 3.2,   # Febrer
    3: 4.4,   # Març
    4: 5.1,   # Abril
    5: 5.8,   # Maig
    6: 6.4,   # Juny
    7: 6.6,   # Juliol
    8: 5.9,   # Agost
    9: 4.7,   # Setembre
    10: 3.4,  # Octubre
    11: 2.6,  # Novembre
    12: 2.2   # Desembre
}

DIES_MES = {
    1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

NOM_MESOS_CA = [
    "Gen", "Feb", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Oct", "Nov", "Des"
]

def simular_estudi_solar(
    num_panells: int = 12,
    potencia_panell_w: int = 450,
    orientacio: str = "ne_pur",
    bateria_kwh: float = 0.0,
    carregar_acumuladors_sol: bool = True
) -> dict:
    """
    Simula la producció, autoconsum, excedents i balanç econòmic
    basant-se en les factures reals i la radiació d'Arbúcies.
    """
    kwp = (num_panells * potencia_panell_w) / 1000.0
    pr = 0.80  # Performance ratio estàndard residencial

    factors_orientacio = {
        "ne_pur": [0.68, 0.75, 0.85, 0.92, 0.95, 0.96, 0.96, 0.94, 0.88, 0.78, 0.70, 0.65],
        "est_oest": [0.88, 0.90, 0.92, 0.93, 0.94, 0.95, 0.95, 0.94, 0.93, 0.90, 0.88, 0.87],
        "sud_optim": [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]
    }
    factors = factors_orientacio.get(orientacio, factors_orientacio["ne_pur"])

    records = load_factures_llum()
    months_kwh = {}
    for r in records:
        try:
            m = int(r["mesAny"].split("-")[1])
            months_kwh.setdefault(m, []).append(float(r.get("kwhTotal", 0.0)))
        except Exception:
            pass

    mensual_dades = []
    tot_consum_anual = 0.0
    tot_generacio_anual = 0.0
    tot_autoconsum_anual = 0.0
    tot_excedents_anual = 0.0

    for m in range(1, 13):
        dies = DIES_MES[m]
        hsp = HSP_ARBUCIES[m]
        f_ori = factors[m - 1]
        prod_kwh = round(kwp * hsp * dies * pr * f_ori, 1)

        c_vals = months_kwh.get(m, [450.0])
        consum_kwh = round(sum(c_vals) / len(c_vals), 1)

        # Autoconsum diürn de base (~35% del consum ordinari té lloc en hores de sol)
        autoconsum_base_dia = consum_kwh * 0.35

        # Acumulador desviat al sol (a l'hivern podem carregar fins a 6 kWh/dia de l'acumulador de 2000W)
        autoconsum_acumuladors = 0.0
        if carregar_acumuladors_sol and m in [1, 2, 3, 4, 10, 11, 12]:
            autoconsum_acumuladors = min(6.0 * dies, prod_kwh * 0.5)

        # Bateria física (descàrrega nocturna)
        autoconsum_bateria = 0.0
        if bateria_kwh > 0:
            consum_nocturn_disponible = max(0.0, consum_kwh - autoconsum_base_dia - autoconsum_acumuladors)
            capacitat_mensual_bateria = bateria_kwh * 0.90 * 0.90 * dies
            autoconsum_bateria = min(capacitat_mensual_bateria, consum_nocturn_disponible, max(0.0, prod_kwh - autoconsum_base_dia - autoconsum_acumuladors))

        autoconsum_mes = round(min(consum_kwh, autoconsum_base_dia + autoconsum_acumuladors + autoconsum_bateria, prod_kwh), 1)
        excedents_mes = round(max(0.0, prod_kwh - autoconsum_mes), 1)
        importat_xarxa = round(max(0.0, consum_kwh - autoconsum_mes), 1)

        tot_consum_anual += consum_kwh
        tot_generacio_anual += prod_kwh
        tot_autoconsum_anual += autoconsum_mes
        tot_excedents_anual += excedents_mes

        mensual_dades.append({
            "mes_num": m,
            "mes_nom": NOM_MESOS_CA[m - 1],
            "consum_kwh": consum_kwh,
            "produccio_kwh": prod_kwh,
            "autoconsum_kwh": autoconsum_mes,
            "excedents_kwh": excedents_mes,
            "xarxa_kwh": importat_xarxa
        })

    autosuficiencia_pct = round((tot_autoconsum_anual / tot_consum_anual * 100), 1) if tot_consum_anual > 0 else 0.0
    autoconsum_ratio_pct = round((tot_autoconsum_anual / tot_generacio_anual * 100), 1) if tot_generacio_anual > 0 else 0.0

    # Estimació econòmica de mercat actual (2025/2026)
    cost_base_panells = kwp * 850.0  # Panells Tier 1 + estructures de teula
    cost_inversor_hibrid = 1400.0   # Inversor híbrid preparat per bateries
    cost_legalitzacio_cie = 650.0   # Butlletí CIE + legalització RAC / RITSIC
    cost_bateria = bateria_kwh * 450.0 if bateria_kwh > 0 else 0.0

    cost_total_empresa = round((cost_base_panells + cost_inversor_hibrid + cost_legalitzacio_cie + cost_bateria) * 1.21, 2)
    # Autoinstal·lació mixta: estalvi d'uns 1.400 € de mà d'obra de teulada
    cost_total_bricolatge = round(max(2000.0, cost_total_empresa - 1400.0), 2)

    deduccio_irpf_40 = round(cost_total_empresa * 0.40, 2)
    deduccio_irpf_60 = round(cost_total_empresa * 0.60, 2)
    bonificacio_ibi_estimada = 250.0 * 3 # ~250 €/any durant 3 anys a Arbúcies

    cost_net_empresa_amb_ajudes = round(max(500.0, cost_total_empresa - deduccio_irpf_40 - bonificacio_ibi_estimada), 2)
    cost_net_bricolatge_amb_ajudes = round(max(500.0, cost_total_bricolatge - (cost_total_bricolatge * 0.40) - bonificacio_ibi_estimada), 2)

    return {
        "kwp": round(kwp, 2),
        "num_panells": num_panells,
        "potencia_panell_w": potencia_panell_w,
        "orientacio": orientacio,
        "bateria_kwh": bateria_kwh,
        "superficie_m2": round(num_panells * 2.1, 1),
        "tot_consum_anual": round(tot_consum_anual, 1),
        "tot_generacio_anual": round(tot_generacio_anual, 1),
        "tot_autoconsum_anual": round(tot_autoconsum_anual, 1),
        "tot_excedents_anual": round(tot_excedents_anual, 1),
        "autosuficiencia_pct": autosuficiencia_pct,
        "autoconsum_ratio_pct": autoconsum_ratio_pct,
        "cost_total_empresa": cost_total_empresa,
        "cost_total_bricolatge": cost_total_bricolatge,
        "deduccio_irpf_40": deduccio_irpf_40,
        "deduccio_irpf_60": deduccio_irpf_60,
        "bonificacio_ibi_estimada": bonificacio_ibi_estimada,
        "cost_net_empresa_amb_ajudes": cost_net_empresa_amb_ajudes,
        "cost_net_bricolatge_amb_ajudes": cost_net_bricolatge_amb_ajudes,
        "mensual_dades": mensual_dades
    }
