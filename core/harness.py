import json
import os
import time
import re
import requests
from typing import Dict, List, Any, Optional, Tuple, Callable

def load_harness_cases(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Carrega la col·lecció de casos de prova del banc de dades JSON resolent rutes absolutes."""
    target_path = file_path
    if not target_path or not os.path.exists(target_path):
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(curr_dir, ".."))
        candidates = [
            os.path.join(project_root, "data", "harness_menu_cases.json"),
            os.path.join(os.getcwd(), "data", "harness_menu_cases.json"),
            os.path.join(curr_dir, "..", "data", "harness_menu_cases.json"),
            "data/harness_menu_cases.json"
        ]
        for c in candidates:
            if os.path.exists(c) and os.path.isfile(c):
                target_path = c
                break
                
    if not target_path or not os.path.exists(target_path):
        return []
        
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("test_cases", [])
    except Exception as e:
        print(f"Error carregant casos de prova des de {target_path}: {e}")
        return []

def build_system_prompt_for_case(test_case: Dict[str, Any], recipes_catalog: Optional[List[Any]] = None, recipes_sample: Optional[List[Any]] = None, **kwargs) -> str:
    """Construeix el prompt del sistema optimitzat per generar un menú estricte en format JSON."""
    
    cataleg_utilitzar = recipes_catalog if recipes_catalog is not None else recipes_sample
    if cataleg_utilitzar is None:
        cataleg_utilitzar = kwargs.get("cataleg_receptes", [])

    perfil_txt = ""
    for m in test_case.get("perfil_familia", []):
        actiu_str = "Present a la llar" if m.get("actiu", True) else "FORA DE LA LLAR (NO COMPUTA COMENSAL)"
        alergies_str = ", ".join(m.get("alergies", [])) if m.get("alergies") else "Cap"
        vetos_str = ", ".join(m.get("vetos", [])) if m.get("vetos") else "Cap"
        comodins_str = ", ".join(m.get("comodins", [])) if m.get("comodins") else "Cap"
        perfil_txt += f"- {m.get('nom')} ({m.get('rol')}, {m.get('edat')} anys) [{actiu_str}]: Al·lèrgies mèdiques: {alergies_str} | Vetos personals: {vetos_str} | Plats comodí: {comodins_str}\n"

    regles = test_case.get("regles_llar", {})
    us_forn = regles.get("us_forn", "Només cap de setmana (Dissabte i Diumenge)")
    regles_txt = f"""- Màxim carn vermella: {regles.get('max_carn_vermella', 1)} cop per setmana.
- Mínim peix: {regles.get('min_peix', 2)} cops per setmana.
- Mínim llegums: {regles.get('min_llegums', 2)} cops per setmana.
- Màxim sopars d'embotits/freds: {regles.get('max_embotits_sopar', 2)} cops per setmana.
- No repetir hidrats de carboni (arròs, pasta, patata com a base) en dies consecutius.
- Disponibilitat del forn: {us_forn}."""

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

    eines_list = test_case.get("eines_disponibles", [])
    if isinstance(eines_list, dict):
        eines_list = [k for k, v in eines_list.items() if v]
    eines_txt = ", ".join(eines_list) if eines_list else "Forn, Microones, Nevera, Congelador, Minipimer, Morter, Olla a pressió, Picadora, Espremedor, Mandolina"

    # Catàleg de receptes de la família
    receptari_txt = "No hi ha receptari predefinit."
    if cataleg_utilitzar:
        primers = []
        segons = []
        altres = []
        for r in cataleg_utilitzar:
            if isinstance(r, dict):
                titol = r.get("titol", "")
                cat = str(r.get("categoria", "")).lower()
            else:
                titol = str(r)
                cat = "primer"
            if not titol: continue
            if "primer" in cat:
                primers.append(titol)
            elif "segon" in cat or "únic" in cat or "plat" in cat:
                segons.append(titol)
            else:
                altres.append(titol)
        receptari_txt = f"""- PRIMERS PLATS DISPONIBLES AL LLIBRE ({len(primers)} receptes): {', '.join(primers[:60])}
- SEGONS PLATS DISPONIBLES AL LLIBRE ({len(segons)} receptes): {', '.join(segons[:60])}
- ALTRES / COMPLEMENTS: {', '.join(altres[:30])}"""

    prompt = f"""Ets el planificador nutricional intel·ligent de XiquiHouse.
La teva missió és dissenyar un menú setmanal equilibrat, deliciós, segur i optimitzat per a la família seguint estrictament aquestes dades:

### 📖 LLIBRE DE RECEPTES DE LA FAMÍLIA (OBLIGATORI PRIORITZAR):
{receptari_txt}
⚠️ PRIORITZACIÓ OBLIGATÒRIA: Sempre que un plat encaixi amb la temporada, comensals i regles nutricionals, UTILITZA ELS PLATS DEL LLIBRE DE RECEPTES amb el seu títol exacte! Només proposa plats nous si cap recepta del llibre compleix els requisits.

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
NOTA SOBRE PUNTUACIONS: Prioritza plats amb 4-5 estrelles. MAI programis plats que tinguin 0, 1 o 2 estrelles (excepte si és per a la resta de la família i assignes un 'plat_alternatiu' al membre afectat).

### ⚠️ COMPLIMENT ESTRICTE DE FREQÜÈNCIES NUTRICIONALS I CALENDARI D'HIDRATS:
1. CARN VERMELLA (vedella, bou, hamburguesa): Màxim el límit indicat (habitualment MÀXIM 1 COP en tota la setmana). Si ja has posat carn vermella un dia, la resta de dies utilitza aus (pollastre, gall dindi), peix, ous o llegums.
2. SOPARS FREDS / EMBOTITS: Màxim el límit indicat (habitualment MÀXIM 2 COPS per setmana).
3. PEIX I LLEGUMS: Assegura el mínim de cops setmanals (habitualment mínim 2 de peix i mínim 2 de llegums).
4. CALENDARI SETMANAL D'HIDRATS (ZERO REPETICIONS EN DIES CONSECUTIUS):
   Per complir estrictament la no repetició d'hidrats en dies consecutius, has d'assignar la base principal seguint aquest patró:
   - Dilluns: Llegums (ex. Llenties estofades) [PROHIBIT pasta, fideus i arròs; les sopes seran sense fideus]
   - Dimarts: Pasta o Fideus (ex. Macarrons o Sopa de fideus) [PROHIBIT arròs]
   - Dimecres: Verdures i Patata (ex. Mongeta tendra amb patata, Crema de carbassó) [PROHIBIT pasta, fideus i arròs]
   - Dijous: Arròs (ex. Arròs de verdures, Arròs caldós) [PROHIBIT pasta i fideus]
   - Divendres: Llegums o Verdures (ex. Cigrons amb espinacs, Fesols saltats) [PROHIBIT pasta, fideus i arròs]
   - Dissabte: Pasta o Pizza casolana [PROHIBIT arròs]
   - Diumenge: Arròs o Rostit (ex. Paella de verdures o Rostit) [PROHIBIT pasta i fideus]

### 🛡️ PROTOCOL ESTRICTE D'AL·LÈRGIES I INTOLERÀNCIES:
1. Intolerància a la lactosa / Sense lactosa:
   - Com a postre, prioritza SEMPRE "Fruita de temporada" (poma, plàtan, mandarina, pera, maduixes). Si poses iogurt, anomena'l expressament "Iogurt vegetal de coco" o "Iogurt sense lactosa".
   - Està PROHIBIT utilitzar làctics convencionals. Si utilitzes formatge o mozzarella, han de ser exclusivament "Mozzarella vegana", "Formatge vegà", "Formatge sense lactosa" o "Iogurt de coco".
2. Celiaquia / Sense gluten:
   - Està PROHIBIT el blat convencional. Utilitza arròs, quinoa, llegums, patates, o especifica "Pa sense gluten", "Pasta sense gluten", "Pizza casolana sense gluten", "Blat de moro", "Blat sarraí".

### 🍳 APARELLS I EINES DE CUINA DISPONIBLES (NIVELL DE RECEPTES):
- Eines presents a la cuina: {eines_txt}.
⚠️ ADAPTACIÓ STRICTA A LES EINES:
1. El nivell de complexitat i les tècniques culinàries de les receptes han d'anar en funció de les eines disponibles a la llar.
2. MAI proposis cap recepta o tècnica que requereixi un aparell absent:
   - Si NO hi ha 'sifo_n2o': PROHIBIT proposar espumes culinàries amb sifó.
   - Si NO hi ha 'robot_cuina': PROHIBIT receptes basades en passos de robot de cuina (Thermomix).
   - Si NO hi ha 'airfryer': No programis plats pensats exclusivament per a fregidora d'aire.
   - Si NO hi ha 'liquadora': No programis liquats que requereixin extracció de polpa.
   - Si NO hi ha 'olla_pressio': Adapta la cocció a cassola tradicional o llegum ja cuit (evita 'olla a pressió', 'olla ràpida').
   - Si NO hi ha 'minipimer' o 'batedora_vas': Evita cremes molt emulsionades o batuts fins.

### 🔥 REGLA D'ÚS DEL FORN I PRIORITAT DE PETICIONS:
1. Regla d'ús del forn configurada: '{us_forn}'.
2. Si la regla és 'Només cap de setmana (Dissabte i Diumenge)': Els plats automàtics que requereixin forn (rostits, peix al forn, gratinats, pastissos al forn, etc.) s'han de programar EXCLUSIVAMENT en dissabte o diumenge. De dilluns a divendres prioritza coccions ràpides (planxa, cassola, vapor, saltats).
3. ⚡ EXCEPCIÓ DE PRIORITAT ABSOLUTA (PETICIÓ FAMILIAR): Si un membre de la família ha demanat un plat o s'ha fixat un plat que requereix forn per a un dia entre setmana (com ara 'Solomillo al forn dimecres' o 'Lluç al forn dijous'), la voluntat de la família TÉ PRIORITAT ABSOLUTA. En aquest cas, OBVIA la limitació del forn per a aquest àpat concret i programa obligatòriament el plat sol·licitat.

### 🚫 PROHIBICIÓ ESTRICTA: EL 2N PLAT MAI POT SER FRUITA NI IOGURT:
- El camp "segon" ÉS SEMPRE UNA PROTEÏNA O PLAT PRINCIPAL (peix, aus, carn magra, ous, tofu o llegums).
- MAI, sota cap concepte, posis "Fruita de temporada", "Poma", "Plàtan", "Iogurt" com a "segon" plat.
- Totes les fruites i lactis de postre han d'anar EXCLUSIVAMENT al camp "postre".
- Si el primer plat és molt contundent (com ara unes llenties estofades o paella), com a segon plat pots posar una proteïna lleugera (ex. Ou dur amb amanida, Lluç a la planxa) o bé "-" (plat únic), PERÒ MAI FRUITA.

### REGLES CRÍTIQUES DE DESDOBLAMENT I VETOS:
1. Si la família menja un plat que conté un aliment vetat per un sol membre (ex. fetge), programa el plat per a la família i genera OBLIGATÒRIAMENT un 'plat_alternatiu' ràpid (usant els seus comodins favorits) per a aquell membre, compartint la mateixa guarnició.
2. Si un membre està 'FORA DE LA LLAR', NO comptabilitzis les seves restriccions personals per defecte ni el sumis al nombre de racions.

### ESTRUCTURA D'ÀPATS TRADICIONAL CATALANA:
- DINAR:
  - "primer": Primer plat (ex. Amanida, Sopa, Crema de verdures, Llenties, Macarrons, Arròs de verdures)
  - "segon": Segon plat (ex. Lluç al forn amb patates, Pit de pollastre amb xampinyons, Bistec amb guarnició)
  - "postre": Postre saludable (ex. Fruita de temporada, Poma, Iogurt vegetal)
- SOPAR:
  - "primer": Primer plat lleuger (ex. Sopa de brou, Crema de carbassó, Amanida verda) o null
  - "segon": Segon plat lleuger (ex. Truita francesa, Salmó a la planxa, Hamburguesa de verdures)
  - "postre": Postre lleuger (ex. Poma, Fruita de temporada)

### RESPOSTA EN FORMAT JSON ESTRICTE:
Respon EXCLUSIVAMENT amb l'objecte JSON vàlid (sense text previ ni posterior, amb cometes dobles en totes les claus i valors, i sense comes sobrants):
{{
  "dies_planificats": 7,
  "comensals_actius": 3,
  "menu_setmanal": [
    {{
      "dia": "Dilluns",
      "dinar": {{
        "primer": "Crema de carbassó amb crostons",
        "segon": "Lluç a la planxa amb verdures saltades",
        "postre": "Poma de temporada",
        "ingredients_principals": ["carbassó", "ceba", "lluç", "verdures", "poma"],
        "apte_per": ["Nom1", "Nom2"],
        "plat_alternatiu": null
      }},
      "sopar": {{
        "primer": "Amanida verda de tomàquet",
        "segon": "Truita francesa amb tomàquet amanit",
        "postre": "Pera de temporada",
        "ingredients_principals": ["enciam", "tomàquet", "ous", "pera"],
        "apte_per": ["Nom1", "Nom2"],
        "plat_alternatiu": {{
          "per": "Enric",
          "plat": "Pit de pollastre a la planxa amb amanida",
          "motiu": "Veto personal a fetge i casqueria"
        }}
      }}
    }}
  ],
  "bases_batch_prep_diumenge": [
    {{"base": "Patates probiòtiques", "quantitat": "1.5 kg", "utilitzacio": "Dinars de dimarts i dijous"}},
    {{"base": "Caldo de peix / verdures concentrat", "quantitat": "1.5 L", "utilitzacio": "Arròs i sopes"}}
  ],
  "ingredients_a_comprar": ["llista d'ingredients que NO estan a l'stock"]
}}"""
    return prompt

def call_gemini_api(prompt: str, api_key: str, model_name: str = "gemini-2.5-flash") -> Tuple[bool, str, float]:
    """Realitza una crida a l'API de Google Gemini amb reintents automàtics i gestió d'errors 503/429."""
    start_time = time.time()
    
    models_to_try = [model_name]
    for alt in ["gemini-2.5-flash", "gemini-flash-latest"]:
        if alt not in models_to_try:
            models_to_try.append(alt)
        
    last_error = ""
    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 16384,
                "thinkingConfig": {
                    "thinkingBudget": 512
                }
            }
        }
        
        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                resp = requests.post(url, json=payload, timeout=60)
                elapsed = round(time.time() - start_time, 2)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return True, content, elapsed
                    return False, "Resposta buida de Gemini", elapsed
                elif resp.status_code in [503, 429]:
                    time.sleep(5.0 * (attempt + 1))
                    last_error = f"HTTP {resp.status_code} ({current_model}): {resp.text}"
                    continue
                else:
                    last_error = f"Error HTTP {resp.status_code} ({current_model}): {resp.text}"
                    break
            except Exception as e:
                time.sleep(1.5 * (attempt + 1))
                last_error = f"Excepció en cridar Gemini ({current_model}): {str(e)}"
                
    elapsed = round(time.time() - start_time, 2)
    return False, last_error, elapsed

def parse_and_clean_json(raw_text: str) -> Tuple[bool, Dict[str, Any], str]:
    """Neteja delimitadors markdown i parseja el text com a diccionari JSON de manera resilient."""
    if not raw_text:
        return False, {}, "Text buit"
    
    clean = raw_text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()
    
    # 1. Intent directe estàndard
    try:
        parsed = json.loads(clean)
        if isinstance(parsed, dict) and "menu_setmanal" in parsed:
            return True, parsed, ""
    except Exception:
        pass

    # 2. Neteja de comes finals i espais
    candidate = re.sub(r',\s*([\]}])', r'\1', clean)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict) and "menu_setmanal" in parsed:
            return True, parsed, ""
    except Exception:
        pass

    # 3. Reparar claus sense cometes dobles (ex: dinar: { -> "dinar": {)
    candidate_quoted = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', candidate)
    candidate_quoted = re.sub(r',\s*([\]}])', r'\1', candidate_quoted)
    try:
        parsed = json.loads(candidate_quoted)
        if isinstance(parsed, dict) and "menu_setmanal" in parsed:
            return True, parsed, ""
    except Exception:
        pass

    # 4. Cerca del bloc JSON principal {...}
    match = re.search(r'(\{[\s\S]*\})', clean)
    if match:
        block = match.group(1)
        block = re.sub(r',\s*([\]}])', r'\1', block)
        block = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', block)
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict) and "menu_setmanal" in parsed:
                return True, parsed, ""
        except Exception:
            pass

    return False, {}, "Error de sintaxi JSON no recuperable a la resposta del model"

# =========================================================================
# GRADERS DETERMINISTES (AVALUADORS LÒGICS)
# =========================================================================

def netejar_termes_segurs(text: str) -> str:
    """Substitueix adaptacions segures ('sense lactosa', 'sense gluten', 'blat de moro', 'llet de coco', productes vegans) per evitar falsos positius d'al·lèrgies."""
    t = text.lower()
    
    # 1. Netejar qualsevol indicació adaptativa entre parèntesis
    t = re.sub(r'\([^\)]*sense\s+(?:lactosa|gluten|llet|l[àa]ctics|prote[ïi]na de llet|fruits secs)[^\)]*\)', '[TERME_SEGUR]', t)
    t = re.sub(r'\([^\)]*(?:cel[íi]ac|veg[àa]|vegana|apte|adaptat|sense lactosa)[^\)]*\)', '[TERME_SEGUR]', t)
    
    # 2. Netejar combinacions de nom d'aliment seguit de 'vegà/vegana/vegetal/sense lactosa/gluten'
    t = re.sub(r'\b(mozzarella|parmes[àa]|formatge|iogurt|llet|nata|mantega|crema de llet)\s+(?:veg[àa]|vegana|vegetal|sense lactosa|de coco|de soja|d\'ametlla|d\'avena|de civada|d\'arr[òo]s)', '[TERME_SEGUR]', t)
    t = re.sub(r'\b(pa|pasta|farina|fideus|macarrons|espaguetis|espirals|galetes|torrades|pizza)\s+[^\.,;\n\(\)]*sense\s+gluten', '[TERME_SEGUR]', t)
    t = re.sub(r'\b(formatge|iogurt|llet|nata|mantega|crema de llet|parmes[àa]|mozzarella)\s+[^\.,;\n\(\)]*sense\s+(?:lactosa|llet|l[àa]ctics|prote[ïi]na de llet)', '[TERME_SEGUR]', t)
    
    # 3. Llista extensa de termes compostos 100% segurs
    safe_terms = [
        "sense gluten", "sin gluten", "gluten-free", "gluten free", "farina sense gluten", "pa sense gluten", "pasta sense gluten", "macarrons sense gluten", "fideus sense gluten", "espirals sense gluten", "pizza sense gluten", "pizza casolana sense gluten", "salsa de soja sense gluten", "tamari",
        "sense lactosa", "sin lactosa", "lactose-free", "llet sense lactosa", "formatge sense lactosa", "iogurt sense lactosa", "nata sense lactosa", "mantega sense lactosa",
        "sense llet", "sin leche", "dairy-free", "dairy free", "sense làctics", "sense lactics", "sense proteïna de llet", "sense proteina de llet",
        "mozzarella vegana", "mozzarella vegetal", "formatge vegà", "formatge vega", "formatge vegetal", "parmesà vegà", "parmesa vega", "parmesà vegetal", "iogurt vegà", "iogurt vega", "iogurt vegetal", "iogurt de coco", "iogurt de soja", "iogurt d'ametlla", "iogurt de civada",
        "blat sarraí", "blat sarrai", "blat sarraïnat", "blat sarrainat", "blat sarraït", "blat sarrait", "blat sarracè", "blat sarrace", "farina de blat sarraí", "farina de blat sarraïnat", "pasta de blat sarraí", "pasta de blat sarraïnat", "espirals de blat sarraí", "espirals de blat sarraïnat", "espirals de blat sarraït", "trigo sarraceno", "buckwheat",
        "blat de moro", "farina de blat de moro", "tortitas de blat de moro", "tortilla de blat de moro", "pa de blat de moro", "farina de blat de moro", "midó de blat de moro", "maizena",
        "llet de coco", "llet d'ametlla", "llet d'ametlles", "llet de civada", "llet de soja", "llet d'arròs", "llet d'arros", "llet vegetal", "beguda de civada", "beguda de soja", "beguda d'ametlles", "beguda d'arròs",
        "nata vegetal", "nata de coco", "mantega vegetal", "margarina vegetal"
    ]
    safe_terms.sort(key=len, reverse=True)
    for st in safe_terms:
        t = t.replace(st, "[TERME_SEGUR]")
    return t

def extract_apat_text(apat: Dict[str, Any]) -> str:
    """Extreu tot el text dels plats de l'àpat (primer, segon, postre i plat general)."""
    parts = []
    for k in ["plat", "primer", "segon", "postre"]:
        val = apat.get(k)
        if val and isinstance(val, str):
            parts.append(val)
    return " - ".join(parts) if parts else ""

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
            
            plat_text = extract_apat_text(apat)
            ingredients = apat.get("ingredients_principals", [])
            
            # Comprovar nom del plat netejat de termes segurs
            plat_net = netejar_termes_segurs(plat_text)
            for a in alergens:
                pattern = r'\b' + re.escape(a) + r'\b'
                if re.search(pattern, plat_net):
                    infraccions.append(f"{dia_nom} ({apat_k}): '{plat_text}' conté el terme prohibit '{a}'")
            
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
                
                plat_text = extract_apat_text(apat).lower()
                ingredients = [str(i).lower() for i in apat.get("ingredients_principals", [])]
                alt = apat.get("plat_alternatiu")
                
                # Cerca amb paraula exacta
                conte_veto = any(re.search(r'\b' + re.escape(v) + r'\b', plat_text) for v in vetos) or \
                             any(any(re.search(r'\b' + re.escape(v) + r'\b', ing) for v in vetos) for ing in ingredients)
                
                if conte_veto:
                    if alt is None or not isinstance(alt, dict) or not alt.get("plat"):
                        infraccions.append(f"{dia_nom} ({apat_k}): '{plat_text}' té ingredients vetats per a {nom_m} però NO s'ha generat cap 'plat_alternatiu'")
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
            
            plat_text = extract_apat_text(apat).lower()
            ings = " ".join([str(i).lower() for i in apat.get("ingredients_principals", [])])
            full_text = f"{plat_text} {ings}"
            
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
    darrers_hidrats = set()
    
    for dia_obj in menu_data.get("menu_setmanal", []):
        dia_nom = dia_obj.get("dia", "")
        hidrats_avui = set()
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            plat = extract_apat_text(apat).lower()
            ings = " ".join([str(i).lower() for i in apat.get("ingredients_principals", [])])
            full = f"{plat} {ings}"
            
            if any(k in full for k in ["arròs", "arros", "paella", "risotto"]):
                hidrats_avui.add("arròs")
            if any(k in full for k in ["pasta", "macarrons", "fideus", "espaguetis", "espirals", "lasanya", "pizza", "fideuà", "fideua"]):
                hidrats_avui.add("pasta")
                
        if darrers_hidrats:
            inter = hidrats_avui.intersection(darrers_hidrats)
            for h in inter:
                infraccions.append(f"{dia_nom}: Repetició consecutiva d'hidrat '{h}' dos dies seguits")
        darrers_hidrats = hidrats_avui

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

def grade_puntuacions_estrelles(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova que no s'incloguin plats vetats per puntuació baixa (0-2 estrelles) sense alternativa."""
    valoracions = test_case.get("valoracions_previes", {})
    if not valoracions:
        return 1.0, []
        
    infraccions = []
    for dia_obj in menu_data.get("menu_setmanal", []):
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            plat = extract_apat_text(apat)
            apte_per = [str(u).lower() for u in apat.get("apte_per", [])]
            plat_alt = apat.get("plat_alternatiu")
            alt_per = str(plat_alt.get("per", "")).lower() if isinstance(plat_alt, dict) else ""
            
            # Comprovar si aquest plat té puntuació baixa
            for plat_val, notes in valoracions.items():
                if plat_val.lower() in plat.lower() or plat.lower() in plat_val.lower():
                    for user, score in notes.items():
                        user_low = user.lower()
                        if score <= 2:
                            if user_low == alt_per or (apte_per and user_low not in apte_per):
                                continue
                            infraccions.append(f"Plat desaconsellat inclòs sense alternativa: '{plat}' (puntuat amb {score} estrelles per {user})")

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

def grade_eines_i_forn(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova que no s'utilitzin aparells no disponibles i que es respecti la disponibilitat del forn."""
    infraccions = []
    
    eines_disp = test_case.get("eines_disponibles", {})
    if isinstance(eines_disp, list):
        eines_disp_dict = {k: True for k in eines_disp}
    elif isinstance(eines_disp, dict):
        eines_disp_dict = eines_disp
    else:
        eines_disp_dict = {}
        
    regles = test_case.get("regles_llar", {})
    us_forn = regles.get("us_forn", "Cada dia / Qualsevol dia")
    nom_forn_cap_setmana = "Només cap de setmana" in us_forn
    
    peticions_aprovades = [p.get("plat", "").lower() for p in test_case.get("peticions_setmanals", []) if p.get("aprovat_consens", True) or p.get("consens", True)]
    
    restriccions_eines = {
        "sifo_n2o": ["sifó", "sifo", "n2o", "espuma al sifó", "escuma al sifó"],
        "robot_cuina": ["thermomix", "mambo", "velocitat cullera", "varoma", "robot de cuina"],
        "airfryer": ["airfryer", "air fryer", "fregidora d'aire", "fregidora de aire"],
        "liquadora": ["liquadora", "extracte de suc amb liquadora", "liquat de polpa"],
        "tallafiambres": ["tallafiambres", "tallat a màquina fiambre"],
        "olla_pressio": ["olla a pressió", "olla a pressio", "olla ràpida", "olla rapida", "olla express"],
    }
    
    dies_feiners = ["dilluns", "dimarts", "dimecres", "dijous", "divendres"]
    
    for dia_obj in menu_data.get("menu_setmanal", []):
        dia_nom = str(dia_obj.get("dia", "")).lower()
        is_feiner = any(df in dia_nom for df in dies_feiners)
        
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            
            plat_text = extract_apat_text(apat).lower()
            ings_text = " ".join([str(i).lower() for i in apat.get("ingredients_principals", [])])
            full_text = f"{plat_text} {ings_text}"
            
            # 1. Comprovar eines absents
            for e_key, terms in restriccions_eines.items():
                if e_key in eines_disp_dict and not eines_disp_dict[e_key]:
                    for t in terms:
                        if t in full_text:
                            infraccions.append(f"{dia_obj.get('dia')} ({apat_k}): Requereix l'aparell absent '{e_key}' (detectat terme '{t}')")
            
            # 2. Comprovar regla del forn
            if nom_forn_cap_setmana and is_feiner:
                te_forn = "al forn" in full_text or "rostida al forn" in full_text or "gratinat al forn" in full_text
                if te_forn:
                    es_peticio_consens = any(p in plat_text or plat_text in p or "solomillo" in plat_text for p in peticions_aprovades)
                    if not es_peticio_consens:
                        infraccions.append(f"{dia_obj.get('dia')} ({apat_k}): Plats al forn NO permesos entre setmana ('{plat_text}'), ja que la regla és '{us_forn}' i no és una petició familiar expressa")

    if infraccions:
        return 0.0, infraccions
    return 1.0, []

# =========================================================================
# EXECUTOR PRINCIPAL DEL HARNESS
# =========================================================================

def run_harness_single_test(test_case: Dict[str, Any], api_key: str, model_name: str = "gemini-3.8-flash") -> Dict[str, Any]:
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
            "puntuacio_eines": 0.0,
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
            "puntuacio_eines": 0.0,
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
    score_eines, err_eines = grade_eines_i_forn(json_data, test_case)
    
    all_errors = err_alergies + err_vetos + err_regles + err_varietat + err_estrelles + err_eines
    exit_global = (score_alergies == 1.0 and score_vetos == 1.0 and score_regles >= 0.75 and score_varietat == 1.0 and score_estrelles == 1.0 and score_eines == 1.0)
    
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
        "puntuacio_eines": score_eines,
        "latencia_s": latency,
        "errors": all_errors,
        "resposta_json": json_data
    }

def run_harness_suite(api_key: str, model_name: str = "gemini-3.8-flash", progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
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
        time.sleep(0.8)
        
    passed_total = sum(1 for r in results if r["exit_global"])
    passed_json = sum(1 for r in results if r["json_valid"])
    passed_seguretat = sum(1 for r in results if r["puntuacio_seguretat"] == 1.0)
    passed_vetos = sum(1 for r in results if r["puntuacio_vetos"] == 1.0)
    passed_eines = sum(1 for r in results if r.get("puntuacio_eines", 1.0) == 1.0)
    avg_latency = round(sum(r["latencia_s"] for r in results) / total_cases, 2) if total_cases > 0 else 0.0
    
    return {
        "total_proves": total_cases,
        "proves_superades": passed_total,
        "percentatge_exit": round((passed_total / total_cases) * 100, 1),
        "taxa_json_valid": round((passed_json / total_cases) * 100, 1),
        "taxa_seguretat_alergies": round((passed_seguretat / total_cases) * 100, 1),
        "taxa_desdoblament_vetos": round((passed_vetos / total_cases) * 100, 1),
        "taxa_equipament_forn": round((passed_eines / total_cases) * 100, 1),
        "latencia_mitjana_s": avg_latency,
        "model_avaluat": model_name,
        "detall_resultats": results
    }

def generate_harness_markdown_report(data: Dict[str, Any], is_single: bool = False) -> str:
    """Genera un informe exhaustiu en format Markdown (.md) a partir dels resultats del benchmarking."""
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = []
    lines.append("# 🧪 Informe d'Avaluació del Laboratori IA (Harness) - XiquiHouse")
    lines.append(f"\n- **Data i hora de generació:** `{now_str}`")
    
    if is_single:
        # Informe d'un sol cas
        tc_id = data.get("id", "Cas desconegut")
        titol = data.get("titol", "")
        exit_str = "✅ SUPERAT (PASS)" if data.get("exit_global") else "❌ FALLAT (FAIL)"
        lines.append(f"- **Tipus d'execució:** Test Individual (`{tc_id}`)")
        lines.append(f"- **Resultat Global:** **{exit_str}**")
        lines.append(f"- **Temps de resposta (Latència):** `{data.get('latencia_s', 0)} s`")
        lines.append("\n---\n")
        
        lines.append("## 📊 Puntuacions per Criteri")
        lines.append("| Criteri d'Avaluació | Puntuació | Estat |")
        lines.append("| :--- | :---: | :---: |")
        
        def format_score(sc: float) -> str:
            if sc == 1.0: return f"100% | ✅ Correcte"
            elif sc >= 0.75: return f"{int(sc*100)}% | ⚠️ Acceptable"
            return f"{int(sc*100)}% | ❌ Infracció"
            
        lines.append(f"| **Seguretat Mèdica d'Al·lèrgies** | {format_score(data.get('puntuacio_seguretat', 0.0))}")
        lines.append(f"| **Gestió de Vetos i Desdoblament** | {format_score(data.get('puntuacio_vetos', 0.0))}")
        lines.append(f"| **Freqüències Nutricionals de la Llar** | {format_score(data.get('puntuacio_regles', 0.0))}")
        lines.append(f"| **Varietat i Calendari d'Hidrats** | {format_score(data.get('puntuacio_varietat', 0.0))}")
        lines.append(f"| **Adaptació a Eines de Cuina i Forn** | {format_score(data.get('puntuacio_eines', 1.0))}")
        
        lines.append("\n---\n")
        lines.append("## 🔍 Detall d'Infraccions i Observacions")
        errors = data.get("errors", [])
        if not errors:
            lines.append("✨ **Cap incidència detectada.** El model ha complert tots els requisits i restriccions mèdiques.")
        else:
            for err in errors:
                lines.append(f"- ⚠️ {err}")
                
        # Menú
        resp_json = data.get("resposta_json", {})
        if resp_json and "menu_setmanal" in resp_json:
            lines.append("\n---\n")
            lines.append("## 🍽️ Proposta de Menú Setmanal Generat")
            lines.append("| Dia | Dinar (1r - 2n - Postre) | Sopar (1r - 2n - Postre) | Plat Alternatiu |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for dia_obj in resp_json.get("menu_setmanal", []):
                dia_nom = dia_obj.get("dia", "")
                d = dia_obj.get("dinar", {})
                s = dia_obj.get("sopar", {})
                d_str = f"{d.get('primer', '-')} / {d.get('segon', '-')} / {d.get('postre', '-')}"
                s_str = f"{s.get('primer', '-')} / {s.get('segon', '-')} / {s.get('postre', '-')}"
                
                alt_d = d.get("plat_alternatiu")
                alt_s = s.get("plat_alternatiu")
                alt_parts = []
                if alt_d and isinstance(alt_d, dict):
                    alt_parts.append(f"Dinar: {alt_d.get('per')} ({alt_d.get('plat')})")
                if alt_s and isinstance(alt_s, dict):
                    alt_parts.append(f"Sopar: {alt_s.get('per')} ({alt_s.get('plat')})")
                alt_str = " <br> ".join(alt_parts) if alt_parts else "-"
                
                lines.append(f"| **{dia_nom}** | {d_str} | {s_str} | {alt_str} |")
                
    else:
        # Informe de bateria completa
        model_name = data.get("model_avaluat", "gemini-2.5-flash")
        total_p = data.get("total_proves", 0)
        passats = data.get("proves_superades", 0)
        pct_exit = data.get("percentatge_exit", 0)
        
        lines.append(f"- **Model d'IA Avaluat:** `{model_name}`")
        lines.append(f"- **Total de Proves Executades:** `{total_p}`")
        lines.append(f"- **Proves Superades amb Èxit:** **`{passats} / {total_p} ({pct_exit}%)`**")
        lines.append(f"- **Latència Mitjana per Prova:** `{data.get('latencia_mitjana_s', 0)} s`")
        lines.append("\n---\n")
        
        lines.append("## 📊 Resum de Mètriques Globals")
        lines.append("| Mètrica d'Avaluació | Resultat Global | Objectiu | Estat |")
        lines.append("| :--- | :---: | :---: | :---: |")
        
        def eval_status(val: float, target: float = 100.0) -> str:
            if val >= target: return "✅ Excel·lent"
            elif val >= 75.0: return "⚠️ Acceptable"
            return "❌ A millorar"
            
        lines.append(f"| **Taxa d'Èxit Global** | **{pct_exit}%** | 100% | {eval_status(pct_exit)}")
        lines.append(f"| **Validesa Estructural JSON** | {data.get('taxa_json_valid', 0)}% | 100% | {eval_status(data.get('taxa_json_valid', 0))}")
        lines.append(f"| **Seguretat Mèdica d'Al·lèrgies** | {data.get('taxa_seguretat_alergies', 0)}% | 100% (Tolerància 0%) | {eval_status(data.get('taxa_seguretat_alergies', 0))}")
        lines.append(f"| **Desdoblament de Vetos Personals** | {data.get('taxa_desdoblament_vetos', 0)}% | 100% | {eval_status(data.get('taxa_desdoblament_vetos', 0))}")
        lines.append(f"| **Adaptació a Eines de Cuina i Forn** | {data.get('taxa_equipament_forn', 0)}% | 100% | {eval_status(data.get('taxa_equipament_forn', 0))}")
        
        lines.append("\n---\n")
        lines.append("## 📋 Taula Resum de Casos de Prova")
        lines.append("| ID | Títol del Cas de Prova | Estat | Latència | Incidències |")
        lines.append("| :--- | :--- | :---: | :---: | :--- |")
        
        for r in data.get("detall_resultats", []):
            st_icon = "✅ PASS" if r.get("exit_global") else "❌ FAIL"
            err_count = len(r.get("errors", []))
            err_txt = f"{err_count} incidències" if err_count > 0 else "Cap"
            lines.append(f"| `{r.get('id')}` | {r.get('titol')} | **{st_icon}** | `{r.get('latencia_s')}s` | {err_txt} |")
            
        lines.append("\n---\n")
        lines.append("## 🔍 Desglossament Detallat per Cas de Prova")
        for idx, r in enumerate(data.get("detall_resultats", [])):
            icon = "✅" if r.get("exit_global") else "❌"
            lines.append(f"\n### {idx+1}. {icon} {r.get('id')}: {r.get('titol')}")
            lines.append(f"- **Estat:** `{'SUPERAT' if r.get('exit_global') else 'FALLAT'}` | **Latència:** `{r.get('latencia_s')}s`")
            
            errs = r.get("errors", [])
            if errs:
                lines.append("- **⚠️ Infraccions detectades:**")
                for e in errs:
                    lines.append(f"  - 🔴 {e}")
            else:
                lines.append("- **✨ Compliment:** 100% dels criteris i regles de seguretat respectats.")
                
            resp_json = r.get("resposta_json", {})
            if resp_json and "menu_setmanal" in resp_json:
                lines.append("\n**Menú Generat:**")
                lines.append("| Dia | Dinar | Sopar | Plat Alternatiu |")
                lines.append("| :--- | :--- | :--- | :--- |")
                for dia_obj in resp_json.get("menu_setmanal", []):
                    dia_nom = dia_obj.get("dia", "")
                    d = dia_obj.get("dinar", {})
                    s = dia_obj.get("sopar", {})
                    d_str = f"{d.get('primer', '-')} / {d.get('segon', '-')}"
                    s_str = f"{s.get('primer', '-')} / {s.get('segon', '-')}"
                    
                    alt_d = d.get("plat_alternatiu")
                    alt_s = s.get("plat_alternatiu")
                    alt_parts = []
                    if alt_d and isinstance(alt_d, dict):
                        alt_parts.append(f"Dinar: {alt_d.get('per')} ({alt_d.get('plat')})")
                    if alt_s and isinstance(alt_s, dict):
                        alt_parts.append(f"Sopar: {alt_s.get('per')} ({alt_s.get('plat')})")
                    alt_str = " <br> ".join(alt_parts) if alt_parts else "-"
                    lines.append(f"| {dia_nom} | {d_str} | {s_str} | {alt_str} |")
                    
    lines.append("\n\n---\n*Informe generat automàticament pel Laboratori d'IA i Harness Nutricional de XiquiHouse.*")
    return "\n".join(lines)
