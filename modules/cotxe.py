import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from core.db import (
    get_supabase_client, fetch_all_supabase, parse_excel_date, clean_numeric,
    get_config_routes, add_route_to_config, init_routes_config, append_to_db,
    save_to_csv, load_dashboard_data, get_csv_mtimes
)

def render():
    # Hide header anchors
    st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    a[data-testid="stHeaderActionLink"] {
        display: none !important;
    }
    .stHeading a, h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    from modules.avatar_widget import render_header_with_avatar
    render_header_with_avatar("<div style='font-size: 1.8rem; font-weight: bold; color:#f39c12; margin-top:0;'>🚗 Cotxe</div>", "cotxe")

    st.write("---")

    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    
    # Ensure data is loaded
    from core.db import ensure_session_dfs
    ensure_session_dfs()

    df_km = st.session_state.get("df_km", pd.DataFrame())
    df_gas = st.session_state.get("df_gas", pd.DataFrame())

    tab_km, tab_repostatge, tab_oli, tab_consum = st.tabs(["🛣️ Km i Rutes", "⛽ Repostatge", "🔧 Manteniment (Oli i Rodes)", "📊 Consum"])

    # ----------------------------------------------------
    # TAB 1: REGISTRE DE KM I RUTES
    # ----------------------------------------------------
    with tab_km:
        st.markdown("<h4 style='color:#f39c12;'>➕ Nou Registre de Quilòmetres</h4>", unsafe_allow_html=True)
        
        km_version = st.session_state.get("km_version", 0)
        cotxe_val = "tívoli"
        
        # Last odometer
        last_km = 0.0
        df_km_car = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km
        if not df_km_car.empty:
            df_km_car_sorted = df_km_car.copy()
            df_km_car_sorted['parsed_date'] = df_km_car_sorted['data'].apply(parse_excel_date)
            df_km_car_sorted = df_km_car_sorted.sort_values(by='parsed_date', ascending=False)
            last_km = float(df_km_car_sorted.dropna(subset=['contador'])['contador'].iloc[0])

        r1_col1, r1_col2, r1_col3 = st.columns([2, 4, 4])
        with r1_col1:
            data_val = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key=f"km_data_{km_version}")
        with r1_col2:
            contador_val = st.number_input("Lectura Odòmetre (km totals)", min_value=0.0, value=None, placeholder=f"Última: {last_km:g}", step=1.0, key=f"km_odo_{km_version}")
        with r1_col3:
            km_val = max(0.0, contador_val - last_km) if contador_val is not None else 0.0
            st.text_input("Kilòmetres del trajecte", value=f"{km_val:g}", disabled=True)

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
                save_ruta_template = st.checkbox("💾 Afegir a la llista de rutes", value=True, key=f"km_save_ruta_{km_version}")
        else:
            with r2_col2:
                st.write("")
            ruta_val = ruta_sel

        col_btns = st.columns([2.5, 2.0, 7.5])
        with col_btns[0]:
            submitted = st.button("💾 Desar Kilòmetres", type="primary", use_container_width=True)
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key=f"cancel_km_{km_version}", use_container_width=True)
            
        if cancelled:
            st.session_state["km_version"] = st.session_state.get("km_version", 0) + 1
            st.rerun()
            
        if submitted:
            if contador_val is None or contador_val <= 0:
                st.error("⚠️ Heu d'introduir una lectura d'odòmetre vàlida.")
            elif not ruta_val or not ruta_val.strip():
                st.error("⚠️ Heu d'especificar la ruta.")
            else:
                # Consultem l'ID màxim directament al núvol per esquivar la memòria cau
                max_id = 1
                try:
                    res = supabase.table('kmCotxe').select('idRuta').order('idRuta', desc=True).limit(1).execute()
                    if res.data and len(res.data) > 0:
                        max_id = int(res.data[0]['idRuta']) + 1
                except:
                    max_id = int(df_km['idRuta'].max() + 1) if not df_km.empty and 'idRuta' in df_km.columns else 1

                new_row = {
                    'idRuta': max_id,
                    'cotxe': cotxe_val,
                    'data': data_val.strftime('%d/%m/%Y'),
                    'ruta': ruta_val.strip(),
                    'contador': int(contador_val),
                    'km': int(km_val)
                }
                ok = append_to_db(pd.DataFrame([new_row]), 'kmCotxe', 'df_km')
                if ok:
                    if current_sel == "Nova ruta...":
                        if st.session_state.get(f"km_save_ruta_{km_version}", True):
                            add_route_to_config(ruta_val.strip(), df_km)
                        else:
                            init_routes_config(df_km)
                    st.success("Ruta desada correctament!")
                    st.session_state["km_version"] = st.session_state.get("km_version", 0) + 1
                    st.rerun()

        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#f39c12;'>📋 Històric de Rutes Registrades</h4>", unsafe_allow_html=True)
        if not df_km.empty:
            df_km_show = df_km.copy()
            df_km_show['parsed_date'] = df_km_show['data'].apply(parse_excel_date)
            sort_cols = [c for c in ['parsed_date', 'idRuta'] if c in df_km_show.columns]
            if sort_cols:
                df_km_show = df_km_show.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
            cols_avail = [c for c in ['data', 'cotxe', 'ruta', 'km', 'contador'] if c in df_km_show.columns]
            df_km_show = df_km_show[cols_avail].head(50)
            df_km_show.rename(columns={'data': 'Data', 'cotxe': 'Cotxe', 'ruta': 'Ruta', 'km': 'Km trajecte', 'contador': 'Odòmetre'}, inplace=True)
            st.dataframe(df_km_show, use_container_width=True, hide_index=True)
        else:
            st.info("No hi ha rutes registrades.")

    # ----------------------------------------------------
    # TAB 2: REPOSTATGE (BBDD GASOLINA)
    # ----------------------------------------------------
    with tab_repostatge:
        st.markdown("<h4 style='color:#f39c12;'>⛽ Històric de Repostatges de Gasolina</h4>", unsafe_allow_html=True)
        st.caption("💡 Les dades de proveïment s'alimenten automàticament des del formulari d'Ingressos / Despeses en seleccionar la categoria Gasolina.")
        
        if not df_gas.empty:
            df_gas_work = df_gas.copy()
            df_gas_work['parsed_date'] = df_gas_work['data'].apply(parse_excel_date)
            df_gas_work['import_val'] = clean_numeric(df_gas_work.get('import', 0))
            df_gas_work['litres_val'] = clean_numeric(df_gas_work.get('litres', 0))
            df_gas_work['preu_l_val'] = clean_numeric(df_gas_work.get('euros/litre', df_gas_work.get('€/l', 0)))
            
            # Sort descending by date and idGasolina
            sort_cols = [c for c in ['parsed_date', 'idGasolina'] if c in df_gas_work.columns]
            df_gas_work = df_gas_work.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
            
            # Metrics: Preu últim repostatge, Preu més alt, Preu més baix
            valid_preus = df_gas_work[df_gas_work['preu_l_val'] > 0.0]
            
            ultim_preu = df_gas_work.iloc[0]['preu_l_val'] if not df_gas_work.empty else 0.0
            max_preu = valid_preus['preu_l_val'].max() if not valid_preus.empty else 0.0
            min_preu = valid_preus['preu_l_val'].min() if not valid_preus.empty else 0.0
            
            c_k1, c_k2, c_k3 = st.columns(3)
            with c_k1:
                st.metric("Preu Últim Repostatge", f"{ultim_preu:.3f} €/l")
            with c_k2:
                st.metric("Preu Més Alt", f"{max_preu:.3f} €/l")
            with c_k3:
                st.metric("Preu Més Baix", f"{min_preu:.3f} €/l")

            st.write("")
            cols_g = [c for c in ['data', 'cotxe', 'lloc', 'import', 'euros/litre', '€/l', 'litres'] if c in df_gas_work.columns]
            df_gas_show = df_gas_work[cols_g].copy()
            df_gas_show.rename(columns={'data': 'Data', 'cotxe': 'Cotxe', 'lloc': 'Benzinera', 'import': 'Import (€)', 'euros/litre': 'Preu/L', '€/l': 'Preu/L', 'litres': 'Litres'}, inplace=True)
            
            st.dataframe(
                df_gas_show.style.format({'Import (€)': '{:,.2f} €', 'Preu/L': '{:.3f} €/l', 'Litres': '{:.2f} l'}, na_rep=""),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hi ha registres de repostatge a la base de dades.")

    # ----------------------------------------------------
    # TAB 3: CANVI D'OLI I MANTENIMENT
    # ----------------------------------------------------
    with tab_oli:
        from core.config_manager import load_app_config, save_app_config, DEFAULT_CONFIG
        import copy

        car_kms_actuals = 0.0
        df_km_oli = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km
        if not df_km_oli.empty and 'contador' in df_km_oli.columns:
            car_kms_actuals = pd.to_numeric(df_km_oli['contador'], errors='coerce').max()
            if pd.isna(car_kms_actuals): car_kms_actuals = 0.0

        _DEF_MANT = {
            "oli": {"ultim_canvi_km": 30000, "interval_km": 16000, "data_ultim_canvi": ""},
            "rodes": {"ultim_canvi_km": 30000, "interval_km": 40000, "quantes_rodes": 4, "posicio": "Totes 4", "data_ultim_canvi": ""},
            "historic": []
        }
        app_cfg = load_app_config()
        mant = copy.deepcopy(app_cfg.get("manteniment_cotxe") or DEFAULT_CONFIG.get("manteniment_cotxe") or _DEF_MANT)
        mant.setdefault("oli", copy.deepcopy(_DEF_MANT["oli"]))
        mant.setdefault("rodes", copy.deepcopy(_DEF_MANT["rodes"]))
        mant.setdefault("historic", [])

        def _save_mant(new_mant):
            cfg = copy.deepcopy(load_app_config())
            cfg["manteniment_cotxe"] = new_mant
            save_app_config(cfg)
            try:
                from core.alerts import get_global_alerts
                get_global_alerts.clear()
            except Exception:
                pass

        def _estat(left, interval):
            usat = 1 - (left / interval) if interval else 1
            usat = min(max(usat, 0.0), 1.0)
            st.progress(usat, text=f"Desgast: {usat*100:.0f}%")
            if left <= 0:
                st.error(f"🚨 Canvi superat per {int(abs(left)):,} km!")
            elif left <= 1000:
                st.warning(f"⚠️ Queden només {int(left):,} km!")
            else:
                st.success(f"✅ Tot correcte. Queden {int(left):,} km.")

        # ---------- OLI ----------
        oli = mant["oli"]
        oli_last = float(oli.get("ultim_canvi_km", 30000))
        oli_int = float(oli.get("interval_km", 16000))
        oli_next = oli_last + oli_int
        oli_left = oli_next - car_kms_actuals

        st.markdown("<h4 style='color:#f39c12;'>🛢️ Canvi d'Oli</h4>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kms actuals", f"{int(car_kms_actuals):,}")
        c2.metric("Últim canvi", f"{int(oli_last):,} km", help=oli.get("data_ultim_canvi") or None)
        c3.metric("Proper canvi", f"{int(oli_next):,} km", help=f"{int(oli_last):,} + {int(oli_int):,}")
        c4.metric("Kms restants", f"{int(oli_left):,}")
        _estat(oli_left, oli_int)

        with st.expander("✏️ Registrar canvi d'oli"):
            with st.form("form_oli"):
                f1, f2, f3 = st.columns(3)
                n_km = f1.number_input("Km del canvi", min_value=0, value=int(oli_last), step=100)
                n_int = f2.number_input("Interval (km)", min_value=1000, value=int(oli_int), step=1000)
                n_data = f3.date_input("Data", value=datetime.today(), format="DD/MM/YYYY")
                n_nota = st.text_input("Observacions", value="Oli i filtre")
                afegir_hist = st.checkbox("Afegir a l'històric", value=True)
                if st.form_submit_button("💾 Desar canvi d'oli", type="primary"):
                    d = n_data.strftime("%d/%m/%Y")
                    mant["oli"] = {"ultim_canvi_km": int(n_km), "interval_km": int(n_int), "data_ultim_canvi": d}
                    if afegir_hist:
                        mant["historic"].append({"data": d, "tipus": "Oli", "km": int(n_km), "rodes": "", "detall": n_nota})
                    _save_mant(mant)
                    st.success(f"Desat! Proper canvi als {int(n_km + n_int):,} km.")
                    st.rerun()

        st.write("---")

        # ---------- RODES ----------
        rodes = mant["rodes"]
        r_last = float(rodes.get("ultim_canvi_km", 30000))
        r_int = float(rodes.get("interval_km", 40000))
        r_next = r_last + r_int
        r_left = r_next - car_kms_actuals

        st.markdown("<h4 style='color:#f39c12;'>🛞 Canvi de Rodes</h4>", unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Últim canvi", f"{int(r_last):,} km", help=rodes.get("data_ultim_canvi") or None)
        d2.metric("Rodes canviades", f"{rodes.get('quantes_rodes', 4)}", help=rodes.get("posicio", ""))
        d3.metric("Proper canvi", f"{int(r_next):,} km")
        d4.metric("Kms restants", f"{int(r_left):,}")
        _estat(r_left, r_int)

        with st.expander("✏️ Registrar canvi de rodes"):
            with st.form("form_rodes"):
                g1, g2, g3 = st.columns(3)
                nr_km = g1.number_input("Km del canvi", min_value=0, value=int(r_last), step=100, key="r_km")
                nr_q = g2.radio("Quantes rodes?", [1, 2, 4], index=[1, 2, 4].index(int(rodes.get("quantes_rodes", 4))) if int(rodes.get("quantes_rodes", 4)) in [1, 2, 4] else 2, horizontal=True)
                nr_pos = g3.selectbox("Posició", ["Totes 4", "Davanteres", "Posteriors", "Davantera esquerra", "Davantera dreta", "Posterior esquerra", "Posterior dreta"])
                h1, h2 = st.columns(2)
                nr_int = h1.number_input("Interval estimat (km)", min_value=1000, value=int(r_int), step=1000)
                nr_data = h2.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key="r_data")
                nr_nota = st.text_input("Observacions (marca, model...)", key="r_nota")
                if st.form_submit_button("💾 Desar canvi de rodes", type="primary"):
                    d = nr_data.strftime("%d/%m/%Y")
                    mant["rodes"] = {"ultim_canvi_km": int(nr_km), "interval_km": int(nr_int), "quantes_rodes": int(nr_q), "posicio": nr_pos, "data_ultim_canvi": d}
                    mant["historic"].append({"data": d, "tipus": "Rodes", "km": int(nr_km), "rodes": f"{nr_q} ({nr_pos})", "detall": nr_nota})
                    _save_mant(mant)
                    st.success("Canvi de rodes desat!")
                    st.rerun()

        st.write("---")

        # ---------- HISTÒRIC ----------
        st.markdown("<h4 style='color:#f39c12;'>📋 Històric de Manteniment</h4>", unsafe_allow_html=True)
        if mant["historic"]:
            df_h = pd.DataFrame(mant["historic"])
            df_h = df_h.sort_values("km", ascending=False).reset_index(drop=True)
            df_h.insert(0, "Eliminar", False)
            edited = st.data_editor(df_h, hide_index=True, use_container_width=True, disabled=[c for c in df_h.columns if c != "Eliminar"], key="hist_mant")
            if edited["Eliminar"].any() and st.button("🗑️ Eliminar seleccionats"):
                mant["historic"] = edited[~edited["Eliminar"]].drop(columns=["Eliminar"]).to_dict("records")
                _save_mant(mant)
                st.rerun()
        else:
            st.info("Encara no hi ha cap manteniment registrat.")

    # ----------------------------------------------------
    # TAB 4: CONSUM ANUAL
    # ----------------------------------------------------
    with tab_consum:
        st.markdown("<h4 style='color:#f39c12;'>📊 Consum Mitjà Anual (L/100km)</h4>", unsafe_allow_html=True)

        if not df_gas.empty and not df_km.empty:
            df_gas_work = df_gas.copy()
            df_km_work = df_km.copy()
            df_gas_work['parsed_date'] = df_gas_work['data'].apply(parse_excel_date)
            df_gas_work['litres_val'] = clean_numeric(df_gas_work.get('litres', 0))
            df_km_work['parsed_date'] = df_km_work['data'].apply(parse_excel_date)

            df_gas_tivoli = df_gas_work[df_gas_work['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_gas_work.columns else df_gas_work
            df_km_tivoli = df_km_work[df_km_work['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km_work.columns else df_km_work

            df_km_tivoli_valid = df_km_tivoli.dropna(subset=['contador', 'parsed_date']).copy()
            df_km_tivoli_valid['contador_val'] = pd.to_numeric(df_km_tivoli_valid['contador'], errors='coerce')
            df_km_tivoli_valid = df_km_tivoli_valid.dropna(subset=['contador_val'])

            if not df_gas_tivoli.empty and not df_km_tivoli_valid.empty:
                gas_yr = df_gas_tivoli.groupby(df_gas_tivoli['parsed_date'].dt.year)['litres_val'].sum()
                km_yr = df_km_tivoli_valid.groupby(df_km_tivoli_valid['parsed_date'].dt.year)['contador_val'].agg(lambda x: x.max() - x.min())
                km_yr = km_yr.replace(0, pd.NA)

                consumption = ((gas_yr / km_yr) * 100).dropna().reset_index()
                consumption.columns = ['Any', 'L/100km']
                consumption['Any'] = consumption['Any'].astype(str)

                if not consumption.empty:
                    fig_line = px.bar(consumption, x='Any', y='L/100km', text_auto='.2f', color_discrete_sequence=['#f39c12'])
                    fig_line.update_traces(textfont_size=20, textposition='outside', cliponaxis=False)
                    fig_line.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f8fafc'),
                        xaxis=dict(gridcolor='#334155', type='category'),
                        yaxis=dict(gridcolor='#334155'),
                        margin=dict(t=40, b=20, l=10, r=10)
                    )
                    st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("No hi ha prou dades per calcular el consum anual.")
            else:
                st.info("No s'han trobat suficients dades de quilometratge per calcular el consum.")
        else:
            st.info("No hi ha dades de gasolina o quilometratge registrades.")
