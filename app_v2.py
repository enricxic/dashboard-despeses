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

    # Layout centrat i calibrat amb precisió de píxels
    html_content = textwrap.dedent(f"""<style>
.stApp {{
    background-color: #9fb5c2 !important;
}}
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}}
.main-wrapper {{
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    min-height: 85vh;
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
    border-radius: 16px;
    box-shadow: 0 12px 35px rgba(0,0,0,0.18);
    pointer-events: none;
    user-select: none;
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
}}
.hotspot:hover {{
    background: rgba(2, 136, 209, 0.3);
    border: 3px solid #0288d1;
    box-shadow: 0 0 22px 6px rgba(2, 136, 209, 0.65), inset 0 0 12px rgba(255,255,255,0.7);
    transform: translate(-50%, -50%) scale(1.12);
}}
@keyframes pulse-ring {{
    0% {{ box-shadow: 0 0 0 0 rgba(2, 136, 209, 0.5); }}
    70% {{ box-shadow: 0 0 0 10px rgba(2, 136, 209, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(2, 136, 209, 0); }}
}}
.pulse {{
    animation: pulse-ring 2.6s infinite;
}}
</style>

<div class="main-wrapper">
<div class="logo-box">
<img src="data:image/jpeg;base64,{b64_logo}" class="img-logo" alt="XiquiHouse">

<!-- 1. Dalt Esquerra: WiFi / Domòtica -->
<a href="?mod=modules.domotica" target="_self" class="hotspot pulse" style="left: 27.5%; top: 26.0%; width: 7.2%; height: 10.8%;" title="📶 Domòtica i Llar"></a>

<!-- 2. Centre Esquerra: Termòmetre / Climatització -->
<a href="?mod=modules.domotica" target="_self" class="hotspot pulse" style="left: 27.6%; top: 41.7%; width: 7.2%; height: 10.8%;" title="🌡️ Climatització i Sensors"></a>

<!-- 3. Baix Esquerra: Càmera / Seguretat -->
<a href="?mod=modules.domotica" target="_self" class="hotspot pulse" style="left: 27.4%; top: 57.8%; width: 7.2%; height: 10.8%;" title="📹 Seguretat i Càmeres"></a>

<!-- 4. Dalt Dreta: Cotxe / Transport / Gasolina -->
<a href="?mod=modules.economic" target="_self" class="hotspot pulse" style="left: 72.2%; top: 26.2%; width: 7.2%; height: 10.8%;" title="🚗 Transport, Km i Gasolina"></a>

<!-- 5. Centre Dreta: Menjar i Rebost -->
<a href="?mod=modules.menjar" target="_self" class="hotspot pulse" style="left: 72.1%; top: 41.6%; width: 7.2%; height: 10.8%;" title="🍽️ Menjar, Menús i Rebost"></a>

<!-- 6. Baix Dreta: Compres al Súper -->
<a href="?mod=modules.compres" target="_self" class="hotspot pulse" style="left: 72.1%; top: 58.3%; width: 7.2%; height: 10.8%;" title="🛒 Compres al Súper i Tiquets"></a>

<!-- 7. Engranatge Superior: Configuració Global -->
<a href="?mod=modules.admin" target="_self" class="hotspot" style="left: 37.0%; top: 17.6%; width: 8.0%; height: 12.0%;" title="⚙️ Configuració Global"></a>

<!-- 8. Gràfic Superior: Àrea Econòmica -->
<a href="?mod=modules.economic" target="_self" class="hotspot" style="left: 60.7%; top: 17.6%; width: 8.0%; height: 12.0%;" title="📊 Àrea Econòmica i Finances"></a>

<!-- 9. Cos Casa Dreta: Manteniment i Agenda -->
<a href="?mod=modules.calendari" target="_self" class="hotspot" style="left: 58.1%; top: 57.4%; width: 9.5%; height: 14.5%;" title="🗓️ Agenda i Manteniment"></a>

<!-- 10. Cos Casa Esquerra: Rebost -->
<a href="?mod=modules.menjar" target="_self" class="hotspot" style="left: 46.3%; top: 57.4%; width: 9.5%; height: 14.5%;" title="🥕 Rebost i Productes"></a>
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
