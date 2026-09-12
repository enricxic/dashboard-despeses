import streamlit as st
from core.avatar_manager import (
    get_avatar_role_for_module,
    get_avatar_image_base64,
    ask_avatar_ai,
    AVATAR_ROLES
)

def render_avatar_widget(current_module: str = None, container=None):
    """Renderitza el widget visual de l'Avatar Anime en un contenidor de Streamlit."""
    role_info = get_avatar_role_for_module(current_module)
    img_b64 = get_avatar_image_base64(role_info["image_file"])
    badge_color = role_info["badge_color"]
    
    # CSS dedicat per a l'Avatar amb efectes visuals neó i glassmorphism
    st.markdown(f"""
    <style>
    .avatar-card {{
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(30, 41, 59, 0.90));
        border: 2px solid {badge_color};
        border-radius: 16px;
        padding: 14px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37), 0 0 15px {badge_color}44;
        backdrop-filter: blur(8px);
        margin-bottom: 15px;
        color: #f8fafc;
        position: relative;
        overflow: hidden;
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
    }}
    .avatar-img-container {{
        text-align: center;
        margin: 8px 0;
        position: relative;
    }}
    .avatar-img {{
        width: 100%;
        max-width: 220px;
        border-radius: 14px;
        border: 2px solid {badge_color};
        box-shadow: 0 0 20px {badge_color}66;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }}
    .avatar-img:hover {{
        transform: scale(1.03);
        box-shadow: 0 0 25px {badge_color}aa;
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
        box-shadow: inset 0 0 10px rgba(0,0,0,0.2);
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
                key=f"avatar_role_sel_{current_module}"
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
        with st.form(key=f"avatar_query_form_{current_module}", clear_on_submit=True):
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
    """Renderitza un botó Popover destacat de l'Avatar Anime directament a la pantalla principal."""
    role_info = get_avatar_role_for_module(current_module)
    badge_color = role_info["badge_color"]
    
    st.markdown(f"""
    <style>
    .avatar-floating-container {{
        margin-bottom: 12px;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    with st.expander(f"✨ Xiqui AI Avatar ({role_info['title']})", expanded=False):
        render_avatar_widget(current_module=current_module)

