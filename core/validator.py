import json
from typing import Dict, Any, List

def verify_menu_constraints(menu_json: Dict[str, Any], test_case: Dict[str, Any]) -> List[str]:
    """
    Analitza el JSON generat i retorna una llista d'errors si incompleix regles bàsiques.
    Si retorna una llista buida, vol dir que està tot correcte.
    """
    errors = []
    
    # 1. Extreure vetos familiars actius
    vetos_familiars = {}
    for m in test_case.get("perfil_familia", []):
        if m.get("actiu", True):
            vetos_familiars[m.get("nom")] = [v.lower() for v in m.get("vetos", [])]
            
    # 2. Analitzar cada dia del menú
    dies_planificats = menu_json.get("menu_setmanal", [])
    
    cops_carn_vermella = 0
    cops_peix = 0
    cops_llegums = 0
    
    paraules_carn_vermella = ["vedella", "bou", "hamburguesa", "entrecot", "xulet", "botifarra"]
    paraules_peix = ["peix", "salmó", "lluç", "orada", "tonyina", "llobarro", "rap", "bacallà", "llenguado", "escamarlans", "gambes", "sípia", "calamars", "musclos"]
    paraules_llegums = ["llegum", "cigrons", "llenties", "mongetes blanques", "fesols", "pèsols"]
    plats_cap_de_setmana = ["paella", "fideuà", "canelons", "rostit"]
    
    for dia_info in dies_planificats:
        dia_nom = dia_info.get("dia", "")
        
        for apat_nom in ["dinar", "sopar"]:
            apat = dia_info.get(apat_nom)
            if not apat: continue
            
            plat1 = str(apat.get("primer", "")).lower()
            plat2 = str(apat.get("segon", "")).lower()
            plats_text = f"{plat1} {plat2}"
            ingredients = " ".join([i.lower() for i in apat.get("ingredients_principals", [])])
            text_total = f"{plats_text} {ingredients}"
            
            # Recompte freqüències
            if any(p in text_total for p in paraules_carn_vermella):
                cops_carn_vermella += 1
            if any(p in text_total for p in paraules_peix):
                cops_peix += 1
            if any(p in text_total for p in paraules_llegums):
                cops_llegums += 1
                
            # Cap de setmana vs Setmana
            if dia_nom not in ["Dissabte", "Diumenge"]:
                plats_prohibits = [p for p in plats_cap_de_setmana if p in plats_text]
                if plats_prohibits:
                    errors.append(f"El {dia_nom} per {apat_nom} has posat {', '.join(plats_prohibits)}, que només s'haurien de fer en cap de setmana (Dissabte/Diumenge).")
            
            # Validar plats alternatius innecessaris o erronis
            alt = apat.get("plat_alternatiu")
            if alt and isinstance(alt, dict):
                persona = alt.get("per", "")
                motiu = alt.get("motiu", "").lower()
                
                # Si la persona no existeix o no té aquest veto
                vetos_persona = vetos_familiars.get(persona)
                if vetos_persona is None:
                    errors.append(f"Has creat un plat alternatiu per a {persona} el {dia_nom}, però aquesta persona no està present a la llar.")
                elif not vetos_persona:
                    errors.append(f"Has creat un plat alternatiu per a {persona} el {dia_nom} per motiu '{motiu}', però aquesta persona NO TÉ CAP VETO.")
                else:
                    # Check if the veto ingredient is actually in the main dish
                    veto_trobat_al_plat = False
                    for vp in vetos_persona:
                        if vp in text_total:
                            veto_trobat_al_plat = True
                            break
                    
                    if not veto_trobat_al_plat:
                        # Sometimes the LLM hallucinates a veto. Example: main dish is "Llom", it says veto is "fetge" or invents a veto.
                        vetos_str = ", ".join(vetos_persona)
                        errors.append(f"Has creat un plat alternatiu per a {persona} el {dia_nom} al·legant '{motiu}', però els plats principals ('{plat1}', '{plat2}') NO CONTENEN cap dels seus vetos reals ({vetos_str}). Revisa les dades i no inventis vetos.")

    # 3. Validar límits globals
    regles = test_case.get("regles_llar", {})
    max_carn = regles.get("max_carn_vermella", 1)
    freq_peix = regles.get("freq_peix", regles.get("min_peix", 2))
    min_llegums = regles.get("min_llegums", 2)
    
    if cops_carn_vermella > max_carn:
        errors.append(f"Has posat carn vermella {cops_carn_vermella} cops a la setmana, i el màxim permès és {max_carn}.")
    if cops_peix != freq_peix:
        errors.append(f"Has posat peix {cops_peix} cops a la setmana, i s'ha demanat EXACTAMENT {freq_peix} cops.")
    if cops_llegums < min_llegums:
        errors.append(f"Has posat llegums només {cops_llegums} cops a la setmana, i el mínim obligatori és {min_llegums}.")
        
    return list(set(errors))
