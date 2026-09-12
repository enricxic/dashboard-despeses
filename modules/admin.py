import streamlit as st
import json
import copy
import os
import base64
from datetime import datetime, date
from core.config_manager import load_app_config, save_app_config, get_translation

def _get_eina_foto_src(foto_val):
    if not foto_val:
        return ""
    if foto_val.startswith("http://") or foto_val.startswith("https://") or foto_val.startswith("data:"):
        return foto_val
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(curr_dir, ".."))
    candidates = [
        foto_val,
        os.path.join(project_root, foto_val),
        os.path.join(os.getcwd(), foto_val)
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            try:
                with open(c, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                    ext = "png" if c.lower().endswith(".png") else "jpeg"
                    return f"data:image/{ext};base64,{b64_data}"
            except Exception:
                pass
    return foto_val

def _render_eina_thumb_html(eina, foto_src):
    e_id = eina['id']
    nom = eina['nom']
    desc = eina['desc']
    return f"""
    <label for="zoom_{e_id}" style="cursor:pointer; display:flex; justify-content:center; align-items:center; margin:0;">
        <img src="{foto_src}" 
             alt="{nom}" 
             loading="lazy" 
             title="Fes clic per veure {nom} en gran" 
             style="width:56px; height:56px; min-width:56px; min-height:56px; object-fit:cover; border-radius:8px; border:1px solid #334155; box-shadow:0 2px 4px rgba(0,0,0,0.15); transition:transform 0.15s ease;" 
        />
    </label>
    <input type="checkbox" id="zoom_{e_id}" class="eina-modal-toggle" />
    <div class="eina-modal-backdrop">
        <label for="zoom_{e_id}" class="eina-modal-close-bg"></label>
        <div class="eina-modal-box">
            <label for="zoom_{e_id}" class="eina-modal-close-btn">&times;</label>
            <h3 style="margin:0 0 14px 0; color:#f8fafc; font-size:1.25rem;">🍳 {nom}</h3>
            <div style="background:#020617; border-radius:12px; padding:14px; border:1px solid #1e293b; margin-bottom:14px; display:flex; justify-content:center;">
                <img src="{foto_src}" alt="{nom}" style="max-width:100%; max-height:420px; object-fit:contain; border-radius:8px;" />
            </div>
            <div style="color:#94a3b8; font-size:0.92rem; line-height:1.4;">{desc}</div>
        </div>
    </div>
    """

def calcular_edat(data_naix_val):
    if not data_naix_val:
        return ""
    try:
        if isinstance(data_naix_val, (datetime, date)):
            b_date = data_naix_val if isinstance(data_naix_val, date) else data_naix_val.date()
        else:
            s = str(data_naix_val).strip()
            if not s:
                return ""
            if '/' in s:
                p = [int(x) for x in s.split('/')]
                if len(p) == 3:
                    if p[0] > 1000:  # YYYY/MM/DD
                        b_date = date(p[0], p[1], p[2])
                    else:            # DD/MM/YYYY
                        b_date = date(p[2], p[1], p[0])
                else:
                    return str(data_naix_val)
            elif '-' in s:
                p = [int(x) for x in s.split('-')]
                if len(p) == 3:
                    if p[0] > 1000:  # YYYY-MM-DD
                        b_date = date(p[0], p[1], p[2])
                    else:            # DD-MM-YYYY
                        b_date = date(p[2], p[1], p[0])
                else:
                    return str(data_naix_val)
            else:
                return str(data_naix_val)
        today = date.today()
        age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
        return age
    except Exception:
        return str(data_naix_val)

def _format_list_to_comma_str(val):
    if isinstance(val, list):
        return ", ".join([str(x).strip() for x in val if str(x).strip()])
    elif isinstance(val, str):
        val_clean = val.strip()
        if val_clean.startswith("[") and val_clean.endswith("]"):
            try:
                parsed = json.loads(val_clean.replace("'", '"'))
                if isinstance(parsed, list):
                    return ", ".join([str(x).strip() for x in parsed if str(x).strip()])
            except Exception:
                pass
        return val_clean
    return ""

def _parse_comma_str_to_list(val):
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if not val or not isinstance(val, str):
        return []
    val_clean = val.strip()
    if val_clean.startswith("[") and val_clean.endswith("]"):
        try:
            parsed = json.loads(val_clean.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    return [x.strip() for x in val_clean.split(",") if x.strip()]

def _clear_all_admin_widget_keys():
    """Neteja totes les claus de sessió de widgets d'Admin per forçar Streamlit a llegir des del disc (config.json)."""
    prefixes = (
        "f_", "t_", "b_", "adm_", "tit_", "mn_", "chk_eina_", "tog_", 
        "input_p", "picker_c", "slider_tamany", "radio_tema", "sel_idioma", 
        "r_carn", "r_lleg", "r_peix", "r_emb", "r_no_rep", "r_forn", "r_mode", "r_com",
        "save_", "btn_preset_c", "chk_val", "harness_"
    )
    keys_to_del = [
        k for k in list(st.session_state.keys()) 
        if any(k.startswith(p) for p in prefixes) and k not in ("cfg_active_tab", "harness_single_result", "harness_results")
    ]
    for k in keys_to_del:
        del st.session_state[k]

def _clear_section_session_keys(prefix):
    keys_to_del = [k for k in list(st.session_state.keys()) if k.startswith(prefix)]
    for k in keys_to_del:
        del st.session_state[k]

def _get_updated_member_from_state(mem):
    m = copy.deepcopy(mem)
    m_id = m.get("id")
    if not m_id:
        return m
    if f"f_nom_{m_id}" in st.session_state:
        m["nom"] = st.session_state[f"f_nom_{m_id}"]
    if f"f_rol_{m_id}" in st.session_state:
        m["rol"] = st.session_state[f"f_rol_{m_id}"]
    if f"f_actiu_{m_id}" in st.session_state:
        m["actiu"] = bool(st.session_state[f"f_actiu_{m_id}"])
    if f"f_naix_{m_id}" in st.session_state:
        m_naix = st.session_state[f"f_naix_{m_id}"]
        m["data_naixement"] = m_naix
        calc_e = str(calcular_edat(m_naix)) if str(calcular_edat(m_naix)).isdigit() else str(m.get("edat", ""))
        m["edat"] = calc_e
    if f"f_al_{m_id}" in st.session_state:
        al_lst = _parse_comma_str_to_list(st.session_state[f"f_al_{m_id}"])
        m["alergies"] = al_lst
        m["circunstancies"] = al_lst
    if f"f_vt_{m_id}" in st.session_state:
        m["vetos"] = _parse_comma_str_to_list(st.session_state[f"f_vt_{m_id}"])
    if f"f_com_{m_id}" in st.session_state:
        m["comodins"] = _parse_comma_str_to_list(st.session_state[f"f_com_{m_id}"])
    if f"f_icon_{m_id}" in st.session_state:
        m["icona"] = st.session_state[f"f_icon_{m_id}"]
    if f"f_gcal_{m_id}" in st.session_state:
        m["google_calendar_ical"] = st.session_state[f"f_gcal_{m_id}"]
    if f"f_col_{m_id}" in st.session_state:
        m["color"] = st.session_state[f"f_col_{m_id}"]
    return m

def _on_delete_family_member(mem_id):
    cur_cfg = load_app_config()
    current_fam = cur_cfg.get("familia", [])
    del_nom = ""
    new_fam = []
    for m in current_fam:
        m_id = m.get("id")
        if m_id == mem_id:
            del_nom = m.get("nom", "")
            continue
        new_fam.append(_get_updated_member_from_state(m))
    cur_cfg["familia"] = new_fam
    if save_app_config(cur_cfg):
        _clear_section_session_keys("f_")
        st.session_state["flash_success"] = f"🗑️ Membre '{del_nom}' eliminat i desat a config.json!"

def _on_add_family_member():
    cur_cfg = load_app_config()
    current_fam = cur_cfg.get("familia", [])
    updated_fam = [_get_updated_member_from_state(m) for m in current_fam]
    next_id = max([m.get("id", 0) for m in updated_fam] + [0]) + 1
    updated_fam.append({
        "id": next_id,
        "nom": f"Membre {len(updated_fam) + 1}",
        "rol": "Familiar",
        "data_naixement": "",
        "edat": "",
        "actiu": True,
        "alergies": [],
        "circunstancies": [],
        "vetos": [],
        "comodins": [],
        "icona": "👤",
        "google_calendar_ical": "",
        "color": "#3b82f6"
    })
    cur_cfg["familia"] = updated_fam
    if save_app_config(cur_cfg):
        _clear_section_session_keys("f_")
        st.session_state["flash_success"] = "✅ Nou membre afegit i desat a config.json!"

def _on_save_family_members():
    cur_cfg = load_app_config()
    current_fam = cur_cfg.get("familia", [])
    updated_fam = [_get_updated_member_from_state(m) for m in current_fam]
    cur_cfg["familia"] = updated_fam
    if save_app_config(cur_cfg):
        _clear_section_session_keys("f_")
        st.session_state["flash_success"] = "✅ Membres de la família desats correctament a config.json!"

def _render_flash_message():
    if "flash_success" in st.session_state:
        msg = st.session_state.pop("flash_success")
        st.toast(msg, icon="💾")
        st.success(msg)

def _on_eina_change(e_id):
    val = st.session_state.get(f"chk_eina_{e_id}")
    cur_cfg = load_app_config()
    if "eines_cuina" not in cur_cfg:
        cur_cfg["eines_cuina"] = {}
    cur_cfg["eines_cuina"][e_id] = bool(val)
    if save_app_config(cur_cfg):
        status_txt = "activada" if val else "desactivada"
        st.session_state["flash_success"] = f"✅ Eina de cuina {status_txt} i desada correctament!"

def _on_icona_change(key_m):
    val = st.session_state.get(f"tog_{key_m}")
    cur_cfg = load_app_config()
    if "icones_actives" not in cur_cfg:
        cur_cfg["icones_actives"] = {}
    cur_cfg["icones_actives"][key_m] = bool(val)
    if save_app_config(cur_cfg):
        status_txt = "activada" if val else "desactivada"
        st.session_state["flash_success"] = f"✅ Icona d'inici {status_txt} i desada correctament!"

def render():
    cfg = load_app_config()
    lang = cfg.get("idioma", "ca")
    
    # ---------------- CSS ESTIL GOOGLE CHROME SETTINGS ----------------
    is_dark = st.session_state.get("app_theme", cfg.get("tema", "Fosc")) != "Clar"
    
    bg_card = "#1e293b" if is_dark else "#ffffff"
    border_color = "#334155" if is_dark else "#dadce0"
    text_primary = "#f8fafc" if is_dark else "#202124"
    text_secondary = "#94a3b8" if is_dark else "#5f6368"
    active_pill_bg = "#25344d" if is_dark else "#e8f0fe"
    active_pill_text = "#8ab4f8" if is_dark else "#1a73e8"
    hover_pill_bg = "rgba(255,255,255,0.06)" if is_dark else "#f1f3f4"
    search_bg = "#0f172a" if is_dark else "#f1f3f4"
    search_border = "#334155" if is_dark else "transparent"
    
    st.markdown(f"""
        <style>
        .chrome-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 18px;
            margin-bottom: 20px;
            background: {bg_card};
            border-bottom: 1px solid {border_color};
            border-radius: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12);
        }}
        .chrome-title-group {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .chrome-logo {{
            font-size: 1.8rem;
            line-height: 1;
        }}
        .chrome-title {{
            font-size: 1.35rem;
            font-weight: 600;
            color: {text_primary};
            letter-spacing: -0.2px;
            margin: 0;
        }}
        .chrome-search-box {{
            flex: 1;
            max-width: 480px;
            margin: 0 20px;
        }}
        .chrome-card {{
            background: {bg_card};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 18px 22px;
            margin-bottom: 18px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .chrome-card-header {{
            font-size: 1.1rem;
            font-weight: 600;
            color: {text_primary};
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .chrome-card-desc {{
            font-size: 0.86rem;
            color: {text_secondary};
            margin-bottom: 16px;
            line-height: 1.4;
        }}
        .chrome-profile-banner {{
            display: flex;
            align-items: center;
            gap: 18px;
            padding: 16px;
            background: {search_bg};
            border: 1px solid {border_color};
            border-radius: 10px;
            margin-bottom: 18px;
        }}
        .chrome-profile-avatar {{
            width: 58px;
            height: 58px;
            border-radius: 50%;
            background: #f39c12;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.9rem;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}
        .chrome-profile-info {{
            flex: 1;
        }}
        .chrome-profile-name {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {text_primary};
            margin: 0 0 3px 0;
        }}
        .chrome-profile-sub {{
            font-size: 0.83rem;
            color: {text_secondary};
            margin: 0;
        }}
        .chrome-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid {border_color};
        }}
        .chrome-row:last-child {{
            border-bottom: none;
        }}
        .chrome-row-label {{
            font-size: 0.92rem;
            font-weight: 500;
            color: {text_primary};
            margin: 0;
        }}
        .chrome-row-sub {{
            font-size: 0.8rem;
            color: {text_secondary};
            margin: 2px 0 0 0;
        }}
        .preview-box {{
            padding: 18px;
            border-radius: 10px;
            border: 2px dashed {border_color};
            background: {search_bg};
            text-align: center;
            margin: 12px 0;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    from modules.avatar_widget import render_header_with_avatar
    
    def _render_search_input():
        st.text_input("🔍 Cercar ajustos", placeholder="Cercar a la configuració...", label_visibility="collapsed", key="cfg_search")

    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>⚙️ Configuració Global</h2>", "admin", extra_button_fn=_render_search_input)
    search_query = st.session_state.get("cfg_search", "")
    st.write("")
    
    # Layout en dues columnes (Menú lateral Chrome a l'esquerra + Contingut a la dreta)
    col_menu, col_body = st.columns([3, 7], gap="large")
    
    with col_menu:
        st.markdown(f"<div style='font-size:0.8rem; text-transform:uppercase; font-weight:700; color:{text_secondary}; margin-bottom:8px; padding-left:6px;'>Seccions</div>", unsafe_allow_html=True)
        
        sections = [
            ("admin", "👤 Administrador"),
            ("titol", "🏷️ Títol de la casa"),
            ("familia", "👨‍👩‍👧‍👦 Família"),
            ("menjar", "🍽️ Menús i Nutrició"),
            ("harness", "🧪 Laboratori IA (Harness)"),
            ("tutelats", "🤝 Tutelats"),
            ("bancs", "🏦 Bancs"),
            ("tema", "🎨 Aspecte i Tema"),
            ("icones", "🔘 Icones pantalla d'inici"),
            ("idioma", "🌐 Idiomes")
        ]
        
        # Filtrar si s'està cercant
        if search_query:
            q = search_query.lower()
            filtered_sections = [s for s in sections if q in s[1].lower() or q in s[0]]
            if not filtered_sections:
                filtered_sections = sections
        else:
            filtered_sections = sections
            
        if "tab" in st.query_params:
            st.session_state.cfg_active_tab = st.query_params.get("tab")
            try:
                del st.query_params["tab"]
            except Exception:
                pass

        if "cfg_active_tab" not in st.session_state:
            st.session_state.cfg_active_tab = "admin"
            
        for key_s, label_s in filtered_sections:
            is_active = (st.session_state.cfg_active_tab == key_s)
            btn_type = "primary" if is_active else "secondary"
            if st.button(label_s, key=f"nav_btn_{key_s}", use_container_width=True, type=btn_type):
                if st.session_state.cfg_active_tab != key_s:
                    _clear_all_admin_widget_keys()
                st.session_state.cfg_active_tab = key_s
                st.rerun()
                
    with col_body:
        _render_flash_message()

        active = st.session_state.get("cfg_active_tab", "admin")
        
        # =========================================================================
        # 1. SECCIÓ: ADMINISTRADOR
        # =========================================================================
        if active == "admin":
            admin_cfg = cfg.get("admin", {})
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">👤 Administrador del Sistema</div>
                <div class="chrome-card-desc">Gestiona el compte principal, el perfil i les credencials d'accés mestres.</div>
                <div class="chrome-profile-banner">
                    <div class="chrome-profile-avatar">{admin_cfg.get('avatar', '👑')}</div>
                    <div class="chrome-profile-info">
                        <div class="chrome-profile-name">{admin_cfg.get('nom', 'Enric Xicars')}</div>
                        <div class="chrome-profile-sub">Sincronitzat amb <b>{admin_cfg.get('email', 'enricxicars@gmail.com')}</b></div>
                        <div class="chrome-profile-sub" style="color:#22c55e; margin-top:2px;">● Rol actiu: {admin_cfg.get('rol', 'Administrador')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
                st.markdown("#### ✏️ Dades de contacte i perfil")
                c1, c2 = st.columns(2)
                with c1:
                    new_nom = st.text_input("Nom de l'administrador", value=admin_cfg.get("nom", "Enric Xicars"))
                    new_email = st.text_input("Correu electrònic", value=admin_cfg.get("email", "enricxicars@gmail.com"))
                with c2:
                    new_tel = st.text_input("Telèfon de contacte", value=admin_cfg.get("telefon", "+34 600 000 000"))
                    avatar_options = ["👑", "👤", "⭐", "🏠", "🛡️", "🚀"]
                    cur_avatar = admin_cfg.get("avatar", "👑")
                    av_idx = avatar_options.index(cur_avatar) if cur_avatar in avatar_options else 0
                    new_avatar = st.selectbox("Icona / Avatar", avatar_options, index=av_idx)
                
                st.markdown("---")
                st.markdown("#### 🔒 Seguretat i PIN mestre")
                c_pin1, c_pin2 = st.columns(2)
                with c_pin1:
                    new_pin = st.text_input("PIN d'accés / Contrasenya", value=admin_cfg.get("pin", "1234"), type="password")
                with c_pin2:
                    new_rol = st.selectbox("Rol per defecte", ["Administrador", "Usuari Avançat", "Convidat"], index=0)
                
                st.write("")
                _render_flash_message()
                if st.button("💾 Desar Dades d'Administrador", type="primary", use_container_width=True, key="save_admin"):
                    cur_cfg = load_app_config()
                    cur_cfg["admin"] = {
                        "nom": new_nom,
                        "email": new_email,
                        "telefon": new_tel,
                        "avatar": new_avatar,
                        "pin": new_pin,
                        "rol": new_rol
                    }
                    if save_app_config(cur_cfg):
                        st.session_state["flash_success"] = "✅ Dades d'administrador actualitzades correctament!"
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 2. SECCIÓ: TÍTOL DE LA CASA
        # =========================================================================
        elif active == "titol":
            casa_cfg = cfg.get("casa", {})
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🏷️ Títol de la Casa (Pantalla d'Inici)</div>
                <div class="chrome-card-desc">Personalitza com s'anomena la teva llar, tria els colors per a cadascuna de les dues parts del nom i ajusta el tamany de la lletra. Pots fer clic als botons de colors predeterminats (<b>#407faf</b> i <b>#73ad69</b>). Si només poses una paraula, quedarà automàticament centrada.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            
            # Gestionar estat dels colors si es cliquen els predeterminats
            if "picker_c1" not in st.session_state:
                st.session_state["picker_c1"] = casa_cfg.get("color1", "#407faf")
            if "picker_c2" not in st.session_state:
                st.session_state["picker_c2"] = casa_cfg.get("color2", "#73ad69")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### 🏷️ Primera Paraula")
                p1 = st.text_input("Text 1", value=casa_cfg.get("paraula1", "Xiqui"), key="input_p1")
                
                c_pick1, c_preset1 = st.columns([1.2, 1.8], vertical_alignment="center")
                with c_preset1:
                    if st.button("🟦 #407faf (Blau original)", key="btn_preset_c1", use_container_width=True):
                        st.session_state["picker_c1"] = "#407faf"
                        st.rerun()
                with c_pick1:
                    col1 = st.color_picker("Color 1", key="picker_c1")
                
            with c2:
                st.markdown("##### 🏷️ Segona Paraula (Opcional)")
                p2 = st.text_input("Text 2", value=casa_cfg.get("paraula2", "House"), key="input_p2")
                
                c_pick2, c_preset2 = st.columns([1.2, 1.8], vertical_alignment="center")
                with c_preset2:
                    if st.button("🟩 #73ad69 (Verd original)", key="btn_preset_c2", use_container_width=True):
                        st.session_state["picker_c2"] = "#73ad69"
                        st.rerun()
                with c_pick2:
                    col2 = st.color_picker("Color 2", key="picker_c2")
                
            st.markdown("##### 🔤 Tamany del Text")
            current_tamany = max(40, min(120, int(casa_cfg.get("tamany_lletra", 58))))
            tamany_lletra = st.slider("Tamany de la lletra del títol (píxels)", min_value=40, max_value=120, value=current_tamany, step=2, key="slider_tamany")
                
            st.markdown("#### 👁️ Previsualització en directe")
            slogan_text = get_translation("slogan", lang)
            
            p1_clean = p1.strip()
            p2_clean = p2.strip()
            if p1_clean and p2_clean:
                preview_title_html = f'<span style="color: {col1};">{p1_clean}</span><span style="color: {col2};">{p2_clean}</span>'
            elif p1_clean:
                preview_title_html = f'<span style="color: {col1};">{p1_clean}</span>'
            elif p2_clean:
                preview_title_html = f'<span style="color: {col2};">{p2_clean}</span>'
            else:
                preview_title_html = f'<span style="color: {col1};">Xiqui</span><span style="color: {col2};">House</span>'

            st.markdown(f"""
            <div class="preview-box">
                <div style="font-size: 0.8rem; color: {text_secondary}; text-transform: uppercase; margin-bottom: 8px;">Com es veurà a la pantalla d'inici:</div>
                <div style="font-size: {tamany_lletra}px; font-weight: 800; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; letter-spacing: 0.5px; line-height: 1.1; text-align: center;">
                    {preview_title_html}
                </div>
                <div style="font-size: {max(12, int(tamany_lletra * 0.36))}px; font-weight: 800; color: #407faf; letter-spacing: 1.8px; margin-top: 12px; text-transform: uppercase; text-align: center;">
                    {slogan_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            _render_flash_message()
            if st.button("💾 Desar Títol de la Casa", type="primary", use_container_width=True, key="save_titol"):
                cur_cfg = load_app_config()
                cur_cfg["casa"] = {
                    "paraula1": p1,
                    "color1": col1,
                    "paraula2": p2,
                    "color2": col2,
                    "tamany_lletra": tamany_lletra
                }
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = "✅ Títol de la casa desat correctament!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 3. SECCIÓ: FAMÍLIA
        # =========================================================================
        elif active == "familia":
            familia_list = list(cfg.get("familia", []))
            num_membres = len(familia_list)
            
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">👨‍👩‍👧‍👦 Membres de la Família ({num_membres} / 10)</div>
                <div class="chrome-card-desc">Afegeix i gestiona els membres de la llar (fins a un màxim de 10). Aquesta informació s'utilitza pel control de medicació, menús familiars, al·lèrgies, vetos personals i assistent IA.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            
            # Botó d'afegir membre
            if num_membres < 10:
                col_add1, col_add2 = st.columns([8, 2])
                with col_add2:
                    st.button("➕ Afegir Membre", type="primary", use_container_width=True, key="btn_add_fam_mem", on_click=_on_add_family_member)
            else:
                st.info("ℹ️ S'ha assolit el límit màxim de 10 membres a la família.")
                
            st.write("")
            
            # Llista de membres
            icons_pool = ["👨", "👩", "👦", "👧", "👶", "👴", "👵", "🐶", "🐱", "🧑", "👑", "⭐"]
            roles_pool = ["Pare", "Mare", "Fill", "Filla", "Avi", "Àvia", "Germà", "Germana", "Mascota", "Altres"]
            
            for i, mem in enumerate(familia_list):
                mem_id = mem.get("id", i + 1)
                raw_naix = mem.get("data_naixement", "")
                raw_edat = mem.get("edat", "")
                calc_e = calcular_edat(raw_naix if raw_naix else raw_edat)
                edat_badge = f" - 🎂 {calc_e} anys" if str(calc_e).isdigit() else ""
                is_mem_actiu = mem.get("actiu", True)
                estat_badge = "🟢 Present a la llar" if is_mem_actiu else "⚪ Fora de la llar"
                
                with st.expander(f"{mem.get('icona', '👤')} {mem.get('nom', f'Membre {i+1}')} ({mem.get('rol', 'Familiar')}){edat_badge} · {estat_badge}", expanded=True):
                    c_act1, c_del_top = st.columns([8.2, 1.8], vertical_alignment="center")
                    with c_act1:
                        m_actiu = st.toggle("🏠 Membre actiu a la llar (Participa en menús i rutines diàries)", value=is_mem_actiu, key=f"f_actiu_{mem_id}")
                        if not m_actiu:
                            st.caption("ℹ️ *Aquest membre viu fora o està temporalment absent. Es guarden totes les meves dades però no es computarà per defecte als menús setmanals.*")
                    with c_del_top:
                        st.button("🗑️ Esborrar", key=f"f_del_{mem_id}", use_container_width=True, on_click=_on_delete_family_member, args=(mem_id,))
                    
                    st.write("")
                    c1, c2, c3, c4 = st.columns([1.2, 3, 2.5, 2.3])
                    with c1:
                        cur_icon = mem.get("icona", "👤")
                        ic_idx = icons_pool.index(cur_icon) if cur_icon in icons_pool else 0
                        st.selectbox("Icona", icons_pool, index=ic_idx, key=f"f_icon_{mem_id}")
                    with c2:
                        st.text_input("Nom", value=mem.get("nom", ""), key=f"f_nom_{mem_id}")
                    with c3:
                        cur_r = mem.get("rol", "Familiar")
                        r_idx = roles_pool.index(cur_r) if cur_r in roles_pool else len(roles_pool)-1
                        st.selectbox("Rol / Relació", roles_pool, index=r_idx, key=f"f_rol_{mem_id}")
                    with c4:
                        init_naix = mem.get("data_naixement", "")
                        if not init_naix and str(mem.get("edat", "")).count("-") == 2:
                            p_old = str(mem.get("edat", "")).split("-")
                            if len(p_old) == 3 and len(p_old[0]) == 4:
                                init_naix = f"{p_old[2]}/{p_old[1]}/{p_old[0]}"
                            else:
                                init_naix = str(mem.get("edat", ""))
                        elif init_naix and '-' in init_naix:
                            p_iso = init_naix.split('-')
                            if len(p_iso) == 3 and len(p_iso[0]) == 4:
                                init_naix = f"{p_iso[2]}/{p_iso[1]}/{p_iso[0]}"
                        m_naix = st.text_input("🎂 Data naixement", value=init_naix, placeholder="ex: 15/05/1980", key=f"f_naix_{mem_id}")
                        calc_now = calcular_edat(m_naix if m_naix else mem.get("edat", ""))
                        if str(calc_now).isdigit():
                            st.caption(f"🎂 Edat: **{calc_now} anys** (recalculada)")
                        elif mem.get("edat"):
                            st.caption(f"Edat registrada: {mem.get('edat')} anys")
                        
                    c_al1, c_vt1 = st.columns(2)
                    with c_al1:
                        cur_al_str = _format_list_to_comma_str(mem.get("alergies", mem.get("circunstancies", [])))
                        st.text_input("🏥 Al·lèrgies mèdiques i intoleràncies (bloqueig)", value=cur_al_str, placeholder="ex: Sense Gluten, Sense Lactosa, Diabètic...", key=f"f_al_{mem_id}")
                    with c_vt1:
                        cur_vt_str = _format_list_to_comma_str(mem.get("vetos", []))
                        st.text_input("🚫 Vetos i aversions personals (no li agrada)", value=cur_vt_str, placeholder="ex: fetge, casqueria, conill, bledes...", key=f"f_vt_{mem_id}")
                        
                    c_com1, c_gcal2_col = st.columns([6.5, 3.5])
                    with c_com1:
                        cur_com_str = _format_list_to_comma_str(mem.get("comodins", []))
                        st.text_input("🍗 Plats Comodí Favorits (alternatives ràpides)", value=cur_com_str, placeholder="ex: pit de pollastre a la planxa, truita francesa...", key=f"f_com_{mem_id}")
                    with c_gcal2_col:
                        cur_col = mem.get("color", "#3b82f6" if i % 2 == 0 else "#ec4899")
                        st.color_picker("Color al calendari", value=cur_col, key=f"f_col_{mem_id}")
                        
                    st.text_input("📅 Enllaç privat iCal de Google Calendar (opcional)", value=mem.get("google_calendar_ical", ""), key=f"f_gcal_{mem_id}", placeholder="https://calendar.google.com/calendar/ical/.../basic.ics")
                        
            st.write("")
            _render_flash_message()
            st.button("💾 Desar Membres de la Família", type="primary", use_container_width=True, key="save_fam", on_click=_on_save_family_members)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 4. SECCIÓ: MENÚS I NUTRICIÓ
        # =========================================================================
        elif active == "menjar":
            regles = cfg.get("regles_menjar", {
                "max_carn_vermella": 1,
                "min_peix": 2,
                "min_llegums": 2,
                "max_embotits_sopar": 2,
                "no_repetir_hidrats": True,
                "mode_apats": "Tota la setmana (Dinars i Sopars - 14 àpats)",
                "comensals_defecte": 3
            })
            
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🍽️ Menús i Regles Nutricionals de la Llar</div>
                <div class="chrome-card-desc">Defineix els límits i directrius setmanals d'alimentació, la rotació d'ingredients i el format de planificació per defecte de XiquiHouse.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            st.markdown("#### 🥗 Regles de Salut i Freqüències Setmanals")
            st.markdown("<div style='font-size:0.86rem; color:#94a3b8; margin-bottom:12px;'>Aquestes regles les avaluarà automàticament el generador de menús i el banc de proves (Harness).</div>", unsafe_allow_html=True)
            
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                r_carn = st.slider("🔴 Màxim de dies de Carn Vermella / setmana", min_value=0, max_value=7, value=int(regles.get("max_carn_vermella", 1)), help="Limita els àpats amb vedella, bou, porc o carn vermella.")
                r_lleg = st.slider("🌱 Mínim de dies de Llegums / setmana", min_value=0, max_value=7, value=int(regles.get("min_llegums", 2)), help="Garanteix plats amb llenties, cigrons, mongetes o pèsols.")
            with c_r2:
                r_peix = st.slider("🐟 Mínim de dies de Peix / setmana", min_value=0, max_value=7, value=int(regles.get("min_peix", 2)), help="Promou el consum de peix blanc i blau.")
                r_emb = st.slider("🥪 Màxim de sopars d'Embotits / Freds / setmana", min_value=0, max_value=7, value=int(regles.get("max_embotits_sopar", 2)), help="Evita abusar de sopars a base d'embotits processats.")
            
            st.markdown("---")
            st.markdown("#### 🔄 Control de Repeticions i Varietat")
            r_no_rep = st.toggle("🚫 Evitar hidrats de carboni idèntics dos dies seguits (Arròs / Pasta)", value=bool(regles.get("no_repetir_hidrats", True)), help="Si dilluns es menja arròs, dimarts no es podrà programar arròs de nou.")
            
            st.markdown("---")
            st.markdown("#### 🔥 Ús del Forn")
            st.markdown("<div style='font-size:0.86rem; color:#94a3b8; margin-bottom:8px;'>Configura la disponibilitat habitual del forn. Si un membre de la família fa una petició concreta d'un plat al forn entre setmana (ex. solomillo al forn dimecres), aquesta petició tindrà prioritat absoluta i obviarà la limitació.</div>", unsafe_allow_html=True)
            forn_options = [
                "Cada dia / Qualsevol dia",
                "Només cap de setmana (Dissabte i Diumenge)"
            ]
            cur_forn = regles.get("us_forn", forn_options[1])
            forn_idx = forn_options.index(cur_forn) if cur_forn in forn_options else 1
            r_forn = st.selectbox("Disponibilitat habitual del forn", forn_options, index=forn_idx, help="Si es tria 'Només cap de setmana', els plats automàtics que requereixen forn només es programaran dissabte o diumenge, excepte si hi ha petició expressa.")
            
            st.markdown("---")
            st.markdown("#### 🍳 Aparells i Eines de Cuina Disponibles a la Llar")
            st.markdown("<div style='font-size:0.86rem; color:#94a3b8; margin-bottom:12px;'>El nivell de complexitat i les tècniques de les receptes proposades per la IA s'adaptaran exclusivament a l'equipament disponible a la llar.</div>", unsafe_allow_html=True)
            
            st.markdown(
                """
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.eina-marker) {
                    min-height: 104px !important;
                    height: 104px !important;
                    display: flex !important;
                    flex-direction: column !important;
                    justify-content: center !important;
                    margin-bottom: 6px !important;
                }
                .eina-desc-fixed {
                    font-size: 0.78rem;
                    color: #94a3b8;
                    line-height: 1.25;
                    height: 32px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    margin-top: 1px;
                }
                .eina-modal-toggle {
                    display: none !important;
                }
                .eina-modal-backdrop {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: rgba(15, 23, 42, 0.88);
                    backdrop-filter: blur(6px);
                    z-index: 999999;
                    justify-content: center;
                    align-items: center;
                }
                .eina-modal-toggle:checked + .eina-modal-backdrop {
                    display: flex !important;
                }
                .eina-modal-close-bg {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    cursor: pointer;
                }
                .eina-modal-box {
                    position: relative;
                    background: #0f172a;
                    border: 1px solid #334155;
                    border-radius: 16px;
                    padding: 24px;
                    max-width: 480px;
                    width: 90vw;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
                    color: #f8fafc;
                    text-align: center;
                    z-index: 1000000;
                }
                .eina-modal-close-btn {
                    position: absolute;
                    top: 14px;
                    right: 14px;
                    background: #1e293b;
                    border: 1px solid #475569;
                    color: #94a3b8;
                    border-radius: 50%;
                    width: 32px;
                    height: 32px;
                    font-size: 1.3rem;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    line-height: 1;
                    text-decoration: none;
                }
                .eina-modal-close-btn:hover {
                    color: #ffffff;
                    background: #334155;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            CATALEG_EINES_CUINA = [
                {"id": "forn", "nom": "Forn", "foto": "imatges/forn.png", "desc": "Rostits, gratinats, pastissos i pizzes"},
                {"id": "microones", "nom": "Microones", "foto": "imatges/microones.jpg", "desc": "Escalfat ràpid i vapor"},
                {"id": "airfryer", "nom": "Airfryer", "foto": "imatges/airfryer.jpg", "desc": "Fregits saludables i cruixents"},
                {"id": "bascula", "nom": "Bàscula de cuina", "foto": "imatges/bascula.jpg", "desc": "Pesat precís de racions"},
                {"id": "minipimer", "nom": "Minipimer", "foto": "imatges/minipimer.jpg", "desc": "Cremes, purés i maioneses"},
                {"id": "batedora_vas", "nom": "Batedora de vas", "foto": "imatges/batedora_vas.jpg", "desc": "Batuts, smoothies i gaspatxos"},
                {"id": "motlles_silicona", "nom": "Motlles de silicona", "foto": "imatges/motlles_silicona.jpg", "desc": "Rebosteria i flameres"},
                {"id": "olla_pressio", "nom": "Olla a pressió", "foto": "imatges/olla_pressio.jpg", "desc": "Llegums i estofats exprés"},
                {"id": "liquadora", "nom": "Liquadora", "foto": "imatges/liquadora.jpg", "desc": "Sucs naturals i liquats"},
                {"id": "tallafiambres", "nom": "Tallafiambres", "foto": "imatges/tallafiambres.jpg", "desc": "Talls fins d'embotits"},
                {"id": "robot_cuina", "nom": "Robot de cuina", "foto": "imatges/robot_cuina.jpg", "desc": "Emulsions i cocció guiada"},
                {"id": "picadora", "nom": "Picadora", "foto": "imatges/picadora.jpg", "desc": "Picar carn i sofregits"},
                {"id": "sifo_n2o", "nom": "Sifó N2O", "foto": "imatges/sifo_n2o.jpg", "desc": "Espumes d'avantguarda"},
                {"id": "mandolina", "nom": "Mandolina", "foto": "imatges/mandolina.jpg", "desc": "Talls laminats precisos"},
            ]
            
            cur_eines = cfg.get("eines_cuina", {})
            updated_eines = {}
            
            cols_eines = st.columns(3)
            for idx_e, eina in enumerate(CATALEG_EINES_CUINA):
                col_e = cols_eines[idx_e % 3]
                e_id = eina["id"]
                val_def = cur_eines.get(e_id, True if e_id in ["forn", "microones", "airfryer", "bascula", "minipimer", "batedora_vas", "motlles_silicona", "olla_pressio", "picadora", "mandolina"] else False)
                with col_e:
                    with st.container(border=True):
                        st.markdown("<span class='eina-marker' style='display:none;'></span>", unsafe_allow_html=True)
                        foto_src = _get_eina_foto_src(eina["foto"])
                        c_ico, c_chk = st.columns([1.1, 3.4], vertical_alignment="center")
                        with c_ico:
                            st.markdown(_render_eina_thumb_html(eina, foto_src), unsafe_allow_html=True)
                        with c_chk:
                            chk_val = st.checkbox(f"**{eina['nom']}**", value=bool(val_def), key=f"chk_eina_{e_id}", on_change=_on_eina_change, args=(e_id,))
                            st.markdown(f"<div class='eina-desc-fixed'>{eina['desc']}</div>", unsafe_allow_html=True)
                        updated_eines[e_id] = chk_val
            
            st.markdown("---")
            st.markdown("#### 📅 Format i Hàbits de Planificació")
            c_p1, c_p2 = st.columns([7, 3])
            with c_p1:
                mode_options = [
                    "Tota la setmana (Dinars i Sopars - 14 àpats)",
                    "Feiners només Sopars + Cap de setmana complet (9 àpats)",
                    "Dinars de carmanyola per a la feina + Sopars a casa"
                ]
                cur_mode = regles.get("mode_apats", mode_options[0])
                mode_idx = mode_options.index(cur_mode) if cur_mode in mode_options else 0
                r_mode = st.selectbox("Format per defecte del menú", mode_options, index=mode_idx)
            with c_p2:
                r_com = st.number_input("👥 Comensals per defecte", min_value=1, max_value=20, value=int(regles.get("comensals_defecte", 3)), step=1)
                
            st.write("")
            _render_flash_message()
            if st.button("💾 Desar Regles de Menús i Nutrició", type="primary", use_container_width=True, key="save_regles_menjar"):
                cur_cfg = load_app_config()
                cur_cfg["regles_menjar"] = {
                    "max_carn_vermella": r_carn,
                    "min_peix": r_peix,
                    "min_llegums": r_lleg,
                    "max_embotits_sopar": r_emb,
                    "no_repetir_hidrats": r_no_rep,
                    "us_forn": r_forn,
                    "mode_apats": r_mode,
                    "comensals_defecte": r_com
                }
                cur_cfg["eines_cuina"] = updated_eines
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = "✅ Regles de menús, nutrició i eines de cuina desades correctament!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # SECCIÓ: LABORATORI IA / HARNESS
        # =========================================================================
        elif active == "harness":
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🧪 Laboratori d'Avaluació IA (Harness)</div>
                <div class="chrome-card-desc">Banc de proves automatitzat per mesurar la seguretat d'al·lèrgies, desdoblament de vetos personals, regles de la llar, zero repeticions d'hidrats i format JSON abans de posar els menús en marxa.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            st.markdown("#### ⚙️ Configuració de la Prova")
            
            c_m1, c_m2 = st.columns([6, 4])
            with c_m1:
                model_options = ["gemini-2.5-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"]
                selected_model = st.selectbox("Model d'IA a avaluar:", model_options, index=0, key="harness_model_sel", help="Selecciona el model de Google Gemini per al test. Si un model dóna límit de quota (429), pots provar-ne un altre.")
            with c_m2:
                default_key = st.secrets.get("GEMINI_API_KEY", "")
                if default_key:
                    st.success("🔑 Clau GEMINI_API_KEY detectada als Secrets")
                    active_api_key = default_key
                else:
                    active_api_key = st.text_input("🔑 Clau d'API Gemini:", type="password", key="harness_key_input")
            
            try:
                from core.harness import (
                    load_harness_cases, run_harness_single_test, generate_harness_markdown_report, generate_harness_txt_report,
                    get_harness_status, start_harness_suite_background, clear_harness_status
                )
            except ImportError:
                import importlib
                import core.harness as ch
                importlib.reload(ch)
                from core.harness import (
                    load_harness_cases, run_harness_single_test, generate_harness_markdown_report, generate_harness_txt_report,
                    get_harness_status, start_harness_suite_background, clear_harness_status
                )

            from datetime import datetime
            import time
            
            def _format_duration_s(sec: float) -> str:
                m = int(sec // 60)
                s = int(sec % 60)
                return f"{m}m {s:02d}s" if m > 0 else f"{s}s"

            cases = load_harness_cases()
            harness_bg = get_harness_status()
            bg_status = harness_bg.get("status", "idle")
            
            st.write("")
            
            # 1. Si hi ha una bateria executant-se en segon pla
            if bg_status == "running":
                prog = harness_bg.get("progress") or {}
                curr = prog.get("current", 0)
                tot = prog.get("total", len(cases))
                title = prog.get("current_title", "Executant...")
                pct = float(prog.get("pct", 0.0))
                
                # Càlcul del temps transcorregut
                start_ts = harness_bg.get("start_ts")
                if start_ts:
                    elapsed_val = max(0.0, time.time() - float(start_ts))
                else:
                    elapsed_val = float(harness_bg.get("elapsed_s", 0.0))
                elapsed_txt = _format_duration_s(elapsed_val)
                
                st.info(f"⏳ **Bateria de proves en curs en segon pla ({curr}/{tot}):** *{title}*")
                st.progress(pct)
                st.caption(f"🚀 **Model actiu:** `{harness_bg.get('model_name', selected_model)}` | 🕒 **Iniciat:** `{harness_bg.get('started_at', '-')}` | ⏱️ **Temps transcorregut:** `{elapsed_txt}`\n\n💡 *Pots navegar lliurement per qualsevol altra secció de l'app (despeses, receptes, etc.). L'anàlisi continuarà treballant en segon pla. Fes clic a **Actualitzar Progrés** per veure l'estat actual.*")
                
                c_bg_btn1, c_bg_btn2 = st.columns([5, 5])
                with c_bg_btn1:
                    if st.button("🔄 Actualitzar Progrés", type="primary", use_container_width=True, key="btn_refresh_harness_bg", help="Refresca l'estat des del fil en segon pla"):
                        st.rerun()
                with c_bg_btn2:
                    if st.button("🛑 Cancel·lar / Reiniciar estat", use_container_width=True, key="btn_clear_harness_bg"):
                        clear_harness_status()
                        st.rerun()
                        
            else:
                # 2. Controls d'execució normals
                c_btn1, c_btn2 = st.columns([5, 5])
                with c_btn1:
                    run_all = st.button(f"▶️ Executar Bateria Completa ({len(cases)} Tests)", type="primary", use_container_width=True, key="btn_run_harness_all")
                with c_btn2:
                    selected_single = st.selectbox("O provar un cas concret:", [f"{c['id']}: {c['titol']}" for c in cases], key="sel_single_test", label_visibility="collapsed")
                    run_single = st.button("🎯 Executar només aquest cas", use_container_width=True, key="btn_run_harness_single")
                    
                if run_all:
                    if not active_api_key:
                        st.error("❌ Cal disposar d'una clau d'API per executar les proves.")
                    else:
                        st.session_state.harness_single_result = None
                        ok_start = start_harness_suite_background(api_key=active_api_key, model_name=selected_model)
                        if ok_start:
                            st.success("🚀 Bateria iniciada en segon pla!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Ja hi ha una execució en curs.")
                            
                elif run_single:
                    if not active_api_key:
                        st.error("❌ Cal disposar d'una clau d'API per executar la prova.")
                    else:
                        target_id = selected_single.split(":")[0].strip()
                        target_case = next((c for c in cases if c["id"] == target_id), None)
                        if target_case:
                            with st.spinner(f"Avaluant {target_case['titol']}..."):
                                single_res = run_harness_single_test(target_case, api_key=active_api_key, model_name=selected_model)
                                st.session_state.harness_single_result = single_res
                                st.rerun()
            
            # Mostra de Resultats Globals (de segon pla o de sessió)
            suite_data = harness_bg.get("results") if bg_status == "completed" else st.session_state.get("harness_results")
            
            if suite_data and isinstance(suite_data, dict):
                res = suite_data
                st.markdown("---")
                
                if "error" in res:
                    st.error(f"❌ Error en executar la bateria de proves: {res.get('error')}")
                else:
                    c_res_header, c_res_dl, c_res_clear = st.columns([5, 3, 2])
                    with c_res_header:
                        st.markdown("### 📊 Resultats del Benchmarking")
                    with c_res_dl:
                        txt_report = generate_harness_txt_report(res, is_single=False)
                        st.download_button(
                            label="📥 Descarregar Informe (.txt)",
                            data=txt_report,
                            file_name=f"informe_laboratori_ia_{res.get('model_avaluat', 'gemini')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key="btn_download_harness_txt"
                        )
                    with c_res_clear:
                        if st.button("🗑️ Netejar Resultats", use_container_width=True, key="btn_clear_suite_res"):
                            clear_harness_status()
                            st.session_state.harness_results = None
                            st.rerun()
                    
                    tot_s = float(res.get("durada_total_s", harness_bg.get("total_duration_s", 0.0)))
                    tot_dur_txt = _format_duration_s(tot_s) if tot_s > 0 else f"{res.get('latencia_mitjana_s', 0)}s / prova"
                    
                    if harness_bg.get("finished_at"):
                        st.caption(f"🕒 Darrer benchmarking completat el: **{harness_bg.get('finished_at')}** | ⏱️ **Durada total del procés:** `{tot_dur_txt}` (Model: `{res.get('model_avaluat', selected_model)}`)")
                    
                    k1, k2, k3, k4, k5 = st.columns(5)
                    with k1:
                        st.metric("🏆 Èxit Global", f"{res.get('percentatge_exit', 0)}%", f"{res.get('proves_superades', 0)}/{res.get('total_proves', 0)} passats")
                    with k2:
                        st.metric("🛡️ Al·lèrgies", f"{res.get('taxa_seguretat_alergies', 0)}%", "Tolerància 0%")
                    with k3:
                        st.metric("🚫 Vetos", f"{res.get('taxa_desdoblament_vetos', 0)}%", "Plats comodí")
                    with k4:
                        st.metric("🍳 Eines i Forn", f"{res.get('taxa_equipament_forn', 100)}%", "Adaptació 100%")
                    with k5:
                        st.metric("⚡ Latència", f"{res.get('latencia_mitjana_s', 0)} s", res.get('model_avaluat', selected_model))
                        
                    st.markdown("#### 📋 Detall de cada Test")
                    for r in res.get("detall_resultats", []):
                        icon = "✅" if r.get("exit_global") else "❌"
                        with st.expander(f"{icon} **{r.get('id')}**: {r.get('titol')} ({r.get('latencia_s')}s)", expanded=not r.get("exit_global")):
                            if r.get("exit_global"):
                                st.success("✨ **Test superat amb èxit.** Cap al·lèrgen, vetos degudament desdoblats i regles nutricionals respectades.")
                            else:
                                st.error(f"⚠️ **Infraccions detectades:**")
                                for err in r.get("errors", []):
                                    st.markdown(f"- 🔴 {err}")
                                    
                            if r.get("resposta_json"):
                                with st.expander("👁️ Veure JSON generat per la IA", expanded=False):
                                    st.json(r.get("resposta_json"))
                                    
            # Mostra de Resultat Individual
            elif "harness_single_result" in st.session_state and isinstance(st.session_state.harness_single_result, dict):
                sr = st.session_state.harness_single_result
                st.markdown("---")
                
                c_s_header, c_s_dl, c_s_clear = st.columns([5, 3, 2])
                with c_s_header:
                    st.markdown(f"### 🎯 Resultat de la Prova: `{sr.get('id')}`")
                with c_s_dl:
                    txt_single_report = generate_harness_txt_report(sr, is_single=True)
                    st.download_button(
                        label="📥 Descarregar Test (.txt)",
                        data=txt_single_report,
                        file_name=f"informe_test_{sr.get('id', 'cas')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="btn_download_single_txt"
                    )
                with c_s_clear:
                    if st.button("🗑️ Tancar Resultat", use_container_width=True, key="btn_close_single_res"):
                        st.session_state.harness_single_result = None
                        st.rerun()
                
                if sr.get("exit_global"):
                    st.success(f"✅ **ÈXIT:** El test s'ha superat en {sr.get('latencia_s')} segons.")
                else:
                    st.error(f"❌ **FALLAT:** S'han detectat infraccions (Temps: {sr.get('latencia_s')}s).")
                    for err in sr.get("errors", []):
                        st.markdown(f"- 🔴 {err}")
                        
                if sr.get("resposta_json"):
                    st.markdown("#### 🍽️ Menú generat per la IA:")
                    st.json(sr.get("resposta_json"))
                    
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 5. SECCIÓ: TUTELATS (PERSONES TUTELADES)
        # =========================================================================
        elif active == "tutelats":
            tutelats_list = list(cfg.get("tutelats", []))
            num_tutelats = len(tutelats_list)
            
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🤝 Persones Tutelades ({num_tutelats})</div>
                <div class="chrome-card-desc">Gestiona persones tutelades o familiars externs que no viuen a casa per controlar la seva medicació i pautes de dosificació. Registra el seu nom i cognoms, edat, telèfon i adreça.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            
            col_add_t1, col_add_t2 = st.columns([8, 2])
            with col_add_t2:
                if st.button("➕ Afegir Tutelat", type="primary", use_container_width=True, key="btn_add_tutelat_sec"):
                    next_id = max([t.get("id", 0) for t in tutelats_list] + [0]) + 1
                    tutelats_list.append({
                        "id": next_id,
                        "nom": f"Persona {num_tutelats + 1}",
                        "edat": "",
                        "telefon": "",
                        "adreca": "",
                        "icona": "👴",
                        "observacions": ""
                    })
                    cfg["tutelats"] = tutelats_list
                    save_app_config(cfg)
                    _clear_section_session_keys("t_")
                    st.rerun()
            
            st.write("")
            
            updated_tutelats = []
            tut_icons_pool = ["👴", "👵", "🧑", "👤", "👨", "👩", "⭐", "🛡️", "💊"]
            
            if not tutelats_list:
                st.info("No hi ha cap persona tutelada registrada. Fes clic a '➕ Afegir Tutelat' per afegir-ne una.")
            
            for j, tut in enumerate(tutelats_list):
                tut_id = tut.get("id", j + 1)
                t_tel_disp = f" · 📞 {tut.get('telefon')}" if tut.get('telefon') else ""
                t_adr_disp = f" · 📍 {tut.get('adreca')}" if tut.get('adreca') else ""
                with st.expander(f"{tut.get('icona', '👴')} {tut.get('nom', f'Tutelat {j+1}')}{t_tel_disp}{t_adr_disp}", expanded=True):
                    c1, c2, c3, c4 = st.columns([1.2, 4.0, 1.8, 3.0])
                    with c1:
                        cur_t_icon = tut.get("icona", "👴")
                        t_ic_idx = tut_icons_pool.index(cur_t_icon) if cur_t_icon in tut_icons_pool else 0
                        t_icon = st.selectbox("Icona", tut_icons_pool, index=t_ic_idx, key=f"t_icon_sec_{tut_id}")
                    with c2:
                        t_nom = st.text_input("Nom i cognoms", value=tut.get("nom", ""), key=f"t_nom_sec_{tut_id}")
                    with c3:
                        t_edat = st.text_input("Edat", value=str(tut.get("edat", "")), key=f"t_edat_sec_{tut_id}")
                    with c4:
                        t_tel = st.text_input("Telèfon", value=str(tut.get("telefon", "")), key=f"t_tel_sec_{tut_id}")
                        
                    c_adr1, c_del_t = st.columns([8.5, 1.5], vertical_alignment="center")
                    with c_adr1:
                        t_adr = st.text_input("Adreça", value=tut.get("adreca", ""), key=f"t_adr_sec_{tut_id}")
                    with c_del_t:
                        st.write("")
                        del_t_btn = st.button("🗑️ Esborrar", key=f"t_del_sec_{tut_id}", use_container_width=True)
                        
                    t_obs = st.text_input("Observacions / Altres dades mèdiques o de contacte", value=tut.get("observacions", ""), key=f"t_obs_sec_{tut_id}")
                    
                    if not del_t_btn:
                        updated_tutelats.append({
                            "id": tut_id,
                            "nom": t_nom,
                            "edat": t_edat,
                            "telefon": t_tel,
                            "adreca": t_adr,
                            "icona": t_icon,
                            "observacions": t_obs
                        })
                    else:
                        new_tut = [t for t in updated_tutelats if t.get("id") != tut_id] + tutelats_list[j+1:]
                        cfg["tutelats"] = new_tut
                        save_app_config(cfg)
                        _clear_section_session_keys("t_")
                        st.success("Persona tutelada eliminada.")
                        st.rerun()
                        
            st.write("")
            _render_flash_message()
            if st.button("💾 Desar Persones Tutelades", type="primary", use_container_width=True, key="save_tutelats_sec"):
                cur_cfg = load_app_config()
                cur_cfg["tutelats"] = updated_tutelats
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = "✅ Dades de persones tutelades desades correctament!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 5. SECCIÓ: BANCS I COMPTES
        # =========================================================================
        elif active == "bancs":
            from core.config_manager import DEFAULT_CONFIG
            bancs_list = list(cfg.get("bancs", DEFAULT_CONFIG.get("bancs", [])))
            num_bancs = len(bancs_list)
            num_actius = sum(1 for b in bancs_list if b.get("actiu", True))
            
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🏦 Gestió de Bancs i Comptes ({num_actius} actius de {num_bancs})</div>
                <div class="chrome-card-desc">Configura les entitats bancàries, targetes i caixes de la llar. <b>Important:</b> Si un banc té el check desactivat, quedarà ocult al Dashboard i no es podrà seleccionar per fer operacions ni despeses.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            
            col_add_b1, col_add_b2 = st.columns([7.5, 2.5])
            with col_add_b2:
                if st.button("➕ Afegir Nou Banc", type="primary", use_container_width=True, key="btn_add_banc_sec"):
                    next_id = max([b.get("id", 0) for b in bancs_list] + [0]) + 1
                    bancs_list.append({
                        "id": next_id,
                        "nom": f"Banc {num_bancs + 1}",
                        "actiu": True,
                        "icona": "🏦",
                        "color": "#3b82f6",
                        "descripcio": "Compte o targeta",
                        "titular": "Enric Xicars",
                        "compte_iban": ""
                    })
                    cur_cfg = load_app_config()
                    cur_cfg["bancs"] = bancs_list
                    save_app_config(cur_cfg)
                    st.rerun()
            
            st.write("")
            
            updated_bancs = []
            bank_icons_pool = ["🏦", "💳", "📈", "🏠", "🛒", "👛", "💰", "🪙", "💵", "🏢", "📱", "🛡️", "⭐"]
            
            if not bancs_list:
                st.info("No hi ha cap entitat bancària configurada. Fes clic a '➕ Afegir Nou Banc' per començar.")
            
            for k, b_item in enumerate(bancs_list):
                b_id = b_item.get("id", k + 1)
                is_act = b_item.get("actiu", True)
                status_badge = "🟢 ACTIU" if is_act else "⚪ INACTIU"
                b_color = b_item.get("color", "#3b82f6")
                b_icon = b_item.get("icona", "🏦")
                b_nom = b_item.get("nom", f"Banc {k+1}")
                b_desc = b_item.get("descripcio", "")
                
                header_title = f"{b_icon} {b_nom} — {status_badge}"
                if b_desc:
                    header_title += f" ({b_desc})"
                
                with st.expander(header_title, expanded=True):
                    # Fila 1: Nom, Toggle Actiu, Icona
                    c1, c2, c3 = st.columns([3.5, 3.5, 1.5], vertical_alignment="center")
                    with c1:
                        new_b_nom = st.text_input("Nom de l'entitat / compte", value=b_nom, key=f"b_nom_{b_id}")
                    with c2:
                        st.markdown("<div style='margin-bottom: 4px; font-size: 0.82rem; font-weight: 600;'>Estat operatiu</div>", unsafe_allow_html=True)
                        new_b_actiu = st.toggle("Actiu (operar i mostrar)", value=is_act, key=f"b_act_{b_id}", help="Si està desactivat, no es veurà al Dashboard ni als formularis de despeses/ingressos.")
                    with c3:
                        cur_b_ic = b_icon
                        b_ic_idx = bank_icons_pool.index(cur_b_ic) if cur_b_ic in bank_icons_pool else 0
                        new_b_icon = st.selectbox("Icona", bank_icons_pool, index=b_ic_idx, key=f"b_icon_{b_id}")
                    
                    # Fila 2: Descripció, Titular, Color
                    c4, c5, c6 = st.columns([4.0, 3.5, 1.5])
                    with c4:
                        new_b_desc = st.text_input("Tipus / Descripció", value=b_desc, key=f"b_desc_{b_id}", placeholder="ex: Compte corrent, Targeta crèdit, etc.")
                    with c5:
                        new_b_titular = st.text_input("Titular del compte", value=b_item.get("titular", ""), key=f"b_titular_{b_id}", placeholder="ex: Enric Xicars")
                    with c6:
                        new_b_color = st.color_picker("Color", value=b_color, key=f"b_color_{b_id}")
                        
                    # Fila 3: IBAN / Núm. Compte i Botó Esborrar
                    c7, c8 = st.columns([8.2, 1.8], vertical_alignment="center")
                    with c7:
                        new_b_iban = st.text_input("IBAN / Núm. Compte o Targeta (opcional)", value=b_item.get("compte_iban", ""), key=f"b_iban_{b_id}", placeholder="ES00 0000 0000 0000 0000")
                    with c8:
                        st.write("")
                        del_b_btn = st.button("🗑️ Eliminar", key=f"b_del_{b_id}", use_container_width=True)
                    
                    if not del_b_btn:
                        updated_bancs.append({
                            "id": b_id,
                            "nom": new_b_nom,
                            "actiu": new_b_actiu,
                            "icona": new_b_icon,
                            "color": new_b_color,
                            "descripcio": new_b_desc,
                            "titular": new_b_titular,
                            "compte_iban": new_b_iban
                        })
                    else:
                        new_bancs = [b for b in updated_bancs if b.get("id") != b_id] + bancs_list[k+1:]
                        cur_cfg = load_app_config()
                        cur_cfg["bancs"] = new_bancs
                        save_app_config(cur_cfg)
                        st.success(f"Entitat '{b_nom}' eliminada.")
                        st.rerun()
                        
            st.write("")
            _render_flash_message()
            if st.button("💾 Desar Configuració de Bancs", type="primary", use_container_width=True, key="save_bancs_sec"):
                cur_cfg = load_app_config()
                cur_cfg["bancs"] = updated_bancs
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = "✅ Configuració de bancs i comptes desada correctament!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 6. SECCIÓ: TEMA I ASPECTE
        # =========================================================================
        elif active == "tema":
            cur_tema = cfg.get("tema", "Fosc")
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🎨 Aspecte i Tema Visual</div>
                <div class="chrome-card-desc">Tria l'aparença visual de l'aplicació per adaptar-la al teu gust o entorn d'il·luminació.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            temes = ["Fosc", "Clar", "Automàtic"]
            idx_tema = temes.index(cur_tema) if cur_tema in temes else 0
            
            sel_tema = st.radio(
                "Selecciona el tema de l'aplicació:",
                temes,
                index=idx_tema,
                format_func=lambda t: {
                    "Fosc": "🌙 Fosc (Colors foscos i descans per a la vista)",
                    "Clar": "☀️ Clar (Fons blanc d'alt contrast)",
                    "Automàtic": "⚙️ Automàtic (S'adapta segons la configuració del teu dispositiu)"
                }[t],
                key="radio_tema"
            )
            
            st.write("")
            _render_flash_message()
            if st.button("💾 Aplicar i Desar Tema", type="primary", use_container_width=True, key="save_tema"):
                cur_cfg = load_app_config()
                cur_cfg["tema"] = sel_tema
                st.session_state["app_theme"] = sel_tema
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = "✅ Tema visual actualitzat!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 5. SECCIÓ: ICONES DE LA PANTALLA D'INICI ACTIVADES
        # =========================================================================
        elif active == "icones":
            icones_cfg = cfg.get("icones_actives", {})
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🔘 Icones de la Pantalla d'Inici</div>
                <div class="chrome-card-desc">Configura quins mòduls estan disponibles i clicables a la pantalla d'inici de l'aplicació. El <b>Dashboard General</b> és l'element principal i està sempre activat de manera fixa.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            
            modules_list = [
                ("dashboard", "📊 Dashboard General", True, True, "Pantalla central de resum general (Sempre activada)"),
                ("economic", "📈 Mòdul Econòmic", icones_cfg.get("economic", True), False, "Gestió financera completa, ingressos, despeses i previsions"),
                ("seguretat", "📹 Seguretat i Càmeres", icones_cfg.get("seguretat", True), False, "Control de càmeres de vigilància i seguretat"),
                ("manteniment", "🛠️ Manteniment de la Llar", icones_cfg.get("manteniment", True), False, "Tasques de manteniment, reparacions i manuals"),
                ("domotica", "📶 Domòtica (Home Assistant)", icones_cfg.get("domotica", True), False, "Integració de llums, sensors i automatitzacions"),
                ("jocs", "🎲 Jocs i Oci Familiar", icones_cfg.get("jocs", True), False, "Partides, puntuacions i jocs familiars"),
                ("agenda", "📅 Agenda i Calendari", icones_cfg.get("agenda", True), False, "Esdeveniments familiars i calendari compartit"),
                ("medicacio", "💊 Control de Medicació", icones_cfg.get("medicacio", True), False, "Pautes de medicació i avisos de preses"),
                ("menjar", "🍽️ Menjar, Menús i Rebost", icones_cfg.get("menjar", True), False, "Planificació de menús setmanals i stock del rebost"),
                ("cotxe", "🚗 Cotxe i Transport", icones_cfg.get("cotxe", True), False, "Quilometratge, consums, canvis d'oli i ITV"),
                ("compres", "🛒 Compres al Súper i Stock", icones_cfg.get("compres", True), False, "Gestió de tiquets del súper i preus d'articles"),
                ("admin", "⚙️ Configuració Global", icones_cfg.get("admin", True), False, "Ajustos de la casa, administradors i paràmetres")
            ]
            
            new_icones_state = {}
            
            for key_m, label_m, val_m, is_locked, desc_m in modules_list:
                c_lbl, c_tog = st.columns([8, 2], vertical_alignment="center")
                with c_lbl:
                    lock_badge = " <span style='color:#38bdf8; font-size:0.75rem; border:1px solid #38bdf8; padding:1px 6px; border-radius:10px; font-weight:bold;'>FIXAT</span>" if is_locked else ""
                    st.markdown(f"<div style='font-size:0.95rem; font-weight:600; color:{text_primary};'>{label_m}{lock_badge}</div><div style='font-size:0.8rem; color:{text_secondary};'>{desc_m}</div>", unsafe_allow_html=True)
                with c_tog:
                    if is_locked:
                        st.toggle("Actiu", value=True, disabled=True, key=f"tog_{key_m}", label_visibility="collapsed")
                        new_icones_state[key_m] = True
                    else:
                        tog_val = st.toggle("Actiu", value=val_m, key=f"tog_{key_m}", label_visibility="collapsed", on_change=_on_icona_change, args=(key_m,))
                        new_icones_state[key_m] = tog_val
                st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:8px 0;'></div>", unsafe_allow_html=True)
                
            st.write("")
            _render_flash_message()
            if st.button("💾 Desar Configuració d'Icones", type="primary", use_container_width=True, key="save_icones"):
                cur_cfg = load_app_config()
                cur_cfg["icones_actives"] = new_icones_state
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = "✅ Configuració d'icones de la pantalla d'inici desada correctament!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 6. SECCIÓ: IDIOMA I TRADUCCIONS
        # =========================================================================
        elif active == "idioma":
            cur_lang = cfg.get("idioma", "ca")
            st.markdown(f"""
            <div class="chrome-card">
                <div class="chrome-card-header">🌐 Idiomes i Traducció</div>
                <div class="chrome-card-desc">Tria l'idioma principal de l'aplicació i revisa els textos de la interfície.</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
            idiomes_map = {
                "ca": "🏴󠁥󠁳󠁣󠁴󠁿 Català (Predeterminat)",
                "es": "🇪🇸 Castellano",
                "en": "🇬🇧 English",
                "fr": "🇫🇷 Français"
            }
            idiomes_keys = list(idiomes_map.keys())
            idx_lang = idiomes_keys.index(cur_lang) if cur_lang in idiomes_keys else 0
            
            sel_lang = st.selectbox(
                "Idioma principal de l'aplicació:",
                idiomes_keys,
                index=idx_lang,
                format_func=lambda k: idiomes_map.get(k, k),
                key="sel_idioma"
            )
            
            st.write("")
            st.markdown("#### 📚 Diccionari de textos actiu")
            from core.config_manager import TRANSLATIONS
            active_dict = TRANSLATIONS.get(sel_lang, TRANSLATIONS["ca"])
            df_trans = [{"Clau": k, "Traducció": v} for k, v in active_dict.items()]
            st.dataframe(df_trans, use_container_width=True, hide_index=True)
            
            st.write("")
            _render_flash_message()
            if st.button("💾 Desar Preferència d'Idioma", type="primary", use_container_width=True, key="save_lang"):
                cur_cfg = load_app_config()
                cur_cfg["idioma"] = sel_lang
                if save_app_config(cur_cfg):
                    st.session_state["flash_success"] = f"✅ Idioma canviat a {idiomes_map[sel_lang]}!"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
