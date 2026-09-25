import pandas as pd  
from sqlalchemy import create_engine  
engine = create_engine('postgresql://postgres.kqnjiueaaioampvtfwir:D315sh1b23rd**@aws-1-eu-north-1.pooler.supabase.com:6543/postgres')  
df = pd.read_sql('SELECT * FROM despeses WHERE \x22ID_mov\x22 > 7095', engine)  
print(df)  
