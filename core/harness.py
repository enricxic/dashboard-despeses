import json
import os
import time
import re
import requests
from typing import Dict, List, Any, Optional, Tuple, Callable

def get_live_family_test_case() -> Dict[str, Any]:
    """Genera un cas de prova dinàmic basat en la configuració real activa de la llar (config.json)."""
    try:
        from core.config_manager import load_app_config
        cfg = load_app_config()
        familia = cfg.get("familia", [])
        regles = cfg.get("regles_menjar", {})
        eines = cfg.get("eines_cuina", {})
        
        return {
            "id": "TC-REAL-XiquiHouse",
            "titol": "Perfil Real de la Llar (Configuració Actual)",
            "descripcio": "Avaluació del menú setmanal usant la configuració real activa de la família, regles nutricionals i equipament de XiquiHouse.",
            "perfil_familia": familia,
            "regles_llar": regles,
            "eines_disponibles": eines,
            "stock_disponible": [],
            "peticions_setmanals": [],
            "valoracions_previes": {},
            "configuracio_apats": {
                "dies": 7,
                "format": "Tota la setmana (Dinars i Sopars - 14 àpats)",
                "comensals_base": sum(1 for m in familia if m.get("actiu", True))
            },
            "criteris_esperats": {
                "max_carn_vermella": regles.get("max_carn_vermella", 1),
                "min_dies_peix": regles.get("min_peix", 2),
                "min_dies_llegum": regles.get("min_llegums", 2),
                "max_embotits_sopar": regles.get("max_embotits_sopar", 2),
                "zero_repeticions_hidrats": regles.get("no_repetir_hidrats", True)
            }
        }
    except Exception as e:
        print(f"Error generant cas de prova real: {e}")
        return {}

def load_harness_cases(file_path: Optional[str] = None, include_live: bool = True) -> List[Dict[str, Any]]:
    """Carrega la col·lecció de casos de prova del banc de dades JSON resolent rutes absolutes."""
    cases = []
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
                
    if target_path and os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cases = data.get("test_cases", [])
        except Exception as e:
            print(f"Error carregant casos de prova des de {target_path}: {e}")
            cases = []

    if include_live:
        live_case = get_live_family_test_case()
        if live_case and live_case.get("id"):
            cases.append(live_case)
            
    try:
        from core.config_manager import load_app_config
        cfg = load_app_config()
        overrides = cfg.get("harness_overrides", {})
        if overrides:
            r_ov = overrides.get("regles_menjar")
            e_ov = overrides.get("eines_cuina")
            for c in cases:
                if r_ov:
                    c.setdefault("regles_llar", {}).update(r_ov)
                if e_ov:
                    c["eines_disponibles"] = e_ov
    except Exception as e:
        print(f"Error aplicant overrides a harness cases: {e}")
        
    return cases

def build_system_prompt_for_case(test_case: Dict[str, Any], recipes_catalog: Optional[List[Any]] = None, recipes_sample: Optional[List[Any]] = None, **kwargs) -> str:
    """Construeix el prompt del sistema optimitzat per generar un menú estricte en format JSON."""
    
    cataleg_utilitzar = recipes_catalog if recipes_catalog is not None else recipes_sample
    if cataleg_utilitzar is None:
        cataleg_utilitzar = kwargs.get("cataleg_receptes", [])

    perfil_txt = ""
    for m in test_case.get("perfil_familia", []):
        if not m.get("actiu", True):
            continue
        alergies_str = ", ".join(m.get("alergies", [])) if m.get("alergies") else "Cap"
        vetos_str = ", ".join(m.get("vetos", [])) if m.get("vetos") else "Cap"
        comodins_str = ", ".join(m.get("comodins", [])) if m.get("comodins") else "Cap"
        alts_str = ", ".join(m.get("plats_alternatius", [])) if m.get("plats_alternatius") else comodins_str
        
        perfil_line = f"- {m.get('nom')} ({m.get('rol')}, {m.get('edat')} anys) [Present a la llar]: Al·lèrgies mèdiques: {alergies_str} | Vetos personals: {vetos_str} | Plats comodí (general): {comodins_str} | Alternatives per Vetos: {alts_str}"
        
        d_tip = m.get("dieta_tipus", "").strip()
        d_dur = m.get("dieta_duracio", "").strip()
        d_mal = m.get("dieta_malaltia", "").strip()
        if d_tip or d_dur or d_mal:
            perfil_line += f" | 🏥 DIETA ESPECIAL PRIORITÀRIA: Tipus '{d_tip}', Duració '{d_dur}', Malaltia/Nota '{d_mal}'"
            
        perfil_txt += perfil_line + "\n"

    regles = test_case.get("regles_llar", {})
    us_forn = regles.get("us_forn", "Només cap de setmana (Dissabte i Diumenge)")
    temporada = regles.get("temporada", "Tot l'any")
    regles_txt = f"""- Temporada actual: {temporada}. Adapta l'estil dels plats (evita sopes calentes a l'estiu, evita gaspatxos a l'hivern).
- Màxim carn vermella: {regles.get('max_carn_vermella', 1)} cop per setmana.
- Cops de peix: EXACTAMENT {regles.get('freq_peix', regles.get('min_peix', 2))} cops per setmana.
- Mínim llegums: {regles.get('min_llegums', 2)} cops per setmana.
- Màxim sopars d'embotits/freds: {regles.get('max_embotits_sopar', 2)} cops per setmana.
- CRÍTIC: NO pots servir arròs ni pasta en dies consecutius (si avui hi ha arròs/pasta, demà NO n'hi pot haver). Intercala amb llegums, verdures o carn/peix.
- Disponibilitat del forn: {us_forn}."""

    if regles.get("control_dietetic"):
        limit_din = regles.get("limit_cals_dinar", 800)
        limit_sop = regles.get("limit_cals_sopar", 500)
        regles_txt += f"\n- 🟢 CONTROL DIETÈTIC ACTIU: Tens l'obligació estricta de generar un menú baix en calories, d'alta puntuació de salut i EQUILIBRAT. El límit és de {limit_din} kcal pel Dinar i {limit_sop} kcal pel Sopar. A més, has de garantir que a la setmana hi hagi almenys 3 plats amb el tag 'peix_blau' o 'peix_blanc', almenys 2 amb 'llegums', i evitar repetir 'carn_vermella'. Usa els 'Tags' que t'indico al costat de cada plat per equilibrar la setmana. Retorna a cada àpat l'atribut 'calories_aprox' (nombre enter)."

    plats_recents = regles.get("plats_recents", [])
    if plats_recents and regles.get("dies_no_repetir", 15) > 0:
        regles_txt += f"\n- 🛑 PROHIBIT REPETIR: Aquests plats s'han menjat en els últims {regles.get('dies_no_repetir', 15)} dies i tens absolutament prohibit incloure'ls de nou sota cap concepte: {', '.join(plats_recents)}."
        
    if regles.get("prioritzar_estrelles", True):
        regles_txt += "\n- ⭐ PRIORITAT ESTRELLES: Rebràs els plats del catàleg amb una nota (ex: [⭐4]). Prioritza SEMPRE que puguis els plats que tinguin 4 o 5 estrelles i evita si és possible els de menor nota."


    stock_list = test_case.get("stock_disponible", [])
    stock_rebost = [s for s in stock_list if "Rebost" in s.get("ubicacio", "")]
    stock_congelador = [s for s in stock_list if "Congelador" in s.get("ubicacio", "")]
    
    stock_txt = "Cap"
    if stock_list:
        stock_txt = ""
        if stock_congelador:
            stock_txt += "🧊 **CONGELADOR (MÀXIMA PRIORITAT - ÚS OBLIGATORI AQUESTA SETMANA):**\n"
            stock_txt += "\n".join([f"  - {s.get('producte')} ({s.get('quantitat')})" for s in stock_congelador]) + "\n"
        if stock_rebost:
            stock_txt += "🥫 **REBOST (Utilitzar preferentment si encaixa):**\n"
            stock_txt += "\n".join([f"  - {s.get('producte')} ({s.get('quantitat')})" for s in stock_rebost])

    peticions_list = test_case.get("peticions_setmanals", [])
    peticions_txt = "Cap"
    if peticions_list:
        peticions_txt = "\n".join([f"- {p.get('comensal')}: '{p.get('plat')}' (Preferència: {p.get('dia_preferit', 'Qualsevol')})" for p in peticions_list])
        peticions_txt += "\n⚠️ Llegeix bé les excepcions on membres estiguin absents, ja que s'han d'ignorar absolutament els seus vetos per aquells àpats concrets i reduir-ne la quantitat de menjar."

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
        primers_dinar = []
        segons_dinar = []
        primers_sopar = []
        segons_sopar = []
        altres = []
        
        for r in cataleg_utilitzar:
            if isinstance(r, dict):
                titol = r.get("titol", "")
                cat = str(r.get("categoria", "")).lower()
                apat = str(r.get("apat", "")).lower()
                estrelles = r.get("estrelles", 4)
                calories = r.get("calories", 0)
                salut = r.get("puntuacio_salut", 0)
                tags = r.get("tags_nutricionals") or []
                
                if titol:
                    cal_str = f", 🔥 {calories} kcal" if calories else ""
                    salut_str = f", 💚 Salut: {salut}/10" if salut else ""
                    tags_str = f", Tags: {', '.join(tags)}" if tags else ""
                    titol = f"{titol} [⭐{estrelles}{cal_str}{salut_str}{tags_str}]"
            else:
                titol = str(r)
                cat = "primer"
                apat = "dinar/sopar"
            
            if not titol: continue
            
            es_dinar = "dinar" in apat or not apat or apat == "nan" or "sense" in apat
            es_sopar = "sopar" in apat or not apat or apat == "nan" or "sense" in apat
            
            if "primer" in cat:
                if es_dinar: primers_dinar.append(titol)
                if es_sopar: primers_sopar.append(titol)
            elif "segon" in cat or "únic" in cat or "plat" in cat:
                if es_dinar: segons_dinar.append(titol)
                if es_sopar: segons_sopar.append(titol)
            else:
                altres.append(titol)
                
        # Treure duplicats si estan tant a dinar com a sopar (només visualment, però l'AI ho entendrà)
        receptari_txt = f"""- PRIMERS PLATS DE DINAR: {', '.join(list(set(primers_dinar))[:40])}
- SEGONS PLATS DE DINAR: {', '.join(list(set(segons_dinar))[:40])}
- PRIMERS PLATS DE SOPAR: {', '.join(list(set(primers_sopar))[:40])}
- SEGONS PLATS DE SOPAR: {', '.join(list(set(segons_sopar))[:40])}
- ALTRES / COMPLEMENTS: {', '.join(list(set(altres))[:30])}"""

    prompt = f"""Ets el planificador nutricional intel·ligent de XiquiHouse.
La teva missió és dissenyar un menú setmanal equilibrat, deliciós, segur i optimitzat per a la família seguint estrictament aquestes dades:

### 📖 LLIBRE DE RECEPTES DE LA FAMÍLIA (OBLIGATORI PRIORITZAR):
{receptari_txt}
⚠️ PRIORITZACIÓ OBLIGATÒRIA: Sempre que un plat encaixi amb la temporada, comensals i regles nutricionals, UTILITZA ELS PLATS DEL LLIBRE DE RECEPTES amb el seu títol exacte! Només proposa plats nous si cap recepta del llibre compleix els requisits.

### PERFIL FAMILIAR:
{perfil_txt}

### REGLES NUTRICIONALS DE LA LLAR:
{regles_txt}

### 🧊 ESTOC EXISTENT AL REBOST / CONGELADOR (PRIORITAT ABSOLUTA D'APROFITAMENT "ZERO WASTE"):
{stock_txt}
⚠️ OBLIGACIÓ D'APROFITAMENT D'ESTOC: Els ingredients llistats a l'estoc tenen presència física positiva al rebost/congelador. TENS LA PREFERÈNCIA ABSOLUTA D'INCORPORAR-LOS als primers o segons plats del menú setmanal per evitar el malbaratament d'aliments i reduir la llista de la compra.

### PETICIONS APROVADES DE LA FAMÍLIA:
{peticions_txt}

### HISTÒRIC DE PUNTUACIONS (ESTRELLES 0-5):
{val_txt}
NOTA SOBRE PUNTUACIONS: Prioritza plats amb 4-5 estrelles. MAI programis plats que tinguin 0, 1 o 2 estrelles (excepte si és per a la resta de la família i assignes un 'plat_alternatiu' al membre afectat).

### ⚠️ COMPLIMENT ESTRICTE DE FREQÜÈNCIES NUTRICIONALS I CALENDARI D'HIDRATS:
1. CARN VERMELLA (vedella, bou, hamburguesa): Màxim el límit indicat (habitualment MÀXIM 1 COP en tota la setmana). Si ja has posat carn vermella un dia, la resta de dies utilitza aus (pollastre, gall dindi), peix, ous o llegums.
2. SOPARS FREDS / EMBOTITS: Màxim el límit indicat (habitualment MÀXIM 2 COPS per setmana).
3. PEIX: Assegura EXACTAMENT la freqüència indicada (habitualment 2 cops setmanals).
4. LLEGUMS: Assegura el mínim de cops setmanals (habitualment mínim 2).
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
2. Si la regla és 'Només cap de setmana (Dissabte i Diumenge)': MAI ENCENGUIS EL FORN DE DILLUNS A DIVENDRES. Els plats que requereixin forn (rostits, peix al forn, gratinats, pastissos al forn, etc.) s'han de programar EXCLUSIVAMENT en dissabte o diumenge.
3. ⚡ EXCEPCIÓ DE PRIORITAT ABSOLUTA (PETICIÓ FAMILIAR): L'únic cas on pots encendre el forn de Dilluns a Divendres és si la família ho ha demanat explícitament a les PETICIONS APROVADES. La voluntat de la família TÉ PRIORITAT ABSOLUTA.

### 🚫 PROHIBICIÓ ESTRICTA: EL 2N PLAT MAI POT SER FRUITA NI IOGURT:
- El camp "segon" ÉS SEMPRE UNA PROTEÏNA O PLAT PRINCIPAL (peix, aus, carn magra, ous, tofu o llegums).
- MAI, sota cap concepte, posis "Fruita de temporada", "Poma", "Plàtan", "Iogurt" com a "segon" plat.
- Totes les fruites i lactis de postre han d'anar EXCLUSIVAMENT al camp "postre".
- Si el primer plat és molt contundent (com ara unes llenties estofades o paella), com a segon plat pots posar una proteïna lleugera (ex. Ou dur amb amanida, Lluç a la planxa) o bé "-", PERÒ MAI FRUITA.
- ⚠️ PROHIBICIÓ POSTRES GENÈRICS: Està PROHIBIT posar simplement "Fruita de temporada" com a postre. HAS D'ESPECIFICAR QUINA FRUITA ES CONCRETAMENT (ex. "Síndria fresca", "Mandarines", "Poma al forn", "Raïm blanc", "Meló tallat"). Varia les fruites durant la setmana.

### REGLES CRÍTIQUES DE DESDOBLAMENT I VETOS (LLEGEIX AMB ATENCIÓ):
1. Si un membre està 'FORA DE LA LLAR', IGNORA COMPLETAMENT I ABSOLUTAMENT TOTS ELS SEUS VETOS. Els seus vetos NO s'apliquen a la resta de la família.
2. ABANS d'aplicar un veto per a un membre actiu, comprova que l'ingredient realment forma part del plat. EXEMPLE CRÍTIC: "Llom de porc" o "Llom a la planxa" NO ÉS "Fetge" ni "Casqueria". "Pollastre" NO ÉS "Carn vermella". No inventis correspondències falses.
3. Si un membre ACTIU té un veto sobre el plat principal familiar, genera OBLIGATÒRIAMENT un 'plat_alternatiu' ràpid (usant els seus comodins favorits) per a aquell membre, compartint la mateixa guarnició.

### ESTRUCTURA D'ÀPATS TRADICIONAL CATALANA:
- DINAR:
  - "primer": Primer plat (ex. Amanida, Sopa, Crema de verdures, Llenties, Macarrons).
  - "segon": Segon plat (ex. Lluç al forn amb patates, Pit de pollastre, Bistec).
  - ⚡ EXCEPCIÓ ARROSSOS I MARISC (CAP DE SETMANA): Si prepares un àpat festiu de cap de setmana amb Arrossos, Paelles o Fideuàs, aquest ha d'anar OBLIGATÒRIAMENT a "segon" (com a plat principal). El "primer" plat ha de ser un aperitiu o entrant lleuger, com ara 'Escamarlans a la planxa', 'Amanida', 'Calamars', 'Musclos' o 'Cloïsses'. És a dir: Primer -> Marisc/Entrant; Segon -> Arròs/Fideuà.
  - "postre": Postre saludable (ex. Fruita de temporada, Poma, Iogurt vegetal)
- SOPAR:
  - "primer": Primer plat lleuger (ex. Sopa de brou, Crema de carbassó, Amanida verda) o null
  - "segon": Segon plat lleuger (ex. Truita francesa, Salmó a la planxa, Hamburguesa de verdures)
  - "postre": Postre lleuger (ex. Poma, Fruita de temporada)

### RESPOSTA EN FORMAT JSON ESTRICTE:
Respon EXCLUSIVAMENT amb l'objecte JSON vàlid (sense text previ ni posterior, amb cometes dobles en totes les claus i valors, i sense comes sobrants):
{{
  "reflexio_obligatoria": {{
    "assignacio_hidrats": "Indica l'esquema d'hidrats per cada dia. Ex: Dl: Llegums, Dm: Pasta, Dc: Verdures, Dj: Arròs, Dv: Llegums, Ds: Pasta, Dg: Arròs. REVISA bé que NO hi hagi pasta o arròs en dies consecutius.",
    "dies_us_forn": "Indica quins dies concrets encendràs el forn. Recorda: Només cap de setmana (Ds i Dg) a no ser que hi hagi una petició expressa familiar.",
    "mapa_vetos_actius": "Llista NOMÉS els comensals que estan presents a la llar i els seus vetos. IGNORE i OMET qualsevol veto de familiars 'FORA DE LA LLAR'. Verifica que els ingredients vetats coincideixen exactament (ex: llom NO és fetge).",
    "recompte_setmanal": {{
      "cops_carn_vermella": "Quants cops apareix carn vermella? (Màxim 1, en cap de setmana)",
      "cops_peix": "Quants cops apareix peix? (Assegura't de complir la quantitat EXACTA demanada)",
      "cops_llegums": "Quants cops apareixen llegums? (Mínim 2)"
    }},
    "peticions_a_integrar": "Llista les peticions que se t'han demanat i com les ubicaràs al calendari.",
    "pla_tactic_estoc": "Explica DIA a DIA com vas a descongelar i utilitzar OBLIGATORIAMENT TOTS els ítems llistats a la secció de CONGELADOR, i quins del REBOST."
  }},
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
          "per": "Nom_del_comensal",
          "plat": "Plat alternatiu escollit",
          "motiu": "Veto personal a Ingredient_vetat"
        }}
      }}
    }}
  ],
  "bases_batch_prep_diumenge": [
    {{"base": "Coure 1.5kg de verdures al vapor (carbassó, pastanaga i bròquil)", "utilitzacio": "Servirà com a acompanyament ràpid i per fer les cremes dels dinars de dilluns a dimecres."}},
    {{"base": "Preparar 1.5L de caldo concentrat de verdures i peix", "utilitzacio": "Serà la base imprescindible per a l'arròs de dijous i la sopa de dimarts."}}
  ],
  "ingredients_a_comprar": [
    {{"nom": "Lluç fresc", "quantitat": "4 filets", "estat": "Comprar"}},
    {{"nom": "Ceba", "quantitat": "1 kg", "estat": "Al rebost"}}
  ]
}}

CRÍTIC: NO TALLIS EL JSON. Assegura't de tancar tots els claudàtors i claus ']' i '}}' correctament."""
    return prompt

from core.llm import call_llm_api
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

    return False, {}, f"Error de sintaxi JSON no recuperable a la resposta del model. Resposta crua:\n{raw_text}"

# =========================================================================
# GRADERS DETERMINISTES (AVALUADORS LÒGICS)
# =========================================================================

def netejar_termes_segurs(text: str) -> str:
    """Substitueix adaptacions segures ('sense lactosa', 'sense gluten', 'blat de moro', 'llet de coco', productes vegans) per evitar falsos positius d'al·lèrgies."""
    t = text.lower()
    
    # 1. Netejar qualsevol indicació adaptativa entre parèntesis
    t = re.sub(r'\([^\)]*sense\s+[^\)]*\)', '[TERME_SEGUR]', t)
    t = re.sub(r'\([^\)]*(?:cel[íi]ac|veg[àa]|vegana|apte|adaptat|sense lactosa)[^\)]*\)', '[TERME_SEGUR]', t)
    
    # 2. Netejar combinacions de nom d'aliment seguit de 'sense lactosa/gluten/llet' o 'vegà/vegana/vegetal'
    t = re.sub(r'\b(mozzarella|parmes[àa]|formatge|iogurt|llet|nata|mantega|crema de llet)\s+sense\s+(?:lactosa|llet|l[àa]ctics|prote[ïi]na de llet)', '[TERME_SEGUR]', t)
    t = re.sub(r'\b(mozzarella|parmes[àa]|formatge|iogurt|llet|nata|mantega|crema de llet)\s+(?:veg[àa]|vegana|vegetal|de coco|de soja|d\'ametlla|d\'avena|de civada|d\'arr[òo]s)', '[TERME_SEGUR]', t)
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
        
    # 4. Neteja genèrica final de 'sense <paraula>'
    t = re.sub(r'\bsense\s+[a-zà-ú0-9_\'-]+', '[TERME_SEGUR]', t)
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
    
    arros_kw = [r"\barròs\b", r"\barros\b", r"\bpaella\b", r"\brisotto\b"]
    pasta_kw = [r"\bpasta\b", r"\bmacarrons\b", r"\bfideus\b", r"\bespaguetis\b", r"\bespirals\b", r"\blasanya\b", r"\bpizza\b", r"\bfideuà\b", r"\bfideua\b"]
    
    for dia_obj in menu_data.get("menu_setmanal", []):
        dia_nom = dia_obj.get("dia", "")
        hidrats_avui = set()
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            
            plat_text = extract_apat_text(apat).lower()
            
            # Avoid counting "sense fideus" or "sense arròs"
            plat_text = re.sub(r'\bsense\s+[a-zà-ú0-9_\'-]+', '', plat_text)
            
            ings = " ".join([str(i).lower() for i in apat.get("ingredients_principals", [])])
            full = f"{plat_text} {ings}"
            
            if any(re.search(k, full) for k in arros_kw):
                hidrats_avui.add("arròs")
            if any(re.search(k, full) for k in pasta_kw):
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

def grade_aprofitament_estoc(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Avalua l'aprofitament de l'estoc de rebost disponible al menú generat."""
    stock_items = test_case.get("stock_disponible", [])
    if not stock_items:
        return 1.0, []
        
    stock_names = []
    for s in stock_items:
        prod_name = str(s.get("producte", "")).strip().lower()
        if prod_name:
            stock_names.append(prod_name)
            
    if not stock_names:
        return 1.0, []
        
    all_menu_text = ""
    for dia_obj in menu_data.get("menu_setmanal", []):
        for apat_k in ["dinar", "sopar"]:
            apat = dia_obj.get(apat_k, {})
            if isinstance(apat, dict):
                plat_t = extract_apat_text(apat).lower()
                ings_t = " ".join([str(i).lower() for i in apat.get("ingredients_principals", [])])
                all_menu_text += f" {plat_t} {ings_t}"
                
    all_menu_text = all_menu_text.lower()
    used_count = 0
    missing_items = []
    
    for s_name in stock_names:
        keywords = [w for w in re.split(r'\W+', s_name) if len(w) >= 3 and w not in ['casolà', 'casola', 'paquet', 'unitats', 'bossa', 'litre', 'pots', 'congelador', 'rebost', 'nevera', 'ingredient', 'preferent', 'estoc', 'prioritat', 'alta']]
        if not keywords:
            keywords = [s_name]
            
        found = any(kw in all_menu_text for kw in keywords)
        if found:
            used_count += 1
        else:
            missing_items.append(s_name)
            
    ratio = used_count / len(stock_names) if stock_names else 1.0
    infraccions = []
    if missing_items and ratio < 0.5:
        infraccions.append(f"Només s'ha aprofitat el {int(ratio*100)}% de l'estoc de rebost positiu (no s'ha utilitzat: {', '.join(missing_items[:3])})")
        return round(ratio, 2), infraccions
        
    return 1.0, []

def grade_control_dietetic(menu_data: Dict[str, Any], test_case: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Comprova que els àpats respectin els límits de calories i el control dietètic."""
    regles = test_case.get("regles_llar", {})
    if not regles.get("control_dietetic"):
        return 1.0, []
        
    limit_din = regles.get("limit_cals_dinar", 800)
    limit_sop = regles.get("limit_cals_sopar", 500)
    
    infraccions = []
    
    for dia_obj in menu_data.get("menu_setmanal", []):
        dia_nom = dia_obj.get("dia", "")
        for apat_k, limit in [("dinar", limit_din), ("sopar", limit_sop)]:
            apat = dia_obj.get(apat_k, {})
            if not isinstance(apat, dict): continue
            
            cals = apat.get("calories_aprox") or apat.get("calories")
            
            if cals is None:
                infraccions.append(f"{dia_nom} ({apat_k}): No s'ha reportat l'atribut 'calories_aprox'")
            else:
                try:
                    cals_val = int(cals)
                    if cals_val > limit:
                        infraccions.append(f"{dia_nom} ({apat_k}): Excés de calories ({cals_val} kcal > límit {limit} kcal)")
                except ValueError:
                    infraccions.append(f"{dia_nom} ({apat_k}): Format invàlid de calories ({cals})")
                    
    if infraccions:
        total_apats = 14
        complerts = max(0, total_apats - len(infraccions))
        return round(complerts / total_apats, 2), infraccions
        
    return 1.0, []

# =========================================================================
# EXECUTOR PRINCIPAL DEL HARNESS
# =========================================================================

def run_harness_single_test(test_case: Dict[str, Any], api_key: str, model_name: str = "gemini-3.8-flash", provider: str = "gemini") -> Dict[str, Any]:
    """Executa un cas de prova complet i retorna el resultat i la targeta de puntuació."""
    prompt = build_system_prompt_for_case(test_case)
    ok_call, raw_resp, latency = call_llm_api(prompt, api_key=api_key, model_name=model_name, provider=provider)
    
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
            "puntuacio_estoc": 0.0,
            "puntuacio_dietetic": 0.0,
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
            "puntuacio_estoc": 0.0,
            "puntuacio_dietetic": 0.0,
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
    score_estoc, err_estoc = grade_aprofitament_estoc(json_data, test_case)
    score_dietetic, err_dietetic = grade_control_dietetic(json_data, test_case)
    
    all_errors = err_alergies + err_vetos + err_regles + err_varietat + err_estrelles + err_eines + err_estoc + err_dietetic
    exit_global = (score_alergies == 1.0 and score_vetos == 1.0 and score_regles >= 0.75 and score_varietat == 1.0 and score_estrelles == 1.0 and score_eines == 1.0 and score_estoc >= 0.5 and score_dietetic >= 0.8)
    
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
        "puntuacio_estoc": score_estoc,
        "puntuacio_dietetic": score_dietetic,
        "latencia_s": latency,
        "errors": all_errors,
        "resposta_json": json_data
    }

def run_harness_suite(api_key: str, model_name: str = "gemini-3.8-flash", provider: str = "gemini", progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
    """Executa la bateria completa de proves i retorna un resum global de rendiment."""
    cases = load_harness_cases()
    if not cases:
        return {"error": "No s'han trobat casos de prova a 'data/harness_menu_cases.json'"}
        
    total_cases = len(cases)
    results = []
    
    for idx, tc in enumerate(cases):
        if progress_callback:
            progress_callback(idx + 1, total_cases, tc.get("titol", f"Test {idx+1}"))
            
        res = run_harness_single_test(tc, api_key=api_key, model_name=model_name, provider=provider)
        results.append(res)
        time.sleep(0.8)
        
    passed_total = sum(1 for r in results if r["exit_global"])
    passed_json = sum(1 for r in results if r["json_valid"])
    passed_seguretat = sum(1 for r in results if r["puntuacio_seguretat"] == 1.0)
    passed_vetos = sum(1 for r in results if r["puntuacio_vetos"] == 1.0)
    passed_eines = sum(1 for r in results if r.get("puntuacio_eines", 1.0) == 1.0)
    passed_dietetic = sum(1 for r in results if r.get("puntuacio_dietetic", 1.0) == 1.0)
    avg_latency = round(sum(r["latencia_s"] for r in results) / total_cases, 2) if total_cases > 0 else 0.0
    
    return {
        "total_proves": total_cases,
        "proves_superades": passed_total,
        "percentatge_exit": round((passed_total / total_cases) * 100, 1),
        "taxa_json_valid": round((passed_json / total_cases) * 100, 1),
        "taxa_seguretat_alergies": round((passed_seguretat / total_cases) * 100, 1),
        "taxa_desdoblament_vetos": round((passed_vetos / total_cases) * 100, 1),
        "taxa_equipament_forn": round((passed_eines / total_cases) * 100, 1),
        "taxa_control_dietetic": round((passed_dietetic / total_cases) * 100, 1),
        "latencia_mitjana_s": avg_latency,
        "model_avaluat": model_name,
        "detall_resultats": results
    }

# =========================================================================
# BACKGROUND WORKER & PERSISTÈNCIA D'ESTAT DEL HARNESS
# =========================================================================

import threading

def _get_status_file_path() -> str:
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(curr_dir, ".."))
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "harness_status.json")

def get_harness_status() -> Dict[str, Any]:
    """Retorna l'estat actual del background worker del Harness."""
    path = _get_status_file_path()
    if not os.path.exists(path):
        return {"status": "idle", "progress": None, "results": None, "error": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"status": "idle", "progress": None, "results": None, "error": None}

def save_harness_status(status_data: Dict[str, Any]):
    """Desa l'estat actual del Harness al disc."""
    path = _get_status_file_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error desant l'estat del harness: {e}")

def clear_harness_status():
    """Restableix l'estat del harness."""
    save_harness_status({"status": "idle", "progress": None, "results": None, "error": None})

def _harness_background_worker(api_key: str, model_name: str, provider: str = "gemini"):
    """Executa la suite en un fil separat i actualitza l'estat progressivament."""
    from datetime import datetime
    cases = load_harness_cases()
    if not cases:
        save_harness_status({
            "status": "error",
            "progress": None,
            "results": None,
            "error": "No s'han trobat casos de prova a 'data/harness_menu_cases.json'",
            "finished_at": datetime.now().strftime("%H:%M:%S (%d/%m/%Y)")
        })
        return
        
    total_cases = len(cases)
    results = []
    start_ts = time.time()
    started_at_str = datetime.now().strftime("%H:%M:%S (%d/%m/%Y)")
    
    save_harness_status({
        "status": "running",
        "started_at": started_at_str,
        "start_ts": start_ts,
        "elapsed_s": 0.0,
        "model_name": model_name,
        "progress": {
            "current": 0,
            "total": total_cases,
            "current_title": "Iniciant bateria...",
            "pct": 0.0
        },
        "results": None,
        "error": None
    })
    
    for idx, tc in enumerate(cases):
        elapsed_now = round(time.time() - start_ts, 1)
        save_harness_status({
            "status": "running",
            "started_at": started_at_str,
            "start_ts": start_ts,
            "elapsed_s": elapsed_now,
            "model_name": model_name,
            "progress": {
                "current": idx + 1,
                "total": total_cases,
                "current_title": tc.get("titol", f"Test {idx+1}"),
                "pct": round((idx) / total_cases, 2)
            },
            "results": None,
            "error": None
        })
        
        res = run_harness_single_test(tc, api_key=api_key, model_name=model_name, provider=provider)
        results.append(res)
        time.sleep(6.0)
        
    total_duration_s = round(time.time() - start_ts, 1)
    passed_total = sum(1 for r in results if r["exit_global"])
    passed_json = sum(1 for r in results if r["json_valid"])
    passed_seguretat = sum(1 for r in results if r["puntuacio_seguretat"] == 1.0)
    passed_vetos = sum(1 for r in results if r["puntuacio_vetos"] == 1.0)
    passed_eines = sum(1 for r in results if r.get("puntuacio_eines", 1.0) == 1.0)
    passed_dietetic = sum(1 for r in results if r.get("puntuacio_dietetic", 1.0) == 1.0)
    avg_latency = round(sum(r["latencia_s"] for r in results) / total_cases, 2) if total_cases > 0 else 0.0
    
    suite_res = {
        "total_proves": total_cases,
        "proves_superades": passed_total,
        "percentatge_exit": round((passed_total / total_cases) * 100, 1),
        "taxa_json_valid": round((passed_json / total_cases) * 100, 1),
        "taxa_seguretat_alergies": round((passed_seguretat / total_cases) * 100, 1),
        "taxa_desdoblament_vetos": round((passed_vetos / total_cases) * 100, 1),
        "taxa_equipament_forn": round((passed_eines / total_cases) * 100, 1),
        "taxa_control_dietetic": round((passed_dietetic / total_cases) * 100, 1),
        "latencia_mitjana_s": avg_latency,
        "model_avaluat": model_name,
        "durada_total_s": total_duration_s,
        "detall_resultats": results
    }
    
    save_harness_status({
        "status": "completed",
        "started_at": started_at_str,
        "finished_at": datetime.now().strftime("%H:%M:%S (%d/%m/%Y)"),
        "total_duration_s": total_duration_s,
        "model_name": model_name,
        "progress": {
            "current": total_cases,
            "total": total_cases,
            "current_title": "Finalitzat!",
            "pct": 1.0
        },
        "results": suite_res,
        "error": None
    })

def start_harness_suite_background(api_key: str, model_name: str = "gemini-2.5-flash", provider: str = "gemini") -> bool:
    """Inicia la suite en un fil en segon pla (Daemon Thread) si no n'hi ha cap en curs."""
    st_data = get_harness_status()
    if st_data.get("status") == "running":
        return False
        
    th = threading.Thread(target=_harness_background_worker, args=(api_key, model_name, provider), daemon=True)
    th.start()
    return True

def generate_harness_txt_report(data: Dict[str, Any], is_single: bool = False) -> str:
    """Genera un informe exhaustiu en format Text Pla (.txt) a partir dels resultats del benchmarking."""
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = []
    lines.append("================================================================================")
    lines.append("        INFORME D'AVALUACIÓ DEL LABORATORI IA (HARNESS) - XIQUIHOUSE            ")
    lines.append("================================================================================")
    lines.append(f"Data i hora de generacio: {now_str}")
    
    if is_single:
        tc_id = data.get("id", "Cas desconegut")
        titol = data.get("titol", "")
        exit_str = "SUPERAT (PASS)" if data.get("exit_global") else "FALLAT (FAIL)"
        lines.append(f"Tipus d'execucio: Test Individual ({tc_id})")
        lines.append(f"Titol del cas: {titol}")
        lines.append(f"Resultat Global: {exit_str}")
        lines.append(f"Temps de resposta (Latencia): {data.get('latencia_s', 0)} s")
        lines.append("\n--------------------------------------------------------------------------------")
        lines.append("PUNTUACIONS PER CRITERI:")
        lines.append(f"  - Seguretat Medica d'Alergies: {int(data.get('puntuacio_seguretat', 0)*100)}%")
        lines.append(f"  - Gestio de Vetos i Desdoblament: {int(data.get('puntuacio_vetos', 0)*100)}%")
        lines.append(f"  - Frequencies Nutricionals de la Llar: {int(data.get('puntuacio_regles', 0)*100)}%")
        lines.append(f"  - Varietat i Calendari d'Hidrats: {int(data.get('puntuacio_varietat', 0)*100)}%")
        lines.append(f"  - Adaptacio a Eines de Cuina i Forn: {int(data.get('puntuacio_eines', 1)*100)}%")
        lines.append(f"  - Aprofitament d'Estoc de Rebost: {int(data.get('puntuacio_estoc', 1)*100)}%")
        lines.append(f"  - Control Dietètic (Calories/Tags): {int(data.get('puntuacio_dietetic', 1)*100)}%")
        lines.append("--------------------------------------------------------------------------------")
        lines.append("INCIDÈNCIES I INCIDÈNCIES:")
        errors = data.get("errors", [])
        if not errors:
            lines.append("  [OK] Cap incidencia detectada. El model ha complert tots els requisits.")
        else:
            for err in errors:
                lines.append(f"  [ERROR] {err}")
    else:
        model_name = data.get("model_avaluat", "gemini-2.5-flash")
        total_p = data.get("total_proves", 0)
        passats = data.get("proves_superades", 0)
        pct_exit = data.get("percentatge_exit", 0)
        tot_s = float(data.get("durada_total_s", 0))
        dur_txt = f"{int(tot_s//60)}m {int(tot_s%60)}s" if tot_s > 0 else f"{data.get('latencia_mitjana_s', 0)}s / prova"
        
        lines.append(f"Model d'IA Avaluat: {model_name}")
        lines.append(f"Total de Proves Executades: {total_p}")
        lines.append(f"Proves Superades amb Exit: {passats} / {total_p} ({pct_exit}%)")
        lines.append(f"Durada Total del Proces: {dur_txt}")
        lines.append(f"Latencia Mitjana per Prova: {data.get('latencia_mitjana_s', 0)} s")
        lines.append("\n--------------------------------------------------------------------------------")
        lines.append("RESUM DE MÈTRIQUES GLOBALS:")
        lines.append(f"  - Taxa d'Exit Global: {pct_exit}% (Objectiu: 100%)")
        lines.append(f"  - Validesa Estructural JSON: {data.get('taxa_json_valid', 0)}% (Objectiu: 100%)")
        lines.append(f"  - Seguretat Medica d'Alergies: {data.get('taxa_seguretat_alergies', 0)}% (Objectiu: 100%)")
        lines.append(f"  - Desdoblament de Vetos Personals: {data.get('taxa_desdoblament_vetos', 0)}% (Objectiu: 100%)")
        lines.append(f"  - Adaptacio a Eines i Forn: {data.get('taxa_equipament_forn', 0)}% (Objectiu: 100%)")
        lines.append(f"  - Control Dietètic: {data.get('taxa_control_dietetic', 0)}% (Objectiu: 100%)")
        lines.append("--------------------------------------------------------------------------------")
        lines.append("TAULA RESUM DE CASOS DE PROVA:")
        lines.append(f"{'ID':<35} | {'ESTAT':<6} | {'LATÈNCIA':<10} | INCIDÈNCIES")
        lines.append("-" * 80)
        for r in data.get("detall_resultats", []):
            st_icon = "PASS" if r.get("exit_global") else "FAIL"
            err_count = len(r.get("errors", []))
            err_txt = f"{err_count} incidencies" if err_count > 0 else "Cap"
            lines.append(f"{r.get('id', ''):<35} | {st_icon:<6} | {r.get('latencia_s', 0):>6.2f}s   | {err_txt}")
            
        lines.append("\n--------------------------------------------------------------------------------")
        lines.append("DETALL DETALLAT PER CAS DE PROVA:")
        for idx, r in enumerate(data.get("detall_resultats", [])):
            st_str = "SUPERAT" if r.get("exit_global") else "FALLAT"
            lines.append(f"\n[{idx+1}] {r.get('id')}: {r.get('titol')}")
            lines.append(f"    Estat: {st_str} | Latencia: {r.get('latencia_s')}s")
            errs = r.get("errors", [])
            if errs:
                lines.append("    Infraccions detectades:")
                for e in errs:
                    lines.append(f"      - {e}")
            else:
                lines.append("    Compliment: 100% dels criteris i regles de seguretat respectats.")

    lines.append("\n================================================================================")
    lines.append("Informe generat automatitzadament pel Laboratori IA de XiquiHouse.")
    return "\n".join(lines)

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
        lines.append(f"| **Aprofitament d'Estoc de Rebost** | {format_score(data.get('puntuacio_estoc', 1.0))}")
        
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


def build_mise_en_place_prompt(menu_json, receptes_cataleg):
    """
    Genera el prompt per a la IA per a extreure i organitzar la 'Mise en place' d'un menú ja planificat.
    """
    import json
    menu_str = json.dumps(menu_json, indent=2, ensure_ascii=False)
    
    # Recopilar els noms dels plats per incloure només les receptes rellevants i estalviar tokens
    noms_plats = set()
    for dia in menu_json.get("menu_setmanal", []):
        for apat in ["dinar", "sopar"]:
            obj = dia.get(apat, {})
            if obj.get("primer") and obj.get("primer") != "-":
                noms_plats.add(obj.get("primer"))
            if obj.get("segon") and obj.get("segon") != "-":
                noms_plats.add(obj.get("segon"))
            if obj.get("postre") and obj.get("postre") != "-":
                noms_plats.add(obj.get("postre"))
            if obj.get("plat_alternatiu"):
                alt = obj.get("plat_alternatiu")
                if isinstance(alt, dict) and alt.get("plat"):
                    noms_plats.add(alt.get("plat"))
                    
    receptes_filtrades = []
    for r in receptes_cataleg:
        if r.get("titol") in noms_plats:
            receptes_filtrades.append(r)
            
    receptes_str = json.dumps(receptes_filtrades, indent=2, ensure_ascii=False)
    
    prompt = f"""
Ets un xef d'alta cuina expert en "Batch Cooking" i "Mise en place" per a famílies.
El teu objectiu és analitzar un Menú Setmanal ja generat i el detall de les seves receptes, i crear una guia d'organització extremadament pràctica per estalviar temps durant la setmana.

### MENÚ SETMANAL ACTIU:
```json
{menu_str}
```

### RECEPTES ASSOCIADES (amb ingredients i preparació):
```json
{receptes_str}
```

### INSTRUCCIONS DE SORTIDA:
Escriu el resultat EXCLUSIVAMENT en format Markdown (visualment atractiu, usant emojis i llistes).
NO expliquis el menú dia per dia. Has d'AGRUPAR les tasques.

Estructura obligatòria:
1. **🥬 Talls i Preparacions (Mise en place bàsica)**: (Ex: "Ceba: Picar 4 cebes grans perquè es necessiten pel Dilluns (Sofregit) i Dimecres (Paella). Guarda-les en un tàper.")
2. **🍳 Batch Cooking (Cocció prèvia)**: (Ex: "Fes un sofregit base el diumenge per a X i Y", "Bull 4 ous i guarda'ls a la nevera per a les amanides", "Deixa els cigrons en remull la nit abans")
3. **🧊 Marinar i Descongelar**: Quins dies concrets s'ha de treure alguna cosa del congelador per al dia següent.

Sigues directe, pràctic, en català, i no t'inventis ingredients que no estiguin a les receptes o al menú.
Només has de respondre amb el text Markdown de la "Mise en Place".
"""
    return prompt.strip()


def generate_mise_en_place_call(menu_json, receptes_cataleg, model="gemini-2.5-flash"):
    """
    Crida a l'API del LLM per generar la Mise en place a partir del menú actiu.
    """
    from core.api_clients import call_llm
    
    prompt = build_mise_en_place_prompt(menu_json, receptes_cataleg)
    system_prompt = "Ets el millor Xef Organitzador de Batch Cooking del món. La teva sortida ha de ser exclusivament Markdown pràctic."
    
    try:
        raw_response = call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            response_format="text",
            temperature=0.3
        )
        return raw_response
    except Exception as e:
        return f"❌ Error generant la Mise en place: {e}"

