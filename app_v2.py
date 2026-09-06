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
    transition: all 0.22s ease-in-out;
    background: rgba(2, 136, 209, 0.01);
    border: 2px solid transparent;
    text-decoration: none !important;
    display: block;
    -webkit-tap-highlight-color: rgba(2, 136, 209, 0.4);
}}
.hotspot:hover, .hotspot:active {{
    background: rgba(2, 136, 209, 0.32);
    border: 3px solid #0288d1;
    box-shadow: 0 0 25px 8px rgba(2, 136, 209, 0.7), inset 0 0 14px rgba(255,255,255,0.75);
    transform: translate(-50%, -50%) scale(1.14);
}}
@keyframes pulse-ring {{
    0% {{ box-shadow: 0 0 0 0 rgba(2, 136, 209, 0.55); }}
    70% {{ box-shadow: 0 0 0 12px rgba(2, 136, 209, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(2, 136, 209, 0); }}
}}
.pulse {{
    animation: pulse-ring 2.4s infinite;
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
        background: rgba(2, 136, 209, 0.01) !important;
    }}
    .hotspot.pulse {{
        border: none !important;
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
<a href="?mod=modules.economic{auth_suffix}" target="_self" class="hotspot pulse" style="left: 27.4%; top: 25.9%; width: 7.2%; height: 10.8%;" title="📈 Mòdul Econòmic"></a>

<!-- 2. Icona càmara: Seguretat -->
<a href="?mod=modules.seguretat{auth_suffix}" target="_self" class="hotspot pulse" style="left: 16.8%; top: 34.5%; width: 7.2%; height: 10.8%;" title="📹 Seguretat i Càmeres"></a>

<!-- 3. Icona casa amb eina: Manteniment -->
<a href="?mod=modules.manteniment{auth_suffix}" target="_self" class="hotspot pulse" style="left: 27.4%; top: 41.5%; width: 7.2%; height: 10.8%;" title="🛠️ Manteniment de la Llar"></a>

<!-- 4. Icona wifi: Domòtica -->
<a href="?mod=modules.domotica{auth_suffix}" target="_self" class="hotspot pulse" style="left: 17.1%; top: 51.5%; width: 7.2%; height: 10.8%;" title="📶 Domòtica (Home Assistant)"></a>

<!-- 5. Icona daus: Jocs -->
<a href="?mod=modules.jocs{auth_suffix}" target="_self" class="hotspot pulse" style="left: 27.4%; top: 57.6%; width: 7.2%; height: 10.8%;" title="🎲 Jocs i Oci Familiar"></a>

<!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
<!-- 6. Icona calendari: Agenda -->
<a href="?mod=modules.calendari{auth_suffix}" target="_self" class="hotspot pulse" style="left: 72.4%; top: 26.0%; width: 7.2%; height: 10.8%;" title="📅 Agenda i Calendari"></a>

<!-- 7. Icona pastilles: Control Medicació -->
<a href="?mod=modules.medicacio{auth_suffix}" target="_self" class="hotspot pulse" style="left: 81.3%; top: 34.2%; width: 7.2%; height: 10.8%;" title="💊 Control de Medicació"></a>

<!-- 8. Icona cuberts: Menjar -->
<a href="?mod=modules.menjar{auth_suffix}" target="_self" class="hotspot pulse" style="left: 72.0%; top: 41.6%; width: 7.2%; height: 10.8%;" title="🍽️ Menjar, Menús i Rebost"></a>

<!-- 9. Icona cotxe: Cotxe -->
<a href="?mod=modules.cotxe{auth_suffix}" target="_self" class="hotspot pulse" style="left: 81.1%; top: 51.3%; width: 7.2%; height: 10.8%;" title="🚗 Cotxe i Transport"></a>

<!-- 10. Icona carro compra: Compres Super/Stock -->
<a href="?mod=modules.compres{auth_suffix}" target="_self" class="hotspot pulse" style="left: 71.9%; top: 58.5%; width: 7.2%; height: 10.8%;" title="🛒 Compres al Súper i Stock"></a>

<!-- ================= INTERIOR DE LA CASA ================= -->
<!-- Rebost interior -->
<a href="?mod=modules.menjar{auth_suffix}" target="_self" class="hotspot" style="left: 41.0%; top: 55.5%; width: 8.0%; height: 12.0%;" title="🥕 Rebost i Productes"></a>

<!-- Eines interior -->
<a href="?mod=modules.manteniment{auth_suffix}" target="_self" class="hotspot" style="left: 58.5%; top: 55.5%; width: 8.0%; height: 12.0%;" title="🛠️ Tasques i Reparacions"></a>

</div>
</div>""")

    st.markdown(html_content, unsafe_allow_html=True)

else:
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())
