import json
import os
import time
import re
import requests
from typing import Dict, List, Any, Optional, Tuple, Callable

# Fitxer per defecte del dataset de proves
DEFAULT_CASES_PATH = "data/harness_menu_cases.json"

def load_harness_cases(file_path: str = DEFAULT_CASES_PATH) -> List[Dict[str, Any]]:
    """Carrega la col·lecció de casos de prova del banc de dades JSON."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("test_cases", [])
    except Exception as e:
        print(f"Error carregant casos de prova: {e}")
        return []

def build_system_prompt_for_case(test_case: Dict[str, Any], recipes_sample: Optional[List[str]] = None) -> str:
    """Construeix el prompt del sistema optimitzat per generar un menú estricte en format JSON."""
    
    perfil_txt = ""
    for m in test_case.get("perfil_familia", []):
        actiu_str = "Present a la llar" if m.get("actiu", True) else "FORA DE LA LLAR (NO COMPUTA COMENSAL)"
        alergies_str = ", ".join(m.get("alergies", [])) if m.get("alergies") else "Cap"
        vetos_str = ", ".join(m.get("vetos", [])) if m.get("vetos") else "Cap"
        comodins_str = ", ".join(m.get("comodins", [])) if m.get("comodins") else "Cap"
        perfil_txt += f"- {m.get('nom')} ({m.get('rol')}, {m.get('edat')} anys) [{actiu_str}]: Al·lèrgies mèdiques: {alergies_str} | Vetos personals: {vetos_str} | Plats comodí: {comodins_str}\n"

    regles = test_case.get("regles_llar", {})
    regles_txt = f"""- Màxim carn vermella: {regles.get('max_carn_vermella', 1)} cop per setmana.
- Mínim peix: {regles.get('min_peix', 2)} cops per setmana.
- Mínim llegums: {regles.get('min_llegums', 2)} cops per setmana.
- Màxim sopars d'embotits/freds: {regles.get('max_embotits_sopar', 2)} cops per setmana.
- No repetir hidrats de carboni (arròs, pasta, patata com a base) en dies consecutius."""

    stock_list = test_case.get("stock_disponible", [])
    stock_txt = "Cap"
    if stock_list:
        stock_txt = "\n".join([f"- {s.get('producte')} ({s.get('quantitat')}) a {s.get('ubicacio')}" for s in stock_list])

    peticions_list = test_case.get("peticions_setmanals", [])
    peticions_txt = "Cap"
    if peticions_list:
        peticions_txt = "\n".join([f"- {p.get('comensal')}: '{p.get('plat')}' (Preferència: {p.get('dia_preferit', 'Qualsevol')}) [Consens Aprovat]" for p in peticions_list])

    valoracions = test_case.get("valoracions_previes", {})
    val_txt = "Cap"
    if valoracions:
        val_txt = json.dumps(valoracions, ensure_ascii=False, indent=2)

    prompt = f"""Ets el planificador nutricional intel·ligent de XiquiHouse.
La teva missió és dissenyar un menú setmanal equilibrat, deliciós, segur i optimitzat per a la família seguint estrictament aquestes dades:

### PERFIL FAMILIAR:
{perfil_txt}

### REGLES NUTRICIONALS DE LA LLAR:
{regles_txt}

### STOCK EXISTENT AL CONGELADOR / REBOST (UTILITZA'L PER NO COMPRAR NI LLENÇAR):
{stock_txt}

### PETICIONS APROVADES DE LA FAMÍLIA:
{peticions_txt}

### HISTÒRIC DE PUNTUACIONS (ESTRELLES 0-5):
{val_txt}
NOTA SOBRE PUNTUACIONS: Prioritza plats amb 4-5 estrelles. MAI programis plats que tinguin 0, 1 o 2 estrelles.

### REGLES CRÍTIQUES DE DESDOBLAMENT I VETOS:
1. Si la família menja un plat que conté un aliment vetat per un sol membre (ex. fetge), programa el plat per a la família i genera OBLIGATÒRIAMENT un 'plat_alternatiu' ràpid (usant els seus comodins favorits) per a aquell membre, compartint la mateixa guarnició.
2. Si un membre està 'FORA DE LA LLAR', NO comptabilitzis les seves restriccions personals per defecte ni el sumis al nombre de racions.

### RESPOSTA EN FORMAT JSON ESTRICTE:
Has de respondre ÚNICAMENT amb un objecte JSON sense blocs markdown extres, amb aquesta estructura:
{{
  "dies_planificats": 7,
  "comensals_actius": 3,
  "menu_setmanal": [
    {{
      "dia": "Dilluns",
      "dinar": {{
        "plat": "Nom del plat principal",
        "categoria": "Primer / Segon / Plat únic",
        "ingredients_principals": ["ing1", "ing2"],
        "apte_per": ["Nom1", "Nom2"],
        "plat_alternatiu": null
      }},
      "sopar": {{
        "plat": "Nom del plat",
        "categoria": "Segon / Plat únic",
        "ingredients_principals": ["ing1", "ing2"],
        "apte_per": ["Nom1", "Nom2"],
        "plat_alternatiu": {{
          "per": "Enric",
          "plat": "Pit de pollastre a la planxa",
          "motiu": "Veto a fetge"
        }}
      }}
    }}
  ],
  "bases_batch_prep_diumenge": [
    {{"base": "Patates probiòtiques", "quantitat": "1.5 kg", "utilitzacio": "Dinars de dimarts i dijous"}},
    {{"base": "Caldo de peix concentrat", "quantitat": "1.5 L", "utilitzacio": "Arròs de dimarts i sopa de dijous"}}
  ],
  "ingredients_a_comprar": ["llista d'ingredients que NO estan a l'stock"]
}}"""
    return prompt

def call_gemini_api(prompt: str, api_key: str, model_name: str = "gemini-2.5-flash") -> Tuple[bool, str, float]:
    """Realitza una crida a l'API de Google Gemini i retorna (èxit, text_resposta, temps_segons)."""
    start_time = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=45)
        elapsed = round(time.time() - start_time, 2)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return True, content, elapsed
            return False, "Resposta buida de Gemini", elapsed
        else:
            return False, f"Error HTTP {resp.status_code}: {resp.text}", elapsed
    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return False, f"Excepció en cridar Gemini: {str(e)}", elapsed

def parse_and_clean_json(raw_text: str) -> Tuple[bool, Dict[str, Any], str]:
    """Neteja delimitadors markdown i parseja el text com a diccionari JSON."""
    if not raw_text:
        return False, {}, "Text buit"
    try:
        clean = raw_text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        
        parsed = json.loads(clean)
        if isinstance(parsed, dict) and "menu_setmanal" in parsed:
            return True, parsed, ""
        return False, parsed if isinstance(parsed, dict) else {}, "JSON vàlid però no conté 'menu_setmanal'"
    except Exception as e:
        return False, {}, f"Error parsejant JSON: {str(e)}"

# =========================================================================
# GRADERS DETERMINISTES (AVALUADORS LÒGICS)
# =========================================================================

def netejar_termes_segurs(text: str) -> str:
    """Substitueix combinacions segures com 'sense gluten', 'blat de moro' o 'llet de coco' per evitar falsos positius."""
    t = text.lower()
    safe_terms = [
        "sense gluten", "sin gluten", "gluten-free", "gluten free", "farina sense gluten", "pa sense gluten", "pasta sense gluten", "macarrons sense gluten", "fideus sense gluten", "salsa de soja sense gluten", "tamari",
        "sense lactosa", "sin lactosa", "lactose-free", "llet sense lactosa", "formatge sense lactosa", "iogurt sense lactosa",
        "blat de moro", "farina de blat de moro", "tortitas de blat de moro", "pa de blat de moro",
        "llet de coco", "llet d'ametlla", "llet d'ametlles", "llet de civada", "llet de soja", "llet d'arròs", "llet d'arros", "llet vegetal",
        "iogurt vegetal", "iogurt de soja", "iogurt de coco", "iogurt d'ametlla",
        "formatge vegà", "formatge vega", "formatge vegetal",
        "nata vegetal", "nata de coco", "mantega vegetal", "margarina vegetal"
    ]
    for st in safe_terms:
        t = t.replace(st, "[TERME_SEGUR]")
    return t

def grade_alergies(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova que CAP ingredient contingui al·lèrgens prohibits (Tolerància 0%)."""
    criteris = test_case.get("criteris_esperats", {})
    alergens = [a.lower() for a in criteris.get("alergens_prohibits", [])]
    
    # Recollir també al·lèrgies dels membres actius
    for m in test_case.get("perfil_familia", []):
        if m.get("actiu", True):
            for al in m.get("alergies", []):
                al_low = al.lower()
                if "gluten" in al_low or "celiac" in al_low:
                    alergens.extend(["gluten", "blat", "farina de blat", "pa de blat", "pasta de blat", "fideus de blat", "espelta", "ordi", "centen"])
                if "lactosa" in al_low:
                    alergens.extend(["llet", "formatge", "nata", "mantega", "iogurt", "crema de llet", "parmesà", "mozzarella"])
                if "fruits secs" in al_low:
                    alergens.extend(["ametlla", "nou", "avellana", "cacauet", "pistatxo", "anacard"])
    
    alergens = list(set(alergens))
    if not alergens:
        return 1.0, []
    
    infraccions = []
    for dia_obj in menu_data.get("menu_setmanal", []):
        dia_nom = dia_obj.get("dia", "Dia desconegut")
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            
            plat = apat.get("plat", "")
            ingredients = apat.get("ingredients_principals", [])
            
            # Comprovar nom del plat netejat de termes segurs
            plat_net = netejar_termes_segurs(plat)
            for a in alergens:
                pattern = r'\b' + re.escape(a) + r'\b'
                if re.search(pattern, plat_net):
                    infraccions.append(f"{dia_nom} ({apat_k}): '{plat}' conté el terme prohibit '{a}'")
            
            # Comprovar ingredients netejats de termes segurs
            for ing in ingredients:
                ing_net = netejar_termes_segurs(str(ing))
                for a in alergens:
                    pattern = r'\b' + re.escape(a) + r'\b'
                    if re.search(pattern, ing_net):
                        infraccions.append(f"{dia_nom} ({apat_k}): ingredient '{ing}' conté '{a}'")

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

def grade_vetos_i_desdoblament(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova si es gestionen els vetos personals assignant un plat alternatiu ràpid."""
    infraccions = []
    
    # Buscar membres actius amb vetos
    membres_veto = [m for m in test_case.get("perfil_familia", []) if m.get("actiu", True) and m.get("vetos")]
    if not membres_veto:
        return 1.0, []
    
    for m in membres_veto:
        nom_m = m.get("nom")
        vetos = [v.lower() for v in m.get("vetos", [])]
        
        for dia_obj in menu_data.get("menu_setmanal", []):
            dia_nom = dia_obj.get("dia", "")
            for apat_k in ["dinar", "sopar"]:
                apat = dia_obj.get(apat_k, {})
                if not isinstance(apat, dict): continue
                
                plat = apat.get("plat", "").lower()
                ingredients = [str(i).lower() for i in apat.get("ingredients_principals", [])]
                alt = apat.get("plat_alternatiu")
                
                # Cerca amb paraula exacta
                conte_veto = any(re.search(r'\b' + re.escape(v) + r'\b', plat) for v in vetos) or \
                             any(any(re.search(r'\b' + re.escape(v) + r'\b', ing) for v in vetos) for ing in ingredients)
                
                if conte_veto:
                    if alt is None or not isinstance(alt, dict) or not alt.get("plat"):
                        infraccions.append(f"{dia_nom} ({apat_k}): '{apat.get('plat')}' té ingredients vetats per a {nom_m} però NO s'ha generat cap 'plat_alternatiu'")
                    else:
                        alt_plat = alt.get("plat", "").lower()
                        if any(re.search(r'\b' + re.escape(v) + r'\b', alt_plat) for v in vetos):
                            infraccions.append(f"{dia_nom} ({apat_k}): El plat alternatiu '{alt.get('plat')}' per a {nom_m} conté el veto")

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

def grade_regles_llar(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova freqüències setmanals de carn vermella, peix, llegums i embotits."""
    regles = test_case.get("regles_llar", {})
    max_carn = regles.get("max_carn_vermella", 1)
    min_peix = regles.get("min_peix", 2)
    min_llegums = regles.get("min_llegums", 2)
    max_embotits = regles.get("max_embotits_sopar", 2)
    
    carn_vermella_kw = ["vedella", "bou", "bistec", "hamburguesa de vedella", "fricando", "entrecot", "porc"]
    peix_kw = ["peix", "salmo", "salmó", "lluç", "lluc", "bacalla", "bacallà", "sardina", "sardines", "tonyina", "dorada", "orada", "llobarro", "rap", "calamar", "sepia", "sèpia", "marisc"]
    llegum_kw = ["llenties", "cigrons", "mongetes", "fesols", "pesols", "pèsols", "soja", "faves"]
    embotit_kw = ["pernil", "embotit", "xarcuteria", "formatge i embotit", "fuet", "llonganissa", "xoriço", "salsitxes"]
    
    count_carn = 0
    count_peix = 0
    count_llegums = 0
    count_embotits_sopar = 0
    
    for dia_obj in menu_data.get("menu_setmanal", []):
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            
            plat = apat.get("plat", "").lower()
            ings = " ".join([str(i).lower() for i in apat.get("ingredients_principals", [])])
            full_text = f"{plat} {ings}"
            
            if any(k in full_text for k in carn_vermella_kw):
                count_carn += 1
            if any(k in full_text for k in peix_kw):
                count_peix += 1
            if any(k in full_text for k in llegum_kw):
                count_llegums += 1
            if apat_k == "sopar" and any(k in full_text for k in embotit_kw):
                count_embotits_sopar += 1

    infraccions = []
    if count_carn > max_carn:
        infraccions.append(f"Excés de carn vermella: {count_carn} cops (màxim permès: {max_carn})")
    if count_peix < min_peix:
        infraccions.append(f"Falta de peix: {count_peix} cops (mínim requerit: {min_peix})")
    if count_llegums < min_llegums:
        infraccions.append(f"Falta de llegums: {count_llegums} cops (mínim requerit: {min_llegums})")
    if count_embotits_sopar > max_embotits:
        infraccions.append(f"Excés d'embotits per sopar: {count_embotits_sopar} cops (màxim permès: {max_embotits})")

    # Puntuació proporcional
    total_regles = 4
    complertes = total_regles - len(infraccions)
    score = max(0.0, complertes / total_regles)
    return score, infraccions

def grade_repeticions_hidrats(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova que no hi hagi dies consecutius amb arròs o pasta."""
    infraccions = []
    darrers_hidrats = []
    
    for dia_obj in menu_data.get("menu_setmanal", []):
        dia_nom = dia_obj.get("dia", "")
        hidrats_avui = []
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            plat = apat.get("plat", "").lower()
            
            if "arròs" in plat or "arros" in plat or "paella" in plat:
                hidrats_avui.append("arròs")
            if "pasta" in plat or "macarrons" in plat or "fideus" in plat or "espaguetis" in plat:
                hidrats_avui.append("pasta")
                
        if darrers_hidrats:
            for h in hidrats_avui:
                if h in darrers_hidrats:
                    infraccions.append(f"{dia_nom}: Repetició consecutiva d'hidrat '{h}' dos dies seguits")
        darrers_hidrats = hidrats_avui

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

def grade_puntuacions_estrelles(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova que no s'incloguin plats vetats per puntuació baixa (0-2 estrelles)."""
    valoracions = test_case.get("valoracions_previes", {})
    if not valoracions:
        return 1.0, []
        
    infraccions = []
    for dia_obj in menu_data.get("menu_setmanal", []):
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            plat = apat.get("plat", "")
            
            # Comprovar si aquest plat té puntuació baixa
            for plat_val, notes in valoracions.items():
                if plat_val.lower() in plat.lower() or plat.lower() in plat_val.lower():
                    # Si alguna nota és <= 2
                    for user, score in notes.items():
                        if score <= 2:
                            infraccions.append(f"Plat desaconsellat inclòs: '{plat}' (puntuat amb {score} estrelles per {user})")

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

# =========================================================================
# EXECUTOR PRINCIPAL DEL HARNESS
# =========================================================================

def run_harness_single_test(test_case: Dict[str, Any], api_key: str, model_name: str = "gemini-2.5-flash") -> Dict[str, Any]:
    """Executa un cas de prova complet i retorna el resultat i la targeta de puntuació."""
    prompt = build_system_prompt_for_case(test_case)
    ok_call, raw_resp, latency = call_gemini_api(prompt, api_key=api_key, model_name=model_name)
    
    if not ok_call:
        return {
            "id": test_case.get("id"),
            "titol": test_case.get("titol"),
            "exit_global": False,
            "json_valid": False,
            "puntuacio_seguretat": 0.0,
            "puntuacio_vetos": 0.0,
            "puntuacio_regles": 0.0,
            "puntuacio_varietat": 0.0,
            "puntuacio_estrelles": 0.0,
            "latencia_s": latency,
            "errors": [raw_resp],
            "resposta_json": {}
        }
        
    json_ok, json_data, json_err = parse_and_clean_json(raw_resp)
    if not json_ok:
        return {
            "id": test_case.get("id"),
            "titol": test_case.get("titol"),
            "exit_global": False,
            "json_valid": False,
            "puntuacio_seguretat": 0.0,
            "puntuacio_vetos": 0.0,
            "puntuacio_regles": 0.0,
            "puntuacio_varietat": 0.0,
            "puntuacio_estrelles": 0.0,
            "latencia_s": latency,
            "errors": [f"Error estructural: {json_err}"],
            "resposta_json": {}
        }
        
    # Execució dels Graders
    score_alergies, err_alergies = grade_alergies(json_data, test_case)
    score_vetos, err_vetos = grade_vetos_i_desdoblament(json_data, test_case)
    score_regles, err_regles = grade_regles_llar(json_data, test_case)
    score_varietat, err_varietat = grade_repeticions_hidrats(json_data, test_case)
    score_estrelles, err_estrelles = grade_puntuacions_estrelles(json_data, test_case)
    
    all_errors = err_alergies + err_vetos + err_regles + err_varietat + err_estrelles
    exit_global = (score_alergies == 1.0 and score_vetos == 1.0 and score_regles >= 0.75 and score_varietat == 1.0 and score_estrelles == 1.0)
    
    return {
        "id": test_case.get("id"),
        "titol": test_case.get("titol"),
        "exit_global": exit_global,
        "json_valid": True,
        "puntuacio_seguretat": score_alergies,
        "puntuacio_vetos": score_vetos,
        "puntuacio_regles": score_regles,
        "puntuacio_varietat": score_varietat,
        "puntuacio_estrelles": score_estrelles,
        "latencia_s": latency,
        "errors": all_errors,
        "resposta_json": json_data
    }

def run_harness_suite(api_key: str, model_name: str = "gemini-2.5-flash", progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
    """Executa la bateria completa de proves i retorna un resum global de rendiment."""
    cases = load_harness_cases()
    if not cases:
        return {"error": "No s'han trobat casos de prova a 'data/harness_menu_cases.json'"}
        
    total_cases = len(cases)
    results = []
    
    for idx, tc in enumerate(cases):
        if progress_callback:
            progress_callback(idx + 1, total_cases, tc.get("titol", f"Test {idx+1}"))
            
        res = run_harness_single_test(tc, api_key=api_key, model_name=model_name)
        results.append(res)
        
    passed_total = sum(1 for r in results if r["exit_global"])
    passed_json = sum(1 for r in results if r["json_valid"])
    passed_seguretat = sum(1 for r in results if r["puntuacio_seguretat"] == 1.0)
    passed_vetos = sum(1 for r in results if r["puntuacio_vetos"] == 1.0)
    avg_latency = round(sum(r["latencia_s"] for r in results) / total_cases, 2) if total_cases > 0 else 0.0
    
    return {
        "total_proves": total_cases,
        "proves_superades": passed_total,
        "percentatge_exit": round((passed_total / total_cases) * 100, 1),
        "taxa_json_valid": round((passed_json / total_cases) * 100, 1),
        "taxa_seguretat_alergies": round((passed_seguretat / total_cases) * 100, 1),
        "taxa_desdoblament_vetos": round((passed_vetos / total_cases) * 100, 1),
        "latencia_mitjana_s": avg_latency,
        "model_avaluat": model_name,
        "detall_resultats": results
    }
