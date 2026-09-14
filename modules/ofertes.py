import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import get_supabase_client, fetch_all_supabase, load_ofertes, save_ofertes

def show():
    st.markdown("<h2 style='color:#f39c12; margin-top:-10px;'>Consulta d'Ofertes i Preus</h2>", unsafe_allow_html=True)
    
    pestanyes = st.tabs(["⚖️ Comparador i Emmagatzematge", "📖 Visor de Fulletons"])
    
    with pestanyes[0]:
        st.write("Aquesta secció permet comparar els preus històrics de la Llista de la Compra i el Rebost, així com introduir ofertes setmanals.")
        
        # --- CARREGAR DADES ---
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_prod = fetch_all_supabase(supabase, 'tb_productes')
        df_pendents = fetch_all_supabase(supabase, 'tb_pendents_compra')
        
        ofertes_list = load_ofertes()
        
        if df_prod.empty:
            st.info("No hi ha productes al catàleg.")
        else:
            col_filt1, col_filt2 = st.columns([1, 2])
            with col_filt1:
                filtre_vista = st.radio("👀 Filtrar productes per:", ["🛒 A la llista de compra", "📦 Tot el rebost"], horizontal=True)
                
            with col_filt2:
                cerca = st.text_input("🔍 Buscar producte...")

            # --- FILTRAR DADES ---
            if filtre_vista == "🛒 A la llista de compra":
                if df_pendents.empty:
                    st.warning("La llista de compra està buida.")
                    df_view = pd.DataFrame()
                else:
                    id_pendents = df_pendents['idProducte'].tolist()
                    df_view = df_prod[df_prod['idProducte'].isin(id_pendents)]
            else:
                df_view = df_prod.copy()
                
            if cerca:
                df_view = df_view[df_view['nom_estandard'].str.contains(cerca, case=False, na=False)]
                
            if not df_view.empty:
                st.markdown("### 📊 Comparador de Preus")
                
                # Afegir dades d'ofertes al dataframe per visualitzar
                ofertes_map = {}
                for of in ofertes_list:
                    # Agafar només ofertes vigents (data de fi > avui)
                    # O si no tenen data_fi
                    try:
                        if of.get("data_fi"):
                            dfi = datetime.strptime(of["data_fi"], "%Y-%m-%d")
                            if dfi < datetime.now():
                                continue # Caducada
                    except Exception:
                        pass
                    
                    pid = of.get("id_producte")
                    if pid:
                        txt_oferta = f"🌟 {of.get('tipus', 'Oferta')}: {of.get('preu_oferta', '')}€ ({of.get('supermercat', '')})"
                        if pid in ofertes_map:
                            ofertes_map[pid] += " | " + txt_oferta
                        else:
                            ofertes_map[pid] = txt_oferta

                df_view['Ofertes Actives'] = df_view['idProducte'].map(ofertes_map).fillna("-")
                
                # Seleccionar columnes a mostrar
                cols_to_show = ['nom_estandard', 'familia', 'super_habitual', 'preuUnit', 'Ofertes Actives']
                df_show = df_view[cols_to_show].copy()
                df_show.rename(columns={
                    'nom_estandard': 'Producte',
                    'familia': 'Família',
                    'super_habitual': 'Súper Habitual',
                    'preuUnit': 'Últim Preu (€)'
                }, inplace=True)
                
                st.dataframe(df_show, use_container_width=True, hide_index=True)
                
            # --- REGISTRAR OFERTA ---
            st.markdown("---")
            st.markdown("### 🏷️ Registrar nova oferta")
            
            with st.form("form_oferta"):
                col_form1, col_form2, col_form3 = st.columns(3)
                with col_form1:
                    productes_list = sorted(df_prod['nom_estandard'].dropna().unique().tolist())
                    prod_sel = st.selectbox("Producte", [""] + productes_list)
                with col_form2:
                    supers = ["Mercadona", "Bonpreu", "Aldi", "Lidl", "Consum", "Dia", "AreaGuissona", "Novavenda", "El Corte Inglés", "Altres"]
                    super_sel = st.selectbox("Supermercat", supers)
                with col_form3:
                    tipus_sel = st.selectbox("Tipus d'oferta", ["Preu rebaixat", "3x2", "2a unitat %", "Altres volumètriques"])
                    
                col_form4, col_form5, col_form6 = st.columns(3)
                with col_form4:
                    preu_of = st.number_input("Preu de l'oferta (€)", min_value=0.0, step=0.01, format="%.2f")
                with col_form5:
                    data_fi = st.date_input("Fins quan (Data Fi)?")
                with col_form6:
                    st.write("")
                    st.write("")
                    submitted = st.form_submit_button("Desar Oferta", type="primary", use_container_width=True)
                    
                if submitted:
                    if not prod_sel:
                        st.error("Has de seleccionar un producte.")
                    else:
                        pid_match = df_prod[df_prod['nom_estandard'] == prod_sel]['idProducte']
                        if not pid_match.empty:
                            pid = int(pid_match.values[0])
                            
                            nova_oferta = {
                                "id_producte": pid,
                                "supermercat": super_sel,
                                "tipus": tipus_sel,
                                "preu_oferta": preu_of,
                                "data_fi": data_fi.strftime("%Y-%m-%d") if data_fi else ""
                            }
                            
                            ofertes_list.append(nova_oferta)
                            if save_ofertes(ofertes_list):
                                st.success(f"✅ Oferta desada per {prod_sel}!")
                                st.rerun()
                            else:
                                st.error("Error al desar l'oferta.")

    with pestanyes[1]:
        st.markdown("### 📖 Fulletons i Catàlegs Setmanals")
        st.write("Accés directe als catàlegs oficials d'ofertes dels supermercats habituals:")
        
        c1, c2, c3, c4 = st.columns(4)
        
        c1.markdown("""
        <div style="background-color:#007B22; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://info.mercadona.es/ca/supermercats" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Mercadona</a>
        </div>
        """, unsafe_allow_html=True)
        
        c2.markdown("""
        <div style="background-color:#E30613; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.bonpreuesclat.cat/ca/promocions" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Bonpreu/Esclat</a>
        </div>
        """, unsafe_allow_html=True)
        
        c3.markdown("""
        <div style="background-color:#0050AA; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.lidl.es/es/folletos-promociones/s1072" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Lidl</a>
        </div>
        """, unsafe_allow_html=True)
        
        c4.markdown("""
        <div style="background-color:#003B7E; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.aldi.es/folletos-promociones.html" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Aldi</a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        c5, c6, c7, c8 = st.columns(4)
        
        c5.markdown("""
        <div style="background-color:#F58220; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.consum.es/ca/ofertes" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Consum</a>
        </div>
        """, unsafe_allow_html=True)
        
        c6.markdown("""
        <div style="background-color:#D81F26; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.dia.es/compra-online/ofertas" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Dia</a>
        </div>
        """, unsafe_allow_html=True)
        
        c7.markdown("""
        <div style="background-color:#D31145; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.bonarea.com/ca/ofertes" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 AreaGuissona</a>
        </div>
        """, unsafe_allow_html=True)

        c8.markdown("""
        <div style="background-color:#E98300; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://novavenda.com/ofertes/" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 Novavenda</a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        c9, c10, c11, c12 = st.columns(4)
        
        c9.markdown("""
        <div style="background-color:#00593B; border-radius:10px; padding:20px; text-align:center; margin-bottom:20px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            <a href="https://www.elcorteingles.es/supermercado/promociones/" target="_blank" style="color:white; text-decoration:none; font-weight:bold; font-size:18px; display:block;">🛒 El Corte Inglés</a>
        </div>
        """, unsafe_allow_html=True)

def render():
    st.markdown('''
        <style>
        .back-button-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 0rem;
            padding-right: 2rem;
            margin-top: -2rem;
        }
        .back-button {
            margin-left: auto;
        }
        .back-button .stButton > button {
            background-color: #ffffff;
            color: #1e293b;
            border: 1px solid #cbd5e1;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            font-weight: 500;
        }
        .back-button .stButton > button:hover {
            border-color: #94a3b8;
            background-color: #f8fafc;
        }
        </style>
    ''', unsafe_allow_html=True)
    
    col_header1, col_header2 = st.columns([9.2, 0.8])
    with col_header2:
        st.markdown('<div class="back-button">', unsafe_allow_html=True)
        auth_token = st.query_params.get("auth", "") or st.session_state.get("auth_token", "")
        auth_suffix = f"&auth={auth_token}" if auth_token else ""
        if st.button("🏡 Inici", key="btn_inici_ofertes"):
            st.session_state.current_module = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    show()
