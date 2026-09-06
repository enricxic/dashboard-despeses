import streamlit as st
import importlib
import base64
import os
from core.auth import check_password
import streamlit.components.v1 as components

st.set_page_config(
    page_title="XiquiHouse Dashboard",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown('''
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden; height: 0px !important;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem !important; margin-top: 0rem !important;}
    
    /* Top back button smaller */
    .back-button .stButton > button {
        height: 40px;
        font-size: 16px;
    }
    </style>
''', unsafe_allow_html=True)

if not check_password():
    st.stop()

# Comprovar si s'ha seleccionat un mòdul a través de query params (des de l'HTML interactiu)
if "mod" in st.query_params:
    selected_mod = st.query_params.get("mod")
    st.session_state.current_module = selected_mod
    try:
        del st.query_params["mod"]
    except Exception:
        pass
    st.rerun()

# Comprovar si s'ha sol·licitat una acció des del menú superior (Home, Reset, Logout)
if "action" in st.query_params:
    act = st.query_params.get("action")
    if act == "home":
        st.session_state.current_module = None
    elif act == "reset":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
    elif act == "logout":
        if "password_correct" in st.session_state:
            del st.session_state["password_correct"]
        if "auth" in st.query_params:
            del st.query_params["auth"]
    try:
        del st.query_params["action"]
    except Exception:
        pass
    st.rerun()

if 'current_module' not in st.session_state:
    st.session_state.current_module = None

def render_traditional_menubar():
    auth_token = st.query_params.get("auth", "")
    auth_suffix = f"&auth={auth_token}" if auth_token else ""
    
    menubar_html = f"""
    <style>
    .desktop-menubar {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        background: transparent;
        padding: 0px;
        margin: -0.8rem 0 0.1rem 0;
        gap: 18px;
        user-select: none;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 0.78rem;
        z-index: 9999;
    }}
    .desktop-menubar .menu-item {{
        position: relative;
        cursor: pointer;
        display: inline-block;
    }}
    .desktop-menubar .menu-title {{
        color: #94a3b8;
        padding: 2px 4px;
        border-radius: 2px;
        transition: all 0.12s ease;
        display: inline-block;
    }}
    .desktop-menubar .menu-item:hover .menu-title {{
        background-color: rgba(255, 255, 255, 0.08);
        color: #f8fafc;
    }}
    .desktop-menubar .menu-dropdown {{
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 4px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
        min-width: 190px;
        z-index: 999999;
        padding: 4px 0;
    }}
    .desktop-menubar .menu-item:hover .menu-dropdown {{
        display: block;
    }}
    .desktop-menubar .menu-dropdown a {{
        display: block;
        padding: 5px 14px;
        color: #cbd5e1 !important;
        text-decoration: none !important;
        font-size: 0.78rem;
        white-space: nowrap;
        transition: background 0.12s ease;
    }}
    .desktop-menubar .menu-dropdown a:hover {{
        background-color: #0284c7 !important;
        color: #ffffff !important;
    }}
    </style>
    
    <nav class="desktop-menubar">
        <div class="menu-item">
            <span class="menu-title">Arxiu</span>
            <div class="menu-dropdown">
                <a href="?action=home{auth_suffix}" target="_self">Pantalla d'inici</a>
                <a href="?action=reset{auth_suffix}" target="_self">Reiniciar sessió</a>
                <a href="?action=logout" target="_self">Tancar sessió</a>
            </div>
        </div>
        <div class="menu-item">
            <span class="menu-title">Finances</span>
            <div class="menu-dropdown">
                <a href="?mod=modules.dashboard{auth_suffix}" target="_self">Dashboard General</a>
                <a href="?mod=modules.economic{auth_suffix}" target="_self">Mòdul Econòmic</a>
                <a href="?mod=modules.compres{auth_suffix}" target="_self">Compres i tiquets súper</a>
            </div>
        </div>
        <div class="menu-item">
            <span class="menu-title">Llar</span>
            <div class="menu-dropdown">
                <a href="?mod=modules.menjar{auth_suffix}" target="_self">Menús i cuina</a>
                <a href="?mod=modules.manteniment{auth_suffix}" target="_self">Manteniment</a>
                <a href="?mod=modules.cotxe{auth_suffix}" target="_self">Cotxe</a>
                <a href="?mod=modules.domotica{auth_suffix}" target="_self">Domòtica</a>
                <a href="?mod=modules.seguretat{auth_suffix}" target="_self">Seguretat</a>
            </div>
        </div>
        <div class="menu-item">
            <span class="menu-title">Família</span>
            <div class="menu-dropdown">
                <a href="?mod=modules.calendari{auth_suffix}" target="_self">Agenda</a>
                <a href="?mod=modules.medicacio{auth_suffix}" target="_self">Medicació</a>
                <a href="?mod=modules.jocs{auth_suffix}" target="_self">Jocs</a>
            </div>
        </div>
        <div class="menu-item">
            <span class="menu-title">Ajustos</span>
            <div class="menu-dropdown">
                <a href="?mod=modules.admin{auth_suffix}" target="_self">Configuració global</a>
            </div>
        </div>
        <div class="menu-item">
            <span class="menu-title">Ajuda</span>
            <div class="menu-dropdown">
                <a href="?mod=modules.admin{auth_suffix}" target="_self">Panell de control i versió</a>
            </div>
        </div>
    </nav>
    """
    st.markdown(menubar_html, unsafe_allow_html=True)

if st.session_state.current_module is None:
    import textwrap
    
    # 1. Carregar el fons de pantalla completa
    fons_path = os.path.join(os.path.dirname(__file__), "imatges", "fons xiquiHouse.jpg")
    b64_fons = ""
    if os.path.exists(fons_path):
        with open(fons_path, "rb") as f_file:
            b64_fons = base64.b64encode(f_file.read()).decode()

    # 2. Carregar el logotip transparent
    logo_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.jpg")
        
    b64_logo = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            b64_logo = base64.b64encode(img_file.read()).decode()

    # Preservar el token d'autenticació a la URL
    auth_token = st.query_params.get("auth", "")
    auth_suffix = f"&auth={auth_token}" if auth_token else ""

    # Determinar rol
    role = st.session_state.get("role", "admin")
    role_icon = "👑" if role == "admin" else ("👁️‍🗨️" if role == "viewer" else "👤")
    role_title = "Administrador" if role == "admin" else ("Visor" if role == "viewer" else "Convidat")

    # Layout responsive integrat amb fons de pantalla completa i SVG Hotspots
    html_content = textwrap.dedent(f"""<style>
.stApp {{
    background-image: url("data:image/jpeg;base64,{b64_fons}") !important;
    background-size: cover !important;
    background-position: center center !important;
    background-repeat: no-repeat !important;
    background-attachment: fixed !important;
    background-color: #9fb5c2 !important;
}}
.block-container {{
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
    max-width: 100% !important;
}}
.role-badge {{
    position: fixed;
    top: 14px;
    right: 20px;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0;
    z-index: 99999;
    user-select: none;
    font-size: 1.6rem;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35));
    cursor: default;
}}
.main-wrapper {{
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    min-height: 90vh;
}}
.logo-box {{
    position: relative;
    display: block;
    width: 95vw;
    max-width: 1300px;
    margin: 0 auto;
    line-height: 0;
}}
.img-logo {{
    width: 100%;
    height: auto;
    display: block;
    pointer-events: none;
    user-select: none;
    filter: drop-shadow(0 15px 30px rgba(0,0,0,0.15));
}}
.hotspot-overlay {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 50;
    pointer-events: none;
}}
.svg-hotspot {{
    fill: rgba(0, 0, 0, 0.001);
    stroke: transparent;
    stroke-width: 1px;
    cursor: pointer !important;
    pointer-events: all !important;
    transition: fill 0.2s ease, stroke 0.2s ease, filter 0.2s ease;
    -webkit-tap-highlight-color: transparent;
}}
.svg-hotspot:hover, .svg-hotspot:active {{
    fill: rgba(2, 136, 209, 0.25) !important;
    stroke: rgba(2, 136, 209, 0.6) !important;
    stroke-width: 2px !important;
    filter: drop-shadow(0 0 10px rgba(2, 136, 209, 0.5));
}}

/* ================= AJUSTOS PER A MÒBILS I PANTALLES VERTICALS ================= */
@media (max-width: 768px) {{
    .stApp {{
        overflow-x: hidden !important;
    }}
    .main-wrapper {{
        min-height: 95vh !important;
        padding: 0 !important;
        overflow: hidden !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    .logo-box {{
        width: 100% !important;
        max-width: 100% !important;
        transform: scale(1.48) !important;
        transform-origin: center center !important;
    }}
}}
</style>

<!-- Indicador de Rol Usuari (Només icona neta) -->
<div class="role-badge" title="{role_title}">
    <span>{role_icon}</span>
</div>

<div class="main-wrapper">
<div class="logo-box">
<img src="data:image/png;base64,{b64_logo}" class="img-logo" alt="XiquiHouse">

<svg viewBox="0 0 1024 682" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" class="hotspot-overlay">
    <!-- ================= SENSE RODONA (SUPERIOR) ================= -->
    <!-- Icona engranatge: Configuracions -->
    <a href="?mod=modules.admin{auth_suffix}" xlink:href="?mod=modules.admin{auth_suffix}" target="_self">
        <circle cx="381.5" cy="127" r="34" class="svg-hotspot"><title>⚙️ Configuració Global</title></circle>
    </a>

    <!-- Icona pantalla + gràfic: Dashboard -->
    <a href="?mod=modules.dashboard{auth_suffix}" xlink:href="?mod=modules.dashboard{auth_suffix}" target="_self">
        <circle cx="626.5" cy="124.5" r="34" class="svg-hotspot"><title>📊 Dashboard General</title></circle>
    </a>

    <!-- ================= AMB RODONA PART ESQUERRA (5 NODES) ================= -->
    <!-- 1. Icona gràfic: Econòmic -->
    <a href="?mod=modules.economic{auth_suffix}" xlink:href="?mod=modules.economic{auth_suffix}" target="_self">
        <circle cx="282" cy="177" r="40" class="svg-hotspot"><title>📈 Mòdul Econòmic</title></circle>
    </a>

    <!-- 2. Icona càmara: Seguretat -->
    <a href="?mod=modules.seguretat{auth_suffix}" xlink:href="?mod=modules.seguretat{auth_suffix}" target="_self">
        <circle cx="176.5" cy="234.5" r="40" class="svg-hotspot"><title>📹 Seguretat i Càmeres</title></circle>
    </a>

    <!-- 3. Icona casa amb eina: Manteniment -->
    <a href="?mod=modules.manteniment{auth_suffix}" xlink:href="?mod=modules.manteniment{auth_suffix}" target="_self">
        <circle cx="282" cy="282.5" r="40" class="svg-hotspot"><title>🛠️ Manteniment de la Llar</title></circle>
    </a>

    <!-- 4. Icona wifi: Domòtica -->
    <a href="?mod=modules.domotica{auth_suffix}" xlink:href="?mod=modules.domotica{auth_suffix}" target="_self">
        <circle cx="175" cy="349.5" r="40" class="svg-hotspot"><title>📶 Domòtica (Home Assistant)</title></circle>
    </a>

    <!-- 5. Icona daus: Jocs -->
    <a href="?mod=modules.jocs{auth_suffix}" xlink:href="?mod=modules.jocs{auth_suffix}" target="_self">
        <circle cx="282" cy="393" r="40" class="svg-hotspot"><title>🎲 Jocs i Oci Familiar</title></circle>
    </a>

    <!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
    <!-- 6. Icona calendari: Agenda -->
    <a href="?mod=modules.calendari{auth_suffix}" xlink:href="?mod=modules.calendari{auth_suffix}" target="_self">
        <circle cx="739" cy="177" r="40" class="svg-hotspot"><title>📅 Agenda i Calendari</title></circle>
    </a>

    <!-- 7. Icona pastilles: Control Medicació -->
    <a href="?mod=modules.medicacio{auth_suffix}" xlink:href="?mod=modules.medicacio{auth_suffix}" target="_self">
        <circle cx="830" cy="233" r="40" class="svg-hotspot"><title>💊 Control de Medicació</title></circle>
    </a>

    <!-- 8. Icona cuberts: Menjar -->
    <a href="?mod=modules.menjar{auth_suffix}" xlink:href="?mod=modules.menjar{auth_suffix}" target="_self">
        <circle cx="736" cy="283.5" r="40" class="svg-hotspot"><title>🍽️ Menjar, Menús i Rebost</title></circle>
    </a>

    <!-- 9. Icona cotxe: Cotxe -->
    <a href="?mod=modules.cotxe{auth_suffix}" xlink:href="?mod=modules.cotxe{auth_suffix}" target="_self">
        <circle cx="828.5" cy="349.5" r="40" class="svg-hotspot"><title>🚗 Cotxe i Transport</title></circle>
    </a>

    <!-- 10. Icona carro compra: Compres Super/Stock -->
    <a href="?mod=modules.compres{auth_suffix}" xlink:href="?mod=modules.compres{auth_suffix}" target="_self">
        <circle cx="736" cy="398" r="40" class="svg-hotspot"><title>🛒 Compres al Súper i Stock</title></circle>
    </a>
</svg>

</div>
</div>""")

    st.markdown(html_content, unsafe_allow_html=True)

else:
    render_traditional_menubar()
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())
