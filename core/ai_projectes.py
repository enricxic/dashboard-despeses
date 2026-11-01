"""
core/ai_projectes.py
Assistent d'Intel·ligència Artificial especialitzat en Projectes d'Obra, Reformes i Manteniment de la Llar.
Proporciona:
 - Assessorament tècnic de materials, eines i normatives.
 - Tutorials d'execució pas a pas i bones pràctiques constructives.
 - Estimació de preus orientatius de mercat (Leroy Merlin, Obramat, ferreteria).
 - Generació estructurada en 1 clic de llistat de materials i fases d'obra.
"""

import json
import re
from typing import Dict, Any, List, Tuple
from core.llm import call_llm_api
import urllib.parse
from core.projectes_manager import format_date_cat

SYS_PROMPT_OBRA = """Ets un arquitecte tècnic i mestre d'obres expert en reformes de la llar, paleta, lampisteria, electricitat, fusteria, pintura i bricolatge avançat a Catalunya i Espanya.
La teva missió és assessorar el propietari d'una vivenda particular sobre un projecte concret de millora o reforma.

Coneixes en detall:
1. Els materials ideals per a cada zona (humida, exterior, interior, aïllaments tèrmics i acústics, coles tipus C2TE, impermeabilitzacions líquides o amb làmina, etc.).
2. Els tutorials i procediments correctes d'execució pas a pas (ordre constructiu lògic, temps d'assecat, precaucions de seguretat, eines manuals i electroportàtils).
3. Els preus orientatius de mercat a botigues habituals (Obramat, Leroy Merlin, Bauhaus, Brico Depôt, ferreteries de barri) i ratios mitjans de cost per m2.

Respon sempre en Català, amb un to pràctic, clar, estructurat i constructiu. Utilitza negretes per ressaltar consells crítics de seguretat o acabat."""

def consultar_assistent_obra(
    projecte: Dict[str, Any],
    pregunta: str,
    provider: str,
    model_name: str,
    api_key: str
) -> Tuple[bool, str]:
    """Genera una resposta conversacional contextualitzada al projecte actiu."""
    ctx_materials = "\n".join([f"- {m.get('article')} (Qtt: {m.get('quantitat')}, Est: {m.get('preu_estimat')}€)" for m in projecte.get("materials", [])])
    ctx_fases = "\n".join([f"- {f.get('nom')} (Estat: {f.get('estat')})" for f in projecte.get("fases", [])])

    prompt = f"""{SYS_PROMPT_OBRA}

CONTEXT DEL PROJECTE ACTUAL:
- Títol: {projecte.get('nom', 'Projecte de reforma')}
- Ubicació: {projecte.get('ubicacio', 'Llar')}
- Descripció: {projecte.get('descripcio', 'Reforma general')}
- Pressupost estimat: {projecte.get('pressupost_estimat', 0)} €
- Estat: {projecte.get('estat', 'Planificació')}

Materials actualment definits:
{ctx_materials if ctx_materials else "(Cap material afegit encara)"}

Fases d'execució previstes:
{ctx_fases if ctx_fases else "(Cap fase afegida encara)"}

CONSULTA DE L'USUARI:
{pregunta}

Respon de manera professional i concisa, aportant valor pràctic immediat."""

    ok, resp, _ = call_llm_api(prompt, api_key, model_name=model_name, provider=provider, json_mode=False)
    return ok, resp

def generar_recomanacions_materials(
    projecte: Dict[str, Any],
    provider: str,
    model_name: str,
    api_key: str
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Demana a la IA que generi una proposta de llista de materials necessaris per al projecte."""
    prompt = f"""{SYS_PROMPT_OBRA}

Per al següent projecte d'obra:
- Nom: {projecte.get('nom')}
- Ubicació: {projecte.get('ubicacio')}
- Descripció: {projecte.get('descripcio')}

Genera la llista de materials i queviures necessaris recomanats amb preus estimats de mercat a Catalunya/Espanya (Obramat / Leroy Merlin).
Has de respondre OBLIGATÒRIAMENT en format JSON pur que sigui una llista d'objectes amb aquesta estructura exacta:
[
  {{
    "article": "Nom del material o eina d'un sol ús",
    "quantitat": 1,
    "proveidor": "Obramat / Leroy Merlin / Ferreteria",
    "preu_estimat": 25.50
  }}
]
Retorna ÚNICAMENT el JSON sense text abans ni després."""

    ok, resp, _ = call_llm_api(prompt, api_key, model_name=model_name, provider=provider, json_mode=True)
    if not ok:
        return False, [], resp

    try:
        # Neteja blocs markdown ```json si n'hi ha
        clean_json = re.sub(r"^```(?:json)?\s*", "", resp.strip(), flags=re.MULTILINE)
        clean_json = re.sub(r"```\s*$", "", clean_json, flags=re.MULTILINE)
        items = json.loads(clean_json)
        if isinstance(items, list):
            for itm in items:
                art = itm.get("article", "")
                if art and not itm.get("imatge"):
                    itm["imatge"] = generar_imatge_material_url(art)
            return True, items, "Materials generats correctament."
    except Exception as e:
        return False, [], f"Error parsejant JSON de materials: {e}"

    return False, [], "El format de resposta no és una llista vàlida."

def generar_recomanacions_fases(
    projecte: Dict[str, Any],
    provider: str,
    model_name: str,
    api_key: str
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Demana a la IA que generi les etapes i subtasques d'execució lògiques d'un projecte."""
    prompt = f"""{SYS_PROMPT_OBRA}

Per al següent projecte d'obra:
- Nom: {projecte.get('nom')}
- Ubicació: {projecte.get('ubicacio')}
- Descripció: {projecte.get('descripcio')}

Planifica les fases seqüencials d'execució i les subtasques de cadascuna (ordre lògic d'obra: preparació, enderroc, instal·lacions, superfícies, muntatge, acabats).
Has de respondre OBLIGATÒRIAMENT en format JSON pur que sigui una llista d'objectes amb aquesta estructura exacta:
[
  {{
    "nom": "1. Preparació i protecció",
    "tasques": [
      "Protegir terres de pas amb cartró ondulat",
      "Tallar clau de pas d'aigua/llum si cal"
    ]
  }}
]
Retorna ÚNICAMENT el JSON sense text abans ni després."""

    ok, resp, _ = call_llm_api(prompt, api_key, model_name=model_name, provider=provider, json_mode=True)
    if not ok:
        return False, [], resp

    try:
        clean_json = re.sub(r"^```(?:json)?\s*", "", resp.strip(), flags=re.MULTILINE)
        clean_json = re.sub(r"```\s*$", "", clean_json, flags=re.MULTILINE)
        fases_raw = json.loads(clean_json)
        if isinstance(fases_raw, list):
            fases_norm = []
            for item in fases_raw:
                fases_norm.append({
                    "nom": item.get("nom", "Fase d'obra"),
                    "estat": "Pendent",
                    "tasques": [{"titol": t, "feta": False} for t in item.get("tasques", [])]
                })
            return True, fases_norm, "Fases generades correctament."
    except Exception as e:
        return False, [], f"Error parsejant JSON de fases: {e}"

    return False, [], "El format de resposta no és una llista vàlida."

def generar_imatge_material_url(nom_material: str) -> str:
    """Retorna una URL directa per generar la imatge del material amb IA."""
    clean_name = nom_material.strip()
    prompt = f"Product photo of {clean_name}, construction DIY material, isolated clean neutral background, 4k"
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=400&height=400&nologo=true"
