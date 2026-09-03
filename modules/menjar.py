import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from core.db import (
    get_supabase_client, fetch_all_supabase, update_db_row, log_action, insert_db_row, get_config_supers
)
import re
import urllib.parse

def clear_form_state(prefix: str):
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]

def render():
    col_t1, col_t2 = st.columns([8.5, 1.5], vertical_alignment="center")
    with col_t1:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>🍽️ Receptari i Menús</h2>", unsafe_allow_html=True)
    with col_t2:
        if st.button("🔙 Tornar a l'inici", use_container_width=True):
            st.session_state.current_module = None
            st.rerun()
    
    


    if True:
        
        
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_receptes = fetch_all_supabase(supabase, 'tb_receptes_pro')
            if not df_receptes.empty:
                df_receptes = df_receptes.sort_values(by=['categoria', 'titol'], ascending=[True, True]).reset_index(drop=True)
            
            subtab_gen, subtab_list, subtab_add = st.tabs(["🧠 Recomanador de Menús", "📖 Llibre de Receptes", "➕ Afegir Recepta"])
            
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
                            with st.container(border=True):
                                img_url = row.get('imatge_url')
                                if not mode_estalvi:
                                    if pd.notna(img_url) and str(img_url).strip() != '':
                                        st.image(img_url, use_container_width=True)
                                    else:
                                        st.info("Sense imatge", icon="📷")
                                
                                st.markdown(f"**{row.get('titol', 'Sense títol')}**")
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
                    st.dataframe(pd.DataFrame(st.session_state['gen_menu_data']), use_container_width=True, hide_index=True)
                    
                    st.markdown("#### ⏱️ Timing i Organització (Batch Cooking)")
                    c_n = st.session_state.get('num_comensals', 2)
                    st.info(f"**Suggeriment d'organització per {c_n} comensals:**\n- **Mise en place:** Revisa el diumenge els ingredients necessaris pels primers plats de la setmana.\n- **Preparació prèvia:** Pots tallar verdures i deixar sofregits a la nevera per accelerar els sopars entre setmana.\n- **Congelació:** Si fas guisats per dinar, planteja't doblar la recepta i congelar els tàpers restants per estalviar temps la setmana vinent.")

        except Exception as e:
            st.error(f"Error carregant Menjar: {e}")
            st.error(f"Error carregant Menjar: {e}")

def cb_set_editing_recepta(r_id, val):
    st.session_state[f"editing_{r_id}"] = val

