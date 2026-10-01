import toml
import requests
import uuid
import os

cfg = toml.load('.streamlit/secrets.toml')
SUPABASE_URL = cfg['SUPABASE_URL']
SUPABASE_KEY = cfg['SUPABASE_KEY_PUBLISHABLE']

images_to_upload = [
    (116, r"e:\Dashboard\imatges\116.png"),
    (184, r"e:\Dashboard\imatges\184.png"),
    (53, r"e:\Dashboard\imatges\53.png"),
    (134, r"e:\Dashboard\imatges\134.png"),
    (169, r"e:\Dashboard\imatges\169.png"),
    (55, r"e:\Dashboard\imatges\55.png"),
    (133, r"e:\Dashboard\imatges\133.png"),
    (148, r"e:\Dashboard\imatges\148.png"),
    (64, r"e:\Dashboard\imatges\64.png"),
    (66, r"e:\Dashboard\imatges\66.png"),
    (67, r"e:\Dashboard\imatges\67.png"),
    (68, r"e:\Dashboard\imatges\68.png"),
    (71, r"e:\Dashboard\imatges\71.png")
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
    
    from core.db import get_supabase_client
    admin_sb = get_supabase_client("admin")
    
    # 2. Update DB using admin client to bypass RLS
    try:
        res2 = admin_sb.table("tb_receptes_pro").update({"imatge_url": final_img_url}).eq("id", rec_id).execute()
        if not res2.data:
            print(f"Failed to update DB for ID {rec_id}: No rows updated")
        else:
            print(f"Success: Updated Recipe ID {rec_id} with URL {final_img_url}")
    except Exception as e:
        print(f"Failed to update DB for ID {rec_id}: {e}")
