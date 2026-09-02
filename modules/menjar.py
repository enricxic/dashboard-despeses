import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from core.db import get_supabase_client, fetch_all_supabase, delete_from_db, update_db_row, log_action, insert_db_row
import pytz
import re
import urllib.parse

def clear_form_state(prefix: str):
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]

def render():
    st.title("🍽️ Mòdul de Menjar")
    
    tab_rebost, tab_receptes = st.tabs(["📦 Rebost / Stock", "🍲 Receptari & Menús"])
    
    with tab_rebost:
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_prods = fetch_all_supabase(supabase, 'tb_productes')
            
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.markdown("<h2 style='color:#3498db;'>📦 Control d'Stock (El teu Rebost)</h2>", unsafe_allow_html=True)
            with col_t2:
                st.write("") # Spacer
                if st.button("📋 Inventari", type="primary", use_container_width=True):
                    modal_inventari(df_prods)
                    
            # ================= LECTOR DE CODIS DE BARRES =================
            st.markdown("### 📷 Escanejar Codi de Barres (Càmera nativa)")
            if True:
                st.write("Clica el botó de sota per obrir la càmera del teu mòbil (o pujar una foto) per escanejar un codi de barres.")
                img_file = st.file_uploader("Fes una foto al codi de barres", type=["png", "jpg", "jpeg"], key="barcode_camera", label_visibility="collapsed")
                if img_file is not None:
                    try:
                        from pyzbar.pyzbar import decode
                        from PIL import Image
                        image = Image.open(img_file)
                        decoded_objects = decode(image)
                        
                        if not decoded_objects:
                            st.error("No s'ha detectat cap codi de barres a la imatge. Prova d'enfocar millor i que hi hagi bona llum.")
                        else:
                            barcode = decoded_objects[0].data.decode('utf-8')
                            barcode_type = decoded_objects[0].type
                            
                            st.success(f"✅ Codi llegit: **{barcode}** ({barcode_type})")
                            
                            # Lookup in database
                            res_codi = supabase.table('tb_codis_barres').select('id_producte').eq('codi_barres', barcode).execute()
                            
                            if res_codi.data:
                                # Found!
                                id_prod = res_codi.data[0]['id_producte']
                                res_prod = supabase.table('tb_productes').select('idProducte, nom_estandard, familia, stock_actual').eq('idProducte', id_prod).execute()
                                
                                if res_prod.data:
                                    prod = res_prod.data[0]
                                    st.info(f"Aquest codi correspon a: **{prod['nom_estandard']}** (Stock actual: {prod['stock_actual']})")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("➕ Afegir 1 a l'stock", type="primary", use_container_width=True, key=f"add_{barcode}"):
                                            new_stock = float(prod['stock_actual']) + 1.0
                                            supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', id_prod).execute()
                                            st.success(f"Afegit! Nou stock: {new_stock}")
                                            st.cache_data.clear()
                                            st.rerun()
                                    with col2:
                                        if st.button("➖ Gastar 1 de l'stock", type="secondary", use_container_width=True, key=f"sub_{barcode}"):
                                            new_stock = max(0.0, float(prod['stock_actual']) - 1.0)
                                            supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', id_prod).execute()
                                            st.success(f"Gastat! Nou stock: {new_stock}")
                                            st.cache_data.clear()
                                            st.rerun()
                            else:
                                # Not found. Ask to associate.
                                st.warning("Aquest codi no està associat a cap producte del teu rebost.")
                                if not df_prods.empty:
                                    df_p = df_prods.sort_values(by=['familia', 'nom_estandard'])
                                    prod_options = df_p.apply(lambda r: f"{r['nom_estandard']} ({r['familia']})", axis=1).tolist()
                                    prod_ids = df_p['idProducte'].tolist()
                                    
                                    selected_idx = st.selectbox("A quin producte correspon?", range(len(prod_options)), format_func=lambda i: prod_options[i])
                                    
                                    if st.button("🔗 Enllaçar Codi i Producte", use_container_width=True):
                                        try:
                                            supabase.table('tb_codis_barres').insert({
                                                'codi_barres': barcode,
                                                'id_producte': prod_ids[selected_idx]
                                            }).execute()
                                            st.success("Enllaçat correctament! Pots prémer els botons per actualitzar l'stock.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error enllaçant: {e}")
                    except Exception as e:
                        st.error(f"Error processant la imatge: {e}")
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
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
                    families = ["Totes"] + families
                        
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
                        if sel_fam == "Totes":
                            df_fam = df_available.sort_values('nom_estandard')
                        elif sel_fam == "Sense Família":
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
                
                # Fetch dynamically updated locations
                df_llocs = fetch_all_supabase(supabase, 'tb_llocs')
                if not df_llocs.empty:
                    df_llocs = df_llocs.sort_values(by='id_lloc')
                    llocs_options = df_llocs['nom_lloc'].tolist()
                else:
                    llocs_options = ["Sense Assignar"]
                    
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
                            "lloc": st.column_config.SelectboxColumn("Lloc", options=llocs_options, required=False)
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


    with tab_receptes:
        st.markdown("### 🍲 Menjar (Receptari MVP)")
        
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_receptes = fetch_all_supabase(supabase, 'tb_receptes_pro')
            if not df_receptes.empty:
                df_receptes = df_receptes.sort_values(by=['categoria', 'titol'], ascending=[True, True]).reset_index(drop=True)
            
            subtab_list, subtab_add, subtab_gen = st.tabs(["📖 Llibre de Receptes", "➕ Afegir Recepta", "🧠 Recomanador de Menús"])
            
            with subtab_list:
                # Sistema de Filtres
                with st.expander("🔍 Cercar i Filtrar Receptes", expanded=False):
                    f_text = st.text_input("Cercar per nom de la recepta...", key="f_text")
                    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns(6)
                    with f_col1:
                        f_cat = st.multiselect("Categoria", ["Tots", "Primer", "Segon", "Plat únic", "Postre", "Complement", "Guarnició", "Salsa"], key="f_cat_m")
                    with f_col2:
                        f_dif = st.multiselect("Dificultat", ["Tots", "Fàcil", "Mitjana", "Difícil"], key="f_dif_m")
                    with f_col3:
                        f_dia = st.multiselect("Dia", ["Tots", "Entre setmana", "Cap de setmana", "Festiu", "Especial"], key="f_dia_m")
                    with f_col4:
                        f_apat = st.multiselect("Àpat", ["Tots", "Esmorzar", "Dinar", "Sopar", "Dinar/Sopar"], key="f_apat_m")
                    with f_col5:
                        f_ori = st.multiselect("Origen", ["Tots", "Biblioteca/Pròpia", "Externa/Internet"], key="f_ori_m")
                    with f_col6:
                        f_temps = st.slider("Temps màxim", min_value=0, max_value=240, value=240, step=5, key="f_temps_s")
                
                # Apply filters
                df_filtrat = df_receptes.copy()
                if not df_filtrat.empty:
                    if f_text:
                        df_filtrat = df_filtrat[df_filtrat['titol'].str.contains(f_text, case=False, na=False)]
                    if f_cat:
                        if "Tots" not in f_cat:
                            df_filtrat = df_filtrat[df_filtrat['categoria'].isin(f_cat)]
                    if f_dif:
                        if "Tots" not in f_dif:
                            df_filtrat = df_filtrat[df_filtrat['dificultat'].isin(f_dif)]
                    if f_dia:
                        if "Tots" not in f_dia:
                            df_filtrat = df_filtrat[df_filtrat['tipus_dia'].isin(f_dia)]
                    if f_apat:
                        if "Tots" not in f_apat:
                            df_filtrat = df_filtrat[df_filtrat['apat'].isin(f_apat)]
                    if f_ori:
                        if "Tots" not in f_ori:
                            df_filtrat = df_filtrat[df_filtrat['origen'].isin(f_ori)]
                    if f_temps < 240:
                        df_filtrat['temps_num'] = pd.to_numeric(df_filtrat['temps_prep_minuts'], errors='coerce').fillna(0)
                        df_filtrat = df_filtrat[df_filtrat['temps_num'] <= f_temps]
                        df_filtrat = df_filtrat.drop(columns=['temps_num'])
                
                st.write("")
                mode_estalvi = st.toggle("📱 Mode Estalvi (Sense imatges per estalviar dades)", value=False)
                
                if df_filtrat.empty:
                    st.info("No s'han trobat receptes amb aquests filtres. Afegeix-ne una!")
                else:
                    cols = st.columns(4)
                    for idx_row, row in df_filtrat.iterrows():
                        col = cols[idx_row % 4]
                        with col:
                            card_height = 175 if mode_estalvi else 335
                            with st.container(border=True, height=card_height):
                                img_url = row.get('imatge_url')
                                if not mode_estalvi:
                                    if pd.notna(img_url) and str(img_url).strip() != '':
                                        st.markdown(f'<img src="{img_url}" loading="lazy" style="width:100%; height:160px; object-fit:cover; border-radius:8px;">', unsafe_allow_html=True)
                                    else:
                                        st.info("Sense imatge", icon="📷")
                                
                                st.markdown(f'<div style="height: 70px; overflow: hidden; margin-top: 10px; margin-bottom: 5px; display: flex; align-items: flex-start;"><h4 style="margin:0; line-height: 1.15;">{row.get("titol", "Sense títol")}</h4></div>', unsafe_allow_html=True)
                                t_prep = int(row['temps_prep_minuts']) if pd.notna(row.get('temps_prep_minuts')) else 0
                                d_dif = row['dificultat'] if pd.notna(row.get('dificultat')) else 'Fàcil'
                                t_apat = row.get('apat', 'Sense definir')
                                if pd.isna(t_apat) or not str(t_apat).strip(): t_apat = 'Sense definir'
                                st.caption(f"🥗 {row.get('categoria', '')} | ⏱️ {t_prep} min | 🔪 {d_dif} | 🍽️ {t_apat}")
                                
                                if st.button("📖 Llegir Recepta", key=f"btn_rec_{row.get('id', idx_row)}", use_container_width=True):
                                    st.session_state[f"editing_{row['id']}"] = False
                                    modal_recepta(row)
            
            with subtab_add:
                c_fields, c_img = st.columns([3, 1])
                
                with c_fields:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        new_titol = st.text_input("Títol de la Recepta", key="k_titol")
                        new_cat = st.selectbox("Categoria", ["Primer", "Segon", "Plat únic", "Postre", "Complement", "Guarnició", "Salsa"], key="k_cat")
                        new_temps = st.number_input("Temps de prep. (min)", min_value=0, step=5, key="k_temps")
                    with c2:
                        new_apat = st.selectbox("Àpat", ["Esmorzar", "Dinar", "Sopar", "Dinar/Sopar"], key="k_apat")
                        new_dif = st.selectbox("Dificultat", ["Fàcil", "Mitjana", "Difícil"], key="k_dif")
                        new_dia = st.selectbox("Tipus de dia", ["Entre setmana", "Cap de setmana", "Festiu", "Especial"], key="k_dia")
                        new_temp = st.selectbox("Temporada", ["Tot l'any", "Primavera", "Estiu", "Tardor", "Hivern"], key="k_temp")
                    with c3:
                        new_ori = st.selectbox("Origen", ["Biblioteca/Pròpia", "Externa/Internet"], key="k_ori")
                        new_salut = st.slider("Puntuació Salut (0-10)", 0, 10, 5, key="k_salut")
                        new_img_url = st.text_input("URL Imatge (opcional)", key="k_img_url")
                        new_vid_url = st.text_input("URL Vídeo (YouTube, opcional)", key="k_vid_url")
                    
                    new_tags = st.multiselect("Etiquetes / Al·lèrgies (Nutrició)", ["Sense Gluten", "Sense Lactosa", "Vegetarià", "Vegà", "Baix en Sal", "Baix en Greix", "Alt en Proteïna", "Sense Sucre"], key="k_tags")
                    new_ing = st.text_area("Ingredients (un per línia)", key="k_ing")
                    new_mise = st.text_area("Mise en place (Preparació prèvia)", key="k_mise")
                    new_ins = st.text_area("Instruccions de preparació", key="k_ins")
                
                with c_img:
                    st.markdown("**🖼️ Imatge del plat**")
                    uploaded_file = st.file_uploader("Pujar des de l'ordinador", type=["jpg", "jpeg", "png", "webp"], key="k_uploaded")
                    
                    if uploaded_file is not None:
                        st.image(uploaded_file, use_container_width=True)
                    elif new_img_url.strip():
                        st.image(new_img_url, use_container_width=True)
                    else:
                        st.info("Sense imatge. Afegeix una URL o puja un arxiu.", icon="📷")
                
                submitted = st.button("💾 Guardar Recepta")
                if submitted:
                    if new_titol:
                        final_img_url = new_img_url
                        if uploaded_file is not None:
                            try:
                                import uuid
                                file_ext = uploaded_file.name.split(".")[-1]
                                file_name = f"{uuid.uuid4()}.{file_ext}"
                                file_bytes = uploaded_file.getvalue()
                                res = supabase.storage.from_("imatges-receptes").upload(file_name, file_bytes)
                                final_img_url = supabase.storage.from_("imatges-receptes").get_public_url(file_name)
                            except Exception as e:
                                st.error(f"Error pujant l'arxiu a Supabase Storage: {e}")
                                final_img_url = new_img_url

                        data_insert = {
                            "titol": new_titol,
                            "categoria": new_cat,
                            "temps_prep_minuts": new_temps,
                            "temporada": new_temp,
                            "puntuacio_salut": new_salut,
                            "ingredients": new_ing,
                            "mise_en_place": new_mise,
                            "instruccions": new_ins,
                            "imatge_url": final_img_url,
                            "video_url": new_vid_url,
                            "dificultat": new_dif,
                            "tipus_dia": new_dia,
                            "origen": new_ori,
                            "apat": new_apat,
                            "tags_nutricionals": new_tags
                        }
                        resp = supabase.table('tb_receptes_pro').insert(data_insert).execute()
                        if resp.data:
                            # Clear form keys from session_state
                            keys_to_clear = ['k_titol', 'k_cat', 'k_temps', 'k_dif', 'k_dia', 'k_temp', 'k_ori', 'k_salut', 'k_img_url', 'k_vid_url', 'k_ing', 'k_mise', 'k_ins', 'k_uploaded']
                            for key in keys_to_clear:
                                if key in st.session_state:
                                    del st.session_state[key]
                                    
                            st.success(f"Recepta '{new_titol}' guardada correctament!")
                            st.rerun()
                        else:
                            st.error("Error al guardar la recepta.")
                    else:
                        st.warning("El títol és obligatori!")
                        
            with subtab_gen:
                st.markdown("### 🧠 Planificador de Menús Setmanal")
                st.write("Genera un menú equilibrat basat en les teves receptes, la temporada i les teves preferències.")
                
                with st.expander("⚙️ Configuració del Perfil Familiar", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        num_comensals = st.number_input("Nombre de comensals", min_value=1, value=2, step=1)
                        st.session_state['num_comensals'] = num_comensals
                        temp_opts = ["Tot l'any", "Primavera", "Estiu", "Tardor", "Hivern"]
                        import pandas as pd
                        month = pd.Timestamp.now().month
                        if month in [3,4,5]: def_temp = "Primavera"
                        elif month in [6,7,8]: def_temp = "Estiu"
                        elif month in [9,10,11]: def_temp = "Tardor"
                        else: def_temp = "Hivern"
                        sel_temp = st.selectbox("Temporada actual", temp_opts, index=temp_opts.index(def_temp))
                    with c2:
                        tags_opts = ["Sense Gluten", "Sense Lactosa", "Vegetarià", "Vegà", "Baix en Sal", "Baix en Greix", "Alt en Proteïna", "Sense Sucre"]
                        req_tags = st.multiselect("Requisits Nutricionals (oblidatoris per la recepta)", tags_opts)
                    with c3:
                        st.write(" ")
                        st.write(" ")
                        btn_gen = st.button("🔄 Generar Menú Setmanal", use_container_width=True, type="primary")

                if btn_gen:
                    if df_receptes.empty:
                        st.warning("No hi ha receptes suficients per generar un menú.")
                    else:
                        with st.spinner("Creant menú intel·ligent..."):
                            import random
                            df_pool = df_receptes.copy()
                            df_pool = df_pool[(df_pool['temporada'].isin([sel_temp, "Tot l'any"]))]
                            if req_tags:
                                def has_all_tags(tags_list):
                                    if not isinstance(tags_list, list): return False
                                    return all(t in tags_list for t in req_tags)
                                df_pool = df_pool[df_pool['tags_nutricionals'].apply(has_all_tags)]
                            
                            def get_pool(apat_req, cat_req):
                                df = df_pool[(df_pool['apat'].isin(apat_req)) & (df_pool['categoria'].isin(cat_req))]
                                return df.to_dict('records')
                                
                            pool_dp = get_pool(['Dinar', 'Dinar/Sopar'], ['Primer'])
                            pool_ds = get_pool(['Dinar', 'Dinar/Sopar'], ['Segon', 'Plat únic'])
                            pool_dpo = get_pool(['Dinar', 'Dinar/Sopar', 'Sopar'], ['Postre'])
                            
                            pool_ss = get_pool(['Sopar', 'Dinar/Sopar'], ['Segon', 'Plat únic'])
                            if len(pool_ss) < 7:
                                pool_ss.extend(get_pool(['Dinar'], ['Primer', 'Plat únic'])) # Borrow light lunches
                                
                            pool_spo = get_pool(['Sopar', 'Dinar/Sopar', 'Dinar'], ['Postre'])
                            
                            def pick_recipe(pool, avoid_ingredients, used_weekly, is_weekend, max_arros_pasta=2):
                                if not pool: return None, avoid_ingredients
                                
                                random.shuffle(pool)
                                
                                # First pass: strict constraints
                                for r in pool:
                                    t = r['titol']
                                    t_low = t.lower()
                                    if t in used_weekly: continue
                                    
                                    # Day constraint
                                    tipus_dia = r.get('tipus_dia', '')
                                    if not is_weekend and tipus_dia in ['Cap de setmana', 'Festiu', 'Especial']: continue
                                    
                                    # Ingredient clash (same meal)
                                    clash = False
                                    for kw in avoid_ingredients:
                                        if kw in t_low: clash = True
                                    if clash: continue
                                        
                                    # Weekly limits (arròs / pasta / llegums)
                                    if 'arròs' in t_low or 'arros' in t_low:
                                        if sum(1 for x in used_weekly if 'arròs' in x.lower() or 'arros' in x.lower()) >= max_arros_pasta:
                                            continue
                                    if 'pasta' in t_low or 'macarrons' in t_low or 'fideus' in t_low or 'espaguetis' in t_low:
                                        if sum(1 for x in used_weekly if 'pasta' in x.lower() or 'macarrons' in x.lower() or 'fideus' in x.lower() or 'espaguetis' in x.lower()) >= max_arros_pasta:
                                            continue
                                            
                                    # Extract new keywords to avoid in same meal
                                    new_av = list(avoid_ingredients)
                                    for kw in ['ou', 'arròs', 'arros', 'pasta', 'pollastre', 'porc', 'vedella', 'peix', 'formatge', 'patata']:
                                        if kw in t_low: new_av.append(kw)
                                        
                                    used_weekly.append(t)
                                    return t, new_av
                                    
                                # Fallback 1: loosen day constraints, but keep weekly ingredient limit and avoid same-meal clashes
                                for r in pool:
                                    t = r['titol']
                                    t_low = t.lower()
                                    if t in used_weekly: continue
                                    clash = False
                                    for kw in avoid_ingredients:
                                        if kw in t_low: clash = True
                                    if clash: continue
                                    used_weekly.append(t)
                                    return t, avoid_ingredients
                                    
                                # Fallback 2: allow repeats if we run out of unique recipes
                                r = random.choice(pool)
                                return r['titol'], avoid_ingredients
                                
                            dies = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
                            menu_data = []
                            used_all_week = []
                            
                            for dia in dies:
                                is_weekend = dia in ["Dissabte", "Diumenge"]
                                av_ingredients_dinar = []
                                av_ingredients_sopar = []
                                
                                p1, av_ingredients_dinar = pick_recipe(pool_dp, av_ingredients_dinar, used_all_week, is_weekend)
                                p2, av_ingredients_dinar = pick_recipe(pool_ds, av_ingredients_dinar, used_all_week, is_weekend)
                                p3, _ = pick_recipe(pool_dpo, [], used_all_week, is_weekend)
                                
                                s1, av_ingredients_sopar = pick_recipe(pool_ss, av_ingredients_sopar, used_all_week, is_weekend)
                                s2, _ = pick_recipe(pool_spo, [], used_all_week, is_weekend)
                                
                                menu_data.append({
                                    "Dia": dia,
                                    "Dinar: Primer": p1 or "-",
                                    "Dinar: Segon": p2 or "-",
                                    "Dinar: Postre": p3 or "-",
                                    "Sopar: Segon": s1 or "-",
                                    "Sopar: Postre": s2 or "-"
                                })
                            st.session_state['gen_menu_data'] = menu_data
                            
                if 'gen_menu_data' in st.session_state:
                    st.markdown("#### 📅 El teu Menú Setmanal")
                    import pandas as pd
                    st.dataframe(pd.DataFrame(st.session_state['gen_menu_data']), use_container_width=True, hide_index=True)
                    
                    st.markdown("#### ⏱️ Timing i Organització (Batch Cooking)")
                    c_n = st.session_state.get('num_comensals', 2)
                    st.info(f"**Suggeriment d'organització per {c_n} comensals:**\n- **Mise en place:** Revisa el diumenge els ingredients necessaris pels primers plats de la setmana.\n- **Preparació prèvia:** Pots tallar verdures i deixar sofregits a la nevera per accelerar els sopars entre setmana.\n- **Congelació:** Si fas guisats per dinar, planteja't doblar la recepta i congelar els tàpers restants per estalviar temps la setmana vinent.")

        except Exception as e:
            st.error(f"Error carregant Menjar: {e}")
            st.error(f"Error carregant Menjar: {e}")

