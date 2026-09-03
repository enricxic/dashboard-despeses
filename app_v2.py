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
    
    /* Make home screen buttons massive */
    .home-button .stButton > button {
        height: 140px;
        font-size: 24px;
        font-weight: bold;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    
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
    st.write("")
    st.write("")
    st.markdown("<h1 style='text-align: center; margin-bottom: 40px;'>👑 Dashboard Principal</h1>", unsafe_allow_html=True)
    
    # We wrap buttons in a container that we can target via markdown if needed, but we'll just use a class wrapper
    st.markdown('<div class="home-button">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Àrea Econòmica", use_container_width=True):
            st.session_state.current_module = "modules.economic"
            st.rerun()
        if st.button("🍽️ Menjar i Rebost", use_container_width=True):
            st.session_state.current_module = "modules.menjar"
            st.rerun()
        if st.button("🏠 Domòtica i Llar", use_container_width=True):
            st.session_state.current_module = "modules.domotica"
            st.rerun()
            
    with col2:
        if st.button("🛒 Compres al Súper", use_container_width=True):
            st.session_state.current_module = "modules.compres"
            st.rerun()
        if st.button("📅 Agenda i Manteniment", use_container_width=True):
            st.session_state.current_module = "modules.calendari"
            st.rerun()
        if st.button("⚙️ Configuració Global", use_container_width=True):
            st.session_state.current_module = "modules.admin"
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

else:
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback; st.error(f"Error carregant el mòdul: {e}"); st.code(traceback.format_exc())
