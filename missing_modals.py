@st.dialog("📋 Inventari Ràpid", width="large")
def modal_inventari(df_inv):
    st.write("Actualitza ràpidament l'stock agrupat pel lloc on el guardes.")
    
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    df_llocs = fetch_all_supabase(supabase, 'tb_llocs')
    if not df_llocs.empty:
        df_llocs = df_llocs.sort_values(by='id_lloc')
        llocs_options = df_llocs['nom_lloc'].tolist()
    else:
        llocs_options = ["Sense Assignar"]
    
    # Filter only products that are tracked in Rebost
    if 'select_stock' in df_inv.columns:
        df_inv = df_inv[df_inv['select_stock'] == True].copy()
        
    if df_inv.empty:
        st.warning("No hi ha productes de rebost.")
        return
        
    # Group by lloc
    df_inv['lloc'] = df_inv.get('lloc', 'Sense Assignar').fillna('Sense Assignar')
    df_inv.loc[df_inv['lloc'] == '', 'lloc'] = 'Sense Assignar'
    
    # Track changes
    if "inv_changes" not in st.session_state:
        st.session_state.inv_changes = {}
        
    for lloc, group in df_inv.groupby('lloc'):
        with st.expander(f"📍 {lloc} ({len(group)} productes)", expanded=False):
            # Sort by familia then name
            group = group.sort_values(by=['familia', 'nom_estandard'])
            
            # Prepare data editor df
            cols_to_show = ['familia', 'nom_estandard', 'lloc', 'stock_actual', 'stock_minim']
            df_edit = group[cols_to_show].copy()
            df_edit.set_index(group['idProducte'], inplace=True)
            
            edited_df = st.data_editor(
                df_edit,
                use_container_width=True,
                disabled=['familia', 'nom_estandard'],
                hide_index=True,
                column_config={
                    "lloc": st.column_config.SelectboxColumn(
                        "Lloc",
                        help="Tria la ubicació on es guarda el producte",
                        options=llocs_options,
                        required=True
                    )
                },
                key=f"editor_inv_{lloc}"
            )
            
            for idx, row in edited_df.iterrows():
                old_act = df_edit.at[idx, 'stock_actual']
                new_act = row['stock_actual']
                old_min = df_edit.at[idx, 'stock_minim']
                new_min = row['stock_minim']
                old_loc = df_edit.at[idx, 'lloc']
                new_loc = row['lloc']
                
                if old_act != new_act or old_min != new_min or old_loc != new_loc:
                    st.session_state.inv_changes[idx] = {
                        'stock_actual': new_act,
                        'stock_minim': new_min,
                        'lloc': new_loc if pd.notna(new_loc) else None
                    }
                    
    st.markdown("---")
    if len(st.session_state.inv_changes) > 0:
        st.info(f"Tens {len(st.session_state.inv_changes)} canvis pendents de guardar.")
    else:
        st.write("No has fet canvis.")
        
    if st.button("💾 Guardar Canvis d'Inventari", type="primary", use_container_width=True):
        if len(st.session_state.inv_changes) > 0:
            try:
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                for idx, changes in st.session_state.inv_changes.items():
                    supabase.table('tb_productes').update(changes).eq('idProducte', int(idx)).execute()
                st.success(f"S'han guardat {len(st.session_state.inv_changes)} canvis correctament!")
                st.session_state.inv_changes = {}
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error guardant: {e}")

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

