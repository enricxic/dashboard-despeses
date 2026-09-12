import json
import os

_CURR_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_CURR_DIR, "config.json")

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
    "idioma": "ca"
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

def load_app_config():
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
            return merged
    except Exception as e:
        print("Error reading config file:", e)
        return copy.deepcopy(DEFAULT_CONFIG)

def save_app_config(cfg_data):
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

# Àlies per compatibilitat
load_config = load_app_config
save_config = save_app_config
