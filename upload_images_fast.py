import toml
import requests
import uuid
import os

cfg = toml.load('.streamlit/secrets.toml')
SUPABASE_URL = cfg['SUPABASE_URL']
SUPABASE_KEY = cfg['SUPABASE_KEY_PUBLISHABLE']

images_to_upload = [
    (50, r"e:\Dashboard\imatges\50.png"),
    (176, r"e:\Dashboard\imatges\176.png"),
    (85, r"e:\Dashboard\imatges\85.png"),
    (163, r"e:\Dashboard\imatges\163.png"),
    (21, r"e:\Dashboard\imatges\21.png"),
    (36, r"e:\Dashboard\imatges\36.png"),
    (46, r"e:\Dashboard\imatges\46.png"),
    (47, r"e:\Dashboard\imatges\47.png"),
    (48, r"e:\Dashboard\imatges\48.png"),
    (212, r"e:\Dashboard\imatges\212.png"),
    (38, r"e:\Dashboard\imatges\38.png"),
    (185, r"e:\Dashboard\imatges\185.png"),
    (128, r"e:\Dashboard\imatges\128.png")
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
