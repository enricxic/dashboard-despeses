import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.db import get_supabase_client, fetch_all_supabase, parse_excel_date

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
    
    # Fetch car data
    try:
        df_gas = fetch_all_supabase(supabase, 'gasolina')
        df_km = fetch_all_supabase(supabase, 'kmCotxe')
    except Exception as e:
        st.error(f"Error carregant dades del vehicle: {e}")
        return

    # Calculate actual kms
    car_kms_actuals = 0.0
    if not df_km.empty and 'contador' in df_km.columns:
        car_kms_actuals = pd.to_numeric(df_km['contador'], errors='coerce').max()
        if pd.isna(car_kms_actuals):
            car_kms_actuals = 0.0

    if "kms_canvi_oli" not in st.session_state:
        st.session_state["kms_canvi_oli"] = 150000.0

    # 🔧 Oil change section
    st.markdown("<h3 style='color:#f39c12;'>🔧 Canvi d'oli cotxe</h3>", unsafe_allow_html=True)
    col_oil1, col_oil2, col_oil3 = st.columns([1, 1, 1])
    with col_oil1:
        st.metric("Kms actuals", f"{int(car_kms_actuals):,}")
    with col_oil2:
        st.session_state["kms_canvi_oli"] = st.number_input("Kms canvi oli", value=float(st.session_state["kms_canvi_oli"]), step=1000.0)
    with col_oil3:
        kms_left = st.session_state["kms_canvi_oli"] - car_kms_actuals
        st.metric("Canvi dintre", f"{int(kms_left):,}", delta=f"{int(kms_left)} km restants", delta_color="normal" if kms_left > 500 else "inverse")

    st.write("")
    st.markdown("<h3 style='color:#f39c12;'>⛽ Consum Cotxe (L/100km)</h3>", unsafe_allow_html=True)

    if not df_gas.empty and not df_km.empty:
        df_gas['parsed_date'] = df_gas['data'].apply(parse_excel_date)
        df_km['parsed_date'] = df_km['data'].apply(parse_excel_date)

        df_gas_tivoli = df_gas[df_gas['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_gas.columns else df_gas
        df_km_tivoli = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km

        df_km_tivoli_valid = df_km_tivoli.dropna(subset=['contador', 'parsed_date'])

        if not df_gas_tivoli.empty and not df_km_tivoli_valid.empty:
            gas_yr = df_gas_tivoli.groupby(df_gas_tivoli['parsed_date'].dt.year)['litres'].sum()

            # Càlcul de km reals recorreguts per any (màxim contador - mínim contador)
            km_yr = df_km_tivoli_valid.groupby(df_km_tivoli_valid['parsed_date'].dt.year)['contador'].agg(lambda x: x.max() - x.min())
            km_yr = km_yr.replace(0, pd.NA) # Evitar divisió per zero

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
            st.info("No s'han trobat dades de gasolina o quilometratge del vehicle.")
    else:
        st.info("No hi ha dades de gasolina o quilometratge registrades.")
