import sys, os, re, glob, shutil, uuid
sys.path.insert(0, 'e:/Dashboard')
import toml
import requests
import streamlit as st
st.session_state = {'role': 'admin'}
from core.db import get_supabase_client

ART = r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa"
IDS = [190, 175, 159, 211, 60, 97, 152, 44, 214, 178, 37, 162, 213]

cfg = toml.load('.streamlit/secrets.toml')
URL = cfg['SUPABASE_URL']
KEY = cfg['SUPABASE_KEY_PUBLISHABLE']
headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "image/png"}
admin = get_supabase_client("admin")

for rid in IDS:
    cands = sorted(glob.glob(os.path.join(ART, f"img_{rid}_*.png")))
    if not cands:
        print(f"❌ Sense imatge generada per ID {rid}")
        continue
    local = rf"e:\Dashboard\imatges\Receptes\{rid}.png"
    shutil.copyfile(cands[-1], local)
    name = f"{uuid.uuid4()}.png"
    with open(local, 'rb') as f:
        data = f.read()
    r = requests.post(f"{URL}/storage/v1/object/imatges-receptes/{name}", headers=headers, data=data)
    if r.status_code >= 400:
        print(f"❌ Pujada fallida ID {rid}: {r.text}")
        continue
    public = f"{URL}/storage/v1/object/public/imatges-receptes/{name}"
    res = admin.table("tb_receptes_pro").update({"imatge_url": public}).eq("id", rid).execute()
    print(("✅" if res.data else "⚠️ cap fila actualitzada"), rid, public)
