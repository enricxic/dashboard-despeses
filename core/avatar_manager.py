import os
import base64
import requests
import streamlit as st

# Mapeig de rols de l'Avatar segons la secció/mòdul de l'aplicació
AVATAR_ROLES = {
    "base": {
        "key": "base",
        "title": "Xiqui AI - Assistent del S.O.",
        "subtitle": "Assistent Virtual de la Llar",
        "image_file": "avatar_base.png",
        "greeting": "Hola! Soc la Xiqui, la teva assistent virtual de XiquiHouse. Com et puc ajudar avui?",
        "system_prompt": "Es el teu nom Xiqui, una assistent virtual anime de 20 anys per al S.O. de la llar XiquiHouse. Parles en català d'una manera molt amable, clara, optimista i servicial.",
        "badge_color": "#3b82f6"
    },
    "manetes": {
        "key": "manetes",
        "title": "Xiqui Manetes - Manteniment i Domòtica",
        "subtitle": "Especialista en Manteniment de la Llar",
        "image_file": "avatar_manetes.png",
        "greeting": "Quina reparació o tasca de domòtica tenim avui? Estic a punt per ajudar-te!",
        "system_prompt": "Et dius Xiqui, assistent en rol de manetes de la llar i domòtica per a XiquiHouse. Respons dubtes sobre reparacions, eines, domòtica i tasques de la casa en català de forma pràctica, tècnica i entenedora.",
        "badge_color": "#f59e0b"
    },
    "infermera": {
        "key": "infermera",
        "title": "Xiqui Infermera - Salut i Medicació",
        "subtitle": "Gestió de Farmaciola i Pautes Mèdiques",
        "image_file": "avatar_infermera.png",
        "greeting": "Recorda revisar les dosis i pautes mèdiques de la família. Com et puc cuidar avui?",
        "system_prompt": "Et dius Xiqui, assistent en rol d'infermera i responsable de salut familiar a XiquiHouse. Parles amb molta empatia, cura i rigor sobre medicació, dosis, consells de salut i farmaciola en català. Recorda sempre consultar un metge per diagnòstics.",
        "badge_color": "#06b6d4"
    },
    "cuinera": {
        "key": "cuinera",
        "title": "Xiqui Cuinera - Menús i Receptes",
        "subtitle": "Xef Gastronòmica i Batch Cooking",
        "image_file": "avatar_cuinera.png",
        "greeting": "Tinc el receptari a punt! Què et ve de gust menjar o cuinar avui?",
        "system_prompt": "Et dius Xiqui, assistent en rol de xef i planificadora de menús gastronòmics per a XiquiHouse. Ofereixes consells culinaris, idees de receptes, tècniques de batch cooking i recomanacions nutricionals adaptades a les al·lèrgies i vetos familiars en català.",
        "badge_color": "#ef4444"
    },
    "administrativa": {
        "key": "administrativa",
        "title": "Xiqui Administrativa - Economia i Compres",
        "subtitle": "Gestió Financer i Control de Despeses",
        "image_file": "avatar_administrativa.png",
        "greeting": "Revisem els números, tiquets o la llista de la compra? Tot sota control!",
        "system_prompt": "Et dius Xiqui, assistent en rol d'administrativa financera i de compres per a XiquiHouse. Ajudes a analitzar el pressupost mensual, tiquets de supermercat, estalvis i inversions en català amb un enfocament organitzat, eficient i analític.",
        "badge_color": "#10b981"
    }
}

MODULE_TO_ROLE = {
    "economic": "administrativa",
    "compres": "administrativa",
    "admin": "administrativa",
    "menjar": "cuinera",
    "medicacio": "infermera",
    "manteniment": "manetes",
    "domotica": "manetes",
    "seguretat": "manetes",
    "calendari": "base",
    "jocs": "base",
    "cotxe": "manetes",
    "dashboard": "base"
}

AVATARS_DIR = os.path.join("imatges", "avatars")

def get_avatar_role_for_module(module_name: str = None) -> dict:
    """Retorna la configuració del rol de l'avatar segons el mòdul actiu o el rol manual seleccionat."""
    manual_role = st.session_state.get("avatar_manual_role")
    if manual_role and manual_role in AVATAR_ROLES:
        return AVATAR_ROLES[manual_role]
    
    clean_mod = str(module_name or "").replace("modules.", "").strip().lower()
    role_key = MODULE_TO_ROLE.get(clean_mod, "base")
    return AVATAR_ROLES.get(role_key, AVATAR_ROLES["base"])

@st.cache_data(ttl=3600, show_spinner=False)
def get_avatar_image_base64(image_file: str) -> str:
    """Carrega la imatge de l'avatar i la converteix en cadena base64 per a renderitzat ultra-ràpid."""
    full_path = os.path.join(AVATARS_DIR, image_file)
    if not os.path.exists(full_path):
        # Fallback a avatar_base si no troba l'arxiu
        full_path = os.path.join(AVATARS_DIR, "avatar_base.png")
    
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/png;base64,{encoded}"
    return ""

def ask_avatar_ai(prompt: str, role_info: dict) -> str:
    """Envia una pregunta a l'API de Gemini amb el perfil i rol de l'avatar anime."""
    if not prompt or not prompt.strip():
        return "Si us plau, escriu una pregunta per a la Xiqui."
        
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ Clau d'API de Gemini no configurada a `st.secrets['GEMINI_API_KEY']`."
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        system_instruction = role_info.get("system_prompt", "Es el teu nom Xiqui, assistent virtual de XiquiHouse.")
        full_prompt = f"{system_instruction}\n\nL'usuari et pregunta: \"{prompt}\"\n\nRespon de forma concisa, directa i molt amable en català."
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": full_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 600
            }
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        return f"Error en generar resposta ({resp.status_code}): {resp.text[:100]}"
    except Exception as e:
        return f"⚠️ No s'ha pogut connectar amb la Xiqui: {str(e)}"
