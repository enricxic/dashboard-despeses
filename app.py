import streamlit as st
import scanner
import io
import pandas as pd
import google.generativeai as genai
import json
from supabase import create_client, Client
import numpy as np
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

# Set page config
st.set_page_config(
    page_title="Dashboard Despeses",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Prevent browser from proposing page translation and hide streamlit developer badges
import streamlit.components.v1 as components
components.html(
    """
    <script>
        const doc = window.parent.document;
        doc.documentElement.classList.add("notranslate");
        doc.body.classList.add("notranslate");
        if (!doc.querySelector('meta[name="google"][content="notranslate"]')) {
            const meta = doc.createElement('meta');
            meta.name = 'google';
            meta.content = 'notranslate';
            doc.head.appendChild(meta);
        }
        
        // Hide Manage App floating element dynamically and continuously
        const hideBadges = () => {
            const badges = doc.querySelectorAll('div[class^="viewerBadge_"], .viewerBadge_container__1QS1h, .viewerBadge_link__29513, footer, [data-testid="stAppDeployButton"]');
            badges.forEach(b => b.style.display = 'none');
            
            // Also search in parent window
            const pBadges = window.parent.document.querySelectorAll('div[class^="viewerBadge_"], .viewerBadge_container__1QS1h, .viewerBadge_link__29513, footer, [data-testid="stAppDeployButton"]');
            pBadges.forEach(b => b.style.display = 'none');
        };
        hideBadges();
        setInterval(hideBadges, 300);
        
        // Target style tag injection in parent (ensures elements are hidden immediately if they are rendered)
        const style = doc.createElement('style');
        style.innerHTML = `
            footer { display: none !important; visibility: hidden !important; height: 0 !important; }
            [data-testid="stAppDeployButton"] { display: none !important; visibility: hidden !important; }
            .viewerBadge_container__1QS1h, .viewerBadge_link__29513 { display: none !important; }
            iframe[title="streamlit.components.v1.html-component"] { display: none !important; height: 0 !important; }
            div[class^="viewerBadge_"] { display: none !important; }
        `;
        doc.head.appendChild(style);
        
        // Detect if client is a desktop computer and redirect with a parameter to bypass login without stealing focus
        const ua = navigator.userAgent;
        const isMobile = /Mobi|Android|iPhone|iPad/i.test(ua);
        if (!isMobile) {
            const params = new URLSearchParams(window.parent.location.search);
            if (!params.has("device") || params.get("device") !== "desktop") {
                params.set("device", "desktop");
                window.parent.location.search = params.toString();
            }
        }
    </script>
    """,
    height=0,
    width=0
)

# Custom styles for premium look (orange/slate dark theme)
st.markdown("""
    <style>
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
    /* Hide step buttons inside number inputs */
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    /* Disable default browser spin buttons */
    input::-webkit-outer-spin-button,
    input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
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
    </style>
""", unsafe_allow_html=True)

# ----------------- SECURITY / LOGIN -----------------
# Default hashed password (sha256 of "despeses2026")
DEFAULT_HASH = "24b7b70518e4d4030003e75d68223a85b07eb95b2cf273f3b13d87c27aa2c863"

def check_password():
    if platform.system() == "Windows":
        st.session_state["authenticated"] = True
        st.session_state["role"] = "admin"
        st.session_state["username"] = "Admin Local"
        return True # Bypass login for local execution on Windows PC
        
    # Check if request is from a desktop PC (via query params, user agent or cookie)
    if st.query_params.get("device") == "desktop":
        st.session_state["authenticated"] = True
        st.session_state["role"] = "admin"
        st.session_state["username"] = "Admin Local"
        return True

    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            # 1. Check via Cookie header set by client script
            cookies = headers.get("Cookie", "")
            if "client_device_type=desktop" in cookies:
                return True
            
            # 2. Check via direct User-Agent
            ua = headers.get("User-Agent", "")
            # If it doesn't contain common mobile indicators, treat it as a PC
            if "Mobi" not in ua and "Android" not in ua and "iPhone" not in ua and "iPad" not in ua:
                return True
    except (ImportError, Exception):
        # Fallback if internal streamlit headers API changed or fails
        pass

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # For bypassed logins, assume admin by default
    if st.session_state["authenticated"] and "role" not in st.session_state:
        st.session_state["role"] = "admin"

    if st.session_state["authenticated"]:
        return True

    # Show login interface
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.markdown("<h2 style='text-align: center; color: #f39c12;'>Accés Protegit</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            # Dummy username field to trigger browser password managers
            st.text_input("Usuari / Nom", value="Admin")
            password = st.text_input("Contrasenya d'accés", type="password")
            submit = st.form_submit_button("Entrar")
            if submit:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                
                # Retrieve configured hashes from secrets (lists or strings)
                admin_hashes = st.secrets.get("admin_password_hashes", [])
                guest_hashes = st.secrets.get("guest_password_hashes", [])
                
                # Retrieve names dictionary
                mapped_names = st.secrets.get("noms_usuaris", {})
                
                if isinstance(admin_hashes, str): admin_hashes = [admin_hashes]
                if isinstance(guest_hashes, str): guest_hashes = [guest_hashes]
                
                assigned_name = mapped_names.get(hashed, "Anònim")
                
                if hashed in admin_hashes:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "admin"
                    st.session_state["username"] = assigned_name
                    st.rerun()
                elif hashed in guest_hashes:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "guest"
                    st.session_state["username"] = assigned_name
                    st.rerun()
                else:
                    st.error("Contrasenya incorrecta")
    return False

if not check_password():
    st.stop()

# --- Role Indicator ---
role_icon = "👑" if st.session_state.get("role") == "admin" else "👤"
role_title = "Administrador" if st.session_state.get("role") == "admin" else "Convidat"
username_disp = st.session_state.get("username", "Local")

st.markdown(
    f"""
    <div title="Rol: {role_title} ({username_disp})" style='position: fixed; top: 3.5rem; right: 1rem; z-index: 9999; 
                font-size: 1.8rem; cursor: help; 
                text-shadow: 0px 0px 5px rgba(255,255,255,0.8);'>
        {role_icon}
    </div>
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
    'Casa': 267.28,
    'CORTEINGLÉS': 1566.69,
    'TRADE REPUB.': 0.0,
    'Tg.Moneder': 0.0,
    'Pago VISA': -2995.45  # Calibrated for correct Debt logic (charges increase, payments decrease)
}

# Bank names in CSV mapped to display names
BANK_MAPPING = {
    'BBVA': 'BBVA',
    'LaCaixa': 'La Caixa',
    'TR Cartera': 'TR Cartera',
    'TradeRep.': 'TRADE REPUB.',
    'Casa': 'Casa',
    'T.CorteInglés': 'CORTEINGLÉS',
    't.CorteInglés': 'CORTEINGLÉS',
    'T.CorteIngles': 'CORTEINGLÉS',
    't.CorteIngles': 'CORTEINGLÉS',
    'T.Moneder': 'Tg.Moneder',
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
    count = 1000
    start = 0
    while True:
        response = client.table(table_name).select("*").range(start, start + count - 1).execute()
        data.extend(response.data)
        if len(response.data) < count:
            break
        start += count
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

@st.cache_data(ttl=300)
def load_dashboard_data(mtimes=None):
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    
    # Load tables from PostgreSQL
    df_desp = fix_mojibake_df(fetch_all_supabase(supabase, 'despeses'))
    df_desp['ID_mov'] = pd.to_numeric(df_desp['ID_mov'], errors='coerce')
    df_desp = df_desp.dropna(subset=['ID_mov']).sort_values(by='ID_mov', ascending=False).reset_index(drop=True)
    df_desp['import ingrés'] = clean_numeric(df_desp['import ingrés'])
    df_desp['Import càrrec'] = clean_numeric(df_desp['Import càrrec'])
    df_desp['parsed_date'] = df_desp['Data'].apply(parse_excel_date)
    df_desp['date_score'] = df_desp['any'] * 12 + df_desp['mes'].astype(str).str.lower().map(MONTHS_MAP).fillna(12).astype(int)
    
    df_ing = fix_mojibake_df(fetch_all_supabase(supabase, 'ingressos'))
    df_ing['idIngres'] = pd.to_numeric(df_ing['idIngres'], errors='coerce')
    df_ing = df_ing.dropna(subset=['idIngres']).sort_values(by='idIngres', ascending=False).reset_index(drop=True)
    df_ing['Import'] = clean_numeric(df_ing['Import'])
    df_ing['parsed_date'] = df_ing['Data'].apply(parse_excel_date)
    
    df_super = fix_mojibake_df(fetch_all_supabase(supabase, 'compresSuper'))
    df_super['IdCompra'] = pd.to_numeric(df_super['IdCompra'], errors='coerce')
    df_super = df_super.dropna(subset=['IdCompra']).sort_values(by='IdCompra', ascending=False).reset_index(drop=True)
    df_super['totLinea'] = clean_numeric(df_super['totLinea'])
    df_super['parsed_date'] = df_super['data'].apply(parse_excel_date)
    
    df_gas = fix_mojibake_df(fetch_all_supabase(supabase, 'gasolina'))
    df_gas['idGasolina'] = pd.to_numeric(df_gas['idGasolina'], errors='coerce')
    df_gas = df_gas.dropna(subset=['idGasolina']).sort_values(by='idGasolina', ascending=False).reset_index(drop=True)
    df_gas['import'] = clean_numeric(df_gas['import'])
    df_gas['litres'] = clean_numeric(df_gas['litres'])
    df_gas['parsed_date'] = df_gas['data'].apply(parse_excel_date)
    
    df_km = fix_mojibake_df(fetch_all_supabase(supabase, 'kmCotxe'))
    df_km['idRuta'] = pd.to_numeric(df_km['idRuta'], errors='coerce')
    df_km = df_km.dropna(subset=['idRuta']).sort_values(by='idRuta', ascending=False).reset_index(drop=True)
    df_km['contador'] = clean_numeric(df_km['contador'])
    df_km['km'] = clean_numeric(df_km['km'])
    df_km['parsed_date'] = df_km['data'].apply(parse_excel_date)
    
    df_hip = fetch_all_supabase(supabase, 'hipoteca').dropna(how='all')
    if 'Quota fixa' in df_hip.columns:
        df_hip = df_hip.dropna(subset=['Quota fixa'])
    df_hip['Quota fixa'] = clean_numeric(df_hip['Quota fixa'])
    
    df_cartera = fix_mojibake_df(fetch_all_supabase(supabase, 'tr_cartera'))
    df_cartera['idTRCartera'] = pd.to_numeric(df_cartera.get('idTRCartera', df_cartera.index), errors='coerce')
    df_cartera = df_cartera.dropna(subset=['idTRCartera']).sort_values(by='idTRCartera', ascending=False).reset_index(drop=True)
    df_cartera['COMPRA'] = clean_numeric(df_cartera.get('COMPRA', 0))
    df_cartera['VENDA'] = clean_numeric(df_cartera.get('VENDA', 0))
    df_cartera['parsed_date'] = df_cartera.get('DATA', pd.Series(dtype=object)).apply(parse_excel_date)
    
    df_est = fetch_all_supabase(supabase, 'estalviDP')
    df_est = df_est.dropna(subset=['mes', 'any'])
    df_est['any'] = pd.to_numeric(df_est['any'], errors='coerce')
    df_est['quota'] = clean_numeric(df_est['quota'])
    if 'aportació' in df_est.columns:
        df_est['aportació'] = clean_numeric(df_est['aportació'])
    if 'rescat' in df_est.columns:
        df_est['rescat'] = clean_numeric(df_est['rescat'])
    if 'pérdua' in df_est.columns:
        df_est['pérdua'] = clean_numeric(df_est['pérdua'])
    
    df_limits = fetch_all_supabase(supabase, 'limitsDespeses').dropna(subset=['data_inici'])
    df_limits['parsed_date'] = df_limits['data_inici'].apply(parse_excel_date)
    
    df_pag = fetch_all_supabase(supabase, 'pagaments')
    df_pag = df_pag.dropna(subset=['idPago'])
    df_pag['Import'] = clean_numeric(df_pag['Import'])
    df_pag['parsed_date'] = df_pag['Data'].apply(parse_excel_date)
    
    return df_desp, df_ing, df_super, df_gas, df_km, df_hip, df_est, df_limits, df_pag, df_cartera

# Load categories_conceptes.json if exists
import json

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
    if cat_config:
        special_keys = ["families_compres", "articles_compres", "bancs", "formes_pago", "supers_tickets"]
        return sorted([k for k in cat_config.keys() if k not in special_keys])
    return sorted(list(df_desp['Idcategoria'].dropna().unique()))

def get_config_concepts(category):
    if cat_config and category in cat_config:
        return sorted(cat_config[category])
    return sorted(list(df_desp[df_desp['Idcategoria'] == category]['Idconcepte'].dropna().unique()))

def get_config_banks():
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
        supabase = get_supabase_client("guest")
        return fetch_all_supabase(supabase, 'tb_productes')
    except:
        return pd.DataFrame()

def get_config_families():
    df_prod = get_tb_productes_cached()
    if not df_prod.empty and 'familia' in df_prod.columns:
        return sorted(list(df_prod['familia'].dropna().unique()))
    if cat_config and "families_compres" in cat_config:
        return cat_config["families_compres"]
    return sorted(list(df_super['familia'].dropna().unique())) if 'familia' in df_super.columns else []

def get_config_articles(family):
    df_prod = get_tb_productes_cached()
    if not df_prod.empty and 'familia' in df_prod.columns and 'nom_estandard' in df_prod.columns:
        articles = df_prod[df_prod['familia'] == family]['nom_estandard'].dropna().unique()
        if len(articles) > 0:
            return sorted(list(articles))
    if cat_config and "articles_compres" in cat_config and family in cat_config["articles_compres"]:
        return cat_config["articles_compres"][family]
    return sorted(list(df_super[df_super['familia'] == family]['article'].dropna().unique())) if 'article' in df_super.columns else []
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
        return True
    except Exception as e:
        st.error(f"❌ **Error al desar la taula `{table_name}` a Supabase**: {str(e)}")
        st.stop()

def log_action(table_name, tipus_accio, detalls):
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    try:
        log_payload = {
            "usuari": st.session_state.get("username", "Desconegut"),
            "rol": st.session_state.get("role", "guest"),
            "taula_afectada": table_name,
            "tipus_accio": tipus_accio,
            "detalls": detalls
        }
        # Log unrestrictedly using anonymous push or admin push (handled by RLS policies)
        supabase.table("registre_accions").insert(log_payload).execute()
    except Exception as e:
        # Silently fail if logging fails
        pass

def insert_db_row(table_name, new_row_dict):
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    try:
        supabase.table(table_name).insert(new_row_dict).execute()
        log_action(table_name, 'INSERT', new_row_dict)
        
        st.cache_data.clear()
        get_db_tracker().update()
        st.session_state["dfs_initialized"] = False
        return True
    except Exception as e:
        st.error(f"❌ Error al desar a Supabase ({table_name}): {str(e)}")

def append_to_db(df_new, table_name, state_key):
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    try:
        supabase.table(table_name).insert(json.loads(df_new.to_json(orient='records', date_format='iso'))).execute()
        details = {'count': len(df_new)}
        if table_name == 'compresSuper' and 'super' in df_new.columns:
            supers = df_new['super'].unique().tolist()
            details['supermercat'] = supers[0] if len(supers) == 1 else supers
        log_action(table_name, 'INSERT_BULK', details)
        
        st.cache_data.clear()
        if state_key and state_key in st.session_state:
            del st.session_state[state_key]
            
        tracker_obj = get_db_tracker()
        tracker_obj.update()
        st.session_state["dfs_initialized"] = False
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
    try:
        supabase.table(table_name).delete().eq(id_col, id_val).execute()
        log_action(table_name, 'DELETE', {'id_col': id_col, 'id_val': id_val})
        
        st.cache_data.clear()
        get_db_tracker().update()
        st.session_state["dfs_initialized"] = False
        return True
    except Exception as e:
        st.error(f"❌ Error a l'esborrar de Supabase ({table_name}): {str(e)}")

def update_db_row(table_name, id_col, id_val, new_data):
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    try:
        update_payload = new_data.copy()
        if id_col in update_payload:
            del update_payload[id_col]
            
        import pandas as pd
        for k, v in update_payload.items():
            if pd.isna(v):
                update_payload[k] = None
                
        supabase.table(table_name).update(update_payload).eq(id_col, id_val).execute()
        log_action(table_name, 'UPDATE', {'id_col': id_col, 'id_val': id_val, 'changes': update_payload})
        
        st.cache_data.clear()
        get_db_tracker().update()
        st.session_state["dfs_initialized"] = False
        return True
    except Exception as e:
        print(f"FAILED PAYLOAD FOR {table_name}:", update_payload)
        st.error(f"❌ Error a l'actualitzar Supabase ({table_name}): {str(e)}")

tracker = get_db_tracker()
if "last_synced_time" not in st.session_state or not isinstance(st.session_state["last_synced_time"], datetime) or st.session_state["last_synced_time"] < tracker.last_update:
    st.session_state["dfs_initialized"] = False

if "dfs_initialized" not in st.session_state or not st.session_state["dfs_initialized"]:
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
    st.session_state["dfs_initialized"] = True
    st.session_state["last_synced_time"] = tracker.last_update

df_desp = st.session_state["df_desp"]
df_ing = st.session_state["df_ing"]
df_super = st.session_state["df_super"]
df_gas = st.session_state["df_gas"]
df_km = st.session_state["df_km"]
df_hip = st.session_state["df_hip"]
df_est = st.session_state["df_est"]
df_limits = st.session_state["df_limits"]
df_pag = st.session_state["df_pag"]
df_cartera = st.session_state.get("df_cartera", pd.DataFrame())

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


# ----------------- TICKET SUPER FUNCTIONALITY -----------------
def normalitzar_text(text):
    if not text:
        return ""
    text_str = str(text)
    
    # Fix common OCR mistakes specifically inside words
    # Replace numbers with letters if they look like letters (like 4MB -> AMB, xISGR4 -> XISTORRA, etc.)
    text_str = re.sub(r'\b4MB\b', 'AMB', text_str, flags=re.IGNORECASE)
    text_str = re.sub(r'\b4\b', 'A', text_str, flags=re.IGNORECASE)
    text_str = re.sub(r'xISGR\s*4', 'XISTORRA', text_str, flags=re.IGNORECASE)
    text_str = re.sub(r'xISG\s*R\s*4', 'XISTORRA', text_str, flags=re.IGNORECASE)
    
    import unicodedata
    text_normalitzat = unicodedata.normalize('NFKD', text_str)
    text_sense_diacritics = ''.join(
        c for c in text_normalitzat 
        if not unicodedata.combining(c) and (c.isalnum() or c.isspace())
    )
    return re.sub(r'\s+', ' ', text_sense_diacritics.lower()).strip()

def translate_spanish_to_catalan_for_matching(text):
    text_lower = text.lower()
    translations = {
        'chocolate': 'xocolata',
        'maiz': 'blat de moro',
        'maíz': 'blat de moro',
        'lavavaj': 'rentavaixella',
        'pistacho': 'festuc',
        'conservas': 'sardina',
        'pasta': 'helixs',
        'ocolate': 'xocolata',
    }
    for es, ca in translations.items():
        if es in text_lower:
            text_lower = text_lower.replace(es, ca)
    return text_lower

def map_product_to_category(product_name):
    best_family = "extres"
    best_article = "varis"
    prod_norm = normalitzar_text(product_name)
    
    # Custom OCR repair rules
    if 'tation' in prod_norm or 'temptation' in prod_norm or 'vche' in prod_norm or 'cry' in prod_norm or 'cons nata' in prod_norm:
        return 'extres', 'Gelat'
    if 'seberg' in prod_norm or 'ent am' in prod_norm or 'ciame' in prod_norm or 'enciam' in prod_norm or 'iceberg' in prod_norm:
        return 'verdura', 'Enciam'
    if 'tomaquet' in prod_norm or 'xcemat' in prod_norm or 'xocmat' in prod_norm:
        return 'verdura', 'Tomàquet'
    if 'pebrot' in prod_norm or 'vermell' in prod_norm or 'vermel' in prod_norm or ('2.19' in prod_norm and 'k' in prod_norm) or ('2,19' in prod_norm and 'k' in prod_norm):
        return 'verdura', 'Pebrot'
    if 'melo' in prod_norm or ('1.29' in prod_norm and 'k' in prod_norm) or ('1,29' in prod_norm and 'k' in prod_norm):
        return 'fruita', 'Meló'
    if 'pit' in prod_norm and ('gall' in prod_norm or 'dindi' in prod_norm or 'gal' in prod_norm or 'pinnt' in prod_norm):
        return 'carn', 'Pit Gall dindi'
    if 'trol' in prod_norm or 'truita' in prod_norm or 'tntegral' in prod_norm:
        return 'verdura', 'Amanida' # Maps to the standard family for Truita/Amanida if not exact
    if 'suetatl' in prod_norm or 'lleixiu' in prod_norm:
        return 'neteja', 'Leixiu'
    if 'sunder' in prod_norm or 'sindria' in prod_norm:
        return 'fruita', 'Xindria'
    if 'mantogs' in prod_norm or 'mantega' in prod_norm:
        return 'lactics', 'Mantega'
    if 'rmse' in prod_norm or 'formatge' in prod_norm or 'untar' in prod_norm:
        return 'lactics', 'Formatge'

    articles_map = cat_config.get("articles_compres", {})
    for fam, articles in articles_map.items():
        for art in articles:
            art_norm = normalitzar_text(art)
            if len(art_norm) <= 3:
                if re.search(r'\b' + re.escape(art_norm) + r'\b', prod_norm):
                    return fam, art
            else:
                if art_norm in prod_norm or prod_norm in art_norm:
                    return fam, art
                    
    for fam in cat_config.get("families_compres", []):
        fam_norm = normalitzar_text(fam)
        if len(fam_norm) <= 3:
            if re.search(r'\b' + re.escape(fam_norm) + r'\b', prod_norm):
                articles = articles_map.get(fam, ["varis"])
                return fam, articles[0]
        else:
            if fam_norm in prod_norm:
                articles = articles_map.get(fam, ["varis"])
                return fam, articles[0]
                
    return best_family, best_article
 
def load_product_mappings():
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_nom = fetch_all_supabase(supabase, 'tb_noms_producte')
        df_prod = fetch_all_supabase(supabase, 'tb_productes')
        df_merged = pd.merge(df_nom, df_prod, on='idProducte', how='inner')
        return df_merged
    except Exception as e:
        print(f"Error loading product mappings from database: {e}")
        return pd.DataFrame()
 
def find_product_in_db(product_name, supermercat, df_mapping):
    if df_mapping.empty or not product_name:
        return None
        
    nom_norm = normalitzar_text(product_name)
    if not nom_norm:
        return None
        
    # Filter by supermercat first (case-insensitive)
    df_super = df_mapping[df_mapping['supermercat'].astype(str).str.lower() == str(supermercat).lower()]
    if df_super.empty:
        df_super = df_mapping
        
    # 1. Exact match on nom_super
    for _, row in df_super.iterrows():
        if nom_norm == normalitzar_text(row['nom_super']):
            return {
                'nomEstandard': row['nom_estandard'],
                'familia': row['familia'],
                'article': row['nom_estandard'],
                'nom_super': row['nom_super']
            }
            
    # 2. Partial match on nom_super (one contains the other)
    for _, row in df_super.iterrows():
        super_norm = normalitzar_text(row['nom_super'])
        if super_norm in nom_norm or nom_norm in super_norm:
            return {
                'nomEstandard': row['nom_estandard'],
                'familia': row['familia'],
                'article': row['nom_estandard'],
                'nom_super': row['nom_super']
            }
            
    # 3. Direct match on nom_estandard (standard product name)
    for _, row in df_super.iterrows():
        est_norm = normalitzar_text(row['nom_estandard'])
        if nom_norm == est_norm or est_norm in nom_norm or nom_norm in est_norm:
            return {
                'nomEstandard': row['nom_estandard'],
                'familia': row['familia'],
                'article': row['nom_estandard'],
                'nom_super': row['nom_super']
            }
            
    # 4. Keyword / Word matching (similar to ocr_ticket.py)
    paraules_nom = set(nom_norm.split())
    best_word_match = None
    best_word_ratio = 0.0
    for _, row in df_super.iterrows():
        super_norm = normalitzar_text(row['nom_super'])
        paraules_super = set(super_norm.split())
        
        # Count matching words (length >= 2)
        coincidencies = 0
        for p_nom in paraules_nom:
            if len(p_nom) < 2:
                continue
            for p_super in paraules_super:
                if len(p_super) < 2:
                    continue
                if p_nom == p_super or (len(p_nom) > 4 and len(p_super) > 4 and (p_nom in p_super or p_super in p_nom)):
                    coincidencies += 1
                    break
        
        if len(paraules_nom) > 0:
            ratio = coincidencies / len(paraules_nom)
        else:
            ratio = 0.0
            
        if ratio > best_word_ratio and ratio >= 0.5:
            best_word_ratio = ratio
            best_word_match = row

    if best_word_match is not None:
        return {
            'nomEstandard': best_word_match['nom_estandard'],
            'familia': best_word_match['familia'],
            'article': best_word_match['nom_estandard'],
            'nom_super': best_word_match['nom_super']
        }

    # 5. Fuzzy match using SequenceMatcher (similarity >= 0.7)
    import difflib
    best_match = None
    best_ratio = 0.0
    for _, row in df_super.iterrows():
        super_norm = normalitzar_text(row['nom_super'])
        ratio = difflib.SequenceMatcher(None, nom_norm, super_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = row
            
    if best_ratio >= 0.60:  # Set to a robust 0.60 since the new preprocessing is very clean
        return {
            'nomEstandard': best_match['nom_estandard'],
            'familia': best_match['familia'],
            'article': best_match['nom_estandard'],
            'nom_super': best_match['nom_super']
        }
            
    # 6. Global match fallback (ignore supermarket filter)
    if len(df_super) < len(df_mapping):
        for _, row in df_mapping.iterrows():
            super_norm = normalitzar_text(row['nom_super'])
            if nom_norm == super_norm or super_norm in nom_norm or nom_norm in super_norm:
                return {
                    'nomEstandard': row['nom_estandard'],
                    'familia': row['familia'],
                    'article': row['nom_estandard'],
                    'nom_super': row['nom_super']
                }
            est_norm = normalitzar_text(row['nom_estandard'])
            if nom_norm == est_norm or est_norm in nom_norm or nom_norm in est_norm:
                return {
                    'nomEstandard': row['nom_estandard'],
                    'familia': row['familia'],
                    'article': row['nom_estandard'],
                    'nom_super': row['nom_super']
                }
                
    return None

def group_duplicate_ticket_items(items):
    grouped = {}
    for i, item in enumerate(items):
        if item['article'] == 'pendent':
            key = (item['familia'], item['article'], item['preuUnit'], i)
        else:
            key = (item['familia'], item['article'], item['preuUnit'])
        
        if key not in grouped:
            grouped[key] = {
                'familia': item['familia'],
                'article': item['article'],
                'pes': item['pes'],
                'quantitat': item['quantitat'],
                'preuUnit': item['preuUnit'],
                'prom': item['prom'],
                'totLinea': item['totLinea'],
                'rebost': item['rebost'],
                'nom_brut': item.get('nom_brut', '')
            }
        else:
            grouped[key]['quantitat'] += item['quantitat']
            try:
                grouped[key]['pes'] = float(grouped[key]['pes']) + float(item['pes'])
            except Exception:
                val1 = str(grouped[key]['pes'])
                val2 = str(item['pes'])
                grouped[key]['pes'] = val1 if val1 == val2 else f"{val1}, {val2}"
            grouped[key]['prom'] += item['prom']
            grouped[key]['totLinea'] += item['totLinea']
    return list(grouped.values())


def save_unknown_products(parsed_items, supermercat):
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_nom = fetch_all_supabase(supabase, 'tb_noms_producte')
        
        if not df_nom.empty:
            df_super = df_nom[df_nom['supermercat'].astype(str).str.lower() == str(supermercat).lower()]
            existing_names = set(df_super['nom_super'].dropna().apply(lambda x: normalitzar_text(x)))
        else:
            existing_names = set()
            
        new_rows = []
        for item in parsed_items:
            nom_brut = item.get('nom_brut', '').strip()
            if not nom_brut:
                continue
                
            nom_norm = normalitzar_text(nom_brut)
            if not nom_norm:
                continue
                
            # If not in existing names, we need to add it
            if nom_norm not in existing_names:
                new_rows.append({
                    "supermercat": supermercat,
                    "nom_super": nom_brut,
                    "similitud_minima": 0.7,
                    "idProducte": None,
                    "tipus": None,
                    "unitat": None,
                    "mesura": None
                })
                existing_names.add(nom_norm)
                
        if new_rows:
            supabase.table("tb_noms_producte").insert(new_rows).execute()
            print(f"Saved {len(new_rows)} new unknown products to tb_noms_producte for {supermercat}.")
    except Exception as e:
        print(f"Error saving unknown products: {e}")

def parse_default_ticket(text_content):
    # Log Streamlit OCR text
    try:
        import os
        os.makedirs("C:/Users/Usuari/.gemini/antigravity/brain/98896f4c-68da-443a-b920-acd856bccd79/scratch", exist_ok=True)
        with open("C:/Users/Usuari/.gemini/antigravity/brain/98896f4c-68da-443a-b920-acd856bccd79/scratch/debug_ocr.log", "w", encoding="utf-8") as f_log:
            f_log.write("--- NEW PARSE ---\n")
            f_log.write(text_content)
            f_log.write("\n-----------------\n")
    except Exception as e_log:
        pass
        
    df_mapping = load_product_mappings()
    lines = text_content.split('\n')
    
    try:
        st.session_state["ticket_discount"] = 0.0
    except Exception:
        pass
    
    # 1. Determine scan zone: between headers and TOTAL COMPRA GRUPO DIA / OFERTES
    in_products_zone = False
    product_lines_text = []
    coupon_lines_text = []
    in_coupons_zone = False
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        line_upper = line_clean.upper()
        
        # End zone check
        if (any(kw in line_upper for kw in [
            'TOTAL COMPRA', 'TOTAL A PAGAR', 'TOTAL ESTALVI', 'TOTAL ESTALVE', 
            'TOTAL COMPRA GRUPO DIA', 'TOTAL COMPRA GRUPC CTA', 'TOTAL', 
            'TARGETA', 'TARGETA BANCÀRIA', 'TARJETA', 'TUTAL', 'TAROETA', 
            'BANCARTA', 'BANCARIA', 'BASE IMPOSABLE', 'IVA BASE', 'VISA', 
            'DEBIT', 'DEBITE', 'IMPORT:', "DESGLÒS D'IVA", "DESGLOS D'IVA", 'EFECTIU', 'CANVI', 'ENTREGAT', 'IVA %', 'SUBTOTAL', 'IVA INCLOS', 'I.V.A.'
        ]) or any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in [
            'TOTAL COMPRA', 'TOTAL A PAGAR', 'TOTAL ESTALVI', 'TOTAL ESTALVE', 
            'TOTAL COMPRA GRUPO DIA', 'TOTAL COMPRA GRUPC CTA', 'TOTAL', 
            'TARGETA', 'TARGETA BANCÀRIA', 'TARJETA'
        ])):
            break
            
        # Coupons zone transition check
        if any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in ['OFERTES', 'OFERTAS', 'CUPONS', 'CLUBDIA', 'CPERTLS']):
            in_coupons_zone = True
            continue
            
        if in_coupons_zone:
            coupon_lines_text.append(line_clean)
            continue
            
        # Header check to start scan zone
        if not in_products_zone:
            if any(kw in line_upper for kw in ['DESCRIPCIÓ', 'DESCRIPCION', 'QUANTITAT', 'PVP/UNIT', 'IMPORT €', 'DESCRIPC', 'DESCRIPCI', 'VSPRIPC', 'P.UNIT', 'IMP.']):
                in_products_zone = True
            continue
            
        if in_products_zone:
            # Skip duplicate headers
            if any(kw in line_upper for kw in ['DESCRIPCIÓ', 'DESCRIPCION', 'QUANTITAT', 'PVP/UNIT', 'IMPORT €', 'DESCRIPC', 'DESCRIPCI', 'QA TA PAP']):
                continue
            product_lines_text.append(line_clean)
            
    # Fallback: if header detection failed to capture any product lines, treat all lines before coupons/totals as products
    if len(product_lines_text) == 0:
        in_coupons_zone = False
        coupon_lines_text = []
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            line_upper = line_clean.upper()
            if any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in ['TOTAL COMPRA', 'TOTAL A PAGAR', 'TOTAL ESTALVI', 'TOTAL ESTALVE', 'TOTAL COMPRA GRUPO DIA', 'TOTAL COMPRA GRUPC CTA']):
                break
            if any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in ['OFERTES', 'OFERTAS', 'CUPONS', 'CLUBDIA', 'CPERTLS']):
                in_coupons_zone = True
                continue
            if in_coupons_zone:
                coupon_lines_text.append(line_clean)
                continue
            # Skip typical header/metadata lines
            if any(kw in line_upper for kw in ['GRUPO', 'OBRIM', 'HORARI', 'FACTURA', 'N.FACT', 'N.CAIXA', 'N.CATXA', 'TELF', 'TEL.']):
                continue
            product_lines_text.append(line_clean)
            
    # 2. Sequential scanning to count and group lines (product + optional weight line)
    raw_products = []
    idx = 0
    while idx < len(product_lines_text):
        line = product_lines_text[idx]
        line_upper = line.upper()
        
        # Check if it has a price
        preu = 0.0
        price_match = None
        bonarea_qty = 1
        bonarea_match = re.search(r'^(.*?)\s+(?:(\d+)\s*[xX]\s*\d+[,.]\d+\s+)?(\d+)[.,](\d{2})\s+\d+[.,]\d{2}$', line.strip())
        
        if bonarea_match:
            nom_brut = bonarea_match.group(1).replace('.', '').strip()
            if bonarea_match.group(2):
                bonarea_qty = int(bonarea_match.group(2))
            preu = float(f"{bonarea_match.group(3)}.{bonarea_match.group(4)}")
            price_match = bonarea_match
        else:
            # Dia tickets have a price followed by IVA letter (A, B, C). OCR sometimes reads A as 4 or 4/A, B as 8 or 3, etc.
            # Price check with optional trailing IVA character and optional dashes/spaces
            price_match_std = re.search(r'(\d+)\s*[\.,\s;:]\s*(\d{2})(?:\s*[A-Z834\-©]+)?\s*[^a-zA-Z0-9]*$', line.strip())
            if price_match_std:
                preu = float(f"{price_match_std.group(1)}.{price_match_std.group(2)}")
                price_match = price_match_std
            else:
                # Fallback for three/four digits with missed separator, e.g. 222A -> 2.22
                price_match_missed = re.search(r'\s+(\d+)(\d{2})(?:\s*[A-Z834\-©]+)?\s*[^a-zA-Z0-9]*$', line.strip())
                if price_match_missed:
                    preu = float(f"{price_match_missed.group(1)}.{price_match_missed.group(2)}")
                    if preu > 50.0:
                        preu = 0.0
                        price_match = None
                    price_match = price_match_missed
                else:
                    # Fallback for letters like O/G/0 at start of cents (e.g. G95 -> 0.95, G95 - -> 0.95)
                    g_match = re.search(r'\b[GgOo0]\s*[\.,\s;:]*\s*(\d{2})(?:\s*[A-Z834\-©]+)?\s*[^a-zA-Z0-9]*$', line.strip())
                    if g_match:
                        preu = float(f"0.{g_match.group(1)}")
                        price_match = g_match
                
        # Parse product name
        if price_match and not bonarea_match:
            nom_brut = line[:price_match.start()].strip()
        elif not bonarea_match:
            nom_brut = line
            
        # Clean trailing letters/spaces/noise and specifically Dia IVA trailing characters/garbage
        nom_brut = re.sub(r'[\s\-\+\|0-9]+$', '', nom_brut).strip()
        nom_brut = re.sub(r'\s+[A-Z834]$', '', nom_brut).strip()
        nom_brut = re.sub(r'\s+[a-zA-Z]$', '', nom_brut).strip() # strip single trailing letter representing IVA if any left
        
        # Check if the line is a void/annulment (starts with ANUL. or has negative price)
        is_void = False
        if 'ANUL.' in line_upper or 'ANULACIO' in line_upper:
            is_void = True
            nom_brut = re.sub(r'^\s*ANUL\b\.?\s*', '', nom_brut, flags=re.IGNORECASE).strip()
            nom_brut = re.sub(r'^\s*ANULACIO\b\.?\s*', '', nom_brut, flags=re.IGNORECASE).strip()
            
        if price_match:
            prefix = line[:price_match.start()].strip()
            if prefix.endswith('-'):
                is_void = True
                nom_brut = re.sub(r'\s*\-$', '', nom_brut).strip()
                
        # Skip typical "Import linia: 2,98" metadata lines
        if 'IMPORT LIN' in nom_brut.upper():
            idx += 1
            continue
            
        if not nom_brut or len(nom_brut) < 2:
            idx += 1
            continue
            
        # Skip Novavenda barcode + quantity lines (e.g. "5449000275165 1 x ")
        if re.match(r'^\d{7,14}\s+\d+\s*[xX]$', nom_brut):
            idx += 1
            continue
            
        # Check if the NEXT line is a weight line (starts with digit and contains 'kg')
        pes_kg = 0.0
        tot_val = 0.0
        extracted_preu_kg = 0.0
        has_next_weight = False
        if idx + 1 < len(product_lines_text):
            next_line = product_lines_text[idx + 1]
            if 'kg' in next_line.lower() or 'e/kg' in next_line.lower() or '/kg' in next_line.lower():
                pes_match = re.search(r'(\d+[\.,]\d{3})', next_line)
                if pes_match:
                    pes_kg = float(pes_match.group(1).replace(',', '.'))
                    
                # Extract preu_kg and totLine value from weight line
                match_kg_price = re.search(r'(\d+[\.,]\d{2})\s*(?:€/kg|/kg)', next_line, re.IGNORECASE)
                if match_kg_price:
                    extracted_preu_kg = float(match_kg_price.group(1).replace(',', '.'))
                else:
                    extracted_preu_kg = 0.0
                    
                # The total is usually the last number with exactly 2 decimals (ignoring the 3 decimal weight)
                prices_match = list(re.finditer(r'(\d+)[\.,](\d{2})(?!\d)', next_line))
                if prices_match:
                    last_price = float(f"{prices_match[-1].group(1)}.{prices_match[-1].group(2)}")
                    if match_kg_price and prices_match[-1].start() == match_kg_price.start(1):
                        # The last price found IS the kg price, which means total price is missing from this line
                        tot_val = round(pes_kg * extracted_preu_kg, 2)
                    else:
                        tot_val = last_price
                elif extracted_preu_kg > 0 and pes_kg > 0:
                    tot_val = round(pes_kg * extracted_preu_kg, 2)
                else:
                    tot_val = 0.0
                has_next_weight = True
                
        # Resolve quantities (e.g. '3 x' or just '3 ' at start of line for Mercadona)
        if bonarea_match:
            quantitat = bonarea_qty
        else:
            quantitat = 1
        quant_match = re.search(r'^(\d+)\s*[xX]\s*', nom_brut)
        if quant_match:
            quantitat = int(quant_match.group(1))
            nom_brut = re.sub(r'^(\d+)\s*[xX]\s*', '', nom_brut).strip()
        else:
            # Check for Mercadona style: starts with a number and then space, e.g., "1 PASTÍS TONYINA"
            # We map 'l', 'i', 'I', '1' to 1
            mercadona_quant_match = re.search(r'^([1liI]|\d+)\s+(?![gG]\b|[kK][gG]\b|[mM][lL]\b)([a-zA-Z].*)', nom_brut)
            if mercadona_quant_match:
                q_val = mercadona_quant_match.group(1)
                if q_val in ['l', 'i', 'I', '1']:
                    quantitat = 1
                else:
                    quantitat = int(q_val)
                nom_brut = mercadona_quant_match.group(2).strip()
            
        # 3. Search in TBNomsProducte and match against TBProductes (via df_mapping)
        ticket_super = st.session_state.get("ticket_super_val", "Dia")
        
        # Look up in DB first to check for high confidence match
        db_match = find_product_in_db(nom_brut, ticket_super, df_mapping)
        nom_super_val = ""
        if db_match:
            fam, art = db_match['familia'], db_match['nomEstandard']
            nom_super_val = db_match.get('nom_super', '')
        else:
            fam, art = 'Pendent', 'pendent'
            nom_super_val = nom_brut

        if has_next_weight:
            preu_unitat = round(tot_val / quantitat, 2) if tot_val > 0.0 else 0.0
            import_total = tot_val
        else:
            preu_unitat = preu if preu > 0.0 else (round(tot_val / quantitat, 2) if tot_val > 0.0 else 0.0)
            import_total = quantitat * preu_unitat
        
        if preu_unitat > 1000.0:
            preu_unitat = 0.0
        if import_total > 1000.0:
            import_total = 0.0
        # Duplicate product price fallback
        if preu_unitat == 0.0 and len(raw_products) > 0:
            prev_item = raw_products[-1]
            if prev_item['article'] == art and art != 'pendent' and prev_item['preuUnit'] > 0.0:
                preu_unitat = prev_item['preuUnit']
                
        if is_void:
            quantitat = -quantitat
            import_total = -import_total
        
        raw_products.append({
            'familia': fam,
            'article': art,
            'pes': int(pes_kg * 1000) if pes_kg > 0.0 else 0,
            'quantitat': quantitat,
            'preuUnit': preu_unitat,
            'prom': 0.0,
            'totLinea': import_total,
            'rebost': None,
            'nom_brut': nom_brut,
            'nom_super': nom_super_val
        })
        
        idx += 2 if has_next_weight else 1
        
    # 4. Parse discounts and coupons
    discounts = []
    for line in coupon_lines_text:
        discount_match = re.search(r'([\-\+]\s*\d+[\.,]\d{2})', line)
        if discount_match:
            val = abs(float(re.sub(r'\s+', '', discount_match.group(1)).replace(',', '.')))
            desc_text = line[:discount_match.start()].strip()
            desc_text = re.sub(r'^[\s\-\+\|0OCoO%0-9\.]+', '', desc_text).strip()
            discounts.append({'text': desc_text, 'val': val})
            
    # Apply discounts to parsed products
    for disc in discounts:
        disc_text = disc['text'].lower()
        disc_text_ca = translate_spanish_to_catalan_for_matching(disc_text)
        best_match_idx = -1
        best_ratio = 0.0
        
        for idx, item in enumerate(raw_products):
            art_lower = item['article'].lower()
            orig_lower = item['nom_brut'].lower()
            super_lower = item.get('nom_super', '').lower()
            
            ratio_std = max(
                difflib.SequenceMatcher(None, disc_text, art_lower).ratio(),
                difflib.SequenceMatcher(None, disc_text_ca, art_lower).ratio()
            )
            ratio_orig = max(
                difflib.SequenceMatcher(None, disc_text, orig_lower).ratio(),
                difflib.SequenceMatcher(None, disc_text_ca, orig_lower).ratio()
            )
            ratio_super = 0.0
            if super_lower:
                ratio_super = max(
                    difflib.SequenceMatcher(None, disc_text, super_lower).ratio(),
                    difflib.SequenceMatcher(None, disc_text_ca, super_lower).ratio()
                )
            
            ratio = max(ratio_std, ratio_orig, ratio_super)
            
            # Substring bonus for words >= 4 characters
            if len(disc_text) >= 4:
                if (disc_text in art_lower or disc_text_ca in art_lower or 
                    disc_text in orig_lower or disc_text_ca in orig_lower or
                    (super_lower and (disc_text in super_lower or disc_text_ca in super_lower))):
                    ratio = max(ratio, 0.95)
                    
            # Substring bonus for clean keywords of discount (e.g. split and check)
            clean_words = [w for w in re.split(r'[^a-zA-Z0-9]', disc_text_ca) if len(w) >= 4]
            for w in clean_words:
                if w in art_lower or w in orig_lower or (super_lower and w in super_lower):
                    ratio = max(ratio, 0.90)
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_idx = idx
                
        if best_ratio >= 0.4:
            raw_products[best_match_idx]['prom'] += disc['val']
            raw_products[best_match_idx]['totLinea'] = max(0.0, (raw_products[best_match_idx]['quantitat'] * raw_products[best_match_idx]['preuUnit']) - raw_products[best_match_idx]['prom'])
            
    # Keep recognized items even with 0.0 price, but discard 'pendent' with 0.0 or negative price (typically garbage lines)
    raw_products = [item for item in raw_products if item['article'] != 'pendent' or item['totLinea'] > 0.0]
    
    # 5. Sum duplicate products
    res = group_duplicate_ticket_items(raw_products)
    res = [item for item in res if item['quantitat'] > 0]
    try:
        with open("C:/Users/Usuari/.gemini/antigravity/brain/98896f4c-68da-443a-b920-acd856bccd79/scratch/debug_ocr.log", "a", encoding="utf-8") as f_log:
            f_log.write(f"\nCollected products zone lines: {len(product_lines_text)}\n")
            f_log.write(f"Parsed items count: {len(res)}\n")
            for p_item in res:
                f_log.write(f"  - {p_item['article']} | preu: {p_item['preuUnit']} | tot: {p_item['totLinea']}\n")
    except Exception:
        pass
    return res
 

def parse_novavenda_ticket(text_content):
    import re
    df_mapping = load_product_mappings()
    lines = text_content.split('\n')
    
    try:
        st.session_state["ticket_discount"] = 0.0
    except Exception:
        pass
        
    raw_products = []
    curr_item = None
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        line_upper = line_clean.upper()
        
        # Stop processing at TOTAL or VAT section
        if 'TOTAL ' in line_upper or line_upper == 'TOTAL' or 'BASE TYPE' in line_upper or 'QUOTA' in line_upper:
            if curr_item:
                raw_products.append(curr_item)
                curr_item = None
            break
            
        # Ignore NIF, header lines
        if any(kw in line_upper for kw in ['NOVAVENDA', 'COMERBAL', 'NIF', 'C/.', 'FACTURA']):
            continue
            
        # Check if line is barcode + quantity (e.g. "5449000275165 1 x 0,92 €")
        match_barcode = re.search(r'^(\d{7,14})\s+(\d+)\s*[xX]\s*(\d+[\.,]\d{2})', line_clean)
        if match_barcode:
            if curr_item:
                curr_item['quantitat'] = int(match_barcode.group(2))
                curr_item['preuUnit'] = float(match_barcode.group(3).replace(',', '.'))
            continue
            
        # Check if line is an offer (starts with OFERTA)
        if line_upper.startswith('OFERTA') or 'PREU NORMAL' in line_upper:
            continue
            
        # Check if line ends with a price
        match_price = re.search(r'^(.*?)\s+(\d+[\.,]\d{2})(?:\s*[€E])?$', line_clean)
        if match_price:
            nom_brut = match_price.group(1).strip()
            # If name is just numbers or very short, probably garbage
            if len(nom_brut) < 3 or re.match(r'^[\d\s,.]+$', nom_brut):
                continue
                
            tot_val = float(match_price.group(2).replace(',', '.'))
            
            if curr_item:
                # Resolve unit price if quantity wasn't found
                if curr_item['preuUnit'] == curr_item['totLinea'] and curr_item['quantitat'] > 1:
                    curr_item['preuUnit'] = round(curr_item['totLinea'] / curr_item['quantitat'], 2)
                raw_products.append(curr_item)
                
            curr_item = {
                'familia': 'Pendent',
                'article': 'pendent',
                'pes': 0,
                'quantitat': 1,
                'preuUnit': tot_val,
                'prom': 0.0,
                'totLinea': tot_val,
                'rebost': None,
                'nom_brut': nom_brut,
                'nom_super': nom_brut
            }
            
    if curr_item:
        if curr_item['preuUnit'] == curr_item['totLinea'] and curr_item['quantitat'] > 1:
            curr_item['preuUnit'] = round(curr_item['totLinea'] / curr_item['quantitat'], 2)
        raw_products.append(curr_item)
        
    # Match against DB
    for item in raw_products:
        db_match = find_product_in_db(item['nom_brut'], "Novavenda", df_mapping)
        if db_match:
            item['familia'] = db_match['familia']
            item['article'] = db_match['nomEstandard']
            item['nom_super'] = db_match.get('nom_super', item['nom_brut'])
            
    # Remove ghost items with 0 total price
    raw_products = [item for item in raw_products if item['totLinea'] > 0.0]
            
    # Group duplicates
    res = group_duplicate_ticket_items(raw_products)
    return res

def parse_text_ticket(text_content):
    import re
    from datetime import datetime
    
    # 1. Extract Date if possible
    found_date = None
    text_content_date = text_content.replace('2926', '2026').replace('41/07', '11/07')
    for match in re.finditer(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b', text_content_date):
        try:
            d_val, m_val, y_val = map(int, match.groups())
            if 1980 <= y_val <= 2090 and 1 <= m_val <= 12 and 1 <= d_val <= 31:
                found_date = datetime(y_val, m_val, d_val).date()
                break
        except ValueError:
            continue
    
    if not found_date:
        for match in re.finditer(r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b', text_content):
            try:
                y_val = int(match.group(1))
                m_val = int(match.group(2))
                d_val = int(match.group(3))
                found_date = datetime(y_val, m_val, d_val).date()
                break
            except ValueError:
                continue
                
    if found_date:
        st.session_state["ticket_date"] = found_date
        st.session_state["ticket_date_widget"] = found_date
        
    # 2. Extract Supermercat
    if not st.session_state.get("ticket_super_val"):
        if re.search(r'\bcomerbal\b', text_content.lower()):
            st.session_state["ticket_super_val"] = "Novavenda"
            st.session_state["ticket_super_widget"] = "Novavenda"
        else:
            for sp in get_config_supers():
                # Use regex for whole word match to prevent "Normal" matching "Preu normal" or "Ous" matching "baixos"
                if re.search(r'\b' + re.escape(sp.lower()) + r'\b', text_content.lower()):
                    st.session_state["ticket_super_val"] = sp
                    st.session_state["ticket_super_widget"] = sp
                    break
            
    ticket_super = st.session_state.get("ticket_super_val", "Dia").lower()
    
    if "novavenda" in ticket_super:
        return parse_novavenda_ticket(text_content)
    
    # Fallback for all other supermarkets (Dia, Mercadona, BonArea, Clarel)
    return parse_default_ticket(text_content)

def simulate_ocr_image(super_name):
    mock_products = {
        "AreaGuissona": [
            ("carn", "Costella porc", 0, 1, 4.50, 0.0, 4.50, None),
            ("carn", "Aletes pollastre", 0, 1, 3.20, 0.0, 3.20, None),
            ("verdura", "Tomàquet Cherry", 0, 1, 1.80, 0.0, 1.80, None),
            ("extres", "varis", 0, 6, 0.23, 0.0, 1.38, None),
        ],
        "Mercadona": [
            ("lactics", "Llet 1,5L", 0, 6, 0.95, 0.0, 5.70, None),
            ("fruita", "Plàtan", 0, 1, 2.15, 0.0, 2.15, None),
            ("neteja", "Detergent", 0, 1, 4.95, 0.0, 4.95, None),
            ("esmorzar", "Galetes", 0, 2, 1.20, 0.0, 2.40, None),
        ],
        "Dia": [
            ("llaunes", "Tonyina", 0, 3, 0.70, 0.0, 2.10, None),
            ("bàsics", "Arròs", 0, 1, 1.15, 0.0, 1.15, None),
            ("begudes", "CocaCola Zero 1.5L", 0, 2, 1.70, 0.0, 3.40, None),
        ],
        "LIDL": [
            ("lactics", "Iogurt grec", 0, 1, 1.95, 0.0, 1.95, None),
            ("pa", "Pa de pagès", 0, 1, 1.45, 0.0, 1.45, None),
            ("xocolata", "Xocolata Negra", 0, 2, 1.30, 0.0, 2.60, None),
        ],
    }
    matched_key = None
    for k in mock_products:
        if k.lower() in super_name.lower():
            matched_key = k
            break
    products_to_use = mock_products[matched_key] if matched_key else [
        ("bàsics", "Ous super", 0, 1, 2.25, 0.0, 2.25, None),
        ("fruita", "Taronja", 0, 1, 3.10, 0.0, 3.10, None),
        ("extres", "varis", 0, 1, 1.50, 0.0, 1.50, None),
    ]
    items = []
    for fam, art, pes, qty, preu, prom, tot, reb in products_to_use:
        items.append({
            'familia': fam,
            'article': art,
            'pes': pes,
            'quantitat': qty,
            'preuUnit': preu,
            'prom': prom,
            'totLinea': tot,
            'rebost': reb
        })
    return items

def cb_edit_ticket_item(idx):
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    item = st.session_state["ticket_items"][idx]
    st.session_state["manual_fam_selectbox"] = item['familia'] if item['familia'] != 'Pendent' else ""
    st.session_state["manual_art_selectbox"] = item['article'] if item['article'] != 'pendent' else ""
    st.session_state["manual_pes_num"] = str(item['pes'])
    st.session_state["manual_qty_num"] = float(item['quantitat'])
    st.session_state["manual_preu_num"] = float(item['preuUnit'])
    st.session_state["manual_prom_num"] = float(item['prom'])
    st.session_state["manual_reb_chk"] = (item['rebost'] == 'rebost')
    st.session_state["editing_ticket_item_idx"] = idx

def cb_del_ticket_item(idx):
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    st.session_state["ticket_items"].pop(idx)
    st.session_state["editing_ticket_item_idx"] = None

def learn_new_mapping(nom_brut, familia, article, supermercat):
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        if not supabase: return
        # Trobar id del producte estandard
        res = supabase.table('tb_productes').select('idProducte').eq('nom_estandard', article).execute()
        if res.data:
            id_prod = res.data[0]['idProducte']
        else:
            # Crear el producte estandard si no existeix
            new_prod = {'nom_estandard': article, 'familia': familia}
            ins = supabase.table('tb_productes').insert(new_prod).execute()
            if ins.data:
                id_prod = ins.data[0]['idProducte']
            else:
                return
                
        # Inserir a tb_noms_producte vinculat al supermercat
        clean_name = normalitzar_text(nom_brut)
        exist = supabase.table('tb_noms_producte').select('idNom').eq('nom_super', nom_brut).eq('supermercat', supermercat).execute()
        if not exist.data:
            new_nom = {'supermercat': supermercat, 'nom_super': nom_brut, 'idProducte': id_prod}
            supabase.table('tb_noms_producte').insert(new_nom).execute()
            print(f"Aprés nou producte: {nom_brut} -> {article}")
    except Exception as e:
        print(f"Error aprenent producte nou: {e}")

def cb_add_ticket_line():
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    fam = st.session_state.get("manual_fam_selectbox", "")
    art = st.session_state.get("manual_art_selectbox", "")
    pes_raw = st.session_state.get("manual_pes_num", "0")
    qty = st.session_state.get("manual_qty_num", 0.0)
    preu = st.session_state.get("manual_preu_num", 0.0)
    prom = st.session_state.get("manual_prom_num", 0.0)
    reb = st.session_state.get("manual_reb_chk", False)
    
    if not fam or not art:
        st.session_state["manual_input_error"] = "Si us plau, selecciona una Família i un Article!"
        return
        
    if "manual_input_error" in st.session_state:
        del st.session_state["manual_input_error"]
        
    pes = str(pes_raw).strip()

    tot = (qty * preu) - prom
    new_item = {
        'familia': fam,
        'article': art,
        'pes': pes,
        'quantitat': int(qty),
        'preuUnit': preu,
        'prom': prom,
        'totLinea': tot,
        'rebost': 'rebost' if reb else None,
        'nom_brut': '',
        'nom_super': ''
    }
    
    editing_idx = st.session_state.get("editing_ticket_item_idx", None)
    if editing_idx is not None and 0 <= editing_idx < len(st.session_state["ticket_items"]):
        old_item = st.session_state["ticket_items"][editing_idx]
        new_item['nom_brut'] = old_item.get('nom_brut', '')
        new_item['nom_super'] = old_item.get('nom_super', '')
        
        # Si era un article no reconegut i ara l'usuari l'ha categoritzat, l'aprenem
        if old_item.get('article') == 'pendent' and art != 'pendent' and art != '':
            supermercat = st.session_state.get("ticket_super_val", "Desconegut")
            nom_brut = st.session_state.get("manual_nom_brut_input", new_item['nom_brut'])
            if nom_brut:
                if nom_brut != old_item.get('nom_brut', ''):
                    try:
                        supabase = get_supabase_client(st.session_state.get("role", "guest"))
                        if supabase:
                            supabase.table('tb_noms_producte').delete().eq('nom_super', old_item.get('nom_brut')).eq('supermercat', supermercat).execute()
                    except Exception:
                        pass
                learn_new_mapping(nom_brut, fam, art, supermercat)
                
        st.session_state["ticket_items"][editing_idx] = new_item
        st.session_state["editing_ticket_item_idx"] = None
    else:
        st.session_state["ticket_items"].append(new_item)
    
    # Reset widget states
    st.session_state["manual_pes_num"] = "0"
    st.session_state["manual_qty_num"] = 1.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["manual_preu_num"] = 0.0
    st.session_state["manual_prom_num"] = 0.0
    st.session_state["manual_reb_chk"] = False
    st.session_state["manual_fam_selectbox"] = ""
    st.session_state["manual_art_selectbox"] = ""

def cb_recalculate_manual_pct():
    pct = st.session_state.get("manual_pct_num", 0.0)
    preu_final = st.session_state.get("manual_preu_num", 0.0)
    existing_prom = st.session_state.get("manual_prom_num", 0.0)
    if pct > 0.0 and pct < 100.0 and preu_final > 0.0:
        base = round(preu_final / (1 - pct / 100.0), 2)
        prom_from_pct = round(base * (pct / 100.0), 2)
        st.session_state["manual_preu_num"] = base
        st.session_state["manual_prom_num"] = round(existing_prom + prom_from_pct, 2)
        st.session_state["manual_pct_num"] = 0.0

def cb_set_date_today():
    st.session_state["ticket_date"] = datetime.today().date()
    st.session_state["ticket_date_widget"] = datetime.today().date()

def cb_clear_ticket():
    st.session_state["ticket_items"] = []
    st.session_state["ticket_discount"] = 0.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["editing_ticket_item_idx"] = None
    st.session_state["ticket_date"] = datetime.today().date()
    st.session_state["ticket_date_widget"] = datetime.today().date()
    if "last_ocr_text" in st.session_state:
        del st.session_state["last_ocr_text"]
    st.session_state["ticket_super_val"] = ""
    if "ticket_super_widget" in st.session_state:
        st.session_state["ticket_super_widget"] = ""
    st.session_state["ticket_pay_method_sel"] = ""
    st.session_state["processed_file_id"] = None
    if "scanned_file" in st.session_state:
        del st.session_state["scanned_file"]
    # Reset manual inputs
    st.session_state["manual_pes_num"] = "0"
    st.session_state["manual_qty_num"] = 1.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["manual_preu_num"] = 0.0
    st.session_state["manual_prom_num"] = 0.0
    st.session_state["manual_reb_chk"] = False
    st.session_state["manual_fam_selectbox"] = ""
    st.session_state["manual_art_selectbox"] = ""
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    current_idx = int(st.session_state.get("uploader_key", "ticket_file_uploader_0").split("_")[-1])
    st.session_state["uploader_key"] = f"ticket_file_uploader_{current_idx + 1}"

def cb_finalize_ticket():
    global df_desp, df_super
    df_desp = st.session_state["df_desp"]
    df_super = st.session_state["df_super"]
    
    items = st.session_state.get("ticket_items", [])
    if not items:
        st.session_state["finalize_error"] = "No es pot desar un tiquet buit!"
        return
        
    ticket_super = st.session_state.get("ticket_super_val", "")
    if not ticket_super:
        st.session_state["finalize_error"] = "Si us plau, selecciona un Supermercat abans de desar el tiquet!"
        return
        
    ticket_date = st.session_state.get("ticket_date", None)
    if not ticket_date:
        st.session_state["finalize_error"] = "Si us plau, especifica la Data del tiquet!"
        return
        
    # Salvem els articles desconeguts si n'hi ha (ara que tenim supermercat confirmat)
    save_unknown_products(items, ticket_super)
        
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
        
    pending_ticket_id = st.session_state.get('pending_ticket_id')
    if pending_ticket_id:
        orig_amt = float(st.session_state.get('pending_import_carrec', 0.0))
        sum_amt = sum(item['totLinea'] for item in items)
        if abs(sum_amt - orig_amt) > 0.001:
            st.session_state["finalize_error"] = f"Desquadrament! El banc diu {orig_amt:.2f} € i els productes sumen {sum_amt:.2f} €. Pots forçar la correcció del banc amb el botó que ha aparegut a dalt."
            st.session_state["pending_ticket_mismatch"] = True
            st.session_state["pending_ticket_sum"] = sum_amt
            return
        
    discount = st.session_state.get("ticket_discount", 0.0)
    send_expense = st.session_state.get("ticket_send_expense", True)
        
    if isinstance(ticket_date, datetime):
        ticket_date = ticket_date.date()
        
    mes_val = month_translations[CATALAN_MONTHS[ticket_date.month - 1]]
    any_val = ticket_date.year
        
    bank_val = st.session_state.get("ticket_bank_sel", "")
    pay_method_val = st.session_state.get("ticket_pay_method_sel", "")
    
    if bank_val is None:
        bank_val = ""
    if pay_method_val is None:
        pay_method_val = ""
        
    bank_val_str = str(bank_val).strip()
    pay_method_val_str = str(pay_method_val).strip()
    
    if send_expense:
        if not bank_val_str or bank_val_str in ["None", "nan", "NaN", ""]:
            st.session_state["finalize_error"] = "Si us plau, selecciona un Banc per a la despesa!"
            return
        if not pay_method_val_str or pay_method_val_str in ["None", "nan", "NaN", ""]:
            st.session_state["finalize_error"] = "Si us plau, selecciona una Forma de Pagament per a la despesa!"
            return
    
    # Separate totals for menjar, neteja, and rebost
    raw_rebost = sum(item['totLinea'] for item in items if item['rebost'] == 'rebost')
    raw_neteja = sum(item['totLinea'] for item in items if item['familia'] == 'neteja' and item['rebost'] != 'rebost')
    raw_menjar = sum(item['totLinea'] for item in items if item['familia'] != 'neteja' and item['rebost'] != 'rebost')
    
    # Distribute discount: apply to menjar first, then rebost, then neteja
    rem_discount = discount
    
    import_menjar = max(0.0, raw_menjar - rem_discount)
    rem_discount = max(0.0, rem_discount - raw_menjar)
    
    import_rebost = max(0.0, raw_rebost - rem_discount)
    rem_discount = max(0.0, rem_discount - raw_rebost)
    
    import_neteja = max(0.0, raw_neteja - rem_discount)
    rem_discount = max(0.0, rem_discount - raw_neteja)
    
    id_despesa_menjar = 0
    id_despesa_neteja = 0
    id_despesa_rebost = 0
    if send_expense:
        new_entries = []
        
        # 1. Food Expense (menjar)
        if import_menjar > 0:
            new_entries.append({
                'Banc': bank_val,
                'FormaPago': pay_method_val,
                'Data': ticket_date.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'import ingrés': 0.0,
                'Import càrrec': import_menjar,
                'grup': 'Càrrec',
                'Idcategoria': 'menjar',
                'Idconcepte': ticket_super,
                'Comentari': None
            })
            
        # 2. Cleaning Expense (neteja)
        if import_neteja > 0:
            new_entries.append({
                'Banc': bank_val,
                'FormaPago': pay_method_val,
                'Data': ticket_date.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'import ingrés': 0.0,
                'Import càrrec': import_neteja,
                'grup': 'Càrrec',
                'Idcategoria': 'neteja',
                'Idconcepte': ticket_super,
                'Comentari': None
            })
            
        # 3. Pantry Expense (rebost)
        if import_rebost > 0:
            new_entries.append({
                'Banc': bank_val,
                'FormaPago': pay_method_val,
                'Data': ticket_date.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'import ingrés': 0.0,
                'Import càrrec': import_rebost,
                'grup': 'Càrrec',
                'Idcategoria': 'rebost',
                'Idconcepte': ticket_super,
                'Comentari': None
            })
            
        # Assign IDs to new_entries
        next_id = int(df_desp['ID_mov'].max() + 1) if not df_desp.empty else 1
        for i, entry in enumerate(new_entries):
            if i == 0 and pending_ticket_id:
                entry['ID_mov'] = pending_ticket_id
                if entry['Idcategoria'] == 'menjar':
                    id_despesa_menjar = pending_ticket_id
                elif entry['Idcategoria'] == 'neteja':
                    id_despesa_neteja = pending_ticket_id
                elif entry['Idcategoria'] == 'rebost':
                    id_despesa_rebost = pending_ticket_id
            else:
                entry['ID_mov'] = next_id
                if entry['Idcategoria'] == 'menjar':
                    id_despesa_menjar = next_id
                elif entry['Idcategoria'] == 'neteja':
                    id_despesa_neteja = next_id
                elif entry['Idcategoria'] == 'rebost':
                    id_despesa_rebost = next_id
                next_id += 1
            
        if new_entries:
            if pending_ticket_id:
                try:
                    supabase = get_supabase_client(st.session_state.get("role", "guest"))
                    supabase.table('despeses').delete().eq('ID_mov', pending_ticket_id).execute()
                    df_desp.drop(df_desp[df_desp['ID_mov'] == pending_ticket_id].index, inplace=True)
                    st.session_state['df_desp'] = df_desp
                except Exception as e:
                    print(f"Error deleting pending ticket {pending_ticket_id}: {e}")
                    
            append_to_db(pd.DataFrame(new_entries), 'despeses', 'df_desp')
    
    new_rows = []
    base_id = int(df_super['IdCompra'].max() + 1) if not df_super.empty else 1
    for idx, item in enumerate(items):
        line_discount = discount if idx == 0 else 0.0
        # Determine linked expense ID based on category/rebost
        if item['rebost'] == 'rebost':
            linked_id_despesa = id_despesa_rebost
        elif item['familia'] == 'neteja':
            linked_id_despesa = id_despesa_neteja
        else:
            linked_id_despesa = id_despesa_menjar
            
        new_row = {
            'IdCompra': base_id + idx,
            'data': ticket_date.strftime('%d/%m/%Y'),
            'mes': mes_val,
            'any': any_val,
            'super': ticket_super,
            'familia': item['familia'],
            'article': item['article'],
            'pes': str(item['pes']),
            'quantitat': int(item['quantitat']),
            'preuUnit': item['preuUnit'],
            'prom': item['prom'],
            'totLinea': item['totLinea'],
            'IdDespesa': linked_id_despesa,
            'descompte': line_discount,
            'rebost': item['rebost']
        }
        new_rows.append(new_row)
    append_to_db(pd.DataFrame(new_rows), 'compresSuper', 'df_super')
    
    # Update stock for recognized products
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    if supabase:
        for item in items:
            article = item.get('article', '').strip()
            if not article or article.lower() in ['pendent', 'varis']:
                continue
            try:
                res = supabase.table('tb_productes').select('idProducte, stock_actual, select_stock').eq('nom_estandard', article).execute()
                if res.data:
                    # Check if the product has select_stock == True
                    if res.data[0].get('select_stock', False) == True:
                        prod_id = res.data[0]['idProducte']
                        current_stock = res.data[0].get('stock_actual', 0)
                        if current_stock is None:
                            current_stock = 0
                        
                        qty_to_add = float(item.get('qty', 1.0))
                        new_stock = current_stock + qty_to_add
                        
                        supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', prod_id).execute()
            except Exception as e:
                print(f"Error updating stock for {article}: {e}")
    
    st.session_state["finalize_success"] = "Tiquet de súper i despesa associada desats correctament!"
    # Clear all fields and files on successful finalize
    st.session_state["ticket_items"] = []
    st.session_state["ticket_discount"] = 0.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["editing_ticket_item_idx"] = None
    st.session_state["ticket_date"] = datetime.today().date()
    st.session_state["ticket_super_val"] = ""
    st.session_state["ticket_bank_sel"] = ""
    st.session_state["ticket_pay_method_sel"] = ""
    st.session_state["processed_file_id"] = None
    if "scanned_file" in st.session_state:
        del st.session_state["scanned_file"]
    # Reset manual inputs
    st.session_state["manual_pes_num"] = "0"
    st.session_state["manual_qty_num"] = 1.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["manual_preu_num"] = 0.0
    st.session_state["manual_prom_num"] = 0.0
    st.session_state["manual_reb_chk"] = False
    st.session_state["manual_fam_selectbox"] = ""
    st.session_state["manual_art_selectbox"] = ""
    
    # Clear pending ticket state if any
    for key in ['pending_ticket_id', 'pending_super', 'pending_data', 'pending_banc', 'pending_forma_pago', 'pending_import_carrec', 'pending_ticket_mismatch', 'pending_ticket_sum', 'last_ocr_text']:
        if key in st.session_state:
            del st.session_state[key]
            
    current_idx = int(st.session_state.get("uploader_key", "ticket_file_uploader_0").split("_")[-1])
    st.session_state["uploader_key"] = f"ticket_file_uploader_{current_idx + 1}"
    st.session_state["viewing_compres_super"] = True

def render_compres_super_interface():
    global df_super, df_desp
    
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
                doc.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const target = e.target;
                if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.getAttribute('role') === 'combobox') {
                    const inputs = Array.from(doc.querySelectorAll('input:not([type="hidden"]):not([disabled]), select:not([disabled]), [role="combobox"]:not([disabled])'));
                    const index = inputs.indexOf(target);
                    if (index > -1 && index < inputs.length - 1) {
                        e.preventDefault();
                        e.stopPropagation();
                        inputs[index + 1].focus();
                    }
                }
            }
        }, true);
        
        doc.addEventListener('focusin', function(e) {
            const target = e.target;
            if (target.tagName === 'INPUT') {
                const val = target.value.trim();
                if (val === '0' || val === '0,00' || val === '0.00' || val === '0.0' || val === '0,0') {
                    setTimeout(() => {
                        target.select();
                    }, 50);
                }
            }
        }, true);
        </script>
        """,
        height=0,
        width=0
    )
    
    st.markdown("<h2 style='text-align: center; color: #f39c12; margin-top: 5px; margin-bottom: 20px;'>Intro ticket Super</h2>", unsafe_allow_html=True)
    
    if "ticket_msg_success" in st.session_state:
        st.success(st.session_state["ticket_msg_success"])
        del st.session_state["ticket_msg_success"]
    if "ticket_msg_error" in st.session_state:
        st.error(st.session_state["ticket_msg_error"])
        del st.session_state["ticket_msg_error"]
    if "finalize_error" in st.session_state:
        st.error(st.session_state["finalize_error"])

    if "ticket_items" not in st.session_state:
        st.session_state["ticket_items"] = []
        
    if st.session_state.get("pending_ticket_mismatch"):
        orig_amt = float(st.session_state.get('pending_import_carrec', 0.0))
        sum_amt = float(st.session_state.get('pending_ticket_sum', 0.0))
        st.warning(f"L'import inicial registrat al banc era de **{orig_amt:.2f} €**, però la suma dels productes és de **{sum_amt:.2f} €**.")
        if st.button(f"Forçar correcció del banc a {sum_amt:.2f} €", type="primary"):
            try:
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                supabase.table("despeses").update({"Import càrrec": sum_amt}).eq("ID_mov", st.session_state.get('pending_ticket_id')).execute()
                if "df_desp" in st.session_state:
                    df_local = st.session_state["df_desp"]
                    idx_orig = df_local.index[df_local['ID_mov'] == st.session_state.get('pending_ticket_id')].tolist()[0]
                    df_local.at[idx_orig, 'Import càrrec'] = round(sum_amt, 2)
                st.session_state['pending_import_carrec'] = sum_amt
                del st.session_state["pending_ticket_mismatch"]
                st.success("Banc actualitzat correctament! Ara pots polsar 'Guardar Ticket de Súper' de nou.")
                st.rerun()
            except Exception as e:
                st.error(f"Error actualitzant banc: {e}")
    if "ticket_discount" not in st.session_state:
        st.session_state["ticket_discount"] = 0.0
    
    # Initialize pending ticket values
    if st.session_state.get('pending_ticket_id'):
        if not st.session_state.get("ticket_super_val") and st.session_state.get('pending_super'):
            st.session_state["ticket_super_val"] = st.session_state['pending_super']
        if not st.session_state.get("ticket_date") and st.session_state.get('pending_data'):
            try:
                st.session_state["ticket_date"] = datetime.strptime(st.session_state['pending_data'], '%d/%m/%Y').date()
            except:
                st.session_state["ticket_date"] = datetime.today().date()
        if not st.session_state.get("ticket_bank_sel") and st.session_state.get('pending_banc'):
            st.session_state["ticket_bank_sel"] = st.session_state['pending_banc']
        if not st.session_state.get("ticket_pay_method_sel") and st.session_state.get('pending_forma_pago'):
            st.session_state["ticket_pay_method_sel"] = st.session_state['pending_forma_pago']
            
    if "ticket_date" not in st.session_state or st.session_state["ticket_date"] is None:
        st.session_state["ticket_date"] = None
    if "ticket_super_val" not in st.session_state:
        st.session_state["ticket_super_val"] = ""
    if "ticket_send_expense" not in st.session_state:
        st.session_state["ticket_send_expense"] = True
    if "ticket_bank_sel" not in st.session_state:
        st.session_state["ticket_bank_sel"] = ""
    if "ticket_pay_method_sel" not in st.session_state:
        st.session_state["ticket_pay_method_sel"] = ""
    if "added_supers" not in st.session_state:
        st.session_state["added_supers"] = []
        
    pending_ticket_id = st.session_state.get('pending_ticket_id')
    if pending_ticket_id:
        st.info(f"🛒 **Desglossant ticket pendent:** de {st.session_state.get('pending_super', '')} el {st.session_state.get('pending_data', '')}")
        
    # Row 1: Send to expense checkbox, Bank, Payment Method, File Uploader
    col_hdr1, col_hdr2, col_hdr3, col_hdr4 = st.columns([2.5, 2.5, 2.5, 4.5], vertical_alignment="bottom")
    with col_hdr1:
        send_expense = st.checkbox("Enviar a despeses", key="ticket_send_expense")
    
    bank_val = ""
    pay_method_val = ""
    if send_expense:
        with col_hdr2:
            bank_val = st.selectbox("Banc:", [""] + get_config_banks(), key="ticket_bank_sel")
        with col_hdr3:
            pay_methods = [""] + get_config_payment_methods()
            if bank_val == "Efectiu":
                pay_methods = ["Efectiu"]
                st.session_state["ticket_pay_method_sel"] = "Efectiu"
            else:
                pay_methods = [m for m in pay_methods if m != "Efectiu"]
                if st.session_state.get("ticket_pay_method_sel") == "Efectiu":
                    st.session_state["ticket_pay_method_sel"] = ""
            pay_method_val = st.selectbox("Forma de Pagament:", pay_methods, key="ticket_pay_method_sel")
    else:
        with col_hdr2:
            st.write("")
        with col_hdr3:
            st.write("")
            
    if send_expense and len(st.session_state.get("ticket_items", [])) > 0:
        b_val_str = str(bank_val).strip()
        p_val_str = str(pay_method_val).strip()
        if not b_val_str or b_val_str in ["None", "nan", "NaN", ""]:
            st.error("Si us plau, selecciona un Banc per a la despesa!")
        if not p_val_str or p_val_str in ["None", "nan", "NaN", ""]:
            st.error("Si us plau, selecciona una Forma de Pagament per a la despesa!")
            
    with col_hdr4:
        uploader_key = st.session_state.get("uploader_key", "ticket_file_uploader_0")
        uploaded_file = st.file_uploader("📷 Llegir ticket", type=["png", "jpg", "jpeg", "txt"], label_visibility="collapsed", key=uploader_key)
        with st.popover("📷 Escanejar amb càmera"):
            camera_file = st.camera_input("Fes una foto al tiquet")
        
        if st.button("⚡ Llegir últim tiquet escanejat", use_container_width=True):
            import os, glob, io
            tickets_dir = "E:/Dashboard/tickets"
            list_of_files = glob.glob(os.path.join(tickets_dir, '*.jpg')) + glob.glob(os.path.join(tickets_dir, '*.png'))
            if list_of_files:
                latest_file = max(list_of_files, key=os.path.getctime)
                with open(latest_file, "rb") as f:
                    file_bytes = f.read()
                file_obj = io.BytesIO(file_bytes)
                file_obj.name = os.path.basename(latest_file)
                file_obj.size = len(file_bytes)
                st.session_state["scanned_file"] = file_obj
                st.session_state["processed_file_id"] = None
                st.session_state["ticket_super_val"] = ""
                if "ticket_super_widget" in st.session_state:
                    del st.session_state["ticket_super_widget"]
                if "ticket_items" in st.session_state:
                    st.session_state["ticket_items"] = []
                if "ticket_msg_success" in st.session_state:
                    del st.session_state["ticket_msg_success"]
                if "ticket_msg_error" in st.session_state:
                    del st.session_state["ticket_msg_error"]
                st.rerun()
            else:
                st.warning("No s'ha trobat cap tiquet a la carpeta.")
        
        if st.session_state.get("scanned_file") is not None:
            uploaded_file = st.session_state["scanned_file"]
        elif camera_file is not None:
            uploaded_file = camera_file
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("processed_file_id") != file_id:
                st.session_state["processed_file_id"] = file_id
                if uploaded_file.name.endswith(".txt"):
                    try:
                        text_content = uploaded_file.read().decode("utf-8")
                        st.session_state["last_ocr_text"] = text_content
                        parsed = parse_text_ticket(text_content)
                        
                        if not st.session_state.get("ticket_super_val"):
                            st.session_state["ticket_msg_error"] = "⚠️ No s'ha detectat automàticament el supermercat. Si us plau, selecciona'l al desplegable inferior perquè es puguin processar els articles."
                            st.session_state["ticket_items"] = []
                            st.rerun()
                            
                        st.session_state["ticket_items"] = parsed
                        save_unknown_products(parsed, st.session_state.get("ticket_super_val", ""))
                        st.session_state["ticket_msg_success"] = f"Tiquet de text llegit correctament! S'han trobat {len(parsed)} línies."
                        st.rerun()
                    except Exception as e:
                        st.session_state["ticket_msg_error"] = f"Error al llegir el tiquet de text: {str(e)}"
                        st.rerun()
                else:
                    try:
                        # Run REAL OCR using pytesseract
                        with st.spinner("Processant tiquet amb OCR..."):
                            from PIL import ImageOps
                            img = Image.open(uploaded_file)
                            img = ImageOps.exif_transpose(img)
                            
                            # Detect orientation by testing crop rotations
                            if img.mode != 'L':
                                img_l = img.convert('L')
                            else:
                                img_l = img.copy()
                            
                            # Scale down for fast orientation check
                            detect_scale = 1.5
                            dw, dh = img_l.size
                            img_detect = img_l.resize((int(dw * detect_scale), int(dh * detect_scale)), Image.Resampling.LANCZOS)
                            
                            best_angle = 0
                            max_prices = -1
                            
                            for angle in [0, 90, 180, 270]:
                                if angle == 0:
                                    rotated_test = img_detect
                                else:
                                    rotated_test = img_detect.rotate(angle, expand=True)
                                    
                                r_w, r_h = rotated_test.size
                                crop_w, crop_h = min(800, r_w), min(800, r_h)
                                left = (r_w - crop_w) // 2
                                top = (r_h - crop_h) // 2
                                crop_img = rotated_test.crop((left, top, left + crop_w, top + crop_h))
                                
                                txt_test = pytesseract.image_to_string(crop_img, config=r'--oem 3 --psm 6 -l spa+cat')
                                prices_found = len(re.findall(r'\b\d+[\.,]\d{2}\b', txt_test))
                                
                                if prices_found > max_prices:
                                    max_prices = prices_found
                                    best_angle = angle
                                    
                                # If we find many prices, it's likely oriented correctly
                                if prices_found > 10:
                                    best_angle = angle
                                    break
                                    
                            if best_angle != 0:
                                img = img.rotate(best_angle, expand=True)
                            
                            # Preprocess image optimized for receipts (similar to offline test)
                            # 1. Convert to grayscale
                            if img.mode != 'L':
                                img = img.convert('L')
                             
                            # 2. Resize by 3.0 to make text larger and easier for Tesseract
                            scale = 3.0
                            new_width = int(img.width * scale)
                            new_height = int(img.height * scale)
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                             
                            # 3. Enhance Contrast moderately (1.2)
                            from PIL import ImageEnhance
                            enhancer = ImageEnhance.Contrast(img)
                            img = enhancer.enhance(1.2)
                             
                            # 4. Enhance Sharpness moderately (1.2)
                            enhancer = ImageEnhance.Sharpness(img)
                            img = enhancer.enhance(1.2)
                            
                            # Run Tesseract OCR with multiple configurations to find the best result
                            # We prefer PSM 6 (uniform block of text) and bilingual Spanish+Catalan first
                            configs_proves = [
                                r'--oem 3 --psm 6 -l spa+cat',   # Bilingual structured
                                r'--oem 3 --psm 6',              # Uniform block of text
                            ]
                            
                            best_text = ""
                            best_lines_count = -1
                            
                            for config in configs_proves:
                                try:
                                    text = pytesseract.image_to_string(img, config=config)
                                    # Ensure the line contains both letters (product name) and price numbers to avoid column-split layouts
                                    lines_with_price = sum(1 for line in text.split('\n') if re.search(r'[a-zA-Z]{3,}.*\b\d+[\.,\s]+\d{2}\b', line))
                                    if lines_with_price > best_lines_count:
                                        best_lines_count = lines_with_price
                                        best_text = text
                                except Exception:
                                    continue
                                    
                            if best_text:
                                text_content = best_text
                            else:
                                text_content = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
                            
                             # Parse date (DD-MM-YYYY or DD/MM/YYYY) with validation
                            found_date = None
                            for match in re.finditer(r'(\d{2})[-/](\d{2})[-/](\d{4})', text_content):
                                try:
                                    d_val, m_val, y_val = map(int, match.groups())
                                    if 1980 <= y_val <= 2090 and 1 <= m_val <= 12 and 1 <= d_val <= 31:
                                        found_date = datetime(y_val, m_val, d_val).date()
                                        break
                                except ValueError:
                                    continue
                            
                            if not found_date:
                                for match in re.finditer(r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b', text_content):
                                    try:
                                        y_val = int(match.group(1))
                                        m_val = int(match.group(2))
                                        d_val = int(match.group(3))
                                        found_date = datetime(y_val, m_val, d_val).date()
                                        break
                                    except ValueError:
                                        continue
                                        
                            if found_date:
                                st.session_state["ticket_date"] = found_date
                                
                            # Parse supermercat
                            if not st.session_state.get("ticket_super_val"):
                                if re.search(r'\bcomerbal\b', text_content.lower()):
                                    st.session_state["ticket_super_val"] = "Novavenda"
                                    st.session_state["ticket_super_widget"] = "Novavenda"
                                else:
                                    for sp in get_config_supers():
                                        if re.search(r'\b' + re.escape(sp.lower()) + r'\b', text_content.lower()):
                                            st.session_state["ticket_super_val"] = sp
                                            st.session_state["ticket_super_widget"] = sp
                                            break
                                    
                            st.session_state["last_ocr_text"] = text_content
                            parsed = parse_text_ticket(text_content)
                            
                            if not st.session_state.get("ticket_super_val"):
                                st.session_state["ticket_msg_error"] = "⚠️ No s'ha detectat automàticament el supermercat. Si us plau, selecciona'l al desplegable inferior perquè es puguin processar els articles."
                                st.session_state["ticket_items"] = []
                                st.rerun()
                                
                            st.session_state["ticket_items"] = parsed
                            save_unknown_products(parsed, st.session_state.get("ticket_super_val", ""))
                            st.session_state["ticket_msg_success"] = f"Tiquet processat amb èxit! S'han detectat {len(parsed)} articles."
                            st.rerun()
                    except Exception as e:
                        st.session_state["ticket_msg_error"] = f"Error al processar l'imatge amb OCR: {str(e)}. Si us plau, introdueix els productes manualment."
                        st.rerun()
        
    # Row 2: Data, Super, Import, Nº Despesa
    col_row2_1, col_row2_2, col_row2_3, col_row2_4 = st.columns([3.5, 3.5, 2.5, 2.5], vertical_alignment="center")
    with col_row2_1:
        col_d1, col_d2 = st.columns([3, 1], vertical_alignment="bottom")
        with col_d1:
            ticket_date = st.date_input("Data:", value=st.session_state.get("ticket_date", None), format="DD/MM/YYYY", key="ticket_date_widget")
            st.session_state["ticket_date"] = ticket_date
        with col_d2:
            st.button("Avui", key="btn_avui", on_click=cb_set_date_today)
                
    with col_row2_2:
        col_s1, col_s2 = st.columns([3, 1.2], vertical_alignment="bottom")
        with col_s1:
            super_options = [""] + get_config_supers()
            for sp in st.session_state["added_supers"]:
                if sp not in super_options:
                    super_options.append(sp)
            default_super = st.session_state.get("ticket_super_val", "")
            if default_super not in super_options:
                super_options.append(default_super)
            def_idx = super_options.index(default_super)
            
            def cb_super_changed():
                new_super = st.session_state["ticket_super_widget"]
                st.session_state["ticket_super_val"] = new_super
                if "last_ocr_text" in st.session_state and st.session_state["last_ocr_text"]:
                    parsed = parse_text_ticket(st.session_state["last_ocr_text"])
                    st.session_state["ticket_items"] = parsed
                    save_unknown_products(parsed, new_super)
                    if "ticket_msg_error" in st.session_state:
                        del st.session_state["ticket_msg_error"]
                    st.session_state["ticket_msg_success"] = f"Tiquet reprocessat correctament com a {new_super}. S'han detectat {len(parsed)} articles."
            
            ticket_super = st.selectbox("Super:", super_options, index=def_idx, key="ticket_super_widget", on_change=cb_super_changed)
            st.session_state["ticket_super_val"] = ticket_super
        with col_s2:
            if st.button("Nou", key="btn_nou_super"):
                st.session_state["show_new_super_popover"] = True
                
        if st.session_state.get("show_new_super_popover", False):
            new_super_name = st.text_input("Nom del nou Súper:", key="new_super_name_input", autocomplete="new-password")
            col_ns1, col_ns2 = st.columns(2)
            with col_ns1:
                if st.button("Afegir", key="btn_add_new_super"):
                    if new_super_name.strip():
                        if new_super_name.strip() not in st.session_state["added_supers"]:
                            st.session_state["added_supers"].append(new_super_name.strip())
                        add_super_to_config(new_super_name.strip())
                        st.session_state["show_new_super_popover"] = False
                        st.rerun()
            with col_ns2:
                if st.button("Tancar", key="btn_close_new_super"):
                    st.session_state["show_new_super_popover"] = False
                    st.rerun()
 
    items = st.session_state["ticket_items"]
    discount = st.session_state["ticket_discount"]
    total_import = sum(item['totLinea'] for item in items) - discount
 
    with col_row2_3:
        st.markdown("**IMPORT TOTAL TICKET**")
        st.markdown(f"<div style='background-color:#1e293b; color:#ffffff; border:1px solid #334155; padding:8px; border-radius:4px; font-size:1.2rem; font-weight:bold; text-align:center;'>{total_import:,.2f} €</div>", unsafe_allow_html=True)
        
    with col_row2_4:
        if pending_ticket_id:
            next_id = pending_ticket_id
        else:
            next_id = int(df_desp['ID_mov'].max() + 1) if not df_desp.empty else 1
        st.markdown("**Nº DESPESA**")
        st.markdown(f"<div style='background-color:#1e293b; color:#ffffff; border:1px solid #334155; padding:8px; border-radius:4px; font-size:1.2rem; font-weight:bold; text-align:center;'>{next_id}</div>", unsafe_allow_html=True)

    # Ensure manual input states are initialized
    if "manual_fam_selectbox" not in st.session_state:
        st.session_state["manual_fam_selectbox"] = ""
    if "manual_art_selectbox" not in st.session_state:
        st.session_state["manual_art_selectbox"] = ""
    if "manual_pes_num" not in st.session_state:
        st.session_state["manual_pes_num"] = "0"
    if "manual_qty_num" not in st.session_state:
        st.session_state["manual_qty_num"] = 1.0
    if "manual_pct_num" not in st.session_state:
        st.session_state["manual_pct_num"] = 0.0
    if "manual_preu_num" not in st.session_state:
        st.session_state["manual_preu_num"] = 0.0
    if "manual_prom_num" not in st.session_state:
        st.session_state["manual_prom_num"] = 0.0
    if "manual_reb_chk" not in st.session_state:
        st.session_state["manual_reb_chk"] = False
    # Dynamic recalculation for manual ticket lines if pct (%) is entered
    pct = st.session_state.get("manual_pct_num", 0.0)
    preu_final = st.session_state.get("manual_preu_num", 0.0)
    qty = st.session_state.get("manual_qty_num", 1.0)
    if qty <= 0.0:
        qty = 1.0
    if pct > 0.0 and pct < 100.0 and preu_final > 0.0:
        base = round(preu_final / (1 - pct / 100.0), 2)
        prom_from_pct = round(base * (pct / 100.0) * qty, 2)
        st.session_state["manual_preu_num"] = base
        st.session_state["manual_prom_num"] = prom_from_pct
        st.session_state["manual_pct_num"] = 0.0 # reset pct
        st.rerun()

    # Manual Line Input Section
    st.write("")
    st.markdown("##### ➕ Introduir línia manualment")
    
    editing_idx = st.session_state.get("editing_ticket_item_idx", None)
    if editing_idx is not None and 0 <= editing_idx < len(st.session_state.get("ticket_items", [])):
        ed_item = st.session_state["ticket_items"][editing_idx]
        if ed_item.get('article') == 'pendent':
            st.text_input("Text original (modifica si cal abans de desar per ensenyar al sistema):", value=ed_item.get('nom_brut', ''), key="manual_nom_brut_input")
            
    col_fam, col_art, col_pes, col_qty, col_pct, col_preu, col_prom, col_tot, col_reb, col_add = st.columns(
        [2, 2.2, 1, 1, 0.8, 1, 1, 1.2, 0.6, 1.2], vertical_alignment="bottom"
    )
    
    with col_fam:
        fam_options = [""] + get_config_families()
        fam_sel = st.selectbox("FAMILIA", fam_options, key="manual_fam_selectbox")
        
    with col_art:
        @st.dialog("➕ Afegir nou article")
        def show_add_article_dialog(family):
            st.markdown(f"Introduïu el nom del nou article per a la família **{family}**:")
            new_art_name = st.text_input("Nom de l'article:", key="new_article_name_input_dialog")
            if st.button("Guardar article", key="btn_save_dialog_article", use_container_width=True):
                if new_art_name.strip():
                    new_art = new_art_name.strip()
                    global cat_config
                    if "articles_compres" not in cat_config:
                        cat_config["articles_compres"] = {}
                    if family not in cat_config["articles_compres"]:
                        cat_config["articles_compres"][family] = []
                    if new_art not in cat_config["articles_compres"][family]:
                        try:
                            supabase = get_supabase_client(st.session_state.get("role", "guest"))
                            if supabase:
                                new_prod_db = {'nom_estandard': new_art, 'familia': family}
                                supabase.table('tb_productes').insert(new_prod_db).execute()
                                get_tb_productes_cached.clear()
                                # Actualitzem manualment el json
                                cat_config["articles_compres"][family].append(new_art)
                                cat_config["articles_compres"][family].sort()
                                save_categories_conceptes(cat_config)
                        except Exception as e:
                            print(f"Error saving to tb_productes: {e}")
                            
                        st.toast(f"Article '{new_art}' afegit correctament!")
                    else:
                        st.toast(f"L'article '{new_art}' ja estava afegit prèviament.")
                        
                    st.session_state["force_article_selection"] = new_art
                    st.rerun()
                else:
                    st.error("El nom de l'article no pot estar buit.")

        if fam_sel:
            art_options = [""] + get_config_articles(fam_sel)
        else:
            art_options = [""]
        if "force_article_selection" in st.session_state:
            force_art = st.session_state.pop("force_article_selection")
            if force_art in art_options:
                st.session_state["manual_art_selectbox"] = force_art
                
        curr_art = st.session_state["manual_art_selectbox"]
        if curr_art not in art_options:
            st.session_state["manual_art_selectbox"] = ""
            
        # Draw side-by-side columns: 85% selectbox, 15% small + button
        art_input_cols = st.columns([8, 2])
        with art_input_cols[0]:
            art_sel = st.selectbox("ARTICLE", art_options, key="manual_art_selectbox")
        with art_input_cols[1]:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if fam_sel:
                st.markdown(
                    """
                    <style>
                    .small-add-btn button {
                        padding: 0px !important;
                        font-size: 12px !important;
                        height: 28px !important;
                        width: 28px !important;
                        min-height: 28px !important;
                        line-height: 28px !important;
                        border-radius: 4px !important;
                    }
                    </style>
                    <div class="small-add-btn">
                    """,
                    unsafe_allow_html=True
                )
                if st.button("➕", key="btn_trigger_add_art", help="Afegir nou article"):
                    show_add_article_dialog(fam_sel)
                st.markdown("</div>", unsafe_allow_html=True)
        
    with col_pes:
        pes_val = st.text_input("PES", key="manual_pes_num")
    with col_qty:
        qty_val = st.number_input("QUANTITAT", min_value=0.0, step=1.0, key="manual_qty_num", on_change=cb_recalculate_manual_pct)
    with col_pct:
        pct_val = st.number_input("%", min_value=0.0, max_value=100.0, step=1.0, key="manual_pct_num", on_change=cb_recalculate_manual_pct)
    with col_preu:
        preu_val = st.number_input("PREU UNIT.", min_value=0.0, step=0.01, key="manual_preu_num", on_change=cb_recalculate_manual_pct)
    with col_prom:
        prom_val = st.number_input("PROMOCIÓ", min_value=0.0, step=0.01, key="manual_prom_num")
        
    tot_linea_val = (qty_val * preu_val) - prom_val
    with col_tot:
        st.text_input("TOTAL LÍNIA", value=f"{tot_linea_val:,.2f} €", disabled=True)
    with col_reb:
        reb_val = st.checkbox("Reb.", key="manual_reb_chk")
    with col_add:
        st.button("Intro línia", key="btn_add_line", type="secondary", on_click=cb_add_ticket_line)

    # Render error if validation failed in callback
    if "manual_input_error" in st.session_state:
        st.error(st.session_state["manual_input_error"])

    # Table Grid
    if items:
        st.write("")
        st.markdown("##### 📝 Línies del Tiquet")
        
        with st.container(height=300):
            st.markdown("<div class='ticket-lines-container'></div>", unsafe_allow_html=True)
            st.markdown("""
            <style>
            div[data-testid="stVerticalBlock"]:has(.ticket-lines-container) {
                gap: 0rem !important;
            }
            div[data-testid="stVerticalBlock"]:has(.ticket-lines-container) > div {
                padding-top: 0 !important;
                padding-bottom: 0 !important;
            }
            div[data-testid="stVerticalBlock"]:has(.ticket-lines-container) hr {
                margin: 4px 0 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            # Render a beautiful Streamlit grid with row-level buttons
            col_headers = st.columns([0.4, 1.4, 2.0, 0.8, 0.6, 1.0, 0.8, 1.0, 0.6, 0.5, 0.5])
            with col_headers[0]: st.markdown("**#**")
            with col_headers[1]: st.markdown("**FAMÍLIA**")
            with col_headers[2]: st.markdown("**ARTICLE**")
            with col_headers[3]: st.markdown("**PES**")
            with col_headers[4]: st.markdown("**QTY**")
            with col_headers[5]: st.markdown("**PREU U.**")
            with col_headers[6]: st.markdown("**PROM.**")
            with col_headers[7]: st.markdown("**TOTAL**")
            with col_headers[8]: st.markdown("**REB.**")
            with col_headers[9]: st.markdown("")
            with col_headers[10]: st.markdown("")
            
            st.markdown("<hr style='margin: 4px 0 8px 0; border-color: #334155;'/>", unsafe_allow_html=True)
            
            def _cell(text, color="", bold=False):
                fw = "font-weight:bold;" if bold else ""
                c = f"color:{color};" if color else ""
                st.markdown(f"<div style='margin-bottom:-12px; padding-top:6px; font-size:0.9rem; {fw} {c}'>{text}</div>", unsafe_allow_html=True)

            for i, item in enumerate(items):
                cols = st.columns([0.4, 1.4, 2.0, 0.8, 0.6, 1.0, 0.8, 1.0, 0.6, 0.5, 0.5], vertical_alignment="center")
                with cols[0]:
                    _cell(f"{i+1}")
                with cols[1]:
                    if item["familia"] == 'Pendent':
                        _cell("Pendent", color="#ef4444", bold=True)
                    else:
                        _cell(item["familia"])
                with cols[2]:
                    if item["article"] == 'pendent':
                        _cell("pendent", color="#ef4444", bold=True)
                    else:
                        _cell(item["article"])
                with cols[3]:
                    p_str = str(item['pes']).strip()
                    if p_str.replace('.', '', 1).isdigit() and float(p_str) > 0:
                        _cell(f"{p_str}g")
                    else:
                        _cell(p_str if p_str else "0g")
                with cols[4]:
                    _cell(f"{item['quantitat']}")
                with cols[5]:
                    _cell(f"{item['preuUnit']:.2f} €")
                with cols[6]:
                    if item['prom'] > 0:
                        _cell(f"-{item['prom']:.2f} €", color="#ef4444")
                    else:
                        _cell("0.00 €")
                with cols[7]:
                    _cell(f"{item['totLinea']:.2f} €", bold=True)
                with cols[8]:
                    _cell("🧺" if item['rebost'] == 'rebost' else "")
                with cols[9]:
                    st.button("✏️", key=f"btn_edit_row_{i}", on_click=cb_edit_ticket_item, args=(i,), help="Modificar línia")
                with cols[10]:
                    st.button("🗑️", key=f"btn_del_row_{i}", on_click=cb_del_ticket_item, args=(i,), help="Eliminar línia")
                st.markdown("<hr style='margin: 4px 0; border-color: #1e293b;'/>", unsafe_allow_html=True)
            st.write("")
    else:
        st.info("El tiquet està buit. Afegeix línies manualment o puja un tiquet per fitxer o càmara.")



    st.write("---")
    col_desc, col_b1, col_b2, col_b3 = st.columns([3, 2, 2, 5], vertical_alignment="bottom")
    
    with col_desc:
        st.number_input("Descompte global del Tiquet (€):", min_value=0.0, step=0.01, key="ticket_discount")

    with col_b1:
        st.button("Fi Tiquet", key="btn_finalize_ticket", type="primary", on_click=cb_finalize_ticket)
                
    with col_b2:
        st.button("Netejar Tiquet", key="btn_clear_ticket", on_click=cb_clear_ticket)

# ----------------- HEADER AREA -----------------
if "finalize_success" in st.session_state:
    st.toast(st.session_state["finalize_success"], icon="✅")
    del st.session_state["finalize_success"]

col_logo, col_title, col_super = st.columns([0.8, 8.7, 2.5], vertical_alignment="center")
with col_logo:
    if os.path.exists("logoEXD.png"):
        st.image("logoEXD.png", width=65)
with col_title:
    st.markdown("<h2 style='margin:0; color:#f39c12;'>Dashboard Despeses</h2>", unsafe_allow_html=True)
with col_super:
    if "viewing_compres_super" not in st.session_state:
        st.session_state["viewing_compres_super"] = False
    if st.session_state["viewing_compres_super"]:
        if st.button("⬅️ Tornar al Dashboard", use_container_width=True):
            st.session_state["viewing_compres_super"] = False
            st.rerun()
    else:
        if st.button("🛒 Compres Súper", use_container_width=True):
            st.session_state["viewing_compres_super"] = True
            st.rerun()

if st.session_state.get("viewing_compres_super", False):
    render_compres_super_interface()
    st.stop()



# Determine default year/month before the tab runs
years_list = sorted(list(df_desp['any'].dropna().unique()), reverse=True)
if 2026 not in years_list:
    years_list.insert(0, 2026)

# Access or default the values
selected_year = st.session_state.get("sel_year", datetime.today().year)

# Default month is always current month
current_month_index = datetime.today().month - 1
selected_month_cat = CATALAN_MONTHS[current_month_index]
selected_month_data = month_translations[selected_month_cat]
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
            b_desp = df_desp[(mask_visa_exp | mask_visa_pay) & (df_desp['any'] == selected_year)].copy()
            # Convert payment's Import càrrec to import ingrés so it reduces the debt!
            is_payment = (b_desp['Idcategoria'] == 'op_banc') & (b_desp['Idconcepte'] == 'Pago VISA')
            b_desp.loc[is_payment, 'import ingrés'] = b_desp.loc[is_payment, 'import ingrés'].fillna(0) + b_desp.loc[is_payment, 'Import càrrec'].fillna(0)
            b_desp.loc[is_payment, 'Import càrrec'] = 0.0
        else:
            b_desp = df_desp[(df_desp['Banc'].isin(csv_names)) & (df_desp['any'] == selected_year)].copy()
            # Exclude VISA payments entirely since the bank settlement covers it
            b_desp = b_desp[b_desp['FormaPago'].fillna('') != 'VISA']
                
        # Calculate starting balance by including EVERYTHING up to Dec 31 of previous year
        prev_target = (selected_year - 1) * 12 + 12
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


# ----------------- TABS SYSTEM -----------------
tabs_list = [
        "📊 Dashboard General", "📋 Detalls del Mes", "📝 Intro Dades", "💬 Xat IA"
    ]
if st.session_state.get("role") in ["admin", "guest"]:
    tabs_list.extend(["🛒 Llista de la Compra", "📦 Rebost / Stock"])

if st.session_state.get("role") == "admin":
    tabs_list.extend(["🗄️ Bases de Dades (Supabase)", "📜 Registre d'Accions"])
    
tabs = st.tabs(tabs_list)
tab_dash = tabs[0]
tab_details = tabs[1]
tab_intro = tabs[2]
tab_xat = tabs[3]

tab_idx = 4
if st.session_state.get("role") in ["admin", "guest"]:
    tab_compra = tabs[tab_idx]
    tab_rebost = tabs[tab_idx + 1]
    tab_idx += 2
else:
    tab_compra = None
    tab_rebost = None

if st.session_state.get("role") == "admin":
    tab_db = tabs[tab_idx]
    tab_log = tabs[tab_idx + 1]
# ================= TAB 1: DASHBOARD GENERAL =================
with tab_dash:
    # 1. Container for bank metrics (physically at the top)
    bank_metrics_container = st.container()
    
    st.write("")
    
    # 2. Row of Title and Filters Popover (in place of Juny 2026)
    col_sum_lbl, col_sum_btn = st.columns([11.4, 0.6], vertical_alignment="center")
    with col_sum_lbl:
        st.markdown(f"<h3 style='margin:0; color:#f39c12;'>📅 Resum Mensual d'Ingressos i Despeses {selected_year}</h3>", unsafe_allow_html=True)
    with col_sum_btn:
        with st.popover("⚙️", use_container_width=False):
            selected_year = st.selectbox("Any", years_list, index=years_list.index(selected_year) if selected_year in years_list else 0, key="sel_year")

    # 3. Re-calculate balances and render bank metrics at the top container
    current_balances = get_balances_up_to(selected_year, selected_month_data)
    # Remove TR Cartera from Dashboard General balances as requested
    current_balances = {k: v for k, v in current_balances.items() if k != 'TR Cartera'}
    
    total_accounts_balance = sum(v for k, v in current_balances.items() if k != 'Pago VISA') + current_balances.get('Pago VISA', 0.0)
    
    with bank_metrics_container:
        col_bal_title, col_bal_metrics = st.columns([1.6, 10.4], vertical_alignment="center")
        with col_bal_title:
            st.markdown(f"<h3 style='margin:0; font-size: 1.3rem;'>💰 Saldo Comptes:<br><span style='color: #22c55e;'>{total_accounts_balance:,.2f} €</span></h3>", unsafe_allow_html=True)
        with col_bal_metrics:
            # Apply custom styling to the nested horizontal block (the one containing the buttons)
            st.markdown("""
                <style>
                div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button {
                    background-color: #0f172a !important;
                    border: 1px solid #334155 !important;
                    border-radius: 8px !important;
                    min-height: 65px !important;
                    min-width: 130px !important;
                    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3) !important;
                    height: 100% !important;
                    padding: 5px !important;
                }
                div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button:hover {
                    border-color: #f39c12 !important;
                }
                div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button p {
                    text-transform: uppercase;
                    font-size: 0.85rem;
                    color: #f1f5f9;
                    font-weight: 600;
                    line-height: 1.4;
                    margin: 0;
                    white-space: nowrap !important;
                }
                /* Make the green/red value larger */
                div[data-testid="stHorizontalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button p span {
                    font-size: 1.15rem;
                    text-transform: none;
                    font-weight: bold;
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
                    
                    label = f"{b_name}\n\n{val_str}"
                    if st.button(label, key=f"btn_bank_{b_name}", use_container_width=True):
                        show_bank_extract_modal(b_name, selected_year, selected_month_data)
    
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
        sub_desp_inflows = sub_desp[sub_desp['Idcategoria'] != 'op_banc']
        
        # Fixed incomes = anything categorized as 'ingres_general' or 'ingrés_general'
        ing_fixes = sub_desp_inflows[sub_desp_inflows['Idcategoria'].isin(['ingres_general', 'ingrés_general'])]['import ingrés'].sum()
        
        # Extra incomes = anything NOT categorized as 'ingres_general' or 'ingrés_general'
        ing_extres = sub_desp_inflows[~sub_desp_inflows['Idcategoria'].isin(['ingres_general', 'ingrés_general'])]['import ingrés'].sum()
        
        ing_total = ing_fixes + ing_extres

        
        # Expenses
        sub_desp = year_desp[year_desp['clean_mes'] == m_data]
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
            'Desp. Fixes': exp_fixes,
            'Desp. Menjar': exp_menjar,
            'Desp. Rebost': exp_rebost,
            'Desp. Gasolina': exp_gasolina,
            'Desp. Restaurant': exp_restaurant,
            'Desp. Farmàcia': exp_farmacia,
            'Desp. Neteja': exp_neteja,
            'Desp. Varis': exp_varis,
            'Desp. Proveïdor': exp_proveidor,
            'Desp. Total': exp_total,
            'Saldo': saldo_total
        })
        
    df_summary = pd.DataFrame(summary_data)
    
    # Calculate Totals Row
    totals_row = {'Mes': 'TOTAL'}
    for col in df_summary.columns:
        if col != 'Mes':
            totals_row[col] = df_summary[col].sum()
    df_summary = pd.concat([df_summary, pd.DataFrame([totals_row])], ignore_index=True)
    
    # Style formatter to highlight values exceeding limit in red
    def highlight_exceeded_limits(df):
        style_df = pd.DataFrame('', index=df.index, columns=df.columns)
        col_mapping = {
            'Desp. Menjar': 'menjar',
            'Desp. Gasolina': 'gasolina',
            'Desp. Restaurant': 'restaurant',
            'Desp. Farmàcia': 'farmacia',
            'Desp. Neteja': 'neteja',
            'Desp. Varis': 'varis'
        }
        for idx, row in df.iterrows():
            if row['Mes'] == 'TOTAL':
                continue
            m_name = str(row['Mes']).lower()
            m_data = month_translations.get(m_name, 'enero')
            
            # Highlight current selected month in yellow text (no background)
            if m_name == selected_month_cat.lower():
                style_df.at[idx, 'Mes'] = 'color: #f1c40f; font-weight: bold;'
                
            row_limits = get_limits_for(selected_year, m_data)
            
            for col_name, limit_key in col_mapping.items():
                val = row[col_name]
                lim = row_limits.get(limit_key, float('inf'))
                if val > lim:
                    style_df.at[idx, col_name] = 'background-color: #7f1d1d; color: #fecaca; font-weight: bold;'
        return style_df

    # Check limits for selected month/year to show alert banner
    selected_limits = get_limits_for(selected_year, selected_month_data)
    selected_month_summary = df_summary[df_summary['Mes'].str.lower() == selected_month_cat.lower()]
    if not selected_month_summary.empty:
        m_row = selected_month_summary.iloc[0]
        exceeded_list = []
        col_mapping_alert = {
            'Desp. Menjar': ('menjar', 'menjar'),
            'Desp. Gasolina': ('gasolina', 'gasolina'),
            'Desp. Restaurant': ('restaurant', 'restaurant'),
            'Desp. Farmàcia': ('farmàcia', 'farmacia'),
            'Desp. Neteja': ('neteja', 'neteja'),
            'Desp. Varis': ('varis', 'varis')
        }
        for col_name, (display_lbl, limit_key) in col_mapping_alert.items():
            val = m_row[col_name]
            lim = selected_limits.get(limit_key, float('inf'))
            if val > lim:
                exceeded_list.append(f"**{display_lbl}** ({val:,.2f} € > {lim:,.2f} €)")
        if exceeded_list:
            st.error(f"⚠️ **Valor superat**: {', '.join(exceeded_list)}")

    # Alerta de canvi d'oli
    kms_left = st.session_state.get("kms_canvi_oli", 31491.0) - car_kms_actuals
    if kms_left <= 0:
        st.error(f"🔧 **Atenció!** Cal fer el canvi d'oli del cotxe. Teniu el límit superat per {int(abs(kms_left))} km.")
    # Display styled summary grid using static compact HTML table
    st.table(
        df_summary.style.format(precision=2, thousands=".", decimal=",")
        .apply(highlight_exceeded_limits, axis=None)
        .background_gradient(subset=['Saldo'], cmap='RdYlGn', vmin=-1000, vmax=1000)
        .highlight_max(subset=['Ing. Total'], color='#27ae60')
        .highlight_max(subset=['Desp. Total'], color='#c0392b')
    )
    
    st.write("")
    
    # 4. Charts block
    show_charts = st.checkbox("Mostra gràfics", value=True)
    if show_charts:
        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("<h4 style='color:#f39c12;'>📈 Previsió ingressos/despeses</h4>", unsafe_allow_html=True)
            # Calculate summary for the last 2 years for the chart
            chart_data = []
            for yr in [selected_year - 1, selected_year]:
                year_desp_c = df_desp[df_desp['any'] == yr]
                year_ing_c = df_ing[(df_ing['any'] == yr) & (df_ing['cobrat'].astype(str).str.lower() == 'cobrat')]
                
                for m_cat in CATALAN_MONTHS:
                    m_data = month_translations[m_cat]
                    
                    # Incomes
                    sub_ing = year_ing_c[year_ing_c['clean_mes'] == m_data]
                    ing_total = sub_ing['Import'].sum()
                    
                    # Expenses
                    sub_desp = year_desp_c[year_desp_c['clean_mes'] == m_data]
                    cat_series = sub_desp['Idcategoria'].astype(str)
                    exp_total = sub_desp[~cat_series.str.contains('op_banc|ingres_general|ingrés_general|ingres_extra|ingrés_extra', case=False, na=False)]['Import càrrec'].sum()
                    
                    chart_data.append({
                        'Mes-Any': f"{m_cat.capitalize()[:3]} {str(yr)[2:]}",
                        'Ingressos': ing_total,
                        'Despeses': exp_total
                    })
            df_chart_2yrs = pd.DataFrame(chart_data)
            
            fig_bar = graph_objects.Figure()
            fig_bar.add_trace(graph_objects.Bar(x=df_chart_2yrs['Mes-Any'], y=df_chart_2yrs['Ingressos'], name='Ingressos', marker_color='#2ecc71'))
            fig_bar.add_trace(graph_objects.Bar(x=df_chart_2yrs['Mes-Any'], y=df_chart_2yrs['Despeses'], name='Despeses', marker_color='#e74c3c'))
            fig_bar.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#f8fafc'),
                xaxis=dict(gridcolor='#334155', tickangle=-45),
                yaxis=dict(gridcolor='#334155')
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with chart_col2:
            st.markdown("<h4 style='color:#f39c12;'>🍕 Compres Super %</h4>", unsafe_allow_html=True)
            # Pie chart of compresSuper for selected month
            super_sub = df_super[(df_super['any'] == selected_year) & (df_super['mes'].str.lower() == selected_month_data)]
            if not super_sub.empty:
                df_pie = super_sub.groupby('familia')['totLinea'].sum().reset_index()
                fig_pie = px.pie(df_pie, values='totLinea', names='familia', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8fafc')
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info(f"No hi ha dades de compres de supermercat per a {selected_month_cat} del {selected_year}.")
                
        st.write("")
        # 🔧 Oil change section moved here
        st.markdown("<h4 style='color:#f39c12;'>🔧 Canvi d'oli cotxe</h4>", unsafe_allow_html=True)
        col_oil1, col_oil2, col_oil3, col_oil_space = st.columns([2, 2, 2, 6])
        with col_oil1:
            st.metric("Kms actuals", f"{int(car_kms_actuals):,}")
        with col_oil2:
            st.session_state["kms_canvi_oli"] = st.number_input("Kms canvi oli", value=st.session_state["kms_canvi_oli"], step=1000.0)
        with col_oil3:
            kms_left = st.session_state["kms_canvi_oli"] - car_kms_actuals
            st.metric("Canvi dintre", f"{int(kms_left):,}", delta=f"{int(kms_left)} km left", delta_color="normal" if kms_left > 500 else "inverse")
            
        st.write("")
        st.markdown("<h4 style='color:#f39c12;'>⛽ Consum Cotxe (L/100km)</h4>", unsafe_allow_html=True)
        # Compute annual fuel consumption
        df_gas['parsed_date'] = df_gas['data'].apply(parse_excel_date)
        df_km['parsed_date'] = df_km['data'].apply(parse_excel_date)
        
        df_gas_tivoli = df_gas[df_gas['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_gas.columns else df_gas
        df_km_tivoli = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km
        
        gas_yr = df_gas_tivoli.groupby(df_gas_tivoli['parsed_date'].dt.year)['litres'].sum()
        km_yr = df_km_tivoli.groupby(df_km_tivoli['parsed_date'].dt.year)['km'].sum()
        
        consumption = ((gas_yr / km_yr) * 100).dropna().reset_index()
        consumption.columns = ['Any', 'L/100km']
        consumption['Any'] = consumption['Any'].astype(str)
        
        fig_line = px.bar(consumption, x='Any', y='L/100km', text_auto='.2f', color_discrete_sequence=['#f39c12'])
        fig_line.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            xaxis=dict(gridcolor='#334155'),
            yaxis=dict(gridcolor='#334155')
        )
        st.plotly_chart(fig_line, use_container_width=True)

# ================= TAB 2: DETALLS DEL MES =================
with tab_details:
    st.markdown(f"### 🔍 Detalls de {selected_month_cat.capitalize()} del {selected_year}")
    
    col_left, col_mid, col_right = st.columns([1, 1.5, 1.5])
    
    with col_left:
        st.markdown("<h4 style='color:#f39c12;'>📋 Pagaments Pendents</h4>", unsafe_allow_html=True)
        
        has_pending = False
        total_pendent = 0.0
        shown_concepts = set()
        
        # 1. Hipoteca status
        sub_hip = df_hip[(df_hip['any'] == selected_year) & (df_hip['mes'].str.lower() == selected_month_data)]
        if not sub_hip.empty:
            hip_row = sub_hip.iloc[0]
            status_hip = "Pagat" if str(hip_row['pagat']).lower() == 'pagat' else "Pendent"
            if status_hip == "Pendent":
                amt = hip_row['Quota fixa']
                st.markdown(f"**🏠 Hipoteca**: {amt:.2f} € (<span style='color:red;'>{status_hip}</span>)", unsafe_allow_html=True)
                has_pending = True
                total_pendent += float(amt)
                shown_concepts.add('hipoteca')
        else:
            st.write("🏠 **Hipoteca**: No programada")
            
        # 2. Pagaments de la taula Previsió de Pagaments
        sub_pag = df_pag[
            (df_pag['any'] == selected_year) & 
            (df_pag['mes'].astype(str).str.lower().str.strip() == selected_month_data.lower().strip()) & 
            (df_pag['pagat'].astype(str).str.lower().str.strip() != 'pagat')
        ]
        
        for _, p_row in sub_pag.iterrows():
            concept_lower = str(p_row['Concepte']).lower().strip()
            if concept_lower in shown_concepts:
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
                
            amt = float(p_row['Import'])
            st.markdown(f"**{icon} {p_row['Concepte']}**: {amt:.2f} € (<span style='color:red;'>Pendent</span>)", unsafe_allow_html=True)
            has_pending = True
            total_pendent += amt
            shown_concepts.add(concept_lower)
            
        if not has_pending:
            st.info("No hi ha cap pagament pendent aquest mes.")
        else:
            st.markdown("---")
            st.markdown(f"<div style='text-align:left; font-size:2.2rem; color:#ef4444; padding-top:0.5rem; line-height:1.2;'>{total_pendent:,.2f} €</div>", unsafe_allow_html=True)
            
    with col_mid:
        st.markdown("<h4 style='color:#f39c12;'>📥 Ingressos del Mes</h4>", unsafe_allow_html=True)
        # Load ingressos list for selected month
        month_ing = df_ing[(df_ing['any'] == selected_year) & (df_ing['clean_mes'] == selected_month_data)]
        if not month_ing.empty:
            try:
                st.dataframe(
                    month_ing[['Concepte', 'Import', 'cobrat']].style.format({'Import': '{:,.2f} €'}),
                    use_container_width=True,
                    hide_index=True
                )
            except Exception as e:
                st.error(f"Error rendering month_ing: {e}")
            st.metric("Total Ingressat", f"{month_ing['Import'].sum():,.2f} €")
        else:
            st.info("No hi ha dades d'ingressos per aquest mes.")
            
    with col_right:
        st.markdown("<h4 style='color:#f39c12;'>📤 Càrrecs per Categoria</h4>", unsafe_allow_html=True)
        month_desp = df_desp[(df_desp['any'] == selected_year) & (df_desp['clean_mes'] == selected_month_data)]
        if not month_desp.empty:
            # Exclude op_banc!
            month_desp_filtered = month_desp[month_desp['Idcategoria'] != 'op_banc']
            
            grouped_desp = month_desp_filtered.groupby('Idcategoria')['Import càrrec'].sum().reset_index()
            grouped_desp = grouped_desp[grouped_desp['Import càrrec'] > 0].sort_values(by='Import càrrec', ascending=False)
            
            try:
                event = st.dataframe(
                    grouped_desp.style.format({'Import càrrec': '{:,.2f} €'}),
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
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

# ================= TAB 3: INTRO DADES =================

@st.dialog("⚠️ Avís: Diferència amb la Previsió")
def show_mismatch_dialog(target_table_name, scheduled_import, input_import, idx, status_col, new_row_desp, is_gas_cat, new_row_gas, is_hipoteca, is_estalvis, df_to_update, csv_filename):
    st.markdown(f"Hi ha una previsió pendent per aquest concepte per valor de **{scheduled_import:,.2f} €**.")
    st.markdown(f"Has introduït **{input_import:,.2f} €**.")
    
    st.write("Què vols fer?")
    
    if st.button(f"✅ Acceptar import previsió ({scheduled_import:,.2f} €)", use_container_width=True):
        if target_table_name == 'pagaments':
            new_row_desp['Import càrrec'] = scheduled_import
        else:
            new_row_desp['import ingrés'] = scheduled_import
            
        df_to_update.loc[idx, status_col] = 'Pagat' if target_table_name == 'pagaments' else 'Cobrat'
        save_to_csv(df_to_update.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), csv_filename)
        
        if target_table_name == 'pagaments':
            st.session_state["df_pag"] = df_to_update
        else:
            st.session_state["df_ing"] = df_to_update
            
        insert_db_row('despeses', new_row_desp)
        if is_gas_cat:
            insert_db_row('gasolina', new_row_gas)
            
        if is_hipoteca:
            df_hip_local = st.session_state["df_hip"]
            df_hip_local.loc[(df_hip_local['any'] == new_row_desp['any']) & (df_hip_local['mes'].str.lower() == new_row_desp['mes'].lower()), 'pagat'] = "pagat"
            save_to_csv(df_hip_local, 'hipoteca.csv')
            st.session_state["df_hip"] = df_hip_local
            
        if is_estalvis:
            df_est_local = st.session_state["df_est"]
            df_est_local.loc[(df_est_local['any'] == new_row_desp['any']) & (df_est_local['mes'].str.lower() == new_row_desp['mes'].lower()), 'pagat'] = "pagat"
            save_to_csv(df_est_local, 'estalviDP.csv')
            st.session_state["df_est"] = df_est_local
            
        st.success("Desat correctament aplicant la previsió!")
        st.session_state["desp_version"] = st.session_state.get("desp_version", 0) + 1
        st.rerun()

    if st.button(f"✏️ Modificar previsió a {input_import:,.2f} €", use_container_width=True):
        df_to_update.loc[idx, 'Import'] = input_import
        df_to_update.loc[idx, status_col] = 'Pagat' if target_table_name == 'pagaments' else 'Cobrat'
        save_to_csv(df_to_update.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), csv_filename)
        
        if target_table_name == 'pagaments':
            st.session_state["df_pag"] = df_to_update
        else:
            st.session_state["df_ing"] = df_to_update
            
        insert_db_row('despeses', new_row_desp)
        if is_gas_cat:
            insert_db_row('gasolina', new_row_gas)
            
        if is_hipoteca:
            df_hip_local = st.session_state["df_hip"]
            df_hip_local.loc[(df_hip_local['any'] == new_row_desp['any']) & (df_hip_local['mes'].str.lower() == new_row_desp['mes'].lower()), 'pagat'] = "pagat"
            save_to_csv(df_hip_local, 'hipoteca.csv')
            st.session_state["df_hip"] = df_hip_local
            
        if is_estalvis:
            df_est_local = st.session_state["df_est"]
            df_est_local.loc[(df_est_local['any'] == new_row_desp['any']) & (df_est_local['mes'].str.lower() == new_row_desp['mes'].lower()), 'pagat'] = "pagat"
            save_to_csv(df_est_local, 'estalviDP.csv')
            st.session_state["df_est"] = df_est_local
            
        st.success("Desat correctament modificant la previsió!")
        st.session_state["desp_version"] = st.session_state.get("desp_version", 0) + 1
        st.rerun()

    if st.button("❌ Denegar (Cancel·lar inserció)", use_container_width=True):
        # Do absolutely nothing, just close dialog and reset form (or not reset form, just close)
        st.rerun()


with tab_intro:
    
    # Inject JavaScript to focus the next input when pressing Enter
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const target = e.target;
                if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.getAttribute('role') === 'combobox') {
                    const inputs = Array.from(doc.querySelectorAll('input:not([type="hidden"]):not([disabled]), select:not([disabled]), [role="combobox"]:not([disabled])'));
                    const index = inputs.indexOf(target);
                    if (index > -1 && index < inputs.length - 1) {
                        e.preventDefault();
                        e.stopPropagation();
                        inputs[index + 1].focus();
                    }
                }
            }
        }, true);
        </script>
        """,
        height=0,
        width=0
    )


    version = st.session_state.get("desp_version", 0)
    def clear_form_state(prefix):
        if prefix == "desp_":
            st.session_state["desp_version"] = st.session_state.get("desp_version", 0) + 1
        elif prefix == "km_":
            st.session_state["km_version"] = st.session_state.get("km_version", 0) + 1
            
        for k in list(st.session_state.keys()):
            if k.startswith(prefix) and k not in ["desp_version", "km_version"]:
                del st.session_state[k]
    
    options = ["Moviment Real (Despesa)", "Previsió de Pagament", "Previsió d'Ingrés", "Compra Súper", "Km Cotxe", "Moviment TR Cartera"]
    default_idx = 0
    if st.session_state.get('requested_view') in options:
        default_idx = options.index(st.session_state['requested_view'])
    
    data_type = st.selectbox("Tipus de registre", options, index=default_idx)
    
    if 'requested_view' in st.session_state:
        del st.session_state['requested_view']
    title_text = "Km Cotxe Tívoli" if data_type == "Km Cotxe" else data_type
    st.markdown(f"### ➕ Introduir Nou Registre: {title_text}")
    
    st.write("---")
    
    # 2-line compressed layout for all form types
    if data_type == "Moviment Real (Despesa)":
        # Row 1 (4 columns)
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
        with r1_col1:
            banks_opt = [""] + get_config_banks()
            banc = st.selectbox("Banc", banks_opt, index=0, key=f"desp_banc_{version}")
        with r1_col2:
            pay_methods_opt = [""] + get_config_payment_methods()
            if banc == "TR Cartera" and "Compte" in pay_methods_opt:
                st.session_state[f"desp_forma_pago_{version}"] = "Compte"
            forma_pago = st.selectbox("Forma de Pagament", pay_methods_opt, key=f"desp_forma_pago_{version}")
        with r1_col3:
            data_val = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key=f"desp_data_{version}")
            mes_val = month_translations[CATALAN_MONTHS[data_val.month - 1]]
            any_val = data_val.year
        with r1_col4:
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                import_carg = st.number_input("Import Càrrec (€)", value=0.0, step=0.01, key=f"desp_import_carg_{version}")
            with sub_col2:
                import_ing = st.number_input("Import Ingrés (€)", value=0.0, step=0.01, key=f"desp_import_ing_{version}")
            
        # Dialog calculator helper for Gasolina price per litre
        @st.dialog("⛽ Calculadora de Litres per Preu/Litre")
        def show_gasoline_calculator_in_desp():
            st.markdown("Introdueix l'import pagat i el preu per litre per calcular els litres automàticament.")
            calc_import = st.number_input("Import total pagat (€):", min_value=0.0, value=st.session_state.get(f"desp_import_carg_{version}", 0.0), step=0.01)
            calc_preu_l = st.number_input("Preu per litre (€/l):", min_value=0.001, value=1.500, step=0.001, format="%.3f")
            
            calc_litres = calc_import / calc_preu_l if calc_preu_l > 0 else 0.0
            st.markdown(f"**Litres estimats**: `{calc_litres:.2f} l` (`{calc_import:.2f} € / {calc_preu_l:.3f} €/l`)")
            
            if st.button("Aplicar al formulari"):
                st.session_state[f"desp_import_carg_{version}"] = calc_import
                st.session_state[f"desp_litres_{version}"] = calc_litres
                st.rerun()

        # Row 2 (4 columns)
        r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
        with r2_col1:
            if banc == "TR Cartera":
                grup_options = ["op_banc"]
            else:
                grup_options = ["", "Càrrec", "op_banc", "Ingrés"]
            grup_val = st.selectbox("Grup", grup_options, index=0, key=f"desp_grup_{version}")
        with r2_col2:
            if banc == "TR Cartera":
                categories_opt = ["op_banc"]
            else:
                categories_opt = [""] + get_config_categories()
            cat_val = st.selectbox("Categoria", categories_opt, index=0, key=f"desp_cat_{version}")
        with r2_col3:
            concept_options = [""] + get_config_concepts(cat_val) + ["➕ Afegir nou..."] if cat_val else [""]
            concept_val = st.selectbox("Concepte", concept_options, index=0, key=f"desp_concepte_{version}")
        with r2_col4:
            comentari_val = st.text_input("Comentari", value="", key=f"desp_comentari_{version}")
        
        # If adding a new concept, show custom inputs
        if concept_val == "➕ Afegir nou...":
            custom_col1, custom_col2, custom_col3 = st.columns([4, 4, 4])
            with custom_col1:
                custom_concept = st.text_input("Nou Concepte (escriu el nom):", key=f"desp_custom_concept_{version}")
            with custom_col2:
                st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                save_new_concept = st.checkbox("Desar a la llista permanent?", value=True, key=f"desp_save_new_concept_{version}")

        # Row 3 (ticket pendent)
        ticket_pendent = st.checkbox("Aquesta despesa és una compra de súper amb ticket pendent de desglossar", key=f"desp_ticket_pendent_{version}")

        # Dynamic extra fields for Gasolina category inside Moviment Real form
        is_gas_cat = (str(cat_val).lower() == "gasolina")
        if is_gas_cat:
            st.markdown("<h5 style='color:#f39c12; margin-top:5px; margin-bottom:5px;'>⛽ Paràmetres del proveïment de gasolina</h5>", unsafe_allow_html=True)
            gas_col1, gas_col2, gas_col3, gas_col4 = st.columns(4)
            with gas_col1:
                cars_list = sorted(list(df_gas['cotxe'].dropna().unique()))
                if "tívoli" not in cars_list:
                    cars_list = ["tívoli"] + cars_list
                default_car_idx = cars_list.index("tívoli") if "tívoli" in cars_list else 0
                gas_cotxe = st.selectbox("Cotxe", cars_list, index=default_car_idx, key=f"desp_gas_cotxe_{version}")
            with gas_col2:
                gas_preu_l = st.number_input("Preu per litre (€/l)", min_value=0.0, value=1.214, step=0.001, format="%.3f", key=f"desp_gas_preu_l_{version}")
            with gas_col3:
                calculated_litres = import_carg / gas_preu_l if gas_preu_l > 0 else 0.0
                st.session_state[f"desp_litres_{version}"] = calculated_litres
                st.markdown(f"<div style='margin-top:28px; font-weight:bold; font-size:0.95rem; color:#f39c12;'>Litres: {calculated_litres:.2f} l</div>", unsafe_allow_html=True)
            with gas_col4:
                st.write("")
            
        col_btns = st.columns([1.8, 1.8, 8.4])
        with col_btns[0]:
            submitted = st.button("Desar", type="primary", use_container_width=True)
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key="cancel_desp", use_container_width=True)
        if cancelled:
            clear_form_state("desp_")
            st.rerun()
        if submitted:
            # Determine actual concept to save
            actual_concept = concept_val
            if concept_val == "➕ Afegir nou...":
                custom_concept_val = st.session_state.get(f"desp_custom_concept_{version}", "").strip()
                if not custom_concept_val:
                    st.error("⚠️ Heu d'escriure el nom del nou concepte.")
                else:
                    actual_concept = custom_concept_val
            
            if not actual_concept or actual_concept == "➕ Afegir nou...":
                # Keep error message trigger
                pass
                
            # Perform group vs import criteria checks
            if grup_val == "Càrrec" and import_ing != 0.0:
                st.error("⚠️ El grup és Càrrec, per tant l'Import Ingrés ha de ser 0.")
            elif grup_val == "Ingrés" and import_carg != 0.0:
                st.error("⚠️ El grup és Ingrés, per tant l'Import Càrrec ha de ser 0.")
            elif grup_val == "op_banc" and import_carg != 0.0 and import_ing != 0.0:
                st.error("⚠️ Per a op_banc s'ha d'emplenar només un dels dos imports (Càrrec o Ingrés), no tots dos.")
            elif grup_val == "op_banc" and import_carg == 0.0 and import_ing == 0.0:
                st.error("⚠️ Per a op_banc s'ha d'introduir un import (Càrrec o Ingrés).")
            elif import_carg == 0.0 and import_ing == 0.0:
                st.error("⚠️ S'ha d'introduir un import vàlid (Càrrec o Ingrés).")
            elif not banc or (banc not in ["Efectiu", "Casa"] and not forma_pago) or not cat_val or not actual_concept or actual_concept == "➕ Afegir nou..." or not grup_val:
                st.error("⚠️ Tots els camps (Banc, Forma de Pagament, Categoria, Concepte i Grup) han d'estar omplerts (excepte Forma de Pagament si el banc és Efectiu o Casa).")
            elif is_gas_cat and st.session_state.get(f"desp_litres_{version}", 0.0) <= 0.0:
                st.error("⚠️ Heu d'introduir un preu per litre vàlid per calcular els litres de gasolina.")
            else:
                # If "➕ Afegir nou..." was selected and checkmark is true, save it permanently
                if concept_val == "➕ Afegir nou..." and st.session_state.get(f"desp_save_new_concept_{version}", True):
                    add_concept_to_config(cat_val, actual_concept)
                    
                # Prepare objects to save
                new_row_desp = {
                    'ID_mov': int(df_desp['ID_mov'].max() + 1) if not df_desp.empty else 1,
                    'Banc': banc,
                    'FormaPago': forma_pago,
                    'Data': data_val.strftime('%d/%m/%Y'),
                    'mes': mes_val,
                    'any': any_val,
                    'import ingrés': import_ing,
                    'Import càrrec': import_carg,
                    'grup': grup_val,
                    'Idcategoria': cat_val,
                    'Idconcepte': actual_concept,
                    'Comentari': comentari_val,
                    'ticketPendent': bool(ticket_pendent)
                }
                
                new_row_gas = {}
                if is_gas_cat:
                    preu_l_saved = st.session_state.get(f"desp_gas_preu_l_{version}", 1.214)
                    litres_saved = round(import_carg / preu_l_saved, 2) if preu_l_saved > 0 else 0.0
                    new_row_gas = {
                        'idGasolina': int(df_gas['idGasolina'].max() + 1) if not df_gas.empty else 1,
                        'cotxe': st.session_state.get(f"desp_gas_cotxe_{version}"),
                        'data': data_val.strftime('%d/%m/%Y'),
                        'mes': mes_val,
                        'any': any_val,
                        'import': import_carg,
                        '€/l': preu_l_saved,
                        'litres': litres_saved,
                        'lloc': actual_concept
                    }

                is_hipoteca = (str(concept_val).lower() == "hipoteca" or str(cat_val).lower() == "hipoteca")
                is_estalvis = (str(concept_val).lower() == "pj isabel")

                # Define a helper function to save directly
                def do_save_direct():
                    if new_row_desp['Banc'] == 'TR Cartera':
                        new_row_desp['FormaPago'] = 'Compte'
                        
                        concept_lower = str(new_row_desp.get('Idconcepte', '')).lower()
                        is_cashback = 'cashback' in concept_lower
                        
                        if is_cashback:
                            # Only one entry for TR Cartera
                            insert_db_row('despeses', new_row_desp)
                        else:
                            row1 = new_row_desp.copy()
                            row1['Banc'] = 'TradeRep.'
                            row1['Import càrrec'] = new_row_desp['import ingrés']
                            row1['import ingrés'] = new_row_desp['Import càrrec']
                            
                            row2 = new_row_desp.copy()
                            row2['ID_mov'] = row1['ID_mov'] + 1
                            row2['Banc'] = 'TR Cartera'
                            
                            insert_db_row('despeses', row1)
                            insert_db_row('despeses', row2)
                        
                        # Sync to tr_cartera
                        cartera_val = ""
                        concept_lower = str(new_row_desp.get('Idconcepte', '')).lower()
                        if "nvidia" in concept_lower:
                            cartera_val = "NVIDIA"
                        elif "500" in concept_lower or "sp" in concept_lower:
                            cartera_val = "S&P500"
                            
                        tr_concepte = "Compra" if new_row_desp.get('Import càrrec', 0) > 0 else "Venda"
                        if "cashback" in concept_lower:
                            tr_concepte = "CashBack"
                            cartera_val = "S&P500"
                        elif "promo" in concept_lower:
                            tr_concepte = "Promoció"
                            
                        new_tr_row = {
                            'DATA': new_row_desp.get('Data', ''),
                            'mes': new_row_desp.get('mes', ''),
                            'any': new_row_desp.get('any', 2026),
                            'COMPRA': new_row_desp.get('Import càrrec', 0),
                            'VENDA': new_row_desp.get('import ingrés', 0),
                            'CARTERA': cartera_val,
                            'CONCEPTE': tr_concepte,
                            'COMENTARI': new_row_desp.get('Comentari', '')
                        }
                        try:
                            supabase = get_supabase_client(st.session_state.get("role", "guest"))
                            supabase.table("tr_cartera").insert([new_tr_row]).execute()
                        except Exception as e:
                            st.error(f"Error inserint a TR Cartera: {e}")
                    else:
                        insert_db_row('despeses', new_row_desp)
                        
                    if is_gas_cat:
                        insert_db_row('gasolina', new_row_gas)
                    if is_hipoteca:
                        df_hip.loc[(df_hip['any'] == any_val) & (df_hip['mes'].str.lower() == mes_val.lower()), 'pagat'] = "pagat"
                        save_to_csv(df_hip, 'hipoteca.csv')
                        st.session_state["df_hip"] = df_hip
                    if is_estalvis:
                        df_est.loc[(df_est['any'] == any_val) & (df_est['mes'].str.lower() == mes_val.lower()), 'pagat'] = "pagat"
                        save_to_csv(df_est, 'estalviDP.csv')
                        st.session_state["df_est"] = df_est
                    
                    st.success("Moviment real i estats associats desats correctament!")
                    clear_form_state("desp_")
                    st.rerun()

                # Check if it matches any scheduled pagament/ingrés
                mask = None
                target_df = None
                table_name = None
                target_status_col = None
                input_import = 0.0
                csv_filename = None

                if import_carg != 0.0:
                    target_df = df_pag
                    table_name = 'pagaments'
                    target_status_col = 'pagat'
                    input_import = import_carg
                    csv_filename = 'pagaments.csv'
                    if not target_df.empty:
                        mask = (target_df['any'].astype(int) == int(any_val)) & (target_df['mes'].astype(str).str.lower().str.strip() == str(mes_val).lower().strip()) & (target_df['Concepte'].astype(str).str.lower().str.strip() == str(actual_concept).lower().strip()) & (target_df[target_status_col].astype(str).str.lower().str.strip() != 'pagat')
                elif import_ing != 0.0:
                    target_df = df_ing
                    table_name = 'ingressos'
                    target_status_col = 'cobrat'
                    input_import = import_ing
                    csv_filename = 'ingressos.csv'
                    if not target_df.empty:
                        mask = (target_df['any'].astype(int) == int(any_val)) & (target_df['mes'].astype(str).str.lower().str.strip() == str(mes_val).lower().strip()) & (target_df['Concepte'].astype(str).str.lower().str.strip() == str(actual_concept).lower().strip()) & (target_df[target_status_col].astype(str).str.lower().str.strip() != 'cobrat')

                if mask is not None and mask.any():
                    idx = target_df[mask].index[0]
                    scheduled_import = target_df.loc[idx, 'Import']
                    if abs(float(scheduled_import) - float(input_import)) < 0.01:
                        # Exact match
                        target_df.loc[idx, target_status_col] = 'Pagat' if table_name == 'pagaments' else 'Cobrat'
                        save_to_csv(target_df.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), csv_filename)
                        if table_name == 'pagaments':
                            st.session_state["df_pag"] = target_df
                        else:
                            st.session_state["df_ing"] = target_df
                        do_save_direct()
                    else:
                        # Mismatch
                        show_mismatch_dialog(table_name, float(scheduled_import), float(input_import), idx, target_status_col, new_row_desp, is_gas_cat, new_row_gas, is_hipoteca, is_estalvis, target_df, csv_filename)
                else:
                    do_save_direct()

        # Show pending tickets section
        st.write("---")
        st.markdown("<h5 style='color:#f39c12; margin-top: 5px; margin-bottom: 5px;'>🛒 Tickets Pendents de Desglossar</h5>", unsafe_allow_html=True)
        
        pendents = df_desp[df_desp['ticketPendent'] == True] if 'ticketPendent' in df_desp.columns else pd.DataFrame()
        if not pendents.empty:
            for idx, row in pendents.iterrows():
                cols = st.columns([1, 2, 2, 2, 2, 3])
                cols[0].write(f"Nº {row['ID_mov']}")
                cols[1].write(row['Data'])
                cols[2].write(row['Idconcepte'])
                cols[3].write(f"{row['Import càrrec']} €")
                cols[4].write(row['grup'])
                if cols[5].button("Desglossar", key=f"desg_{row['ID_mov']}"):
                    st.session_state['viewing_compres_super'] = True
                    st.session_state['pending_ticket_id'] = row['ID_mov']
                    st.session_state['pending_super'] = row['Idconcepte']
                    st.session_state['pending_data'] = row['Data']
                    st.session_state['pending_banc'] = row['Banc']
                    st.session_state['pending_forma_pago'] = row['FormaPago']
                    st.session_state['pending_import_carrec'] = row['Import càrrec']
                    st.rerun()
        else:
            st.info("No hi ha cap ticket pendent de desglossar.")

            

    elif data_type == "Moviment TR Cartera":
        # Row 1
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
        with r1_col1:
            data_val = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key=f"tr_data_{version}")
            mes_val = month_translations[CATALAN_MONTHS[data_val.month - 1]]
            any_val = data_val.year
        with r1_col2:
            cartera_val = st.selectbox("CARTERA", ["S&P500", "NVIDIA"], key=f"tr_cartera_{version}")
        with r1_col3:
            tr_concepte = st.selectbox("CONCEPTE", ["Compra", "Venda", "Promoció", "CashBack"], key=f"tr_concepte_{version}")
        with r1_col4:
            tr_import = st.number_input("Import (€)", value=0.0, step=0.01, key=f"tr_import_{version}")
            
        # Row 2
        tr_comentari = st.text_input("COMENTARI", value="", key=f"tr_comentari_{version}")
        
        st.write("")
        if st.button("💾 Desar Moviment TR Cartera", type="primary", use_container_width=True):
            if tr_import <= 0 and tr_concepte != "CashBack": # Allow 0 or small for cashback just in case, but warn
                st.error("L'import ha de ser superior a 0")
            else:
                with st.spinner("Desant..."):
                    compra = tr_import if tr_concepte in ["Compra", "CashBack"] else 0.0
                    venda = tr_import if tr_concepte in ["Venda", "Promoció"] else 0.0
                    
                    new_tr_row = {
                        'DATA': data_val.strftime('%Y-%m-%d'),
                        'mes': mes_val,
                        'any': any_val,
                        'COMPRA': compra,
                        'VENDA': venda,
                        'CARTERA': cartera_val,
                        'CONCEPTE': tr_concepte,
                        'COMENTARI': tr_comentari
                    }
                    
                    supabase = get_supabase_client(st.session_state.get("role", "guest"))
                    supabase.table("tr_cartera").insert([new_tr_row]).execute()
                    
                    # Also insert into despeses to balance the bank
                    import_carg = tr_import if tr_concepte == "Compra" else 0.0
                    import_ing = tr_import if tr_concepte != "Compra" else 0.0
                    
                    row_traderep = {
                        'Data': data_val.strftime('%Y-%m-%d'),
                        'mes': mes_val,
                        'any': any_val,
                        'Banc': 'TradeRep.',
                        'FormaPago': 'Compte',
                        'Import càrrec': import_carg,
                        'import ingrés': import_ing,
                        'grup': 'op_banc',
                        'Idcategoria': 'op_banc',
                        'Concepte': tr_concepte,
                        'Descripcio': f"[{cartera_val}] {tr_comentari}".strip(),
                        'litres': 0.0,
                        'Revisat': True
                    }
                    row_trcartera = {
                        'Data': data_val.strftime('%Y-%m-%d'),
                        'mes': mes_val,
                        'any': any_val,
                        'Banc': 'TR Cartera',
                        'FormaPago': 'Compte',
                        'Import càrrec': import_ing,
                        'import ingrés': import_carg,
                        'grup': 'op_banc',
                        'Idcategoria': 'op_banc',
                        'Concepte': tr_concepte,
                        'Descripcio': f"[{cartera_val}] {tr_comentari}".strip(),
                        'litres': 0.0,
                        'Revisat': True
                    }
                    supabase.table("despeses").insert([row_traderep, row_trcartera]).execute()
                    
                    st.success("Moviment TR Cartera desat correctament!")
                    clear_form_state("tr_")
                    st.rerun()

    elif data_type == "Previsió de Pagament":
        # Row 1 (4 columns)
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
        with r1_col1:
            banc = st.selectbox("Banc", get_config_banks(), key="pag_banc")
        with r1_col2:
            forma_pago = st.selectbox("Forma de Pagament", get_config_payment_methods(), key="pag_forma_pago")
        with r1_col3:
            data_val = st.date_input("Data Previsió", value=datetime.today(), format="DD/MM/YYYY", key="pag_data")
            mes_val = month_translations[CATALAN_MONTHS[data_val.month - 1]]
            any_val = data_val.year
        with r1_col4:
            import_carg = st.number_input("Import (€)", min_value=0.0, step=0.01, key="pag_import")
            
        # Row 2 (5 columns to fit repeating settings)
        r2_col1, r2_col2, r2_col3, r2_col4, r2_col5 = st.columns([2.5, 2.5, 2.0, 2.5, 2.5])
        with r2_col1:
            cat_val = st.selectbox("Categoria", get_config_categories(), key="pag_cat")
        with r2_col2:
            concept_options = get_config_concepts(cat_val)
            concept_val = st.selectbox("Concepte", concept_options, key="pag_concepte")
        with r2_col3:
            pagat_val = st.selectbox("Estat", ["pendent", "pagat"], key="pag_estat")
        with r2_col4:
            repetir = st.checkbox("Repetir mensualment?", value=False, help="Crearà o actualitzarà l'import d'aquest concepte per a tots els mesos restants fins a l'any indicat.", key="pag_repetir")
        with r2_col5:
            repetir_any_limit = st.selectbox("Fins a desembre de l'any:", [any_val, any_val + 1, any_val + 2], index=0, key="rep_any_pag")
        
        col_btns = st.columns([3.5, 2.0, 6.5])
        with col_btns[0]:
            submitted = st.button("Desa la Previsió de Pagament")
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key="cancel_pag")
        if cancelled:
            clear_form_state("pag_")
            clear_form_state("rep_any_pag")
            st.rerun()
        if submitted:
            if repetir:
                current_max_id = int(df_pag['idPago'].max() + 1) if not df_pag.empty else 1
                updated_count = 0
                added_count = 0
                for yr in range(any_val, repetir_any_limit + 1):
                    start_month = data_val.month if yr == any_val else 1
                    for m_idx in range(start_month, 13):
                        m_cat = CATALAN_MONTHS[m_idx - 1]
                        m_data = month_translations[m_cat]
                        
                        mask = (df_pag['any'] == yr) & (df_pag['mes'].str.lower() == m_data) & (df_pag['Concepte'].str.lower() == concept_val.lower())
                        if mask.any():
                            df_pag.loc[mask, 'Import'] = import_carg
                            df_pag.loc[mask, 'Banc'] = banc
                            df_pag.loc[mask, 'Formapago'] = forma_pago
                            df_pag.loc[mask, 'Categoria'] = cat_val
                            df_pag.loc[mask, 'pagat'] = pagat_val
                            updated_count += 1
                        else:
                            new_row = {
                                'idPago': current_max_id,
                                'Banc': banc,
                                'Formapago': forma_pago,
                                'Data': f"{data_val.day:02d}/{m_idx:02d}/{yr}",
                                'dia': data_val.day,
                                'mes': m_data,
                                'any': yr,
                                'Categoria': cat_val,
                                'Concepte': concept_val,
                                'Import': import_carg,
                                'pagat': pagat_val
                            }
                            df_pag = pd.concat([df_pag, pd.DataFrame([new_row])], ignore_index=True)
                            current_max_id += 1
                            added_count += 1
                save_to_csv(df_pag.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'pagaments.csv')
                st.success(f"Previsions desades: {added_count} creades de nou i {updated_count} actualitzades fins a desembre del {repetir_any_limit}!")
            else:
                new_row = {
                    'idPago': int(df_pag['idPago'].max() + 1) if not df_pag.empty else 1,
                    'Banc': banc,
                    'Formapago': forma_pago,
                    'Data': data_val.strftime('%d/%m/%Y'),
                    'dia': data_val.day,
                    'mes': mes_val,
                    'any': any_val,
                    'Categoria': cat_val,
                    'Concepte': concept_val,
                    'Import': import_carg,
                    'pagat': pagat_val
                }
                df_pag = pd.concat([df_pag, pd.DataFrame([new_row])], ignore_index=True)
                save_to_csv(df_pag.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'pagaments.csv')
                st.success("Previsió de pagament desada correctament!")
            clear_form_state("pag_")
            clear_form_state("rep_any_pag")
            st.rerun()
            
    elif data_type == "Previsió d'Ingrés":
        # Row 1 (4 columns)
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
        with r1_col1:
            banc = st.selectbox("Banc", get_config_banks(), key="ing_banc")
        with r1_col2:
            data_val = st.date_input("Data Previsió", value=datetime.today(), format="DD/MM/YYYY", key="ing_data")
            mes_val = month_translations[CATALAN_MONTHS[data_val.month - 1]]
            any_val = data_val.year
        with r1_col3:
            import_ing = st.number_input("Import Ingrés (€)", min_value=0.0, step=0.01, key="ing_import")
        with r1_col4:
            cat_val = st.selectbox("Categoria", ["ingrés_general", "ingrés_extra"], key="ing_cat")
            
        # Row 2 (4 columns)
        r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
        with r2_col1:
            concept_options = get_config_concepts(cat_val)
            concept_val = st.selectbox("Concepte", concept_options, key="ing_concepte")
        with r2_col2:
            cobrat_val = st.selectbox("Estat", ["cobrat", "pendent"], key="ing_cobrat")
        with r2_col3:
            repetir = st.checkbox("Repetir mensualment?", value=False, help="Crearà o actualitzarà l'import d'aquest concepte per a tots els mesos restants fins a l'any indicat.", key="ing_repetir")
        with r2_col4:
            repetir_any_limit = st.selectbox("Fins a desembre de l'any:", [any_val, any_val + 1, any_val + 2], index=0, key="rep_any_ing")
        
        col_btns = st.columns([3.5, 2.0, 6.5])
        with col_btns[0]:
            submitted = st.button("Desa la Previsió d'Ingrés")
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key="cancel_ing")
        if cancelled:
            clear_form_state("ing_")
            clear_form_state("rep_any_ing")
            st.rerun()
        if submitted:
            if repetir:
                current_max_id = int(df_ing['idIngres'].max() + 1) if not df_ing.empty else 1
                updated_count = 0
                added_count = 0
                for yr in range(any_val, repetir_any_limit + 1):
                    start_month = data_val.month if yr == any_val else 1
                    for m_idx in range(start_month, 13):
                        m_cat = CATALAN_MONTHS[m_idx - 1]
                        m_data = month_translations[m_cat]
                        
                        mask = (df_ing['any'] == yr) & (df_ing['mes'].str.lower() == m_data) & (df_ing['Concepte'].str.lower() == concept_val.lower())
                        if mask.any():
                            df_ing.loc[mask, 'Import'] = import_ing
                            df_ing.loc[mask, 'Banc'] = banc
                            df_ing.loc[mask, 'Categoria'] = cat_val
                            df_ing.loc[mask, 'cobrat'] = cobrat_val
                            updated_count += 1
                        else:
                            new_row = {
                                'idIngres': current_max_id,
                                'Banc': banc,
                                'Data': f"{data_val.day:02d}/{m_idx:02d}/{yr}",
                                'dia': data_val.day,
                                'mes': m_data,
                                'any': yr,
                                'Categoria': cat_val,
                                'Concepte': concept_val,
                                'Import': import_ing,
                                'comentari': '',
                                'cobrat': cobrat_val
                            }
                            df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                            current_max_id += 1
                            added_count += 1
                save_to_csv(df_ing.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'ingressos.csv')
                st.success(f"Previsions d'ingrés desades: {added_count} creades de nou i {updated_count} actualitzades fins a desembre del {repetir_any_limit}!")
            else:
                new_row = {
                    'idIngres': int(df_ing['idIngres'].max() + 1) if not df_ing.empty else 1,
                    'Banc': banc,
                    'Data': data_val.strftime('%d/%m/%Y'),
                    'dia': data_val.day,
                    'mes': mes_val,
                    'any': any_val,
                    'Categoria': cat_val,
                    'Concepte': concept_val,
                    'Import': import_ing,
                    'comentari': '',
                    'cobrat': cobrat_val
                }
                df_ing = pd.concat([df_ing, pd.DataFrame([new_row])], ignore_index=True)
                save_to_csv(df_ing.drop(columns=['parsed_date', 'clean_mes'], errors='ignore'), 'ingressos.csv')
                st.success("Previsió d'ingrés desada correctament!")
            clear_form_state("ing_")
            clear_form_state("rep_any_ing")
            st.rerun()
            default_super_idx = supers_list.index(pending_super) if pending_super in supers_list else 0
            try:
                default_data = datetime.strptime(pending_data, '%d/%m/%Y').date()
            except:
                default_data = datetime.today()
        else:
            default_super_idx = 0
            default_data = datetime.today()

        # Row 1 (5 columns)
        r1_col1, r1_col2, r1_col3, r1_col4, r1_col5 = st.columns(5)
        with r1_col1:
            super_val = st.selectbox("Supermercat", get_config_supers(), index=default_super_idx, key="super_super")
        with r1_col2:
            data_val = st.date_input("Data", value=default_data, format="DD/MM/YYYY", key="super_data")
            mes_val = month_translations[CATALAN_MONTHS[data_val.month - 1]]
            any_val = data_val.year
        with r1_col3:
            fam_val = st.selectbox("Família", get_config_families(), key="super_familia")
        with r1_col4:
            article_options = get_config_articles(fam_val)
            art_val = st.selectbox("Article", article_options, key="super_article")
        with r1_col5:
            pes_val = st.number_input("Pes (grams/units)", min_value=0.0, step=1.0, key="super_pes")
            
        # Row 2 (4 columns)
        r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
        with r2_col1:
            qty_val = st.number_input("Quantitat", min_value=1.0, value=1.0, step=1.0, key="super_quantitat")
        with r2_col2:
            preu_unit = st.number_input("Preu Unitari (€)", min_value=0.0, step=0.01, key="super_preu")
        with r2_col3:
            prom_val = st.checkbox("Promoció / Descompte?", key="super_prom")
        with r2_col4:
            rebost_val = st.checkbox("Rebost / Celler?", key="super_rebost")
            
        col_btns = st.columns([2.5, 2.0, 7.5])
        with col_btns[0]:
            submitted = st.button("Desa la Compra")
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key="cancel_super")
            
        if cancelled:
            clear_form_state("super_")
            st.rerun()
        if submitted:
            tot_linea = preu_unit * qty_val
            new_row = {
                'IdCompra': int(df_super['IdCompra'].max() + 1) if not df_super.empty else 1,
                'data': data_val.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'super': super_val,
                'familia': fam_val,
                'article': art_val,
                'pes': int(pes_val),
                'quantitat': int(qty_val),
                'preuUnit': preu_unit,
                'prom': 1 if prom_val else 0,
                'totLinea': tot_linea,
                'IdDespesa': 0,
                'descompte': 0.0,
                'rebost': 'rebost' if rebost_val else None
            }
            df_super = pd.concat([df_super, pd.DataFrame([new_row])], ignore_index=True)
            save_to_csv(df_super.drop(columns=['parsed_date'], errors='ignore'), 'compresSuper.csv')
            
            # Update stock for the recognized product
            try:
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                if supabase and art_val and art_val.lower() not in ['pendent', 'varis']:
                    res = supabase.table('tb_productes').select('idProducte, stock_actual, select_stock').eq('nom_estandard', art_val).execute()
                    if res.data:
                        if res.data[0].get('select_stock', False) == True:
                            prod_id = res.data[0]['idProducte']
                            current_stock = res.data[0].get('stock_actual', 0)
                            if current_stock is None: current_stock = 0
                            new_stock = current_stock + float(qty_val)
                            supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', prod_id).execute()
                            st.success(f"📦 Stock actualitzat automàticament: {art_val} (+{int(qty_val)} unitats)")
            except Exception as e:
                print(f"Error updating stock manually: {e}")
            
            st.success("Compra de súper desada correctament!")
            clear_form_state("super_")
            st.rerun()
            
    elif data_type == "Km Cotxe":
        km_version = st.session_state.get("km_version", 0)
        cotxe_val = "tívoli"
        
        # Row 1 (3 columns)
        r1_col1, r1_col2, r1_col3 = st.columns([2, 4, 4])
        with r1_col1:
            data_val = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key=f"km_data_{km_version}")
        with r1_col2:
            # Find the last odometer reading for the selected car
            last_km = 0.0
            df_km_car = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km
            if not df_km_car.empty:
                last_km = float(df_km_car.dropna(subset=['contador'])['contador'].iloc[0])
                
            contador_val = st.number_input("Lectura Odometer", min_value=0.0, value=None, placeholder=f"Última: {last_km:g}", step=1.0, key=f"km_odo_{km_version}")
        with r1_col3:
            km_val = max(0.0, contador_val - last_km) if contador_val is not None else 0.0
            st.text_input("Kilòmetres recorreguts", value=f"{km_val:g}", disabled=True)
            
        # Row 2 (2 columns)
        ruta_opts = get_config_routes(df_km)
        if "Nova ruta..." not in ruta_opts:
            ruta_opts.insert(0, "Nova ruta...")
            
        ruta_sel_key = f"km_ruta_sel_{km_version}"
        current_sel = st.session_state.get(ruta_sel_key, "Nova ruta...")
        
        r2_col1, r2_col2 = st.columns(2)
        with r2_col1:
            ruta_sel = st.selectbox("Ruta / Destinació", ruta_opts, key=ruta_sel_key)
        
        if current_sel == "Nova ruta...":
            with r2_col2:
                ruta_val = st.text_input("Escriu la nova ruta:", key=f"km_ruta_{km_version}")
                save_ruta_template = st.checkbox("💾 Guardar com a plantilla", value=True, key=f"km_save_ruta_{km_version}")
        else:
            with r2_col2:
                st.write("") # Just filler
            ruta_val = ruta_sel
            
        col_btns = st.columns([2.5, 2.0, 7.5])
        with col_btns[0]:
            submitted = st.button("Desa els Kilòmetres", type="primary")
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key=f"cancel_km_{km_version}")
        if cancelled:
            clear_form_state("km_")
            st.rerun()
        if submitted:
            if contador_val is None or contador_val <= 0:
                st.error("⚠️ Heu d'introduir la lectura de l'odòmetre vàlida.")
            elif not ruta_val.strip():
                st.error("⚠️ Heu d'introduir una ruta.")
            else:
                new_row = {
                    'idRuta': int(df_km['idRuta'].max() + 1) if not df_km.empty else 1,
                    'cotxe': cotxe_val,
                    'data': data_val.strftime('%d/%m/%Y'),
                    'ruta': ruta_val,
                    'contador': int(contador_val),
                    'km': int(km_val)
                }
                append_to_db(pd.DataFrame([new_row]), 'kmCotxe', 'df_km')
                if current_sel == "Nova ruta...":
                    if st.session_state.get(f"km_save_ruta_{km_version}", True):
                        add_route_to_config(ruta_val, df_km)
                    else:
                        init_routes_config(df_km)
                st.success("Ruta desada correctament!")
                st.session_state["km_ruta_sel"] = "Nova ruta..."
                st.session_state["km_ruta"] = ""
                clear_form_state("km_")
                st.rerun()
            
    if data_type == "Km Cotxe":
        st.markdown("<h5 style='color:#f39c12; margin-top: 20px; margin-bottom: 5px;'>📋 Últimes rutes registrades</h5>", unsafe_allow_html=True)
        if not df_km.empty:
            df_km_show = df_km.head(5)[['data', 'cotxe', 'ruta', 'km', 'contador']].copy()
            df_km_show.rename(columns={'data': 'Data', 'cotxe': 'Cotxe', 'ruta': 'Ruta', 'km': 'Km recorreguts', 'contador': 'Odòmetre'}, inplace=True)
            st.table(df_km_show.set_index('Data'))
    else:
        st.markdown("<h5 style='color:#f39c12; margin-top: 20px; margin-bottom: 5px;'>📋 Últims moviments</h5>", unsafe_allow_html=True)
        
        last_movs = []
        for bank_key in get_config_banks():
            df_b = df_desp[df_desp['Banc'] == bank_key]
            if not df_b.empty:
                last_row = df_b.iloc[0]
                is_charge = float(last_row['Import càrrec']) > 0
                val = last_row['Import càrrec'] if is_charge else last_row['import ingrés']
                lbl = "Càrrec" if is_charge else "Ingrés"
                
                last_movs.append({
                    'Banc': BANK_MAPPING.get(bank_key, bank_key),
                    'Data': last_row['Data'],
                    'Categoria': last_row['Idcategoria'],
                    'Concepte': last_row['Idconcepte'],
                    'Tipus': lbl,
                    'Import': val,
                    '_Tipus_raw': lbl  # hidden helper for styling
                })
                
        if last_movs:
            df_last = pd.DataFrame(last_movs)
            
            # Style callback to highlight charges in red, inflows in green
            def style_last_mov_cells(val):
                if isinstance(val, float):
                    return ""
                return ""
                
            def style_rows(df):
                style_df = pd.DataFrame("", index=df.index, columns=df.columns)
                for idx, row in df.iterrows():
                    color = "#ef4444" if df_last.loc[idx, '_Tipus_raw'] == "Càrrec" else "#22c55e"
                    style_df.at[idx, 'Import'] = f"color: {color}; font-weight: bold;"
                    style_df.at[idx, 'Tipus'] = f"color: {color}; font-weight: bold;"
                return style_df
                
            # Display as a compact, styled static table
            st.table(
                df_last.drop(columns=['_Tipus_raw'])
                .style.format({'Import': '{:,.2f} €'})
                .apply(style_rows, axis=None)
                .set_properties(**{'font-size': '11px', 'padding': '3px'})
            )
# ----------------- DIALOGS FOR MODIFY / DELETE -----------------
@st.dialog("✏️ Modificar Registre")
def show_modify_dialog(table_name, id_col, id_val, current_row_data, db_select, df_to_show, row_idx):
    st.markdown(f"Modificant el registre seleccionat de la taula **{db_select}**.")
    with st.form(key=f"dialog_edit_form_{db_select}_{row_idx}"):
        new_values = {}
        form_cols = st.columns(2)
        editable_cols = [c for c in df_to_show.columns if c not in ['ID_mov', 'idPago', 'idIngres', 'IdCompra', 'idGasolina', 'idRuta', 'mes_lower', 'parsed_date', 'clean_mes', 'date_score']]
        
        for col_num, col_name in enumerate(editable_cols):
            col_idx = col_num % 2
            val = current_row_data[col_name]
            
            with form_cols[col_idx]:
                if isinstance(val, (int, np.integer)):
                    new_values[col_name] = st.number_input(f"{col_name}", value=int(val), step=1)
                elif isinstance(val, (float, np.floating)):
                    new_values[col_name] = st.number_input(f"{col_name}", value=float(val), step=0.01)
                elif col_name == 'cobrat' and db_select == "Previsió d'Ingressos":
                    new_values[col_name] = st.selectbox(f"{col_name}", ["pendent", "cobrat"], index=1 if str(val).lower() == "cobrat" else 0)
                elif col_name == 'pagat' and db_select == "Previsió de Pagaments":
                    new_values[col_name] = st.selectbox(f"{col_name}", ["pendent", "pagat"], index=1 if str(val).lower() == "pagat" else 0)
                elif isinstance(val, bool):
                    new_values[col_name] = st.checkbox(f"{col_name}", value=val)
                else:
                    new_values[col_name] = st.text_input(f"{col_name}", value=str(val) if not pd.isna(val) else "")
                    
        st.write("")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submit = st.form_submit_button("💾 Desa els canvis", use_container_width=True)
        with col_btn2:
            cancel = st.form_submit_button("Cancel·la", use_container_width=True)
            
        if cancel:
            st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
            st.rerun()
            
        if submit:
            typed_values = {}
            for k, v in new_values.items():
                orig_val = current_row_data[k]
                if pd.isna(orig_val):
                    typed_values[k] = v
                elif isinstance(orig_val, (int, np.integer)):
                    typed_values[k] = int(v) if v != "" else None
                elif isinstance(orig_val, (float, np.floating)):
                    typed_values[k] = float(v) if v != "" else None
                elif isinstance(orig_val, bool):
                    typed_values[k] = bool(v)
                else:
                    typed_values[k] = str(v)
            
            if id_col:
                if update_db_row(table_name, id_col, id_val, typed_values):
                    st.success("Registre modificat correctament!")
                    st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
                    st.rerun()
            else:
                tbl_filename = {
                    "Pagament Hipoteca": "hipoteca.csv",
                    "Estalvis DP": "estalviDP.csv"
                }.get(db_select)
                if tbl_filename:
                    for k, v in typed_values.items():
                        df_to_show.at[row_idx, k] = v
                    save_to_csv(df_to_show, tbl_filename)
                    st.success("Registre modificat correctament!")
                    st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
                    st.rerun()

@st.dialog("❌ Confirmar Eliminació")
def show_delete_dialog(table_name, id_col, id_val, current_row_data, db_select, df_to_show, row_idx):
    st.warning("⚠️ **Atenció:** Aquesta acció no es pot desfer. El registre s'esborrarà definitivament.")
    
    st.markdown("**Detalls del registre a eliminar:**")
    details_html = "<div style='background-color:#1e293b; padding:15px; border-radius:8px; margin-bottom:15px; border:1px solid #475569; color:#f8fafc; font-size:0.95rem;'>"
    for col, val in current_row_data.items():
        if col not in ['ID_mov', 'idPago', 'idIngres', 'IdCompra', 'idGasolina', 'idRuta', 'mes_lower', 'parsed_date', 'clean_mes', 'date_score'] and not pd.isna(val):
            details_html += f"<div style='margin-bottom:6px; border-bottom:1px solid #334155; padding-bottom:4px;'><span style='color:#94a3b8; font-weight:600;'>{col}:</span> <span style='font-weight:700; color:#f8fafc;'>{val}</span></div>"
    details_html += "</div>"
    st.markdown(details_html, unsafe_allow_html=True)
    
    col_del1, col_del2 = st.columns(2)
    with col_del1:
        if st.button("❌ Sí, esborra definitivament", type="primary", use_container_width=True):
            if id_col:
                if delete_db_row(table_name, id_col, id_val):
                    st.success("Registre esborrat correctament!")
                    st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
                    st.rerun()
            else:
                tbl_filename = {
                    "Pagament Hipoteca": "hipoteca.csv",
                    "Estalvis DP": "estalviDP.csv"
                }.get(db_select)
                if tbl_filename:
                    df_updated = df_to_show.drop(row_idx)
                    save_to_csv(df_updated, tbl_filename)
                    st.success("Registre esborrat correctament!")
                    st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
                    st.rerun()
    with col_del2:
        if st.button("Cancel·la", use_container_width=True):
            st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
            st.rerun()


# ================= TAB LLISTA DE LA COMPRA =================
if tab_compra:
    with tab_compra:
        st.markdown("## 🛒 Llista de la Compra")
        st.write("Aquesta llista mostra els productes del teu rebost on l'stock actual està per sota de l'stock mínim.")
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_prods = fetch_all_supabase(supabase, 'tb_productes')
            
            if not df_prods.empty:
                # Ensure select_stock exists
                if 'select_stock' not in df_prods.columns:
                    df_prods['select_stock'] = False
                
                # Filter ONLY items that are in the pantry (select_stock == True)
                df_prods_filtered = df_prods[df_prods['select_stock'] == True].copy()
                
                for col in ['stock_actual', 'stock_minim']:
                    if col not in df_prods_filtered.columns:
                        df_prods_filtered[col] = 0.0
                if 'super_habitual' not in df_prods_filtered.columns:
                    df_prods_filtered['super_habitual'] = None
                    
                df_shopping = df_prods_filtered[df_prods_filtered['stock_actual'] < df_prods_filtered['stock_minim']].copy()
                
                if not df_shopping.empty:
                    df_shopping['falta'] = df_shopping['stock_minim'] - df_shopping['stock_actual']
                    # Fill missing supermarket
                    df_shopping['super_habitual'] = df_shopping['super_habitual'].fillna("Sense Assignar").replace("", "Sense Assignar")
                    
                    # Sort by supermarket name
                    df_shopping = df_shopping.sort_values(by='super_habitual')
                    
                    # Group by super_habitual
                    for superm, group in df_shopping.groupby('super_habitual'):
                        # Use expander for each supermarket
                        with st.expander(f"🏪 {superm} ({len(group)} productes)", expanded=True):
                            for _, row in group.iterrows():
                                unit_str = row['unitat'] if 'unitat' in row and pd.notna(row['unitat']) and str(row['unitat']).lower() != 'none' else 'u.'
                                st.checkbox(f"**{row['nom_estandard']}**: falta **{int(row['falta'])}** {unit_str}", key=f"chk_shop_{row['idProducte']}")
                else:
                    st.success("Ho tens tot! El teu stock està per sobre del mínim a tot arreu.")
            else:
                st.info("No hi ha productes a la base de dades.")
                
        except Exception as e:
            st.error(f"⚠️ Error carregant la llista de la compra: {str(e)}")

# ================= TAB REBOST / STOCK =================
if tab_rebost:
    with tab_rebost:
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_prods = fetch_all_supabase(supabase, 'tb_productes')
            
            st.markdown("<h2 style='color:#3498db;'>📦 Control d'Stock (El teu Rebost)</h2>", unsafe_allow_html=True)
            if not df_prods.empty:
                # ================= REGISTRE DE BAIXES =================
                st.markdown("### 🍽️ Registrar Baixa d'Stock")
                st.write("Has gastat un producte? Registra-ho aquí perquè l'stock baixi de forma segura.")
                
                # Filter only products that have select_stock == True and stock_actual > 0
                # Wait, df_prods might not have stock_actual as float yet, let's fillna first
                for col in ['stock_actual', 'stock_minim']:
                    if col not in df_prods.columns:
                        df_prods[col] = 0.0
                    else:
                        df_prods[col] = pd.to_numeric(df_prods[col], errors='coerce').fillna(0.0)
                        
                if 'select_stock' not in df_prods.columns:
                    df_prods['select_stock'] = False
                
                df_available = df_prods[(df_prods['select_stock'] == True) & (df_prods['stock_actual'] > 0)].copy()
                
                if not df_available.empty:
                    families = sorted([str(f) for f in df_available['familia'].dropna().unique() if str(f).strip() != ""])
                    if not families:
                        families = ["Sense Família"]
                        
                    if 'selected_family_consum' not in st.session_state:
                        st.session_state['selected_family_consum'] = families[0] if families else None
                    elif st.session_state['selected_family_consum'] not in families:
                        st.session_state['selected_family_consum'] = families[0] if families else None
                        
                    # Create horizontal radio for families
                    st.radio(
                        "1️⃣ Tria la família:", 
                        families, 
                        horizontal=True,
                        key='selected_family_consum'
                    )
                    
                    # Generate 6 columns grid for smaller buttons (TPV style)
                    cols_per_row = 6
                    
                    # Inject CSS to make mobile grid 3 columns
                    st.components.v1.html("""
                    <script>
                        const parentDoc = window.parent.document;
                        const spans = parentDoc.querySelectorAll('strong');
                        spans.forEach(span => {
                            if(span.innerText.includes('Què has gastat?')) {
                                const verticalBlock = span.closest('div[data-testid="stVerticalBlock"]');
                                if(verticalBlock) {
                                    verticalBlock.classList.add('stock-grid-container');
                                }
                            }
                        });
                        
                        if (!parentDoc.getElementById('stock-grid-style')) {
                            const style = parentDoc.createElement('style');
                            style.id = 'stock-grid-style';
                            style.innerHTML = `
                                @media (max-width: 576px) {
                                    .stock-grid-container div[data-testid="stHorizontalBlock"] {
                                        flex-wrap: wrap !important;
                                    }
                                    .stock-grid-container div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                                        min-width: calc(33.33% - 1rem) !important;
                                        flex: 1 1 calc(33.33% - 1rem) !important;
                                    }
                                }
                            `;
                            parentDoc.head.appendChild(style);
                        }
                    </script>
                    """, height=0)
                    
                    sel_fam = st.session_state['selected_family_consum']
                    if sel_fam:
                        # Handle the "Sense Família" case
                        if sel_fam == "Sense Família":
                            df_fam = df_available[df_available['familia'].isna() | (df_available['familia'] == "")].sort_values('nom_estandard')
                        else:
                            df_fam = df_available[df_available['familia'] == sel_fam].sort_values('nom_estandard')
                            
                        st.markdown(f"**2️⃣ Què has gastat? (Toca per restar-ne 1)**")
                        
                        for i in range(0, len(df_fam), cols_per_row):
                            cols = st.columns(cols_per_row)
                            chunk = df_fam.iloc[i:i+cols_per_row]
                            for j, (_, row) in enumerate(chunk.iterrows()):
                                prod_name = row['nom_estandard']
                                stock = int(row['stock_actual']) # Convert to int
                                
                                with cols[j]:
                                    # Use HTML to enforce a fixed height for all images/placeholders
                                    # This guarantees all buttons align perfectly at the bottom
                                    if 'foto_url' in row and pd.notna(row['foto_url']) and str(row['foto_url']).strip() != "":
                                        foto_src = str(row['foto_url']).strip()
                                        
                                        # Handle local files by converting to base64 for HTML img tag
                                        import base64
                                        import os
                                        
                                        img_src = foto_src
                                        if not foto_src.startswith("http"):
                                            # It's a local file
                                            if os.path.exists(foto_src):
                                                with open(foto_src, "rb") as f:
                                                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                                                    ext = foto_src.split('.')[-1].lower()
                                                    mime = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                                                    img_src = f"data:{mime};base64,{b64_data}"
                                            else:
                                                img_src = "" # File not found
                                                
                                        if img_src:
                                            st.markdown(f'''
                                                <div style="height: 80px; display: flex; justify-content: center; align-items: center; margin-bottom: 5px;">
                                                    <img src="{img_src}" style="max-height: 100%; max-width: 100%; border-radius: 8px; object-fit: contain; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                                                </div>
                                            ''', unsafe_allow_html=True)
                                        else:
                                            # File was local but not found, show placeholder
                                            st.markdown('''
                                                <div style="height: 80px; display: flex; justify-content: center; align-items: center; margin-bottom: 5px; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #dee2e6;">
                                                    <span style="font-size: 2rem; color: #ced4da;">📦</span>
                                                </div>
                                            ''', unsafe_allow_html=True)
                                    else:
                                        # Placeholder for items without image to maintain alignment
                                        st.markdown('''
                                            <div style="height: 80px; display: flex; justify-content: center; align-items: center; margin-bottom: 5px; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #dee2e6;">
                                                <span style="font-size: 2rem; color: #ced4da;">📦</span>
                                            </div>
                                        ''', unsafe_allow_html=True)
                                            
                                    btn_label = f"{prod_name}\n📦 {stock}"
                                    
                                    if st.button(btn_label, key=f"btn_consum_{row['idProducte']}", use_container_width=True):
                                        new_stock = stock - 1.0
                                        supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', row['idProducte']).execute()
                                        st.success(f"➖ 1x {prod_name} gastat! (Et queden {int(new_stock)})")
                                        st.cache_data.clear() # Clear cache so other devices see it
                                        st.rerun()
                else:
                    st.info("Actualment no tens cap producte controlat amb stock disponible (> 0).")
                


                st.divider()
                st.markdown("### 📋 Taula d'Edició Ràpida")
                st.write("Edita les quantitats i el lloc on guardes cada article directament a la taula.")
                # We need to make sure cols exist in df
                for col in ['stock_actual', 'stock_minim']:
                    if col not in df_prods.columns:
                        df_prods[col] = 0.0
                if 'lloc' not in df_prods.columns:
                    df_prods['lloc'] = ""
                if 'super_habitual' not in df_prods.columns:
                    df_prods['super_habitual'] = None
                
                # Ensure select_stock exists
                if 'select_stock' not in df_prods.columns:
                    df_prods['select_stock'] = False
                    
                # Order by familia and nom
                df_prods = df_prods.sort_values(by=['familia', 'nom_estandard'])
                
                # Filter ONLY items that are in the pantry (select_stock == True)
                df_prods_filtered = df_prods[df_prods['select_stock'] == True].copy()
                
                with st.form("form_edicio_rapida_stock"):
                    edited_df = st.data_editor(
                        df_prods_filtered[['idProducte', 'select_stock', 'nom_estandard', 'familia', 'super_habitual', 'stock_actual', 'stock_minim', 'lloc']],
                        column_config={
                            "idProducte": None,
                            "select_stock": st.column_config.CheckboxColumn("En Rebost?", default=True),
                            "nom_estandard": st.column_config.TextColumn("Producte", disabled=True),
                            "familia": st.column_config.TextColumn("Família", disabled=True),
                            "super_habitual": st.column_config.SelectboxColumn("Súper Habitual", options=get_config_supers() + ["Sense Assignar"], required=False),
                            "stock_actual": st.column_config.NumberColumn("Stock Actual", min_value=0.0, step=1.0),
                            "stock_minim": st.column_config.NumberColumn("Stock Mínim", min_value=0.0, step=1.0),
                            "lloc": st.column_config.SelectboxColumn("Lloc", options=["Rebost", "Sota-pica", "Escala", "Nevera", "Congelador", "Bany", "Altres"], required=False)
                        },
                        hide_index=True,
                        use_container_width=True,
                        key="editor_stock"
                    )
                    
                    submitted = st.form_submit_button("Guardar Estat del Stock", type="primary")
                
                if submitted:
                    # We need to find changed rows and update supabase
                    updates_made = 0
                    for i, row in edited_df.iterrows():
                        orig_row = df_prods_filtered.loc[i]
                        if (row['stock_actual'] != orig_row['stock_actual'] or 
                            row['stock_minim'] != orig_row['stock_minim'] or 
                            row['lloc'] != orig_row['lloc'] or
                            row['super_habitual'] != orig_row['super_habitual'] or
                            row['select_stock'] != orig_row['select_stock']):
                            
                            def s_float(v):
                                try:
                                    val = float(v)
                                    import math
                                    return 0.0 if math.isnan(val) else val
                                except:
                                    return 0.0
                                    
                            supabase.table('tb_productes').update({
                                'select_stock': bool(row['select_stock']),
                                'stock_actual': s_float(row['stock_actual']),
                                'stock_minim': s_float(row['stock_minim']),
                                'lloc': str(row['lloc']) if pd.notna(row['lloc']) and str(row['lloc']).strip().lower() != "none" else None,
                                'super_habitual': str(row['super_habitual']) if pd.notna(row['super_habitual']) and str(row['super_habitual']).strip().lower() != "none" else None
                            }).eq('idProducte', row['idProducte']).execute()
                            updates_made += 1
                            
                    if updates_made > 0:
                        st.success(f"S'han actualitzat {updates_made} productes!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.info("No s'ha detectat cap canvi.")
                        
        except Exception as e:
            st.error(f"Error carregant dades del rebost: {e}")

# ================= TAB 4: BASES DE DADES (Supabase) =================
with tab_db:
    st.write("")
    col_sel, col_search, col_size = st.columns([3, 5, 2], vertical_alignment="bottom")
    with col_sel:
        db_select = st.selectbox("Taula", [
            "Despeses (General)", "Previsió de Pagaments", "Previsió d'Ingressos", "Compres Supermercat", "Gasolina", "Kilòmetres Cotxe", "Pagament Hipoteca", "Estalvis DP", "TR Cartera", "Stock Rebost"
        ], key="db_select_box")
    with col_search:
        search_query = st.text_input("🔍 Cerca global", value="", key=f"search_{db_select}")
    with col_size:
        page_size = st.selectbox("Registres/pàgina", [20, 50, 100, 200, 500, 1000], index=2, key=f"size_{db_select}")
        
    st.write("")
    col_title, col_check = st.columns([7, 3], vertical_alignment="bottom")
    with col_title:
        st.markdown(f"<h3 style='margin:0; color:#f39c12; text-transform:uppercase;'>🗃️ {db_select}</h3>", unsafe_allow_html=True)
    with col_check:
        show_all_prev = False
        if db_select in ["Previsió de Pagaments", "Previsió d'Ingressos"]:
            sort_desc = False
            show_all_prev = st.checkbox("Veure tots els registres", value=False, key=f"show_all_{db_select}")
        else:
            sort_desc = st.checkbox("Veure primer els més recents", value=True, key=f"sort_{db_select}")
        
    st.write("")
    
    # 1. Select the base dataframe
    if db_select == "Despeses (General)":
        df_to_show = df_desp.drop(columns=['parsed_date', 'clean_mes', 'date_score', 'mes_lower'], errors='ignore')
    elif db_select == "Previsió de Pagaments":
        df_to_show = df_pag.sort_values(by='parsed_date', ascending=False).drop(columns=['parsed_date', 'clean_mes'], errors='ignore')
        if not show_all_prev:
            mask_pendent = df_to_show['pagat'].astype(str).str.lower() != 'pagat'
            mask_mes_actual = (df_to_show['any'] == selected_year) & (df_to_show['mes'].astype(str).str.lower() == selected_month_data.lower())
            df_to_show = df_to_show[mask_pendent | mask_mes_actual]
        
        # Reordenar per assegurar que l'estat es veu clarament
        cols = list(df_to_show.columns)
        if 'pagat' in cols and 'Import' in cols:
            cols.remove('pagat')
            cols.insert(cols.index('Import') + 1, 'pagat')
            df_to_show = df_to_show[cols]
            
    elif db_select == "Previsió d'Ingressos":
        df_to_show = df_ing.sort_values(by='parsed_date', ascending=False).drop(columns=['parsed_date', 'clean_mes'], errors='ignore')
        if not show_all_prev:
            mask_pendent = df_to_show['cobrat'].astype(str).str.lower() != 'cobrat'
            mask_mes_actual = (df_to_show['any'] == selected_year) & (df_to_show['mes'].astype(str).str.lower() == selected_month_data.lower())
            df_to_show = df_to_show[mask_pendent | mask_mes_actual]
        
        # Reordenar per assegurar que l'estat es veu clarament
        cols = list(df_to_show.columns)
        if 'cobrat' in cols and 'Import' in cols:
            cols.remove('cobrat')
            cols.insert(cols.index('Import') + 1, 'cobrat')
            df_to_show = df_to_show[cols]
    elif db_select == "Compres Supermercat":
        df_to_show = df_super.drop(columns=['parsed_date'], errors='ignore')
        
        # Reordenar per posar rebost en una posició visible (p. ex., just després d'article)
        cols = list(df_to_show.columns)
        if 'rebost' in cols and 'article' in cols:
            cols.remove('rebost')
            cols.insert(cols.index('article') + 1, 'rebost')
            df_to_show = df_to_show[cols]
    elif db_select == "Gasolina":
        df_to_show = df_gas.drop(columns=['parsed_date'], errors='ignore')
    elif db_select == "Kilòmetres Cotxe":
        df_to_show = df_km.drop(columns=['parsed_date'], errors='ignore')
    elif db_select == "Pagament Hipoteca":
        df_to_show = df_hip
    elif db_select == "TR Cartera":
        df_to_show = df_cartera.drop(columns=['parsed_date'], errors='ignore')
    elif db_select == "Estalvis DP":
        df_to_show = df_est
        
        # Reordenar les columnes per l'ordre clàssic de l'usuari i assegurar que id està al principi o final
        desired_order = ['id', 'mes', 'any', 'quota', 'aportació', 'rescat', 'pérdua', 'pagat']
        available_cols = [c for c in desired_order if c in df_to_show.columns]
        # Si hi ha altres columnes (no hauria), les posem al final
        other_cols = [c for c in df_to_show.columns if c not in desired_order]
        df_to_show = df_to_show[available_cols + other_cols]
        
    elif db_select == "Stock Rebost":
        df_to_show = fetch_all_supabase(supabase, 'tb_productes')
        if not df_to_show.empty:
            if 'select_stock' in df_to_show.columns:
                df_to_show['select_stock'] = df_to_show['select_stock'].fillna(False).astype(bool)
            if 'foto_url' in df_to_show.columns:
                df_to_show['foto_url'] = df_to_show['foto_url'].fillna("")
            for col in ['stock_actual', 'stock_minim']:
                if col in df_to_show.columns:
                    df_to_show[col] = pd.to_numeric(df_to_show[col], errors='coerce').fillna(0.0)
            df_to_show = df_to_show.sort_values(by='nom_estandard')
        
    df_filtered = df_to_show.copy()
    
    # 2. Column filters
        
    # Column filters
    with st.expander("⚙️ Filtres de columna", expanded=False):
        filterable_cols = []
        for col in df_to_show.columns:
            unique_vals = df_to_show[col].dropna().unique()
            if 1 < len(unique_vals) <= 30:
                filterable_cols.append((col, sorted(list(unique_vals))))
        
        if filterable_cols:
            cols_layout = st.columns(min(4, len(filterable_cols)))
            for idx, (col_name, vals) in enumerate(filterable_cols):
                col_idx = idx % len(cols_layout)
                with cols_layout[col_idx]:
                    selected_val = st.selectbox(f"Filtra per {col_name}", ["Tots"] + [str(v) for v in vals], key=f"filter_{db_select}_{col_name}")
                    if selected_val != "Tots":
                        df_filtered = df_filtered[df_filtered[col_name].astype(str) == selected_val]
                        
    if not sort_desc:
        df_filtered = df_filtered.iloc[::-1]
        
    # Text search
    if search_query:
        mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]
        
    # 3. Pagination logic
    filter_hash = f"{search_query}_{len(df_filtered)}_{sort_desc}"
    hash_key = f"hash_{db_select}"
    page_key = f"page_{db_select}"
    
    if hash_key not in st.session_state or st.session_state[hash_key] != filter_hash:
        st.session_state[hash_key] = filter_hash
        st.session_state[page_key] = 0
        
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
        
    total_rows = len(df_filtered)
    total_pages = max(1, int(np.ceil(total_rows / page_size)))
    st.session_state[page_key] = max(0, min(st.session_state[page_key], total_pages - 1))
    
    # Navigation buttons
    st.write("")
    col_nav_1, col_nav_2, col_nav_3, col_nav_4, col_nav_5 = st.columns([1.5, 1.5, 3, 1.5, 1.5])
    with col_nav_1:
        if st.button("⏮️ Primer", disabled=(st.session_state[page_key] == 0), key=f"first_{db_select}", use_container_width=True):
            st.session_state[page_key] = 0
            st.rerun()
    with col_nav_2:
        if st.button("◀️ Anterior", disabled=(st.session_state[page_key] == 0), key=f"prev_{db_select}", use_container_width=True):
            st.session_state[page_key] -= 1
            st.rerun()
    with col_nav_3:
        st.markdown(f"<div style='text-align: center; margin-top: -10px;'><span style='font-size: 1.3rem; color: #000000; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;'>{db_select}</span><br><span style='font-weight: 700; font-size: 1.15rem; color: #000000;'>Pàgina {st.session_state[page_key] + 1} de {total_pages}</span></div>", unsafe_allow_html=True)
    with col_nav_4:
        if st.button("Següent ▶️", disabled=(st.session_state[page_key] >= total_pages - 1), key=f"next_{db_select}", use_container_width=True):
            st.session_state[page_key] += 1
            st.rerun()
    with col_nav_5:
        if st.button("Últim ⏭️", disabled=(st.session_state[page_key] >= total_pages - 1), key=f"last_{db_select}", use_container_width=True):
            st.session_state[page_key] = total_pages - 1
            st.rerun()
            
    # Slicing
    start_idx = st.session_state[page_key] * page_size
    end_idx = min(start_idx + page_size, total_rows)
    df_page = df_filtered.iloc[start_idx:end_idx].copy()
    
    if total_rows > 0:
        st.markdown(f"Mostrant registres **{start_idx + 1}** a **{end_idx}** de **{total_rows}** filtrats (Total taula: **{len(df_to_show)}**)")
    else:
        st.markdown("No s'ha trobat cap registre amb els criteris seleccionats.")
        
    col_table, col_sidebar_actions = st.columns([10, 2])
    
    # Configurem dinàmicament l'amplada de les columnes per donar més espai als comentaris
    col_configs = {}
    for col in df_page.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ["comentari", "descrip", "motiu", "ruta", "observac", "detall"]):
            col_configs[col] = st.column_config.TextColumn(width=220)
        elif any(x in col_lower for x in ["id_", "idpago", "idingres", "idcompra", "idgasolina", "idruta"]):
            col_configs[col] = st.column_config.Column(width=45)
        elif any(x in col_lower for x in ["data", "fecha"]):
            col_configs[col] = st.column_config.Column(width=70)
        elif "any" in col_lower:
            col_configs[col] = st.column_config.Column(width=40)
        elif "mes" in col_lower:
            col_configs[col] = st.column_config.Column(width=45)
        elif "dia" in col_lower:
            col_configs[col] = st.column_config.Column(width=35)
        elif "forma" in col_lower:
            col_configs[col] = st.column_config.Column(width=70)
        elif any(x in col_lower for x in ["import", "quantitat", "preu", "valor", "totlinea", "pes", "prom", "descompte", "quota", "aportació", "rescat", "pérdua"]):
            col_configs[col] = st.column_config.Column(width=60)
        elif "grup" in col_lower:
            col_configs[col] = st.column_config.Column(width=60)
        elif "pendent" in col_lower:
            col_configs[col] = st.column_config.CheckboxColumn(width=65)
        elif any(x in col_lower for x in ["categoria", "super", "familia", "rebost"]):
            col_configs[col] = st.column_config.TextColumn(width=75)
        elif "concepte" in col_lower or "article" in col_lower:
            col_configs[col] = st.column_config.TextColumn(width=100)
        elif any(x in col_lower for x in ["banc", "compte"]):
            col_configs[col] = st.column_config.TextColumn(width=75)
            
    with col_table:
        # Interactive dataframe with row selection enabled
        dynamic_height = 38 + len(df_page) * 35.5
        
        if db_select == "Stock Rebost":
            # Add disabled ID column to config
            col_configs["idProducte"] = st.column_config.Column(disabled=True, width=45)
            
            with st.form("edit_stock_rebost_form"):
                edited_df = st.data_editor(
                    df_page, 
                    use_container_width=True,
                    height=int(dynamic_height),
                    column_config=col_configs,
                    hide_index=True,
                    key=f"df_select_{db_select}_{st.session_state[page_key]}_{st.session_state.get('df_key_counter', 0)}"
                )
                submitted = st.form_submit_button("💾 Guardar Canvis", type="primary")
            
            if submitted:
                updates = 0
                for i in range(len(df_page)):
                    orig_row = df_page.iloc[i]
                    new_row = edited_df.iloc[i]
                    if not orig_row.equals(new_row):
                        update_data = new_row.to_dict()
                        prod_id = update_data.pop('idProducte', None)
                        if prod_id:
                            for k, v in update_data.items():
                                import math
                                if pd.isna(v) or (isinstance(v, float) and math.isnan(v)): 
                                    update_data[k] = None
                                elif hasattr(v, 'item'): 
                                    update_data[k] = v.item()
                            supabase.table('tb_productes').update(update_data).eq('idProducte', prod_id).execute()
                            updates += 1
                
                if updates > 0:
                    st.cache_data.clear()
                    st.session_state["df_key_counter"] = st.session_state.get("df_key_counter", 0) + 1
                    st.rerun()
                
            # Dummy selection event to bypass the edit form
            class DummySelection:
                def __init__(self):
                    self.selection = {}
            selection_event = DummySelection()
        else:
            selection_event = st.dataframe(
                df_page, 
                use_container_width=True,
                height=int(dynamic_height),
                on_select="rerun",
                selection_mode="single-row",
                column_config=col_configs,
                key=f"df_select_{db_select}_{st.session_state[page_key]}_{st.session_state.get('df_key_counter', 0)}"
            )
    
    # 4. Modify / Delete Section
    st.write("")
    
    selected_rows = selection_event.selection.get("rows", [])
    
    if selected_rows:
        row_idx_page = selected_rows[0]
        row_idx = df_page.index[row_idx_page]
        current_row_data = df_to_show.loc[row_idx]
        
        db_table_info = {
            "Despeses (General)": ("despeses", "ID_mov"),
            "Previsió de Pagaments": ("pagaments", "idPago"),
            "Previsió d'Ingressos": ("ingressos", "idIngres"),
            "Compres Supermercat": ("compresSuper", "IdCompra"),
            "Gasolina": ("gasolina", "idGasolina"),
            "Kilòmetres Cotxe": ("kmCotxe", "idRuta"),
            "Pagament Hipoteca": ("hipoteca", None),
            "Estalvis DP": ("estalviDP", None),
            "Stock Rebost": ("tb_productes", "idProducte")
        }.get(db_select)
        
        table_name, id_col = db_table_info
        id_val = None
        if id_col:
            id_val = current_row_data[id_col]
            try:
                if float(id_val).is_integer():
                    id_val = int(float(id_val))
                else:
                    id_val = float(id_val)
            except (ValueError, TypeError):
                id_val = str(id_val)
                
        # Calculate dynamic margin-top to align buttons with the selected row
        # 36px for the header, 35px per row.
        margin_top = 40 + row_idx_page * 35.5
        
        with col_sidebar_actions:
            # Spacer to push the buttons down to the selected row's height
            st.markdown(f"<div style='margin-top: {margin_top}px;'></div>", unsafe_allow_html=True)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("✏️", help="Modificar registre", key=f"btn_mod_call_{db_select}_{row_idx}"):
                    show_modify_dialog(table_name, id_col, id_val, current_row_data, db_select, df_to_show, row_idx)
            with btn_col2:
                if st.button("❌", help="Esborrar registre", key=f"btn_del_call_{db_select}_{row_idx}"):
                    show_delete_dialog(table_name, id_col, id_val, current_row_data, db_select, df_to_show, row_idx)






# ================= TAB 4: XAT IA =================
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

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # React to user input
        if prompt := st.chat_input("Exemple: Quant he gastat en gasolina el mes de juny?"):
            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
                
            with st.spinner("L'assistent està pensant..."):
                try:
                    model = genai.GenerativeModel('gemini-flash-latest')
                        
                    # Prepare context using only analisi_year to drastically reduce token usage
                    year_desp_context = df_desp[df_desp['any'] == analisi_year] if 'any' in df_desp.columns else df_desp
                    year_ing_context = df_ing[df_ing['any'] == analisi_year] if 'any' in df_ing.columns else df_ing
                        
                    context = f"Tens les següents taules de dades financeres de l'any {analisi_year} en format CSV:\n\n"
                    context += "TAULA DESPESES:\n" + year_desp_context.to_csv(index=False) + "\n\n"
                    context += "TAULA INGRESSOS:\n" + year_ing_context.to_csv(index=False) + "\n\n"
                    context += "TAULA TR CARTERA:\n" + df_cartera.to_csv(index=False) + "\n\n"
                        
                    sys_prompt = "Ets un assistent financer expert. Respon a les preguntes de l'usuari únicament basant-te en les dades proporcionades. Respon sempre en català de forma clara i concisa. IMPORTANT: Respon exclusivament amb text normal, no utilitzis cap eina ni function call ni codi."
                        
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


# ================= TAB 6: REGISTRE D'ACCIONS (ONLY ADMIN) =================
if st.session_state.get("role") == "admin":
    with tab_log:
        st.markdown("<h3 style='color:#f39c12;'>📜 Registre d'Activitats i Accions</h3>", unsafe_allow_html=True)
        st.write("Aquesta pestanya només és visible per als administradors. Aquí es mostren els canvis fets a la base de dades.")
        if st.button("🔄 Refrescar Registre"):
            st.rerun()
            
        try:
            supabase = get_supabase_client("admin")
            logs_response = supabase.table("registre_accions").select("*").order("data_hora", desc=True).limit(200).execute()
            if logs_response.data:
                df_logs = pd.DataFrame(logs_response.data)
                df_logs['data_hora'] = pd.to_datetime(df_logs['data_hora']).dt.strftime('%d/%m/%Y %H:%M:%S')
                df_logs['detalls'] = df_logs['detalls'].apply(lambda x: str(x) if str(x) == "None" else f"ℹ️ {x}")
                try:
                    st.dataframe(
                        df_logs[['data_hora', 'usuari', 'rol', 'tipus_accio', 'taula_afectada', 'detalls']],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "detalls": st.column_config.TextColumn("Detalls")
                        }
                    )
                except Exception as e:
                    st.error(f"Error rendering df_logs: {e}")
            else:
                st.info("Encara no hi ha cap registre d'accions.")
        except Exception as e:
            st.error(f"Error llegint el registre: {e}")

# Auto-select text on focus for number inputs
import streamlit.components.v1 as components
components.html(
    '''
    <script>
    const parent = window.parent.document;
    if (!parent.window.hasOwnProperty('autoSelectAdded')) {
        parent.window.autoSelectAdded = true;
        parent.body.addEventListener('focusin', function(e) {
            if (e.target && e.target.tagName === 'INPUT' && (e.target.type === 'number' || e.target.inputMode === 'numeric')) {
                e.target.select();
            }
        });
    }
    </script>
    ''',
    height=0, width=0
)


import streamlit.components.v1 as components
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('focusin', function(e) {
        if (e.target && (e.target.type === 'number' || e.target.type === 'text')) {
            e.target.select();
        }
    });
    </script>
    """,
    height=0,
    width=0,
)
