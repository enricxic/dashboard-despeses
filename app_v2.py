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
    # Fons degradat suau estil llar connectada
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 40%, #7dd3fc 100%);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Carregar la imatge en base64
    logo_path = os.path.join(os.path.dirname(__file__), "logoXiquiHouse.png")
    b64_logo = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            b64_logo = base64.b64encode(img_file.read()).decode()
            
    # Component interactiu injectat directament al DOM amb st.markdown
    st.markdown(f"""
    <style>
        .interactive-stage {{
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            margin: 10px auto 30px auto;
        }}
        .interactive-container {{
            position: relative;
            width: 100%;
            max-width: 800px;
            margin: 0 auto;
            display: inline-block;
        }}
        .base-image {{
            width: 100%;
            height: auto;
            display: block;
            border-radius: 16px;
            pointer-events: none;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
        }}
        
        /* Botons rodons interactius */
        .hotspot {{
            position: absolute;
            border-radius: 50%;
            cursor: pointer;
            transform: translate(-50%, -50%);
            transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 100;
            background: rgba(2, 136, 209, 0.02);
            border: 2px solid transparent;
            text-decoration: none !important;
            display: block;
        }}
        
        .hotspot:hover {{
            background: rgba(2, 136, 209, 0.25);
            border: 3px solid #0288d1;
            box-shadow: 0 0 22px 6px rgba(2, 136, 209, 0.6), inset 0 0 12px rgba(255,255,255,0.7);
            transform: translate(-50%, -50%) scale(1.15);
        }}
        
        .hotspot:active {{
            transform: translate(-50%, -50%) scale(0.95);
        }}

        /* Tooltips personalitzats */
        .hotspot .tooltip {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            background: rgba(15, 23, 42, 0.95);
            color: #ffffff;
            text-align: center;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
            pointer-events: none;
            transition: opacity 0.2s ease, transform 0.2s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 200;
        }}

        /* Posició del tooltip */
        .hotspot.left .tooltip {{
            right: 110%;
            top: 50%;
            transform: translateY(-50%) translateX(8px);
        }}
        .hotspot.left:hover .tooltip {{
            visibility: visible;
            opacity: 1;
            transform: translateY(-50%) translateX(0);
        }}

        .hotspot.right .tooltip {{
            left: 110%;
            top: 50%;
            transform: translateY(-50%) translateX(-8px);
        }}
        .hotspot.right:hover .tooltip {{
            visibility: visible;
            opacity: 1;
            transform: translateY(-50%) translateX(0);
        }}

        .hotspot.top .tooltip {{
            bottom: 115%;
            left: 50%;
            transform: translateX(-50%) translateY(8px);
        }}
        .hotspot.top:hover .tooltip {{
            visibility: visible;
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }}

        .hotspot.center-btn .tooltip {{
            bottom: 115%;
            left: 50%;
            transform: translateX(-50%) translateY(8px);
        }}
        .hotspot.center-btn:hover .tooltip {{
            visibility: visible;
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }}

        /* Polsador subtil animat */
        @keyframes pulse-ring {{
            0% {{
                box-shadow: 0 0 0 0 rgba(2, 136, 209, 0.45);
            }}
            70% {{
                box-shadow: 0 0 0 10px rgba(2, 136, 209, 0);
            }}
            100% {{
                box-shadow: 0 0 0 0 rgba(2, 136, 209, 0);
            }}
        }}
        .pulse-indicator {{
            animation: pulse-ring 2.8s infinite;
        }}
    </style>

    <div class="interactive-stage">
        <div class="interactive-container">
            <img class="base-image" src="data:image/png;base64,{b64_logo}" alt="XiquiHouse">
            
            <!-- ================= ESQUERRA (3 NODES) ================= -->
            <!-- 1. Dalt Esquerra: WiFi / Domòtica -->
            <a href="?mod=modules.domotica" target="_self" class="hotspot left pulse-indicator" style="left: 27.4%; top: 25.4%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">📶 Domòtica i Xarxa</span>
            </a>

            <!-- 2. Centre Esquerra: Termòmetre / Climatització -->
            <a href="?mod=modules.domotica" target="_self" class="hotspot left pulse-indicator" style="left: 27.4%; top: 41.3%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">🌡️ Climatització i Sensors</span>
            </a>

            <!-- 3. Baix Esquerra: Càmera / Seguretat -->
            <a href="?mod=modules.domotica" target="_self" class="hotspot left pulse-indicator" style="left: 27.1%; top: 57.7%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">📹 Seguretat i Càmeres</span>
            </a>

            <!-- ================= DRETA (3 NODES) ================= -->
            <!-- 4. Dalt Dreta: Cotxe / Transport / Gasolina -->
            <a href="?mod=modules.economic" target="_self" class="hotspot right pulse-indicator" style="left: 72.1%; top: 25.5%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">🚗 Transport, Km i Gasolina</span>
            </a>

            <!-- 5. Centre Dreta: Menjar i Rebost -->
            <a href="?mod=modules.menjar" target="_self" class="hotspot right pulse-indicator" style="left: 71.9%; top: 41.3%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">🍽️ Menjar, Menús i Rebost</span>
            </a>

            <!-- 6. Baix Dreta: Compres al Súper -->
            <a href="?mod=modules.compres" target="_self" class="hotspot right pulse-indicator" style="left: 72.1%; top: 58.0%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">🛒 Compres al Súper i Tiquets</span>
            </a>

            <!-- ================= ZONES DE LA CASA ================= -->
            <!-- 7. Engranatge Superior: Configuració Global -->
            <a href="?mod=modules.admin" target="_self" class="hotspot top" style="left: 37.1%; top: 17.8%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">⚙️ Configuració Global</span>
            </a>

            <!-- 8. Gràfic i Monedes Superior: Àrea Econòmica -->
            <a href="?mod=modules.economic" target="_self" class="hotspot top" style="left: 60.9%; top: 17.8%; width: 7.5%; aspect-ratio: 1/1;">
                <span class="tooltip">📊 Àrea Econòmica i Finances</span>
            </a>

            <!-- 9. Cos Casa Dreta: Manteniment i Agenda -->
            <a href="?mod=modules.calendari" target="_self" class="hotspot center-btn" style="left: 58.0%; top: 57.4%; width: 9%; aspect-ratio: 1/1;">
                <span class="tooltip">🗓️ Agenda i Manteniment</span>
            </a>

            <!-- 10. Cos Casa Esquerra: Menjar i Rebost -->
            <a href="?mod=modules.menjar" target="_self" class="hotspot center-btn" style="left: 46.4%; top: 57.4%; width: 9%; aspect-ratio: 1/1;">
                <span class="tooltip">🥕 Rebost i Productes</span>
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
        
    # Barra d'accés ràpid opcional a sota per a màxima comoditat
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        if st.button("📊 Àrea Econòmica", use_container_width=True):
            st.session_state.current_module = "modules.economic"
            st.rerun()
    with c2:
        if st.button("🍽️ Menjar i Rebost", use_container_width=True):
            st.session_state.current_module = "modules.menjar"
            st.rerun()
    with c3:
        if st.button("🛒 Compres al Súper", use_container_width=True):
            st.session_state.current_module = "modules.compres"
            st.rerun()
    with c4:
        if st.button("🏡 Domòtica i Llar", use_container_width=True):
            st.session_state.current_module = "modules.domotica"
            st.rerun()
    with c5:
        if st.button("🗓️ Agenda", use_container_width=True):
            st.session_state.current_module = "modules.calendari"
            st.rerun()
    with c6:
        if st.button("⚙️ Configuració", use_container_width=True):
            st.session_state.current_module = "modules.admin"
            st.rerun()

else:
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())
