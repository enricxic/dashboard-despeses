import pandas as pd
import streamlit as st
from datetime import datetime
import json
import os
from core.db import load_dashboard_data

def load_alerts_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'alerts_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "membres_familia": [],
            "regles_alertes": {
                "loteria": {"activar_dia_sorteig": True, "dies_avis_caducitat": 7, "mostrar_a_campana": True}
            }
        }

def get_global_alerts():
    alerts = []
    config = load_alerts_config()
    
    try:
        # Prioritzar df_desp carregat a la sessió activa
        df_desp = None
        if "df_desp" in st.session_state and isinstance(st.session_state["df_desp"], pd.DataFrame) and not st.session_state["df_desp"].empty:
            df_desp = st.session_state["df_desp"]
            
        data = load_dashboard_data(tables_to_load=['despeses', 'kmCotxe', 'limitsDespeses'])
        if data and len(data) >= 10:
            d_desp, df_ing, df_super, df_gas, df_km, df_hip, df_cartera, df_est, df_limits, df_pag = data
            if df_desp is None or df_desp.empty:
                df_desp = d_desp
        else:
            if df_desp is None:
                return alerts
            
        # 1. Alerta de canvi d'oli (Cotxe)
        if df_km is not None and not df_km.empty:
            if 'cotxe' in df_km.columns:
                df_km_tivoli = df_km[df_km['cotxe'].astype(str).str.contains('tivoli|tívoli', case=False, na=False)].copy()
            else:
                df_km_tivoli = df_km.copy()
            
            if not df_km_tivoli.empty:
                df_km_tivoli = df_km_tivoli.sort_values(by='data', ascending=False)
                car_kms_actuals = pd.to_numeric(df_km_tivoli['contador'], errors='coerce').max()
                if pd.isna(car_kms_actuals):
                    car_kms_actuals = 0.0
                from core.config_manager import load_app_config
                mant = load_app_config().get("manteniment_cotxe", {})
                oli = mant.get("oli", {})
                rodes = mant.get("rodes", {})
                avis_km = float(mant.get("avis_km", 20000))
                oli_next = float(oli.get("ultim_canvi_km", 30000)) + float(oli.get("interval_km", 16000))
                kms_left = oli_next - car_kms_actuals
                if kms_left <= 0:
                    alerts.append({"type": "error", "icon": "🔧", "title": "Canvi d'Oli (Tivoli)",
                                   "message": f"Cal fer el canvi d'oli (previst als {int(oli_next):,} km). Superat per {int(abs(kms_left)):,} km."})
                elif kms_left <= avis_km:
                    alerts.append({"type": "warning", "icon": "🔧", "title": "Canvi d'Oli (Tivoli)",
                                   "message": f"Queden {int(kms_left):,} km per al canvi d'oli (als {int(oli_next):,} km)."})
                previst = rodes.get("previst") or {}
                if previst.get("km"):
                    rodes_next = float(previst["km"])
                elif rodes.get("ultim_canvi_km"):
                    rodes_next = float(rodes["ultim_canvi_km"]) + float(rodes.get("interval_km", 40000))
                else:
                    rodes_next = None
                rodes_left = (rodes_next - car_kms_actuals) if rodes_next else None
                if rodes_left is not None and rodes_left <= avis_km:
                    alerts.append({"type": "error" if rodes_left <= 0 else "warning", "icon": "🛞", "title": "Pneumàtics (Tivoli)",
                                   "message": f"Revisar/canviar rodes: previst als {int(rodes_next):,} km ({int(rodes_left):,} km restants)."})
                    
        # 2. Alerta de Loteria
        loteria_cfg = config.get("regles_alertes", {}).get("loteria", {})
        if loteria_cfg.get("mostrar_a_campana", True):
            if df_desp is not None and not df_desp.empty and 'Comentari' in df_desp.columns:
                loteria_mask = df_desp['Comentari'].astype(str).str.startswith('[LOTERIA]', na=False)
                if loteria_mask.any():
                    loteria_tickets = df_desp[loteria_mask]
                    avui = datetime.today().date()
                    for _, row in loteria_tickets.iterrows():
                        com = str(row['Comentari'])
                        parts = [p.strip() for p in com.split('|')]
                        try:
                            caduca_str = [p for p in parts if 'Caduca:' in p][0].split('Caduca:')[1].strip()
                            caduca_date = datetime.strptime(caduca_str, '%d/%m/%Y').date()
                            
                            sorteig_date = None
                            try:
                                sorteig_str = [p for p in parts if 'Sorteig:' in p][0].split('Sorteig:')[1].strip()
                                sorteig_date = datetime.strptime(sorteig_str, '%d/%m/%Y').date()
                            except IndexError:
                                pass # No Sorteig date specified
                            
                            if caduca_date >= avui:
                                dies_restants = (caduca_date - avui).days
                                num_str = [p for p in parts if 'Num:' in p][0].split('Num:')[1].strip()
                                tipus_str = [p for p in parts if 'Tipus:' in p][0].split('Tipus:')[1].strip().replace('[LOTERIA] Tipus:', '').strip()
                                
                                avis_caducitat = loteria_cfg.get("dies_avis_caducitat", 7)
                                activar_sorteig = loteria_cfg.get("activar_dia_sorteig", True)
                                
                                # Si avui és el dia del sorteig i està activat
                                is_draw_day = (activar_sorteig and sorteig_date == avui)
                                
                                if dies_restants <= avis_caducitat:
                                    alerts.append({
                                        "type": "error",
                                        "icon": "🍀",
                                        "title": f"Loteria a punt de caducar ({tipus_str})",
                                        "message": f"Núm. {num_str} - Caduca el {caduca_str} ({dies_restants} dies restants)."
                                    })
                                elif is_draw_day:
                                    alerts.append({
                                        "type": "warning",
                                        "icon": "🍀",
                                        "title": f"Sorteig Avui! ({tipus_str})",
                                        "message": f"Avui és el sorteig del núm. {num_str}!"
                                    })
                        except Exception as e:
                            pass
                        
        # 3. Alerta Límits de despesa (Valor superat)
        try:
            if df_desp is not None and not df_desp.empty:
                avui = datetime.today()
                curr_year = str(avui.year)
                from core.db import CATALAN_MONTHS, get_limits_for
                curr_month_str = CATALAN_MONTHS[avui.month - 1]
                
                # Filter df_desp for current year and month
                if 'any' in df_desp.columns and 'mes' in df_desp.columns:
                    df_curr = df_desp[(df_desp['any'].astype(str) == curr_year) & (df_desp['mes'].str.lower() == curr_month_str)].copy()
                    
                    if not df_curr.empty:
                        cat_col = 'Idcategoria' if 'Idcategoria' in df_curr.columns else ('Categoria' if 'Categoria' in df_curr.columns else None)
                        imp_col = 'Import càrrec' if 'Import càrrec' in df_curr.columns else ('import' if 'import' in df_curr.columns else None)
                        
                        if cat_col and imp_col:
                            df_curr[cat_col] = df_curr[cat_col].astype(str).str.strip().str.lower()
                            sum_menjar = df_curr[df_curr[cat_col] == 'menjar'][imp_col].sum()
                            sum_gasolina = df_curr[df_curr[cat_col] == 'gasolina'][imp_col].sum()
                            sum_restaurant = df_curr[df_curr[cat_col] == 'restaurant'][imp_col].sum()
                            sum_farmacia = df_curr[df_curr[cat_col] == 'farmàcia'][imp_col].sum()
                            sum_neteja = df_curr[df_curr[cat_col] == 'neteja'][imp_col].sum()
                            sum_varis = df_curr[df_curr[cat_col] == 'varis'][imp_col].sum()
                            
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
        except Exception as e_limits:
            print(f"Error alerta limits: {e_limits}")
                    
        # 4. Alerta Tiquets de súper pendents de desglossar
        try:
            tiquets_cfg = config.get("regles_alertes", {}).get("tiquets_pendents", {})
            if tiquets_cfg.get("mostrar_a_campana", True):
                df_target = st.session_state.get("df_desp")
                if df_target is None or df_target.empty:
                    df_target = df_desp
                    
                df_sup_check = st.session_state.get("df_super")
                if df_sup_check is None or df_sup_check.empty:
                    df_sup_check = df_super
                    
                if df_target is not None and not df_target.empty and 'ticketPendent' in df_target.columns:
                    pendents = df_target[df_target['ticketPendent'].astype(str).str.lower().str.strip().isin(['true', '1'])].copy()
                    if df_sup_check is not None and not df_sup_check.empty and 'IdDespesa' in df_sup_check.columns and not pendents.empty:
                        desglossats_ids = set(pd.to_numeric(df_sup_check['IdDespesa'], errors='coerce').dropna().astype(int).unique())
                        pendents = pendents[~pendents['ID_mov'].isin(desglossats_ids)]
                    if not pendents.empty:
                        n_pend = len(pendents)
                        t_details = []
                        for _, p_row in pendents.iterrows():
                            p_id = str(p_row.get('ID_mov', '')).replace('.0', '')
                            p_super = str(p_row.get('Idconcepte', '')).capitalize()
                            p_imp_raw = p_row.get('Import càrrec')
                            if p_imp_raw is None or pd.isna(p_imp_raw) or str(p_imp_raw).strip() == '':
                                p_imp_raw = p_row.get('import', '')
                            try:
                                p_imp = f"{float(p_imp_raw):.2f} €"
                            except Exception:
                                p_imp = f"{p_imp_raw} €"
                            t_details.append(f"Nº {p_id} ({p_super} - {p_imp})")
                        
                        alerts.append({
                            "type": "warning",
                            "icon": "🛒",
                            "title": f"Tiquet{'s' if n_pend > 1 else ''} pendent{'s' if n_pend > 1 else ''} de desglossar ({n_pend})",
                            "message": f"Tens {n_pend} tiquet{'s' if n_pend > 1 else ''} pendent{'s' if n_pend > 1 else ''} a Compres Súper: {', '.join(t_details)}."
                        })
        except Exception as e_tiquets:
            print(f"Error alerta tiquets pendents: {e_tiquets}")
            
        # 6. Alerta de Tasques de Manteniment pendents
        try:
            from core.manteniment_manager import load_registre_manteniment
            tasks = load_registre_manteniment()
            avui = datetime.today().date()
            for t in tasks:
                if str(t.get("acompliment", "No")).strip().lower() not in ["sí", "si", "true"]:
                    d_prev_str = str(t.get("dataManteniment", "")).strip()
                    d_prev = None
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            d_prev = datetime.strptime(d_prev_str, fmt).date()
                            break
                        except Exception:
                            pass
                    if d_prev:
                        delta = (d_prev - avui).days
                        alerta_a = t.get("alertaA", "Tothom")
                        tipus = t.get("tipus", "Manteniment")
                        feina = str(t.get("feina", "")).strip()
                        obs = str(t.get("observacions", "")).strip()
                        desc_text = feina if feina else obs
                        tit = f"[{tipus}] {desc_text[:30]}..." if len(desc_text) > 30 else f"[{tipus}] {desc_text or 'Tasca'}"
                        if delta < 0:
                            alerts.append({
                                "type": "error",
                                "icon": "🛠️",
                                "title": f"Manteniment vençut ({alerta_a})",
                                "message": f"{tit}: prevista per al {d_prev.strftime('%d/%m/%Y')} (vençuda fa {abs(delta)} dies)."
                            })
                        elif delta <= 2:
                            alerts.append({
                                "type": "warning",
                                "icon": "🛠️",
                                "title": f"Manteniment pendent ({alerta_a})",
                                "message": f"{tit}: prevista per al {d_prev.strftime('%d/%m/%Y')} ({'avui!' if delta==0 else f'en {delta} dies'})."
                            })
        except Exception as e_mant:
            pass
                        
    except Exception as e:
        print(f"Error generant alertes globals: {e}")
        
    return alerts

def _clear_alerts_cache():
    try:
        from core.db import load_dashboard_data
        load_dashboard_data.clear()
    except Exception:
        pass

get_global_alerts.clear = _clear_alerts_cache
