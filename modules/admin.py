import streamlit as st
import json
import os
from core.config_manager import load_app_config, save_app_config, get_translation

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
    
    # Header estil Google Chrome
    c_head1, c_head2, c_head3 = st.columns([3, 5, 2], vertical_alignment="center")
    with c_head1:
        st.markdown(f"""
        <div class="chrome-title-group">
            <span class="chrome-logo">⚙️</span>
            <h2 class="chrome-title">Configuració</h2>
        </div>
        """, unsafe_allow_html=True)
    with c_head2:
        search_query = st.text_input("🔍 Cercar ajustos", placeholder="Cercar a la configuració...", label_visibility="collapsed", key="cfg_search")
    with c_head3:
        if st.button("🔙 Tornar a l'inici", use_container_width=True, key="btn_cfg_home"):
            st.session_state.current_module = None
            st.rerun()
            
    st.write("")
    
    # Layout en dues columnes (Menú lateral Chrome a l'esquerra + Contingut a la dreta)
    col_menu, col_body = st.columns([3, 7], gap="large")
    
    with col_menu:
        st.markdown(f"<div style='font-size:0.8rem; text-transform:uppercase; font-weight:700; color:{text_secondary}; margin-bottom:8px; padding-left:6px;'>Seccions</div>", unsafe_allow_html=True)
        
        sections = [
            ("admin", "👤 Administrador"),
            ("titol", "🏷️ Títol de la casa"),
            ("familia", "👨‍👩‍👧‍👦 Família"),
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
                st.session_state.cfg_active_tab = key_s
                st.rerun()
                
    with col_body:
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
                if st.button("💾 Desar Dades d'Administrador", type="primary", use_container_width=True, key="save_admin"):
                    cfg["admin"] = {
                        "nom": new_nom,
                        "email": new_email,
                        "telefon": new_tel,
                        "avatar": new_avatar,
                        "pin": new_pin,
                        "rol": new_rol
                    }
                    if save_app_config(cfg):
                        st.success("✅ Dades d'administrador actualitzades correctament!")
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
                <div style="font-size: {max(12, int(tamany_lletra * 0.36))}px; font-weight: 800; color: #407faf; letter-spacing: 1.8px; margin-top: 6px; text-transform: uppercase; text-align: center;">
                    {slogan_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            if st.button("💾 Desar Títol de la Casa", type="primary", use_container_width=True, key="save_titol"):
                cfg["casa"] = {
                    "paraula1": p1,
                    "color1": col1,
                    "paraula2": p2,
                    "color2": col2,
                    "tamany_lletra": tamany_lletra
                }
                if save_app_config(cfg):
                    st.success("✅ Títol de la casa desat correctament!")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 3. SECCIÓ: FAMÍLIA I TUTELATS
        # =========================================================================
        elif active == "familia":
            tab_fam_membres, tab_fam_tutelats = st.tabs(["👨‍👩‍👧‍👦 Membres de la Llar", "🤝 Persones Tutelades (Externes)"])
            
            with tab_fam_membres:
                familia_list = list(cfg.get("familia", []))
                num_membres = len(familia_list)
                
                st.markdown(f"""
                <div class="chrome-card">
                    <div class="chrome-card-header">👨‍👩‍👧‍👦 Membres de la Família ({num_membres} / 10)</div>
                    <div class="chrome-card-desc">Afegeix i gestiona els membres de la llar (fins a un màxim de 10). Aquesta informació s'utilitza pel control de medicació, menús familiars, preferències i assistent IA.</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
                
                # Botó d'afegir membre
                if num_membres < 10:
                    col_add1, col_add2 = st.columns([8, 2])
                    with col_add2:
                        if st.button("➕ Afegir Membre", type="primary", use_container_width=True, key="btn_add_fam_mem"):
                            next_id = max([m.get("id", 0) for m in familia_list] + [0]) + 1
                            familia_list.append({
                                "id": next_id,
                                "nom": f"Membre {num_membres + 1}",
                                "rol": "Familiar",
                                "edat": "",
                                "circunstancies": "",
                                "icona": "👤"
                            })
                            cfg["familia"] = familia_list
                            save_app_config(cfg)
                            st.rerun()
                else:
                    st.info("ℹ️ S'ha assolit el límit màxim de 10 membres a la família.")
                    
                st.write("")
                
                # Llista de membres
                updated_familia = []
                icons_pool = ["👨", "👩", "👦", "👧", "👶", "👴", "👵", "🐶", "🐱", "🧑", "👑", "⭐"]
                roles_pool = ["Pare", "Mare", "Fill", "Filla", "Avi", "Àvia", "Germà", "Germana", "Mascota", "Altres"]
                
                for i, mem in enumerate(familia_list):
                    with st.expander(f"{mem.get('icona', '👤')} {mem.get('nom', f'Membre {i+1}')} ({mem.get('rol', 'Familiar')})", expanded=True):
                        c1, c2, c3, c4 = st.columns([1.2, 3, 2.5, 1.5])
                        with c1:
                            cur_icon = mem.get("icona", "👤")
                            ic_idx = icons_pool.index(cur_icon) if cur_icon in icons_pool else 0
                            m_icon = st.selectbox("Icona", icons_pool, index=ic_idx, key=f"f_icon_{i}")
                        with c2:
                            m_nom = st.text_input("Nom", value=mem.get("nom", ""), key=f"f_nom_{i}")
                        with c3:
                            cur_r = mem.get("rol", "Familiar")
                            r_idx = roles_pool.index(cur_r) if cur_r in roles_pool else len(roles_pool)-1
                            m_rol = st.selectbox("Rol / Relació", roles_pool, index=r_idx, key=f"f_rol_{i}")
                        with c4:
                            m_edat = st.text_input("Edat", value=str(mem.get("edat", "")), key=f"f_edat_{i}")
                            
                        c_circ1, c_circ2 = st.columns([8.5, 1.5], vertical_alignment="center")
                        with c_circ1:
                            m_circ = st.text_input("Al·lèrgies, dietes o circumstàncies mèdiques/personals", value=mem.get("circunstancies", ""), key=f"f_circ_{i}")
                        with c_circ2:
                            st.write("")
                            del_btn = st.button("🗑️ Esborrar", key=f"f_del_{i}", use_container_width=True)
                            
                        if not del_btn:
                            updated_familia.append({
                                "id": mem.get("id", i + 1),
                                "nom": m_nom,
                                "rol": m_rol,
                                "edat": m_edat,
                                "circunstancies": m_circ,
                                "icona": m_icon
                            })
                        else:
                            cfg["familia"] = updated_familia + familia_list[i+1:]
                            save_app_config(cfg)
                            st.success(f"Membre eliminat.")
                            st.rerun()
                            
                st.write("")
                if st.button("💾 Desar Membres de la Família", type="primary", use_container_width=True, key="save_fam"):
                    cfg["familia"] = updated_familia
                    if save_app_config(cfg):
                        st.success("✅ Membres de la família desats correctament!")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
            with tab_fam_tutelats:
                tutelats_list = list(cfg.get("tutelats", []))
                num_tutelats = len(tutelats_list)
                
                st.markdown(f"""
                <div class="chrome-card">
                    <div class="chrome-card-header">🤝 Persones Tutelades ({num_tutelats})</div>
                    <div class="chrome-card-desc">Afegeix i gestiona persones tutelades o familiars externs que no viuen a casa per controlar la seva medicació, pautes i informació de contacte.</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<div class='chrome-card'>", unsafe_allow_html=True)
                
                col_add_t1, col_add_t2 = st.columns([8, 2])
                with col_add_t2:
                    if st.button("➕ Afegir Tutelat", type="primary", use_container_width=True, key="btn_add_tutelat"):
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
                        st.rerun()
                
                st.write("")
                
                updated_tutelats = []
                tut_icons_pool = ["👴", "👵", "🧑", "👤", "👨", "👩", "⭐", "🛡️", "💊"]
                
                if not tutelats_list:
                    st.info("No hi ha cap persona tutelada registrada. Fes clic a '➕ Afegir Tutelat' per afegir-ne una.")
                
                for j, tut in enumerate(tutelats_list):
                    t_tel_disp = f" · {tut.get('telefon')}" if tut.get('telefon') else ""
                    with st.expander(f"{tut.get('icona', '👴')} {tut.get('nom', f'Tutelat {j+1}')}{t_tel_disp}", expanded=True):
                        c1, c2, c3, c4 = st.columns([1.2, 4.0, 1.8, 3.0])
                        with c1:
                            cur_t_icon = tut.get("icona", "👴")
                            t_ic_idx = tut_icons_pool.index(cur_t_icon) if cur_t_icon in tut_icons_pool else 0
                            t_icon = st.selectbox("Icona", tut_icons_pool, index=t_ic_idx, key=f"t_icon_{j}")
                        with c2:
                            t_nom = st.text_input("Nom i cognoms", value=tut.get("nom", ""), key=f"t_nom_{j}")
                        with c3:
                            t_edat = st.text_input("Edat", value=str(tut.get("edat", "")), key=f"t_edat_{j}")
                        with c4:
                            t_tel = st.text_input("Telèfon", value=str(tut.get("telefon", "")), key=f"t_tel_{j}")
                            
                        c_adr1, c_del_t = st.columns([8.5, 1.5], vertical_alignment="center")
                        with c_adr1:
                            t_adr = st.text_input("Adreça", value=tut.get("adreca", ""), key=f"t_adr_{j}")
                        with c_del_t:
                            st.write("")
                            del_t_btn = st.button("🗑️ Esborrar", key=f"t_del_{j}", use_container_width=True)
                            
                        t_obs = st.text_input("Observacions / Altres dades de contacte", value=tut.get("observacions", ""), key=f"t_obs_{j}")
                        
                        if not del_t_btn:
                            updated_tutelats.append({
                                "id": tut.get("id", j + 1),
                                "nom": t_nom,
                                "edat": t_edat,
                                "telefon": t_tel,
                                "adreca": t_adr,
                                "icona": t_icon,
                                "observacions": t_obs
                            })
                        else:
                            cfg["tutelats"] = updated_tutelats + tutelats_list[j+1:]
                            save_app_config(cfg)
                            st.success(f"Persona tutelada eliminada.")
                            st.rerun()
                            
                st.write("")
                if st.button("💾 Desar Persones Tutelades", type="primary", use_container_width=True, key="save_tutelats"):
                    cfg["tutelats"] = updated_tutelats
                    if save_app_config(cfg):
                        st.success("✅ Dades de persones tutelades desades correctament!")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # =========================================================================
        # 4. SECCIÓ: TEMA I ASPECTE
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
            if st.button("💾 Aplicar i Desar Tema", type="primary", use_container_width=True, key="save_tema"):
                cfg["tema"] = sel_tema
                st.session_state["app_theme"] = sel_tema
                if save_app_config(cfg):
                    st.success("✅ Tema visual actualitzat!")
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
                        tog_val = st.toggle("Actiu", value=val_m, key=f"tog_{key_m}", label_visibility="collapsed")
                        new_icones_state[key_m] = tog_val
                st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:8px 0;'></div>", unsafe_allow_html=True)
                
            st.write("")
            if st.button("💾 Desar Configuració d'Icones", type="primary", use_container_width=True, key="save_icones"):
                cfg["icones_actives"] = new_icones_state
                if save_app_config(cfg):
                    st.success("✅ Configuració d'icones de la pantalla d'inici desada correctament!")
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
            if st.button("💾 Desar Preferència d'Idioma", type="primary", use_container_width=True, key="save_lang"):
                cfg["idioma"] = sel_lang
                if save_app_config(cfg):
                    st.success(f"✅ Idioma canviat a {idiomes_map[sel_lang]}!")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
