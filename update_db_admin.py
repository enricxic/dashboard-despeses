import toml
import requests

cfg = toml.load('.streamlit/secrets.toml')
SUPABASE_URL = cfg['SUPABASE_URL']
SUPABASE_SERVICE_ROLE_KEY = cfg.get('SUPABASE_KEY_SECRET')

if not SUPABASE_SERVICE_ROLE_KEY:
    print("No service role key found. Using publishable key, this might fail due to RLS.")
    SUPABASE_SERVICE_ROLE_KEY = cfg['SUPABASE_KEY_PUBLISHABLE']

headers_db = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"  # Ensure it returns the updated row to confirm
}

updates = {
    104: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/ad60303a-bbbd-4877-aa5b-6a4a4daf2d4c.png",
    109: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/f0b3ee8a-f00f-496f-a4c8-da4cebb52c8e.png",
    79: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/9cf4235a-9d2a-453c-aba8-71208aff54f7.png",
    45: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/9627d29b-d4c0-47fc-a8ef-12f5852d8421.png",
    143: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/54b7f264-ed5a-4a61-961c-091615be59e1.png",
    200: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/92b651b8-93a1-4eae-8472-ec153d590ce1.png",
    164: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/241e377a-d402-4f23-b2c3-5c1e1082d0b0.png",
    136: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/45227a5f-3c25-4795-800c-abe03a9dc193.png",
    77: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/7a3d3284-afbc-4996-b56f-fed83ef2d855.png",
    144: "https://kqnjiueaaioampvtfwir.supabase.co/storage/v1/object/public/imatges-receptes/fb802f4d-f5b9-418b-98a3-913ff6bf5491.png"
}

for rec_id, img_url in updates.items():
    db_url = f"{SUPABASE_URL}/rest/v1/tb_receptes_pro?id=eq.{rec_id}"
    res2 = requests.patch(db_url, headers=headers_db, json={"imatge_url": img_url})
    
    if res2.status_code >= 400:
        print(f"Failed to update DB for ID {rec_id}: {res2.text}")
    else:
        # Check if the row was actually updated
        updated_data = res2.json()
        if len(updated_data) > 0:
            print(f"Success: Updated Recipe ID {rec_id}")
        else:
            print(f"Failed: No rows updated for ID {rec_id}. Check RLS or if ID exists.")
