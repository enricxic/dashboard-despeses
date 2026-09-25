import sys
sys.path.append('.')
import pandas as pd
import streamlit as st
st.session_state={'role': 'admin'}
from core.db import get_db_engine
engine = get_db_engine()
try:
    df = pd.read_sql('SELECT count(*) FROM "despeses"', engine)
    print("Count in PG:", df.iloc[0,0])
except Exception as e:
    print("Error:", e)
