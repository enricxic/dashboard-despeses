import streamlit as st
from core.avatar_manager import (
    get_avatar_role_for_module,
    get_avatar_image_base64,
    ask_avatar_ai,
    AVATAR_ROLES
)

def render_avatar_widget(current_module: str = None, container=None, key_prefix: str = "sb"):
    """Renderitza el widget visual de l'Avatar Anime en un contenidor de Streamlit."""
    role_info = get_avatar_role_for_module(current_module)
    img_b64 = get_avatar_image_base64(role_info["image_file"])
    badge_color = role_info["badge_color"]
    
    # CSS dedicat per a l'Avatar amb efectes visuals neó i fons 100% transparent
    st.markdown(f"""
    <style>
    .avatar-card {{
        background: transparent !important;
        border: none !important;
        padding: 4px;
        color: #f8fafc;
        position: relative;
        text-align: center;
    }}
    .avatar-badge {{
        display: inline-block;
        background-color: {badge_color};
        color: #ffffff;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 3px 10px;
        border-radius: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        box-shadow: 0 0 10px {badge_color}aa;
    }}
    .avatar-img-container {{
        text-align: center;
        margin: 4px 0;
        position: relative;
    }}
    .avatar-img {{
        width: 100%;
        max-width: 220px;
        border: none !important;
        border-radius: 0 !important;
        background: transparent !important;
        filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.5)) drop-shadow(0 0 18px {badge_color}aa);
        transition: transform 0.3s ease, filter 0.3s ease;
    }}
    .avatar-img:hover {{
        transform: scale(1.05) translateY(-3px);
        filter: drop-shadow(0 15px 30px rgba(0, 0, 0, 0.6)) drop-shadow(0 0 28px {badge_color});
    }}
    .speech-bubble {{
        position: relative;
        background: rgba(30, 41, 59, 0.95);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 10px 14px;
        font-size: 0.88rem;
        line-height: 1.4;
        color: #e2e8f0;
        margin-top: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}
    .speech-bubble::before {{
        content: '';
        position: absolute;
        top: -8px;
        left: 24px;
        width: 0;
        height: 0;
        border-left: 8px solid transparent;
        border-right: 8px solid transparent;
        border-bottom: 8px solid #475569;
    }}
    .avatar-title {{
        font-size: 1.1rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 2px;
    }}
    .avatar-subtitle {{
        font-size: 0.8rem;
        color: #94a3b8;
        margin-bottom: 8px;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    target = container if container else st
    
    with target.container():
        # Header & Card Avatar
        st.markdown(f"""
        <div class="avatar-card">
            <div class="avatar-badge">{role_info['title']}</div>
            <div class="avatar-title">✨ Xiqui AI Avatar</div>
            <div class="avatar-subtitle">{role_info['subtitle']}</div>
            <div class="avatar-img-container">
                <img src="{img_b64}" class="avatar-img" alt="{role_info['title']}" />
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Selector de Rol manual (opcional per l'usuari)
        with st.popover("👗 Canviar Vestuari / Rol Avatar", use_container_width=True):
            st.markdown("**Selecciona la variant de vestuari de la Xiqui:**")
            role_options = {
                "base": "🌐 Base (Assistent General)",
                "manetes": "🛠️ Manetes (Manteniment & Domòtica)",
                "infermera": "💊 Infermera (Salut & Medicació)",
                "cuinera": "🍽️ Cuinera (Menús & Cuina)",
                "administrativa": "💼 Administrativa (Economia & Compres)"
            }
            selected_r = st.selectbox(
                "Rol actiu:",
                options=list(role_options.keys()),
                format_func=lambda x: role_options[x],
                index=list(role_options.keys()).index(role_info["key"]),
                key=f"avatar_role_sel_{key_prefix}_{current_module}"
            )
            if selected_r != st.session_state.get("avatar_manual_role"):
                st.session_state["avatar_manual_role"] = selected_r
                st.rerun()
        
        # Gestió del missatge actual i resposta de la IA
        last_response = st.session_state.get("avatar_last_response")
        current_text = last_response if last_response else role_info["greeting"]
        
        st.markdown(f"""
        <div class="speech-bubble">
            💬 <b>Xiqui:</b> "{current_text}"
        </div>
        """, unsafe_allow_html=True)
        
        # Formulari d'interacció "Pregunta'm"
        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        with st.form(key=f"avatar_query_form_{key_prefix}_{current_module}", clear_on_submit=True):
            user_input = st.text_input(
                "Pregunta'm...",
                placeholder="Ex: Què tenim per dinar avui? O quines tasques queden?",
                label_visibility="collapsed"
            )
            col_b1, col_b2 = st.columns([7, 3])
            with col_b1:
                submitted = st.form_submit_button("💬 Enviar", use_container_width=True)
            with col_b2:
                reset_btn = st.form_submit_button("🔄", help="Restablir diàleg")
                
            if submitted and user_input.strip():
                with st.spinner("La Xiqui està pensant la resposta..."):
                    res = ask_avatar_ai(user_input, role_info)
                    st.session_state["avatar_last_response"] = res
                    st.rerun()
            elif reset_btn:
                st.session_state["avatar_last_response"] = None
                st.rerun()

def render_floating_avatar(current_module: str = None):
    """Renderitza la secció desplegable de l'avatar (només quan sigui necessari)."""
    pass

def render_header_with_avatar(title_html: str, module_name: str = None, extra_button_fn=None):
    """Renderitza la capçalera del mòdul amb el títol, la imatge petita transparent de l'avatar a 1/3 de la mida (si està activa),
    el botó estrella ✨ per activar/desactivar la visibilitat i el botó 🔙 Inici intacte."""
    
    if "show_avatar_overlay" not in st.session_state:
        st.session_state["show_avatar_overlay"] = True
        
    show_avatar = st.session_state["show_avatar_overlay"]
    role_info = get_avatar_role_for_module(module_name)
    img_b64 = get_avatar_image_base64(role_info["image_file"])
    badge_color = role_info["badge_color"]
    
    st.markdown(f"""
    <style>
    .hdr-avatar-img-standalone {{
        height: 68px;
        max-height: 68px;
        width: auto;
        object-fit: contain;
        filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.4)) drop-shadow(0 0 10px {badge_color}aa);
        transition: transform 0.25s ease, filter 0.25s ease;
        vertical-align: middle;
        user-select: none;
    }}
    .hdr-avatar-img-standalone:hover {{
        transform: scale(1.12) translateY(-2px);
        filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.6)) drop-shadow(0 0 18px {badge_color});
    }}
    </style>
    """, unsafe_allow_html=True)
    
    c_title, c_controls = st.columns([6.2, 5.8], vertical_alignment="center")
    
    with c_title:
        st.markdown(title_html, unsafe_allow_html=True)
        
    with c_controls:
        # Calcular columnes dinàmiques
        cols_spec = []
        if extra_button_fn:
            cols_spec.append(2.6)
            
        if show_avatar and img_b64:
            cols_spec.append(1.8) # Només la imatge transparent de l'avatar a 1/3 de tamany
            
        cols_spec.append(1.0) # Botó Estrella ✨
        cols_spec.append(2.1) # Botó 🔙 Inici intacte en mides
        
        cols = st.columns(cols_spec, vertical_alignment="center")
        
        col_idx = 0
        if extra_button_fn:
            with cols[col_idx]:
                extra_button_fn()
            col_idx += 1
            
        if show_avatar and img_b64:
            with cols[col_idx]:
                st.markdown(f"""
                <div style="text-align: center; display: flex; justify-content: center; align-items: center;">
                    <img src="{img_b64}" class="hdr-avatar-img-standalone" title="Xiqui ({role_info['title']})" alt="Xiqui Avatar" />
                </div>
                """, unsafe_allow_html=True)
            col_idx += 1
            
        with cols[col_idx]:
            star_type = "primary" if show_avatar else "secondary"
            if st.button("✨", key=f"btn_toggle_avatar_star_{module_name}", type=star_type, help="Activar / Desactivar visibilitat de l'avatar transparent Xiqui"):
                st.session_state["show_avatar_overlay"] = not show_avatar
                st.rerun()
                
        with cols[col_idx + 1]:
            if st.button("🔙 Inici", use_container_width=True, key=f"btn_nav_inici_{module_name}"):
                st.session_state.current_module = None
                st.rerun()
