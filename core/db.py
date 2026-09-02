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
    df_gas = df_gas.rename(columns={'?/l': '€/l'})
    df_gas['idGasolina'] = pd.to_numeric(df_gas['idGasolina'], errors='coerce')
    df_gas = df_gas.dropna(subset=['idGasolina']).sort_values(by='idGasolina', ascending=False).reset_index(drop=True)
    df_gas['import'] = clean_numeric(df_gas['import'])
    df_gas['litres'] = clean_numeric(df_gas['litres'])
    df_gas['€/l'] = clean_numeric(df_gas['€/l'])
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
    import json
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
        st.cache_data.clear()
        get_db_tracker().update()
        st.session_state["last_synced_time"] = get_db_tracker().last_update
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


