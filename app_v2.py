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
    # Fons i ajust a pantalla completa
    st.markdown("""
<style>
    .stApp {
        background: #a9c7d8 !important;
    }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
    }
    .interactive-stage {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100vw;
        height: 100vh;
        margin: 0;
        padding: 0;
        overflow: hidden;
        background: #a9c7d8;
    }
    .interactive-container {
        position: relative;
        width: 100%;
        max-width: 1400px;
        height: 100%;
        max-height: 95vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .base-image {
        max-width: 100%;
        max-height: 95vh;
        width: auto;
        height: auto;
        object-fit: contain;
        display: block;
        pointer-events: none;
        user-select: none;
    }
    
    /* Botons rodons interactius */
    .hotspot {
        position: absolute;
        border-radius: 50%;
        cursor: pointer;
        transform: translate(-50%, -50%);
        transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 100;
        background: rgba(2, 136, 209, 0.01);
        border: 2px solid transparent;
        text-decoration: none !important;
        display: block;
    }
    
    .hotspot:hover {
        background: rgba(2, 136, 209, 0.28);
        border: 3px solid #0288d1;
        box-shadow: 0 0 25px 8px rgba(2, 136, 209, 0.65), inset 0 0 15px rgba(255,255,255,0.8);
        transform: translate(-50%, -50%) scale(1.16);
    }
    
    .hotspot:active {
        transform: translate(-50%, -50%) scale(0.95);
    }

    /* Tooltips personalitzats */
    .hotspot .tooltip {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        background: rgba(15, 23, 42, 0.95);
        color: #ffffff;
        text-align: center;
        padding: 7px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        white-space: nowrap;
        pointer-events: none;
        transition: opacity 0.2s ease, transform 0.2s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.35);
        z-index: 200;
    }

    .hotspot.left .tooltip {
        right: 110%;
        top: 50%;
        transform: translateY(-50%) translateX(8px);
    }
    .hotspot.left:hover .tooltip {
        visibility: visible;
        opacity: 1;
        transform: translateY(-50%) translateX(0);
    }

    .hotspot.right .tooltip {
        left: 110%;
        top: 50%;
        transform: translateY(-50%) translateX(-8px);
    }
    .hotspot.right:hover .tooltip {
        visibility: visible;
        opacity: 1;
        transform: translateY(-50%) translateX(0);
    }

    .hotspot.top .tooltip {
        bottom: 115%;
        left: 50%;
        transform: translateX(-50%) translateY(8px);
    }
    .hotspot.top:hover .tooltip {
        visibility: visible;
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }

    .hotspot.center-btn .tooltip {
        bottom: 115%;
        left: 50%;
        transform: translateX(-50%) translateY(8px);
    }
    .hotspot.center-btn:hover .tooltip {
        visibility: visible;
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }

    @keyframes pulse-ring {
        0% { box-shadow: 0 0 0 0 rgba(2, 136, 209, 0.5); }
        70% { box-shadow: 0 0 0 12px rgba(2, 136, 209, 0); }
        100% { box-shadow: 0 0 0 0 rgba(2, 136, 209, 0); }
    }
    .pulse-indicator {
        animation: pulse-ring 2.5s infinite;
    }
</style>
""", unsafe_allow_html=True)
    
    # Carregar la imatge en base64 des de imatges/logo xiquiHouse.jpg
    logo_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.jpg")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "logoXiquiHouse.png")
        
    b64_logo = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            b64_logo = base64.b64encode(img_file.read()).decode()
            
    # Renderitzat HTML sense indentació inicial per evitar blocs de codi markdown
    html_markup = f"""<div class="interactive-stage">
<div class="interactive-container" style="position: relative; display: inline-block;">
<img class="base-image" src="data:image/jpeg;base64,{b64_logo}" alt="XiquiHouse">
<a href="?mod=modules.domotica" target="_self" class="hotspot left pulse-indicator" style="left: 27.5%; top: 26.0%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">📶 Domòtica i Xarxa</span></a>
<a href="?mod=modules.domotica" target="_self" class="hotspot left pulse-indicator" style="left: 27.6%; top: 41.7%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">🌡️ Climatització i Sensors</span></a>
<a href="?mod=modules.domotica" target="_self" class="hotspot left pulse-indicator" style="left: 27.4%; top: 57.8%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">📹 Seguretat i Càmeres</span></a>
<a href="?mod=modules.economic" target="_self" class="hotspot right pulse-indicator" style="left: 72.2%; top: 26.2%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">🚗 Transport, Km i Gasolina</span></a>
<a href="?mod=modules.menjar" target="_self" class="hotspot right pulse-indicator" style="left: 72.1%; top: 41.6%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">🍽️ Menjar, Menús i Rebost</span></a>
<a href="?mod=modules.compres" target="_self" class="hotspot right pulse-indicator" style="left: 72.1%; top: 58.3%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">🛒 Compres al Súper i Tiquets</span></a>
<a href="?mod=modules.admin" target="_self" class="hotspot top" style="left: 37.1%; top: 17.8%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">⚙️ Configuració Global</span></a>
<a href="?mod=modules.economic" target="_self" class="hotspot top" style="left: 60.9%; top: 17.8%; width: 7.5%; aspect-ratio: 1/1;"><span class="tooltip">📊 Àrea Econòmica i Finances</span></a>
<a href="?mod=modules.calendari" target="_self" class="hotspot center-btn" style="left: 58.0%; top: 57.4%; width: 9%; aspect-ratio: 1/1;"><span class="tooltip">🗓️ Agenda i Manteniment</span></a>
<a href="?mod=modules.menjar" target="_self" class="hotspot center-btn" style="left: 46.4%; top: 57.4%; width: 9%; aspect-ratio: 1/1;"><span class="tooltip">🥕 Rebost i Productes</span></a>
</div>
</div>"""

    st.markdown(html_markup, unsafe_allow_html=True)

else:
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())
