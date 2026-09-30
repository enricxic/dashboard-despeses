import streamlit as st
import scanner
import io
import pandas as pd
import google.generativeai as genai
import json
from supabase import create_client, Client
from core.db import get_config_supers
import numpy as np
import time
import plotly.express as px
import plotly.graph_objects as graph_objects
import os
import hashlib
import re
from datetime import datetime
import pytesseract
from PIL import Image
import difflib

import platform
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"




# Custom styles for premium look (orange/slate dark theme)
st.markdown("""
    <style>
    [data-testid="stElementToolbar"], [data-testid="stDataFrameToolbar"] {
        display: none !important;
    }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 5px 10px;
        text-align: center;
        box-shadow: 0 2px 4px -1px rgb(0 0 0 / 0.1);
        min-width: 125px; /* Increased min-width to support up to 7 digits + € */
        margin: 0 4px; /* Separate cards slightly */
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.8rem; /* Increased font size */
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 2px;
        white-space: nowrap;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.12rem; /* Increased font size */
        font-weight: 700;
        white-space: nowrap;
    }
    .metric-value-red {
        color: #ef4444 !important;
    }
    .metric-value-green {
        color: #22c55e !important;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #f39c12;
        margin-bottom: 20px;
        text-align: center;
    }
    /* Compact Excel-like static table styling */
    div[data-testid="stTable"] table {
        font-size: 0.82rem !important;
    }
    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        padding: 3px 6px !important;
        line-height: 1.15 !important;
    }
    /* Hide Streamlit Menu and Toolbar */
    [data-testid="stHeader"] {
        display: none !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    div.block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
    }
    /* Tighten vertical space */
    [data-testid="stVerticalBlock"] {
        gap: 0.25rem !important;
    }
    [data-testid="column"] {
        padding: 0px 3px !important;
    }
    .stNumberInput, .stTextInput, .stSelectbox, .stCheckbox {
        margin-bottom: 0px !important;
    }
    div.element-container {
        margin-bottom: 1px !important;
    }
    /* Fer la càmera més gran a mòbils */
    div[data-testid="stCameraInput"] {
        min-height: 450px !important;
    }
    div[data-testid="stCameraInput"] video, div[data-testid="stCameraInput"] canvas {
        width: 100% !important;
        min-height: 450px !important;
        object-fit: cover !important;
    }
    /* Hide step buttons inside number inputs */
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    /* Disable default browser spin buttons */
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;\n                        display: flex;\n                        flex-direction: column;\n                        align-items: center;\n                        justify-content: center;\n                        text-align: center;\n                        gap: 2px;
    }
    input[type=number] {
        -moz-appearance: textfield;
    }
    
    /* Hide Streamlit default viewer elements, deploy button and Manage App footer */
    div[data-testid="stAppDeployButton"] {
        display: none !important;
    }
    footer {
        display: none !important;
    }
    .viewerBadge_container__1QS1h, .viewerBadge_link__29513 {
        display: none !important;
    }
    
    /* CSS logic to target st.error container to reduce occupied height/rows */
    div[data-testid="stAlert"] {
        padding: 2px 10px !important;
        margin: 2px auto !important;
    }
    div[data-testid="stAlert"] p {
        margin: 0 !important;
        line-height: 1.2 !important;
    }
    /* Hide Streamlit header, deploy button, and main menu */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    .stDeployButton {
        display: none !important;
    }
    #MainMenu {
        display: none !important;
    }
    /* Safely hide header anchor links without affecting other buttons */
    [data-testid="stHeaderActionElements"],
    a[data-testid="stHeaderActionLink"],
    .stHeading a,
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    div[data-testid="stMarkdownContainer"] a[href^="#"],
    span[data-testid="stHeaderActionElements"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
    </style>
""", unsafe_allow_html=True)



def render(view_mode="economic"):
    from modules.compres import render_compres_super_interface, render_ingres_despesa_general_interface
    # --- Role Indicator ---
    role_icon = "👑" if st.session_state.get("role") == "admin" else ("👁️‍🗨️" if st.session_state.get("role") == "viewer" else "👤")
    role_title = "Administrador" if st.session_state.get("role") == "admin" else ("Visor" if st.session_state.get("role") == "viewer" else "Convidat")
    username_disp = st.session_state.get("username", "Local")
    
    if st.session_state.get("app_theme") == "Clar":
        st.markdown("""<style>
        :root { --background-color: #ffffff !important; --secondary-background-color: #f0f2f6 !important; --text-color: #262730 !important; }
        .stApp { background-color: #ffffff !important; color: #262730 !important; }
        .stAppHeader { background-color: transparent !important; }
        [data-testid='stSidebar'] { background-color: #f0f2f6 !important; }
        h1, h2, h3, h4, h5, h6, p, label { color: #262730 !important; }
        button[kind='secondary'] { background-color: #ffffff !important; color: #262730 !important; border: 1px solid #cccccc !important; }
        div[data-baseweb='select'] > div { background-color: #ffffff !important; color: #262730 !important; border-color: #cccccc !important; }
        div[data-baseweb='popover'] { background-color: #ffffff !important; color: #262730 !important; border-color: #cccccc !important; }
        [data-testid='stPopoverBody'] { background-color: #ffffff !important; color: #262730 !important; border-color: #cccccc !important; }
        div[data-testid='stExpander'] div[role='button'] p { color: #262730 !important; }
        
        .stTextInput>div>div { background-color: #ffffff !important; border-color: #cccccc !important; }
        .stTextInput>div>div>input { color: #262730 !important; -webkit-text-fill-color: #262730 !important; }
        
        .stNumberInput>div>div { background-color: #ffffff !important; border-color: #cccccc !important; }
        .stNumberInput>div>div>input { color: #262730 !important; -webkit-text-fill-color: #262730 !important; }
        
        .stDateInput>div>div { background-color: #ffffff !important; border-color: #cccccc !important; }
        .stDateInput>div>div>input { color: #262730 !important; -webkit-text-fill-color: #262730 !important; }
        
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div { background-color: #ffffff !important; border-color: #cccccc !important; }
        [data-testid="stSelectbox"] div[data-baseweb="select"] span { color: #262730 !important; }
        
        [data-testid='stNumberInputContainer'] { background-color: #ffffff !important; border-color: #cccccc !important; }
        </style>""", unsafe_allow_html=True)
    elif st.session_state.get("app_theme") == "Fosc":
        st.markdown("""<style>
        :root { --background-color: #0f172a !important; --secondary-background-color: #1e293b !important; --text-color: #f8fafc !important; }
        .stApp { background-color: #0f172a !important; color: #f8fafc !important; }
        .stAppHeader { background-color: transparent !important; }
        [data-testid='stSidebar'] { background-color: #1e293b !important; }
        h1, h2, h3, h4, h5, h6, p, label { color: #f8fafc !important; }
        button[kind='secondary'] { background-color: #0f172a !important; color: #f8fafc !important; border: 1px solid #334155 !important; }
        div[data-baseweb='select'] > div { background-color: #0f172a !important; color: #f8fafc !important; border-color: #334155 !important; }
        div[data-baseweb='popover'], div[data-baseweb='popover'] > div { background-color: #0f172a !important; color: #f8fafc !important; border-color: #334155 !important; }
        [data-testid='stPopoverBody'] { background-color: #0f172a !important; color: #f8fafc !important; border-color: #334155 !important; }
        div[data-testid='stExpander'] div[role='button'] p { color: #f8fafc !important; }
        .stTextInput>div>div>input { color: #f8fafc !important; }
        .stNumberInput>div>div>input { color: #f8fafc !important; }
        [data-testid='stNumberInputContainer'] { border-color: #334155 !important; }
        </style>""", unsafe_allow_html=True)
    
    st.markdown(
        f"""
        <style>
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    
    # ----------------- DATA UTILITIES -----------------
    CSV_DIR = "csv"
    
    # Dict of month name translations from Catalan/Spanish CSV inputs to order index
    MONTHS_MAP = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
        'gener': 1, 'febrer': 2, 'març': 3, 'maig': 5, 'juny': 6, 'juliol': 7, 'agost': 8,
        'setembre': 9, 'novembre': 11, 'desembre': 12
    }
    
    CATALAN_MONTHS = [
        'gener', 'febrer', 'març', 'abril', 'maig', 'juny', 
        'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre'
    ]
    
    # Define translations mapping
    month_translations = {
        'gener': 'enero', 'febrer': 'febrero', 'març': 'marzo', 'abril': 'abril', 
        'maig': 'mayo', 'juny': 'junio', 'juliol': 'julio', 'agost': 'agosto', 
        'setembre': 'septiembre', 'octubre': 'octubre', 'novembre': 'noviembre', 'desembre': 'diciembre'
    }
    
    # Account Initial Balances to align with Excel formulas
    INITIAL_BALANCES = {
        'BBVA': -2157.00,  # Adjusted to match real bank balance of 2178.86 (after removing VISA duplicates)
        'La Caixa': 102.28,
        'TRADE REPUB.': 0.0,
        'Casa': 267.28,
        'Tg.Moneder': 0.0,
        'CORTEINGLÉS': 1566.69,
        'Pago VISA': -2995.45  # Calibrated for correct Debt logic (charges increase, payments decrease)
    }
    
    # Bank names in CSV / Supabase mapped to display names
    BANK_MAPPING = {
        'BBVA': 'BBVA',
        'LaCaixa': 'La Caixa',
        'La Caixa': 'La Caixa',
        'TR Cartera': 'TR Cartera',
        'TradeRep.': 'TRADE REPUB.',
        'Trade Repub.': 'TRADE REPUB.',
        'Casa': 'Casa',
        'T.Moneder': 'Tg.Moneder',
        'Tg.Moneder': 'Tg.Moneder',
        'T.CorteInglés': 'CORTEINGLÉS',
        't.CorteInglés': 'CORTEINGLÉS',
        'T.CorteIngles': 'CORTEINGLÉS',
        't.CorteIngles': 'CORTEINGLÉS',
        'CORTEINGLÉS': 'CORTEINGLÉS',
        'Pago VISA': 'Pago VISA'
    }
    
    def clean_numeric(series):
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(0.0)
        
        def parse_val(val):
            if pd.isna(val):
                return 0.0
            val_str = str(val).replace(' €', '').strip()
            if not val_str:
                return 0.0
            try:
                return float(val_str)
            except ValueError:
                pass
            if ',' in val_str:
                val_str = val_str.replace('.', '').replace(',', '.')
            else:
                try:
                    return float(val_str)
                except ValueError:
                    val_str = val_str.replace('.', '')
            try:
                return float(val_str)
            except ValueError:
                return 0.0
                
        return series.apply(parse_val)
    
    def parse_excel_date(val):
        if pd.isna(val):
            return pd.NaT
        try:
            val_f = float(str(val).replace(',', '.'))
            if 30000 < val_f < 60000:
                return pd.to_datetime('1899-12-30') + pd.to_timedelta(val_f, unit='D')
        except ValueError:
            pass
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
            try:
                return pd.to_datetime(str(val).strip(), format=fmt)
            except ValueError:
                continue
        return pd.to_datetime(str(val).strip(), errors='coerce')
    
    
    
    class DBTracker:
        def __init__(self):
            self.last_update = datetime.now()
        def update(self):
            self.last_update = datetime.now()
    
    @st.cache_resource
    @st.cache_resource
    def get_db_engine():
        if "connection_string" in st.secrets:
            try:
                import sqlalchemy
                return sqlalchemy.create_engine(
                    st.secrets["connection_string"],
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=5
                )
            except Exception:
                return None
        return None

    def fetch_table_fast(table_name):
        engine = get_db_engine()
        if engine:
            try:
                with engine.connect() as conn:
                    return table_name, pd.read_sql(f'SELECT * FROM "{table_name}"', conn)
            except Exception:
                pass
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        return table_name, fetch_all_supabase(supabase, table_name)

    def get_db_tracker():
        return DBTracker()
    
    @st.cache_resource
    def get_supabase_client(role: str) -> Client:
        url = st.secrets["SUPABASE_URL"]
        if role == "admin":
            key = st.secrets["SUPABASE_KEY_SECRET"]
        else:
            key = st.secrets["SUPABASE_KEY_PUBLISHABLE"]
        return create_client(url, key)
    
    def fetch_all_supabase(client, table_name):
        data = []
        count = 250
        start = 0
        max_retries = 3
        while True:
            success = False
            for attempt in range(max_retries):
                try:
                    response = client.table(table_name).select("*").range(start, start + count - 1).execute()
                    if response and hasattr(response, 'data') and response.data is not None:
                        data.extend(response.data)
                        if len(response.data) < count:
                            return pd.DataFrame(data)
                        start += count
                        success = True
                        break
                except Exception as e:
                    import time
                    print(f"⚠️ Reintent fetch_all_supabase ({attempt+1}/{max_retries}) per a '{table_name}': {e}")
                    time.sleep(0.4 * (attempt + 1))
            if not success:
                break
        return pd.DataFrame(data)
    
    def get_csv_mtimes():
        # With Supabase, we don't need local file modified times.
        # Return a dummy dict to preserve compatibility with existing signatures.
        return {"db": 1.0}
    
    def fix_mojibake(val):
        if isinstance(val, str):
            try:
                return val.encode('cp850').decode('utf-8')
            except:
                pass
            try:
                return val.encode('latin1').decode('utf-8')
            except:
                pass
        return val
    
    def fix_mojibake_df(df):
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(fix_mojibake)
        return df
    
    # No cache here, relies on core.db global cached functions to prevent Streamlit inner-function cache crash
    def load_dashboard_data(mtimes=None):
        from core.db import _fetch_fast_tables, _fetch_slow_tables
        fetched = {}
        fetched.update(_fetch_fast_tables())
        fetched.update(_fetch_slow_tables())
        
        # Load tables from PostgreSQL
        df_desp = fix_mojibake_df(fetched['despeses'])
        df_desp['ID_mov'] = pd.to_numeric(df_desp['ID_mov'], errors='coerce')
        df_desp = df_desp.dropna(subset=['ID_mov']).sort_values(by='ID_mov', ascending=False).reset_index(drop=True)
        df_desp['import ingrés'] = clean_numeric(df_desp['import ingrés'])
        df_desp['Import càrrec'] = clean_numeric(df_desp['Import càrrec'])
        df_desp['any'] = pd.to_numeric(df_desp['any'], errors='coerce').fillna(2026).astype(int)
        df_desp['parsed_date'] = df_desp['Data'].apply(parse_excel_date)
        if 'mes' in df_desp.columns:
            df_desp['clean_mes'] = df_desp['mes'].astype(str).str.strip().str.lower()
        else:
            df_desp['clean_mes'] = ''
        df_desp['date_score'] = df_desp['any'] * 12 + df_desp['clean_mes'].map(MONTHS_MAP).fillna(12).astype(int)
        
        df_ing = fix_mojibake_df(fetched['ingressos'])
        df_ing['idIngres'] = pd.to_numeric(df_ing['idIngres'], errors='coerce')
        df_ing = df_ing.dropna(subset=['idIngres']).sort_values(by='idIngres', ascending=False).reset_index(drop=True)
        df_ing['Import'] = clean_numeric(df_ing['Import'])
        df_ing['parsed_date'] = df_ing['Data'].apply(parse_excel_date)
        if 'mes' in df_ing.columns:
            df_ing['clean_mes'] = df_ing['mes'].astype(str).str.strip().str.lower()
        else:
            df_ing['clean_mes'] = ''
        
        df_super = fix_mojibake_df(fetched['compresSuper'])
        df_super['IdCompra'] = pd.to_numeric(df_super['IdCompra'], errors='coerce')
        df_super = df_super.dropna(subset=['IdCompra']).sort_values(by='IdCompra', ascending=False).reset_index(drop=True)
        df_super['totLinea'] = clean_numeric(df_super['totLinea'])
        df_super['parsed_date'] = df_super['data'].apply(parse_excel_date)
        
        df_gas = fix_mojibake_df(fetched['gasolina'])
        df_gas = df_gas.rename(columns={'?/l': 'euros/litre', '€/l': 'euros/litre'})
        df_gas['idGasolina'] = pd.to_numeric(df_gas['idGasolina'], errors='coerce')
        df_gas = df_gas.dropna(subset=['idGasolina']).sort_values(by='idGasolina', ascending=False).reset_index(drop=True)
        df_gas['import'] = clean_numeric(df_gas['import'])
        df_gas['litres'] = clean_numeric(df_gas['litres'])
        df_gas['euros/litre'] = clean_numeric(df_gas.get('euros/litre', 0))
        df_gas['parsed_date'] = df_gas['data'].apply(parse_excel_date)
        
        df_km = fix_mojibake_df(fetched['kmCotxe'])
        df_km['idRuta'] = pd.to_numeric(df_km['idRuta'], errors='coerce')
        df_km = df_km.dropna(subset=['idRuta']).sort_values(by='idRuta', ascending=False).reset_index(drop=True)
        df_km['contador'] = clean_numeric(df_km['contador'])
        df_km['km'] = clean_numeric(df_km['km'])
        df_km['parsed_date'] = df_km['data'].apply(parse_excel_date)
        
        df_hip = fetched['hipoteca'].dropna(how='all')
        if 'Quota fixa' in df_hip.columns:
            df_hip = df_hip.dropna(subset=['Quota fixa'])
        df_hip['Quota fixa'] = clean_numeric(df_hip['Quota fixa'])
        
        df_cartera = fix_mojibake_df(fetched['tr_cartera'])
        df_cartera['idTRCartera'] = pd.to_numeric(df_cartera.get('idTRCartera', df_cartera.index), errors='coerce')
        df_cartera = df_cartera.dropna(subset=['idTRCartera']).sort_values(by='idTRCartera', ascending=False).reset_index(drop=True)
        df_cartera['COMPRA'] = clean_numeric(df_cartera.get('COMPRA', 0))
        df_cartera['VENDA'] = clean_numeric(df_cartera.get('VENDA', 0))
        df_cartera['parsed_date'] = df_cartera.get('DATA', pd.Series(dtype=object)).apply(parse_excel_date)
        
        df_est = fetched['estalviDP']
        df_est = df_est.dropna(subset=['mes', 'any'])
        df_est['any'] = pd.to_numeric(df_est['any'], errors='coerce')
        df_est['quota'] = clean_numeric(df_est['quota'])
        if 'aportació' in df_est.columns:
            df_est['aportació'] = clean_numeric(df_est['aportació'])
        if 'rescat' in df_est.columns:
            df_est['rescat'] = clean_numeric(df_est['rescat'])
        if 'pérdua' in df_est.columns:
            df_est['pérdua'] = clean_numeric(df_est['pérdua'])
        
        df_limits = fetched['limitsDespeses'].dropna(subset=['data_inici'])
        df_limits['parsed_date'] = df_limits['data_inici'].apply(parse_excel_date)
        
        df_pag = fetched['pagaments']
        df_pag = df_pag.dropna(subset=['idPago'])
        df_pag['Import'] = clean_numeric(df_pag['Import'])
        df_pag['parsed_date'] = df_pag['Data'].apply(parse_excel_date)
        if 'mes' in df_pag.columns:
            df_pag['clean_mes'] = df_pag['mes'].astype(str).str.strip().str.lower()
        else:
            df_pag['clean_mes'] = ''
        
        return df_desp, df_ing, df_super, df_gas, df_km, df_hip, df_est, df_limits, df_pag, df_cartera
        
    # Monkey-patch clear method so existing code calling load_dashboard_data.clear() still works
    def _clear_dashboard_cache():
        from core.db import _fetch_fast_tables, _fetch_slow_tables
        _fetch_fast_tables.clear()
        _fetch_slow_tables.clear()
    load_dashboard_data.clear = _clear_dashboard_cache
    
    # Load categories_conceptes.json if exists
    import json
    
    @st.cache_data(ttl=600, show_spinner=False)
    def load_categories_conceptes():
        try:
            supabase = get_supabase_client("guest")
            res = supabase.table("app_config").select("config_json").eq("id", 1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["config_json"]
        except Exception as e:
            print("Supabase config load failed:", e)
            pass
    
        # Fallback to local
        filepath = "categories_conceptes.json"
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    cat_config = load_categories_conceptes()
    
    def get_config_categories():
        from core.db import get_config_categories as core_get_cats
        return core_get_cats()
    
    def get_config_concepts(category):
        cfg = load_categories_conceptes()
        concepts = set()
        if cfg and category in cfg:
            concepts.update([c for c in cfg[category] if c])
        if category == "op_banc":
            concepts.update(["Amortització", "Cashback TR", "TR Cashback", "Embargament", "Gestions Banc", "Pago ElCorteInglés", "Pago VISA", "Reintegre Caixer", "Transferència", "Traspàs comptes"])
        if 'df_desp' in locals() and not df_desp.empty and 'Idcategoria' in df_desp.columns and 'Idconcepte' in df_desp.columns:
            desp_c = df_desp[df_desp['Idcategoria'] == category]['Idconcepte'].dropna().unique()
            concepts.update(desp_c)
            
        cleaned_dict = {}
        for c in concepts:
            if c and not str(c).startswith("➕"):
                c_str = str(c).strip()
                if not c_str: continue
                import unicodedata
                norm = unicodedata.normalize('NFKD', c_str).encode('ASCII', 'ignore').decode('utf-8').lower()
                if norm in cleaned_dict:
                    if len(c_str.encode('ascii', 'ignore')) < len(c_str):
                        cleaned_dict[norm] = c_str
                else:
                    cleaned_dict[norm] = c_str
                    
        if "cashback tr" in cleaned_dict and "tr cashback" in cleaned_dict:
            del cleaned_dict["cashback tr"]
            
        return sorted(list(cleaned_dict.values()))
    
    def get_config_banks():
        try:
            from core.config_manager import get_active_bancs
            active_b = get_active_bancs()
            if active_b:
                return [b["nom"] for b in active_b]
        except Exception:
            pass
        if cat_config and "bancs" in cat_config:
            return cat_config["bancs"]
        return list(BANK_MAPPING.keys())
    
    def get_config_payment_methods():
        if cat_config and "formes_pago" in cat_config:
            return [fp for fp in cat_config["formes_pago"] if fp]
        return ["Compte", "Dèbit", "VISA", "Efectiu"]
    
    @st.cache_data(ttl=300)
    def get_tb_supers_cached():
        try:
            supabase = get_supabase_client("guest")
            return fetch_all_supabase(supabase, 'tb_supers')
        except:
            return pd.DataFrame()
    
    def get_config_supers():
        df_supers = get_tb_supers_cached()
        if not df_supers.empty and 'supermercat' in df_supers.columns:
            return sorted(list(df_supers['supermercat'].dropna().unique()))
        if cat_config and "supers_tickets" in cat_config:
            return cat_config["supers_tickets"]
        return sorted(list(df_super['super'].dropna().unique())) if 'super' in df_super.columns else []
    
    @st.cache_data(ttl=300)
    def get_tb_productes_cached():
        try:
            _, df = fetch_table_fast('tb_productes')
            if df is not None and not df.empty:
                return fix_mojibake_df(df)
        except Exception:
            pass
        try:
            supabase = get_supabase_client("guest")
            df = fetch_all_supabase(supabase, 'tb_productes')
            if df is not None and not df.empty:
                return fix_mojibake_df(df)
        except Exception:
            pass
        return pd.DataFrame()
    
    def get_config_families():
        families = set()
        df_prod = get_tb_productes_cached()
        if not df_prod.empty and 'familia' in df_prod.columns:
            families.update([str(f).strip() for f in df_prod['familia'].dropna().unique() if str(f).strip()])
        if cat_config and "families_compres" in cat_config:
            families.update([str(f).strip() for f in cat_config["families_compres"] if str(f).strip()])
        if cat_config and "articles_compres" in cat_config:
            families.update([str(f).strip() for f in cat_config["articles_compres"].keys() if str(f).strip()])
        families.discard('')
        families.discard('nan')
        return sorted(list(families))
    
    def get_config_articles(family):
        if not family:
            return []
        fam_str = str(family).strip().lower()
        articles = set()
        
        df_prod = get_tb_productes_cached()
        if not df_prod.empty and 'familia' in df_prod.columns and 'nom_estandard' in df_prod.columns:
            mask = df_prod['familia'].astype(str).str.strip().str.lower() == fam_str
            matched_arts = df_prod[mask]['nom_estandard'].dropna().unique()
            articles.update([str(a).strip() for a in matched_arts if str(a).strip()])
            
        if cat_config and "articles_compres" in cat_config:
            for k, v in cat_config["articles_compres"].items():
                if str(k).strip().lower() == fam_str and isinstance(v, list):
                    articles.update([str(a).strip() for a in v if str(a).strip()])
                    
        articles.discard('')
        articles.discard('nan')
        return sorted(list(articles))
    def save_to_csv(df, filename):
        import numpy as np
        table_name = filename.replace('.csv', '')
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        try:
            df_clean = df.replace({np.nan: None})
            records = json.loads(df_clean.to_json(orient='records', date_format='iso'))
            chunk_size = 500
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i+chunk_size]
                supabase.table(table_name).upsert(chunk).execute()
                
            st.cache_data.clear()
            get_db_tracker().update()
            st.session_state["last_synced_time"] = get_db_tracker().last_update
            return True
        except Exception as e:
            st.error(f"❌ **Error al desar la taula `{table_name}` a Supabase**: {str(e)}")
            st.stop()
    
    def log_action(table_name, tipus_accio, detalls):
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        try:
            import json
            import numpy as np
            
            # Clean detalls for JSON serialization
            def clean_dict(d):
                if isinstance(d, dict):
                    return {k: clean_dict(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [clean_dict(x) for x in d]
                elif isinstance(d, pd.Timestamp):
                    return d.isoformat()
                elif pd.isna(d):
                    return None
                return d
                
            clean_detalls = clean_dict(detalls)
            
            log_payload = {
                "usuari": st.session_state.get("username", "Desconegut"),
                "rol": st.session_state.get("role", "guest"),
                "taula_afectada": table_name,
                "tipus_accio": tipus_accio,
                "detalls": clean_detalls
            }
            # Log unrestrictedly using anonymous push or admin push (handled by RLS policies)
            supabase.table("registre_accions").insert(log_payload).execute()
        except Exception as e:
            # Silently fail if logging fails
            pass
    
    @st.dialog("🗑️ Paperera de Reciclatge", width="large")
    def show_paperera_modal():
        st.write("Aquesta pantalla et permet recuperar els últims registres esborrats.")
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            res = supabase.table("registre_accions").select("*").eq("tipus_accio", "DELETE").order("id", desc=True).limit(20).execute()
            if not res.data:
                st.info("No hi ha registres esborrats recents.")
                return
                
            for r in res.data:
                import json
                det = r.get("detalls", {})
                if isinstance(det, str):
                    try: det = json.loads(det)
                    except: pass
                
                row_data = det.get("deleted_row") if isinstance(det, dict) else None
                if not row_data:
                    continue
                    
                taula = r.get("taula_afectada", "desconeguda")
                data_esb = r.get("created_at", "")[:16].replace("T", " ")
                usuari = r.get("usuari", "desconegut")
                
                with st.container():
                    c1, c2 = st.columns([8, 2])
                    with c1:
                        st.markdown(f"**{taula.upper()}** (esborrat per {usuari} el {data_esb})")
                        st.json(row_data, expanded=False)
                    with c2:
                        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                        if st.button("♻️ Recuperar", key=f"rec_{r.get('id')}"):
                            try:
                                supabase.table(taula).insert(row_data).execute()
                                log_action(taula, "RESTORE", {"restored_id": r.get("id"), "row": row_data})
                                st.cache_data.clear()
                                get_db_tracker().update()
                                st.session_state["last_synced_time"] = get_db_tracker().last_update
                                st.success("Recuperat correctament! Refrescant...")
                                import time
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    st.divider()
        except Exception as e:
            st.error(f"No s'ha pogut carregar la paperera: {e}")
    
    def update_session_state_insert(table_name, new_row_dict):
        table_map = {
            'despeses': ('df_desp', 'ID_mov'), 'ingressos': ('df_ing', 'idIngres'),
            'compresSuper': ('df_super', 'IdCompra'), 'gasolina': ('df_gas', 'idGasolina'),
            'kmCotxe': ('df_km', 'idRuta'), 'hipoteca': ('df_hip', None),
            'estalviDP': ('df_est', None), 'limitsDespeses': ('df_limits', None),
            'pagaments': ('df_pag', 'idPago'), 'tr_cartera': ('df_cartera', 'idTRCartera')
        }
        if table_name not in table_map: return
        df_key, sort_col = table_map[table_name]
        if df_key in st.session_state:
            df = st.session_state[df_key]
            new_row = new_row_dict.copy()
            for col in df.columns:
                if col in new_row:
                    val = new_row[col]
                    if pd.api.types.is_numeric_dtype(df[col]):
                        try: new_row[col] = pd.to_numeric(val)
                        except: pass
            if 'Data' in new_row and 'parsed_date' in df.columns:
                try: new_row['parsed_date'] = pd.to_datetime(new_row['Data'], format='%d/%m/%Y', errors='coerce')
                except: pass
                
            if df_key == 'df_desp':
                if 'mes' in new_row:
                    new_row['clean_mes'] = str(new_row['mes']).strip().lower()
                else:
                    new_row['clean_mes'] = ''
                
                try:
                    any_val = int(new_row.get('any', 0))
                    mes_idx = int(MONTHS_MAP.get(new_row['clean_mes'], 12))
                    new_row['date_score'] = any_val * 12 + mes_idx
                except:
                    pass
                    
            new_df = pd.DataFrame([new_row])
            updated_df = pd.concat([new_df, df], ignore_index=True)
            if sort_col and sort_col in updated_df.columns:
                updated_df[sort_col] = pd.to_numeric(updated_df[sort_col], errors='coerce')
                updated_df = updated_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
            st.session_state[df_key] = updated_df
    
    def update_session_state_update(table_name, id_col, id_val, update_dict):
        table_map = {
            'despeses': ('df_desp', 'ID_mov'), 'ingressos': ('df_ing', 'idIngres'),
            'compresSuper': ('df_super', 'IdCompra'), 'gasolina': ('df_gas', 'idGasolina'),
            'kmCotxe': ('df_km', 'idRuta'), 'hipoteca': ('df_hip', None),
            'estalviDP': ('df_est', None), 'limitsDespeses': ('df_limits', None),
            'pagaments': ('df_pag', 'idPago'), 'tr_cartera': ('df_cartera', 'idTRCartera')
        }
        if table_name not in table_map: return
        df_key, _ = table_map[table_name]
        if df_key in st.session_state:
            df = st.session_state[df_key]
            if id_col in df.columns:
                mask = df[id_col] == id_val
                if mask.any():
                    for k, v in update_dict.items():
                        if k in df.columns:
                            if pd.api.types.is_numeric_dtype(df[k]):
                                try: v = pd.to_numeric(v)
                                except: pass
                            df.loc[mask, k] = v
                    st.session_state[df_key] = df
    
    def update_session_state_delete(table_name, id_col, id_val):
        table_map = {
            'despeses': 'df_desp', 'ingressos': 'df_ing', 'compresSuper': 'df_super',
            'gasolina': 'df_gas', 'kmCotxe': 'df_km', 'pagaments': 'df_pag', 'tr_cartera': 'df_cartera'
        }
        if table_name not in table_map: return
        df_key = table_map[table_name]
        if df_key in st.session_state:
            df = st.session_state[df_key]
            if id_col in df.columns:
                st.session_state[df_key] = df[df[id_col] != id_val].reset_index(drop=True)
    
    def insert_db_row(table_name, new_row_dict):
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        try:
            supabase.table(table_name).insert(new_row_dict).execute()
            log_action(table_name, 'INSERT', new_row_dict)
            
            update_session_state_insert(table_name, new_row_dict)
            st.cache_data.clear()
            get_db_tracker().update()
            st.session_state["last_synced_time"] = get_db_tracker().last_update
            return True
        except Exception as e:
            st.error(f"❌ Error al desar a Supabase ({table_name}): {str(e)}")
    
    def append_to_db(df_new, table_name, state_key, extra_details=None):
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        try:
            supabase.table(table_name).insert(json.loads(df_new.to_json(orient='records', date_format='iso'))).execute()
            details = {'count': len(df_new)}
            if table_name == 'compresSuper' and 'super' in df_new.columns:
                supers = df_new['super'].unique().tolist()
                details['supermercat'] = supers[0] if len(supers) == 1 else supers
                
            if extra_details:
                details.update(extra_details)
                
            # Also store the fully inserted rows for auditing
            import json
            details['rows_inserted'] = json.loads(df_new.to_json(orient='records', date_format='iso'))
                
            log_action(table_name, 'INSERT_BULK', details)
            
            st.cache_data.clear()
            if state_key and state_key in st.session_state:
                del st.session_state[state_key]
                
            tracker_obj = get_db_tracker()
            tracker_obj.update()
            st.session_state["last_synced_time"] = get_db_tracker().last_update
            load_dashboard_data.clear()
            return True
        except Exception as e:
            st.error(f"❌ **Error a la base de dades (APPEND {table_name})**: {str(e)}")
            return False
    
    def add_concept_to_config(category, concept):
        global cat_config
        if cat_config is None:
            cat_config = {}
        if category not in cat_config:
            cat_config[category] = []
        if concept not in cat_config[category]:
            cat_config[category].append(concept)
            cat_config[category].sort()
            save_categories_conceptes(cat_config)
    
    def get_config_routes(df_km):
        if cat_config and "rutes_cotxe" in cat_config:
            return sorted(cat_config["rutes_cotxe"])
        return sorted(list(df_km['ruta'].dropna().unique()))
    
    def init_routes_config(df_km):
        global cat_config
        if cat_config is None:
            cat_config = {}
        if "rutes_cotxe" not in cat_config:
            cat_config["rutes_cotxe"] = list(df_km['ruta'].dropna().unique())
            cat_config["rutes_cotxe"] = list(df_km['ruta'].dropna().unique())
            save_categories_conceptes(cat_config)
    
    def update_ticket_pendent_db(id_mov, status):
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            supabase.table("despeses").update({"ticketPendent": status}).eq("ID_mov", id_mov).execute()
            if "df_desp" in st.session_state:
                st.session_state["df_desp"].loc[st.session_state["df_desp"]["ID_mov"] == id_mov, "ticketPendent"] = status
        except Exception as e:
            print(f"Error updating ticketPendent for {id_mov}: {e}")
    
    def add_route_to_config(route, df_km):
        init_routes_config(df_km)
        if route not in cat_config["rutes_cotxe"]:
            cat_config["rutes_cotxe"].append(route)
            cat_config["rutes_cotxe"].sort()
            save_categories_conceptes(cat_config)
    
    def add_super_to_config(super_name):
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            supabase.table("tb_supers").insert({"supermercat": super_name}).execute()
            get_tb_supers_cached.clear()
        except Exception as e:
            print("Supabase insert failed for tb_supers:", e)
            
        global cat_config
        if cat_config is None:
            cat_config = {}
        if "supers_tickets" not in cat_config:
            cat_config["supers_tickets"] = []
        if super_name not in cat_config["supers_tickets"]:
            cat_config["supers_tickets"].append(super_name)
            cat_config["supers_tickets"].sort()
            save_categories_conceptes(cat_config)
    
    def save_categories_conceptes(config):
        # Save to Supabase
        try:
            supabase = get_supabase_client("admin")
            supabase.table("app_config").upsert({"id": 1, "config_json": config}).execute()
        except Exception as e:
            print("Supabase config save failed:", e)
            
        # Also save to local fallback
        filepath = "categories_conceptes.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False
    
    
    def delete_db_row(table_name, id_col, id_val):
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        
        # NEW CODE: Fetch deleted row from session_state before deleting
        deleted_row_data = {}
        table_map = {
            'despeses': 'df_desp', 'ingressos': 'df_ing',
            'compresSuper': 'df_super', 'gasolina': 'df_gas',
            'hipoteca': 'df_hip', 'estalviDP': 'df_est',
            'tb_productes': 'df_prod', 'tb_llocs': 'df_llocs',
            'tb_pendents_compra': 'df_pendents',
            'tr_cartera': 'df_tr_cartera'
        }
        df_key = table_map.get(table_name)
        if df_key and df_key in st.session_state:
            import numpy as np
            df = st.session_state[df_key]
            mask = df[id_col] == id_val
            if mask.any():
                row_dict = df[mask].iloc[0].replace({np.nan: None}).to_dict()
                for k, v in row_dict.items():
                    if isinstance(v, pd.Timestamp):
                        row_dict[k] = v.isoformat()
                deleted_row_data = row_dict
    
        try:
            supabase.table(table_name).delete().eq(id_col, id_val).execute()
            
            detalls = {'id_col': id_col, 'id_val': id_val}
            if deleted_row_data:
                detalls['deleted_row'] = deleted_row_data
                
            log_action(table_name, 'DELETE', detalls)
            
            update_session_state_delete(table_name, id_col, id_val)
            st.cache_data.clear()
            get_db_tracker().update()
            st.session_state["last_synced_time"] = get_db_tracker().last_update
            return True
        except Exception as e:
            st.error(f"❌ Error a l'esborrar de Supabase ({table_name}): {str(e)}")
    
    def update_db_row(table_name, id_col, id_val, new_data):
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        
        old_row_data = {}
        table_map = {
            'despeses': 'df_desp', 'ingressos': 'df_ing',
            'compresSuper': 'df_super', 'gasolina': 'df_gas',
            'hipoteca': 'df_hip', 'estalviDP': 'df_est',
            'tb_productes': 'df_prod', 'tb_llocs': 'df_llocs',
            'tb_pendents_compra': 'df_pendents',
            'tr_cartera': 'df_tr_cartera'
        }
        df_key = table_map.get(table_name)
        if df_key and df_key in st.session_state:
            import numpy as np
            df = st.session_state[df_key]
            mask = df[id_col] == id_val
            if mask.any():
                row_dict = df[mask].iloc[0].replace({np.nan: None}).to_dict()
                for k, v in row_dict.items():
                    if isinstance(v, pd.Timestamp):
                        row_dict[k] = v.isoformat()
                old_row_data = row_dict
                
        try:
            update_payload = new_data.copy()
            if id_col in update_payload:
                del update_payload[id_col]
                
            for k, v in update_payload.items():
                if pd.isna(v):
                    update_payload[k] = None
                    
            supabase.table(table_name).update(update_payload).eq(id_col, id_val).execute()
            
            detalls = {'id_col': id_col, 'id_val': id_val, 'changes': update_payload}
            if old_row_data:
                detalls['old_row'] = old_row_data
            log_action(table_name, 'UPDATE', detalls)
            
            update_session_state_update(table_name, id_col, id_val, update_payload)
            st.cache_data.clear()
            get_db_tracker().update()
            st.session_state["last_synced_time"] = get_db_tracker().last_update
            return True
        except Exception as e:
            print(f"FAILED PAYLOAD FOR {table_name}:", update_payload)
            st.error(f"❌ Error a l'actualitzar Supabase ({table_name}): {str(e)}")
    
    required_keys = ["df_desp", "df_ing", "df_super", "df_gas", "df_km", "df_hip", "df_est", "df_limits", "df_pag", "df_cartera"]
    tracker = get_db_tracker()
    needs_init = (
        "dfs_initialized" not in st.session_state 
        or not st.session_state.get("dfs_initialized", False)
        or any(k not in st.session_state for k in required_keys)
        or "last_synced_time" not in st.session_state 
        or not isinstance(st.session_state.get("last_synced_time"), datetime) 
        or st.session_state.get("last_synced_time") < tracker.last_update
        or 'date_score' not in st.session_state.get("df_desp", pd.DataFrame()).columns
    )
    
    if needs_init:
        dfs = load_dashboard_data(get_csv_mtimes())
        st.session_state["df_desp"] = dfs[0]
        st.session_state["df_ing"] = dfs[1]
        st.session_state["df_super"] = dfs[2]
        st.session_state["df_gas"] = dfs[3]
        st.session_state["df_km"] = dfs[4]
        st.session_state["df_hip"] = dfs[5]
        st.session_state["df_est"] = dfs[6]
        st.session_state["df_limits"] = dfs[7]
        st.session_state["df_pag"] = dfs[8]
        if len(dfs) > 9:
            st.session_state["df_cartera"] = dfs[9]
        else:
            st.session_state["df_cartera"] = pd.DataFrame()
        st.session_state["dfs_initialized"] = True
        st.session_state["last_synced_time"] = tracker.last_update
    
    df_desp = st.session_state.get("df_desp", pd.DataFrame())
    df_ing = st.session_state.get("df_ing", pd.DataFrame())
    df_super = st.session_state.get("df_super", pd.DataFrame())
    df_gas = st.session_state.get("df_gas", pd.DataFrame())
    df_km = st.session_state.get("df_km", pd.DataFrame())
    df_hip = st.session_state.get("df_hip", pd.DataFrame())
    df_est = st.session_state.get("df_est", pd.DataFrame())
    df_limits = st.session_state.get("df_limits", pd.DataFrame())
    df_pag = st.session_state.get("df_pag", pd.DataFrame())
    df_cartera = st.session_state.get("df_cartera", pd.DataFrame())
    
    if 'clean_mes' not in df_desp.columns and 'mes' in df_desp.columns:
        df_desp['clean_mes'] = df_desp['mes'].astype(str).str.strip().str.lower()
    if 'clean_mes' not in df_ing.columns and 'mes' in df_ing.columns:
        df_ing['clean_mes'] = df_ing['mes'].astype(str).str.strip().str.lower()
    if 'clean_mes' not in df_pag.columns and 'mes' in df_pag.columns:
        df_pag['clean_mes'] = df_pag['mes'].astype(str).str.strip().str.lower()
    
    def get_limits_for(year, month_name):
        month_idx = MONTHS_MAP.get(month_name.lower(), 12)
        target_date = datetime(year, month_idx, 1)
        
        # Find matching row
        applicable = df_limits[df_limits['parsed_date'] <= target_date]
        if not applicable.empty:
            best_row = applicable.sort_values(by='parsed_date').iloc[-1]
            return {
                'menjar': float(best_row['menjar']),
                'gasolina': float(best_row['gasolina']),
                'restaurant': float(best_row['restaurant']),
                'farmacia': float(best_row['farmacia']),
                'neteja': float(best_row['neteja']),
                'varis': float(best_row['varis'])
            }
        return {'menjar': 500.0, 'gasolina': 140.0, 'restaurant': 220.0, 'farmacia': 25.0, 'neteja': 125.0, 'varis': 120.0}
    
    
    # ----------------- HEADER AREA -----------------
    if "finalize_success" in st.session_state:
        st.toast(st.session_state["finalize_success"], icon="✅")
        del st.session_state["finalize_success"]
    
    col_logo, col_title, col_super = st.columns([0.7, 8.5, 0.8], vertical_alignment="center")
    with col_logo:
        import os, base64
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(root_dir, "imatges", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<img src="data:image/png;base64,{b64}" style="width: 60px;">', unsafe_allow_html=True)
        else:
            st.error(f"Image not found: {logo_path}")
    with col_title:
        title_text = "Dashboard General" if view_mode == "dashboard" else "Mòdul Econòmic"
        st.markdown(f"<h2 style='margin:0; font-size:2.1rem; font-weight:800; color:#f39c12; user-select:none; line-height:1.2;'>{title_text}</h2>", unsafe_allow_html=True)
    with col_super:
        if st.button("🔙 Inici", use_container_width=True, key=f"btn_back_{view_mode}"):
            st.session_state.current_module = None
            st.rerun()
    
    
    
    
    
    # Determine default year/month before the tab runs
    years_list = sorted(list(df_desp['any'].dropna().unique()), reverse=True)
    if 2026 not in years_list:
        years_list.insert(0, 2026)
    
    # Access or default the values
    selected_year = st.session_state.get("detalls_sel_year", st.session_state.get("sel_year", datetime.today().year))
    
    # Default month is current month unless chosen
    current_month_index = datetime.today().month - 1
    selected_month_cat = st.session_state.get("detalls_sel_mes", st.session_state.get("sel_mes", CATALAN_MONTHS[current_month_index]))
    selected_month_data = month_translations.get(selected_month_cat.lower(), month_translations[CATALAN_MONTHS[current_month_index]])
    payment_filter = "Tots"
    
    # ----------------- ACCOUNT BALANCES CALCULATION -----------------
    # Calculate balances for each account from inception up to end of selected month and year
    def show_bank_extract_modal(bank_display_name, selected_year, month_name):
        @st.dialog(f"📋 Extracte {bank_display_name}", width="large")
        def _modal_inner():
            df_desp = st.session_state["df_desp"]
            
            csv_names = [k for k, v in BANK_MAPPING.items() if v == bank_display_name]
            if not csv_names:
                csv_names = [bank_display_name]
            
            st.markdown(f"### Moviments de {bank_display_name} ({selected_year})")
            
            if bank_display_name == 'Pago VISA':
                mask_visa_exp = (df_desp['FormaPago'] == 'VISA')
                mask_visa_pay = (df_desp['Idcategoria'] == 'op_banc') & (df_desp['Idconcepte'] == 'Pago VISA')
                b_desp = df_desp[(mask_visa_exp | mask_visa_pay) & (df_desp['any'] == int(selected_year))].copy()
                # Convert payment's Import càrrec to import ingrés so it reduces the debt!
                is_payment = (b_desp['Idcategoria'] == 'op_banc') & (b_desp['Idconcepte'] == 'Pago VISA')
                b_desp.loc[is_payment, 'import ingrés'] = b_desp.loc[is_payment, 'import ingrés'].fillna(0) + b_desp.loc[is_payment, 'Import càrrec'].fillna(0)
                b_desp.loc[is_payment, 'Import càrrec'] = 0.0
            else:
                b_desp = df_desp[(df_desp['Banc'].isin(csv_names)) & (df_desp['any'] == int(selected_year))].copy()
                # Exclude VISA payments entirely since the bank settlement covers it
                b_desp = b_desp[b_desp['FormaPago'].fillna('') != 'VISA']
                    
            # Calculate starting balance by including EVERYTHING up to Dec 31 of previous year
            prev_target = (int(selected_year) - 1) * 12 + 12
            if bank_display_name == 'Pago VISA':
                mask_visa_exp = (df_desp['FormaPago'] == 'VISA')
                mask_visa_pay = (df_desp['Idcategoria'] == 'op_banc') & (df_desp['Idconcepte'] == 'Pago VISA')
                sub_desp_prev = df_desp[(mask_visa_exp | mask_visa_pay) & (df_desp['date_score'] <= prev_target)].copy()
                is_payment = (sub_desp_prev['Idcategoria'] == 'op_banc') & (sub_desp_prev['Idconcepte'] == 'Pago VISA')
                sub_desp_prev.loc[is_payment, 'import ingrés'] = sub_desp_prev.loc[is_payment, 'import ingrés'].fillna(0) + sub_desp_prev.loc[is_payment, 'Import càrrec'].fillna(0)
                sub_desp_prev.loc[is_payment, 'Import càrrec'] = 0.0
            else:
                sub_desp_prev = df_desp[(df_desp['Banc'].isin(csv_names)) & (df_desp['date_score'] <= prev_target)]
                sub_desp_prev = sub_desp_prev[sub_desp_prev['FormaPago'].fillna('') != 'VISA']
                
            start_bal = INITIAL_BALANCES.get(bank_display_name, 0.0) + sub_desp_prev['import ingrés'].fillna(0).sum() - sub_desp_prev['Import càrrec'].fillna(0).sum()
            
            b_desp = b_desp.sort_values(by=['parsed_date', 'ID_mov'], ascending=[True, True])
            inflows = b_desp['import ingrés'].fillna(0)
            outflows = b_desp['Import càrrec'].fillna(0)
            b_desp['Saldo'] = start_bal + (inflows - outflows).cumsum()
                
            b_desp['Saldo'] = b_desp['Saldo'].round(2)
            b_desp = b_desp.sort_values(by=['parsed_date', 'ID_mov'], ascending=[False, False])
            
            cols_to_show = ['Data', 'Idcategoria', 'Idconcepte', 'import ingrés', 'Import càrrec', 'Saldo', 'Comentari']
            if bank_display_name != 'Pago VISA':
                cols_to_show.append('FormaPago')
                
            b_desp = b_desp[cols_to_show].copy()
            for col in ['import ingrés', 'Import càrrec', 'Saldo']:
                if col in b_desp.columns:
                    b_desp[col] = pd.to_numeric(b_desp[col], errors='coerce')
            for col in ['Data', 'Idcategoria', 'Idconcepte', 'Comentari', 'FormaPago']:
                if col in b_desp.columns:
                    b_desp[col] = b_desp[col].apply(lambda x: str(x) if pd.notna(x) else "")
            
            try:
                st.dataframe(
                    b_desp,
                    use_container_width=True,
                    hide_index=True
                )
            except Exception as e:
                st.error(f"Error rendering b_desp: {e}")
        _modal_inner()
    
    def get_balances_up_to(year, month_name):
        month_idx = MONTHS_MAP.get(month_name, 12)
        
        # Filter despeses up to target date
        target_score = year * 12 + month_idx
        
        sub_desp = df_desp[df_desp['date_score'] <= target_score]
        
        balances = {}
        for csv_name, disp_name in BANK_MAPPING.items():
            # Exclude ALL VISA payments since the total bank settlement is logged manually (e.g. op_banc)
            b_desp = sub_desp[
                (sub_desp['Banc'] == csv_name) & 
                (sub_desp['FormaPago'].fillna('') != 'VISA')
            ]
            inflows = b_desp['import ingrés'].sum()
            outflows = b_desp['Import càrrec'].sum()
            
            # Calculate current net balance with initial offset
            initial = INITIAL_BALANCES.get(disp_name, 0.0)
            balances[disp_name] = balances.get(disp_name, 0.0) + (inflows - outflows)
            
        # Apply initial offset once
        for k in INITIAL_BALANCES:
            balances[k] = balances.get(k, 0.0) + INITIAL_BALANCES[k]
            
        # Account for VISA separately: VISA is a liability card, its balance is cumulative.
        # The debt increases with VISA expenses, and decreases when the bank settlement is recorded (Idconcepte == 'Pago VISA')
        mask_visa_exp = (sub_desp['FormaPago'] == 'VISA')
        mask_visa_pay = (sub_desp['Idcategoria'] == 'op_banc') & (sub_desp['Idconcepte'] == 'Pago VISA')
        
        mask_pure_exp = mask_visa_exp & ~mask_visa_pay
        
        visa_expenses_charges = sub_desp[mask_pure_exp]['Import càrrec'].fillna(0).sum()
        visa_expenses_refunds = sub_desp[mask_pure_exp]['import ingrés'].fillna(0).sum()
        visa_payments = sub_desp[mask_visa_pay]['Import càrrec'].fillna(0).sum() + sub_desp[mask_visa_pay]['import ingrés'].fillna(0).sum()
        balances['Pago VISA'] = INITIAL_BALANCES.get('Pago VISA', 0.0) + visa_payments + visa_expenses_refunds - visa_expenses_charges
        
        # Clean up small negative values that should be zero
        for k in balances:
            if abs(balances[k]) < 0.05:
                balances[k] = 0.0
                
        return balances
    
    current_balances = get_balances_up_to(selected_year, selected_month_data)
    total_accounts_balance = sum(v for k, v in current_balances.items() if k != 'Pago VISA') + current_balances.get('Pago VISA', 0.0)
    
    # ----------------- OIL CHANGE METRICS -----------------
    # Get latest odometer reading
    car_kms_actuals = 0.0
    if not df_km.empty:
        if 'cotxe' in df_km.columns:
            df_km_tivoli = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)]
        else:
            df_km_tivoli = df_km
        if not df_km_tivoli.empty:
            car_kms_actuals = df_km_tivoli.dropna(subset=['contador'])['contador'].iloc[0]
    
    # Make oil change target customizable or saved in session state
    if "kms_canvi_oli" not in st.session_state:
        st.session_state["kms_canvi_oli"] = 31491.0
    
    # ----------------- APP HEADER & BANNER -----------------
    # Header already rendered above
    
    
    # Setup Gemini API if available
    has_gemini = False
    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            # We can test the configuration or just assume it's valid
            has_gemini = True
        except Exception as e:
            st.sidebar.error(f"Error configuring Gemini: {e}")
    
    
    @st.dialog("📋 Inventari Ràpid", width="large")
    def modal_inventari(df_inv):
        st.write("Actualitza ràpidament l'stock agrupat pel lloc on el guardes.")
        
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_llocs = fetch_all_supabase(supabase, 'tb_llocs')
        if not df_llocs.empty:
            df_llocs = df_llocs.sort_values(by='id_lloc')
            llocs_options = df_llocs['nom_lloc'].tolist()
        else:
            llocs_options = ["Sense Assignar"]
        
        # Filter only products that are tracked in Rebost
        if 'select_stock' in df_inv.columns:
            df_inv = df_inv[df_inv['select_stock'] == True].copy()
            
        if df_inv.empty:
            st.warning("No hi ha productes de rebost.")
            return
            
        # Group by lloc
        df_inv['lloc'] = df_inv.get('lloc', 'Sense Assignar').fillna('Sense Assignar')
        df_inv.loc[df_inv['lloc'] == '', 'lloc'] = 'Sense Assignar'
        
        # Track changes
        if "inv_changes" not in st.session_state:
            st.session_state.inv_changes = {}
            
        for lloc, group in df_inv.groupby('lloc'):
            with st.expander(f"📍 {lloc} ({len(group)} productes)", expanded=False):
                # Sort by familia then name
                group = group.sort_values(by=['familia', 'nom_estandard'])
                
                # Prepare data editor df
                cols_to_show = ['familia', 'nom_estandard', 'lloc', 'stock_actual', 'stock_minim']
                df_edit = group[cols_to_show].copy()
                df_edit.set_index(group['idProducte'], inplace=True)
                
                edited_df = st.data_editor(
                    df_edit,
                    use_container_width=True,
                    disabled=['familia', 'nom_estandard'],
                    hide_index=True,
                    column_config={
                        "lloc": st.column_config.SelectboxColumn(
                            "Lloc",
                            help="Tria la ubicació on es guarda el producte",
                            options=llocs_options,
                            required=True
                        )
                    },
                    key=f"editor_inv_{lloc}"
                )
                
                for idx, row in edited_df.iterrows():
                    old_act = df_edit.at[idx, 'stock_actual']
                    new_act = row['stock_actual']
                    old_min = df_edit.at[idx, 'stock_minim']
                    new_min = row['stock_minim']
                    old_loc = df_edit.at[idx, 'lloc']
                    new_loc = row['lloc']
                    
                    if old_act != new_act or old_min != new_min or old_loc != new_loc:
                        st.session_state.inv_changes[idx] = {
                            'stock_actual': new_act,
                            'stock_minim': new_min,
                            'lloc': new_loc if pd.notna(new_loc) else None
                        }
                        
        st.markdown("---")
        if len(st.session_state.inv_changes) > 0:
            st.info(f"Tens {len(st.session_state.inv_changes)} canvis pendents de guardar.")
        else:
            st.write("No has fet canvis.")
            
        if st.button("💾 Guardar Canvis d'Inventari", type="primary", use_container_width=True):
            if len(st.session_state.inv_changes) > 0:
                try:
                    supabase = get_supabase_client(st.session_state.get("role", "guest"))
                    for idx, changes in st.session_state.inv_changes.items():
                        supabase.table('tb_productes').update(changes).eq('idProducte', int(idx)).execute()
                    st.success(f"S'han guardat {len(st.session_state.inv_changes)} canvis correctament!")
                    st.session_state.inv_changes = {}
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error guardant: {e}")
    
    # ----------------- VISTA DASHBOARD GENERAL -----------------
    if view_mode == "dashboard":
        # 1. Container for bank metrics (physically at the top)
        bank_metrics_container = st.container()
        
        # 2. Row of Title and Filters Popover (in place of Juny 2026)
        col_sum_lbl, col_sum_btn = st.columns([11.4, 0.6], vertical_alignment="center")
        with col_sum_lbl:
            st.markdown(f"<h3 style='margin: 14px 0 8px 0; font-size: 1.3rem; color:#f39c12; font-weight:700;'>📅 Resum Mensual d'Ingressos i Despeses {selected_year}</h3>", unsafe_allow_html=True)
        with col_sum_btn:
            with st.popover("🔍", use_container_width=False):
                selected_year = st.selectbox("Any", years_list, index=years_list.index(selected_year) if selected_year in years_list else 0, key="sel_year")
                show_limits = st.checkbox("Veure límits despesa", value=False)
    
        # 3. Re-calculate balances and render bank metrics at the top container
        # Use "desembre" to ensure ALL confirmed real transactions in the DB for the current year are included in the global balance
        current_balances = get_balances_up_to(selected_year, "desembre")
        
        # Explicit required dashboard order:
        # BBVA -> La Caixa -> Trade Repub. -> Casa -> Tg.Moneder -> CORTEINGLÉS -> Pago VISA
        dashboard_bank_order = ['BBVA', 'La Caixa', 'TRADE REPUB.', 'Casa', 'Tg.Moneder', 'CORTEINGLÉS', 'Pago VISA']
        
        try:
            from core.config_manager import get_active_bancs
            active_b = get_active_bancs()
            active_b_names = [BANK_MAPPING.get(b["nom"], b["nom"]).strip().upper() for b in active_b]
        except Exception:
            active_b_names = [b.strip().upper() for b in dashboard_bank_order]
            
        filtered_balances = {k: v for k, v in current_balances.items() if k.strip().upper() in active_b_names and k != 'TR Cartera' and k.strip().upper() != 'EFECTIU'}
        
        ordered_balances = {}
        for b_name in dashboard_bank_order:
            b_upper = b_name.strip().upper()
            for k, v in filtered_balances.items():
                if k.strip().upper() == b_upper:
                    ordered_balances[k] = v
                    break
        for k, v in filtered_balances.items():
            if k not in ordered_balances:
                ordered_balances[k] = v
        current_balances = ordered_balances
        
        total_accounts_balance = sum(v for k, v in current_balances.items() if k != 'Pago VISA') + current_balances.get('Pago VISA', 0.0)
        
        with bank_metrics_container:
            st.markdown("<div style='margin-top: 8px; margin-bottom: 6px;'>", unsafe_allow_html=True)
            col_bal_title, col_bal_metrics = st.columns([1.6, 10.4], vertical_alignment="center")
            with col_bal_title:
                st.markdown(f"<h3 style='margin:0; font-size: 1.15rem; line-height:1.25;'>💰 Saldo Comptes:<br><span style='color: #22c55e; font-size:1.45rem; font-weight:800;'>{total_accounts_balance:,.2f} €</span></h3>", unsafe_allow_html=True)
            with col_bal_metrics:
                # Apply custom styling to the nested horizontal block (the one containing the buttons)
                st.markdown("""
                    <style>
                    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button {
                        border-radius: 8px !important;
                        min-height: 72px !important;
                        min-width: 125px !important;
                        box-shadow: 0 3px 6px -1px rgb(0 0 0 / 0.35) !important;
                        height: 100% !important;
                        padding: 8px 10px !important;
                    }
                    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button:hover {
                        border-color: #f39c12 !important;
                    }
                    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button p {
                        text-transform: uppercase;
                        font-size: 0.82rem;
                        font-weight: 700;
                        line-height: 1.35;
                        margin: 0;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        text-align: center;
                        gap: 3px;
                        white-space: normal !important;
                    }
                    /* Make the green/red/zero value larger */
                    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button p span,
                    div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button p strong {
                        font-size: 1.35rem;
                        text-transform: none;
                        font-weight: 800;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                col_ratios = [1] * len(current_balances)
                cols = st.columns(col_ratios, gap="small")
                for i, (b_name, b_val) in enumerate(current_balances.items()):
                    with cols[i]:
                        if b_val < -0.05:
                            val_str = f":red[**{b_val:,.2f} €**]"
                        elif b_val > 0.05:
                            val_str = f":green[**{b_val:,.2f} €**]"
                        else:
                            val_str = f"**{b_val:,.2f} €**"
                        label = f"{b_name}\n{val_str}"
                        if st.button(label, key=f"btn_bank_{b_name}", use_container_width=True):
                            show_bank_extract_modal(b_name, selected_year, selected_month_data)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Pivot-like summary computation for the selected year
        summary_data = []
        
        # Clean despeses year and month
        df_desp['clean_mes'] = df_desp['mes'].str.lower()
        df_ing['clean_mes'] = df_ing['mes'].str.lower()
        
        # Filter by selected year
        year_desp = df_desp[df_desp['any'] == selected_year]
        year_ing = df_ing[(df_ing['any'] == selected_year) & (df_ing['cobrat'].astype(str).str.lower() == 'cobrat')]
        
        for m_cat in CATALAN_MONTHS:
            m_data = month_translations[m_cat]
            
            # Incomes are calculated EXCLUSIVELY from the despeses (bank) table
            sub_desp = year_desp[year_desp['clean_mes'] == m_data]
            sub_desp_inflows = sub_desp[(sub_desp['Idcategoria'] != 'op_banc') & (sub_desp['grup'] != 'op_banc')]
            
            # Fixed incomes = anything categorized as 'ingres_general' or 'ingrés_general'
            ing_fixes = sub_desp_inflows[sub_desp_inflows['Idcategoria'].isin(['ingres_general', 'ingrés_general'])]['import ingrés'].sum()
            
            # Extra incomes = anything NOT categorized as 'ingres_general' or 'ingrés_general'
            ing_extres = sub_desp_inflows[~sub_desp_inflows['Idcategoria'].isin(['ingres_general', 'ingrés_general'])]['import ingrés'].sum()
            
            ing_total = ing_fixes + ing_extres
    
            
            # Expenses
            sub_desp = year_desp[year_desp['clean_mes'] == m_data]
            sub_desp = sub_desp[(sub_desp['Idcategoria'] != 'op_banc') & (sub_desp['grup'] != 'op_banc')]
            # Grid column mapping logic
            cat_series = sub_desp['Idcategoria'].astype(str)
            
            exp_fixes = sub_desp[cat_series.str.contains('despesa_general|asseguran', case=False, na=False)]['Import càrrec'].sum()
            exp_menjar = sub_desp[cat_series.str.contains('menjar', case=False, na=False)]['Import càrrec'].sum()
            exp_rebost = sub_desp[cat_series.str.contains('rebost', case=False, na=False)]['Import càrrec'].sum()
            exp_gasolina = sub_desp[cat_series.str.contains('gasolina', case=False, na=False)]['Import càrrec'].sum()
            exp_restaurant = sub_desp[cat_series.str.contains('restaurant', case=False, na=False)]['Import càrrec'].sum()
            exp_farmacia = sub_desp[cat_series.str.contains('farmacia|farmàcia', case=False, na=False)]['Import càrrec'].sum()
            exp_neteja = sub_desp[cat_series.str.contains('neteja', case=False, na=False)]['Import càrrec'].sum()
            exp_proveidor = sub_desp[cat_series.str.contains('proveidor', case=False, na=False)]['Import càrrec'].sum()
            
            # Varis column sums all remaining categories
            exp_varis = sub_desp[~cat_series.str.contains(
                'despesa_general|asseguran|menjar|rebost|gasolina|restaurant|farmacia|farmàcia|neteja|proveidor|op_banc|ingres_general|ingrés_general|ingres_extra|ingrés_extra',
                case=False, na=False
            )]['Import càrrec'].sum()
            
            exp_total = exp_fixes + exp_menjar + exp_rebost + exp_gasolina + exp_restaurant + exp_farmacia + exp_neteja + exp_proveidor + exp_varis
            saldo_total = ing_total - exp_total
            
            summary_data.append({
                'Mes': m_cat.capitalize(),
                'Ing. Fixes': ing_fixes,
                'Ing. Extres': ing_extres,
                'Ing. Total': ing_total,
                'Fixes': exp_fixes,
                'Menjar': exp_menjar,
                'Rebost': exp_rebost,
                'Gasolina': exp_gasolina,
                'Restaurant': exp_restaurant,
                'Farmàcia': exp_farmacia,
                'Neteja': exp_neteja,
                'Varis': exp_varis,
                'Proveïdor': exp_proveidor,
                'Total Desp.': exp_total,
                'Saldo': saldo_total
            })
            
        df_summary = pd.DataFrame(summary_data)
        
        # Calculate Totals Row
        totals_row = {'Mes': 'TOTAL'}
        for col in df_summary.columns:
            if col != 'Mes':
                totals_row[col] = df_summary[col].sum()
        df_summary = pd.concat([df_summary, pd.DataFrame([totals_row])], ignore_index=True)
        
        # Check limits for selected month/year to show alert banner
        selected_limits = get_limits_for(selected_year, selected_month_data)
        selected_month_summary = df_summary[df_summary['Mes'].str.lower() == selected_month_cat.lower()]
        if not selected_month_summary.empty:
            m_row = selected_month_summary.iloc[0]
            exceeded_list = []
            col_mapping_alert = {
                'Menjar': ('menjar', 'menjar'),
                'Gasolina': ('gasolina', 'gasolina'),
                'Restaurant': ('restaurant', 'restaurant'),
                'Farmàcia': ('farmàcia', 'farmacia'),
                'Neteja': ('neteja', 'neteja'),
                'Varis': ('varis', 'varis')
            }
            for col_name, (display_lbl, limit_key) in col_mapping_alert.items():
                val = m_row[col_name]
                lim = selected_limits.get(limit_key, float('inf'))
                if val > lim:
                    exceeded_list.append(f"<b>{display_lbl}</b> ({val:,.2f} € > {lim:,.2f} €)")
            if exceeded_list:
                st.markdown(f"<div style='background-color: rgba(239, 68, 68, 0.15); border: 1px solid #ef4444; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;'>⚠️ <b style='color:#ef4444;'>Valor superat:</b> {', '.join(exceeded_list)}</div>", unsafe_allow_html=True)

        if show_limits:
            limits_row = {c: None for c in df_summary.columns}
            limits_row['Mes'] = 'LÍMITS'
            for col_name, (display_lbl, limit_key) in col_mapping_alert.items():
                if limit_key in selected_limits:
                    limits_row[col_name] = selected_limits[limit_key]
            df_summary = pd.concat([pd.DataFrame([limits_row]), df_summary], ignore_index=True)
    
        def get_saldo_gradient_rgb(val):
            v = max(-1000.0, min(1000.0, float(val)))
            norm = (v + 1000.0) / 2000.0
            if norm < 0.5:
                ratio = norm / 0.5
                r = int(215 + (254 - 215) * ratio)
                g = int(48 + (224 - 48) * ratio)
                b = int(39 + (139 - 39) * ratio)
            else:
                ratio = (norm - 0.5) / 0.5
                r = int(254 + (26 - 254) * ratio)
                g = int(224 + (152 - 224) * ratio)
                b = int(139 + (80 - 139) * ratio)
            return f"rgb({r},{g},{b})"

        def generate_fast_summary_table_html(df):
            non_total_df = df[~df['Mes'].isin(['TOTAL', 'LÍMITS'])]
            max_ing = non_total_df['Ing. Total'].max() if 'Ing. Total' in non_total_df.columns and not non_total_df.empty else None
            max_desp = non_total_df['Total Desp.'].max() if 'Total Desp.' in non_total_df.columns and not non_total_df.empty else None

            col_limits_keys = {
                'Menjar': 'menjar', 'Gasolina': 'gasolina', 'Restaurant': 'restaurant',
                'Farmàcia': 'farmacia', 'Neteja': 'neteja', 'Varis': 'varis'
            }

            rows_html = []
            for _, row in df.iterrows():
                mes_val = str(row['Mes'])
                is_total = mes_val == 'TOTAL'
                is_limits = mes_val == 'LÍMITS'
                is_cur_month = mes_val.lower() == selected_month_cat.lower()
                
                m_data = month_translations.get(mes_val.lower(), 'enero')
                row_limits = get_limits_for(selected_year, m_data) if not is_total and not is_limits else {}

                tr_style = ""
                if is_limits:
                    tr_style = 'color: #3498db; font-weight: bold; background-color: rgba(52, 152, 219, 0.1);'
                elif is_total:
                    tr_style = 'font-weight: bold; border-top: 2px solid #555;'

                cells_html = []
                for col in df.columns:
                    val = row[col]
                    td_style = []
                    
                    if col == 'Mes':
                        if is_cur_month:
                            td_style.append('color: #f1c40f; font-weight: bold;')
                        td_style.append('text-align: left; font-weight: bold;')
                        formatted = mes_val
                    else:
                        td_style.append('text-align: right;')
                        if pd.isna(val) or val == "":
                            formatted = ""
                        else:
                            try:
                                v_num = float(val)
                                formatted = f"{v_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                                
                                if col == 'Saldo' and not is_limits:
                                    bg = get_saldo_gradient_rgb(v_num)
                                    td_style.append(f'background-color: {bg}; color: #000000 !important; font-weight: bold;')
                                
                                if is_total:
                                    if col == 'Ing. Total':
                                        td_style.append('background-color: #27ae60; color: white; font-weight: bold;')
                                    elif col == 'Total Desp.':
                                        td_style.append('background-color: #c0392b; color: white; font-weight: bold;')
                                elif not is_limits:
                                    if col in col_limits_keys:
                                        lim = row_limits.get(col_limits_keys[col], float('inf'))
                                        if v_num > lim:
                                            td_style.append('background-color: #7f1d1d; color: #fecaca; font-weight: bold;')
                            except (ValueError, TypeError):
                                formatted = str(val)

                    style_str = f' style="padding: 2px 3px; border-bottom: 1px solid #333; {" ".join(td_style)}"'
                    cells_html.append(f'<td{style_str}>{formatted}</td>')

                tr_style_str = f' style="{tr_style}"' if tr_style else ''
                rows_html.append(f'<tr{tr_style_str}>{"".join(cells_html)}</tr>')

            headers_html = "".join([f'<th style="padding: 2px 3px; text-align: {"left" if c == "Mes" else "center"}; border-bottom: 1px solid #333; font-weight: bold; color: #bbb;">{c}</th>' for c in df.columns])
            return f'<table style="width:100%; border-collapse:collapse; font-size:0.85em;"><thead><tr>{headers_html}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'

        html_table = generate_fast_summary_table_html(df_summary)
        
        st.markdown(
            f"""<style>
    .custom-summary-table table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85em;
    }}
    .custom-summary-table th, .custom-summary-table td {{
        padding: 2px 3px;
        text-align: right;
        border-bottom: 1px solid #333;
    }}
    .custom-summary-table th {{
        text-align: center;
        font-weight: bold;
        color: #bbb;
    }}
    .custom-summary-table td:first-child {{
        font-weight: bold;
        text-align: left;
    }}
    .custom-summary-table tbody tr td:last-child {{
        color: #000000 !important;
        font-weight: bold !important;
    }}
    </style>
<div class="custom-summary-table">
{html_table}
</div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<div style='margin-top: 55px;'></div>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#f39c12; margin-top: 10px; margin-bottom: 8px; font-size:1.35rem; font-weight:700;'>📈 Previsió ingressos/despeses</h3>", unsafe_allow_html=True)
        # Calculate past average expense from operated months in selected_year
        past_expenses = []
        for m_cat in CATALAN_MONTHS:
            m_data = month_translations[m_cat]
            sub_desp_test = df_desp[(df_desp['any'] == selected_year) & (df_desp['clean_mes'] == m_data)]
            sub_desp_test = sub_desp_test[(sub_desp_test['Idcategoria'] != 'op_banc') & (sub_desp_test['grup'] != 'op_banc')]
            cat_series_test = sub_desp_test['Idcategoria'].astype(str)
            exp_val = sub_desp_test[~cat_series_test.str.contains('op_banc|ingres_general|ingrés_general|ingres_extra|ingrés_extra', case=False, na=False)]['Import càrrec'].sum()
            if exp_val > 100:
                past_expenses.append(exp_val)
        avg_monthly_expense = float(np.mean(past_expenses)) if past_expenses else 3100.0

        today = datetime.today()
        cur_year = today.year
        cur_month_idx = today.month - 1

        chart_data = []
        for yr in [selected_year - 1, selected_year]:
            year_desp_c = df_desp[df_desp['any'] == yr]
            year_ing_c = df_ing[df_ing['any'] == yr]
            
            for m_idx, m_cat in enumerate(CATALAN_MONTHS):
                m_data = month_translations[m_cat]
                
                # Check real expenses
                sub_desp = year_desp_c[year_desp_c['clean_mes'] == m_data]
                sub_desp_inflows = sub_desp[(sub_desp['Idcategoria'] != 'op_banc') & (sub_desp['grup'] != 'op_banc')]
                cat_series = sub_desp_inflows['Idcategoria'].astype(str)
                exp_real = sub_desp_inflows[~cat_series.str.contains('op_banc|ingres_general|ingrés_general|ingres_extra|ingrés_extra', case=False, na=False)]['Import càrrec'].sum()
                
                # Check real incomes
                ing_real = sub_desp_inflows[sub_desp_inflows['Idcategoria'].isin(['ingres_general', 'ingrés_general', 'ingres_extra', 'ingrés_extra'])]['import ingrés'].sum()
                if ing_real == 0:
                    sub_ing_c = year_ing_c[(year_ing_c['clean_mes'] == m_data) & (year_ing_c['cobrat'].astype(str).str.lower() == 'cobrat')]
                    ing_real = sub_ing_c['Import'].sum()
                
                # Determine time frame: past, current month, or future
                is_past = (yr < cur_year) or (yr == cur_year and m_idx < cur_month_idx)
                is_current = (yr == cur_year and m_idx == cur_month_idx)
                
                if is_past:
                    ing_val = ing_real
                    ing_color = '#2ecc71'  # Verd real
                    ing_hover = f"🟢 Ingressos reals: <b>{ing_val:,.2f} €</b>"
                    
                    exp_real_val = exp_real
                    exp_prev_val = 0.0
                    exp_real_hover = f"🔴 Despeses reals: <b>{exp_real_val:,.2f} €</b>"
                    exp_prev_hover = ""
                    exp_real_hoverinfo = 'all'
                    exp_prev_hoverinfo = 'skip'
                elif is_current:
                    sub_ing_all = year_ing_c[year_ing_c['clean_mes'] == m_data]
                    ing_val = max(ing_real, sub_ing_all['Import'].sum())
                    if ing_val == 0:
                        ing_val = 2850.0
                    ing_color = '#f1c40f'  # Groc previsió
                    ing_hover = f"🟡 Ingressos (Previsió): <b>{ing_val:,.2f} €</b>"
                    
                    exp_real_val = exp_real
                    exp_target = avg_monthly_expense if avg_monthly_expense > exp_real else exp_real
                    exp_prev_val = max(0.0, exp_target - exp_real_val)
                    
                    exp_real_hover = f"🔴 Gastat fins ara: <b>{exp_real_val:,.2f} €</b>"
                    total_cur_exp = exp_real_val + exp_prev_val
                    exp_prev_hover = f"🔻 Previsió restant: <b>{exp_prev_val:,.2f} €</b> (Total: <b>{total_cur_exp:,.2f} €</b>)"
                    exp_real_hoverinfo = 'all'
                    exp_prev_hoverinfo = 'all' if exp_prev_val > 0 else 'skip'
                else:  # Future month
                    sub_ing_all = year_ing_c[year_ing_c['clean_mes'] == m_data]
                    ing_val = sub_ing_all['Import'].sum()
                    if ing_val == 0:
                        ing_val = 2850.0
                    ing_color = '#f1c40f'  # Groc previsió
                    ing_hover = f"🟡 Ingressos (Previsió): <b>{ing_val:,.2f} €</b>"
                    
                    exp_real_val = 0.0
                    exp_prev_val = avg_monthly_expense
                    exp_real_hover = ""
                    exp_prev_hover = f"🔻 Despeses (Previsió): <b>{exp_prev_val:,.2f} €</b>"
                    exp_real_hoverinfo = 'skip'
                    exp_prev_hoverinfo = 'all'
                
                chart_data.append({
                    'Mes-Any': f"{m_cat.capitalize()[:3]} {str(yr)[2:]}",
                    'Ingressos': ing_val,
                    'Despeses_Real': exp_real_val,
                    'Despeses_Prev': exp_prev_val,
                    'Ing_Color': ing_color,
                    'Ing_Hover': ing_hover,
                    'Exp_Real_Hover': exp_real_hover,
                    'Exp_Prev_Hover': exp_prev_hover,
                    'Exp_Real_HoverInfo': exp_real_hoverinfo,
                    'Exp_Prev_HoverInfo': exp_prev_hoverinfo
                })
        df_chart_2yrs = pd.DataFrame(chart_data)
        
        fig_bar = graph_objects.Figure()
        fig_bar.add_trace(graph_objects.Bar(
            x=df_chart_2yrs['Mes-Any'],
            y=df_chart_2yrs['Ingressos'],
            name='Ingressos (Reals 🟢 / Previsió 🟡)',
            offsetgroup='1',
            marker_color=df_chart_2yrs['Ing_Color'],
            customdata=df_chart_2yrs['Ing_Hover'],
            hovertemplate='%{customdata}<extra></extra>'
        ))
        fig_bar.add_trace(graph_objects.Bar(
            x=df_chart_2yrs['Mes-Any'],
            y=df_chart_2yrs['Despeses_Real'],
            name='Despeses (Gastat / Reals 🔴)',
            offsetgroup='2',
            marker_color='#e74c3c',
            customdata=df_chart_2yrs['Exp_Real_Hover'],
            hoverinfo=df_chart_2yrs['Exp_Real_HoverInfo'].tolist(),
            hovertemplate='%{customdata}<extra></extra>'
        ))
        fig_bar.add_trace(graph_objects.Bar(
            x=df_chart_2yrs['Mes-Any'],
            y=df_chart_2yrs['Despeses_Prev'],
            name='Despeses (Previsió / Restant 🔻)',
            offsetgroup='2',
            marker_color='#7f1d1d',
            customdata=df_chart_2yrs['Exp_Prev_Hover'],
            hoverinfo=df_chart_2yrs['Exp_Prev_HoverInfo'].tolist(),
            hovertemplate='%{customdata}<extra></extra>'
        ))
        fig_bar.update_layout(
            barmode='relative',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc', size=12),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='#1e293b',
                bordercolor='#334155',
                font_size=13,
                font_family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
            ),
            xaxis=dict(gridcolor='#334155', tickangle=-45),
            yaxis=dict(
                gridcolor='#334155',
                dtick=1000,
                tick0=0,
                tickformat=',.0f',
                ticksuffix=' €'
            ),
            margin=dict(t=20, b=30, l=10, r=10),
            height=460,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
        st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

        # ================= PESTANYA 1 ECONÒMIC: DETALLS DEL MES =================
    
        @st.dialog("⚙️ Confirmar Operacions i Bancs", width="large")
        def dialog_confirmar_operacions(pagaments_sel, ingressos_sel, any_val, mes_cat):
            st.write("Verifica els imports i bancs de les operacions seleccionades. Si a alguna li falta el banc, pots assignar-lo aquí mateix al vol.")
            
            from core.db import get_config_banks
            bancs_disp = get_config_banks()
            if not bancs_disp:
                bancs_disp = ["BBVA", "Sabadell", "TR Cartera", "Revolut", "Efectiu"]
        
            results = {}
        
            if pagaments_sel:
                st.markdown("#### 🔴 Pagaments a processar")
                for p in pagaments_sel:
                    idx = p['idx']
                    row = p['row']
                    amt = float(row.get('Import', 0.0))
                    banc = str(row.get('Banc', '')).strip()
                    forma_pago = str(row.get('Formapago', row.get('FormaPago', ''))).strip()
                    if not forma_pago:
                        forma_pago = "Compte"
                
                    col_info, col_banc = st.columns([0.65, 0.35], vertical_alignment="center")
                    with col_info:
                        st.markdown(f"**{row.get('Concepte', 'Pagament')}**<br><span style='font-size:1.1em;'>{amt:.2f} €</span>", unsafe_allow_html=True)
                    
                    with col_banc:
                        if not banc or banc.lower() == 'nan':
                            nou_banc = st.selectbox("Assigna Banc:", [""] + bancs_disp, key=f"sel_banc_pag_{idx}")
                            banc_final = nou_banc
                        else:
                            st.markdown(f"<div style='padding-top:10px;'>➡️ **{banc}**</div>", unsafe_allow_html=True)
                            banc_final = banc
                
                    results[f"pag_{idx}"] = {'type': 'pagament', 'idx': idx, 'row': row, 'banc': banc_final, 'forma_pago': forma_pago, 'import_final': amt}
                st.divider()
                
            if ingressos_sel:
                st.markdown("#### 🟢 Ingressos a processar")
                for i in ingressos_sel:
                    idx = i['idx']
                    row = i['row']
                    amt = float(row.get('Import', 0.0))
                    banc = str(row.get('Banc', '')).strip()
                    forma_pago = str(row.get('Formapago', row.get('FormaPago', ''))).strip()
                    if not forma_pago:
                        forma_pago = "Compte"
                
                    col_info, col_banc = st.columns([0.65, 0.35], vertical_alignment="center")
                    with col_info:
                        st.markdown(f"**{row.get('Concepte', 'Ingrés')}**<br><span style='font-size:1.1em;'>{amt:.2f} €</span>", unsafe_allow_html=True)
                    
                    with col_banc:
                        if not banc or banc.lower() == 'nan':
                            nou_banc = st.selectbox("Assigna Banc:", [""] + bancs_disp, key=f"sel_banc_ing_{idx}")
                            banc_final = nou_banc
                        else:
                            st.markdown(f"<div style='padding-top:10px;'>➡️ **{banc}**</div>", unsafe_allow_html=True)
                            banc_final = banc
                
                    results[f"ing_{idx}"] = {'type': 'ingres', 'idx': idx, 'row': row, 'banc': banc_final, 'forma_pago': forma_pago, 'import_final': amt}
                st.divider()
                
            if st.button("✅ Confirmar i Desar a BBDD", type="primary", use_container_width=True):
                df_desp_local = st.session_state["df_desp"]
                max_id = int(df_desp_local['ID_mov'].max()) if not df_desp_local.empty else 0
            
                df_pag_local = st.session_state["df_pag"]
                df_ing_local = st.session_state["df_ing"]
            
                avui = datetime.now().strftime("%d/%m/%Y")
            
                updates_made = False
                for key, res in results.items():
                    if not res['banc']:
                        st.error(f"⚠️ Si us plau, assigna un Banc per a l'operació: **{res['row'].get('Concepte', '')}** utilitzant els desplegables de més amunt.")
                        return
                    
                    max_id += 1
                    if res['type'] == 'pagament':
                        if res['idx'] == 'hipoteca':
                            df_hip_local = st.session_state["df_hip"]
                            df_hip_local.loc[(df_hip_local['any'] == any_val) & (df_hip_local['mes'].str.lower() == selected_month_data), 'pagat'] = 'pagat'
                            df_hip_local.loc[(df_hip_local['any'] == any_val) & (df_hip_local['mes'].str.lower() == selected_month_data), 'Quota fixa'] = float(res['import_final'])
                            save_to_csv(df_hip_local, 'hipoteca.csv')
                            st.session_state["df_hip"] = df_hip_local
                        else:
                            df_pag_local.loc[res['idx'], 'pagat'] = 'Pagat'
                            df_pag_local.loc[res['idx'], 'Import'] = float(res['import_final'])
                        
                        new_row = {
                            'ID_mov': int(max_id),
                            'Data': avui,
                            'Banc': str(res['banc']),
                            'FormaPago': str(res['forma_pago']),
                            'Idcategoria': str(res['row'].get('Categoria', 'despesa_general')),
                            'Idconcepte': str(res['row']['Concepte']),
                            'Import càrrec': float(res['import_final']),
                            'import ingrés': 0.0,
                            'Comentari': None,
                            'mes': month_translations.get(mes_cat.lower(), mes_cat.lower()),
                            'any': int(any_val),
                            'grup': "Càrrec",
                            'ticketPendent': False
                        }
                        insert_db_row('despeses', new_row)
                    
                        # Check for scheduled transfers
                        banc_desti = None
                        if 'banc_desti_traspas' in df_pag_local.columns and res['idx'] in df_pag_local.index:
                            banc_desti = df_pag_local.loc[res['idx'], 'banc_desti_traspas']
                        
                        if banc_desti and pd.notna(banc_desti) and str(banc_desti).strip() != '':
                            banc_desti_str = str(banc_desti).strip()
                            # 1. Add compensatory income to despeses
                            row_dest = new_row.copy()
                            row_dest['ID_mov'] = int(max_id + 1)
                            row_dest['Banc'] = banc_desti_str
                            row_dest['Import càrrec'] = 0.0
                            row_dest['import ingrés'] = float(res['import_final'])
                            row_dest['grup'] = "op_banc"
                            insert_db_row('despeses', row_dest)
                            max_id += 1
                        
                            # 2. If dest_banc == TR Cartera, insert into tr_cartera as Compra
                            if banc_desti_str == 'TR Cartera':
                                concepte_str = str(res['row']['Concepte']).lower()
                                cartera_val = 'NVIDIA' if 'nvidia' in concepte_str else 'S&P500'
                                new_tr_row = {
                                    'DATA': datetime.datetime.now().strftime('%Y-%m-%d'),
                                    'mes': month_translations.get(mes_cat.lower(), mes_cat.lower()),
                                    'any': int(any_val),
                                    'COMPRA': float(res['import_final']),
                                    'VENDA': 0.0,
                                    'CARTERA': cartera_val,
                                    'CONCEPTE': 'Compra',
                                    'COMENTARI': f"Traspàs automàtic: {res['row']['Concepte']}"
                                }
                                insert_db_row('tr_cartera', new_tr_row)
                            
                        updates_made = True
                    elif res['type'] == 'ingres':
                        df_ing_local.loc[res['idx'], 'cobrat'] = 'cobrat'
                        df_ing_local.loc[res['idx'], 'Import'] = float(res['import_final'])
                        new_row = {
                            'ID_mov': int(max_id),
                            'Data': avui,
                            'Banc': str(res['banc']),
                            'FormaPago': str(res['forma_pago']),
                            'Idcategoria': 'ingres_general',
                            'Idconcepte': str(res['row']['Concepte']),
                            'Import càrrec': 0.0,
                            'import ingrés': float(res['import_final']),
                            'Comentari': None,
                            'mes': month_translations.get(mes_cat.lower(), mes_cat.lower()),
                            'any': int(any_val),
                            'grup': "Ingrés",
                            'ticketPendent': False
                        }
                        try:
                            insert_db_row('despeses', new_row)
                            updates_made = True
                        except Exception as e:
                            st.error(f"Error inserint ingressos: {e}")
                    
                if updates_made:
                    save_to_csv(df_pag_local.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'pagaments.csv')
                    save_to_csv(df_ing_local.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'ingressos.csv')
                    st.session_state["df_pag"] = df_pag_local
                    st.session_state["df_ing"] = df_ing_local
                
                    st.success("Operacions desades correctament!")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
    
        with st.container():
            col_det_title, col_det_mes, col_det_any = st.columns([6, 3, 3], vertical_alignment="center")
            with col_det_mes:
                cur_m_idx = CATALAN_MONTHS.index(selected_month_cat) if selected_month_cat in CATALAN_MONTHS else current_month_index
                sel_m = st.selectbox("Mes", CATALAN_MONTHS, index=cur_m_idx, key="detalls_sel_mes")
            with col_det_any:
                cur_y_idx = years_list.index(selected_year) if selected_year in years_list else 0
                sel_y = st.selectbox("Any", years_list, index=cur_y_idx, key="detalls_sel_year")
            with col_det_title:
                st.markdown(f"<h3 style='margin:0; font-size:1.45rem; color:#f39c12; font-weight:700;'>🔍 Detalls de {sel_m.capitalize()} del {sel_y}</h3>", unsafe_allow_html=True)
            
            selected_month_cat = sel_m
            selected_month_data = month_translations.get(sel_m.lower(), sel_m.lower())
            selected_year = int(sel_y)
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
            col_left, col_mid, col_right = st.columns([1, 1, 1], gap="medium")
        
            with col_left:
                st.markdown("<h4 style='color:#f39c12;'>📋 Pagaments del Mes</h4>", unsafe_allow_html=True)
            
                all_items = []
                seen_concepts = set()
                pagaments_a_processar = []
            
                # 1. Hipoteca status
                sub_hip = df_hip[(df_hip['any'] == selected_year) & (df_hip['mes'].str.lower() == selected_month_data)]
                if not sub_hip.empty:
                    hip_row = sub_hip.iloc[0]
                    amt_hip = float(clean_numeric(pd.Series([hip_row.get('Quota fixa', 0.0)])).iloc[0])
                    status_hip = "Pagat" if str(hip_row.get('pagat', '')).lower().strip() == 'pagat' else "Pendent"
                    banc_hip = str(hip_row.get('Banc', 'BBVA')).strip()
                    if banc_hip.lower() == 'nan': banc_hip = 'BBVA'
                    forma_pago_hip = str(hip_row.get('FormaPago', hip_row.get('Formapago', 'Compte'))).strip()
                    if forma_pago_hip.lower() == 'nan': forma_pago_hip = 'Compte'
                    
                    all_items.append({
                        'idx': 'hipoteca',
                        'Concepte': 'Hipoteca',
                        'Import': amt_hip,
                        'status': status_hip,
                        'Categoria': 'despesa_general',
                        'icon': '🏠',
                        'row': {'Concepte': 'Hipoteca', 'Import': amt_hip, 'Categoria': 'despesa_general', 'Banc': banc_hip, 'Formapago': forma_pago_hip}
                    })
                    seen_concepts.add('hipoteca')

                # 2. Pagaments de la taula Previsió de Pagaments
                sub_pag_all = df_pag[
                    (df_pag['any'] == selected_year) & 
                    (df_pag['mes'].astype(str).str.lower().str.strip() == selected_month_data.lower().strip())
                ]
            
                if not sub_pag_all.empty:
                    sub_pag_work = sub_pag_all.copy()
                    sub_pag_work['import_num'] = clean_numeric(sub_pag_work['Import'])
                
                    for p_idx, p_row in sub_pag_work.iterrows():
                        concept_str = str(p_row.get('Concepte', '')).strip()
                        concept_lower = concept_str.lower()
                        if concept_lower in seen_concepts:
                            continue
                    
                        # Assignem icones segons el concepte
                        if any(k in concept_lower for k in ["hipoteca", "ajunt", "bbva asseg", "casa"]):
                            icon = "🏠"
                        elif any(k in concept_lower for k in ["cotxe", "lloguer parking"]):
                            icon = "🚗"
                        elif "piscina" in concept_lower:
                            icon = "🏊‍♂️"
                        elif "pj isabel" in concept_lower:
                            icon = "🐷"
                        elif any(k in concept_lower for k in ["lowi", "telefon", "mòbil"]):
                            icon = "📱"
                        elif "accions" in concept_lower:
                            icon = "💸"
                        elif any(k in concept_lower for k in ["morts", "ocaso"]):
                            icon = "✝️"
                        else:
                            icon = "💸"
                    
                        amt = float(p_row['import_num'])
                        status_p = "Pagat" if str(p_row.get('pagat', '')).lower().strip() == 'pagat' else "Pendent"
                        all_items.append({
                            'idx': p_idx,
                            'Concepte': concept_str,
                            'Import': amt,
                            'status': status_p,
                            'Categoria': p_row.get('Categoria', 'despesa_general'),
                            'icon': icon,
                            'row': p_row
                        })
                        seen_concepts.add(concept_lower)
            
                pendent_items = [it for it in all_items if it['status'] != 'Pagat']
                paid_items = [it for it in all_items if it['status'] == 'Pagat']
            
                total_programat = sum(it['Import'] for it in all_items)
                total_pendent = sum(it['Import'] for it in pendent_items)

                # --- Render Pendents ---
                if pendent_items:
                    st.write("**Pendents de pagament:**")
                    for it in pendent_items:
                        amt = float(it['Import'])
                        icon = it.get('icon', '💸')
                        c_chk, c_txt = st.columns([0.08, 0.92], gap="small")
                        with c_chk:
                            is_sel = st.checkbox(" ", key=f"chk_pag_{it['idx']}", label_visibility="collapsed")
                        with c_txt:
                            if is_sel:
                                c_name, c_num = st.columns([0.60, 0.40])
                                c_name.markdown(f"<div style='display:flex; align-items:center; padding-top:4px;'><span style='min-width:140px; font-size:0.95rem; white-space:nowrap;'>{icon} {it['Concepte']}</span></div>", unsafe_allow_html=True)
                                custom_amt = c_num.number_input("Import real", value=float(amt), step=0.01, format="%.2f", key=f"num_pag_in_{it['idx']}", label_visibility="collapsed")
                                new_row = it['row'].copy()
                                new_row['Import'] = custom_amt
                                pagaments_a_processar.append({'idx': it['idx'], 'row': new_row})
                            else:
                                st.markdown(f"<div style='display:flex; align-items:center; padding-top:4px;'><span style='min-width:140px; font-size:0.95rem; white-space:nowrap;'>{icon} {it['Concepte']}</span><span style='font-weight:600; font-size:0.95rem; white-space:nowrap; margin-left:14px;'>{amt:,.2f} €</span></div>", unsafe_allow_html=True)
                
                    if len(pagaments_a_processar) > 0:
                        if st.button("📥 Passar seleccionats a la BBDD", key="btn_proc_pag"):
                            dialog_confirmar_operacions(pagaments_a_processar, [], selected_year, selected_month_cat)
                
                    st.write("") # spacer
                elif not all_items:
                    st.info("No hi ha dades de pagaments per aquest mes.")
                else:
                    st.info("No hi ha cap pagament pendent aquest mes.")

                # --- Render Pagats (sense línies de taula, espaiat reduït i alineat) ---
                if paid_items:
                    st.write("**Pagats:**")
                    rows_html = []
                    for it in paid_items:
                        amt = float(it['Import'])
                        icon = it.get('icon', '💸')
                        rows_html.append(f"<tr style='border:none;'><td style='padding:3px 18px 3px 0; border:none; font-size:0.95rem; white-space:nowrap;'>{icon} {it['Concepte']}</td><td style='padding:3px 10px 3px 0; border:none; text-align:right; font-weight:600; font-size:0.95rem; white-space:nowrap;'>{amt:,.2f} €</td><td style='padding:3px 0; border:none; color:#22c55e; font-size:0.82rem; font-weight:600; white-space:nowrap;'>pagat</td></tr>")
                    table_html = f"<table style='width:auto; border:none; border-collapse:collapse; margin-bottom:6px;'><tbody>{''.join(rows_html)}</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
                    st.write("")

                if total_programat > 0 or total_pendent > 0:
                    st.markdown(f"""
                    <div style="display: flex; gap: 40px; margin-top: 10px;">
                        <div data-testid="stMetric">
                            <div style="font-size: 14px; color: rgb(85, 85, 85); padding-bottom: 0.25rem;">Total per a pagar</div>
                            <div style="font-size: 2.25rem; font-weight: 400; color: inherit;">{total_programat:,.2f} €</div>
                        </div>
                        <div data-testid="stMetric">
                            <div style="font-size: 14px; color: rgb(85, 85, 85); padding-bottom: 0.25rem;">Pendent</div>
                            <div style="font-size: 2.25rem; font-weight: 400; color: #ef4444;">{total_pendent:,.2f} €</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
            with col_mid:
                st.markdown("<h4 style='color:#f39c12;'>📥 Ingressos del Mes</h4>", unsafe_allow_html=True)
                # Load ingressos list for selected month
                month_ing = df_ing[(df_ing['any'] == selected_year) & (df_ing['clean_mes'] == selected_month_data)]
                if not month_ing.empty:
                    ingressos_a_processar = []
                    mask_pendent = month_ing['cobrat'].astype(str).str.strip().str.lower() == 'pendent'
                    month_ing_pendent = month_ing[mask_pendent]
                    month_ing_cobrat = month_ing[~mask_pendent].copy()
                
                    if not month_ing_pendent.empty:
                        st.write("**Pendents de cobrament:**")
                        for i_idx, i_row in month_ing_pendent.iterrows():
                            amt = float(clean_numeric(pd.Series([i_row['Import']])).iloc[0])
                            concepte = i_row['Concepte']
                            c_chk, c_txt = st.columns([0.08, 0.92], gap="small")
                            with c_chk:
                                is_sel = st.checkbox(" ", key=f"chk_ing_{i_idx}", label_visibility="collapsed")
                            with c_txt:
                                if is_sel:
                                    c_name, c_num = st.columns([0.60, 0.40])
                                    c_name.markdown(f"<div style='display:flex; align-items:center; padding-top:4px;'><span style='min-width:190px; font-size:0.95rem; white-space:nowrap;'>🟢 {concepte}</span></div>", unsafe_allow_html=True)
                                    custom_amt = c_num.number_input("Import real", value=float(amt), step=0.01, format="%.2f", key=f"num_ing_in_{i_idx}", label_visibility="collapsed")
                                    new_row = i_row.copy()
                                    new_row['Import'] = custom_amt
                                    ingressos_a_processar.append({'idx': i_idx, 'row': new_row})
                                else:
                                    st.markdown(f"<div style='display:flex; align-items:center; padding-top:4px;'><span style='min-width:190px; font-size:0.95rem; white-space:nowrap;'>🟢 {concepte}</span><span style='font-weight:600; font-size:0.95rem; white-space:nowrap; margin-left:14px;'>{amt:,.2f} €</span></div>", unsafe_allow_html=True)
                    
                        if len(ingressos_a_processar) > 0:
                            if st.button("📥 Passar ingressos a BBDD", key="btn_proc_ing"):
                                dialog_confirmar_operacions([], ingressos_a_processar, selected_year, selected_month_cat)
                    
                        st.write("") # spacer
                
                    # --- Render Cobrats (sense línies de taula, espaiat reduït i alineat) ---
                    if not month_ing_cobrat.empty:
                        st.write("**Cobrats:**")
                        rows_ing_html = []
                        for _, i_row in month_ing_cobrat.iterrows():
                            amt = float(clean_numeric(pd.Series([i_row['Import']])).iloc[0])
                            concepte = i_row['Concepte']
                            rows_ing_html.append(f"<tr style='border:none;'><td style='padding:3px 18px 3px 0; border:none; font-size:0.95rem; white-space:nowrap;'>🟢 {concepte}</td><td style='padding:3px 10px 3px 0; border:none; text-align:right; font-weight:600; font-size:0.95rem; white-space:nowrap;'>{amt:,.2f} €</td><td style='padding:3px 0; border:none; color:#22c55e; font-size:0.82rem; font-weight:600; white-space:nowrap;'>cobrat</td></tr>")
                        table_ing_html = f"<table style='width:auto; border:none; border-collapse:collapse; margin-bottom:6px;'><tbody>{''.join(rows_ing_html)}</tbody></table>"
                        st.markdown(table_ing_html, unsafe_allow_html=True)
                        st.write("")
                        
                    # Sum the pending ingressos
                    pendent_sum = month_ing_pendent['Import'].sum() if not month_ing_pendent.empty else 0.0
                    
                    st.markdown(f"""
                    <div style="display: flex; gap: 40px; margin-top: 10px;">
                        <div data-testid="stMetric">
                            <div style="font-size: 14px; color: rgb(85, 85, 85); padding-bottom: 0.25rem;">Total per a ingressar</div>
                            <div style="font-size: 2.25rem; font-weight: 400; color: inherit;">{month_ing['Import'].sum():,.2f} €</div>
                    </div>
                        <div data-testid="stMetric">
                            <div style="font-size: 14px; color: rgb(85, 85, 85); padding-bottom: 0.25rem;">Pendent</div>
                            <div style="font-size: 2.25rem; font-weight: 400; color: #3b82f6;">{pendent_sum:,.2f} €</div>
                    </div>
                </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No hi ha dades d'ingressos per aquest mes.")
                
            with col_right:
                st.markdown("<h4 style='color:#f39c12;'>📤 Càrrecs per Categoria</h4>", unsafe_allow_html=True)
                month_desp = df_desp[(df_desp['any'] == selected_year) & (df_desp['clean_mes'] == selected_month_data)]
                if not month_desp.empty:
                    # Exclude op_banc!
                    month_desp_filtered = month_desp[(month_desp['Idcategoria'] != 'op_banc') & (month_desp['grup'] != 'op_banc')]
                
                    grouped_desp = month_desp_filtered.groupby('Idcategoria')['Import càrrec'].sum().reset_index()
                    grouped_desp = grouped_desp[grouped_desp['Import càrrec'] > 0].sort_values(by='Import càrrec', ascending=False)
                
                    try:
                        event = st.dataframe(
                            grouped_desp[['Idcategoria', 'Import càrrec']],
                            use_container_width=True,
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            column_config={
                                "Idcategoria": st.column_config.TextColumn("Idcategoria"),
                                "Import càrrec": st.column_config.NumberColumn("Import càrrec", format="%.2f €", width="small")
                            }
                        )
                    except Exception as e:
                        st.error(f"Error rendering grouped_desp: {e}")
                        event = None
                    st.metric("Total Gastat", f"{grouped_desp['Import càrrec'].sum():,.2f} €")
                
                    # Show details of selected group if clicked
                    if event and 'rows' in event.selection and event.selection['rows']:
                        selected_row_idx = event.selection['rows'][0]
                        selected_cat = grouped_desp.iloc[selected_row_idx]['Idcategoria']
                        st.write("")
                        st.markdown(f"**🔍 Desglòs de despeses: {selected_cat}**")
                    
                        cat_details = month_desp_filtered[month_desp_filtered['Idcategoria'] == selected_cat][
                            ['Data', 'FormaPago', 'Idconcepte', 'Import càrrec', 'Comentari']
                        ].copy()
                    
                        try:
                            st.dataframe(
                                cat_details.style.format({'Import càrrec': '{:,.2f} €'}),
                                use_container_width=True,
                                hide_index=True
                            )
                        except Exception as e:
                            st.error(f"Error rendering cat_details: {e}")
                else:
                    st.info("No hi ha dades de despeses per aquest mes.")
    


        
        return

    # ================= MÒDUL ECONÒMIC (PESTANYES) =================
    st.write("")

    tabs_list = ["📝 Ingrés / Despesa General"]
    if st.session_state.get("role") in ["admin", "guest"]:
        tabs_list.extend(["🔴 Prev. Despeses", "🟢 Prev. Ingressos", "📈 Inversions", "💰 Estalvis", "🤖 Xat IA"])
    
    if tabs_list:
        tabs = st.tabs(tabs_list)
    
    tab_ingres_despesa = tabs[0]
    if st.session_state.get("role") in ["admin", "guest"]:
        tab_prev_desp = tabs[1]
        tab_prev_ing = tabs[2]
        tab_inversions = tabs[3]
        tab_estalvis = tabs[4]
        tab_xat = tabs[5]
    else:
        tab_prev_desp = None
        tab_prev_ing = None
        tab_inversions = None
        tab_estalvis = None
        tab_xat = None

    # Removed Compres Super
    if tab_ingres_despesa:
        with tab_ingres_despesa:
            render_ingres_despesa_general_interface()

    # ================= TAB: PREVISIÓ DE DESPESES =================
    if tab_prev_desp:
        with tab_prev_desp:
            st.markdown("<h3 style='color:#f39c12;'>🔴 Previsió de Despeses (Pagaments Programats)</h3>", unsafe_allow_html=True)
            
            with st.expander("➕ Nova Previsió de Pagament", expanded=True):
                # Row 1 (4 columns)
                r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
                with r1_col1:
                    banc_pag = st.selectbox("Banc", [""] + get_config_banks(), index=0, key="pag_banc")
                with r1_col2:
                    forma_pago_pag = st.selectbox("Forma de Pagament", [""] + get_config_payment_methods(), index=0, key="pag_forma_pago")
                with r1_col3:
                    data_val_pag = st.date_input("Data Previsió", value=datetime.today(), format="DD/MM/YYYY", key="pag_data")
                    mes_val_pag = month_translations[CATALAN_MONTHS[data_val_pag.month - 1]]
                    any_val_pag = data_val_pag.year
                with r1_col4:
                    import_carg_pag = st.number_input("Import (€)", min_value=0.0, value=None, step=0.01, key="pag_import")
                    
                # Row 2 (5 columns)
                r2_col1, r2_col2, r2_col3, r2_col4, r2_col5 = st.columns([2.5, 2.5, 2.0, 2.5, 2.5])
                with r2_col1:
                    cat_val_pag = st.selectbox("Categoria", [""] + get_config_categories(), index=0, key="pag_cat")
                with r2_col2:
                    concept_options_pag = [""] + get_config_concepts(cat_val_pag) if cat_val_pag else [""]
                    concept_val_pag = st.selectbox("Concepte", concept_options_pag, index=0, key="pag_concepte")
                with r2_col3:
                    pagat_val_pag = st.selectbox("Estat", ["pendent", "pagat"], key="pag_estat")
                with r2_col4:
                    repetir_pag = st.checkbox("Repetir mensualment?", value=False, help="Crearà o actualitzarà l'import d'aquest concepte per a tots els mesos restants fins a l'any indicat.", key="pag_repetir")
                with r2_col5:
                    repetir_any_limit_pag = st.selectbox("Fins a desembre de l'any:", [any_val_pag, any_val_pag + 1, any_val_pag + 2], index=0, key="rep_any_pag")
                
                # Row 3
                r3_col1, r3_col2 = st.columns([1, 1])
                with r3_col1:
                    dest_banc_pag = st.selectbox("Banc de Destí (Opcional, només per Traspassos)", [""] + get_config_banks(), index=0, key="pag_dest_banc")
                
                col_btns_pag = st.columns([3.5, 2.0, 6.5])
                with col_btns_pag[0]:
                    submitted_pag = st.button("💾 Desar Previsió de Pagament", type="primary", use_container_width=True)
                with col_btns_pag[1]:
                    cancelled_pag = st.button("Cancel·lar", key="cancel_pag", use_container_width=True)
                    
                if cancelled_pag:
                    for k in list(st.session_state.keys()):
                        if k.startswith("pag_") or k == "rep_any_pag": del st.session_state[k]
                    st.rerun()
                    
                if submitted_pag:
                    if not concept_val_pag or not banc_pag or import_carg_pag is None or import_carg_pag <= 0:
                        st.error("⚠️ Heu d'omplir Banc, Concepte i un Import vàlid.")
                    else:
                        if repetir_pag:
                            current_max_id = int(df_pag['idPago'].max() + 1) if not df_pag.empty and 'idPago' in df_pag.columns else 1
                            updated_count = 0
                            added_count = 0
                            for yr in range(any_val_pag, repetir_any_limit_pag + 1):
                                start_month = data_val_pag.month if yr == any_val_pag else 1
                                for m_idx in range(start_month, 13):
                                    m_cat = CATALAN_MONTHS[m_idx - 1]
                                    m_data = month_translations[m_cat]
                                    
                                    mask = (df_pag['any'] == yr) & (df_pag['mes'].astype(str).str.lower() == m_data) & (df_pag['Concepte'].astype(str).str.lower() == concept_val_pag.lower())
                                    if mask.any():
                                        df_pag.loc[mask, 'Import'] = import_carg_pag
                                        df_pag.loc[mask, 'Banc'] = banc_pag
                                        df_pag.loc[mask, 'Formapago'] = forma_pago_pag
                                        df_pag.loc[mask, 'Categoria'] = cat_val_pag
                                        df_pag.loc[mask, 'pagat'] = pagat_val_pag
                                        df_pag.loc[mask, 'banc_desti_traspas'] = dest_banc_pag if dest_banc_pag else None
                                        updated_count += 1
                                    else:
                                        new_row = {
                                            'idPago': current_max_id,
                                            'Banc': banc_pag,
                                            'Formapago': forma_pago_pag,
                                            'Data': f"{data_val_pag.day:02d}/{m_idx:02d}/{yr}",
                                            'dia': data_val_pag.day,
                                            'mes': m_data,
                                            'any': yr,
                                            'Categoria': cat_val_pag,
                                            'Concepte': concept_val_pag,
                                            'Import': import_carg_pag,
                                            'pagat': pagat_val_pag,
                                            'banc_desti_traspas': dest_banc_pag if dest_banc_pag else None
                                        }
                                        df_pag = pd.concat([df_pag, pd.DataFrame([new_row])], ignore_index=True)
                                        current_max_id += 1
                                        added_count += 1
                            save_to_csv(df_pag.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'pagaments.csv')
                            st.session_state["df_pag"] = df_pag
                            st.success(f"Previsions desades: {added_count} creades i {updated_count} actualitzades!")
                        else:
                            new_row = {
                                'idPago': int(df_pag['idPago'].max() + 1) if not df_pag.empty and 'idPago' in df_pag.columns else 1,
                                'Banc': banc_pag,
                                'Formapago': forma_pago_pag,
                                'Data': data_val_pag.strftime('%d/%m/%Y'),
                                'dia': data_val_pag.day,
                                'mes': mes_val_pag,
                                'any': any_val_pag,
                                'Categoria': cat_val_pag,
                                'Concepte': concept_val_pag,
                                'Import': import_carg_pag,
                                'pagat': pagat_val_pag,
                                'banc_desti_traspas': dest_banc_pag if dest_banc_pag else None
                            }
                            df_pag = pd.concat([df_pag, pd.DataFrame([new_row])], ignore_index=True)
                            save_to_csv(df_pag.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'pagaments.csv')
                            st.session_state["df_pag"] = df_pag
                            st.success("Previsió de pagament desada correctament!")
                        for k in list(st.session_state.keys()):
                            if k.startswith("pag_") or k == "rep_any_pag": del st.session_state[k]
                        st.rerun()

            col_t_pag, col_chk_pag = st.columns([7, 3], vertical_alignment="bottom")
            with col_t_pag:
                st.markdown("#### 📋 Llistat de Pagaments Previstos")
            with col_chk_pag:
                ordenar_recent_pag = st.checkbox("Ordenar pel més recent primer", value=True, help="Si està marcat, es mostrarà el més recent a dalt de tot.", key="ord_rec_pag")
            if not df_pag.empty:
                df_pag_filtered = df_pag.copy()
                with st.expander("🔍 Filtres", expanded=False):
                    f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 2, 1], vertical_alignment="bottom")
                    with f1:
                        f_any_pag = st.selectbox("Any", ["Tots"] + sorted(list(df_pag['any'].unique()), reverse=True), key="f_any_pag")
                    with f2:
                        f_mes_pag = st.selectbox("Mes", ["Tots"] + sorted(list(df_pag['mes'].astype(str).unique())), key="f_mes_pag")
                    with f3:
                        f_banc_pag = st.selectbox("Banc", ["Tots"] + sorted(list(df_pag['Banc'].astype(str).unique())), key="f_banc_pag")
                    with f4:
                        f_estat_pag = st.selectbox("Estat", ["Tots"] + sorted(list(df_pag['pagat'].astype(str).unique())), key="f_estat_pag")
                    with f5:
                        if st.button("🔄 Netejar", key="clear_pag_filters", use_container_width=True):
                            for k in ["f_any_pag", "f_mes_pag", "f_banc_pag", "f_estat_pag"]:
                                if k in st.session_state: del st.session_state[k]
                            st.rerun()
                        
                if f_any_pag != "Tots": df_pag_filtered = df_pag_filtered[df_pag_filtered['any'] == f_any_pag]
                if f_mes_pag != "Tots": df_pag_filtered = df_pag_filtered[df_pag_filtered['mes'].astype(str) == f_mes_pag]
                if f_banc_pag != "Tots": df_pag_filtered = df_pag_filtered[df_pag_filtered['Banc'].astype(str) == f_banc_pag]
                if f_estat_pag != "Tots": df_pag_filtered = df_pag_filtered[df_pag_filtered['pagat'].astype(str) == f_estat_pag]

                cols_p = [c for c in ['Data', 'Concepte', 'Categoria', 'Banc', 'Formapago', 'Import', 'pagat'] if c in df_pag_filtered.columns]
                sort_cols = [c for c in ['any', 'Concepte', 'Categoria', 'Banc', 'Formapago', 'pagat'] if c in df_pag_filtered.columns]
                if ordenar_recent_pag and 'parsed_date' in df_pag_filtered.columns:
                    df_pag_filtered = df_pag_filtered.sort_values(by=['parsed_date'], ascending=False)
                elif sort_cols:
                    df_pag_filtered = df_pag_filtered.sort_values(by=sort_cols)
                st.dataframe(
                    df_pag_filtered[cols_p],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Import": st.column_config.NumberColumn(format="%.2f €")}
                )
            else:
                st.info("No hi ha previsions de pagament.")

    # ================= TAB: PREVISIÓ D'INGRESSOS =================
    if tab_prev_ing:
        with tab_prev_ing:
            st.markdown("<h3 style='color:#f39c12;'>🟢 Previsió d'Ingressos (Nòmines i Altres)</h3>", unsafe_allow_html=True)
            
            with st.expander("➕ Nova Previsió d'Ingrés", expanded=True):
                # Row 1 (4 columns)
                r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
                with r1_col1:
                    banc_ing = st.selectbox("Banc", [""] + get_config_banks(), index=0, key="ing_banc")
                with r1_col2:
                    data_val_ing = st.date_input("Data Previsió", value=datetime.today(), format="DD/MM/YYYY", key="ing_data")
                    mes_val_ing = month_translations[CATALAN_MONTHS[data_val_ing.month - 1]]
                    any_val_ing = data_val_ing.year
                with r1_col3:
                    import_ing_val = st.number_input("Import Ingrés (€)", min_value=0.0, value=None, step=0.01, key="ing_import")
                with r1_col4:
                    cat_val_ing = st.selectbox("Categoria", ["", "ingrés_general", "ingrés_extra"], index=0, key="ing_cat")
                    
                # Row 2 (4 columns)
                r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
                with r2_col1:
                    concept_options_ing = [""] + get_config_concepts(cat_val_ing) if cat_val_ing else [""]
                    concept_val_ing = st.selectbox("Concepte", concept_options_ing, index=0, key="ing_concepte")
                with r2_col2:
                    cobrat_val_ing = st.selectbox("Estat", ["cobrat", "pendent"], key="ing_cobrat")
                with r2_col3:
                    repetir_ing = st.checkbox("Repetir mensualment?", value=False, help="Crearà o actualitzarà l'import d'aquest concepte per a tots els mesos restants fins a l'any indicat.", key="ing_repetir")
                with r2_col4:
                    repetir_any_limit_ing = st.selectbox("Fins a desembre de l'any:", [any_val_ing, any_val_ing + 1, any_val_ing + 2], index=0, key="rep_any_ing")
                
                col_btns_ing = st.columns([3.5, 2.0, 6.5])
                with col_btns_ing[0]:
                    submitted_ing = st.button("💾 Desar Previsió d'Ingrés", type="primary", use_container_width=True)
                with col_btns_ing[1]:
                    cancelled_ing = st.button("Cancel·lar", key="cancel_ing", use_container_width=True)
                    
                if cancelled_ing:
                    for k in list(st.session_state.keys()):
                        if k.startswith("ing_") or k == "rep_any_ing": del st.session_state[k]
                    st.rerun()
                    
                if submitted_ing:
                    if not concept_val_ing or not banc_ing or import_ing_val is None or import_ing_val <= 0:
                        st.error("⚠️ Heu d'omplir Banc, Concepte i un Import vàlid.")
                    else:
                        if repetir_ing:
                            current_max_id = int(df_ing['idIngres'].max() + 1) if not df_ing.empty and 'idIngres' in df_ing.columns else 1
                            updated_count = 0
                            added_count = 0
                            for yr in range(any_val_ing, repetir_any_limit_ing + 1):
                                start_month = data_val_ing.month if yr == any_val_ing else 1
                                for m_idx in range(start_month, 13):
                                    m_cat = CATALAN_MONTHS[m_idx - 1]
                                    m_data = month_translations[m_cat]
                                    
                                    mask = (df_ing['any'] == yr) & (df_ing['mes'].astype(str).str.lower() == m_data) & (df_ing['Concepte'].astype(str).str.lower() == concept_val_ing.lower())
                                    if mask.any():
                                        df_ing.loc[mask, 'Import'] = import_ing_val
                                        df_ing.loc[mask, 'Banc'] = banc_ing
                                        df_ing.loc[mask, 'Categoria'] = cat_val_ing
                                        df_ing.loc[mask, 'cobrat'] = cobrat_val_ing
                                        updated_count += 1
                                    else:
                                        new_row = {
                                            'idIngres': current_max_id,
                                            'Banc': banc_ing,
                                            'Data': f"{data_val_ing.day:02d}/{m_idx:02d}/{yr}",
                                            'dia': data_val_ing.day,
                                            'mes': m_data,
                                            'any': yr,
                                            'Categoria': cat_val_ing,
                                            'Concepte': concept_val_ing,
                                            'Import': import_ing_val,
                                            'comentari': '',
                                            'cobrat': cobrat_val_ing
                                        }
                                        df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                                        current_max_id += 1
                                        added_count += 1
                            save_to_csv(df_ing.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'ingressos.csv')
                            st.session_state["df_ing"] = df_ing
                            st.success(f"Previsions d'ingrés desades: {added_count} creades i {updated_count} actualitzades!")
                        else:
                            new_row = {
                                'idIngres': int(df_ing['idIngres'].max() + 1) if not df_ing.empty and 'idIngres' in df_ing.columns else 1,
                                'Banc': banc_ing,
                                'Data': data_val_ing.strftime('%d/%m/%Y'),
                                'dia': data_val_ing.day,
                                'mes': mes_val_ing,
                                'any': any_val_ing,
                                'Categoria': cat_val_ing,
                                'Concepte': concept_val_ing,
                                'Import': import_ing_val,
                                'comentari': '',
                                'cobrat': cobrat_val_ing
                            }
                            df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                            save_to_csv(df_ing.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'ingressos.csv')
                            st.session_state["df_ing"] = df_ing
                            st.success("Previsió d'ingrés desada correctament!")
                        for k in list(st.session_state.keys()):
                            if k.startswith("ing_") or k == "rep_any_ing": del st.session_state[k]
                        st.rerun()

            col_t_ing, col_chk_ing = st.columns([7, 3], vertical_alignment="bottom")
            with col_t_ing:
                st.markdown("#### 📋 Llistat d'Ingressos Previstos")
            with col_chk_ing:
                ordenar_recent_ing = st.checkbox("Ordenar pel més recent primer", value=True, help="Si està marcat, es mostrarà el més recent a dalt de tot.", key="ord_rec_ing")
            if not df_ing.empty:
                df_ing_filtered = df_ing.copy()
                with st.expander("🔍 Filtres", expanded=False):
                    fi1, fi2, fi3, fi4, fi5 = st.columns([2, 2, 2, 2, 1], vertical_alignment="bottom")
                    with fi1:
                        f_any_ing = st.selectbox("Any", ["Tots"] + sorted(list(df_ing['any'].unique()), reverse=True), key="f_any_ing")
                    with fi2:
                        f_mes_ing = st.selectbox("Mes", ["Tots"] + sorted(list(df_ing['mes'].astype(str).unique())), key="f_mes_ing")
                    with fi3:
                        f_banc_ing = st.selectbox("Banc", ["Tots"] + sorted(list(df_ing['Banc'].astype(str).unique())), key="f_banc_ing")
                    with fi4:
                        f_estat_ing = st.selectbox("Estat", ["Tots"] + sorted(list(df_ing['cobrat'].astype(str).unique())), key="f_estat_ing")
                    with fi5:
                        if st.button("🔄 Netejar", key="clear_ing_filters", use_container_width=True):
                            for k in ["f_any_ing", "f_mes_ing", "f_banc_ing", "f_estat_ing"]:
                                if k in st.session_state: del st.session_state[k]
                            st.rerun()
                        
                if f_any_ing != "Tots": df_ing_filtered = df_ing_filtered[df_ing_filtered['any'] == f_any_ing]
                if f_mes_ing != "Tots": df_ing_filtered = df_ing_filtered[df_ing_filtered['mes'].astype(str) == f_mes_ing]
                if f_banc_ing != "Tots": df_ing_filtered = df_ing_filtered[df_ing_filtered['Banc'].astype(str) == f_banc_ing]
                if f_estat_ing != "Tots": df_ing_filtered = df_ing_filtered[df_ing_filtered['cobrat'].astype(str) == f_estat_ing]

                cols_i = [c for c in ['Data', 'Concepte', 'Categoria', 'Banc', 'Import', 'cobrat'] if c in df_ing_filtered.columns]
                sort_cols_i = [c for c in ['any', 'Concepte', 'Categoria', 'Banc', 'cobrat'] if c in df_ing_filtered.columns]
                if ordenar_recent_ing and 'parsed_date' in df_ing_filtered.columns:
                    df_ing_filtered = df_ing_filtered.sort_values(by=['parsed_date'], ascending=False)
                elif sort_cols_i:
                    df_ing_filtered = df_ing_filtered.sort_values(by=sort_cols_i)
                st.dataframe(
                    df_ing_filtered[cols_i],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Import": st.column_config.NumberColumn(format="%.2f €")}
                )
            else:
                st.info("No hi ha previsions d'ingrés.")

    # ================= TAB: INVERSIONS (TR CARTERA) =================
    if tab_inversions:
        with tab_inversions:
            st.markdown("<h3 style='color:#f39c12;'>📈 Inversions (Trade Republic / TR Cartera)</h3>", unsafe_allow_html=True)
            
            with st.expander("➕ Nou Moviment TR Cartera", expanded=True):
                r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
                with r1_col1:
                    data_val_tr = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key="tr_data_inv")
                    mes_val_tr = month_translations[CATALAN_MONTHS[data_val_tr.month - 1]]
                    any_val_tr = data_val_tr.year
                with r1_col2:
                    cartera_val_tr = st.selectbox("CARTERA", ["S&P500", "NVIDIA"], key="tr_cartera_inv")
                with r1_col3:
                    tr_concepte_inv = st.selectbox("CONCEPTE", ["Compra", "Venda", "Promoció", "CashBack"], key="tr_concepte_inv")
                with r1_col4:
                    tr_import_inv = st.number_input("Import (€)", min_value=0.0, value=0.0, step=0.01, key="tr_import_inv")
                    
                tr_comentari_inv = st.text_input("COMENTARI", value="", key="tr_comentari_inv")
                
                if st.button("💾 Desar Moviment TR Cartera", type="primary", use_container_width=True):
                    if tr_import_inv <= 0 and tr_concepte_inv != "CashBack":
                        st.error("L'import ha de ser superior a 0 €")
                    else:
                        with st.spinner("Desant moviment d'inversió..."):
                            compra = tr_import_inv if tr_concepte_inv in ["Compra", "CashBack"] else 0.0
                            venda = tr_import_inv if tr_concepte_inv in ["Venda", "Promoció"] else 0.0
                            
                            new_tr_row = {
                                'DATA': data_val_tr.strftime('%Y-%m-%d'),
                                'mes': mes_val_tr,
                                'any': any_val_tr,
                                'COMPRA': compra,
                                'VENDA': venda,
                                'CARTERA': cartera_val_tr,
                                'CONCEPTE': tr_concepte_inv,
                                'COMENTARI': tr_comentari_inv
                            }
                            
                            supabase = get_supabase_client(st.session_state.get("role", "guest"))
                            supabase.table("tr_cartera").insert([new_tr_row]).execute()
                            
                            import_carg = tr_import_inv if tr_concepte_inv == "Compra" else 0.0
                            import_ing = tr_import_inv if tr_concepte_inv != "Compra" else 0.0
                            
                            row_traderep = {
                                'Data': data_val_tr.strftime('%Y-%m-%d'),
                                'mes': mes_val_tr,
                                'any': any_val_tr,
                                'Banc': 'TradeRep.',
                                'FormaPago': 'Compte',
                                'Import càrrec': import_carg,
                                'import ingrés': import_ing,
                                'grup': 'op_banc',
                                'Idcategoria': 'op_banc',
                                'Concepte': tr_concepte_inv,
                                'Descripcio': f"[{cartera_val_tr}] {tr_comentari_inv}".strip(),
                                'litres': 0.0,
                                'Revisat': True
                            }
                            row_trcartera = {
                                'Data': data_val_tr.strftime('%Y-%m-%d'),
                                'mes': mes_val_tr,
                                'any': any_val_tr,
                                'Banc': 'TR Cartera',
                                'FormaPago': 'Compte',
                                'Import càrrec': import_ing,
                                'import ingrés': import_carg,
                                'grup': 'op_banc',
                                'Idcategoria': 'op_banc',
                                'Concepte': tr_concepte_inv,
                                'Descripcio': f"[{cartera_val_tr}] {tr_comentari_inv}".strip(),
                                'litres': 0.0,
                                'Revisat': True
                            }
                            supabase.table("despeses").insert([row_traderep, row_trcartera]).execute()
                            
                            st.success("Moviment TR Cartera desat correctament!")
                            st.cache_data.clear()
                            st.rerun()

            st.markdown("#### 📊 Resum i Balanç d'Inversions")
            if not df_cartera.empty:
                col_kpi1, col_kpi2, col_kpi_amz, col_kpi3, col_kpi_sum, col_kpi_vendes = st.columns(6)
                
                valid_concepts = ['compra', 'promoció', 'promocio']
                
                sp_compres = df_cartera[(df_cartera['CARTERA'] == 'S&P500') & (df_cartera['CONCEPTE'].str.lower().isin(valid_concepts))]['COMPRA'].sum()
                nv_compres = df_cartera[(df_cartera['CARTERA'] == 'NVIDIA') & (df_cartera['CONCEPTE'].str.lower().isin(valid_concepts))]['COMPRA'].sum()
                amz_compres = df_cartera[(df_cartera['CARTERA'] == 'Amazon') & (df_cartera['CONCEPTE'].str.lower().isin(valid_concepts))]['COMPRA'].sum()
                total_cashback = df_cartera[df_cartera['CONCEPTE'].str.lower() == 'cashback']['COMPRA'].sum()
                suma_accions = sp_compres + nv_compres + amz_compres + total_cashback
                total_vendes = df_cartera['VENDA'].sum()
                
                with col_kpi1:
                    st.metric("Total S&P500", f"{sp_compres:,.2f} €")
                with col_kpi2:
                    st.metric("Total NVIDIA", f"{nv_compres:,.2f} €")
                with col_kpi_amz:
                    st.metric("Total Amazon", f"{amz_compres:,.2f} €")
                with col_kpi3:
                    st.metric("CashBack", f"{total_cashback:,.2f} €")
                with col_kpi_sum:
                    st.metric("Suma Inversió", f"{suma_accions:,.2f} €")
                with col_kpi_vendes:
                    st.metric("Total Vendes", f"{total_vendes:,.2f} €")

                st.markdown("#### 📋 Històric de Moviments TR Cartera")
                cols_tr = [c for c in ['DATA', 'CARTERA', 'CONCEPTE', 'COMPRA', 'VENDA', 'COMENTARI'] if c in df_cartera.columns]
                
                format_dict = {'COMPRA': '{:,.2f} €', 'VENDA': '{:,.2f} €'}
                if 'DATA' in df_cartera.columns:
                    format_dict['DATA'] = lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if pd.notnull(x) and str(x).strip() else ''
                    df_cartera_display = df_cartera.sort_values(by='DATA', ascending=False)
                else:
                    df_cartera_display = df_cartera
                    
                st.dataframe(
                    df_cartera_display[cols_tr].style.format(format_dict),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hi ha registres d'inversions a TR Cartera.")

    # ================= TAB: ESTALVIS (ESTALVI DP) =================
    if tab_estalvis:
        with tab_estalvis:
            st.markdown("<h3 style='color:#f39c12;'>💰 Pla d'Estalvi (Fons Estalvi DP)</h3>", unsafe_allow_html=True)
            
            if not df_est.empty:
                df_est_work = df_est.copy()
                
                # Normalize column names in case of encoding differences
                col_rename = {}
                for c in df_est_work.columns:
                    c_clean = c.lower().strip()
                    if 'aport' in c_clean:
                        col_rename[c] = 'aportacio'
                    elif 'perdu' in c_clean or 'psrdu' in c_clean:
                        col_rename[c] = 'perdua'
                df_est_work.rename(columns=col_rename, inplace=True)
                
                df_est_work['quota_val'] = clean_numeric(df_est_work['quota']) if 'quota' in df_est_work.columns else pd.Series(0.0, index=df_est_work.index)
                df_est_work['aport_val'] = clean_numeric(df_est_work['aportacio']) if 'aportacio' in df_est_work.columns else pd.Series(0.0, index=df_est_work.index)
                df_est_work['rescat_val'] = clean_numeric(df_est_work['rescat']) if 'rescat' in df_est_work.columns else pd.Series(0.0, index=df_est_work.index)
                df_est_work['perdua_val'] = clean_numeric(df_est_work['perdua']) if 'perdua' in df_est_work.columns else (df_est_work['aport_val'] - df_est_work['rescat_val'])
                
                # Sort chronologically
                month_order = {
                    'gener': 1, 'febrer': 2, 'març': 3, 'marc': 3, 'abril': 4, 'maig': 5, 'juny': 6,
                    'juliol': 7, 'agost': 8, 'setembre': 9, 'octubre': 10, 'novembre': 11, 'desembre': 12,
                    'enero': 1, 'febrero': 2, 'marzo': 3, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'noviembre': 11, 'diciembre': 12
                }
                df_est_work['m_num'] = df_est_work['mes'].astype(str).str.lower().str.strip().map(month_order).fillna(1).astype(int)
                df_est_work['any_num'] = pd.to_numeric(df_est_work['any'], errors='coerce').fillna(2026).astype(int)
                df_est_work['sort_score'] = df_est_work['any_num'] * 100 + df_est_work['m_num']
                df_est_sorted = df_est_work.sort_values(by='sort_score', ascending=True).copy()
                
                # Separate paid (actual) vs pending (future projection)
                mask_pagat = df_est_sorted['pagat'].astype(str).str.lower().str.strip() == 'pagat'
                df_pagats = df_est_sorted[mask_pagat]
                
                # Latest actual status (last paid record)
                if not df_pagats.empty:
                    last_paid_row = df_pagats.iloc[-1]
                    capital_rescat_actual = float(last_paid_row['rescat_val'])
                    total_aportat_actual = float(last_paid_row['aport_val'])
                    perdua_actual = float(last_paid_row['perdua_val'])
                else:
                    first_row = df_est_sorted.iloc[0]
                    capital_rescat_actual = float(first_row['rescat_val'])
                    total_aportat_actual = float(first_row['aport_val'])
                    perdua_actual = float(first_row['perdua_val'])
                
                # Final maturity objective (last row of table)
                last_row = df_est_sorted.iloc[-1]
                rescat_final = float(last_row['rescat_val'])
                
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                with col_e1:
                    st.metric("Capital Acumulat (Rescat Actual)", f"{capital_rescat_actual:,.2f} €")
                with col_e2:
                    st.metric("Total Aportat Fins Ara", f"{total_aportat_actual:,.2f} €")
                with col_e3:
                    st.metric("Rendiment / Pèrdua", f"-{perdua_actual:,.2f} €" if perdua_actual > 0 else f"+{abs(perdua_actual):,.2f} €")
                with col_e4:
                    st.metric("Previsió a Venciment", f"{rescat_final:,.2f} €", delta=f"Objectiu ({int(last_row['any_num'])})")

                # Evolution chart of accumulated savings over time
                st.markdown("<h4 style='color:#f39c12; margin-top:20px;'>📈 Evolució del Pla d'Estalvi (Aportat vs Valor de Rescat)</h4>", unsafe_allow_html=True)
                
                df_est_sorted['Period'] = df_est_sorted['mes'].astype(str).str.capitalize() + " " + df_est_sorted['any_num'].astype(str)
                
                fig_est = graph_objects.Figure()
                fig_est.add_trace(graph_objects.Scatter(
                    x=df_est_sorted['Period'],
                    y=df_est_sorted['aport_val'],
                    mode='lines',
                    name='Total Aportat (€)',
                    line=dict(color='#f1c40f', width=3),
                    hovertemplate='<b>%{x}</b><br>Total Aportat: <b>%{y:,.2f} €</b><extra></extra>'
                ))
                fig_est.add_trace(graph_objects.Scatter(
                    x=df_est_sorted['Period'],
                    y=df_est_sorted['rescat_val'],
                    mode='lines',
                    name='Valor de Rescat (€)',
                    line=dict(color='#22c55e', width=3),
                    fill='tonexty',
                    fillcolor='rgba(34, 197, 94, 0.1)',
                    hovertemplate='<b>%{x}</b><br>Valor Rescat: <b>%{y:,.2f} €</b><extra></extra>'
                ))
                fig_est.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8fafc', size=12),
                    hovermode='x unified',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis=dict(gridcolor='#334155', tickangle=-45),
                    yaxis=dict(gridcolor='#334155', ticksuffix=' €', tickformat=',.0f'),
                    margin=dict(t=20, b=30, l=10, r=10),
                    height=380
                )
                st.plotly_chart(fig_est, use_container_width=True, config={'displayModeBar': False})

                st.markdown("<h4 style='color:#f39c12; margin-top:20px;'>📋 Detall del Pla d'Amortització i Estalvi</h4>", unsafe_allow_html=True)
                df_table_show = df_est_sorted[['any_num', 'mes', 'quota_val', 'aport_val', 'rescat_val', 'perdua_val', 'pagat']].copy()
                df_table_show.rename(columns={
                    'any_num': 'Any',
                    'mes': 'Mes',
                    'quota_val': 'Quota (€)',
                    'aport_val': 'Total Aportat (€)',
                    'rescat_val': 'Valor Rescat (€)',
                    'perdua_val': 'Pèrdua/Rendiment (€)',
                    'pagat': 'Estat'
                }, inplace=True)
                st.dataframe(
                    df_table_show.style.format({
                        'Quota (€)': '{:,.2f} €',
                        'Total Aportat (€)': '{:,.2f} €',
                        'Valor Rescat (€)': '{:,.2f} €',
                        'Pèrdua/Rendiment (€)': '{:,.2f} €'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No hi ha dades registrades al pla d'estalvi.")


        # ================= TAB 4: XAT IA =================
    if tab_xat:
        with tab_xat:
            st.markdown("<h3 style='color:#f39c12;'>💬 Xat IA amb Gemini</h3>", unsafe_allow_html=True)
                
            if not has_gemini:
                st.warning("⚠️ No s'ha detectat la clau GEMINI_API_KEY als secrets. L'assistent no està disponible.")
            else:
                col_text, col_filter = st.columns([8, 4], vertical_alignment="bottom")
                with col_text:
                    st.write("Pregunta-li el que vulguis a l'assistent sobre les teves despeses, ingressos o cartera.")
                with col_filter:
                    analisi_year = st.selectbox("📅 Any a analitzar per l'IA:", years_list, index=years_list.index(selected_year) if selected_year in years_list else 0, key="sel_year_analisi")
                    
                st.info(f"💡 L'assistent està analitzant exclusivament les dades de l'any **{analisi_year}** per garantir una resposta ràpida i respectar els límits.")
                    
                # Initialize chat history
                if "messages" not in st.session_state:
                    st.session_state.messages = []
    
                from PIL import Image
                avatar_admin_img = "💼"
                if os.path.exists("imatges/avatars/avatar_administrativa.png"):
                    try:
                        avatar_admin_img = Image.open("imatges/avatars/avatar_administrativa.png")
                    except Exception:
                        pass

                # Display chat messages from history on app rerun
                for message in st.session_state.messages:
                    av = avatar_admin_img if message["role"] == "assistant" else "👤"
                    with st.chat_message(message["role"], avatar=av):
                        st.markdown(message["content"])
    
                # React to user input
                if prompt := st.chat_input("Exemple: Quant he gastat en gasolina el mes de juny?"):
                    # Display user message in chat message container
                    st.chat_message("user", avatar="👤").markdown(prompt)
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": prompt})
                        
                    with st.spinner("La Xiqui Administrativa està pensant..."):
                        try:
                            model = genai.GenerativeModel('gemini-flash-latest')
                                
                            # Prepare context using only analisi_year to drastically reduce token usage
                            year_desp_context = df_desp[df_desp['any'] == analisi_year] if 'any' in df_desp.columns else df_desp
                            year_ing_context = df_ing[df_ing['any'] == analisi_year] if 'any' in df_ing.columns else df_ing
                                
                            context = f"Tens les següents taules de dades financeres de l'any {analisi_year} en format CSV:\n\n"
                            context += "TAULA DESPESES:\n" + year_desp_context.to_csv(index=False) + "\n\n"
                            context += "TAULA INGRESSOS:\n" + year_ing_context.to_csv(index=False) + "\n\n"
                            context += "TAULA TR CARTERA:\n" + df_cartera.to_csv(index=False) + "\n\n"
                                
                            sys_prompt = "Ets la Xiqui, l'assistent financera anime de 20 anys per a XiquiHouse. Respons a les preguntes de l'usuari únicament basant-te en les dades proporcionades. Respon sempre en català de forma molt clara, amable i concisa. IMPORTANT: Respon exclusivament amb text normal, no utilitzis cap eina ni function call ni codi."
                                
                            # Generate response
                            response = model.generate_content([sys_prompt, context, prompt])
                                
                            try:
                                response_text = response.text
                            except ValueError:
                                # Safely extract parts if it threw an error
                                parts = response.candidates[0].content.parts
                                response_text = "".join([p.text for p in parts if hasattr(p, 'text')])
                                if not response_text:
                                    response_text = "L'assistent ha intentat executar codi però aquesta funció no està habilitada. Si us plau, torna a fer la pregunta."
                        except Exception as e:
                            response_text = f"❌ Error de l'API: {str(e)}"
                                
                    # Display assistant response in chat message container
                    with st.chat_message("assistant"):
                        st.markdown(response_text)
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
    
    

    # ================= EXTRA SPACE AT THE BOTTOM =================
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
