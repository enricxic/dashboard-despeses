import streamlit as st
import importlib

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

if 'role' not in st.session_state:
    st.session_state['role'] = 'guest'

def set_role():
    st.session_state['role'] = st.session_state.temp_role_selector

with st.sidebar:
    rol_index = 0 if st.session_state.get('role') == 'admin' else 1
    selected_role = st.selectbox(
        "Rol Actual",
        ["admin", "guest"],
        index=rol_index,
        on_change=set_role,
        key="temp_role_selector"
    )
    
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
