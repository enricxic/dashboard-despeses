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
    st.query_params.clear()
    st.rerun()

if 'current_module' not in st.session_state:
    st.session_state.current_module = None

if st.session_state.current_module is None:
    import textwrap
    # Carregar la imatge en base64 des de imatges/logo xiquiHouse.jpg
    logo_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.jpg")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "logoXiquiHouse.png")
        
    b64_logo = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            b64_logo = base64.b64encode(img_file.read()).decode()

    # SVG natiu interactiu de pantalla completa sense indentació
    svg_fullscreen = textwrap.dedent(f"""<style>
/* Netejar marges de Streamlit per a la pantalla d'inici */
.stApp {{
    background-color: #9fb5c2 !important;
    overflow: hidden !important;
}}
.block-container {{
    padding: 0 !important;
    max-width: 100vw !important;
    margin: 0 !important;
}}

/* Contenidor a pantalla completa fixa */
.xiqui-fullscreen {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: #9fb5c2;
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 999;
    margin: 0;
    padding: 0;
}}

.xiqui-svg {{
    width: 100vw;
    height: 100vh;
    max-width: 100%;
    max-height: 100%;
    display: block;
}}

/* Estils dels botons circulars sobre el SVG */
.svg-hotspot {{
    fill: rgba(2, 136, 209, 0.01);
    stroke: transparent;
    stroke-width: 8;
    cursor: pointer;
    transition: all 0.22s ease-in-out;
}}

.svg-hotspot:hover {{
    fill: rgba(2, 136, 209, 0.3);
    stroke: #0288d1;
    stroke-width: 10;
    filter: drop-shadow(0px 0px 14px #0288d1);
}}

/* Efecte polsador animat */
@keyframes svg-pulse {{
    0% {{ stroke-width: 6; stroke: rgba(2, 136, 209, 0.5); }}
    50% {{ stroke-width: 14; stroke: rgba(2, 136, 209, 0.1); }}
    100% {{ stroke-width: 6; stroke: rgba(2, 136, 209, 0.5); }}
}}
.pulse-node {{
    animation: svg-pulse 2.6s infinite ease-in-out;
}}
</style>

<div class="xiqui-fullscreen">
<svg class="xiqui-svg" viewBox="0 0 1772 1181" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
<!-- Fons / Logotip d'alta definició -->
<image href="data:image/jpeg;base64,{b64_logo}" width="1772" height="1181" preserveAspectRatio="xMidYMid slice"/>

<!-- ================= ESQUERRA (3 BOTONS) ================= -->
<!-- 1. Dalt Esquerra: WiFi / Domòtica -->
<a href="?mod=modules.domotica" target="_self">
<circle class="svg-hotspot pulse-node" cx="488" cy="307" r="62">
<title>📶 Domòtica i Llar</title>
</circle>
</a>

<!-- 2. Centre Esquerra: Termòmetre / Climatització -->
<a href="?mod=modules.domotica" target="_self">
<circle class="svg-hotspot pulse-node" cx="489" cy="493" r="62">
<title>🌡️ Climatització i Sensors</title>
</circle>
</a>

<!-- 3. Baix Esquerra: Càmera / Seguretat -->
<a href="?mod=modules.domotica" target="_self">
<circle class="svg-hotspot pulse-node" cx="485" cy="683" r="62">
<title>📹 Seguretat i Càmeres</title>
</circle>
</a>

<!-- ================= DRETA (3 BOTONS) ================= -->
<!-- 4. Dalt Dreta: Cotxe / Transport / Gasolina -->
<a href="?mod=modules.economic" target="_self">
<circle class="svg-hotspot pulse-node" cx="1280" cy="309" r="62">
<title>🚗 Transport, Km i Gasolina</title>
</circle>
</a>

<!-- 5. Centre Dreta: Menjar i Rebost -->
<a href="?mod=modules.menjar" target="_self">
<circle class="svg-hotspot pulse-node" cx="1277" cy="491" r="62">
<title>🍽️ Menjar, Menús i Rebost</title>
</circle>
</a>

<!-- 6. Baix Dreta: Compres al Súper -->
<a href="?mod=modules.compres" target="_self">
<circle class="svg-hotspot pulse-node" cx="1277" cy="688" r="62">
<title>🛒 Compres al Súper i Tiquets</title>
</circle>
</a>

<!-- ================= ELEMENTS DE LA CASA ================= -->
<!-- 7. Engranatge Superior: Configuració Global -->
<a href="?mod=modules.admin" target="_self">
<circle class="svg-hotspot" cx="655" cy="208" r="70">
<title>⚙️ Configuració Global</title>
</circle>
</a>

<!-- 8. Gràfic Superior: Àrea Econòmica -->
<a href="?mod=modules.economic" target="_self">
<circle class="svg-hotspot" cx="1075" cy="208" r="70">
<title>📊 Àrea Econòmica i Finances</title>
</circle>
</a>

<!-- 9. Cos Casa Dreta: Manteniment i Agenda -->
<a href="?mod=modules.calendari" target="_self">
<circle class="svg-hotspot" cx="1030" cy="678" r="88">
<title>🗓️ Agenda i Manteniment</title>
</circle>
</a>

<!-- 10. Cos Casa Esquerra: Rebost -->
<a href="?mod=modules.menjar" target="_self">
<circle class="svg-hotspot" cx="820" cy="678" r="88">
<title>🥕 Rebost i Productes</title>
</circle>
</a>
</svg>
</div>""")

    if hasattr(st, "html"):
        st.html(svg_fullscreen)
    else:
        st.markdown(svg_fullscreen, unsafe_allow_html=True)

else:
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())
