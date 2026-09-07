import json
import os

CONFIG_FILE = "core/config.json"

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
        {"id": 1, "nom": "Enric", "rol": "Pare", "edat": "45", "circunstancies": "Cap al·lèrgia", "icona": "👨", "google_calendar_ical": "", "color": "#3b82f6"},
        {"id": 2, "nom": "Adult 2", "rol": "Mare", "edat": "42", "circunstancies": "Vegetariana", "icona": "👩", "google_calendar_ical": "", "color": "#ec4899"}
    ],
    "tutelats": [],
    "tema": "Fosc",
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
        "tutelats_title": "Persones Tutelades",
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
        "tema_title": "Apparence et Thème",
        "icones_title": "Icônes d'accueil",
        "idioma_title": "Langues",
        "back_home": "Retour à l'accueil",
        "slogan": "TOUTE VOTRE MAISON, CONTRÔLÉE"
    }
}

def load_app_config():
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        save_app_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            for k, v in cfg.items():
                if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            return merged
    except Exception as e:
        print("Error reading config file:", e)
        return DEFAULT_CONFIG

def save_app_config(cfg_data):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print("Error saving config file:", e)
        return False

def get_translation(key, lang="ca"):
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["ca"])
    return lang_dict.get(key, key)
