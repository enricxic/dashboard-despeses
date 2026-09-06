import streamlit as st
import importlib
import base64
import os
import textwrap
from core.auth import check_password
from core.config_manager import load_app_config

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

app_cfg = load_app_config()

# Comprovar si s'ha seleccionat un mòdul a través de query params (des de l'HTML interactiu)
if "mod" in st.query_params:
    selected_mod = st.query_params.get("mod")
    st.session_state.current_module = selected_mod
    try:
        del st.query_params["mod"]
    except Exception:
        pass
    st.rerun()

# Comprovar si s'ha sol·licitat una acció des del menú superior (Home, Reset, Logout, DB Actions)
if "action" in st.query_params:
    act = st.query_params.get("action")
    if act == "home":
        st.session_state.current_module = None
    elif act == "reset":
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.cache_data.clear()
    elif act == "logout":
        if "password_correct" in st.session_state:
            del st.session_state["password_correct"]
        if "auth" in st.query_params:
            del st.query_params["auth"]
    elif act == "sync_db":
        st.cache_data.clear()
        st.session_state["db_synced_toast"] = True
    elif act == "backup_db":
        import zipfile
        os.makedirs("backup_dades", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join("backup_dades", f"backup_dades_{ts}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists("csv"):
                for root, _, files in os.walk("csv"):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, "csv"))
            if os.path.exists("core/config.json"):
                zipf.write("core/config.json", "config.json")
        st.session_state["db_backup_toast"] = os.path.basename(zip_path)
    try:
        del st.query_params["action"]
    except Exception:
        pass
    st.rerun()

if st.session_state.get("db_synced_toast"):
    st.toast("🔄 Memòria cau alliberada i dades sincronitzades!", icon="⚡")
    del st.session_state["db_synced_toast"]

if st.session_state.get("db_backup_toast"):
    st.toast(f"💾 Còpia de seguretat desada a backup_dades/{st.session_state['db_backup_toast']}", icon="✅")
    del st.session_state["db_backup_toast"]

if 'current_module' not in st.session_state:
    st.session_state.current_module = None

def render_traditional_menubar():
    auth_token = st.query_params.get("auth", "")
    auth_suffix = f"&auth={auth_token}" if auth_token else ""
    icones_actives = app_cfg.get("icones_actives", {})
    
    menubar_html = f"""<style>
.desktop-menubar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    background: transparent;
    padding: 0px;
    margin: -0.8rem 0 0.1rem 0;
    gap: 18px;
    user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 0.78rem;
    z-index: 9999;
}}
.desktop-menubar .menu-item {{
    position: relative;
    cursor: pointer;
    display: inline-block;
}}
.desktop-menubar .menu-title {{
    color: #94a3b8;
    padding: 2px 4px;
    border-radius: 2px;
    transition: all 0.12s ease;
    display: inline-block;
}}
.desktop-menubar .menu-item:hover .menu-title {{
    background-color: rgba(255, 255, 255, 0.08);
    color: #f8fafc;
}}
.desktop-menubar .menu-dropdown {{
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
    min-width: 220px;
    z-index: 999999;
    padding: 4px 0;
}}
.desktop-menubar .menu-item:hover .menu-dropdown {{
    display: block;
}}
.desktop-menubar .menu-dropdown a {{
    display: block;
    padding: 6px 14px;
    color: #cbd5e1 !important;
    text-decoration: none !important;
    font-size: 0.78rem;
    white-space: nowrap;
    transition: background 0.12s ease;
}}
.desktop-menubar .menu-dropdown a:hover {{
    background-color: #0284c7 !important;
    color: #ffffff !important;
}}
</style>
<nav class="desktop-menubar">
<div class="menu-item">
<span class="menu-title">Arxiu</span>
<div class="menu-dropdown">
<a href="?action=home{auth_suffix}" target="_self">🏠 Pantalla d'inici</a>
<a href="?action=reset{auth_suffix}" target="_self">🔄 Reiniciar aplicació / memòria cau</a>
<a href="?action=logout" target="_self">🔒 Tancar sessió</a>
</div>
</div>
<div class="menu-item">
<span class="menu-title">Finances</span>
<div class="menu-dropdown">
<a href="?mod=modules.dashboard{auth_suffix}" target="_self">📊 Resum General (Dashboard)</a>
{f'<a href="?mod=modules.economic{auth_suffix}" target="_self">📈 Mòdul Econòmic complet</a>' if icones_actives.get('economic', True) else ''}
{f'<a href="?mod=modules.compres{auth_suffix}" target="_self">🛒 Compres i tiquets súper</a>' if icones_actives.get('compres', True) else ''}
</div>
</div>
<div class="menu-item">
<span class="menu-title">Llar</span>
<div class="menu-dropdown">
{f'<a href="?mod=modules.menjar{auth_suffix}" target="_self">🍽️ Menús i cuina</a>' if icones_actives.get('menjar', True) else ''}
{f'<a href="?mod=modules.manteniment{auth_suffix}" target="_self">🛠️ Manteniment de la llar</a>' if icones_actives.get('manteniment', True) else ''}
{f'<a href="?mod=modules.cotxe{auth_suffix}" target="_self">🚗 Cotxe i manteniment</a>' if icones_actives.get('cotxe', True) else ''}
{f'<a href="?mod=modules.domotica{auth_suffix}" target="_self">📶 Domòtica (Home Assistant)</a>' if icones_actives.get('domotica', True) else ''}
{f'<a href="?mod=modules.seguretat{auth_suffix}" target="_self">📹 Seguretat i Càmeres</a>' if icones_actives.get('seguretat', True) else ''}
</div>
</div>
<div class="menu-item">
<span class="menu-title">Família</span>
<div class="menu-dropdown">
{f'<a href="?mod=modules.calendari{auth_suffix}" target="_self">📅 Agenda i esdeveniments</a>' if icones_actives.get('agenda', True) else ''}
{f'<a href="?mod=modules.medicacio{auth_suffix}" target="_self">💊 Control de medicació</a>' if icones_actives.get('medicacio', True) else ''}
{f'<a href="?mod=modules.jocs{auth_suffix}" target="_self">🎲 Jocs i oci</a>' if icones_actives.get('jocs', True) else ''}
</div>
</div>
<div class="menu-item">
<span class="menu-title">Bases de dades</span>
<div class="menu-dropdown">
<a href="?mod=modules.economic{auth_suffix}" target="_self">🗄️ Taules de Dades (Despeses / Ingressos)</a>
<a href="?action=sync_db{auth_suffix}" target="_self">🔄 Sincronitzar / Recarregar dades</a>
<a href="?action=backup_db{auth_suffix}" target="_self">💾 Crear Còpia de seguretat (ZIP)</a>
<a href="?mod=modules.compres{auth_suffix}" target="_self">🛒 Base de dades d'articles i súper</a>
</div>
</div>
<div class="menu-item">
<span class="menu-title">Ajustos</span>
<div class="menu-dropdown">
<a href="?mod=modules.admin{auth_suffix}" target="_self">⚙️ Configuració general</a>
<a href="?mod=modules.admin&tab=admin{auth_suffix}" target="_self">👤 Perfil Administrador</a>
<a href="?mod=modules.admin&tab=titol{auth_suffix}" target="_self">🏷️ Títol de la casa</a>
<a href="?mod=modules.admin&tab=familia{auth_suffix}" target="_self">👨‍👩‍👧‍👦 Membres de la família</a>
<a href="?mod=modules.admin&tab=tema{auth_suffix}" target="_self">🎨 Aspecte i tema</a>
<a href="?mod=modules.admin&tab=icones{auth_suffix}" target="_self">🔘 Icones actives d'inici</a>
<a href="?mod=modules.admin&tab=idioma{auth_suffix}" target="_self">🌐 Idioma i traducció</a>
</div>
</div>
</nav>"""
    st.markdown(menubar_html, unsafe_allow_html=True)

if st.session_state.current_module is None:
    # ------------------ PANTALLA PRINCIPAL (LOGO INTERACTIU) ------------------
    # Carregar el fons de pantalla completa
    fons_path = os.path.join(os.path.dirname(__file__), "imatges", "fons xiquiHouse.jpg")
    b64_fons = ""
    if os.path.exists(fons_path):
        with open(fons_path, "rb") as f_img:
            b64_fons = base64.b64encode(f_img.read()).decode()

    # Carregar el logotip transparent (1024x682)
    logo_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.jpg")
    b64_logo = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            b64_logo = base64.b64encode(img_file.read()).decode()

    auth_token = st.query_params.get("auth", "")
    auth_suffix = f"&auth={auth_token}" if auth_token else ""

    role = st.session_state.get("role", "admin")
    role_icon = "👑" if role == "admin" else ("👁️‍🗨️" if role == "viewer" else "👤")
    role_title = "Administrador" if role == "admin" else ("Visor" if role == "viewer" else "Convidat")

    # Dades del títol i colors de la casa
    from core.config_manager import get_translation
    casa_cfg = app_cfg.get("casa", {})
    p1 = str(casa_cfg.get("paraula1", "")).strip()
    c1 = casa_cfg.get("color1", "#407faf")
    p2 = str(casa_cfg.get("paraula2", "")).strip()
    c2 = casa_cfg.get("color2", "#73ad69")
    tamany_px = int(casa_cfg.get("tamany_lletra", 58))
    
    if p1 and p2:
        title_html = f'<span style="color: {c1};">{p1}</span><span style="color: {c2};">{p2}</span>'
    elif p1:
        title_html = f'<span style="color: {c1};">{p1}</span>'
    elif p2:
        title_html = f'<span style="color: {c2};">{p2}</span>'
    else:
        title_html = f'<span style="color: {c1};">Xiqui</span><span style="color: {c2};">House</span>'
    
    lang = app_cfg.get("idioma", "ca")
    slogan_text = get_translation("slogan", lang)
    
    icones_actives = app_cfg.get("icones_actives", {})

    def render_hotspot(mod_key, style_str, title_str, always_active=False):
        is_active = always_active or icones_actives.get(mod_key, True)
        if is_active:
            return f'<a href="?mod=modules.{mod_key}{auth_suffix}" target="_self" class="hotspot" style="{style_str}" title="{title_str}"></a>'
        return f'<div class="hotspot-disabled" style="{style_str}" title="{title_str} (Desactivat)"></div>'

    html_content = textwrap.dedent(f"""<style>
:root {{
    --title-size: {tamany_px}px;
}}
.stApp {{
    background-image: url("data:image/jpeg;base64,{b64_fons}") !important;
    background-size: cover !important;
    background-position: center center !important;
    background-repeat: no-repeat !important;
    background-attachment: fixed !important;
    background-color: #9fb5c2 !important;
}}
.block-container {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin: 0 auto !important;
    max-width: 100% !important;
}}
.role-badge {{
    position: fixed;
    top: 14px;
    right: 20px;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0;
    z-index: 99999;
    user-select: none;
    font-size: 1.75rem;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35));
    cursor: default;
}}
.main-wrapper {{
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    min-height: 98vh;
    padding: 0;
    margin: 0 auto;
}}
.logo-box {{
    position: relative;
    display: block;
    width: min(98vw, 146vh);
    aspect-ratio: 1024 / 682;
    margin: 0 auto;
    line-height: 0;
}}
.img-logo {{
    width: 100%;
    height: 100%;
    display: block;
    pointer-events: none;
    user-select: none;
    object-fit: contain;
    filter: drop-shadow(0 15px 30px rgba(0,0,0,0.15));
}}
.house-custom-title {{
    position: absolute;
    top: 70.8%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: calc({tamany_px} * min(98vw, 146vh) / 1024);
    font-weight: 800;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    text-align: center;
    white-space: nowrap;
    z-index: 50;
    pointer-events: none;
    user-select: none;
    letter-spacing: 0.5px;
    line-height: 1;
    display: inline-flex;
    justify-content: center;
    align-items: center;
}}
.house-custom-slogan {{
    position: absolute;
    top: 79.2%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: calc({max(12, int(tamany_px * 0.36))} * min(98vw, 146vh) / 1024);
    font-weight: 800;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #407faf;
    letter-spacing: 2px;
    text-transform: uppercase;
    text-align: center;
    white-space: nowrap;
    z-index: 50;
    pointer-events: none;
    user-select: none;
    line-height: 1;
}}
.hotspot {{
    position: absolute;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    cursor: pointer !important;
    z-index: 100;
    transition: all 0.15s ease-in-out;
    background: rgba(0, 0, 0, 0.001) !important;
    border: 2px solid transparent !important;
    box-shadow: none !important;
    outline: none !important;
    text-decoration: none !important;
    display: block !important;
    -webkit-tap-highlight-color: transparent;
}}
.hotspot:hover, .hotspot:active {{
    background: rgba(2, 136, 209, 0.25) !important;
    border: 2px solid rgba(2, 136, 209, 0.6) !important;
    box-shadow: 0 0 16px rgba(2, 136, 209, 0.55) !important;
}}
.hotspot-disabled {{
    position: absolute;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    opacity: 0.25;
    filter: grayscale(100%);
    pointer-events: none;
    z-index: 99;
}}

@media (max-width: 768px) {{
    .stApp {{
        overflow-x: hidden !important;
    }}
    .main-wrapper {{
        min-height: 96vh !important;
        padding: 0 !important;
    }}
    .logo-box {{
        width: 100vw !important;
        max-width: 100vw !important;
    }}
    .house-custom-title {{
        font-size: calc({tamany_px} * 0.7px);
    }}
    .house-custom-slogan {{
        font-size: calc({max(12, int(tamany_px * 0.36))} * 0.7px);
    }}
}}
</style>

<!-- Indicador de Rol Usuari -->
<div class="role-badge" title="{role_title}">
    <span>{role_icon}</span>
</div>

<div class="main-wrapper">
<div class="logo-box">
<img src="data:image/png;base64,{b64_logo}" class="img-logo" alt="XiquiHouse">

<!-- Títol personalitzat de la casa en dues caselles, colors i tamany -->
<div class="house-custom-title">
    {title_html}
</div>

<!-- Eslògan traduït de la llar -->
<div class="house-custom-slogan">
    {slogan_text}
</div>

<!-- ================= SENSE RODONA (SUPERIOR) ================= -->
{render_hotspot('admin', 'left: 37.33%; top: 18.43%; width: 7.2%;', '⚙️ Configuració Global')}
{render_hotspot('dashboard', 'left: 61.18%; top: 18.26%; width: 7.2%;', '📊 Dashboard General', always_active=True)}

<!-- ================= AMB RODONA PART ESQUERRA (5 NODES) ================= -->
{render_hotspot('economic', 'left: 27.54%; top: 25.95%; width: 8.2%;', '📈 Mòdul Econòmic')}
{render_hotspot('seguretat', 'left: 17.24%; top: 34.38%; width: 8.2%;', '📹 Seguretat i Càmeres')}
{render_hotspot('manteniment', 'left: 27.54%; top: 41.42%; width: 8.2%;', '🛠️ Manteniment de la Llar')}
{render_hotspot('domotica', 'left: 17.09%; top: 51.25%; width: 8.2%;', '📶 Domòtica (Home Assistant)')}
{render_hotspot('jocs', 'left: 27.54%; top: 57.62%; width: 8.2%;', '🎲 Jocs i Oci Familiar')}

<!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
{render_hotspot('calendari', 'left: 72.17%; top: 25.95%; width: 8.2%;', '📅 Agenda i Calendari')}
{render_hotspot('medicacio', 'left: 81.05%; top: 34.16%; width: 8.2%;', '💊 Control de Medicació')}
{render_hotspot('menjar', 'left: 71.88%; top: 41.57%; width: 8.2%;', '🍽️ Menjar, Menús i Rebost')}
{render_hotspot('cotxe', 'left: 80.91%; top: 51.25%; width: 8.2%;', '🚗 Cotxe i Transport')}
{render_hotspot('compres', 'left: 71.88%; top: 58.36%; width: 8.2%;', '🛒 Compres al Súper i Stock')}

</div>
</div>""")

    st.markdown(html_content, unsafe_allow_html=True)
    
    # Pre-escalfar la memòria cau de dades en segon pla per a una càrrega instantània
    if "prewarmed" not in st.session_state:
        import threading
        from core.db import load_dashboard_data, get_csv_mtimes
        def _prewarm():
            try:
                load_dashboard_data(get_csv_mtimes())
            except Exception:
                pass
        threading.Thread(target=_prewarm, daemon=True).start()
        st.session_state["prewarmed"] = True

else:
    render_traditional_menubar()
    try:
        mod = importlib.import_module(st.session_state.current_module)
        mod.render()
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())
