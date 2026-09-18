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
    import sqlalchemy
    secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.streamlit', 'secrets.toml'))
    with open(secrets_path, "rb") as f:
        data = tomllib.load(f)
    
    # Try different possible key names from secrets.toml
    key = data.get("SUPABASE_KEY") or data.get("SUPABASE_KEY_PUBLISHABLE") or data.get("SUPABASE_KEY_SECRET")
    url = data.get("SUPABASE_URL")
    conn_str = data.get("connection_string")
    return url, key, conn_str

def main():
    print(f"[{datetime.now()}] Iniciant sincronització silenciada en segon pla...")
    try:
        url, key, conn_str = get_keys()
        supabase = create_client(url, key)
        engine = None
        if conn_str:
            import sqlalchemy
            try:
                engine = sqlalchemy.create_engine(conn_str, connect_args={'connect_timeout': 3})
            except:
                pass
                
        tables_to_fetch = [
            'despeses', 'ingressos', 'compresSuper', 'gasolina', 'kmCotxe',
            'hipoteca', 'tr_cartera', 'estalviDP', 'limitsDespeses', 'pagaments'
        ]
        
        from concurrent.futures import ThreadPoolExecutor
        
        def fetch_and_save(table_name):
            try:
                df = pd.DataFrame()
                if engine is not None:
                    try:
                        df = pd.read_sql(f'SELECT * FROM "{table_name}"', engine)
                    except Exception as e:
                        print(f"PostgreSQL fallback per a {table_name}: {e}")
                
                if df.empty:
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
