import sys
import os
import json
sys.path.insert(0, 'e:/Dashboard')
import streamlit as st
st.session_state = {'role': 'admin'}
from core.db import get_supabase_client

client = get_supabase_client('admin')
res = client.table('tb_receptes_pro').select('id, titol, ingredients').execute()

local_images = os.listdir('e:/Dashboard/imatges')
local_pngs = [f.split('.')[0] for f in local_images if f.endswith('.png') and f.split('.')[0].isdigit()]

missing = []
for r in res.data:
    if str(r['id']) not in local_pngs:
        missing.append(r)

print(f"Total receptes sense imatge local: {len(missing)}")
for i, m in enumerate(missing[:13]):
    print(f"- ID {m['id']}: {m['titol']}")

with open('pending_13.json', 'w', encoding='utf-8') as f:
    json.dump(missing[:13], f, ensure_ascii=False, indent=2)
