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

    # Layout responsive integrat amb fons de pantalla completa i Hotspots HTML
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
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin: 0 auto !important;
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
    font-size: 1.75rem;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35));
    cursor: default;
}}
.main-wrapper {{
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    min-height: 95vh;
    padding: 0;
    margin: 0 auto;
}}
.logo-box {{
    position: relative;
    display: block;
    width: min(94vw, 138vh);
    aspect-ratio: 1024 / 682;
    margin: 0 auto;
    line-height: 0;
}}
.img-logo {{
    width: 100%;
    height: 100%;
    display: block;
    pointer-events: none;
    user-select: none;
    object-fit: contain;
    filter: drop-shadow(0 15px 30px rgba(0,0,0,0.15));
}}
.hotspot {{
    position: absolute;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    cursor: pointer !important;
    z-index: 100;
    transition: all 0.15s ease-in-out;
    background: rgba(0, 0, 0, 0.001) !important;
    border: 2px solid transparent !important;
    box-shadow: none !important;
    outline: none !important;
    text-decoration: none !important;
    display: block !important;
    -webkit-tap-highlight-color: transparent;
}}
.hotspot:hover, .hotspot:active {{
    background: rgba(2, 136, 209, 0.25) !important;
    border: 2px solid rgba(2, 136, 209, 0.6) !important;
    box-shadow: 0 0 16px rgba(2, 136, 209, 0.55) !important;
}}

/* ================= AJUSTOS PER A MÒBILS I PANTALLES VERTICALS ================= */
@media (max-width: 768px) {{
    .stApp {{
        overflow-x: hidden !important;
    }}
    .main-wrapper {{
        min-height: 96vh !important;
        padding: 0 !important;
    }}
    .logo-box {{
        width: 100vw !important;
        max-width: 100vw !important;
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

<!-- ================= SENSE RODONA (SUPERIOR) ================= -->
<!-- Icona engranatge: Configuracions -->
<a href="?mod=modules.admin{auth_suffix}" target="_self" class="hotspot" style="left: 37.33%; top: 18.43%; width: 7.2%;" title="⚙️ Configuració Global"></a>

<!-- Icona pantalla + gràfic: Dashboard -->
<a href="?mod=modules.dashboard{auth_suffix}" target="_self" class="hotspot" style="left: 61.18%; top: 18.26%; width: 7.2%;" title="📊 Dashboard General"></a>

<!-- ================= AMB RODONA PART ESQUERRA (5 NODES) ================= -->
<!-- 1. Icona gràfic: Econòmic -->
<a href="?mod=modules.economic{auth_suffix}" target="_self" class="hotspot" style="left: 27.54%; top: 25.95%; width: 8.2%;" title="📈 Mòdul Econòmic"></a>

<!-- 2. Icona càmara: Seguretat -->
<a href="?mod=modules.seguretat{auth_suffix}" target="_self" class="hotspot" style="left: 17.24%; top: 34.38%; width: 8.2%;" title="📹 Seguretat i Càmeres"></a>

<!-- 3. Icona casa amb eina: Manteniment -->
<a href="?mod=modules.manteniment{auth_suffix}" target="_self" class="hotspot" style="left: 27.54%; top: 41.42%; width: 8.2%;" title="🛠️ Manteniment de la Llar"></a>

<!-- 4. Icona wifi: Domòtica -->
<a href="?mod=modules.domotica{auth_suffix}" target="_self" class="hotspot" style="left: 17.09%; top: 51.25%; width: 8.2%;" title="📶 Domòtica (Home Assistant)"></a>

<!-- 5. Icona daus: Jocs -->
<a href="?mod=modules.jocs{auth_suffix}" target="_self" class="hotspot" style="left: 27.54%; top: 57.62%; width: 8.2%;" title="🎲 Jocs i Oci Familiar"></a>

<!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
<!-- 6. Icona calendari: Agenda -->
<a href="?mod=modules.calendari{auth_suffix}" target="_self" class="hotspot" style="left: 72.17%; top: 25.95%; width: 8.2%;" title="📅 Agenda i Calendari"></a>

<!-- 7. Icona pastilles: Control Medicació -->
<a href="?mod=modules.medicacio{auth_suffix}" target="_self" class="hotspot" style="left: 81.05%; top: 34.16%; width: 8.2%;" title="💊 Control de Medicació"></a>

<!-- 8. Icona cuberts: Menjar -->
<a href="?mod=modules.menjar{auth_suffix}" target="_self" class="hotspot" style="left: 71.88%; top: 41.57%; width: 8.2%;" title="🍽️ Menjar, Menús i Rebost"></a>

<!-- 9. Icona cotxe: Cotxe -->
<a href="?mod=modules.cotxe{auth_suffix}" target="_self" class="hotspot" style="left: 80.91%; top: 51.25%; width: 8.2%;" title="🚗 Cotxe i Transport"></a>

<!-- 10. Icona carro compra: Compres Super/Stock -->
<a href="?mod=modules.compres{auth_suffix}" target="_self" class="hotspot" style="left: 71.88%; top: 58.36%; width: 8.2%;" title="🛒 Compres al Súper i Stock"></a>

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
