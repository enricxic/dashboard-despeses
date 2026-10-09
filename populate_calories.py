import sys
import toml
sys.path.insert(0, 'e:/Dashboard')
from core.db import get_supabase_client
from core.llm import call_llm_api

# Load config
cfg = toml.load('e:/Dashboard/.streamlit/secrets.toml')
gemini_key = cfg['GEMINI_API_KEY']

def estimate_calories(titol, ingredients):
    prompt = f"""
    Ets un expert nutricionista. 
    Tinc una recepta que es diu "{titol}".
    Els seus ingredients són: {ingredients}.
    Dona'm l'estimació de CALORIES TOTALS per a 1 RACIÓ (1 persona) d'aquest plat.
    RESPON ÚNICAMENT AMB EL NÚMERO ENTER EN KCAL, res més. Per exemple: 450
    """
    try:
        ok, resp, lat = call_llm_api(prompt, gemini_key, "gemini-1.5-flash", "gemini")
        if ok:
            text = resp.strip().replace('kcal', '').replace('Kcal', '').strip()
            # Keep only numbers
            cal_str = ''.join([c for c in text if c.isdigit()])
            if cal_str:
                return int(cal_str)
        return 0
    except Exception as e:
        print(f"Error estimating for {titol}: {e}")
        return 0

def main():
    client = get_supabase_client("admin")
    res = client.table("tb_receptes_pro").select("id, titol, ingredients, calories").eq("calories", 0).execute()
    
    recipes = res.data
    print(f"Found {len(recipes)} recipes without calories.")
    
    updates = 0
    for idx, r in enumerate(recipes):
        cal = estimate_calories(r['titol'], r['ingredients'])
        if cal > 0:
            client.table("tb_receptes_pro").update({"calories": cal}).eq("id", r['id']).execute()
            print(f"[{idx+1}/{len(recipes)}] {r['titol']} -> {cal} kcal")
            updates += 1
        else:
            print(f"[{idx+1}/{len(recipes)}] Failed to estimate for {r['titol']}")
            
    print(f"Finished updating {updates} recipes.")

if __name__ == "__main__":
    main()
