import os
import pandas as pd
from sqlalchemy import create_engine

# Read connection string from secrets.toml
secrets_path = os.path.join(".streamlit", "secrets.toml")
if not os.path.exists(secrets_path):
    raise FileNotFoundError("Could not find .streamlit/secrets.toml")

with open(secrets_path, "r") as f:
    lines = f.readlines()

conn_str = None
for line in lines:
    if line.startswith("connection_string"):
        conn_str = line.split("=")[1].strip().strip('"').strip("'")
        break

if not conn_str:
    raise ValueError("connection_string not found in secrets.toml")

print("Connecting to Supabase...")
engine = create_engine(conn_str)

csv_files = {
    'despeses': 'despeses.csv',
    'ingressos': 'ingressos.csv',
    'compresSuper': 'compresSuper.csv',
    'gasolina': 'gasolina.csv',
    'kmCotxe': 'kmCotxe.csv',
    'hipoteca': 'hipoteca.csv',
    'estalviDP': 'estalviDP.csv',
    'limitsDespeses': 'limitsDespeses.csv',
    'pagaments': 'pagaments.csv'
}

for table_name, csv_name in csv_files.items():
    csv_path = os.path.join("csv", csv_name)
    if os.path.exists(csv_path):
        print(f"Reading {csv_name}...")
        df = pd.read_csv(csv_path, sep=';', encoding='cp850')
        
        # Specific rename for estalviDP before dropping Unnamed columns
        if csv_name == 'estalviDP.csv':
            df = df.rename(columns={
                'Unnamed: 0': 'mes',
                'Unnamed: 1': 'any',
                'Unnamed: 2': 'quota',
                'Unnamed: 5': 'pagat'
            })
        
        # Clean unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Write to PostgreSQL
        print(f"Uploading to Supabase table '{table_name}'...")
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"Uploaded {len(df)} rows.")
    else:
        print(f"Warning: {csv_name} not found, skipping.")

print("Migration completed successfully!")
