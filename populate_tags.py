import sys
import toml
import time
import json

sys.path.insert(0, 'e:/Dashboard')
from core.db import get_supabase_client
from core.llm import call_llm_api

cfg = toml.load('e:/Dashboard/.streamlit/secrets.toml')
gemini_key = cfg.get('GEMINI_API_KEY')

TAGS_PERMESOS = [
    "peix_blau", "peix_blanc", "carn_blanca", "carn_vermella", "llegums", 
    "verdura_principal", "pasta", "arros", "patata",
    "alt_en_proteina", "lleuger", "ric_en_fibra", "pesat"
]

def estimate_tags_batch(recipes_batch):
    # Formatejem el batch
    text_batch = ""
    for r in recipes_batch:
        text_batch += f"ID: {r['id']} | Títol: {r['titol']} | Ingredients: {r['ingredients']}\n"
        
    prompt = f"""
    Ets un expert nutricionista. Aquí tens una llista de receptes.
    Per cadascuna, tria les etiquetes nutricionals que millor la descriguin, seleccionant-les ÚNICAMENT d'aquesta llista exacta:
    {', '.join(TAGS_PERMESOS)}
    
    RESPON EXCLUSIVAMENT AMB UN JSON (sense markdown) amb el format exacte:
    [
      {{"id": "id_de_la_recepta", "tags": ["tag1", "tag2"]}},
      ...
    ]
    Si no hi ha tags, posa una llista buida.
    
    Receptes:
    {text_batch}
    """
    
    try:
        ok, resp, lat = call_llm_api(prompt, gemini_key, "gemini-2.5-flash", "gemini")
        if ok:
            text = resp.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return data
        else:
            print(f"API Error: {resp}")
    except Exception as e:
        print(f"Error parsing JSON: {e}\nResponse was: {resp}")
    
    return None

def main():
    client = get_supabase_client("admin")
    
    res = client.table("tb_receptes_pro").select("id, titol, ingredients, tags_nutricionals").execute()
    recipes = res.data
    
    recipes_to_update = [r for r in recipes if not r.get("tags_nutricionals") or len(r.get("tags_nutricionals")) == 0]
    
    print(f"S'han trobat {len(recipes_to_update)} receptes sense tags.", flush=True)
    
    # Processar en blocs de 20
    batch_size = 20
    updates = 0
    
    for i in range(0, len(recipes_to_update), batch_size):
        batch = recipes_to_update[i:i+batch_size]
        print(f"Processant batch {i//batch_size + 1}... ({len(batch)} receptes)", flush=True)
        
        results = estimate_tags_batch(batch)
        if results:
            for item in results:
                rec_id = item.get("id")
                raw_tags = item.get("tags", [])
                final_tags = [t for t in raw_tags if t in TAGS_PERMESOS]
                
                if final_tags:
                    client.table("tb_receptes_pro").update({"tags_nutricionals": final_tags}).eq("id", rec_id).execute()
                    updates += 1
                    print(f"  Actualitzada ID {rec_id} -> {final_tags}", flush=True)
                else:
                    client.table("tb_receptes_pro").update({"tags_nutricionals": []}).eq("id", rec_id).execute()
                    
        time.sleep(10) # Pausa entre batches per no excedir quotes de requests per minut
            
    print(f"S'han actualitzat correctament {updates} receptes.", flush=True)

if __name__ == "__main__":
    main()
