# Dashboard XiquiHouse - Punt d'Entrada Canònic (Consolidat)
import streamlit as st
import importlib
import base64
import os
import textwrap
import json
from datetime import datetime
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
    header[data-testid="stHeader"] {visibility: hidden; height: 0px !important;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem !important; margin-top: 0rem !important;}
    
    /* Top back button smaller */
    .back-button .stButton > button {
        height: 40px;
        font-size: 16px;
    }

    /* Hide + and - stepper buttons on all quantity and number inputs */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"],
    div[data-testid="stNumberInputContainer"] button {
        display: none !important;
    }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    input[type=number] {
        -moz-appearance: textfield;
    }
    
    /* Ocultar enllaços "anchor" autogenerats per Streamlit als títols (Totes les versions) */
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
    h1 svg, h2 svg, h3 svg, h4 svg, h5 svg, h6 svg,
    a.header-anchor, a[data-testid="stHeaderAnchor"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
        opacity: 0 !important;
    }
    
    /* Peça clau: tapar completament l'espai i el contingut de l'enllaç */
    .stMarkdown h1 a *, .stMarkdown h2 a *, .stMarkdown h3 a *, .stMarkdown h4 a * {
        display: none !important;
    }
    </style>
''', unsafe_allow_html=True)

import streamlit.components.v1 as components
components.html('''
<script>
function attachSelectAllToNumberInputs() {
    try {
        const doc = window.parent.document;
        if (!doc) return;
        const inputs = doc.querySelectorAll('input[type="number"], div[data-testid="stNumberInputContainer"] input');
        inputs.forEach(input => {
            if (!input.dataset.hasSelectAll) {
                input.dataset.hasSelectAll = "true";
                input.addEventListener('focus', function() {
                    setTimeout(() => { this.select(); }, 20);
                });
                input.addEventListener('mouseup', function(e) {
                    if (doc.activeElement === this && this.selectionStart === this.selectionEnd) {
                        this.select();
                    }
                });
            }
        });
    } catch(e) {}
}
attachSelectAllToNumberInputs();
try {
    const observer = new MutationObserver(attachSelectAllToNumberInputs);
    observer.observe(window.parent.document.body, { childList: true, subtree: true });
} catch(e) {}
</script>
''', height=0, width=0)

if not check_password():
    st.stop()

# Si StartDashboard.py ha engegat el mode d'emergència, fixem l'estat offline d'entrada
if "is_offline" not in st.session_state:
    st.session_state["is_offline"] = (os.environ.get("STREAMLIT_OFFLINE_MODE") == "1")

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

# Comprovar si s'ha sol·licitat una acció des del menú superior (Home, Reset, Logout, DB Actions, Edit JSON)
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
    elif act == "edit_json":
        json_f = st.query_params.get("file", "")
        if json_f:
            st.session_state["editing_json_file"] = json_f
    elif act == "edit_rules":
        st.session_state["editing_ocr_rules"] = True
    elif act == "clean_orphans":
        st.session_state["cleaning_ocr_orphans"] = True
    elif act == "sync_db":
        st.cache_data.clear()
        st.session_state["db_synced_toast"] = True
    elif act == "toggle_offline":
        if "is_offline" not in st.session_state:
            st.session_state["is_offline"] = True
        else:
            st.session_state["is_offline"] = not st.session_state["is_offline"]
        st.session_state["offline_toast"] = True
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
        if "file" in st.query_params:
            del st.query_params["file"]
    except Exception:
        pass
    st.rerun()

if st.session_state.get("db_synced_toast"):
    st.toast("🔄 Memòria cau alliberada i dades sincronitzades!", icon="⚡")
    del st.session_state["db_synced_toast"]

if st.session_state.get("offline_toast"):
    if st.session_state.get("is_offline"):
        st.toast("⚠️ MODE OFFLINE ACTIVAT. Els canvis es guarden en local.", icon="⚠️")
    else:
        st.toast("🌐 MODE ONLINE RECUPERAT. Es tornarà a utilitzar el núvol.", icon="🌐")
    del st.session_state["offline_toast"]

# Mostra una franja permanent de mode offline si està activat
if st.session_state.get("is_offline"):
    st.markdown('''
    <div style="background-color: #ef4444; color: white; text-align: center; padding: 10px; font-weight: bold; border-radius: 5px; margin-bottom: 15px; border: 2px solid #b91c1c; animation: pulse 2s infinite;">
        ⚠️ ATENCIÓ: Estàs treballant en MODE OFFLINE. Totes les dades s'estan desant localment i s'encuaran per sincronitzar-les quan torni Internet.
    </div>
    ''', unsafe_allow_html=True)

if st.session_state.get("db_backup_toast"):
    st.toast(f"💾 Còpia de seguretat desada a backup_dades/{st.session_state['db_backup_toast']}", icon="✅")
    del st.session_state["db_backup_toast"]

if 'current_module' not in st.session_state:
    st.session_state.current_module = None

def get_project_json_files():
    json_files = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_dirs = {".git", "venv", ".venv", "app_menjar_pyside", "__pycache__", ".pytest_cache", ".idea", ".vscode", "build", "dist"}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
        for f in files:
            if f.endswith(".json"):
                rel_path = os.path.relpath(os.path.join(root, f), base_dir).replace("\\", "/")
                json_files.append(rel_path)
    return sorted(json_files)

@st.dialog("📝 Editor d'Arxius JSON", width="large")
def show_json_editor_dialog(file_rel_path):
    st.markdown(f"**📁 Fitxer:** `{file_rel_path}`")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.abspath(os.path.join(base_dir, file_rel_path))
    
    # Comprovació de seguretat de la ruta
    if not full_path.startswith(base_dir) or not full_path.endswith(".json"):
        st.error("Ruta de fitxer no permesa.")
        if st.button("Tancar"):
            if "editing_json_file" in st.session_state:
                del st.session_state["editing_json_file"]
            st.rerun()
        return

    content_key = f"json_content_{file_rel_path}"
    
    if content_key not in st.session_state:
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    st.session_state[content_key] = json.dumps(raw_data, indent=2, ensure_ascii=False)
            except Exception:
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        st.session_state[content_key] = f.read()
                except Exception:
                    st.session_state[content_key] = "{}"
        else:
            st.session_state[content_key] = "{}"

    current_val = st.text_area(
        "Contingut JSON",
        value=st.session_state[content_key],
        height=480,
        label_visibility="collapsed",
        key=f"ta_{content_key}"
    )

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1:
        if st.button("💾 Desar canvis", use_container_width=True, type="primary"):
            try:
                parsed = json.loads(current_val)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)
                
                # Sincronització especial si és categories_conceptes.json
                if os.path.basename(full_path) == "categories_conceptes.json":
                    try:
                        from core.db import save_categories_conceptes
                        save_categories_conceptes(parsed)
                    except Exception:
                        pass
                
                st.cache_data.clear()
                st.toast("✅ Arxiu JSON desat correctament!", icon="💾")
                if "editing_json_file" in st.session_state:
                    del st.session_state["editing_json_file"]
                if content_key in st.session_state:
                    del st.session_state[content_key]
                st.rerun()
            except json.JSONDecodeError as err:
                st.error(f"❌ Error de sintaxi JSON: {err}")
            except Exception as e:
                st.error(f"❌ Error en desar el fitxer: {e}")

    with c2:
        if st.button("🔄 Format / Validar", use_container_width=True):
            try:
                parsed = json.loads(current_val)
                st.session_state[content_key] = json.dumps(parsed, indent=2, ensure_ascii=False)
                st.toast("✅ JSON vàlid i formatat!", icon="✨")
                st.rerun()
            except json.JSONDecodeError as err:
                st.error(f"❌ Error de sintaxi JSON: {err}")

    with c3:
        if st.button("❌ Tancar", use_container_width=True):
            if "editing_json_file" in st.session_state:
                del st.session_state["editing_json_file"]
            if content_key in st.session_state:
                del st.session_state[content_key]
            st.rerun()

if st.session_state.get("editing_json_file"):
    show_json_editor_dialog(st.session_state["editing_json_file"])

@st.dialog("📝 Editar regles súper (OCR)", width="large")
def show_ocr_rules_editor_dialog():
    st.markdown("**📁 Fitxer:** `core/ocr_rules.md`")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.abspath(os.path.join(base_dir, "core", "ocr_rules.md"))
    
    content_key = "ocr_rules_content"
    
    if content_key not in st.session_state:
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                st.session_state[content_key] = f.read()
        else:
            st.session_state[content_key] = "# Regles Específiques per Supermercat (OCR)\n\n"

    current_val = st.text_area(
        "Contingut de les regles",
        value=st.session_state[content_key],
        height=480,
        label_visibility="collapsed",
        key=f"ta_{content_key}"
    )

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("💾 Desar Regles", type="primary", use_container_width=True):
            try:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(current_val)
                st.toast("✅ Regles desades correctament!", icon="✨")
                st.session_state[content_key] = current_val
                if "editing_ocr_rules" in st.session_state:
                    del st.session_state["editing_ocr_rules"]
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error en desar: {e}")

    with c3:
        if st.button("❌ Cancel·lar", use_container_width=True):
            if "editing_ocr_rules" in st.session_state:
                del st.session_state["editing_ocr_rules"]
            st.rerun()

if st.session_state.get("editing_ocr_rules"):
    show_ocr_rules_editor_dialog()
@st.dialog("🧹 Neteja Orfes (OCR)", width="large")
def show_orphan_cleaner_dialog():
    from core.db import get_supabase_client
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    if not supabase:
        st.error("No hi ha connexió amb Supabase.")
        return
        
    try:
        # Fetch orphans
        res = supabase.table('tb_noms_producte').select('idNom, supermercat, nom_super').is_('idProducte', 'null').execute()
        orphans = res.data
        if not orphans:
            st.success("🎉 No hi ha cap producte orfe a la base de dades! Està tot net.")
            if st.button("Tancar"):
                if "cleaning_ocr_orphans" in st.session_state:
                    del st.session_state["cleaning_ocr_orphans"]
                st.rerun()
            return
            
        st.info(f"S'han trobat **{len(orphans)}** noms de producte orfes (sense idProducte assignat).")
        
        import pandas as pd
        df = pd.DataFrame(orphans)
        df.insert(0, "Seleccionar", False)
        
        edited_df = st.data_editor(
            df,
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False),
                "idNom": "ID",
                "supermercat": "Supermercat",
                "nom_super": "Nom Original (OCR)"
            },
            disabled=["idNom", "supermercat", "nom_super"],
            hide_index=True,
            use_container_width=True
        )
        
        selected_ids = edited_df[edited_df["Seleccionar"] == True]["idNom"].tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Esborrar Seleccionats", type="primary", use_container_width=True):
                if selected_ids:
                    for id_nom in selected_ids:
                        supabase.table('tb_noms_producte').delete().eq('idNom', id_nom).execute()
                    st.toast(f"{len(selected_ids)} orfes esborrats correctament!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Selecciona almenys un element per esborrar.")
                    
        with col2:
            st.markdown("#### O enllaça un element:")
            if len(selected_ids) == 1:
                item_to_link = df[df["idNom"] == selected_ids[0]].iloc[0]
                st.write(f"Enllaçant: **{item_to_link['nom_super']}** ({item_to_link['supermercat']})")
                
                from core.db import get_config_families, get_config_articles, get_tb_productes_cached, save_categories_conceptes, load_categories_conceptes
                fam_options = [""] + get_config_families()
                fam_sel = st.selectbox("Família", fam_options, key="orf_fam")
                if fam_sel:
                    art_options = [""] + get_config_articles(fam_sel)
                    
                    if "orf_force_art" in st.session_state:
                        if st.session_state["orf_force_art"] in art_options:
                            st.session_state["orf_art"] = st.session_state["orf_force_art"]
                        del st.session_state["orf_force_art"]

                    art_col1, art_col2 = st.columns([8, 2])
                    with art_col1:
                        art_sel = st.selectbox("Article", art_options, key="orf_art")
                    with art_col2:
                        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                        if st.button("➕", key="btn_add_orf_art", help="Crear nou article"):
                            st.session_state["show_new_art_orf"] = not st.session_state.get("show_new_art_orf", False)
                            st.rerun()
                            
                    if st.session_state.get("show_new_art_orf", False):
                        st.markdown(f"<div style='background:#1e293b; padding:10px; border-radius:8px; border:1px solid #334155;'>", unsafe_allow_html=True)
                        new_art_name = st.text_input(f"Nom del nou article per **{fam_sel}**:", key="new_orf_art_input")
                        if st.button("Crear i Seleccionar", use_container_width=True):
                            if new_art_name.strip():
                                new_art = new_art_name.strip()
                                try:
                                    supabase.table('tb_productes').insert({'nom_estandard': new_art, 'familia': fam_sel}).execute()
                                    get_tb_productes_cached.clear()
                                    cfg = load_categories_conceptes()
                                    if "articles_compres" not in cfg:
                                        cfg["articles_compres"] = {}
                                    if fam_sel not in cfg["articles_compres"]:
                                        cfg["articles_compres"][fam_sel] = []
                                    if new_art not in cfg["articles_compres"][fam_sel]:
                                        cfg["articles_compres"][fam_sel].append(new_art)
                                        cfg["articles_compres"][fam_sel].sort()
                                        save_categories_conceptes(cfg)
                                    st.toast(f"Article '{new_art}' creat!", icon="✅")
                                    st.session_state["show_new_art_orf"] = False
                                    st.session_state["orf_force_art"] = new_art
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error creant article: {e}")
                        st.markdown("</div>", unsafe_allow_html=True)
                            
                    if art_sel and st.button("🔗 Enllaçar", use_container_width=True):
                        # Trobar idProducte
                        res_prod = supabase.table('tb_productes').select('idProducte').eq('nom_estandard', art_sel).execute()
                        if res_prod.data:
                            id_prod = res_prod.data[0]['idProducte']
                            supabase.table('tb_noms_producte').update({'idProducte': id_prod}).eq('idNom', selected_ids[0]).execute()
                            st.toast(f"Element enllaçat a {art_sel}!", icon="✅")
                            if "orf_art" in st.session_state:
                                del st.session_state["orf_art"]
                            st.rerun()
                        else:
                            st.error("No s'ha trobat l'ID de l'article a tb_productes.")
            elif len(selected_ids) > 1:
                st.info("Només pots enllaçar 1 element a la vegada.")
            else:
                st.info("Selecciona 1 element per enllaçar-lo a un producte existent.")
        
        st.markdown("<hr/>", unsafe_allow_html=True)
        if st.button("❌ Tancar Menu", use_container_width=True):
            if "cleaning_ocr_orphans" in st.session_state:
                del st.session_state["cleaning_ocr_orphans"]
            st.rerun()
                
    except Exception as e:
        st.error(f"Error llegint dades: {e}")

if st.session_state.get("cleaning_ocr_orphans"):
    show_orphan_cleaner_dialog()

def render_traditional_menubar():
    auth_token = st.query_params.get("auth", "") or st.session_state.get("auth_token", "")
    auth_suffix = f"&auth={auth_token}" if auth_token else ""
    icones_actives = app_cfg.get("icones_actives", {})
    
    json_files = get_project_json_files()
    json_items_html = ""
    for jf in json_files:
        json_items_html += f'<a href="?action=edit_json&file={jf}{auth_suffix}" target="_self">📄 {jf}</a>\n'
    if not json_items_html:
        json_items_html = '<span style="display:block; padding: 6px 14px; color: #64748b; font-size: 0.78rem;">Cap arxiu trobat</span>'
    
    menubar_html = f"""<style>
div.block-container {{
    padding-top: 0.2rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}}
[data-testid="stVerticalBlock"] {{
    gap: 0.4rem !important;
}}
[data-testid="stHeader"] {{
    display: none !important;
}}
.desktop-menubar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    background: transparent;
    padding: 0px;
    margin: -0.6rem 0 0.2rem 0;
    gap: 18px;
    user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 0.82rem;
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
/* Pont invisible per evitar que el menú es tanqui al moure el ratolí avall */
.desktop-menubar .menu-dropdown::before {{
    content: "";
    position: absolute;
    top: -15px;
    left: 0;
    right: 0;
    height: 15px;
    background: transparent;
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
.desktop-menubar .menu-dropdown .submenu-item {{
    position: relative;
}}
.desktop-menubar .menu-dropdown .submenu-title {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 14px;
    color: #cbd5e1;
    font-size: 0.78rem;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.12s ease;
}}
.desktop-menubar .menu-dropdown .submenu-item:hover > .submenu-title {{
    background-color: #0284c7;
    color: #ffffff;
}}
.desktop-menubar .menu-dropdown .submenu-dropdown {{
    display: none;
    position: absolute;
    top: 0;
    left: 100%;
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
    min-width: 240px;
    z-index: 1000000;
    padding: 4px 0;
}}
/* Pont invisible per al submenú al moure el ratolí cap a la dreta */
.desktop-menubar .menu-dropdown .submenu-dropdown::before {{
    content: "";
    position: absolute;
    top: 0;
    left: -15px;
    width: 15px;
    bottom: 0;
    background: transparent;
}}
.desktop-menubar .menu-dropdown .submenu-item:hover .submenu-dropdown {{
    display: block;
}}
.desktop-menubar .submenu-dropdown a {{
    display: block;
    padding: 6px 14px;
    color: #cbd5e1 !important;
    text-decoration: none !important;
    font-size: 0.78rem;
    white-space: nowrap;
    transition: background 0.12s ease;
}}
.desktop-menubar .submenu-dropdown a:hover {{
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
<span class="menu-title">Editar</span>
<div class="menu-dropdown">
<div class="submenu-item">
<div class="submenu-title"><span>📂 Arxius JSON</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></div>
<div class="submenu-dropdown">
{json_items_html}
</div>
</div>
<a href="?action=edit_rules{auth_suffix}" target="_self">📝 Editar regles súper (OCR)</a>
<a href="?action=clean_orphans{auth_suffix}" target="_self">🧹 Neteja Orfes (OCR)</a>
</div>
</div>
<div class="menu-item">
<span class="menu-title">Finances</span>
<div class="menu-dropdown">
<a href="?mod=modules.dashboard{auth_suffix}" target="_self">📊 Resum General (Dashboard)</a>
{f'<a href="?mod=modules.economic{auth_suffix}" target="_self">📈 Mòdul Econòmic complet</a>' if icones_actives.get('economic', True) else ''}
{f'<a href="?mod=modules.compres{auth_suffix}" target="_self">🛒 Ingressos i Despeses</a>' if icones_actives.get('compres', True) else ''}
<a href="?mod=modules.ofertes{auth_suffix}" target="_self">🔍 Consulta d\'Ofertes i Preus</a>
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
<div class="submenu-item">
<div class="submenu-title"><span>🗄️ Gestor de Bases de Dades</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></div>
<div class="submenu-dropdown">
<a href="?mod=modules.bases_dades&db=despeses{auth_suffix}" target="_self">💸 Despeses</a>
<a href="?mod=modules.bases_dades&db=ingressos{auth_suffix}" target="_self">💰 Ingressos</a>
<a href="?mod=modules.bases_dades&db=compresSuper{auth_suffix}" target="_self">🛒 Compres Super</a>
<a href="?mod=modules.bases_dades&db=tb_productes{auth_suffix}" target="_self">📦 Productes (Catàleg)</a>
<a href="?mod=modules.bases_dades{auth_suffix}" target="_self">🔍 Totes les taules...</a>
</div>
</div>
<a href="?action=sync_db{auth_suffix}" target="_self">🔄 Sincronitzar / Recarregar dades</a>
<a href="?mod=modules.sincronitzacio{auth_suffix}" target="_self" style="color: #60a5fa !important;">🌍 Consolidar Dades Offline</a>
<a href="?action=backup_db{auth_suffix}" target="_self">💾 Crear Còpia de seguretat (ZIP)</a>
</div>
</div>
<div class="menu-item">
<span class="menu-title">Ajustos</span>
<div class="menu-dropdown">
<a href="?mod=modules.admin{auth_suffix}" target="_self">⚙️ Configuració general</a>
<a href="?mod=modules.admin&tab=admin{auth_suffix}" target="_self">👤 Perfil Administrador</a>
<a href="?mod=modules.admin&tab=titol{auth_suffix}" target="_self">🏷️ Títol de la casa</a>
<a href="?mod=modules.admin&tab=familia{auth_suffix}" target="_self">👨‍👩‍👧‍👦 Membres de la família</a>
<a href="?mod=modules.admin&tab=tutelats{auth_suffix}" target="_self">🤝 Persones Tutelades</a>
<a href="?mod=modules.admin&tab=bancs{auth_suffix}" target="_self">🏦 Bancs i Comptes</a>
<a href="?mod=modules.admin&tab=tema{auth_suffix}" target="_self">🎨 Aspecte i tema</a>
<a href="?mod=modules.admin&tab=icones{auth_suffix}" target="_self">🔘 Icones actives d'inici</a>
<a href="?mod=modules.admin&tab=idioma{auth_suffix}" target="_self">🌐 Idioma i traducció</a>
<a href="?action=toggle_offline{auth_suffix}" target="_self" style="color: #f87171 !important;">🔌 Commutar Mode Offline</a>
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

    # Carregar el logotip horitzontal
    logo_h_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse ampliat.png")
    if not os.path.exists(logo_h_path):
        logo_h_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.png")
    b64_logo_h = ""
    if os.path.exists(logo_h_path):
        with open(logo_h_path, "rb") as img_file:
            b64_logo_h = base64.b64encode(img_file.read()).decode()

    # Carregar el logotip vertical
    logo_v_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse vertical.png")
    if not os.path.exists(logo_v_path):
        logo_v_path = logo_h_path
    b64_logo_v = ""
    if os.path.exists(logo_v_path):
        with open(logo_v_path, "rb") as img_file:
            b64_logo_v = base64.b64encode(img_file.read()).decode()

    auth_token = st.query_params.get("auth", "") or st.session_state.get("auth_token", "")
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

    def render_hotspot(mod_key, title_str, always_active=False):
        is_active = always_active or icones_actives.get(mod_key, True) or (mod_key == "calendari" and icones_actives.get("agenda", True))
        cls = "hotspot" if is_active else "hotspot-disabled"
        href = f'href="?mod=modules.{mod_key}{auth_suffix}" target="_self"' if is_active else ""
        if is_active:
            return f'<a {href} class="{cls} hs-{mod_key}" title="{title_str}"></a>'
        return f'<div class="{cls} hs-{mod_key}" title="{title_str} (Desactivat)"></div>'

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
[data-testid="stElementToolbar"], [data-testid="stDataFrameToolbar"] {{
    display: none !important;
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

/* -- HORITZONTAL PER DEFECTE -- */
.logo-box {{
    position: relative;
    display: block;
    width: min(98vw, 175vh);
    aspect-ratio: 1772 / 1181;
    margin: 0 auto;
    line-height: 0;
    transform: translateY(-6vh);
}}
.img-logo-h {{
    display: block !important;
    width: 100%; height: 100%; pointer-events: none; user-select: none;
    background-image: url("data:image/png;base64,{b64_logo_h}");
    background-size: contain; background-repeat: no-repeat; background-position: center;
}}
.img-logo-v {{
    display: none !important;
    width: 100%; height: 100%; pointer-events: none; user-select: none;
    background-image: url("data:image/png;base64,{b64_logo_v}");
    background-size: contain; background-repeat: no-repeat; background-position: center;
}}

.house-title-container {{
    position: absolute;
    top: 74.5%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: calc(14 * min(98vw, 175vh) / 1772);
    z-index: 50;
    pointer-events: none;
    user-select: none;
    width: 100%;
}}
.house-custom-title {{
    font-size: calc({tamany_px} * min(98vw, 175vh) / 1024);
    font-weight: 800;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    text-align: center;
    white-space: nowrap;
    letter-spacing: 0.5px;
    line-height: 1;
    display: inline-flex;
    justify-content: center;
    align-items: center;
}}
.house-custom-slogan {{
    font-size: calc({max(11, int(tamany_px * 0.32))} * min(98vw, 175vh) / 1024);
    font-weight: 800;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #407faf;
    letter-spacing: calc(2.2 * min(98vw, 175vh) / 1024);
    text-transform: uppercase;
    text-align: center;
    white-space: nowrap;
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

/* COORDENADES HORITZONTALS (Actualitzades a imatge ampliada) */
.hs-admin {{ left: 35.50%; top: 12.28%; width: 8.2%; }}
.hs-dashboard {{ left: 64.71%; top: 12.07%; width: 8.2%; }}
.hs-economic {{ left: 23.51%; top: 21.49%; width: 8.2%; }}
.hs-seguretat {{ left: 10.90%; top: 31.82%; width: 8.2%; }}
.hs-manteniment {{ left: 23.51%; top: 40.44%; width: 8.2%; }}
.hs-domotica {{ left: 10.72%; top: 52.48%; width: 8.2%; }}
.hs-jocs {{ left: 23.51%; top: 60.28%; width: 8.2%; }}
.hs-calendari {{ left: 78.17%; top: 21.49%; width: 8.2%; }}
.hs-medicacio {{ left: 89.05%; top: 31.54%; width: 8.2%; }}
.hs-menjar {{ left: 77.82%; top: 40.62%; width: 8.2%; }}
.hs-cotxe {{ left: 88.88%; top: 52.47%; width: 8.2%; }}
.hs-compres {{ left: 77.82%; top: 61.18%; width: 8.2%; }}

/* -- VERTICAL (Mòbils / Tablets verticals) -- */
@media (max-width: 900px) and (orientation: portrait), (orientation: portrait) {{
    .img-logo-h {{ display: none !important; }}
    .img-logo-v {{ display: block !important; }}
    
    .stApp {{ overflow-x: hidden !important; }}
    .main-wrapper {{ min-height: 96vh !important; padding: 0 !important; }}
    
    .logo-box {{
        width: 100vw !important;
        max-width: 100vw !important;
        aspect-ratio: 1181 / 1772 !important;
        transform: translateY(0) !important;
    }}
    
    .house-title-container {{
        display: none !important;
    }}
    .house-custom-title {{
        font-size: calc({tamany_px} * 1.6 * 98vw / 1024) !important;
    }}
    .house-custom-slogan {{
        font-size: calc({max(11, int(tamany_px * 0.32))} * 1.6 * 98vw / 1024) !important;
        letter-spacing: 1.5px !important;
    }}

    /* COORDENADES VERTICALS (Actualitzades a imatge ampliada) */
    .hs-admin {{ left: 30.27%; top: 13.69%; width: 12.3%; }}
    .hs-dashboard {{ left: 69.86%; top: 13.40%; width: 12.3%; }}
    .hs-economic {{ left: 10.3%; top: 20.32%; width: 12.3%; }}
    .hs-seguretat {{ left: 10.5%; top: 30.81%; width: 12.3%; }}
    .hs-manteniment {{ left: 10.3%; top: 40.46%; width: 12.3%; }}
    .hs-domotica {{ left: 10.3%; top: 50.56%; width: 12.3%; }}
    .hs-jocs {{ left: 10.3%; top: 60.67%; width: 12.3%; }}
    .hs-calendari {{ left: 89.5%; top: 20.09%; width: 12.3%; }}
    .hs-medicacio {{ left: 88.8%; top: 30.76%; width: 12.3%; }}
    .hs-menjar {{ left: 89.0%; top: 40.74%; width: 12.3%; }}
    .hs-cotxe {{ left: 89.2%; top: 51.02%; width: 12.3%; }}
    .hs-compres {{ left: 88.9%; top: 61.34%; width: 12.3%; }}
}}
</style>

<!-- Indicador de Rol Usuari -->
<div class="role-badge" title="{role_title}">
    <span>{role_icon}</span>
</div>

<div class="main-wrapper">
<div class="logo-box">
<div class="img-logo-h"></div>
<div class="img-logo-v"></div>

<!-- Títol i Eslògan personalitzats de la casa -->
<div class="house-title-container">
    <div class="house-custom-title">
        {title_html}
    </div>
    <div class="house-custom-slogan">
        {slogan_text}
    </div>
</div>

<!-- ================= SENSE RODONA (SUPERIOR) ================= -->
{render_hotspot('admin', '⚙️ Configuració Global')}
{render_hotspot('dashboard', '📊 Dashboard General', always_active=True)}

<!-- ================= AMB RODONA PART ESQUERRA (5 NODES) ================= -->
{render_hotspot('economic', '📈 Mòdul Econòmic')}
{render_hotspot('seguretat', '📹 Seguretat i Càmeres')}
{render_hotspot('manteniment', '🛠️ Manteniment de la Llar')}
{render_hotspot('domotica', '📶 Domòtica (Home Assistant)')}
{render_hotspot('jocs', '🎲 Jocs i Oci Familiar')}

<!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
{render_hotspot('calendari', '📅 Agenda i Calendari')}
{render_hotspot('medicacio', '💊 Control de Medicació')}
{render_hotspot('menjar', '🍽️ Menjar, Menús i Rebost')}
{render_hotspot('cotxe', '🚗 Cotxe i Transport')}
{render_hotspot('compres', '🛒 Ingressos i Despeses')}

</div>
</div>""")

    st.markdown(html_content, unsafe_allow_html=True)


def render_module_view(module_name):
    from core.db import ensure_session_dfs
    ensure_session_dfs()
    
    import sys
    for m in list(sys.modules.keys()):
        if m.startswith('core.'):
            importlib.reload(sys.modules[m])
            
    mod = importlib.import_module(module_name)
    importlib.reload(mod)
    mod.render()


if st.session_state.current_module is None:
    pass
else:
    render_traditional_menubar()
        
    try:
        render_module_view(st.session_state.current_module)
    except Exception as e:
        import traceback
        st.error(f"Error carregant el mòdul: {e}")
        st.code(traceback.format_exc())

