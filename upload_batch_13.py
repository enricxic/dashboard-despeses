import toml
import requests
import uuid
import os

cfg = toml.load('.streamlit/secrets.toml')
SUPABASE_URL = cfg['SUPABASE_URL']
SUPABASE_KEY = cfg['SUPABASE_KEY_PUBLISHABLE']

images_to_upload = [
    (150, r"e:\Dashboard\imatges\150.png"),
    (199, r"e:\Dashboard\imatges\199.png"),
    (181, r"e:\Dashboard\imatges\181.png"),
    (35, r"e:\Dashboard\imatges\35.png"),
    (96, r"e:\Dashboard\imatges\96.png"),
    (40, r"e:\Dashboard\imatges\40.png"),
    (73, r"e:\Dashboard\imatges\73.png"),
    (63, r"e:\Dashboard\imatges\63.png"),
    (201, r"e:\Dashboard\imatges\201.png"),
    (81, r"e:\Dashboard\imatges\81.png"),
    (82, r"e:\Dashboard\imatges\82.png"),
    (83, r"e:\Dashboard\imatges\83.png"),
    (88, r"e:\Dashboard\imatges\88.png")
]

headers_storage = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "image/png"
}

for rec_id, path in images_to_upload:
    if not os.path.exists(path):
        print(f"❌ File not found for ID {rec_id}: {path}")
        continue

    file_name = f"{uuid.uuid4()}.png"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/imatges-receptes/{file_name}"
    
    with open(path, 'rb') as f:
        file_bytes = f.read()
        
    res = requests.post(upload_url, headers=headers_storage, data=file_bytes)
    if res.status_code >= 400:
        print(f"❌ Failed to upload image for ID {rec_id}: {res.text}")
        continue
        
    final_img_url = f"{SUPABASE_URL}/storage/v1/object/public/imatges-receptes/{file_name}"
    
    from core.db import get_supabase_client
    admin_sb = get_supabase_client("admin")
    
    try:
        res2 = admin_sb.table("tb_receptes_pro").update({"imatge_url": final_img_url}).eq("id", rec_id).execute()
        if not res2.data:
            print(f"Failed to update DB for ID {rec_id}: No rows updated")
        else:
            print(f"Success: Updated Recipe ID {rec_id} with URL {final_img_url}")
    except Exception as e:
        print(f"Failed to update DB for ID {rec_id}: {e}")
