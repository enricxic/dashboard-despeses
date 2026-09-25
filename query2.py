import sys  
import app  
supabase = app.get_supabase_client('guest')  
res = supabase.table('registre_accions').select('*').order('creat_el', desc=True).limit(5).execute()  
print(res.data)  
