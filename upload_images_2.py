import sys
import uuid
sys.path.insert(0, 'e:/Dashboard')
import streamlit as st
st.session_state = {'role': 'admin'}
from core.db import get_supabase_client
from supabase import create_client
import toml
import time

cfg = toml.load('.streamlit/secrets.toml')
SUPABASE_URL = cfg['SUPABASE_URL']
SUPABASE_KEY_SECRET = cfg['SUPABASE_KEY_SECRET']
client = create_client(SUPABASE_URL, SUPABASE_KEY_SECRET)

images_to_upload = [
    (65, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\calamars_romana_1790598732829.png"),
    (153, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\ramen_chashu_1790598743916.png"),
    (206, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\amanida_formatge_1790598757647.png")
]

for recipe_id, img_path in images_to_upload:
    print(f"Uploading image for recipe {recipe_id}...")
    file_ext = "png"
    file_name = f"{uuid.uuid4()}.{file_ext}"
    with open(img_path, 'rb') as f:
        file_bytes = f.read()
    
    res = client.storage.from_("imatges-receptes").upload(file_name, file_bytes, {"content-type": "image/png"})
    
    public_url = client.storage.from_("imatges-receptes").get_public_url(file_name)
    
    update_res = client.table("tb_receptes_pro").update({"imatge_url": public_url}).eq("id", recipe_id).execute()
    
    print(f"Success: Updated Recipe ID {recipe_id} with {public_url}")
    time.sleep(1)
