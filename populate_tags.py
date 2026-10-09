import sys
import toml
import time
import json

sys.path.insert(0, 'e:/Dashboard')
from core.db import get_supabase_client
from core.llm import call_llm_api

# Load config
cfg = toml.load('e:/Dashboard/.streamlit/secrets.toml')
gemini_key = cfg.get('GEMINI_API_KEY')

# Llista estricta de tags permesos
TAGS_PERMESOS = [
    "peix_blau", "peix_blanc", "carn_blanca", "carn_vermella", "llegums", 
    "verdura_principal", "pasta", "arros", "patata",
    "alt_en_proteina", "lleuger", "ric_en_fibra", "pesat"
]

def estimate_tags(titol, ingredients):
    prompt = f"""
    Ets un expert nutricionista. Tinc una recepta anomenada "{titol}".
    Ingredients: {ingredients}.
    
    Tria les etiquetes nutricionals que millor descriguin aquest plat, seleccionant-les ÚNICAMENT d'aquesta llista exacta:
    {', '.join(TAGS_PERMESOS)}
    
    RESPON ÚNICAMENT AMB ELS TAGS SEPARATS PER COMES, res més.
    Si cap encaixa bé, respon 'Cap'.
    """
    
    try:
        ok, resp, lat = call_llm_api(prompt, gemini_key, "gemini-2.5-flash", "gemini")
        if ok:
            # Process the response to match allowed tags
            raw_tags = [t.strip().lower().replace(" ", "_") for t in resp.split(',')]
            final_tags = [t for t in raw_tags if t in TAGS_PERMESOS]
            return final_tags
        else:
            print(f"API Error: {resp}")
    except Exception as e:
        print(f"Error: {e}")
    
    return []

def main():
    client = get_supabase_client("admin")
    
    # Obtenim receptes que tinguin els tags buits o Null
    res = client.table("tb_receptes_pro").select("id, titol, ingredients, tags_nutricionals").execute()
    recipes = res.data
    
    # Filtrem manualment per seguretat (els camps null o llistes buides)
    recipes_to_update = [r for r in recipes if not r.get("tags_nutricionals") or len(r.get("tags_nutricionals")) == 0]
    
    print(f"S'han trobat {len(recipes_to_update)} receptes sense tags.", flush=True)
    
    updates = 0
    for idx, r in enumerate(recipes_to_update):
        tags = estimate_tags(r['titol'], r['ingredients'])
        
        if tags:
            # Pujem l'array de tags a Supabase (PostgreSQL suporta array de texts)
            client.table("tb_receptes_pro").update({"tags_nutricionals": tags}).eq("id", r['id']).execute()
            print(f"[{idx+1}/{len(recipes_to_update)}] {r['titol']} -> {tags}", flush=True)
            updates += 1
        else:
            print(f"[{idx+1}/{len(recipes_to_update)}] No s'han trobat tags per {r['titol']}", flush=True)
            
        # Donem marge de temps per no col·lapsar la quota (15 segons entre crides per la quota Free de Gemini)
        time.sleep(15)
            
    print(f"S'han actualitzat correctament {updates} receptes.", flush=True)

if __name__ == "__main__":
    main()
