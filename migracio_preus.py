import os
import sys
import pandas as pd
import sqlalchemy

try:
    import streamlit as st
    st.secrets = {} 
except:
    pass

import toml
secrets = toml.load('.streamlit/secrets.toml')
conn_str = secrets['connection_string']

engine = sqlalchemy.create_engine(conn_str)

with engine.connect() as conn:
    print("1. Afegint la columna 'preuUnit' a 'tb_productes'...")
    try:
        conn.execute(sqlalchemy.text('ALTER TABLE "tb_productes" ADD COLUMN "preuUnit" double precision DEFAULT 0.0;'))
        print("Columna afegida correctament.")
    except sqlalchemy.exc.ProgrammingError as e:
        if "already exists" in str(e) or "ja existeix" in str(e):
            print("La columna 'preuUnit' ja existeix. Continuant...")
        else:
            raise e

    print("2. Actualitzant les dades des de 'compresSuper'...")
    # SQL query to get the most recent price from compresSuper for each article and update tb_productes.
    # Note: compresSuper.preuUnit is stored as text, so we cast it to numeric.
    # Sometimes text might contain commas instead of dots, or be empty. We handle basic casting.
    
    update_sql = """
    UPDATE "tb_productes" p
    SET "preuUnit" = sub."preuUnit_num"
    FROM (
        SELECT article, 
               CAST(REPLACE(REPLACE(COALESCE("preuUnit", '0'), ',', '.'), ' ', '') AS double precision) as "preuUnit_num",
               ROW_NUMBER() OVER(PARTITION BY article ORDER BY "IdCompra" DESC) as rn
        FROM "compresSuper"
        WHERE "preuUnit" IS NOT NULL AND "preuUnit" != ''
    ) sub
    WHERE p."nom_estandard" = sub.article AND sub.rn = 1;
    """
    
    res = conn.execute(sqlalchemy.text(update_sql))
    conn.commit()
    print(f"3. Dades actualitzades correctament! Files afectades: {res.rowcount}")
    
print("Procés finalitzat amb èxit.")
