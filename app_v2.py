import streamlit as st
import importlib
from core.auth import check_password

st.set_page_config(
    page_title="Dashboard V2",
    page_icon="👑",
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

if 'current_module' not in st.session_state:
    st.session_state.current_module = None

if st.session_state.current_module is None:
    
    # Add light blue gradient to home screen only and massive square buttons
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 50%, #80deea 100%);
        }
        div.stButton > button {
            height: 180px !important;
            font-size: 24px !important;
            background-color: rgba(255, 255, 255, 0.85) !important;
            color: #111 !important;
            border: 2px solid #fff !important;
            border-radius: 15px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
            margin-bottom: 20px !important;
        }
        div.stButton > button:hover {
            background-color: white !important;
            border-color: #2980b9 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # Logo centered using base64
    col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
    with col_l2:
        try:
            import base64
            import os
            logo_path = os.path.join(os.path.dirname(__file__), "logoXiquiHouse.png")
            with open(logo_path, "rb") as img_file:
                b64_logo = base64.b64encode(img_file.read()).decode()
            st.markdown(f'<div style="text-align: center; margin-bottom: 40px;"><img src="data:image/png;base64,{b64_logo}" style="width: 100%; max-width: 400px; border-radius: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(str(e))
            st.markdown("<h1 style='text-align: center; margin-bottom: 40px; color: #333;'>👑 Dashboard Principal</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Àrea Econòmica", use_container_width=True):
            st.session_state.current_module = "modules.economic"
            st.rerun()
        if st.button("🍽️ Menjar i Rebost", use_container_width=True):
            st.session_state.current_module = "modules.menjar"
            st.rerun()
            
    with col2:
        if st.button("🛒 Compres al Súper", use_container_width=True):
            st.session_state.current_module = "modules.compres"
            st.rerun()
        if st.button("🗓️ Agenda i Manteniment", use_container_width=True):
            st.session_state.current_module = "modules.calendari"
            st.rerun()
            
    with col3:
        if st.button("🏡 Domòtica i Llar", use_container_width=True):
            st.session_state.current_module = "modules.domotica"
            st.rerun()
        if st.button("⚙️ Configuració Global", use_container_width=True):
            st.session_state.current_module = "modules.admin"
            st.rerun()

else:
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback; st.error(f"Error carregant el mòdul: {e}"); st.code(traceback.format_exc())
