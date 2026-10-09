import sys
import json
sys.path.insert(0, 'e:/Dashboard')
import streamlit as st
st.session_state = {'role': 'admin'}
from core.db import get_supabase_client

client = get_supabase_client('admin')
res = client.table('tb_receptes_pro').select('id, titol, imatge_url, ingredients').execute()

missing = []
for r in res.data:
    url = r.get('imatge_url')
    if not url or str(url).strip() == '' or str(url).strip().lower() == 'null' or str(url).strip() == 'sense imatge':
        missing.append(r)

print(f"Total receptes realment sense imatge a DB: {len(missing)}")
for i, m in enumerate(missing[:13]):
    print(f"- ID {m['id']}: {m['titol']}")

with open('pending_13_real.json', 'w', encoding='utf-8') as f:
    json.dump(missing[:13], f, ensure_ascii=False, indent=2)
