import sys
sys.path.insert(0, 'e:/Dashboard')
from core.db import get_supabase_client
client = get_supabase_client('admin')
res = client.table('tb_receptes_pro').select('id, titol, imatge_url').eq('id', 104).execute()
print(res.data)
