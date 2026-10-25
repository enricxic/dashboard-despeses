import json
import os

_CURR_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.abspath(os.path.join(_CURR_DIR, "config.json"))

DEFAULT_CONFIG = {
    "admin": {
        "nom": "Enric Xicars",
        "email": "enricxicars@gmail.com",
        "telefon": "+34 600 000 000",
        "avatar": "👑",
        "rol": "Administrador",
        "pin": "1234"
    },
    "casa": {
        "paraula1": "Xiqui",
        "color1": "#407faf",
        "paraula2": "House",
        "color2": "#73ad69",
        "tamany_lletra": 60
    },
    "familia": [
        {"id": 1, "nom": "Enric", "rol": "Pare", "data_naixement": "23/09/1957", "edat": "68", "actiu": True, "alergies": [], "vetos": ["fetge", "casqueria"], "comodins": ["Pit de pollastre a la planxa", "Truita francesa"], "icona": "👨", "google_calendar_ical": "", "color": "#3b82f6"},
        {"id": 2, "nom": "Isabel", "rol": "Mare", "data_naixement": "06/03/1959", "edat": "67", "actiu": True, "alergies": [], "vetos": [], "comodins": ["Amanida completa", "Salmó a la planxa"], "icona": "👩", "google_calendar_ical": "", "color": "#ec4899"},
        {"id": 3, "nom": "Jordi", "rol": "Fill", "data_naixement": "18/12/1988", "edat": "37", "actiu": True, "alergies": [], "vetos": [], "comodins": ["Macarrons", "Hamburguesa"], "icona": "👦", "google_calendar_ical": "", "color": "#10b981"},
        {"id": 4, "nom": "Mireia", "rol": "Filla", "data_naixement": "01/08/1994", "edat": "32", "actiu": False, "alergies": ["Lactosa"], "vetos": ["Carn vermella"], "comodins": ["Wok de verdures amb tofu", "Arròs vegetal"], "icona": "👧", "google_calendar_ical": "", "color": "#f59e0b"}
    ],
    "tutelats": [],
    "bancs": [
        {"id": 1, "nom": "BBVA", "actiu": True, "icona": "🏦", "color": "#004481", "descripcio": "Compte Corrent BBVA", "titular": "Enric Xicars", "compte_iban": ""},
        {"id": 2, "nom": "LaCaixa", "actiu": True, "icona": "🏦", "color": "#007eae", "descripcio": "Compte Corrent CaixaBank", "titular": "Enric Xicars", "compte_iban": ""},
        {"id": 3, "nom": "TradeRep.", "actiu": True, "icona": "📈", "color": "#111827", "descripcio": "Compte Inversió Trade Republic", "titular": "Enric Xicars", "compte_iban": ""},
        {"id": 4, "nom": "Casa", "actiu": True, "icona": "🏠", "color": "#10b981", "descripcio": "Diners guardats a casa", "titular": "Llar", "compte_iban": ""},
        {"id": 5, "nom": "T.Moneder", "actiu": True, "icona": "👛", "color": "#f59e0b", "descripcio": "Targeta Moneder / Prepago", "titular": "Enric Xicars", "compte_iban": ""},
        {"id": 6, "nom": "T.CorteInglés", "actiu": True, "icona": "🛒", "color": "#047857", "descripcio": "Targeta El Corte Inglés", "titular": "Enric Xicars", "compte_iban": ""},
        {"id": 7, "nom": "Pago VISA", "actiu": True, "icona": "💳", "color": "#6366f1", "descripcio": "Targeta de Crèdit VISA", "titular": "Enric Xicars", "compte_iban": ""},
        {"id": 8, "nom": "Efectiu", "actiu": True, "icona": "💵", "color": "#059669", "descripcio": "Pagaments en efectiu", "titular": "Llar", "compte_iban": ""}
    ],
    "tema": "Fosc",
    "regles_menjar": {
        "max_carn_vermella": 1,
        "min_peix": 2,
        "min_llegums": 2,
        "max_embotits_sopar": 2,
        "no_repetir_hidrats": True,
        "us_forn": "Només cap de setmana (Dissabte i Diumenge)",
        "mode_apats": "Tota la setmana (Dinars i Sopars - 14 àpats)",
        "comensals_defecte": 3
    },
    "eines_cuina": {
        "forn": True,
        "microones": True,
        "airfryer": True,
        "bascula": True,
        "minipimer": True,
        "batedora_vas": True,
        "motlles_silicona": True,
        "olla_pressio": True,
        "liquadora": False,
        "tallafiambres": False,
        "robot_cuina": False,
        "picadora": True,
        "sifo_n2o": False,
        "mandolina": True
    },
    "eines_extra": [],
    "icones_actives": {
        "dashboard": True,
        "economic": True,
        "seguretat": True,
        "manteniment": True,
        "domotica": True,
        "jocs": True,
        "agenda": True,
        "medicacio": True,
        "menjar": True,
        "cotxe": True,
        "compres": True,
        "admin": True
    },
    "idioma": "ca",
    "manteniment_cotxe": {
        "oli": {"ultim_canvi_km": 30000, "interval_km": 16000, "data_ultim_canvi": ""},
        "rodes": {"ultim_canvi_km": None, "interval_km": 40000, "previst": {"km": 39600, "quantes": 2, "posicio": "Davanteres", "data": "Nadal 2026"}},
        "inflat_rodes": {
            "propera_data": "22/12/2026",
            "repeticions_any": 2,
            "avis_dies_abans": 15,
            "data_ultim_inflat": "",
            "km_ultim_inflat": None,
            "pressio": "2.4 bar",
            "planificacions": [
                {"id": "estiu", "titol": "Viatge d'estiu (~1800 km)", "dia": 20, "mes": 7, "recurrent": True, "avis_dies_abans": 15, "actiu": True},
                {"id": "nadal", "titol": "Viatge de Nadal (~1800 km)", "dia": 22, "mes": 12, "recurrent": True, "avis_dies_abans": 15, "actiu": True}
            ]
        },
        "control_nivells": {
            "propera_data": "22/12/2026",
            "repeticions_any": 2,
            "avis_dies_abans": 15,
            "data_ultim_control": "",
            "km_ultim_control": None,
            "estat_nivells": "Tots correctes (Oli, refrigerant, parabrises, frens)",
            "planificacions": [
                {"id": "estiu", "titol": "Viatge d'estiu (~1800 km)", "dia": 20, "mes": 7, "recurrent": True, "avis_dies_abans": 15, "actiu": True},
                {"id": "nadal", "titol": "Viatge de Nadal (~1800 km)", "dia": 22, "mes": 12, "recurrent": True, "avis_dies_abans": 15, "actiu": True}
            ]
        },
                "historic": []
    },
    "periferics": {
        "escaner": {
            "dispositiu": "default",
            "nom_mostrar": "Primer escàner detectat (per defecte)",
            "dpi": 300,
            "mode_color": "Color",
            "actiu": True
        },
        "impressora": {
            "activa": True,
            "metode": "raw_usb",
            "nom_controlador": "BIXOLON_SRP275",
            "port": "USB001",
            "ample_mm": 76,
            "tall_automatic": True,
            "salts_linia_tall": 6
        }
    },
    "energia_llar": {
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
    },
    "previsions_any": {
        "ingressos_recurrents": [
            {"concepte": "Complement Generalitat", "banc": "LaCaixa", "cat": "ingres_general", "dia": 25, "default_imp": 68.25},
            {"concepte": "Pensió Enric", "banc": "BBVA", "cat": "ingres_general", "dia": 25, "default_imp": 940.74},
            {"concepte": "Pensió Isabel", "banc": "BBVA", "cat": "ingres_general", "dia": 25, "default_imp": 962.50},
            {"concepte": "Cartera DP Gran", "banc": "BBVA", "cat": "ingres_general", "dia": 25, "default_imp": 47.14},
            {"concepte": "Cartera DP Petit", "banc": "BBVA", "cat": "ingres_general", "dia": 29, "default_imp": 13.99},
            {"concepte": "Pensió no contributiva", "banc": "LaCaixa", "cat": "ingres_general", "dia": 25, "default_imp": 628.80},
            {"concepte": "Hisenda 50 2", "banc": "BBVA", "cat": "ingres_general", "dia": 21, "default_imp": 50.00},
            {"concepte": "Hisenda 100", "banc": "BBVA", "cat": "ingres_general", "dia": 21, "default_imp": 100.00},
            {"concepte": "Hisenda 50 1", "banc": "BBVA", "cat": "ingres_general", "dia": 21, "default_imp": 50.00}
        ],
        "despeses_recurrents": [
            {"concepte": "Hipoteca", "banc": "BBVA", "forma": "Compte", "cat": "despesa_general", "dia": 30, "default_imp": 489.43},
            {"concepte": "Lowi", "banc": "BBVA", "forma": "Compte", "cat": "despesa_general", "dia": 19, "default_imp": 35.90},
            {"concepte": "DP Morts Enric", "banc": "BBVA", "forma": "Compte", "cat": "assegurança", "dia": 7, "default_imp": 14.04},
            {"concepte": "BBVA Asseg. Casa", "banc": "BBVA", "forma": "Compte", "cat": "assegurança", "dia": 7, "default_imp": 42.34},
            {"concepte": "PJ Isabel", "banc": "BBVA", "forma": "Compte", "cat": "despesa_general", "dia": 5, "default_imp": 231.53},
            {"concepte": "Ajunt. Arbúcies", "banc": "LaCaixa", "forma": "Compte", "cat": "despesa_general", "dia": 5, "default_imp": 68.46},
            {"concepte": "Piscina", "banc": "BBVA", "forma": "Compte", "cat": "despesa_general", "dia": 4, "default_imp": 90.28},
            {"concepte": "Accions NVIDIA", "banc": "TradeRep.", "forma": "Compte", "cat": "despesa_general", "dia": 2, "default_imp": 25.00},
            {"concepte": "Accions S&P500", "banc": "TradeRep.", "forma": "Compte", "cat": "despesa_general", "dia": 2, "default_imp": 25.00},
            {"concepte": "Ocaso", "banc": "BBVA", "forma": "Compte", "cat": "despesa_general", "dia": 2, "default_imp": 12.90},
            {"concepte": "Endesa", "banc": "BBVA", "forma": "Compte", "cat": "despesa_general", "dia": 1, "default_imp": 25.00},
            {"concepte": "Lloguer Parking", "banc": "Efectiu", "forma": "Compte", "cat": "despesa_general", "dia": 1, "default_imp": 55.00}
        ],
        "pagues_extres": [
            {"concepte": "Paga extra Enric", "origen": "Pensió Enric", "banc": "BBVA", "cat": "ingres_general", "dia": 25, "default_imp": 940.74, "mesos": [6, 11]},
            {"concepte": "Paga extra Isa", "origen": "Pensió Isabel", "banc": "BBVA", "cat": "ingres_general", "dia": 25, "default_imp": 962.50, "mesos": [6, 11]},
            {"concepte": "Paga extra Pensió no contributiva", "origen": "Pensió no contributiva", "banc": "LaCaixa", "cat": "ingres_general", "dia": 25, "default_imp": 628.80, "mesos": [6, 11]}
        ]
    }
}

TRANSLATIONS = {
    "ca": {
        "settings_title": "Configuració",
        "search_placeholder": "Cercar ajustos",
        "save": "Desar canvis",
        "saved_success": "Configuració desada correctament!",
        "admin_title": "Administrador",
        "casa_title": "Títol de la casa",
        "familia_title": "Família",
        "menjar_title": "Menús i Nutrició",
        "tutelats_title": "Persones Tutelades",
        "bancs_title": "Bancs i Comptes",
        "tema_title": "Aspecte i Tema",
        "icones_title": "Icones d'inici",
        "idioma_title": "Idiomes",
        "periferics_title": "Perifèrics (Impressora i Escàner)",
        "back_home": "Tornar a l'inici",
        "slogan": "TOTA LA TEVA LLAR, CONTROLADA"
    },
    "es": {
        "settings_title": "Configuración",
        "search_placeholder": "Buscar ajustes",
        "save": "Guardar cambios",
        "saved_success": "¡Configuración guardada correctamente!",
        "admin_title": "Administrador",
        "casa_title": "Título de la casa",
        "familia_title": "Familia",
        "tutelats_title": "Personas Tuteladas",
        "bancs_title": "Bancos y Cuentas",
        "tema_title": "Aspecto y Tema",
        "icones_title": "Iconos de inicio",
        "idioma_title": "Idiomas",
        "back_home": "Volver al inicio",
        "slogan": "TODO TU HOGAR, CONTROLADO"
    },
    "en": {
        "settings_title": "Settings",
        "search_placeholder": "Search settings",
        "save": "Save changes",
        "saved_success": "Settings saved successfully!",
        "admin_title": "Administrator",
        "casa_title": "House Title",
        "familia_title": "Family",
        "tutelats_title": "Guarded Persons",
        "bancs_title": "Banks and Accounts",
        "tema_title": "Appearance and Theme",
        "icones_title": "Home screen icons",
        "idioma_title": "Languages",
        "back_home": "Back to Home",
        "slogan": "ALL YOUR HOME, UNDER CONTROL"
    },
    "fr": {
        "settings_title": "Paramètres",
        "search_placeholder": "Rechercher des paramètres",
        "save": "Enregistrer les modifications",
        "saved_success": "Paramètres enregistrés avec succès !",
        "admin_title": "Administrateur",
        "casa_title": "Titre de la maison",
        "familia_title": "Famille",
        "tutelats_title": "Personnes sous tutelle",
        "bancs_title": "Banques et Comptes",
        "tema_title": "Apparence et Thème",
        "icones_title": "Icônes d'accueil",
        "idioma_title": "Langues",
        "back_home": "Retour à l'accueil",
        "slogan": "TOUTE VOTRE MAISON, CONTRÔLÉE"
    }
}

import copy
import streamlit as st

@st.cache_data(ttl=3600, show_spinner=False)
def load_app_config():
    # Intenta llegir de Supabase primer (id=2 per la configuració general)
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client("guest")
        res = supabase.table("app_config").select("config_json").eq("id", 2).execute()
        if res.data and len(res.data) > 0:
            cfg = res.data[0]["config_json"]
            merged = copy.deepcopy(DEFAULT_CONFIG)
            for k, v in cfg.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            # Assegurar estructura inflat_rodes i control_nivells
            mant_c = merged.setdefault("manteniment_cotxe", {})
            inf_c = mant_c.setdefault("inflat_rodes", {})
            if "pressio" not in inf_c or not inf_c["pressio"]:
                inf_c["pressio"] = "2.4 bar"
            if "planificacions" not in inf_c or not isinstance(inf_c["planificacions"], list) or len(inf_c["planificacions"]) == 0:
                inf_c["planificacions"] = copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
            
            niv_c = mant_c.setdefault("control_nivells", {})
            if "estat_nivells" not in niv_c or not niv_c["estat_nivells"]:
                niv_c["estat_nivells"] = "Tots correctes (Oli, refrigerant, parabrises, frens)"
            if "planificacions" not in niv_c or not isinstance(niv_c["planificacions"], list) or len(niv_c["planificacions"]) == 0:
                niv_c["planificacions"] = copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
            return merged
    except Exception as e:
        print("Supabase config_manager load failed:", e)

    # Fallback: llegir del fitxer local
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_app_config(copy.deepcopy(DEFAULT_CONFIG))
        return copy.deepcopy(DEFAULT_CONFIG)
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            merged = copy.deepcopy(DEFAULT_CONFIG)
            for k, v in cfg.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            # Assegurar estructura inflat_rodes i control_nivells
            mant_c = merged.setdefault("manteniment_cotxe", {})
            inf_c = mant_c.setdefault("inflat_rodes", {})
            if "pressio" not in inf_c or not inf_c["pressio"]:
                inf_c["pressio"] = "2.4 bar"
            if "planificacions" not in inf_c or not isinstance(inf_c["planificacions"], list) or len(inf_c["planificacions"]) == 0:
                inf_c["planificacions"] = copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
            
            niv_c = mant_c.setdefault("control_nivells", {})
            if "estat_nivells" not in niv_c or not niv_c["estat_nivells"]:
                niv_c["estat_nivells"] = "Tots correctes (Oli, refrigerant, parabrises, frens)"
            if "planificacions" not in niv_c or not isinstance(niv_c["planificacions"], list) or len(niv_c["planificacions"]) == 0:
                niv_c["planificacions"] = copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
            return merged
    except Exception as e:
        print("Error reading config file:", e)
        return copy.deepcopy(DEFAULT_CONFIG)

def save_app_config(cfg_data):
    load_app_config.clear()
    # Desar primer a Supabase (id=2)
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client("admin")
        supabase.table("app_config").upsert({
            "id": 2,
            "config_json": cfg_data
        }).execute()
    except Exception as e:
        print("Error saving config to Supabase:", e)

    # Backup local
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print("Error saving config file:", e)
        return False

def get_bancs_config():
    cfg = load_app_config()
    return cfg.get("bancs", DEFAULT_CONFIG.get("bancs", []))

def get_active_bancs():
    bancs = get_bancs_config()
    return [b for b in bancs if b.get("actiu", True)]

def get_translation(key, lang="ca"):
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["ca"])
    return lang_dict.get(key, key)

DEFAULT_CATALEG_EINES = [
    {"id": "forn", "nom": "Forn", "foto": "imatges/Eines/forn.png", "desc": "Rostits, gratinats, pastissos i pizzes"},
    {"id": "microones", "nom": "Microones", "foto": "imatges/Eines/microones.jpg", "desc": "Escalfat ràpid i vapor"},
    {"id": "airfryer", "nom": "Airfryer", "foto": "imatges/Eines/airfryer.jpg", "desc": "Fregits saludables i cruixents"},
    {"id": "bascula", "nom": "Bàscula de cuina", "foto": "imatges/Eines/bascula.jpg", "desc": "Pesat precís de racions"},
    {"id": "minipimer", "nom": "Minipimer", "foto": "imatges/Eines/minipimer.jpg", "desc": "Cremes, purés i maioneses"},
    {"id": "batedora_vas", "nom": "Batedora de vas", "foto": "imatges/Eines/batedora_vas.jpg", "desc": "Batuts, smoothies i gaspatxos"},
    {"id": "motlles_silicona", "nom": "Motlles de silicona", "foto": "imatges/Eines/motlles_silicona.jpg", "desc": "Rebosteria i flameres"},
    {"id": "olla_pressio", "nom": "Olla a pressió", "foto": "imatges/Eines/olla_pressio.jpg", "desc": "Llegums i estofats exprés"},
    {"id": "liquadora", "nom": "Liquadora", "foto": "imatges/Eines/liquadora.jpg", "desc": "Sucs naturals i liquats"},
    {"id": "tallafiambres", "nom": "Tallafiambres", "foto": "imatges/Eines/tallafiambres.jpg", "desc": "Talls fins d'embotits"},
    {"id": "robot_cuina", "nom": "Robot de cuina", "foto": "imatges/Eines/robot_cuina.jpg", "desc": "Emulsions i cocció guiada"},
    {"id": "picadora", "nom": "Picadora", "foto": "imatges/Eines/picadora.jpg", "desc": "Picar carn i sofregits"},
    {"id": "sifo_n2o", "nom": "Sifó N2O", "foto": "imatges/Eines/sifo_n2o.jpg", "desc": "Espumes d'avantguarda"},
    {"id": "mandolina", "nom": "Mandolina", "foto": "imatges/Eines/mandolina.jpg", "desc": "Talls laminats precisos"},
]

def get_cataleg_eines(cfg=None):
    if cfg is None:
        cfg = load_app_config()
    extra = cfg.get("eines_extra", [])
    default_ids = {e["id"] for e in DEFAULT_CATALEG_EINES}
    result = list(DEFAULT_CATALEG_EINES)
    for e in extra:
        if isinstance(e, dict) and e.get("id") and e["id"] not in default_ids:
            result.append(e)
    return result


DEFAULT_PLANIFICACIONS_INFLAT = [
    {"id": "estiu", "titol": "Viatge d'estiu (~1800 km)", "dia": 20, "mes": 7, "recurrent": True, "avis_dies_abans": 15, "actiu": True},
    {"id": "nadal", "titol": "Viatge de Nadal (~1800 km)", "dia": 22, "mes": 12, "recurrent": True, "avis_dies_abans": 15, "actiu": True}
]

def get_inflat_occurrences(planificacions, data_ultim_inflat_str=None, avui=None):
    from datetime import date as d_date, datetime as dt_datetime, timedelta
    if avui is None:
        avui = dt_datetime.today().date()
    elif isinstance(avui, dt_datetime):
        avui = avui.date()
        
    d_ultim = None
    if data_ultim_inflat_str:
        try:
            d_ultim = dt_datetime.strptime(str(data_ultim_inflat_str).strip(), "%d/%m/%Y").date()
        except Exception:
            pass

    results = []
    if not planificacions or not isinstance(planificacions, list):
        return results

    for p in planificacions:
        if not isinstance(p, dict) or not p.get("actiu", True):
            continue
        titol = p.get("titol", "Inflat de rodes")
        avis_dies = int(p.get("avis_dies_abans", 15))
        is_recurrent = p.get("recurrent", True)
        ultim_fet_any = p.get("ultim_fet_any")
        
        if is_recurrent:
            dia = int(p.get("dia", 1))
            mes = int(p.get("mes", 1))
            
            try:
                date_this_year = d_date(avui.year, mes, dia)
            except ValueError:
                date_this_year = d_date(avui.year, mes, 28)
                
            if ultim_fet_any == avui.year:
                next_date = d_date(avui.year + 1, mes, dia)
                status = "fet_enguany"
            elif avui <= date_this_year:
                next_date = date_this_year
                status = "pendent"
            else:
                # avui > date_this_year
                if d_ultim and abs((d_ultim - date_this_year).days) <= 25 and d_ultim >= (date_this_year - timedelta(days=15)):
                    next_date = d_date(avui.year + 1, mes, dia)
                    status = "fet_enguany"
                elif (avui - date_this_year).days <= 30:
                    next_date = date_this_year
                    status = "superat"
                else:
                    next_date = d_date(avui.year + 1, mes, dia)
                    status = "proper_any"
        else:
            d_str = p.get("data_puntual", "")
            try:
                next_date = dt_datetime.strptime(str(d_str).strip(), "%d/%m/%Y").date()
            except Exception:
                continue
            if p.get("fet", False) or (d_ultim and d_ultim >= next_date):
                status = "fet"
            elif avui <= next_date:
                status = "pendent"
            else:
                status = "superat"

        dies_left = (next_date - avui).days
        results.append({
            "id": p.get("id", titol),
            "titol": titol,
            "next_date": next_date,
            "dies_left": dies_left,
            "avis_dies": avis_dies,
            "status": status,
            "recurrent": is_recurrent,
            "dia": p.get("dia"),
            "mes": p.get("mes"),
            "data_puntual": p.get("data_puntual")
        })
        
    return results


# Àlies per compatibilitat
load_config = load_app_config
save_config = save_app_config

