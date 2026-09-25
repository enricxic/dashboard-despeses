import sqlalchemy  
engine = sqlalchemy.create_engine('postgresql://postgres.kqnjiueaaioampvtfwir:D315sh1b23rd**@aws-1-eu-north-1.pooler.supabase.com:6543/postgres')  
with engine.connect() as conn:  
    conn.execute(sqlalchemy.text('ALTER TABLE tb_receptes_pro ADD COLUMN IF NOT EXISTS tags_nutricionals TEXT[];'))  
    conn.commit()  
