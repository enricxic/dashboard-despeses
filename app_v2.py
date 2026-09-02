import streamlit as st
import importlib
from core.auth import check_password

st.set_page_config(
    page_title="Dashboard V2",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown('''
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .css-1d391kg {padding-top: 1rem;}
    </style>
''', unsafe_allow_html=True)

if not check_password():
    st.stop()

with st.sidebar:
    st.markdown("---")
    st.markdown("### 🎛️ Navegació V2")
    
    menu = {
        "📊 Econòmic": "modules.economic",
        "🛒 Compres Súper": "modules.compres",
        "🍽️ Menjar": "modules.menjar",
        "📅 Calendari": "modules.calendari",
        "🏠 Domòtica": "modules.domotica",
        "⚙️ Administració": "modules.admin"
    }
    
    selection = st.radio("Mòdul Actiu:", list(menu.keys()))
    
    st.markdown("---")
    st.info("Aquesta és la versió de prova modular. L'app original continua funcionant a app.py.")

try:
    module_name = menu[selection]
    mod = importlib.import_module(module_name)
    mod.render()
except Exception as e:
    st.error(f"Error carregant el mòdul {selection}: {e}")
