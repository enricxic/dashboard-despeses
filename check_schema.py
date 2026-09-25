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
    print("TB_PRODUCTES columns:")
    res = conn.execute(sqlalchemy.text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tb_productes'"))
    for r in res:
        print(r)
        
    print("\nCOMPRESSUPER columns:")
    res = conn.execute(sqlalchemy.text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'compresSuper'"))
    for r in res:
        print(r)
