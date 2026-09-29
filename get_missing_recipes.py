import sys
import json
sys.path.insert(0, 'e:/Dashboard')
import streamlit as st
st.session_state = {'role': 'admin'}
from core.db import get_supabase_client

client = get_supabase_client('admin')
res = client.table('tb_receptes_pro').select('id, titol, imatge_url, ingredients, instruccions').execute()

missing = []
for r in res.data:
    url = r.get('imatge_url')
    if not url or str(url).strip() == '' or str(url).strip().lower() == 'null' or str(url).strip() == 'Sense imatge':
        missing.append(r)

with open('missing_recipes.json', 'w', encoding='utf-8') as f:
    json.dump(missing, f, ensure_ascii=False, indent=2)

print(f"Found {len(missing)} missing recipes.")
