import toml
import requests
import uuid
import os

cfg = toml.load('.streamlit/secrets.toml')
SUPABASE_URL = cfg['SUPABASE_URL']
SUPABASE_KEY = cfg['SUPABASE_KEY_PUBLISHABLE']

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

headers_storage = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "image/png"
}

headers_db = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

for rec_id, path in images_to_upload:
    if not os.path.exists(path):
        print(f"❌ File not found for ID {rec_id}: {path}")
        continue

    file_name = f"{uuid.uuid4()}.png"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/imatges-receptes/{file_name}"
    
    with open(path, 'rb') as f:
        file_bytes = f.read()
        
    # 1. Upload Image
    res = requests.post(upload_url, headers=headers_storage, data=file_bytes)
    if res.status_code >= 400:
        print(f"❌ Failed to upload image for ID {rec_id}: {res.text}")
        continue
        
    final_img_url = f"{SUPABASE_URL}/storage/v1/object/public/imatges-receptes/{file_name}"
    
    # 2. Update DB
    db_url = f"{SUPABASE_URL}/rest/v1/tb_receptes_pro?id=eq.{rec_id}"
    res2 = requests.patch(db_url, headers=headers_db, json={"imatge_url": final_img_url})
    
    if res2.status_code >= 400:
        print(f"Failed to update DB for ID {rec_id}: {res2.text}")
    else:
        print(f"Success: Updated Recipe ID {rec_id} with URL {final_img_url}")
