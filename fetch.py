import httpx  
import json  
url = ''  
key = ''  
with open('.streamlit/secrets.toml', 'r') as f:  
    for line in f:  
        if 'SUPABASE_URL' in line: url = line.split('=')[1].strip().strip('\x22')  
        if 'SUPABASE_KEY_PUBLISHABLE' in line: key = line.split('=')[1].strip().strip('\x22')  
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}  
res = httpx.get(f'{url}/rest/v1/registre_accions?select=*&order=creat_el.desc&limit=5', headers=headers)  
print(res.text)  
res = httpx.get(f'{url}/rest/v1/registre_accions?select=*&limit=10', headers=headers)  
print(res.text)  
