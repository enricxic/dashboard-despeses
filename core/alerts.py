import pandas as pd
import streamlit as st
from datetime import datetime
from core.db import load_dashboard_data

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
                        
    except Exception as e:
        print(f"Error generant alertes globals: {e}")
        
    return alerts
