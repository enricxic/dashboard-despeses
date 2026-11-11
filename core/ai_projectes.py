"""
core/ai_projectes.py
Assistent d'Intel·ligència Artificial especialitzat en Projectes d'Obra, Reformes i Manteniment de la Llar.
Proporciona:
 - Assessorament tècnic de materials, eines i normatives.
 - Tutorials d'execució pas a pas i bones pràiques constructives.
 - Estimació de preus orientatius de mercat (Leroy Merlin, Obramat, ferreteria).
 - Generació estructurada en 1 clic de llistat de materials i fases d'obra.
 - Generació d'imatges de materials amb traducció visual tècnica a l'anglès + Gemini Image / Pollinations Flux.
"""

import base64
import hashlib
import json
import random
import re
import unicodedata
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

import requests
from core.llm import call_llm_api
from core.projectes_manager import compress_image_b64, format_date_cat

SYS_PROMPT_OBRA = """Ets un arquitecte tècnic i mestre d'obres expert en reformes de la llar, paleta, lampisteria, electricitat, fusteria, pintura i bricolatge avançat a Catalunya i Espanya.
La teva missió és assessorar el propietari d'una vivenda particular sobre un projecte concret de millora o reforma.

Coneixes en detall:
1. Els materials ideals per a cada zona (humida, exterior, interior, aïllaments tèrmics i acústics, coles tipus C2TE, impermeabilitzacions líquides o amb làmina, etc.).
2. Els tutorials i procediments correctes d'execució pas a pas (ordre constructiu lògic, temps d'assecat, precaucions de seguretat, eines manuals i electroportàtils).
3. Els preus orientatius de mercat a botigues habituals (Obramat, Leroy Merlin, Bauhaus, Brico Depôt, ferreteries de barri) i ratios mitjans de cost per m2.

Respon sempre en Català, amb un to pràctic, clar, estructurat i constructiu. Utilitza negretes per ressaltar consells crítics de seguretat o acabat."""

_HARDWARE_VISUAL_DICT: List[Tuple[Tuple[str, ...], str]] = [
    (("canaleta", "canal blanc", "canal pvc", "canal electric", "canal de pvc"),
     "white rectangular PVC electrical cable trunking duct raceway with snap-on cover lid for wall wiring"),
    (("contactor",),
     "modular DIN rail electrical contactor relay switch with screw terminals and blue indicator"),
    (("magnetotermic", "pia", "interruptor automatic"),
     "DIN rail miniature circuit breaker MCB electrical protection switch"),
    (("diferencial", "rcd"),
     "DIN rail residual current circuit breaker RCD electrical switch with test button"),
    (("corrugat", "tub corrugat"),
     "coiled flexible plastic corrugated electrical conduit pipe"),
    (("caixa registre", "caixa empotrar", "caixa derivacio", "caja registro"),
     "rectangular plastic electrical wall junction box enclosure with lid"),
    (("endoll", "presa corrent", "enchufe"),
     "modern white flush-mounted wall electrical power socket outlet"),
    (("interruptor", "commutador"),
     "modern white single rocker wall light switch frame"),
    (("regleta", "clema", "born"),
     "electrical screw terminal block connector strip"),
    (("cable", "fil electric", "manguera"),
     "coil roll of insulated copper electrical power wire cable"),
    (("silicona", "segellador", "massilla", "masilla"),
     "cartridge tube of waterproof construction silicone sealant with white nozzle"),
    (("ciment", "morter", "cemento", "cola rajola"),
     "paper sack bag of construction mortar tile adhesive powder"),
    (("rajola", "taulell", "azulejo", "gres"),
     "single square ceramic porcelain wall and floor tile"),
    (("aixeta", "grifo"),
     "modern brushed chrome bathroom or kitchen sink water faucet tap"),
    (("sifo", "desguac", "desague"),
     "white PVC plumbing sink U-bend drain siphon pipe fitting"),
    (("tub pvc", "canonada", "colze", "manguito"),
     "grey rigid PVC plumbing pipe and elbow fitting"),
    (("cargol", "tornillo", "tac"),
     "metal wood screws and plastic wall anchor plugs set"),
    (("pintura", "esmalt", "imprimacio"),
     "sealed plastic paint bucket can for interior wall painting"),
    (("rodell", "rodillo", "brotxa", "pinzell"),
     "paint roller handle with microfiber cover and angled paintbrush"),
    (("cinta",),
     "roll of beige crepe painter masking adhesive tape"),
    (("tauler", "melamina", "fusta", "contrachapat", "dm", "mdf"),
     "flat rectangular cut melamine wood furniture panel board"),
    (("frontissa", "bisagra"),
     "stainless steel concealed cabinet door cup hinge hardware"),
    (("led", "focus", "downlight", "bombeta"),
     "round white recessed LED ceiling spotlight downlight fixture"),
]


def _normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _match_hardware_visual_dict(nom_material: str, extra_desc: str = "") -> str:
    norm = _normalize_text(f"{nom_material} {extra_desc}")
    for keywords, en_desc in _HARDWARE_VISUAL_DICT:
        if any(kw in norm for kw in keywords):
            return en_desc
    return ""


def _get_default_llm_credentials() -> Tuple[str, str, str]:
    try:
        import streamlit as st
        gem_key = st.secrets.get("GEMINI_API_KEY", "")
        if gem_key:
            return "gemini", "gemini-2.5-flash", gem_key
        or_key = st.secrets.get("OPENROUTER_API_KEY", "")
        if or_key:
            return "openrouter", "deepseek/deepseek-chat", or_key
    except Exception:
        pass
    return "", "", ""


def _build_english_product_prompt(
    nom_material: str,
    extra_desc: str = "",
    context_projecte: str = "",
    provider: str = "",
    model_name: str = "",
    api_key: str = "",
) -> str:
    clean_name = nom_material.strip()
    dict_hit = _match_hardware_visual_dict(clean_name, extra_desc)

    if not api_key:
        provider, model_name, api_key = _get_default_llm_credentials()

    visual_core = ""
    if api_key and provider and not extra_desc:
        try:
            ctx_txt = f" Project context: {context_projecte}." if context_projecte else ""
            hint_txt = f" Technical match: {dict_hit}." if dict_hit else ""
            tr_prompt = (
                "You are writing an image-generation prompt for a DIY hardware store catalog.\n"
                f"Material name (Catalan/Spanish): '{clean_name}'.{ctx_txt}{hint_txt}\n"
                "Describe concisely in English (12-22 words) the exact physical construction/electrical/plumbing "
                "object so an image model never mistakes it for a vase, food, or scenery.\n"
                "Return ONLY the English object description, no quotes, no preamble."
            )
            ok, resp, _ = call_llm_api(tr_prompt, api_key, model_name=model_name, provider=provider, json_mode=False)
            if ok and resp and len(resp.strip()) > 6:
                visual_core = resp.strip().strip('"\'').replace("\n", " ")
        except Exception:
            pass

    if not visual_core:
        if dict_hit:
            detail = f" ({extra_desc.strip()})" if extra_desc.strip() else ""
            visual_core = f"{dict_hit}{detail}"
        else:
            detail = f", {extra_desc.strip()}" if extra_desc.strip() else ""
            visual_core = f"{clean_name}{detail}, hardware store DIY building electrical or plumbing material"

    return (
        f"Studio product photography of {visual_core}, single item centered, "
        "isolated on clean solid pure white background, sharp focus, realistic hardware catalog photo, "
        "no text, no watermark, no logos"
    )


def _try_gemini_image_generation(prompt: str, api_key: str) -> Optional[bytes]:
    """Prova la generació nativa d'imatges de Google Gemini (sense marques d'aigua)."""
    if not api_key:
        return None

    # 1. Gemini multimodal image output (gemini-2.5-flash-image / gemini-2.0-flash-exp-image-generation)
    for model_id in ("gemini-2.5-flash-image", "gemini-2.0-flash-exp-image-generation"):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["IMAGE"]},
            }
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        inline = part.get("inlineData") or part.get("inline_data")
                        if inline and inline.get("data"):
                            return base64.b64decode(inline["data"])
        except Exception:
            pass

    # 2. Imagen 3 predict endpoint
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "1:1"},
        }
        resp = requests.post(url, json=payload, timeout=25)
        if resp.status_code == 200:
            preds = resp.json().get("predictions", [])
            if preds and preds[0].get("bytesBase64Encoded"):
                return base64.b64decode(preds[0]["bytesBase64Encoded"])
    except Exception:
        pass

    return None


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
    "article": "Nom del material o eina",
    "quantitat": 1,
    "proveidor": "Obramat / Leroy Merlin / Ferreteria",
    "preu_estimat": 25.50,
    "imatge_prompt_en": "Clear 15-word visual product photo description in English on white background (e.g. white rectangular PVC electrical cable trunking duct with snap lid)"
  }}
]
Retorna ÚNICAMENT el JSON sense text abans ni després."""

    ok, resp, _ = call_llm_api(prompt, api_key, model_name=model_name, provider=provider, json_mode=True)
    if not ok:
        return False, [], resp

    try:
        clean_json = re.sub(r"^```(?:json)?\s*", "", resp.strip(), flags=re.MULTILINE)
        clean_json = re.sub(r"```\s*$", "", clean_json, flags=re.MULTILINE)
        items = json.loads(clean_json)
        if isinstance(items, list):
            ctx_proj = f"{projecte.get('nom', '')} - {projecte.get('descripcio', '')}".strip(" -")
            for itm in items:
                art = itm.get("article", "")
                if art and not itm.get("imatge"):
                    itm["imatge"] = generar_imatge_material_url(
                        art,
                        prompt_visual_en=itm.get("imatge_prompt_en", ""),
                        context_projecte=ctx_proj,
                        provider=provider,
                        model_name=model_name,
                        api_key=api_key,
                    )
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


def generar_imatge_material_url(
    nom_material: str,
    prompt_visual_en: str = "",
    extra_desc: str = "",
    context_projecte: str = "",
    provider: str = "",
    model_name: str = "",
    api_key: str = "",
    force_refresh: bool = False,
) -> str:
    """
    Genera una imatge realista del material:
    1) Tradueix/descriu tècnicament en anglès (evitant ambigüitats com 'canal' -> gerro).
    2) Prova primer Google Gemini Image Generation (sense marca d'aigua) desant JPEG base64 comprimit.
    3) Fallback a Pollinations model 'flux' amb prompt tècnic enriquit i seed controlat.
    """
    if prompt_visual_en.strip():
        final_prompt = (
            f"Studio product photography of {prompt_visual_en.strip()}, "
            "isolated on clean solid white background, realistic hardware store catalog photo, "
            "no text, no watermark, no logos"
        )
    else:
        final_prompt = _build_english_product_prompt(
            nom_material=nom_material,
            extra_desc=extra_desc,
            context_projecte=context_projecte,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
        )

    gem_key = api_key if (provider == "gemini" and api_key) else ""
    if not gem_key:
        try:
            import streamlit as st
            gem_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass

    gem_bytes = _try_gemini_image_generation(final_prompt, gem_key)
    if gem_bytes:
        comp = compress_image_b64(gem_bytes, max_dim=480, quality=82)
        if comp:
            return comp

    seed = random.randint(1, 999999) if force_refresh else int(
        hashlib.md5(nom_material.strip().lower().encode("utf-8")).hexdigest()[:6], 16
    )
    encoded = urllib.parse.quote(final_prompt)
    flux_url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?model=flux&width=512&height=512&nologo=true&enhance=true&seed={seed}"
    )

    try:
        resp = requests.get(flux_url, timeout=18)
        ctype = resp.headers.get("Content-Type", "").lower()
        if resp.status_code == 200 and ctype.startswith("image/") and len(resp.content) > 1000:
            comp = compress_image_b64(resp.content, max_dim=480, quality=82)
            if comp:
                return comp
    except Exception:
        pass

    return flux_url
