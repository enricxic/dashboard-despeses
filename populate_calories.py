import sys
import toml
import requests
import time

sys.path.insert(0, 'e:/Dashboard')
from core.db import get_supabase_client

# Load config
cfg = toml.load('e:/Dashboard/.streamlit/secrets.toml')
or_key = cfg.get('OPENROUTER_API_KEY')

def estimate_calories(titol, ingredients):
    prompt = f"""
    Ets un expert nutricionista. 
    Tinc una recepta que es diu "{titol}".
    Els seus ingredients són: {ingredients}.
    Dona'm l'estimació de CALORIES TOTALS per a 1 RACIÓ (1 persona) d'aquest plat.
    RESPON ÚNICAMENT AMB EL NÚMERO ENTER EN KCAL, res més. Per exemple: 450
    """
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {or_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "google/gemma-2-9b-it:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            content = data.get("choices", [])[0].get("message", {}).get("content", "")
            text = content.strip().replace('kcal', '').replace('Kcal', '').strip()
            cal_str = ''.join([c for c in text if c.isdigit()])
            if cal_str:
                return int(cal_str)
            else:
                print(f"Failed to parse: {content}")
        else:
            print(f"HTTP {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Error: {e}")
    return 0

def main():
    client = get_supabase_client("admin")
    res = client.table("tb_receptes_pro").select("id, titol, ingredients, calories").eq("calories", 0).execute()
    
    recipes = res.data
    print(f"Found {len(recipes)} recipes without calories.", flush=True)
    
    updates = 0
    for idx, r in enumerate(recipes):
        cal = estimate_calories(r['titol'], r['ingredients'])
        if cal > 0:
            client.table("tb_receptes_pro").update({"calories": cal}).eq("id", r['id']).execute()
            print(f"[{idx+1}/{len(recipes)}] {r['titol']} -> {cal} kcal", flush=True)
            updates += 1
        else:
            print(f"[{idx+1}/{len(recipes)}] Failed to estimate for {r['titol']}", flush=True)
        time.sleep(0.5)
            
    print(f"Finished updating {updates} recipes.", flush=True)

if __name__ == "__main__":
    main()
