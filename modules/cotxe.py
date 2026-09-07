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

    col_t1, col_t2 = st.columns([8.5, 1.5], vertical_alignment="center")
    with col_t1:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>🚗 Cotxe i Transport</h2>", unsafe_allow_html=True)
    with col_t2:
        if st.button("🔙 Tornar a l'inici", use_container_width=True):
            st.session_state.current_module = None
            st.rerun()

    st.write("---")

    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    
    # Ensure data is loaded
    if "df_km" not in st.session_state or "df_gas" not in st.session_state:
        dfs = load_dashboard_data(get_csv_mtimes())
        (st.session_state["df_desp"], st.session_state["df_ing"], st.session_state["df_super"],
         st.session_state["df_gas"], st.session_state["df_km"], st.session_state["df_hip"],
         st.session_state["df_cartera"], st.session_state["df_est"], st.session_state["df_limits"],
         st.session_state["df_pag"]) = dfs

    df_km = st.session_state["df_km"]
    df_gas = st.session_state["df_gas"]

    tab_km, tab_repostatge, tab_oli, tab_consum = st.tabs(["🛣️ Registre Km i Rutes", "⛽ Repostatge", "🔧 Canvi d'Oli", "📊 Consum"])

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
            last_km = float(df_km_car.dropna(subset=['contador'])['contador'].iloc[0])

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
                new_row = {
                    'idRuta': int(df_km['idRuta'].max() + 1) if not df_km.empty and 'idRuta' in df_km.columns else 1,
                    'cotxe': cotxe_val,
                    'data': data_val.strftime('%d/%m/%Y'),
                    'ruta': ruta_val.strip(),
                    'contador': int(contador_val),
                    'km': int(km_val)
                }
                append_to_db(pd.DataFrame([new_row]), 'kmCotxe', 'df_km')
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
            if 'parsed_date' not in df_km_show.columns:
                df_km_show['parsed_date'] = df_km_show['data'].apply(parse_excel_date)
            df_km_show = df_km_show.sort_values(by=['parsed_date', 'idRuta'], ascending=[False, False], errors='ignore')
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
            df_gas_work['preu_l_val'] = clean_numeric(df_gas_work.get('€/l', 0))
            
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
            cols_g = [c for c in ['data', 'cotxe', 'lloc', 'import', '€/l', 'litres'] if c in df_gas_work.columns]
            df_gas_show = df_gas_work[cols_g].copy()
            df_gas_show.rename(columns={'data': 'Data', 'cotxe': 'Cotxe', 'lloc': 'Benzinera', 'import': 'Import (€)', '€/l': 'Preu/L', 'litres': 'Litres'}, inplace=True)
            
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
        st.markdown("<h4 style='color:#f39c12;'>🔧 Estat del Canvi d'Oli</h4>", unsafe_allow_html=True)
        
        car_kms_actuals = 0.0
        if not df_km.empty and 'contador' in df_km.columns:
            car_kms_actuals = pd.to_numeric(df_km['contador'], errors='coerce').max()
            if pd.isna(car_kms_actuals): car_kms_actuals = 0.0

        if "kms_canvi_oli" not in st.session_state:
            st.session_state["kms_canvi_oli"] = 150000.0

        col_oil1, col_oil2, col_oil3 = st.columns([1, 1, 1])
        with col_oil1:
            st.metric("Kms actuals del cotxe", f"{int(car_kms_actuals):,}")
        with col_oil2:
            st.session_state["kms_canvi_oli"] = st.number_input("Objectiu proper canvi d'oli (km)", value=float(st.session_state["kms_canvi_oli"]), step=1000.0)
        with col_oil3:
            kms_left = st.session_state["kms_canvi_oli"] - car_kms_actuals
            st.metric("Kms restants", f"{int(kms_left):,}", delta=f"{int(kms_left)} km per al canvi", delta_color="normal" if kms_left > 1000 else "inverse")

        if kms_left <= 1000:
            st.warning(f"⚠️ Atenció: Queden només {int(kms_left)} km per al proper canvi d'oli!")
        else:
            st.success("✅ El vehicle està dins dels marges òptims de quilometratge per a l'oli.")

    # ----------------------------------------------------
    # TAB 4: CONSUM ANUAL
    # ----------------------------------------------------
    with tab_consum:
        st.markdown("<h4 style='color:#f39c12;'>📊 Consum Mitjà Anual (L/100km)</h4>", unsafe_allow_html=True)

        if not df_gas.empty and not df_km.empty:
            df_gas_work = df_gas.copy()
            df_km_work = df_km.copy()
            df_gas_work['parsed_date'] = df_gas_work['data'].apply(parse_excel_date)
            df_km_work['parsed_date'] = df_km_work['data'].apply(parse_excel_date)

            df_gas_tivoli = df_gas_work[df_gas_work['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_gas_work.columns else df_gas_work
            df_km_tivoli = df_km_work[df_km_work['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km_work.columns else df_km_work

            df_km_tivoli_valid = df_km_tivoli.dropna(subset=['contador', 'parsed_date'])

            if not df_gas_tivoli.empty and not df_km_tivoli_valid.empty:
                gas_yr = df_gas_tivoli.groupby(df_gas_tivoli['parsed_date'].dt.year)['litres'].sum()
                km_yr = df_km_tivoli_valid.groupby(df_km_tivoli_valid['parsed_date'].dt.year)['contador'].agg(lambda x: x.max() - x.min())
                km_yr = km_yr.replace(0, pd.NA)

                consumption = ((gas_yr / km_yr) * 100).dropna().reset_index()
                consumption.columns = ['Any', 'L/100km']
                consumption['Any'] = consumption['Any'].astype(str)

                if not consumption.empty:
                    fig_line = px.bar(consumption, x='Any', y='L/100km', text_auto='.2f', color_discrete_sequence=['#f39c12'])
                    fig_line.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f8fafc'),
                        xaxis=dict(gridcolor='#334155'),
                        yaxis=dict(gridcolor='#334155'),
                        margin=dict(t=20, b=20, l=10, r=10)
                    )
                    st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("No hi ha prou dades per calcular el consum anual.")
            else:
                st.info("No s'han trobat suficients dades de quilometratge per calcular el consum.")
        else:
            st.info("No hi ha dades de gasolina o quilometratge registrades.")
