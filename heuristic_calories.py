import sys
sys.path.insert(0, 'e:/Dashboard')
from core.db import get_supabase_client
import time

def estimate_heuristic(titol, ingredients):
    t = (str(titol) + " " + str(ingredients)).lower()
    if any(k in t for k in ['arròs', 'pasta', 'espagueti', 'macarron', 'fideuà', 'pizza', 'canelon']):
        return 650
    if any(k in t for k in ['porc', 'vedella', 'bou', 'hamburguesa', 'botifarra']):
        return 550
    if any(k in t for k in ['pollastre', 'gall dindi', 'ànec']):
        return 450
    if any(k in t for k in ['peix', 'salmó', 'lluç', 'orada', 'bacallà', 'calamar', 'sípia']):
        return 400
    if any(k in t for k in ['amanida', 'verdura', 'sopa', 'crema', 'gaspatxo']):
        return 250
    if any(k in t for k in ['postre', 'fruita', 'iogurt', 'maduixa', 'pastís']):
        return 150
    return 450

def main():
    client = get_supabase_client("admin")
    res = client.table("tb_receptes_pro").select("id, titol, ingredients, calories").eq("calories", 0).execute()
    recipes = res.data
    
    print(f"Found {len(recipes)} recipes. Populating with heuristics...", flush=True)
    
    for idx, r in enumerate(recipes):
        cal = estimate_heuristic(r['titol'], r['ingredients'])
        client.table("tb_receptes_pro").update({"calories": cal}).eq("id", r['id']).execute()
        print(f"[{idx+1}/{len(recipes)}] {r['titol']} -> {cal} kcal", flush=True)

if __name__ == "__main__":
    main()
