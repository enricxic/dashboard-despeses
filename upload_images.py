import sys
import uuid
sys.path.insert(0, 'e:/Dashboard')
import streamlit as st
st.session_state = {'role': 'admin'}
from core.db import get_supabase_client

client = get_supabase_client('admin')

images_to_upload = [
    (104, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\rollets_pernil_esparrecs_1790591101725.png"),
    (109, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\tomaquet_cherry_formatge_1790591111148.png"),
    (79, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\tomaquets_farcits_1790591123023.png"),
    (45, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\pizza_verdures_pasta_full_1790591134791.png"),
    (143, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\boquerons_arrebossats_1790591143907.png"),
    (200, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\edamame_1790591162464.png"),
    (164, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\pesols_llagrima_ou_1790591172725.png"),
    (136, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\torreznos_1790591182748.png"),
    (77, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\xipirons_andalusa_1790591194640.png"),
    (144, r"C:\Users\Usuari\.gemini\antigravity\brain\43929060-9ca5-471b-83f7-6900422203fa\bunyols_bacalla_1790591205431.png")
]

for rec_id, path in images_to_upload:
    try:
        with open(path, 'rb') as f:
            file_bytes = f.read()
        file_name = f"{uuid.uuid4()}.png"
        client.storage.from_("imatges-receptes").upload(file_name, file_bytes)
        final_img_url = client.storage.from_("imatges-receptes").get_public_url(file_name)
        
        client.table('tb_receptes_pro').update({"imatge_url": final_img_url}).eq('id', rec_id).execute()
        print(f"✅ Success: Updated Recipe ID {rec_id} with URL {final_img_url}")
    except Exception as e:
        print(f"❌ Error updating Recipe ID {rec_id}: {e}")
