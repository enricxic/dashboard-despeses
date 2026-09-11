import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from core.db import (
    get_supabase_client, fetch_all_supabase, update_db_row, log_action, insert_db_row, get_config_supers
)
from core.config_manager import load_config
from core.harness import build_system_prompt_for_case, call_gemini_api, parse_and_clean_json
import re
import urllib.parse
import json

def clear_form_state(prefix: str):
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]

def scale_single_ingredient(line: str, base: float = 3.0, target: float = 3.0) -> str:
    line = line.strip()
    if not line:
        return ""
    if base <= 0:
        base = 3.0
    if target <= 0:
        target = 3.0
        
    factor = target / base
    if abs(factor - 1.0) < 1e-4:
        return line

    # Ignore items that should not scale linearly
    unscalable_keywords = ['al gust', 'al gusto', 'raig', 'pessic', 'mica', 'opcional', 'polsim', 'fulla', 'fulles', 'ramet', 'branqueta', 'aigua per']
    if any(k in line.lower() for k in unscalable_keywords):
        return line

    # Match fraction (e.g. 1/2, 1/4, 3/4)
    frac_match = re.match(r'^(\d+)/(\d+)\s*(.*)$', line)
    if frac_match:
        num = int(frac_match.group(1))
        den = int(frac_match.group(2))
        val = (num / den) * factor
        val_str = f"{val:.1f}".rstrip('0').rstrip('.')
        rest = frac_match.group(3)
        return f"{val_str} {rest}".strip()

    # Match range (e.g. 1 a 1.5 kg, 3-4 carxofes, 3 a 4)
    range_match = re.match(r'^(\d+(?:[\.,]\d+)?)\s*(?:a|-)\s*(\d+(?:[\.,]\d+)?)\s*([a-zA-Zà-ÿÀ-Ý%]+.*)$', line)
    if range_match:
        v1 = float(range_match.group(1).replace(',', '.')) * factor
        v2 = float(range_match.group(2).replace(',', '.')) * factor
        v1_str = f"{v1:.1f}".rstrip('0').rstrip('.') if v1 < 10 else f"{round(v1)}"
        v2_str = f"{v2:.1f}".rstrip('0').rstrip('.') if v2 < 10 else f"{round(v2)}"
        unit_rest = range_match.group(3)
        return f"{v1_str}-{v2_str} {unit_rest}".strip()

    # Match number + optional unit + rest (e.g. 250g, 250 g, 4 ous, 1.5 kg, 1 gra d'all)
    num_match = re.match(r'^(\d+(?:[\.,]\d+)?)\s*([a-zA-Zà-ÿÀ-Ý\']*)(.*)$', line)
    if num_match:
        num_val = float(num_match.group(1).replace(',', '.'))
        unit = num_match.group(2)
        rest = num_match.group(3)
        
        scaled_val = num_val * factor
        
        # Format the number nicely
        if scaled_val >= 10:
            val_str = str(round(scaled_val))
        elif scaled_val >= 1:
            val_str = f"{scaled_val:.1f}".rstrip('0').rstrip('.')
        else:
            val_str = f"{scaled_val:.2f}".rstrip('0').rstrip('.')
            
        if unit:
            if unit.lower() in ['g', 'gr', 'kg', 'ml', 'cl', 'l', 'mg']:
                return f"{val_str}{unit}{rest}".strip()
            else:
                return f"{val_str} {unit}{rest}".strip()
        else:
            return f"{val_str}{rest}".strip()

    return line

def scale_ingredients(raw_ingredients: str, base: float = 3.0, target: float = 3.0) -> str:
    if not raw_ingredients or str(raw_ingredients).strip().lower() == 'nan':
        return "Sense ingredients"
    
    if '\n' in raw_ingredients:
        raw_lines = [re.sub(r'^[\-\*•\·]\s*', '', l.strip()).strip() for l in raw_ingredients.split('\n') if l.strip()]
    elif '*' in raw_ingredients:
        raw_lines = [re.sub(r'^[\-\*•\·]\s*', '', l.strip()).strip() for l in raw_ingredients.split('*') if l.strip()]
    else:
        raw_lines = [raw_ingredients.strip()]
        
    scaled_lines = [scale_single_ingredient(line, base=base, target=target) for line in raw_lines]
    return " * ".join(scaled_lines)

def cb_set_editing_recepta(r_id, val):
    st.session_state[f"editing_{r_id}"] = val

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
            c_ing_title, c_com = st.columns([2.2, 1.8], vertical_alignment="center")
            with c_ing_title:
                st.markdown("### Ingredients:")
            with c_com:
                num_c = st.number_input("Comensals", min_value=1, max_value=30, value=3, step=1, key=f"rec_comensals_{row['id']}")
            
            st.caption(f"Quantitats calculades per a **{num_c} comensals** (recepta base: 3 persones):")
            ing_val = row.get('ingredients', '')
            scaled_ing = scale_ingredients(ing_val, base=3, target=num_c)
            st.info(scaled_ing)
            
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
            
            st.markdown("---")
            st.markdown("### ⭐ Valoració Familiar (0 - 5 estrelles):")
            cfg_fam = load_config().get("familia", [])
            cols_v = st.columns(max(1, len(cfg_fam)))
            for idx_f, f_m in enumerate(cfg_fam):
                col_vf = cols_v[idx_f % len(cols_v)]
                with col_vf:
                    f_nom = f_m.get("nom", f"Membre {idx_f+1}")
                    f_ico = f_m.get("icona", "👤")
                    st.caption(f"{f_ico} **{f_nom}**")
                    st.slider("Nota", 0, 5, 4, key=f"val_{row['id']}_{idx_f}", label_visibility="collapsed")

def cercar_recepta_per_nom(nom_plat: str, df_receptes: pd.DataFrame):
    """Cerca de forma tolerant una recepta al DataFrame pel nom o paraules clau."""
    if not nom_plat or df_receptes is None or df_receptes.empty or str(nom_plat).strip() in ['-', '', 'null', 'None']:
        return None
    nom_clean = nom_plat.lower().strip()
    
    # 1. Coincidència exacta
    exact = df_receptes[df_receptes['titol'].str.lower().str.strip() == nom_clean]
    if not exact.empty:
        return exact.iloc[0]
        
    # 2. Conté el títol o viceversa
    for _, row in df_receptes.iterrows():
        t_clean = str(row.get('titol', '')).lower().strip()
        if t_clean and (t_clean in nom_clean or nom_clean in t_clean):
            return row
            
    # 3. Paraules clau significatives
    words = [w for w in re.split(r'\W+', nom_clean) if len(w) > 3 and w not in ['amb', 'dels', 'deles', 'sense', 'plat', 'estofat', 'estofada', 'planxa', 'forn', 'salsa', 'feta', 'estil']]
    if words:
        for _, row in df_receptes.iterrows():
            t_clean = str(row.get('titol', '')).lower()
            if any(w in t_clean for w in words):
                return row
                
    return None

def sanitize_segon(p_seg: str) -> str:
    """Evita que cap fruita o postre aparegui com a segon plat."""
    if not p_seg or str(p_seg).strip() in ['-', 'null', 'None']:
        return '-'
    p_seg_lower = str(p_seg).lower()
    if any(k in p_seg_lower for k in ['fruita', 'iogurt', 'postre', 'poma', 'plàtan', 'pera', 'taronja', 'maduixa', 'mandarina']):
        return '-'
    return p_seg

def render_plat_card(tipus_label: str, nom_plat: str, df_receptes: pd.DataFrame, key_btn: str, n_comensals: int = 3):
    """Renderitza una targeta visual amb miniatura i botó per obrir la recepta."""
    if not nom_plat or str(nom_plat).strip() in ['-', '', 'null', 'None']:
        return
    
    rec = cercar_recepta_per_nom(nom_plat, df_receptes)
    
    with st.container(border=True):
        col_img, col_txt = st.columns([1.3, 3.7], vertical_alignment="center")
        
        with col_img:
            if rec is not None and pd.notna(rec.get('imatge_url')) and str(rec.get('imatge_url')).strip():
                st.markdown(f'<img src="{rec.get("imatge_url")}" loading="lazy" style="width:100%; height:64px; object-fit:cover; border-radius:6px;">', unsafe_allow_html=True)
            else:
                emoji_cat = "🥣" if "1r" in tipus_label else ("🥩" if "2n" in tipus_label else "🍳")
                st.markdown(f'<div style="width:100%; height:64px; background:#1b222d; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:1.6rem; color:#888;">{emoji_cat}</div>', unsafe_allow_html=True)
        
        with col_txt:
            st.markdown(f"**{tipus_label}:** {nom_plat}")
            if rec is not None:
                t_prep = int(rec['temps_prep_minuts']) if pd.notna(rec.get('temps_prep_minuts')) else 0
                st.caption(f"📖 *{rec.get('titol')}* | ⏱️ {t_prep} min")
                if st.button("🔍 Veure Recepta", key=key_btn, use_container_width=True):
                    st.session_state[f"editing_{rec['id']}"] = False
                    st.session_state[f"rec_comensals_{rec['id']}"] = n_comensals
                    modal_recepta(rec)
            else:
                st.caption("✨ *Proposta de la IA*")

DEFAULT_PANTRY_CATALOG = [
    # Verdures / Hortalisses
    {"nom": "Ceba", "categoria": "Verdures", "stock_actual": 2.0, "unitat": "kg"},
    {"nom": "All / Alls", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "cap"},
    {"nom": "Patata", "categoria": "Verdures", "stock_actual": 3.0, "unitat": "kg"},
    {"nom": "Zanahoria / Pastanaga", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "kg"},
    {"nom": "Carbassó", "categoria": "Verdures", "stock_actual": 2.0, "unitat": "u"},
    {"nom": "Albergínia", "categoria": "Verdures", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Pimentó / Pebrot", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "u"},
    {"nom": "Tomàquet", "categoria": "Verdures", "stock_actual": 1.5, "unitat": "kg"},
    {"nom": "Carbassa", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "u"},
    {"nom": "Porró / All porró", "categoria": "Verdures", "stock_actual": 2.0, "unitat": "u"},
    {"nom": "Bròcoli", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "u"},
    {"nom": "Coliflor", "categoria": "Verdures", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Espinacs", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "bossa"},
    {"nom": "Bledes / Acelgas", "categoria": "Verdures", "stock_actual": 0.0, "unitat": "bossa"},
    {"nom": "Enciam / Amanida", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "u"},
    {"nom": "Canonges", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "bossa"},
    {"nom": "Xampinyons / Bolets", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "bandeja"},
    {"nom": "Carxofes", "categoria": "Verdures", "stock_actual": 0.0, "unitat": "kg"},
    {"nom": "Calçots", "categoria": "Verdures", "stock_actual": 0.0, "unitat": "manat"},
    {"nom": "Cogombre", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "u"},
    {"nom": "Espàrrecs", "categoria": "Verdures", "stock_actual": 1.0, "unitat": "manat"},
    {"nom": "Api", "categoria": "Verdures", "stock_actual": 0.0, "unitat": "u"},

    # Proteïnes
    {"nom": "Ous", "categoria": "Proteïnes", "stock_actual": 6.0, "unitat": "u"},
    {"nom": "Pollastre", "categoria": "Proteïnes", "stock_actual": 500.0, "unitat": "g"},
    {"nom": "Carn picada", "categoria": "Proteïnes", "stock_actual": 400.0, "unitat": "g"},
    {"nom": "Gall dindi / Pavo", "categoria": "Proteïnes", "stock_actual": 0.0, "unitat": "g"},
    {"nom": "Tonyina en conserva", "categoria": "Proteïnes", "stock_actual": 3.0, "unitat": "llaunes"},
    {"nom": "Cigrons cuits", "categoria": "Proteïnes", "stock_actual": 2.0, "unitat": "pots"},
    {"nom": "Llenties cuites", "categoria": "Proteïnes", "stock_actual": 2.0, "unitat": "pots"},
    {"nom": "Fesols / Alubias", "categoria": "Proteïnes", "stock_actual": 1.0, "unitat": "pots"},
    {"nom": "Lluç / Peix blanc", "categoria": "Proteïnes", "stock_actual": 4.0, "unitat": "filets"},
    {"nom": "Salmó", "categoria": "Proteïnes", "stock_actual": 2.0, "unitat": "filets"},
    {"nom": "Bacallà", "categoria": "Proteïnes", "stock_actual": 0.0, "unitat": "g"},
    {"nom": "Sèpia / Calamar", "categoria": "Proteïnes", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Gambes", "categoria": "Proteïnes", "stock_actual": 1.0, "unitat": "caixa"},
    {"nom": "Pernil / Bacon / Xorís", "categoria": "Proteïnes", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Botifarra", "categoria": "Proteïnes", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Tofu", "categoria": "Proteïnes", "stock_actual": 0.0, "unitat": "paquet"},

    # Cereals i Pa
    {"nom": "Arròs bomba", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "kg"},
    {"nom": "Arròs basmati / integral", "categoria": "Cereals i Pa", "stock_actual": 0.0, "unitat": "kg"},
    {"nom": "Pasta / Macarrons / Espaguetis", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Fideus", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Pa de motlle / Pa integral", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Farina de blat", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "kg"},
    {"nom": "Farina sense gluten", "categoria": "Cereals i Pa", "stock_actual": 0.0, "unitat": "kg"},
    {"nom": "Civada / Avena", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Tortilles de blat de moro", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Cuscús / Quinoa", "categoria": "Cereals i Pa", "stock_actual": 0.0, "unitat": "paquet"},
    {"nom": "Galetes / Torrades", "categoria": "Cereals i Pa", "stock_actual": 1.0, "unitat": "paquet"},

    # Fruita
    {"nom": "Llimona", "categoria": "Fruita", "stock_actual": 3.0, "unitat": "u"},
    {"nom": "Taronja", "categoria": "Fruita", "stock_actual": 2.0, "unitat": "kg"},
    {"nom": "Poma", "categoria": "Fruita", "stock_actual": 1.0, "unitat": "kg"},
    {"nom": "Plàtan", "categoria": "Fruita", "stock_actual": 4.0, "unitat": "u"},
    {"nom": "Pera", "categoria": "Fruita", "stock_actual": 0.0, "unitat": "kg"},
    {"nom": "Aguacate / Alvocat", "categoria": "Fruita", "stock_actual": 2.0, "unitat": "u"},
    {"nom": "Maduixes", "categoria": "Fruita", "stock_actual": 0.0, "unitat": "caixa"},
    {"nom": "Meló / Sandía", "categoria": "Fruita", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Kiwi", "categoria": "Fruita", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Pinya", "categoria": "Fruita", "stock_actual": 0.0, "unitat": "u"},

    # Làctics
    {"nom": "Llet", "categoria": "Làctics", "stock_actual": 2.0, "unitat": "L"},
    {"nom": "Iogurt natural", "categoria": "Làctics", "stock_actual": 4.0, "unitat": "u"},
    {"nom": "Iogurt grec", "categoria": "Làctics", "stock_actual": 0.0, "unitat": "u"},
    {"nom": "Formatge curat", "categoria": "Làctics", "stock_actual": 200.0, "unitat": "g"},
    {"nom": "Formatge fresc / Feta", "categoria": "Làctics", "stock_actual": 1.0, "unitat": "u"},
    {"nom": "Formatge ratllat / Mozzarella", "categoria": "Làctics", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Mantega", "categoria": "Làctics", "stock_actual": 1.0, "unitat": "paquet"},
    {"nom": "Nata de cuina", "categoria": "Làctics", "stock_actual": 1.0, "unitat": "bric"},

    # Rebost
    {"nom": "Tomàquet triturat / Frit", "categoria": "Rebost", "stock_actual": 2.0, "unitat": "pots"},
    {"nom": "Caldo de peix", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "L"},
    {"nom": "Caldo de pollastre / verdures", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "L"},
    {"nom": "Ametlles / Nous / Fruits secs", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "bossa"},
    {"nom": "Olives", "categoria": "Rebost", "stock_actual": 2.0, "unitat": "pots"},
    {"nom": "Oli d'oliva", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "ampolla"},
    {"nom": "Vinagre / Saboritzants", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "ampolla"},
    {"nom": "Sal / Pebre / Espècies", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "pot"},
    {"nom": "Mel / Sucre", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "pot"},
    {"nom": "Salses (Maionesa / Mostassa / Soja)", "categoria": "Rebost", "stock_actual": 1.0, "unitat": "pot"},
]

def render_pantry_tag_cloud(supabase_client=None) -> List[Dict[str, str]]:
    """Renderitza el núvol d'etiquetes del rebost interactiu (imatges 1 i 2).
    En fer clic sobre qualsevol etiqueta, aquesta canvia de color (verd vibrant amb estrella ⭐)
    per indicar que té PREFERÈNCIA ABSOLUTA per ser utilitzada per la IA."""
    
    st.markdown('''
    <style>
    .pantry-card-box {
        background: #0d131d;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
        margin-bottom: 16px;
    }
    .pantry-cat-title {
        font-size: 0.82rem;
        font-weight: 800;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-top: 12px;
        margin-bottom: 8px;
        border-bottom: 1px dashed #334155;
        padding-bottom: 4px;
    }
    </style>
    ''', unsafe_allow_html=True)
    
    st.markdown("#### 📦 Núvol d'Etiquetes del Rebost (Fes clic per donar Preferència)")
    st.caption("👈 **Fes clic sobre qualsevol etiqueta per canviar-la de color!** Les etiquetes ressaltades en verd amb **`⭐ PREFERENT`** seran utilitzades de manera prioritària per la IA per elaborar el menú setmanal.")

    # Funció auxiliar per filtrar productes de neteja, llar i higiene de les etiquetes d'alimentació
    clean_terms = [
        "neteja", "limpieza", "detergent", "detergente", "sabó", "jabon", "suavitzant", "suavizante",
        "fregasuelos", "lejía", "lleixiu", "papel", "paper", "servilleta", "servilletes", "champú", "champu",
        "xampú", "xampu", "gel", "dentifric", "dentifrico", "pastilla", "rentavaixelles", "lavavajillas",
        "bayeta", "estropajo", "fregall", "basura", "brossa", "higienico", "higiènic", "drogeria", "drogería",
        "higiene", "hogar", "llavavaixelles", "insecticida", "desinfectant", "desinfectante", "fregar", "bayetas",
        "scottex", "colgate", "fairy", "ariel", "skip", "mistol", "kh7", "kh-7", "don limpio", "harpic", "dodot",
        "compresa", "tampón", "tampon", "desodorant", "desodorante"
    ]

    def is_cleaning_product(name: str, cat: str) -> bool:
        n_low = str(name).lower()
        c_low = str(cat).lower()
        return any(term in n_low or term in c_low for term in clean_terms)

    # Fusionar el catàleg per defecte amb Supabase garantint que només surtin ingredients d'alimentació
    catalog_dict = {}
    for item in DEFAULT_PANTRY_CATALOG:
        if not is_cleaning_product(item["nom"], item.get("categoria", "")):
            k = item["nom"].lower().strip()
            catalog_dict[k] = dict(item)

    if supabase_client is not None:
        try:
            df_prods = fetch_all_supabase(supabase_client, 'tb_productes')
            if df_prods is not None and not df_prods.empty:
                for _, r in df_prods.iterrows():
                    nom = str(r.get('nom_estandard', '')).strip()
                    if not nom: continue
                    cat = str(r.get('familia', 'Rebost')).strip()
                    if is_cleaning_product(nom, cat):
                        continue
                    stk = float(r.get('stock_actual', 0.0)) if pd.notna(r.get('stock_actual')) else 0.0
                    k = nom.lower().strip()
                    if k in catalog_dict:
                        catalog_dict[k]["stock_actual"] = max(catalog_dict[k].get("stock_actual", 0.0), stk)
                        if cat and cat != 'Rebost':
                            catalog_dict[k]["categoria"] = cat
                    else:
                        catalog_dict[k] = {
                            "nom": nom,
                            "categoria": cat if cat else "Rebost",
                            "stock_actual": stk,
                            "unitat": "disponible"
                        }
        except Exception:
            pass
            
    catalog_items = list(catalog_dict.values())

    in_stock_items = [item for item in catalog_items if item.get("stock_actual", 0) > 0]
    in_stock_names = [item["nom"] for item in in_stock_items]

    if "pantry_selected_items" not in st.session_state:
        st.session_state["pantry_selected_items"] = []

    selected_set = set(st.session_state["pantry_selected_items"])

    # Barra d'accions ràpides i cerca
    col_search, col_act1, col_act2 = st.columns([5, 3.5, 3.5])
    with col_search:
        search_q = st.text_input("🔍 Cercar aliment al rebost...", key="pantry_search_input", label_visibility="collapsed", placeholder="🔍 Cercar aliment (ex. Carbassó, Tomàquet, Pollastre...)")
    with col_act1:
        if st.button("⭐ Seleccionar Tots d'Estoc Positiu", key="btn_sel_all_stock", use_container_width=True):
            st.session_state["pantry_selected_items"] = list(in_stock_names)
            st.rerun()
    with col_act2:
        if st.button("✨ Desmarcar Tots", key="btn_deselect_all_stock", use_container_width=True):
            st.session_state["pantry_selected_items"] = []
            st.rerun()

    # Agrupar per Categoria
    categories_map = {
        "Verdures": ["Verdures", "Hortalisses", "Verdura"],
        "Proteïnes": ["Proteïnes", "Proteína", "Carns", "Peix", "Llegums", "Ous"],
        "Cereals i Pa": ["Cereals i Pa", "Cereales", "Pasta", "Farines"],
        "Fruita": ["Fruita", "Frutas", "Fruites"],
        "Làctics": ["Làctics", "Lácteos", "Formatges"],
        "Rebost": ["Rebost", "Despensa", "Conserves", "Altres"]
    }

    grouped = {cat: [] for cat in categories_map.keys()}
    for item in catalog_items:
        if search_q.strip() and search_q.lower() not in item["nom"].lower():
            continue
        i_cat = item.get("categoria", "Rebost")
        matched = False
        for main_cat, synonyms in categories_map.items():
            if any(s.lower() in i_cat.lower() for s in synonyms):
                grouped[main_cat].append(item)
                matched = True
                break
        if not matched:
            grouped["Rebost"].append(item)

    # Renderitzar etiquetes clickables per categoria
    for cat_name, cat_items in grouped.items():
        if not cat_items: continue
        pos_count = sum(1 for it in cat_items if it.get("stock_actual", 0) > 0)
        sel_count = sum(1 for it in cat_items if it["nom"] in selected_set)
        
        st.markdown(f"<div class='pantry-cat-title'>{cat_name.upper()} ({sel_count} PREFERENTS / {pos_count} amb estoc)</div>", unsafe_allow_html=True)
        
        # Renderitzar en quadrícula de botons pastilla (6 columnes)
        cols = st.columns(6)
        for idx_it, it in enumerate(cat_items):
            col_idx = cols[idx_it % 6]
            name = it["nom"]
            is_sel = name in selected_set
            has_stock = it.get("stock_actual", 0) > 0
            stk_val = it.get("stock_actual", 0)
            u_str = it.get("unitat", "")
            
            with col_idx:
                if is_sel:
                    lbl = f"⭐ {name}"
                    if has_stock and stk_val > 0:
                        lbl += f" ({stk_val} {u_str})"
                    btn_type = "primary"
                else:
                    icon = "🟢 " if has_stock else "⚪ "
                    lbl = f"{icon}{name}"
                    if has_stock and stk_val > 0:
                        lbl += f" ({stk_val} {u_str})"
                    btn_type = "secondary"

                if st.button(lbl, key=f"btn_pantry_tag_{cat_name}_{idx_it}_{name}", type=btn_type, use_container_width=True):
                    if is_sel:
                        st.session_state["pantry_selected_items"].remove(name)
                    else:
                        st.session_state["pantry_selected_items"].append(name)
                    st.rerun()

    # Resum d'ingredients preferents
    sel_count_tot = len(st.session_state["pantry_selected_items"])
    if sel_count_tot > 0:
        st.success(f"⭐ **{sel_count_tot} ingredients marcats com a PREFERENTS de l'estoc.** La IA els donarà prioritat absoluta al menú setmanal.")
    else:
        st.info("ℹ️ Cap ingredient marcat com a preferent. Fes clic a les etiquetes per seleccionar els productes a aprofitar.")

    final_stock_list = []
    for s_name in st.session_state["pantry_selected_items"]:
        matching_item = next((it for it in catalog_items if it["nom"] == s_name), None)
        stk_info = f"Estoc actual: {matching_item['stock_actual']} {matching_item.get('unitat', '')}" if matching_item and matching_item.get("stock_actual", 0) > 0 else "Disponible al rebost"
        final_stock_list.append({
            "producte": f"⭐ {s_name} [INGREDIENT PREFERENT DE L'ESTOC]",
            "quantitat": stk_info,
            "ubicacio": "Rebost / Nevera / Congelador (Prioritat Alta)"
        })

    return final_stock_list

def render():
    col_t1, col_t2 = st.columns([9.2, 0.8], vertical_alignment="center")
    with col_t1:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>🍽️ Receptari i Menús</h2>", unsafe_allow_html=True)
    with col_t2:
        if st.button("🔙 Inici", use_container_width=True):
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
                                    st.session_state[f"rec_comensals_{row['id']}"] = 3
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
                st.markdown("### 🧠 Planificador Nutricional Intel·ligent (IA)")
                st.write("Genera un menú setmanal complet (Primer, Segon i Postre) adaptat a les al·lèrgies mèdiques, vetos personals amb desdoblament de plats, regles nutricionals i estoc existent.")
                
                cfg = load_config()
                familia_cfg = cfg.get("familia", [])
                regles_cfg = cfg.get("regles_menjar", {})
                
                with st.expander("⚙️ 1. Membres de la Llar, Al·lèrgies i Vetos", expanded=True):
                    st.markdown("**👥 Selecció i ajust de comensals per a aquesta setmana:**")
                    st.caption("Pots activar/desactivar qui menjarà a casa i ajustar les seves al·lèrgies o vetos directament per a aquesta planificació:")
                    
                    comensals_seleccionats = []
                    cols_fam = st.columns(max(1, len(familia_cfg)))
                    
                    for idx_f, memb in enumerate(familia_cfg):
                        col_f = cols_fam[idx_f % len(cols_fam)]
                        m_nom = memb.get("nom", f"Membre {idx_f+1}")
                        m_actiu_def = memb.get("actiu", True)
                        raw_al = memb.get("alergies", [])
                        m_alergies_list = raw_al if isinstance(raw_al, list) else [x.strip() for x in str(raw_al).split(",") if x.strip()]
                        raw_vt = memb.get("vetos", [])
                        m_vetos_list = raw_vt if isinstance(raw_vt, list) else [x.strip() for x in str(raw_vt).split(",") if x.strip()]
                        raw_com = memb.get("comodins", [])
                        m_comodins_list = raw_com if isinstance(raw_com, list) else [x.strip() for x in str(raw_com).split(",") if x.strip()]
                        
                        with col_f:
                            with st.container(border=True):
                                st.markdown(f"<div style='text-align:center; font-size:1.8rem;'>{memb.get('icona', '👤')}</div>", unsafe_allow_html=True)
                                chk = st.checkbox(f"**{m_nom}**", value=m_actiu_def, key=f"sel_mem_{idx_f}")
                                
                                # Edició ràpida de restriccions per membre
                                al_opts = ["Gluten", "Lactosa", "Fruits secs", "Marisc", "Ou", "Peix", "Soja"]
                                sel_al = st.multiselect("Al·lèrgies mèdiques", al_opts, default=[a for a in m_alergies_list if a in al_opts], key=f"al_m_{idx_f}")
                                
                                vet_input = st.text_input("Vetos personals", value=", ".join(m_vetos_list), key=f"vet_m_{idx_f}", placeholder="Ex. fetge, bledes")
                                cur_vetos = [v.strip() for v in vet_input.split(",") if v.strip()]
                                
                                comod_input = st.text_input("Plats comodí", value=", ".join(m_comodins_list), key=f"com_m_{idx_f}", placeholder="Ex. Pit de pollastre, Truita")
                                cur_comodins = [c.strip() for c in comod_input.split(",") if c.strip()]
                                
                                if chk:
                                    comensals_seleccionats.append({
                                        "nom": m_nom,
                                        "rol": memb.get("rol", ""),
                                        "edat": int(memb.get("edat", 30)) if str(memb.get("edat", "")).isdigit() else 30,
                                        "actiu": True,
                                        "alergies": sel_al,
                                        "vetos": cur_vetos,
                                        "comodins": cur_comodins
                                    })
                                else:
                                    st.caption("*(Fora de la llar aquesta setmana)*")
                
                with st.expander("🥗 2. Regles Nutricionals de la Llar", expanded=False):
                    c_r1, c_r2, c_r3 = st.columns(3)
                    with c_r1:
                        month = pd.Timestamp.now().month
                        if month in [3,4,5]: def_temp = "Primavera"
                        elif month in [6,7,8]: def_temp = "Estiu"
                        elif month in [9,10,11]: def_temp = "Tardor"
                        else: def_temp = "Hivern"
                        temp_opts = ["Tot l'any", "Primavera", "Estiu", "Tardor", "Hivern"]
                        sel_temp = st.selectbox("Temporada actual", temp_opts, index=temp_opts.index(def_temp), key="m_sel_temp")
                        max_carn = st.number_input("Màx. carn vermella / setm.", min_value=0, max_value=7, value=int(regles_cfg.get("max_carn_vermella", 1)), key="m_max_carn")
                    with c_r2:
                        min_peix = st.number_input("Mín. peix / setmana", min_value=0, max_value=7, value=int(regles_cfg.get("min_peix", 2)), key="m_min_peix")
                        min_lleg = st.number_input("Mín. llegums / setmana", min_value=0, max_value=7, value=int(regles_cfg.get("min_llegums", 2)), key="m_min_lleg")
                    with c_r3:
                        max_embotits = st.number_input("Màx. sopars embotits / freds", min_value=0, max_value=7, value=int(regles_cfg.get("max_embotits_sopar", 2)), key="m_max_embotits")
                        chk_hidrats = st.checkbox("🚫 Zero repeticions d'hidrats en dies consecutius", value=True, key="m_chk_hidrats")
                        forn_options = ["Cada dia / Qualsevol dia", "Només cap de setmana (Dissabte i Diumenge)"]
                        def_forn = regles_cfg.get("us_forn", forn_options[1])
                        sel_forn = st.selectbox("🔥 Disponibilitat del forn", forn_options, index=forn_options.index(def_forn) if def_forn in forn_options else 1, key="m_sel_forn")

                    eines_cfg = cfg.get("eines_cuina", {})
                    eines_actives_llista = [k for k, v in eines_cfg.items() if v]
                    st.caption(f"🍳 **Equipament de cuina actiu:** {', '.join(eines_actives_llista) if eines_actives_llista else 'Bàsic'}")

                with st.expander("📌 3. Fixar Plats per Dies i Peticions Familiars", expanded=False):
                    st.markdown("**🗓️ Fixació de plats o preferències per a cada dia de la setmana:**")
                    st.caption("Pots fixar plats concrets per als dies que vulguis (ex. Llenties dilluns, Sardines divendres, Paella diumenge). La IA respectarà aquests plats obligatòriament.")
                    
                    dies_setmana = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
                    peticions_dies = {}
                    
                    tabs_dies = st.tabs([f"🗓️ {d}" for d in dies_setmana])
                    for idx_d, tab_d in enumerate(tabs_dies):
                        dia_nom = dies_setmana[idx_d]
                        with tab_d:
                            col_pd1, col_pd2 = st.columns(2)
                            with col_pd1:
                                fix_dinar = st.text_input(f"☀️ Plat fixat per Dinar ({dia_nom}):", key=f"fix_din_{idx_d}", placeholder="Ex. Arròs de verdures / Llenties estofades / Lliure")
                                if fix_dinar.strip():
                                    peticions_dies[f"{dia_nom} dinar"] = fix_dinar.strip()
                            with col_pd2:
                                fix_sopar = st.text_input(f"🌙 Plat fixat per Sopar ({dia_nom}):", key=f"fix_sop_{idx_d}", placeholder="Ex. Sardines a la planxa / Truita de patates / Lliure")
                                if fix_sopar.strip():
                                    peticions_dies[f"{dia_nom} sopar"] = fix_sopar.strip()
                    
                    st.markdown("---")
                    peticio_general = st.text_area("💬 Petició especial o comentaris addicionals:", key="m_peticio_gen", placeholder="Ex. Diumenge dinar serem 6 comensals per la paella. Sopars de dimarts i dijous molt lleugers.", height=85)

                with st.expander("📦 4. Estoc del Rebost i Ingredients Preferents (Zero Malbaratament)", expanded=True):
                    pantry_tag_stock = render_pantry_tag_cloud(supabase)
                    st.markdown("---")
                    stock_input = st.text_area("🧊 Altres ingredients o notes d'estoc manuals (Congelador / Nevera):", key="m_stock_input", placeholder="Ex. Caldo de peix al congelador, 500g de carn picada, carbassons de l'hort", height=85)

                st.write("")
                btn_gen_ai = st.button("✨ Generar Menú Setmanal Intel·ligent (Primer + Segon + Postre)", use_container_width=True, type="primary")

                if btn_gen_ai:
                    if not comensals_seleccionats:
                        st.warning("Has de seleccionar com a mínim un membre actiu a la llar!")
                    else:
                        with st.spinner("🧠 Generant menú setmanal estructurat amb Gemini IA..."):
                            api_key = st.secrets.get("GEMINI_API_KEY", "")
                            
                            peticions_list = []
                            if peticio_general.strip():
                                peticions_list.append({"comensal": "Família", "plat": peticio_general.strip(), "dia_preferit": "Qualsevol"})
                            for k_dia, p_plat in peticions_dies.items():
                                peticions_list.append({"comensal": "Família", "plat": p_plat, "dia_preferit": k_dia})
                            
                            stock_list = list(pantry_tag_stock)
                            if stock_input.strip():
                                for s_line in stock_input.split("\n"):
                                    if s_line.strip():
                                        stock_list.append({"producte": s_line.strip(), "quantitat": "Disponible", "ubicacio": "Rebost/Congelador"})
                            
                            # Construir el cas de prova dinàmic
                            active_case = {
                                "id": "PLAN_SETMANAL_ACTUAL",
                                "titol": "Planificació Setmanal XiquiHouse",
                                "perfil_familia": comensals_seleccionats,
                                "regles_llar": {
                                    "max_carn_vermella": max_carn,
                                    "min_peix": min_peix,
                                    "min_llegums": min_lleg,
                                    "max_embotits_sopar": max_embotits,
                                    "no_repetir_hidrats": chk_hidrats,
                                    "us_forn": sel_forn
                                },
                                "eines_disponibles": eines_actives_llista,
                                "stock_disponible": stock_list,
                                "peticions_setmanals": peticions_list,
                                "valoracions_previes": {}
                            }
                            
                            rec_list = []
                            if not df_receptes.empty:
                                rec_list = df_receptes[['id', 'titol', 'categoria', 'apat', 'tags_nutricionals']].to_dict('records')
                            
                            prompt_str = build_system_prompt_for_case(active_case, recipes_catalog=rec_list)
                            ok_call, raw_resp, latency = call_gemini_api(prompt_str, api_key=api_key, model_name="gemini-3.8-flash")
                            
                            if ok_call:
                                json_ok, json_data, json_err = parse_and_clean_json(raw_resp)
                                if json_ok:
                                    st.session_state['ai_menu_result'] = json_data
                                    st.success(f"🎉 Menú generat amb èxit en {latency} segons utilitzant el teu receptari!")
                                else:
                                    st.error(f"Error parsejant el menú de la IA: {json_err}")
                            else:
                                st.error(f"Error cridant la IA: {raw_resp}")
                                st.info("🔄 Revisa la connexió o les regles seleccionades.")

                # Renderitzar el menú generat si existeix
                if 'ai_menu_result' in st.session_state:
                    menu_obj = st.session_state['ai_menu_result']
                    menu_setmanal = menu_obj.get("menu_setmanal", [])
                    
                    st.markdown("### 📅 El teu Menú Setmanal (Primer, Segon i Postre)")
                    st.caption("Fes clic a **🔍 Veure Recepta** a qualsevol plat per obrir la fitxa sencera amb quantitats i instruccions.")
                    
                    # Commutador de Mode Edició en viu
                    mode_edit = st.toggle("✏️ Mode Edició: Modificar / Canviar plats directament", value=False, key="toggle_edit_menu")
                    
                    # Targetes per dies
                    for idx_d, dia_data in enumerate(menu_setmanal):
                        dia_nom = dia_data.get("dia", f"Dia {idx_d+1}")
                        dinar = dia_data.get("dinar", {})
                        sopar = dia_data.get("sopar", {})
                        
                        with st.container(border=True):
                            st.markdown(f"#### 🗓️ {dia_nom}")
                            c_d1, c_d2 = st.columns(2)
                            
                            with c_d1:
                                st.markdown("##### ☀️ Dinar")
                                if not mode_edit:
                                    p_prim = dinar.get('primer', dinar.get('plat', '-'))
                                    p_seg = sanitize_segon(dinar.get('segon', '-'))
                                    p_post = dinar.get('postre', 'Fruita de temporada')
                                    
                                    # 1r Plat amb miniatura i botó de recepta
                                    if p_prim and p_prim != '-':
                                        render_plat_card("🥣 1r Plat", p_prim, df_receptes, f"btn_d_p1_{idx_d}", n_comensals=len(comensals_seleccionats))
                                    
                                    # 2n Plat amb miniatura i botó de recepta
                                    if p_seg and p_seg != '-':
                                        render_plat_card("🥩/🐟 2n Plat", p_seg, df_receptes, f"btn_d_p2_{idx_d}", n_comensals=len(comensals_seleccionats))
                                        
                                    # Postre
                                    st.markdown(f"<div style='margin-top:6px; padding:6px 10px; background:#18221e; border-radius:6px; font-size:0.9rem;'>🍏 <strong>Postre:</strong> {p_post}</div>", unsafe_allow_html=True)
                                else:
                                    dinar['primer'] = st.text_input("1r Plat Dinar", value=dinar.get('primer', dinar.get('plat', '')), key=f"ed_d_prim_{idx_d}")
                                    dinar['segon'] = st.text_input("2n Plat Dinar", value=sanitize_segon(dinar.get('segon', '')), key=f"ed_d_seg_{idx_d}")
                                    dinar['postre'] = st.text_input("Postre Dinar", value=dinar.get('postre', 'Fruita de temporada'), key=f"ed_d_post_{idx_d}")
                                
                                alt_d = dinar.get("plat_alternatiu")
                                if alt_d and isinstance(alt_d, dict) and alt_d.get('plat'):
                                    alt_plat_nom = alt_d.get('plat')
                                    st.markdown(f"<div style='background-color:#2a2318; border-left:4px solid #f39c12; padding:6px 10px; border-radius:4px; font-size:0.85rem; margin-top:8px;'>⚡ <strong>Plat ràpid per a {alt_d.get('per', '')}:</strong> {alt_plat_nom}<br><em style='color:#bbb;'>Motiu: {alt_d.get('motiu', '')}</em></div>", unsafe_allow_html=True)
                                    rec_alt_d = cercar_recepta_per_nom(alt_plat_nom, df_receptes)
                                    if rec_alt_d is not None:
                                        if st.button(f"🔍 Recepta per a {alt_d.get('per', '')}", key=f"btn_d_alt_{idx_d}", use_container_width=True):
                                            st.session_state[f"editing_{rec_alt_d['id']}"] = False
                                            st.session_state[f"rec_comensals_{rec_alt_d['id']}"] = 1
                                            modal_recepta(rec_alt_d)
                            
                            with c_d2:
                                st.markdown("##### 🌙 Sopar")
                                if not mode_edit:
                                    s_prim = sopar.get('primer', '')
                                    s_seg = sanitize_segon(sopar.get('segon', sopar.get('plat', '-')))
                                    s_post = sopar.get('postre', 'Iogurt')
                                    
                                    # 1r Plat Sopar (si existeix)
                                    if s_prim and s_prim.strip() and s_prim != '-':
                                        render_plat_card("🥣 1r Plat", s_prim, df_receptes, f"btn_s_p1_{idx_d}", n_comensals=len(comensals_seleccionats))
                                    
                                    # 2n Plat / Principal Sopar
                                    if s_seg and s_seg != '-':
                                        render_plat_card("🍳 Plat principal", s_seg, df_receptes, f"btn_s_p2_{idx_d}", n_comensals=len(comensals_seleccionats))
                                        
                                    # Postre
                                    st.markdown(f"<div style='margin-top:6px; padding:6px 10px; background:#18221e; border-radius:6px; font-size:0.9rem;'>🥛 <strong>Postre:</strong> {s_post}</div>", unsafe_allow_html=True)
                                else:
                                    sopar['primer'] = st.text_input("1r Plat Sopar (opcional)", value=sopar.get('primer', ''), key=f"ed_s_prim_{idx_d}")
                                    sopar['segon'] = st.text_input("Plat principal Sopar", value=sanitize_segon(sopar.get('segon', sopar.get('plat', ''))), key=f"ed_s_seg_{idx_d}")
                                    sopar['postre'] = st.text_input("Postre Sopar", value=sopar.get('postre', 'Iogurt'), key=f"ed_s_post_{idx_d}")
                                
                                alt_s = sopar.get("plat_alternatiu")
                                if alt_s and isinstance(alt_s, dict) and alt_s.get('plat'):
                                    alt_plat_nom = alt_s.get('plat')
                                    st.markdown(f"<div style='background-color:#2a2318; border-left:4px solid #f39c12; padding:6px 10px; border-radius:4px; font-size:0.85rem; margin-top:8px;'>⚡ <strong>Plat ràpid per a {alt_s.get('per', '')}:</strong> {alt_plat_nom}<br><em style='color:#bbb;'>Motiu: {alt_s.get('motiu', '')}</em></div>", unsafe_allow_html=True)
                                    rec_alt_s = cercar_recepta_per_nom(alt_plat_nom, df_receptes)
                                    if rec_alt_s is not None:
                                        if st.button(f"🔍 Recepta per a {alt_s.get('per', '')}", key=f"btn_s_alt_{idx_d}", use_container_width=True):
                                            st.session_state[f"editing_{rec_alt_s['id']}"] = False
                                            st.session_state[f"rec_comensals_{rec_alt_s['id']}"] = 1
                                            modal_recepta(rec_alt_s)
                    
                    st.write("")
                    
                    # Generador del text per WhatsApp (Consens)
                    wa_lines = ["*🍽️ Menú Setmanal XiquiHouse 🍽️*", ""]
                    for d in menu_setmanal:
                        wa_lines.append(f"📅 *{d.get('dia')}:*")
                        d_obj = d.get('dinar', {})
                        d_p1 = d_obj.get('primer', d_obj.get('plat', '-'))
                        d_p2 = sanitize_segon(d_obj.get('segon', ''))
                        d_pos = d_obj.get('postre', '')
                        d_txt = f"{d_p1}" + (f" + {d_p2}" if d_p2 and d_p2 != '-' else "") + (f" | 🍏 {d_pos}" if d_pos else "")
                        wa_lines.append(f"  • *Dinar:* {d_txt}")
                        
                        d_alt = d_obj.get('plat_alternatiu')
                        if d_alt and isinstance(d_alt, dict):
                            wa_lines.append(f"    ↳ _Alt. ({d_alt.get('per')}): {d_alt.get('plat')}_")
                        
                        s_obj = d.get('sopar', {})
                        s_p1 = s_obj.get('primer', '')
                        s_p2 = sanitize_segon(s_obj.get('segon', s_obj.get('plat', '-')))
                        s_pos = s_obj.get('postre', '')
                        s_txt = (f"{s_p1} + " if s_p1 and s_p1.strip() else "") + f"{s_p2}" + (f" | 🥛 {s_pos}" if s_pos else "")
                        wa_lines.append(f"  • *Sopar:* {s_txt}")
                        
                        s_alt = s_obj.get('plat_alternatiu')
                        if s_alt and isinstance(s_alt, dict):
                            wa_lines.append(f"    ↳ _Alt. ({s_alt.get('per')}): {s_alt.get('plat')}_")
                        wa_lines.append("")
                    wa_lines.append("💬 _Validem aquest menú per preparar la compra?_")
                    
                    wa_text = "\n".join(wa_lines)
                    wa_encoded = urllib.parse.quote(wa_text)
                    wa_url = f"https://wa.me/?text={wa_encoded}"
                    
                    c_wa, c_exp = st.columns([6, 4])
                    with c_wa:
                        st.markdown(f"""
                        <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                            <div style="background-color:#25D366; color:white; padding:12px 20px; border-radius:8px; text-align:center; font-weight:700; font-size:1.05rem; display:flex; align-items:center; justify-content:center; gap:8px;">
                                <span>📲</span> Enviar Menú per WhatsApp per a Consens Familiar
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                        
                    st.write("")
                    
                    # Pestanya Batch Cooking & Ingredients a Comprar
                    st.markdown("#### ⏱️ Mise en Place de Diumenge (Batch Cooking) i Compres")
                    c_bp1, c_bp2 = st.columns(2)
                    
                    with c_bp1:
                        st.markdown("**🔪 Bases a preparar el diumenge:**")
                        bases = menu_obj.get("bases_batch_prep_diumenge", [])
                        if bases:
                            for b in bases:
                                st.info(f"🥣 **{b.get('base', 'Base')}** ({b.get('quantitat', '')}): {b.get('utilitzacio', '')}")
                        else:
                            st.write("No calen bases prèvies per a aquest menú.")
                            
                    with c_bp2:
                        st.markdown("**🛒 Ingredients a comprar:**")
                        ings_comprar = menu_obj.get("ingredients_a_comprar", [])
                        if ings_comprar:
                            st.markdown("- " + "\n- ".join(ings_comprar))
                        else:
                            st.write("Tots els ingredients estan disponibles.")

        except Exception as e:
            st.error(f"Error carregant Menjar: {e}")

