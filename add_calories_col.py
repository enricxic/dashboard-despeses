import toml
import psycopg2

try:
    cfg = toml.load('e:/Dashboard/.streamlit/secrets.toml')
    conn_str = cfg['connection_string']
    
    # Establish connection
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Add column if not exists
    cursor.execute("""
        ALTER TABLE tb_receptes_pro 
        ADD COLUMN IF NOT EXISTS calories INTEGER DEFAULT 0;
    """)
    print("Column 'calories' added successfully to tb_receptes_pro.")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
