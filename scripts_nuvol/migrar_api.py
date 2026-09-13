import os
import json
import requests
import toml

def get_supabase_creds():
    with open('.streamlit/secrets.toml', 'r', encoding='utf-8') as f:
        secrets = toml.load(f)
    return secrets['SUPABASE_URL'], secrets['SUPABASE_KEY_SECRET']

def migrate_file(filepath, target_id, url, key):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath}, does not exist.")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    payload = {
        "id": target_id,
        "config_json": data
    }
    
    endpoint = f"{url}/rest/v1/app_config"
    resp = requests.post(endpoint, headers=headers, json=payload)
    if resp.status_code in [200, 201]:
        print(f"✅ Success migrating {filepath} to id={target_id}")
    else:
        print(f"❌ Failed migrating {filepath}: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    url, key = get_supabase_creds()
    migrate_file("categories_conceptes.json", 1, url, key)
    migrate_file("core/config.json", 2, url, key)
    migrate_file("data/events.json", 3, url, key)
    migrate_file("data/feeds_cache.json", 4, url, key)
    migrate_file("data/medication_plans.json", 5, url, key)
