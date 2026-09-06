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

if 'current_module' not in st.session_state:
    st.session_state.current_module = None

def render_traditional_menubar():
    st.markdown("""
        <style>
        /* Traditional Desktop Menu Bar styling - Discreet & Minimal */
        div[data-testid="stPopover"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stPopover"] > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #94a3b8 !important;
            font-size: 0.76rem !important;
            font-weight: 400 !important;
            padding: 1px 7px !important;
            min-height: 22px !important;
            height: 22px !important;
            border-radius: 2px !important;
            line-height: 1 !important;
        }
        div[data-testid="stPopover"] > button:hover {
            background-color: rgba(255, 255, 255, 0.08) !important;
            color: #f8fafc !important;
        }
        div[data-testid="stPopover"] > button:focus, div[data-testid="stPopover"] > button:active {
            background-color: rgba(2, 136, 209, 0.25) !important;
            color: #ffffff !important;
        }
        div[data-testid="stPopover"] > button svg {
            display: none !important;
        }
        div[data-testid="stPopoverBody"] {
            background-color: #1e293b !important;
            border: 1px solid #334155 !important;
            border-radius: 4px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
            padding: 4px !important;
            min-width: 190px !important;
        }
        div[data-testid="stPopoverBody"] button {
            text-align: left !important;
            justify-content: flex-start !important;
            font-size: 0.78rem !important;
            padding: 4px 8px !important;
            margin-bottom: 1px !important;
            border: none !important;
            background: transparent !important;
            color: #cbd5e1 !important;
            border-radius: 3px !important;
            width: 100% !important;
        }
        div[data-testid="stPopoverBody"] button:hover {
            background-color: #0284c7 !important;
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5, c6, c_spacer = st.columns([0.7, 0.85, 0.6, 0.8, 0.8, 0.65, 8.6], vertical_alignment="center")
    
    with c1:
        with st.popover("Arxiu"):
            if st.button("Pantalla d'inici", use_container_width=True, key="m_arxiu_inici"):
                st.session_state.current_module = None
                st.rerun()
            if st.button("Reiniciar sessió", use_container_width=True, key="m_arxiu_reset"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
            if st.button("Tancar sessió", use_container_width=True, key="m_arxiu_logout"):
                if "password_correct" in st.session_state:
                    del st.session_state["password_correct"]
                if "auth" in st.query_params:
                    del st.query_params["auth"]
                st.rerun()

    with c2:
        with st.popover("Finances"):
            if st.button("Dashboard General", use_container_width=True, key="m_fin_dash"):
                st.session_state.current_module = "modules.dashboard"
                st.rerun()
            if st.button("Mòdul Econòmic", use_container_width=True, key="m_fin_econ"):
                st.session_state.current_module = "modules.economic"
                st.rerun()
            if st.button("Compres i tiquets súper", use_container_width=True, key="m_fin_comp"):
                st.session_state.current_module = "modules.compres"
                st.rerun()

    with c3:
        with st.popover("Llar"):
            if st.button("Menús i cuina", use_container_width=True, key="m_llar_menjar"):
                st.session_state.current_module = "modules.menjar"
                st.rerun()
            if st.button("Manteniment", use_container_width=True, key="m_llar_mant"):
                st.session_state.current_module = "modules.manteniment"
                st.rerun()
            if st.button("Cotxe", use_container_width=True, key="m_llar_cotxe"):
                st.session_state.current_module = "modules.cotxe"
                st.rerun()
            if st.button("Domòtica", use_container_width=True, key="m_llar_dom"):
                st.session_state.current_module = "modules.domotica"
                st.rerun()
            if st.button("Seguretat", use_container_width=True, key="m_llar_seg"):
                st.session_state.current_module = "modules.seguretat"
                st.rerun()

    with c4:
        with st.popover("Família"):
            if st.button("Agenda", use_container_width=True, key="m_fam_cal"):
                st.session_state.current_module = "modules.calendari"
                st.rerun()
            if st.button("Medicació", use_container_width=True, key="m_fam_med"):
                st.session_state.current_module = "modules.medicacio"
                st.rerun()
            if st.button("Jocs", use_container_width=True, key="m_fam_jocs"):
                st.session_state.current_module = "modules.jocs"
                st.rerun()

    with c5:
        with st.popover("Ajustos"):
            if st.button("Configuració global", use_container_width=True, key="m_aj_admin"):
                st.session_state.current_module = "modules.admin"
                st.rerun()

    with c6:
        with st.popover("Ajuda"):
            st.caption("XiquiHouse v2.2.0")
            if st.button("Panell de control", use_container_width=True, key="m_aj_doc"):
                st.session_state.current_module = "modules.admin"
                st.rerun()

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

    # Layout responsive integrat amb fons de pantalla completa
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
.main-wrapper {{
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    min-height: 88vh;
}}
.logo-box {{
    position: relative;
    display: inline-block;
    width: 100%;
    max-width: 1100px;
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
.hotspot {{
    position: absolute;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    cursor: pointer;
    z-index: 50;
    transition: all 0.2s ease-in-out;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    text-decoration: none !important;
    display: block;
    -webkit-tap-highlight-color: transparent;
}}
.hotspot:hover, .hotspot:active {{
    background: rgba(2, 136, 209, 0.22) !important;
    box-shadow: 0 0 15px rgba(2, 136, 209, 0.4) !important;
    transform: translate(-50%, -50%) scale(1.08);
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
    /* Mida tàctil còmoda i fàcil de prémer al mòbil */
    .hotspot {{
        width: 10.5% !important;
        height: 14.5% !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
}}
</style>

<div class="main-wrapper">
<div class="logo-box">
<img src="data:image/png;base64,{b64_logo}" class="img-logo" alt="XiquiHouse">

<!-- ================= SENSE RODONA (SUPERIOR) ================= -->
<!-- Icona engranatge: Configuracions -->
<a href="?mod=modules.admin{auth_suffix}" target="_self" class="hotspot" style="left: 37.3%; top: 18.6%; width: 7.5%; height: 11.2%;" title="⚙️ Configuració Global"></a>

<!-- Icona pantalla + gràfic: Dashboard -->
<a href="?mod=modules.dashboard{auth_suffix}" target="_self" class="hotspot" style="left: 61.2%; top: 18.3%; width: 7.5%; height: 11.2%;" title="📊 Dashboard General"></a>

<!-- ================= AMB RODONA PART ESQUERRA (5 NODES) ================= -->
<!-- 1. Icona gràfic: Econòmic -->
<a href="?mod=modules.economic{auth_suffix}" target="_self" class="hotspot" style="left: 27.4%; top: 25.9%; width: 7.2%; height: 10.8%;" title="📈 Mòdul Econòmic"></a>

<!-- 2. Icona càmara: Seguretat -->
<a href="?mod=modules.seguretat{auth_suffix}" target="_self" class="hotspot" style="left: 16.8%; top: 34.5%; width: 7.2%; height: 10.8%;" title="📹 Seguretat i Càmeres"></a>

<!-- 3. Icona casa amb eina: Manteniment -->
<a href="?mod=modules.manteniment{auth_suffix}" target="_self" class="hotspot" style="left: 27.4%; top: 41.5%; width: 7.2%; height: 10.8%;" title="🛠️ Manteniment de la Llar"></a>

<!-- 4. Icona wifi: Domòtica -->
<a href="?mod=modules.domotica{auth_suffix}" target="_self" class="hotspot" style="left: 17.1%; top: 51.5%; width: 7.2%; height: 10.8%;" title="📶 Domòtica (Home Assistant)"></a>

<!-- 5. Icona daus: Jocs -->
<a href="?mod=modules.jocs{auth_suffix}" target="_self" class="hotspot" style="left: 27.4%; top: 57.6%; width: 7.2%; height: 10.8%;" title="🎲 Jocs i Oci Familiar"></a>

<!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
<!-- 6. Icona calendari: Agenda -->
<a href="?mod=modules.calendari{auth_suffix}" target="_self" class="hotspot" style="left: 72.4%; top: 26.0%; width: 7.2%; height: 10.8%;" title="📅 Agenda i Calendari"></a>

<!-- 7. Icona pastilles: Control Medicació -->
<a href="?mod=modules.medicacio{auth_suffix}" target="_self" class="hotspot" style="left: 81.3%; top: 34.2%; width: 7.2%; height: 10.8%;" title="💊 Control de Medicació"></a>

<!-- 8. Icona cuberts: Menjar -->
<a href="?mod=modules.menjar{auth_suffix}" target="_self" class="hotspot" style="left: 72.0%; top: 41.6%; width: 7.2%; height: 10.8%;" title="🍽️ Menjar, Menús i Rebost"></a>

<!-- 9. Icona cotxe: Cotxe -->
<a href="?mod=modules.cotxe{auth_suffix}" target="_self" class="hotspot" style="left: 81.1%; top: 51.3%; width: 7.2%; height: 10.8%;" title="🚗 Cotxe i Transport"></a>

<!-- 10. Icona carro compra: Compres Super/Stock -->
<a href="?mod=modules.compres{auth_suffix}" target="_self" class="hotspot" style="left: 71.9%; top: 58.5%; width: 7.2%; height: 10.8%;" title="🛒 Compres al Súper i Stock"></a>

<!-- ================= INTERIOR DE LA CASA ================= -->
<!-- Rebost interior -->
<a href="?mod=modules.menjar{auth_suffix}" target="_self" class="hotspot" style="left: 41.0%; top: 55.5%; width: 8.0%; height: 12.0%;" title="🥕 Rebost i Productes"></a>

<!-- Eines interior -->
<a href="?mod=modules.manteniment{auth_suffix}" target="_self" class="hotspot" style="left: 58.5%; top: 55.5%; width: 8.0%; height: 12.0%;" title="🛠️ Tasques i Reparacions"></a>

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
