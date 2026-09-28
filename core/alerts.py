import pandas as pd
import streamlit as st
from datetime import datetime
from core.db import load_dashboard_data

@st.cache_data(ttl=600, show_spinner=False)
def get_global_alerts():
    alerts = []
    
    try:
        # Assegurar que les dades estan carregades
        data = load_dashboard_data()
        if data and len(data) >= 10:
            df_desp, df_ing, df_super, df_gas, df_km, df_hip, df_cartera, df_est, df_limits, df_pag = data
        else:
            return alerts
            
        # 1. Alerta de canvi d'oli (Cotxe)
        if df_km is not None and not df_km.empty:
            df_km_tivoli = df_km[df_km['vehicle'] == 'Tivoli'].copy()
            if not df_km_tivoli.empty:
                df_km_tivoli = df_km_tivoli.sort_values(by='data', ascending=False)
                car_kms_actuals = df_km_tivoli.dropna(subset=['contador'])['contador'].iloc[0]
                kms_left = st.session_state.get("kms_canvi_oli", 31491.0) - car_kms_actuals
                if kms_left <= 0:
                    alerts.append({
                        "type": "error",
                        "icon": "🔧",
                        "title": "Canvi d'Oli (Tivoli)",
                        "message": f"Cal fer el canvi d'oli del cotxe. Teniu el límit superat per {int(abs(kms_left))} km."
                    })
                    
        # 2. Alerta de Loteria
        if df_desp is not None and not df_desp.empty and 'Comentari' in df_desp.columns:
            loteria_mask = df_desp['Comentari'].astype(str).str.startswith('[LOTERIA]', na=False)
            if loteria_mask.any():
                loteria_tickets = df_desp[loteria_mask]
                avui = datetime.today().date()
                for _, row in loteria_tickets.iterrows():
                    com = str(row['Comentari'])
                    parts = com.split('|')
                    try:
                        caduca_str = [p for p in parts if 'Caduca:' in p][0].split('Caduca:')[1].strip()
                        caduca_date = datetime.strptime(caduca_str, '%d/%m/%Y').date()
                        if caduca_date >= avui:
                            dies_restants = (caduca_date - avui).days
                            num_str = [p for p in parts if 'Num:' in p][0].split('Num:')[1].strip()
                            tipus_str = [p for p in parts if 'Tipus:' in p][0].split('Tipus:')[1].strip().replace('[LOTERIA] Tipus:', '').strip()
                            if dies_restants <= 15:
                                alerts.append({
                                    "type": "error",
                                    "icon": "🍀",
                                    "title": f"Loteria Activa ({tipus_str})",
                                    "message": f"Núm. {num_str} - Caduca el {caduca_str} ({dies_restants} dies restants)."
                                })
                            else:
                                alerts.append({
                                    "type": "warning",
                                    "icon": "🍀",
                                    "title": f"Loteria Activa ({tipus_str})",
                                    "message": f"Núm. {num_str} - Caduca el {caduca_str} ({dies_restants} dies restants)."
                                })
                    except:
                        pass
                        
        # 3. Alerta Límits de despesa (Valor superat)
        if df_desp is not None and not df_desp.empty:
            avui = datetime.today()
            curr_year = str(avui.year)
            from core.db import CATALAN_MONTHS, get_limits_for
            curr_month_str = CATALAN_MONTHS[avui.month - 1]
            
            # Filter df_desp for current year and month
            df_curr = df_desp[(df_desp['any'].astype(str) == curr_year) & (df_desp['mes'].str.lower() == curr_month_str)].copy()
            
            if not df_curr.empty:
                df_curr['Categoria'] = df_curr['Categoria'].str.strip().str.lower()
                sum_menjar = df_curr[df_curr['Categoria'] == 'menjar']['import'].sum()
                sum_gasolina = df_curr[df_curr['Categoria'] == 'gasolina']['import'].sum()
                sum_restaurant = df_curr[df_curr['Categoria'] == 'restaurant']['import'].sum()
                sum_farmacia = df_curr[df_curr['Categoria'] == 'farmàcia']['import'].sum()
                sum_neteja = df_curr[df_curr['Categoria'] == 'neteja']['import'].sum()
                sum_varis = df_curr[df_curr['Categoria'] == 'varis']['import'].sum()
                
                curr_limits = get_limits_for(avui.year, curr_month_str)
                
                col_mapping_alert = {
                    'menjar': ('menjar', sum_menjar),
                    'gasolina': ('gasolina', sum_gasolina),
                    'restaurant': ('restaurant', sum_restaurant),
                    'farmacia': ('farmàcia', sum_farmacia),
                    'neteja': ('neteja', sum_neteja),
                    'varis': ('varis', sum_varis)
                }
                
                exceeded = []
                for limit_key, (display_lbl, val) in col_mapping_alert.items():
                    lim = curr_limits.get(limit_key, float('inf'))
                    if val > lim:
                        exceeded.append(f"{display_lbl} ({val:,.2f} € > {lim:,.2f} €)")
                
                if exceeded:
                    alerts.append({
                        "type": "error",
                        "icon": "⚠️",
                        "title": "Valor superat",
                        "message": ", ".join(exceeded)
                    })
                        
    except Exception as e:
        print(f"Error generant alertes globals: {e}")
        
    return alerts
