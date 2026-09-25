import sqlalchemy  
engine = sqlalchemy.create_engine('postgresql://postgres.kqnjiueaaioampvtfwir:D315sh1b23rd**@aws-1-eu-north-1.pooler.supabase.com:6543/postgres')  
with engine.connect() as conn:  
    conn.execute(sqlalchemy.text('ALTER TABLE gasolina RENAME COLUMN "?/l" TO "€/l";'))  
    conn.commit()  
print("Renamed ?/l to €/l successfully!")

