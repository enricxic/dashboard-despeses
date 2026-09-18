import os
import sys
import pandas as pd
from datetime import datetime

# Assegurar que podem importar core.db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from supabase import create_client
from core.db import fetch_all_supabase

def get_keys():
    import tomllib
    secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml'))
    with open(secrets_path, "rb") as f:
        data = tomllib.load(f)
    return data.get("SUPABASE_URL"), data.get("SUPABASE_KEY")

def main():
    print(f"[{datetime.now()}] Iniciant sincronització silenciada en segon pla...")
    try:
        url, key = get_keys()
        supabase = create_client(url, key)
        tables_to_fetch = [
            'despeses', 'ingressos', 'compresSuper', 'gasolina', 'kmCotxe',
            'hipoteca', 'tr_cartera', 'estalviDP', 'limitsDespeses', 'pagaments'
        ]
        
        from concurrent.futures import ThreadPoolExecutor
        
        def fetch_and_save(table_name):
            try:
                df = fetch_all_supabase(supabase, table_name)
                if not df.empty:
                    os.makedirs("csv", exist_ok=True)
                    csv_path = os.path.join("csv", f"{table_name}.csv")
                    df.to_csv(csv_path, sep=';', index=False)
                    print(f"[{datetime.now()}] CSV local actualitzat per: {table_name}")
            except Exception as e:
                print(f"Error sincronitzant {table_name}: {e}")
                
        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(fetch_and_save, tables_to_fetch)
            
        print(f"[{datetime.now()}] Sincronització en segon pla completada.")
    except Exception as e:
        print(f"Error fatal sincronitzant en segon pla: {e}")

if __name__ == "__main__":
    main()
