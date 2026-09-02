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
    footer {visibility: hidden;}
    .css-1d391kg {padding-top: 1rem;}
    /* Custom styling for the navigation radio buttons to make them look like pills */
    div.row-widget.stRadio > div { flex-direction: row; justify-content: center; gap: 10px;}
    </style>
''', unsafe_allow_html=True)

if not check_password():
    st.stop()

menu = {
    "📊 Econòmic": "modules.economic",
    "🛒 Compres Súper": "modules.compres",
    "🍽️ Menjar": "modules.menjar",
    "📅 Calendari": "modules.calendari",
    "🏠 Domòtica": "modules.domotica",
    "⚙️ Administració": "modules.admin"
}

st.markdown("### 🎛️ Navegació V2")

# st.pills or st.segmented_control if available, else horizontal radio
if hasattr(st, 'segmented_control'):
    selection = st.segmented_control("Mòdul", list(menu.keys()), default=list(menu.keys())[0], label_visibility="collapsed")
    if not selection:
        selection = list(menu.keys())[0]
elif hasattr(st, 'pills'):
    selection = st.pills("Mòdul", list(menu.keys()), default=list(menu.keys())[0], label_visibility="collapsed")
    if not selection:
        selection = list(menu.keys())[0]
else:
    selection = st.radio("Mòdul", list(menu.keys()), horizontal=True, label_visibility="collapsed")

st.markdown("---")

try:
    module_name = menu[selection]
    mod = importlib.import_module(module_name)
    mod.render()
except Exception as e:
    st.error(f"Error carregant el mòdul {selection}: {e}")
