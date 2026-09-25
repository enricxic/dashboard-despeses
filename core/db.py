import os
import streamlit as st
import pandas as pd
import numpy as np
import uuid
import json
from datetime import datetime, date
from supabase import create_client, Client
import sqlalchemy
from sqlalchemy import text as sa_text

# ----------------- DATA UTILITIES -----------------
CSV_DIR = "csv"
_DB_ENGINE_FAILED = False

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
    'LA CAIXA': 'La Caixa',
    'TR Cartera': 'TR Cartera',
    'TradeRep.': 'TRADE REPUB.',
    'Trade Repub.': 'TRADE REPUB.',
    'TRADE REPUB.': 'TRADE REPUB.',
    'Casa': 'Casa',
    'CASA': 'Casa',
    'T.Moneder': 'Tg.Moneder',
    'Tg.Moneder': 'Tg.Moneder',
    'TG.MONEDER': 'Tg.Moneder',
    'T.CorteInglés': 'CORTEINGLÉS',
    't.CorteInglés': 'CORTEINGLÉS',
    'T.CorteIngles': 'CORTEINGLÉS',
    't.CorteIngles': 'CORTEINGLÉS',
    'CORTEINGLÉS': 'CORTEINGLÉS',
    'CORTEINGLES': 'CORTEINGLÉS',
    'Pago VISA': 'Pago VISA',
    'PAGO VISA': 'Pago VISA'
}

def clean_numeric(series):
    if not isinstance(series, pd.Series):
        if isinstance(series, (int, float, np.number)):
            return float(series)
        series = pd.Series(series if series is not None else [0.0])
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
def get_db_engine():
    if "connection_string" in st.secrets:
        try:
            return sqlalchemy.create_engine(
                st.secrets["connection_string"],
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=5,
                connect_args={'connect_timeout': 3}
            )
        except Exception:
            return None
    return None

def fetch_table_fast(table_name):
    import os
    csv_path = os.path.join("csv", f"{table_name}.csv")
    
    is_offline = False
    try:
        import streamlit as st
        is_offline = st.session_state.get("is_offline", False)
    except:
        pass
        
    if is_offline:
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path, sep=';')
                return table_name, df
            except Exception as e:
                print(f"Error reading local CSV for {table_name}: {e}")
        return table_name, pd.DataFrame()

    df_result = pd.DataFrame()
    
    global _DB_ENGINE_FAILED
    
    if not _DB_ENGINE_FAILED:
        try:
            engine = get_db_engine()
            if engine is not None:
                df_result = pd.read_sql(f'SELECT * FROM "{table_name}"', engine)
        except Exception as e:
            _DB_ENGINE_FAILED = True
            print(f"Error connexio directa PostgreSQL a {table_name}, fallback a REST API: {e}")
    if df_result.empty:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_result = fetch_all_supabase(supabase, table_name)
        
    # Guardar còpia local al CSV si s'ha pogut baixar del núvol per properes avaries
    if not df_result.empty:
        os.makedirs("csv", exist_ok=True)
        try:
            df_result.to_csv(csv_path, sep=';', index=False)
        except Exception:
            pass
            
    return table_name, df_result

@st.cache_resource
def get_db_tracker():
    return DBTracker()

@st.cache_resource
def get_supabase_client(role: str) -> Client:
    url = st.secrets["SUPABASE_URL"]
    if role == "admin" and "SUPABASE_KEY_SECRET" in st.secrets:
        key = st.secrets["SUPABASE_KEY_SECRET"]
    else:
        key = st.secrets.get("SUPABASE_KEY_PUBLISHABLE") or st.secrets.get("SUPABASE_KEY_SECRET")
    return create_client(url, key)

def fetch_all_supabase(client, table_name):
    data = []
    count = 1000  # Optimitzat a 1000 per reduir les peticions massives a la API REST
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

@st.cache_data(ttl=600, show_spinner=False)
def load_dashboard_data(tables_to_load=None, mtimes=None):
    from concurrent.futures import ThreadPoolExecutor
    
    if tables_to_load is None:
        tables_to_load = [
            'despeses', 'ingressos', 'compresSuper', 'gasolina', 'kmCotxe',
            'hipoteca', 'tr_cartera', 'estalviDP', 'limitsDespeses', 'pagaments'
        ]
        
    with ThreadPoolExecutor(max_workers=4) as executor:
        fetched = dict(zip(tables_to_load, executor.map(fetch_table_fast, tables_to_load)))
    
    out = {}
    if 'despeses' in fetched:
        _, df = fetched['despeses']
        df = fix_mojibake_df(df)
        df['ID_mov'] = pd.to_numeric(df['ID_mov'], errors='coerce')
        df = df.dropna(subset=['ID_mov']).sort_values(by='ID_mov', ascending=False).reset_index(drop=True)
        df['import ingrés'] = clean_numeric(df['import ingrés'])
        df['Import càrrec'] = clean_numeric(df['Import càrrec'])
        df['parsed_date'] = df['Data'].apply(parse_excel_date)
        df['date_score'] = df['any'] * 12 + df['mes'].astype(str).str.lower().map(MONTHS_MAP).fillna(12).astype(int)
        out['df_desp'] = df
        
    if 'ingressos' in fetched:
        _, df = fetched['ingressos']
        df = fix_mojibake_df(df)
        df['idIngres'] = pd.to_numeric(df['idIngres'], errors='coerce')
        df = df.dropna(subset=['idIngres']).sort_values(by='idIngres', ascending=False).reset_index(drop=True)
        df['Import'] = clean_numeric(df['Import'])
        df['parsed_date'] = df['Data'].apply(parse_excel_date)
        out['df_ing'] = df
        
    if 'compresSuper' in fetched:
        _, df = fetched['compresSuper']
        df = fix_mojibake_df(df)
        df['IdCompra'] = pd.to_numeric(df['IdCompra'], errors='coerce')
        df = df.dropna(subset=['IdCompra']).sort_values(by='IdCompra', ascending=False).reset_index(drop=True)
        df['totLinea'] = clean_numeric(df['totLinea'])
        df['parsed_date'] = df['data'].apply(parse_excel_date)
        out['df_super'] = df
        
    if 'gasolina' in fetched:
        _, df = fetched['gasolina']
        df = fix_mojibake_df(df)
        df = df.rename(columns={'?/l': 'euros/litre', '€/l': 'euros/litre'})
        df['idGasolina'] = pd.to_numeric(df['idGasolina'], errors='coerce')
        df = df.dropna(subset=['idGasolina']).sort_values(by='idGasolina', ascending=False).reset_index(drop=True)
        df['import'] = clean_numeric(df['import'])
        df['litres'] = clean_numeric(df['litres'])
        df['euros/litre'] = clean_numeric(df.get('euros/litre', 0))
        df['parsed_date'] = df['data'].apply(parse_excel_date)
        out['df_gas'] = df
        
    if 'kmCotxe' in fetched:
        _, df = fetched['kmCotxe']
        df = fix_mojibake_df(df)
        df['idRuta'] = pd.to_numeric(df['idRuta'], errors='coerce')
        df = df.dropna(subset=['idRuta']).sort_values(by='idRuta', ascending=False).reset_index(drop=True)
        df['contador'] = clean_numeric(df['contador'])
        df['km'] = clean_numeric(df['km'])
        df['parsed_date'] = df['data'].apply(parse_excel_date)
        out['df_km'] = df
        
    if 'hipoteca' in fetched:
        _, df = fetched['hipoteca']
        if 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce')
            df = df.dropna(subset=['id'])
        if 'Quota fixa' in df.columns:
            df = df.dropna(subset=['Quota fixa'])
            df['Quota fixa'] = clean_numeric(df['Quota fixa'])
        out['df_hip'] = df
        
    if 'tr_cartera' in fetched:
        _, df = fetched['tr_cartera']
        df = fix_mojibake_df(df)
        df['idTRCartera'] = pd.to_numeric(df.get('idTRCartera', df.index), errors='coerce')
        df = df.dropna(subset=['idTRCartera']).sort_values(by='idTRCartera', ascending=False).reset_index(drop=True)
        df['COMPRA'] = clean_numeric(df.get('COMPRA', 0))
        df['VENDA'] = clean_numeric(df.get('VENDA', 0))
        df['parsed_date'] = df.get('DATA', pd.Series(dtype=object)).apply(parse_excel_date)
        out['df_cartera'] = df
        
    if 'estalviDP' in fetched:
        _, df = fetched['estalviDP']
        df = df.dropna(subset=['mes', 'any'])
        df['any'] = pd.to_numeric(df['any'], errors='coerce')
        df['quota'] = clean_numeric(df['quota'])
        if 'aportació' in df.columns: df['aportació'] = clean_numeric(df['aportació'])
        if 'rescat' in df.columns: df['rescat'] = clean_numeric(df['rescat'])
        if 'pérdua' in df.columns: df['pérdua'] = clean_numeric(df['pérdua'])
        out['df_est'] = df
        
    if 'limitsDespeses' in fetched:
        _, df = fetched['limitsDespeses']
        df = df.dropna(subset=['data_inici'])
        df['parsed_date'] = df['data_inici'].apply(parse_excel_date)
        out['df_limits'] = df
        
    if 'pagaments' in fetched:
        _, df = fetched['pagaments']
        df = df.dropna(subset=['idPago'])
        df['Import'] = clean_numeric(df['Import'])
        df['parsed_date'] = df['Data'].apply(parse_excel_date)
        out['df_pag'] = df
        
    df_desp = out.get('df_desp', pd.DataFrame())
    df_ing = out.get('df_ing', pd.DataFrame())
    df_super = out.get('df_super', pd.DataFrame())
    df_gas = out.get('df_gas', pd.DataFrame())
    df_km = out.get('df_km', pd.DataFrame())
    df_hip = out.get('df_hip', pd.DataFrame())
    df_est = out.get('df_est', pd.DataFrame())
    df_limits = out.get('df_limits', pd.DataFrame())
    df_pag = out.get('df_pag', pd.DataFrame())
    df_cartera = out.get('df_cartera', pd.DataFrame())

    return df_desp, df_ing, df_super, df_gas, df_km, df_hip, df_est, df_limits, df_pag, df_cartera

# Load categories_conceptes.json if exists
import json

@st.cache_data(ttl=60, show_spinner=False)
def load_categories_conceptes():
    if "cached_cat_config" in st.session_state and isinstance(st.session_state["cached_cat_config"], dict):
        return st.session_state["cached_cat_config"]
    try:
        supabase = get_supabase_client("guest")
        res = supabase.table("app_config").select("config_json").eq("id", 1).execute()
        if res.data and len(res.data) > 0:
            cfg = res.data[0]["config_json"]
            if isinstance(cfg, dict):
                st.session_state["cached_cat_config"] = cfg
                return cfg
    except Exception as e:
        print("Supabase config load failed:", e)
        pass

    # Fallback to local
    filepath = "categories_conceptes.json"
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                if isinstance(cfg, dict):
                    st.session_state["cached_cat_config"] = cfg
                    return cfg
        except Exception:
            pass
    return {}

cat_config = load_categories_conceptes()

def get_config_categories():
    cfg = load_categories_conceptes()
    special_keys = {"families_compres", "articles_compres", "bancs", "formes_pago", "supers_tickets"}
    cats = set()
    
    if cfg and isinstance(cfg, dict):
        for k in cfg.keys():
            k_str = str(k).strip()
            if k_str and k_str not in special_keys:
                cats.add(k_str)
                
    filepath = "categories_conceptes.json"
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                local_cfg = json.load(f)
                if local_cfg and isinstance(local_cfg, dict):
                    for k in local_cfg.keys():
                        k_str = str(k).strip()
                        if k_str and k_str not in special_keys:
                            cats.add(k_str)
        except Exception:
            pass

    canon_map = {
        "farmacia": "farmàcia",
        "asseguranca": "assegurança",
        "assegurana": "assegurança",
        "ingrés_general": "ingres_general",
        "ingrés_extra": "ingres_extra",
        "parallar": "parallar",
        "para_llar": "parallar",
    }
    cleaned_cats = set()
    for c in cats:
        c_clean = c.strip()
        c_norm = canon_map.get(c_clean.lower(), c_clean)
        cleaned_cats.add(c_norm)
            
    return sorted(list(cleaned_cats))

def get_config_concepts(category):
    if not category:
        return []
    cfg = load_categories_conceptes()
    concepts = set()
    
    # 1. From active config
    if cfg and category in cfg:
        concepts.update([str(c).strip() for c in cfg[category] if c and str(c).strip()])
        
    # 2. From local json file
    filepath = "categories_conceptes.json"
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                local_cfg = json.load(f)
                if local_cfg and category in local_cfg:
                    concepts.update([str(c).strip() for c in local_cfg[category] if c and str(c).strip()])
        except Exception:
            pass
            
    # 3. Ensure defaults for op_banc
    if category == "op_banc":
        concepts.update(["Amortització", "Cashback TR", "TR Cashback", "Embargament", "Gestions Banc", "Pago ElCorteInglés", "Pago VISA", "Reintegre Caixer", "Transferència", "Traspàs comptes"])
        
    # 4. From df_desp
    if "df_desp" in st.session_state and not st.session_state["df_desp"].empty:
        df_d = st.session_state["df_desp"]
        if 'Idcategoria' in df_d.columns and 'Idconcepte' in df_d.columns:
            desp_c = df_d[df_d['Idcategoria'] == category]['Idconcepte'].dropna().unique()
            concepts.update([str(c).strip() for c in desp_c if c and str(c).strip()])
            
    # Clean and filter: remove empty items, and '+' items, deduplicate by normalized string
    cleaned_dict = {}
    for c in concepts:
        if c and not str(c).startswith("➕"):
            c_str = str(c).strip()
            if not c_str: continue
            import unicodedata
            norm = unicodedata.normalize('NFKD', c_str).encode('ASCII', 'ignore').decode('utf-8').lower()
            if norm in cleaned_dict:
                # Prefer version with accents (non-ascii characters)
                if len(c_str.encode('ascii', 'ignore')) < len(c_str):
                    cleaned_dict[norm] = c_str
            else:
                cleaned_dict[norm] = c_str
                
    if "cashback tr" in cleaned_dict and "tr cashback" in cleaned_dict:
        del cleaned_dict["cashback tr"]
        
    cleaned = list(cleaned_dict.values())
    return sorted(cleaned)

def get_config_banks():
    try:
        from core.config_manager import get_active_bancs
        active_b = get_active_bancs()
        if active_b:
            return [b["nom"] for b in active_b]
    except Exception:
        pass
    cfg = load_categories_conceptes()
    if cfg and "bancs" in cfg:
        return cfg["bancs"]
    return list(BANK_MAPPING.keys())

def get_config_payment_methods():
    cfg = load_categories_conceptes()
    if cfg and "formes_pago" in cfg:
        return [fp for fp in cfg["formes_pago"] if fp]
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
        import pandas as pd
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
        new_df = pd.DataFrame([new_row])
        updated_df = pd.concat([new_df, df], ignore_index=True)
        if sort_col and sort_col in updated_df.columns:
            updated_df[sort_col] = pd.to_numeric(updated_df[sort_col], errors='coerce')
            updated_df = updated_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
            
        # Generar camps derivats necessaris pel dashboard si falten
        if 'mes' in updated_df.columns:
            updated_df['clean_mes'] = updated_df['mes'].astype(str).str.strip().str.lower()
        if 'any' in updated_df.columns and 'clean_mes' in updated_df.columns:
            updated_df['date_score'] = updated_df['any'] * 12 + updated_df['clean_mes'].map(MONTHS_MAP).fillna(12).astype(int)
            
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
                
                # Refrescar camps derivats després de l'update
                if 'mes' in df.columns:
                    df['clean_mes'] = df['mes'].astype(str).str.strip().str.lower()
                if 'any' in df.columns and 'clean_mes' in df.columns:
                    df['date_score'] = df['any'] * 12 + df['clean_mes'].map(MONTHS_MAP).fillna(12).astype(int)
                    
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

def log_offline_action(table_name, action_type, details):
    import json
    import os
    from datetime import datetime
    queue_file = "sync_queue.json"
    queue = []
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except:
            pass
            
    # Clean datetime objects for json
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
        
    queue.append({
        "taula": table_name,
        "accio": action_type,
        "detalls": clean_dict(details),
        "timestamp": datetime.now().isoformat()
    })
    try:
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving offline action to queue: {e}")

def save_to_csv_local(df, table_name):
    import os
    os.makedirs("csv", exist_ok=True)
    csv_path = os.path.join("csv", f"{table_name}.csv")
    try:
        df.to_csv(csv_path, sep=';', index=False)
    except Exception as e:
        print(f"Error saving {csv_path} locally: {e}")

def insert_db_row(table_name, new_row_dict):
    is_offline = st.session_state.get("is_offline", False)
    if is_offline:
        log_offline_action(table_name, 'INSERT', new_row_dict)
        update_session_state_insert(table_name, new_row_dict)
        # Try to save the updated session state df to local CSV
        table_map = {
            'despeses': 'df_desp', 'ingressos': 'df_ing',
            'compresSuper': 'df_super', 'gasolina': 'df_gas',
            'kmCotxe': 'df_km', 'hipoteca': 'df_hip',
            'estalviDP': 'df_est', 'limitsDespeses': 'df_limits',
            'pagaments': 'df_pag', 'tr_cartera': 'df_cartera'
        }
        if table_name in table_map and table_map[table_name] in st.session_state:
            save_to_csv_local(st.session_state[table_map[table_name]], table_name)
        return True

    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    try:
        supabase.table(table_name).insert(new_row_dict).execute()
        log_action(table_name, 'INSERT', new_row_dict)
        
        update_session_state_insert(table_name, new_row_dict)
        return True
    except Exception as e:
        st.error(f"❌ Error al desar a Supabase ({table_name}): {str(e)}")

def append_to_db(df_new, table_name, state_key, extra_details=None):
    import json
    
    is_offline = st.session_state.get("is_offline", False)
    
    details = {'count': len(df_new)}
    if table_name == 'compresSuper' and 'super' in df_new.columns:
        supers = df_new['super'].unique().tolist()
        details['supermercat'] = supers[0] if len(supers) == 1 else supers
        
    if extra_details:
        details.update(extra_details)
        
    # Store the fully inserted rows
    rows_json = json.loads(df_new.to_json(orient='records', date_format='iso'))
    details['rows_inserted'] = rows_json

    if is_offline:
        log_offline_action(table_name, 'INSERT_BULK', details)
        # Update session state df directly
        if state_key and state_key in st.session_state:
            del st.session_state[state_key]
        load_dashboard_data.clear()
        # En el proper load_dashboard_data offline es llegirà del CSV, 
        # així que hauríem d'actualitzar el CSV ara. Però primer l'hem de carregar si no ho està.
        # Ho simplifiquem deixant que load_dashboard_data.clear() faci la seva feina i 
        # nosaltres només desem aquest chunk al CSV manualment llegint-lo abans:
        import os
        csv_path = os.path.join("csv", f"{table_name}.csv")
        if os.path.exists(csv_path):
            try:
                df_existing = pd.read_csv(csv_path, sep=';')
                df_updated = pd.concat([df_new, df_existing], ignore_index=True)
                df_updated.to_csv(csv_path, sep=';', index=False)
            except:
                pass
        return True

    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    try:
        supabase.table(table_name).insert(rows_json).execute()
        log_action(table_name, 'INSERT_BULK', details)
        
        if state_key and state_key in st.session_state:
            st.session_state[state_key] = pd.concat([st.session_state[state_key], df_new], ignore_index=True)
            
        load_dashboard_data.clear()
        get_db_tracker().update()
        st.session_state["last_synced_time"] = get_db_tracker().last_update
        return True
    except Exception as e:
        st.error(f"❌ **Error a la base de dades (APPEND {table_name})**: {str(e)}")
        return False

def add_concept_to_config(category, concept):
    if not concept or not category:
        return
    c_str = str(concept).strip()
    cat_str = str(category).strip()
    if not c_str or c_str.startswith("➕"):
        return
    global cat_config
    if cat_config is None or not isinstance(cat_config, dict):
        cat_config = load_categories_conceptes() or {}
    if cat_str not in cat_config:
        existing = get_config_concepts(cat_str)
        cat_config[cat_str] = list(existing)
    if c_str not in cat_config[cat_str]:
        cat_config[cat_str].append(c_str)
        cat_config[cat_str] = [c for c in cat_config[cat_str] if c and not c.startswith("➕")]
        cat_config[cat_str].sort()
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
    global cat_config
    cat_config = config
    st.session_state["cached_cat_config"] = config
    # Save to Supabase
    try:
        supabase = get_supabase_client("admin")
        supabase.table("app_config").upsert({"id": 1, "config_json": config}).execute()
        load_categories_conceptes.clear()
    except Exception as e:
        try:
            supabase = get_supabase_client("guest")
            supabase.table("app_config").upsert({"id": 1, "config_json": config}).execute()
            load_categories_conceptes.clear()
        except Exception as e2:
            print("Supabase config save failed:", e, e2)
        
    # Also save to local fallback
    filepath = "categories_conceptes.json"
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


def load_ofertes():
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        res = supabase.table("app_config").select("config_json").eq("id", 6).execute()
        if res.data and "config_json" in res.data[0]:
            return res.data[0]["config_json"] or []
    except Exception as e:
        print(f"Error loading ofertes: {e}")
    return []

def save_ofertes(ofertes_list):
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        supabase.table("app_config").upsert({"id": 6, "config_json": ofertes_list}).execute()
        return True
    except Exception as e:
        print(f"Error saving ofertes: {e}")
        return False

def delete_db_row(table_name, id_col, id_val):
    is_offline = st.session_state.get("is_offline", False)
    if is_offline:
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
            import pandas as pd
            df = st.session_state[df_key]
            mask = df[id_col] == id_val
            if mask.any():
                row_dict = df[mask].iloc[0].replace({np.nan: None}).to_dict()
                for k, v in row_dict.items():
                    if isinstance(v, pd.Timestamp):
                        row_dict[k] = v.isoformat()
                deleted_row_data = row_dict
        detalls = {'id_col': id_col, 'id_val': id_val}
        if deleted_row_data:
            detalls['deleted_row'] = deleted_row_data
        log_offline_action(table_name, 'DELETE', detalls)
        update_session_state_delete(table_name, id_col, id_val)
        csv_table_map = {
            'despeses': 'df_desp', 'ingressos': 'df_ing', 'compresSuper': 'df_super',
            'gasolina': 'df_gas', 'kmCotxe': 'df_km', 'pagaments': 'df_pag', 'tr_cartera': 'df_cartera'
        }
        if table_name in csv_table_map and csv_table_map[table_name] in st.session_state:
            save_to_csv_local(st.session_state[csv_table_map[table_name]], table_name)
        return True

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
        import pandas as pd
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
        return True
    except Exception as e:
        st.error(f"❌ Error a l'esborrar de Supabase ({table_name}): {str(e)}")

def update_db_row(table_name, id_col, id_val, new_data):
    is_offline = st.session_state.get("is_offline", False)
    if is_offline:
        update_payload = new_data.copy()
        if id_col in update_payload:
            del update_payload[id_col]
        import pandas as pd
        for k, v in update_payload.items():
            if pd.isna(v):
                update_payload[k] = None
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
        detalls = {'id_col': id_col, 'id_val': id_val, 'changes': update_payload}
        if old_row_data:
            detalls['old_row'] = old_row_data
        log_offline_action(table_name, 'UPDATE', detalls)
        update_session_state_update(table_name, id_col, id_val, update_payload)
        csv_table_map = {
            'despeses': 'df_desp', 'ingressos': 'df_ing',
            'compresSuper': 'df_super', 'gasolina': 'df_gas',
            'kmCotxe': 'df_km', 'hipoteca': 'df_hip',
            'estalviDP': 'df_est', 'limitsDespeses': 'df_limits',
            'pagaments': 'df_pag', 'tr_cartera': 'df_cartera'
        }
        if table_name in csv_table_map and csv_table_map[table_name] in st.session_state:
            save_to_csv_local(st.session_state[csv_table_map[table_name]], table_name)
        return True

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
        import pandas as pd
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
            
        import pandas as pd
        for k, v in update_payload.items():
            if pd.isna(v):
                update_payload[k] = None
                
        supabase.table(table_name).update(update_payload).eq(id_col, id_val).execute()
        
        detalls = {'id_col': id_col, 'id_val': id_val, 'changes': update_payload}
        if old_row_data:
            detalls['old_row'] = old_row_data
        log_action(table_name, 'UPDATE', detalls)
        
        update_session_state_update(table_name, id_col, id_val, update_payload)
        return True
    except Exception as e:
        print(f"FAILED PAYLOAD FOR {table_name}:", update_payload)
        st.error(f"❌ Error a l'actualitzar Supabase ({table_name}): {str(e)}")

def ensure_session_dfs():
    module = st.session_state.get("current_module")
    
    table_requirements = {
        'modules.compres': ['despeses', 'ingressos', 'compresSuper', 'gasolina', 'hipoteca', 'estalviDP', 'limitsDespeses', 'pagaments'],
        'modules.dashboard': ['despeses', 'ingressos', 'tr_cartera'],
        'modules.cotxe': ['gasolina', 'kmCotxe']
    }
    
    # Per defecte ho carreguem tot si no estem en un mòdul específic que tingui requeriments
    tables_to_load = tuple(table_requirements.get(module, [
        'despeses', 'ingressos', 'compresSuper', 'gasolina', 'kmCotxe',
        'hipoteca', 'tr_cartera', 'estalviDP', 'limitsDespeses', 'pagaments'
    ]))
    
    key_mapping = {
        'despeses': 'df_desp', 'ingressos': 'df_ing', 'compresSuper': 'df_super',
        'gasolina': 'df_gas', 'kmCotxe': 'df_km', 'hipoteca': 'df_hip',
        'estalviDP': 'df_est', 'limitsDespeses': 'df_limits', 'pagaments': 'df_pag',
        'tr_cartera': 'df_cartera'
    }
    
    required_keys = [key_mapping[t] for t in tables_to_load]
    
    tracker = get_db_tracker()
    needs_init = (
        "dfs_initialized" not in st.session_state 
        or not st.session_state.get("dfs_initialized", False)
        or any(k not in st.session_state for k in required_keys)
        or "last_synced_time" not in st.session_state 
        or not isinstance(st.session_state.get("last_synced_time"), datetime) 
        or st.session_state.get("last_synced_time") < tracker.last_update
    )
    if needs_init:
        dfs = load_dashboard_data(tables_to_load=tables_to_load, mtimes=tracker.last_update)
        st.session_state["df_desp"] = dfs[0]
        st.session_state["df_ing"] = dfs[1]
        st.session_state["df_super"] = dfs[2]
        st.session_state["df_gas"] = dfs[3]
        st.session_state["df_km"] = dfs[4]
        st.session_state["df_hip"] = dfs[5]
        st.session_state["df_est"] = dfs[6]
        st.session_state["df_limits"] = dfs[7]
        st.session_state["df_pag"] = dfs[8]
        st.session_state["df_cartera"] = dfs[9]
        
        st.session_state["dfs_initialized"] = True
        st.session_state["last_synced_time"] = tracker.last_update

try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx() is not None:
        ensure_session_dfs()
except Exception:
    pass

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


