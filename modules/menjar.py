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
                                        st.markdown(f'<img src="{img_url}" loading="lazy" style="width:100%; height:160px; object-fit:cover; border-radius:8px; margin-bottom: 10px;">', unsafe_allow_html=True)
                                    else:
                                        st.markdown('<div style="width:100%; height:160px; background-color:#1e2530; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#555; margin-bottom: 10px;">📷 Sense imatge</div>', unsafe_allow_html=True)
                                
                                st.markdown(f'<div style="height: 55px; overflow: hidden; margin-bottom: 5px;"><strong>{row.get("titol", "Sense títol")}</strong></div>', unsafe_allow_html=True)
                                t_prep = int(row['temps_prep_minuts']) if pd.notna(row.get('temps_prep_minuts')) else 0
                                d_dif = row['dificultat'] if pd.notna(row.get('dificultat')) else 'Fàcil'
                                t_apat = row.get('apat', 'Sense definir')
                                if pd.isna(t_apat) or not str(t_apat).strip(): t_apat = 'Sense definir'
                                st.markdown(f'<div style="height: 45px; overflow: hidden; font-size: 0.85em; color: #a3a8b8; margin-bottom: 10px;">🍳 {row.get("categoria", "")} | ⏱️ {t_prep} min | ⚖️ {d_dif} | 🍽️ {t_apat}</div>', unsafe_allow_html=True)
                                
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

@st.dialog(" ", width="large")
def modal_recepta(row):
    is_editing = st.session_state.get(f"editing_{row['id']}", False)
    
    if is_editing:
        st.markdown("### ✏️ Editar Recepta")
        c_fields, c_img = st.columns([3, 1])
        with c_fields:
            c1, c2, c3 = st.columns(3)
            with c1:
                e_titol = st.text_input("Títol", value=row.get('titol', ''))
                cat_opts = ["Primer", "Segon", "Plat únic", "Postre", "Complement", "Guarnició", "Salsa"]
                e_cat = st.selectbox("Categoria", cat_opts, index=cat_opts.index(row.get('categoria')) if row.get('categoria') in cat_opts else 0)
                val_temps = row.get('temps_prep_minuts', 0)
                e_temps = st.number_input("Temps (min)", value=int(val_temps) if pd.notna(val_temps) else 0, step=5)
            with c2:
                apat_opts = ["Esmorzar", "Dinar", "Sopar", "Dinar/Sopar"]
                e_apat = st.selectbox("Àpat", apat_opts, index=apat_opts.index(row.get('apat')) if row.get('apat') in apat_opts else 0)
                dif_opts = ["Fàcil", "Mitjana", "Difícil"]
                e_dif = st.selectbox("Dificultat", dif_opts, index=dif_opts.index(row.get('dificultat')) if row.get('dificultat') in dif_opts else 0)
                dia_opts = ["Entre setmana", "Cap de setmana", "Festiu", "Especial"]
                e_dia = st.selectbox("Tipus de dia", dia_opts, index=dia_opts.index(row.get('tipus_dia')) if row.get('tipus_dia') in dia_opts else 0)
                temp_opts = ["Tot l'any", "Primavera", "Estiu", "Tardor", "Hivern"]
                e_temp = st.selectbox("Temporada", temp_opts, index=temp_opts.index(row.get('temporada')) if row.get('temporada') in temp_opts else 0)
            with c3:
                ori_opts = ["Biblioteca/Pròpia", "Externa/Internet"]
                e_ori = st.selectbox("Origen", ori_opts, index=ori_opts.index(row.get('origen')) if row.get('origen') in ori_opts else 0)
                val_salut = row.get('puntuacio_salut', 5)
                e_salut = st.slider("Salut (0-10)", 0, 10, int(val_salut) if pd.notna(val_salut) else 5)
                e_img_url = st.text_input("URL Imatge", value=str(row.get('imatge_url', '')).strip() if pd.notna(row.get('imatge_url')) else "")
                e_vid_url = st.text_input("URL Vídeo", value=str(row.get('video_url', '')).strip() if pd.notna(row.get('video_url')) else "")
                
            tags_opts = ["Sense Gluten", "Sense Lactosa", "Vegetarià", "Vegà", "Baix en Sal", "Baix en Greix", "Alt en Proteïna", "Sense Sucre"]
            curr_tags = row.get('tags_nutricionals')
            if not isinstance(curr_tags, list): curr_tags = []
            curr_tags = [t for t in curr_tags if t in tags_opts]
            e_tags = st.multiselect("Etiquetes / Al·lèrgies (Nutrició)", tags_opts, default=curr_tags, key=f"e_tags_{row['id']}")
            
            e_ing = st.text_area("Ingredients", value=row.get('ingredients', ''))
            e_mise = st.text_area("Mise en place (Preparació prèvia)", value=row.get('mise_en_place', ''))
            e_ins = st.text_area("Instruccions", value=row.get('instruccions', ''))
            
        with c_img:
            st.markdown("**Imatge Actual**")
            if e_img_url:
                st.image(e_img_url, use_container_width=True)
            else:
                st.info("Sense imatge")
                
            e_uploaded = st.file_uploader("Substituir imatge", type=["jpg", "jpeg", "png", "webp"], key=f"e_up_{row['id']}")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("❌ Cancel·lar", use_container_width=True):
                st.session_state[f"editing_{row['id']}"] = False
                st.rerun()
        with col_btn2:
            if st.button("💾 Desar Canvis", use_container_width=True):
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                final_img = e_img_url
                if e_uploaded is not None:
                    try:
                        import uuid
                        file_ext = e_uploaded.name.split(".")[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        supabase.storage.from_("imatges-receptes").upload(file_name, e_uploaded.getvalue())
                        final_img = supabase.storage.from_("imatges-receptes").get_public_url(file_name)
                    except Exception as e:
                        st.error(f"Error pujant la imatge: {e}")
                
                update_data = {
                    "titol": e_titol, "categoria": e_cat, "temps_prep_minuts": e_temps,
                    "temporada": e_temp, "puntuacio_salut": e_salut, "ingredients": e_ing,
                    "mise_en_place": e_mise,
                    "instruccions": e_ins, "imatge_url": final_img, "video_url": e_vid_url,
                    "dificultat": e_dif, "tipus_dia": e_dia, "origen": e_ori, "apat": e_apat,
                    "tags_nutricionals": e_tags
                }
                
                res = supabase.table('tb_receptes_pro').update(update_data).eq('id', row['id']).execute()
                if res.data:
                    st.session_state[f"editing_{row['id']}"] = False
                    st.success("Recepta actualitzada!")
                    st.rerun()
                else:
                    st.error("Error al actualitzar.")

    else:
        # Mode Lectura
        col_titol, col_btn = st.columns([4, 1])
        with col_titol:
            st.markdown(f"## {row.get('titol', '')}")
            t_prep = int(row['temps_prep_minuts']) if pd.notna(row.get('temps_prep_minuts')) else 0
            d_dif = row['dificultat'] if pd.notna(row.get('dificultat')) else 'No definida'
            t_dia = row['tipus_dia'] if pd.notna(row.get('tipus_dia')) else 'Qualsevol'
            t_apat = row['apat'] if pd.notna(row.get('apat')) else 'Sense definir'
            st.caption(f"🥗 {row.get('categoria', '')} | ⏱️ {t_prep} min | 🔪 {d_dif} | 📅 {t_dia} | 🍽️ {t_apat}")
        with col_btn:
            st.button("✏️ Editar", key=f"edit_top_{row['id']}", on_click=cb_set_editing_recepta, args=(row['id'], True), use_container_width=True)
                
        col_i, col_d = st.columns([1, 1])
        with col_i:
            img_url = row.get('imatge_url')
            if pd.notna(img_url) and str(img_url).strip() != '':
                st.image(img_url, use_container_width=True)
                
            vid_url = row.get('video_url')
            if pd.notna(vid_url) and str(vid_url).strip() != '':
                vid_str = str(vid_url).strip()
                if "3cat.cat" in vid_str or "ccma.cat" in vid_str:
                    import urllib.request
                    import re
                    import streamlit.components.v1 as components
                    try:
                        req = urllib.request.Request(vid_str, headers={'User-Agent': 'Mozilla/5.0'})
                        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
                        match = re.search(r'"embedUrl":\s*"//(www\.3cat\.cat/video/embed/\d+/)"', html)
                        if match:
                            embed_url = f"https://{match.group(1)}"
                            components.iframe(embed_url, height=300)
                        else:
                            st.video(vid_str)
                    except:
                        st.video(vid_str)
                else:
                    st.video(vid_str)
        
        with col_d:
            st.markdown("### Ingredients:")
            ing_val = row.get('ingredients', '')
            ing_raw = str(ing_val) if pd.notna(ing_val) and str(ing_val).strip().lower() != 'nan' else ''
            if ing_raw.strip():
                import re
                lines = [re.sub(r'^[\-\*•\·]\s*', '', line.strip()).strip() for line in ing_raw.split('\n') if line.strip()]
                ing_format = " * ".join(lines)
            else:
                ing_format = "Sense ingredients"
            st.info(ing_format)
            
            mise = row.get('mise_en_place', '')
            if pd.notna(mise) and str(mise).strip() != '' and str(mise).strip().lower() != 'nan':
                st.markdown("### Mise en place:")
                st.info(str(mise).strip())
                
            st.markdown("### Info Addicional:")
            salut = row.get('puntuacio_salut', 0)
            salut_str = int(salut) if pd.notna(salut) and str(salut).strip().lower() != 'nan' else 0
            temp = row.get('temporada', '')
            temp_str = temp if pd.notna(temp) and str(temp).strip().lower() != 'nan' else "Tot l'any"
            ori = row.get('origen', 'Desconegut')
            ori_str = ori if pd.notna(ori) and str(ori).strip().lower() != 'nan' else 'Desconegut'
            
            st.write(f"**Salut:** {salut_str}/10 | **Temporada:** {temp_str}")
            st.write(f"**Origen:** {ori_str}")
            
            st.markdown("### Instruccions:")
            ins_val = row.get('instruccions', '')
            ins_raw = str(ins_val) if pd.notna(ins_val) and str(ins_val).strip().lower() != 'nan' else 'Sense instruccions'
            st.write(ins_raw)


def cb_set_editing_recepta(r_id, val):
    st.session_state[f"editing_{r_id}"] = val

