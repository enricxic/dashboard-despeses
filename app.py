# Dashboard XiquiHouse - Punt d'Entrada Canònic (Consolidat) - Versió: 21/10/2026 18:15
import streamlit as st
import importlib
import sys
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

    /* Icona offline neta: treure qualsevol subratllat, vora inferior, linia o sombra */
    .offline-icon-link,
    .offline-icon-link:link,
    .offline-icon-link:visited,
    .offline-icon-link:hover,
    .offline-icon-link:active,
    .offline-icon-link:focus,
    a.offline-icon-link,
    a.offline-icon-link:hover,
    a.offline-icon-link:focus,
    a.offline-icon-link:active,
    div a.offline-icon-link {
        text-decoration: none !important;
        text-decoration-line: none !important;
        text-decoration-color: transparent !important;
        border: none !important;
        border-bottom: none !important;
        border-bottom-width: 0px !important;
        outline: none !important;
        box-shadow: none !important;
        background-image: none !important;
    }
    .offline-icon-link::before,
    .offline-icon-link::after,
    a.offline-icon-link::before,
    a.offline-icon-link::after {
        display: none !important;
        content: none !important;
        border: none !important;
    }
    .offline-icon-link span {
        text-decoration: none !important;
        text-decoration-line: none !important;
        border: none !important;
        border-bottom: none !important;
        outline: none !important;
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

function attachMenuTabInterceptors() {
    try {
        const doc = window.parent.document;
        if (!doc) return;
        const links = doc.querySelectorAll('.submenu-dropdown a');
        links.forEach(link => {
            if (!link.dataset.hasTabInterceptor) {
                link.dataset.hasTabInterceptor = "true";
                link.addEventListener('click', function(e) {
                    const href = link.getAttribute('href') || '';
                    if (!href.includes('tab=')) return;

                    const curHref = window.parent.location.href;
                    let belongsToCurrentMod = false;
                    const mods = ['modules.compres', 'modules.economic', 'modules.cotxe', 'modules.menjar', 'modules.medicacio', 'modules.manteniment', 'modules.llum_aigua'];
                    for (const m of mods) {
                        if (href.includes('mod=' + m) && curHref.includes('mod=' + m)) {
                            belongsToCurrentMod = true;
                            break;
                        }
                    }

                    if (belongsToCurrentMod) {
                        let targetIdx = -1;
                        let targetText = '';

                        if (href.includes('mod=modules.compres')) {
                            if (href.includes('tab=compres_super')) { targetIdx = 0; targetText = 'compres super'; }
                            else if (href.includes('tab=llista_compra')) { targetIdx = 1; targetText = 'llista'; }
                            else if (href.includes('tab=rebost_stock')) { targetIdx = 2; targetText = 'rebost'; }
                            else if (href.includes('tab=estadistiques')) { targetIdx = 3; targetText = 'estadist'; }
                            else if (href.includes('tab=comparador')) { targetIdx = 4; targetText = 'comparador'; }
                            else if (href.includes('tab=fulletons')) { targetIdx = 5; targetText = 'fulletons'; }
                        } else if (href.includes('mod=modules.economic')) {
                            if (href.includes('tab=ingres_despesa')) { targetIdx = 0; targetText = 'ingres'; }
                            else if (href.includes('tab=prev_despeses')) { targetIdx = 1; targetText = 'prev. despeses'; }
                            else if (href.includes('tab=prev_ingressos')) { targetIdx = 2; targetText = 'prev. ingressos'; }
                            else if (href.includes('tab=inversions')) { targetIdx = 3; targetText = 'inversions'; }
                            else if (href.includes('tab=estalvis')) { targetIdx = 4; targetText = 'estalvis'; }
                            else if (href.includes('tab=xat_ia')) { targetIdx = 5; targetText = 'xat'; }
                        } else if (href.includes('mod=modules.cotxe')) {
                            if (href.includes('tab=km_rutes')) { targetIdx = 0; targetText = 'km'; }
                            else if (href.includes('tab=repostatge')) { targetIdx = 1; targetText = 'repostatge'; }
                            else if (href.includes('tab=manteniment')) { targetIdx = 2; targetText = 'manteniment'; }
                            else if (href.includes('tab=consum')) { targetIdx = 3; targetText = 'consum'; }
                        } else if (href.includes('mod=modules.menjar')) {
                            if (href.includes('tab=menu_setmanal') || href.includes('tab=planificador')) { targetIdx = 0; targetText = 'menu'; }
                            else if (href.includes('tab=mise_en_place')) { targetIdx = 1; targetText = 'mise'; }
                            else if (href.includes('tab=recomanador') || href.includes('tab=generador')) { targetIdx = 2; targetText = 'recomanador'; }
                            else if (href.includes('tab=llibre_receptes') || href.includes('tab=llistat_receptes')) { targetIdx = 3; targetText = 'llibre'; }
                            else if (href.includes('tab=afegir_recepta')) { targetIdx = 4; targetText = 'afegir'; }
                            else if (href.includes('tab=bustia_peticions') || href.includes('tab=bustia')) { targetIdx = 5; targetText = 'bustia'; }
                        } else if (href.includes('mod=modules.medicacio')) {
                            if (href.includes('tab=avui_supervisio') || href.includes('tab=avui')) { targetIdx = 0; targetText = 'preses'; }
                            else if (href.includes('tab=crear_pla') || href.includes('tab=nou')) { targetIdx = 1; targetText = 'crear'; }
                            else if (href.includes('tab=plans_historial') || href.includes('tab=plans')) { targetIdx = 2; targetText = 'plans'; }
                        } else if (href.includes('mod=modules.manteniment')) {
                            if (href.includes('tab=registre')) { targetIdx = 0; targetText = 'registre'; }
                            else if (href.includes('tab=manuals')) { targetIdx = 1; targetText = 'manuals'; }
                            else if (href.includes('tab=garanties')) { targetIdx = 2; targetText = 'garanties'; }
                        } else if (href.includes('mod=modules.llum_aigua')) {
                            if (href.includes('tab=llum') || href.includes('tab=electricitat') || href.includes('tab=consum_llum')) { targetIdx = 0; targetText = 'llum'; }
                            else if (href.includes('tab=aigua') || href.includes('tab=consum_aigua')) { targetIdx = 1; targetText = 'aigua'; }
                        }

                        if (targetIdx >= 0) {
                            const tabs = Array.from(doc.querySelectorAll('button[data-baseweb="tab"], div[data-testid="stTabs"] button[role="tab"]'))
                                .filter(b => b.tagName === 'BUTTON');
                            if (tabs && tabs.length > 0) {
                                let targetBtn = null;
                                for (let i = 0; i < tabs.length; i++) {
                                    const txt = (tabs[i].innerText || tabs[i].textContent || '').toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
                                    if (targetText && txt.includes(targetText)) {
                                        targetBtn = tabs[i];
                                        break;
                                    }
                                }
                                if (!targetBtn && targetIdx < tabs.length) {
                                    targetBtn = tabs[targetIdx];
                                }
                                if (targetBtn) {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    try {
                                        const curUrl = new URL(window.parent.location.href);
                                        const newUrl = new URL(href, window.parent.location.origin);
                                        const tabVal = newUrl.searchParams.get('tab');
                                        if (tabVal) {
                                            curUrl.searchParams.set('tab', tabVal);
                                        }
                                        window.parent.history.replaceState({}, '', curUrl.toString());
                                    } catch(err) {}
                                    targetBtn.focus();
                                    targetBtn.click();
                                    return;
                                }
                            }
                        }
                    }
                }, true);
            }
        });
    } catch(e) {}
}

function onAppDomMutated() {
    attachSelectAllToNumberInputs();
    attachMenuTabInterceptors();
}

onAppDomMutated();
try {
let debounceTimer = null;
const observer = new MutationObserver(() => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(onAppDomMutated, 300);
});
observer.observe(window.parent.document.body, { childList: true, subtree: true });
} catch(e) {}
</script>
''', height=0, width=0)

if not check_password():
    st.stop()

# Quan s'engega l'app, sempre ho ha de fer primer en mode ONLINE (es manté offline si la URL porta offline=1)
os.environ.pop("STREAMLIT_OFFLINE_MODE", None)
if st.query_params.get("action") in ("set_online", "online"):
    st.session_state["is_offline"] = False
elif "is_offline" not in st.session_state:
    st.session_state["is_offline"] = (st.query_params.get("offline") == "1")
elif st.query_params.get("offline") == "1" and not st.session_state["is_offline"] and st.query_params.get("action") not in ("set_online", "online", "toggle_offline"):
    st.session_state["is_offline"] = True

app_cfg = load_app_config()

from core.alerts import get_global_alerts
st.session_state["global_alerts_list"] = get_global_alerts()
alerts_html = ""
for al in st.session_state["global_alerts_list"]:
    color = "#fecaca" if al['type'] == 'error' else "#fef08a"
    alerts_html += f'<div style="padding: 8px; margin-bottom: 5px; background: {color}; color: #1e293b; border-radius: 4px; font-size: 0.8rem; line-height: 1.2;"><strong>{al["icon"]} {al["title"]}</strong><br>{al["message"]}</div>'
if not alerts_html:
    alerts_html = '<div style="padding: 10px; color: #94a3b8; font-size: 0.9rem; text-align: center;">Sense alertes</div>'

# Comprovar si s'ha seleccionat un mòdul a través de query params (des de l'HTML interactiu o URL del navegador)
if "mod" in st.query_params:
    selected_mod = st.query_params.get("mod")
    if selected_mod:
        # Només actualitzem current_module si la URL ha canviat externament respecte a l'últim mòdul sincronitzat
        if selected_mod != st.session_state.get("_browser_mod"):
            if st.session_state.get("current_module") != selected_mod:
                for k in ["editing_json_file", "editing_routes", "editing_ocr_rules", "cleaning_ocr_orphans", "show_faq_economic", "show_faq_menjar", "show_afegir_any_comptable"]:
                    st.session_state.pop(k, None)
                st.session_state.current_module = selected_mod
            st.session_state["_browser_mod"] = selected_mod
        if "db" in st.query_params:
            st.session_state["db_to_open"] = st.query_params.get("db")

# Comprovar si s'ha sol·licitat una acció des del menú superior (Home, Reset, Logout, DB Actions, Edit JSON)
if "action" in st.query_params:
    act = st.query_params.get("action")
    if act == "home":
        st.session_state.current_module = None
        st.session_state["_browser_mod"] = None
        if "mod" in st.query_params:
            try:
                del st.query_params["mod"]
            except Exception:
                pass
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
    elif act == "edit_routes":
        st.session_state["editing_routes"] = True
    elif act == "show_faq_economic":
        st.session_state["show_faq_economic"] = True
    elif act == "afegir_any_comptable":
        st.session_state["show_afegir_any_comptable"] = True
    elif act == "generar_any_manteniment":
        st.session_state["show_generar_any_manteniment"] = True
    elif act == "show_faq_menjar":
        st.session_state["show_faq_menjar"] = True
    elif act == "edit_rules":
        st.session_state["editing_ocr_rules"] = True
    elif act == "clean_orphans":
        st.session_state["cleaning_ocr_orphans"] = True
    elif act == "sync_db":
        st.cache_data.clear()
        st.session_state["db_synced_toast"] = True
    elif act in ("set_online", "online"):
        st.session_state["is_offline"] = False
        st.session_state.pop("offline_banner_shown_at", None)
        if "offline" in st.query_params:
            del st.query_params["offline"]
        st.session_state["offline_toast"] = True
    elif act in ("set_offline", "offline"):
        import time
        st.session_state["is_offline"] = True
        st.session_state["offline_banner_shown_at"] = time.time()
        st.query_params["offline"] = "1"
        st.session_state["offline_toast"] = True
    elif act == "toggle_offline":
        import time
        was_offline = st.session_state.get("is_offline", False) or (st.query_params.get("offline") == "1")
        if was_offline:
            st.session_state["is_offline"] = False
            st.session_state.pop("offline_banner_shown_at", None)
            if "offline" in st.query_params:
                del st.query_params["offline"]
        else:
            st.session_state["is_offline"] = True
            st.session_state["offline_banner_shown_at"] = time.time()
            st.query_params["offline"] = "1"
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
    elif act == "notifications":
        st.session_state["show_notifications"] = True
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
        st.toast("⚠️ MODE OFFLINE ACTIVAT. Fes clic a l'endoll 🔌 o al menú Arxiu per tornar a Online.", icon="🔌")
    else:
        st.toast("🌐 MODE ONLINE RECUPERAT. Es torna a connectar al núvol.", icon="🌐")
    del st.session_state["offline_toast"]

if st.session_state.get("show_notifications"):
    del st.session_state["show_notifications"]
    @st.dialog("🔔 Notificacions i Alertes")
    def notifications_dialog():
        from core.alerts import get_global_alerts
        alerts = get_global_alerts()
        if not alerts:
            st.info("No tens cap notificació o alerta activa.")
        else:
            for al in alerts:
                if al['type'] == 'error':
                    st.error(f"**{al['icon']} {al['title']}**: {al['message']}")
                else:
                    st.warning(f"**{al['icon']} {al['title']}**: {al['message']}")
    notifications_dialog()

# Mostra una franja temporal de mode offline durant uns 12 segons abans de retirar-se a la icona superior
if st.session_state.get("is_offline"):
    import time
    banner_start = st.session_state.get("offline_banner_shown_at")
    if banner_start is None:
        st.session_state["offline_banner_shown_at"] = time.time()
        banner_start = st.session_state["offline_banner_shown_at"]
    
    if time.time() - banner_start <= 14:
        st.markdown('''
        <style>
        @keyframes fadeOutOfflineBanner {
            0% { opacity: 1; max-height: 80px; margin-bottom: 15px; }
            75% { opacity: 1; max-height: 80px; margin-bottom: 15px; }
            100% { opacity: 0; max-height: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; overflow: hidden; display: none; }
        }
        .offline-banner-temp {
            background-color: #ef4444;
            color: white;
            text-align: center;
            padding: 10px;
            font-weight: bold;
            border-radius: 5px;
            margin-bottom: 15px;
            border: 2px solid #b91c1c;
            animation: fadeOutOfflineBanner 14s forwards;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
        }
        </style>
        <div class="offline-banner-temp">
            ⚠️ ATENCIÓ: Estàs treballant en MODE OFFLINE. Totes les dades s'estan desant localment i s'encuaran per sincronitzar-les quan torni Internet.
        </div>
        ''', unsafe_allow_html=True)

if st.session_state.get("db_backup_toast"):
    st.toast(f"💾 Còpia de seguretat desada a backup_dades/{st.session_state['db_backup_toast']}", icon="✅")
    del st.session_state["db_backup_toast"]

if 'current_module' not in st.session_state:
    st.session_state.current_module = st.query_params.get("mod", None)

# Sincronitzar query param 'mod' amb l'estat del mòdul actiu
if st.session_state.get("current_module"):
    if st.query_params.get("mod") != st.session_state.current_module:
        st.query_params["mod"] = st.session_state.current_module
    st.session_state["_browser_mod"] = st.session_state.current_module
else:
    st.session_state["_browser_mod"] = None
    if "mod" in st.query_params:
        try:
            del st.query_params["mod"]
        except Exception:
            pass

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

@st.dialog("📝 Manteniment de Rutes (Cotxe)", width="large")
def show_routes_editor_dialog():
    import pandas as pd
    from core.db import load_categories_conceptes, save_categories_conceptes
    
    cat_config = load_categories_conceptes() or {}
    rutes = cat_config.get("rutes_cotxe", [])
    
    df = pd.DataFrame({"Ruta": rutes})
    
    st.markdown("Afegeix, edita o esborra les rutes existents:")
    try:
        edited_df = st.data_editor(
            df,
            key="rutes_editor_taula",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
    except Exception as e:
        st.error(f"Error a la taula: {e}")
        edited_df = df
        
    if st.button("💾 Desar canvis", type="primary"):
        noves_rutes = [str(r).strip() for r in edited_df["Ruta"].tolist() if str(r).strip()]
        cat_config["rutes_cotxe"] = sorted(list(set(noves_rutes)))
        save_categories_conceptes(cat_config)
        st.success("Rutes desades correctament!")
        import time; time.sleep(1)
        if "editing_routes" in st.session_state:
            del st.session_state["editing_routes"]
        st.rerun()
        
    if st.button("❌ Tancar", type="secondary"):
        if "editing_routes" in st.session_state:
            del st.session_state["editing_routes"]
        st.rerun()

if st.session_state.get("editing_routes"):
    show_routes_editor_dialog()

if st.session_state.get("show_faq_economic"):
    @st.dialog("❓ Preguntes i Respostes (Mòdul Econòmic)", width="large")
    def show_faq_dialog():
        import os
        faq_path = os.path.join(os.path.dirname(__file__), "docs", "faq_economic.md")
        if os.path.exists(faq_path):
            with open(faq_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Encara no s'ha creat l'arxiu de preguntes freqüents.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Tancar", type="secondary"):
            if "show_faq_economic" in st.session_state:
                del st.session_state["show_faq_economic"]
            st.rerun()
    show_faq_dialog()

if st.session_state.get("show_faq_menjar"):
    @st.dialog("❓ Preguntes i Respostes (Menús i Cuina)", width="large")
    def show_faq_menjar_dialog():
        import os
        faq_path = os.path.join(os.path.dirname(__file__), "docs", "faq_menjar.md")
        if os.path.exists(faq_path):
            with open(faq_path, "r", encoding="utf-8") as f:
                st.markdown(f.read(), unsafe_allow_html=True)
        else:
            st.warning("Encara no s'ha creat l'arxiu de preguntes freqüents.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Tancar", type="secondary"):
            if "show_faq_menjar" in st.session_state:
                del st.session_state["show_faq_menjar"]
            st.rerun()
    show_faq_menjar_dialog()

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
    offline_suffix = "&offline=1" if st.session_state.get("is_offline") else ""
    url_suffix = f"{auth_suffix}{offline_suffix}"
    curr_mod = st.session_state.get("current_module")
    mod_suffix = f"&mod={curr_mod}" if curr_mod else ""
    action_suffix = f"{mod_suffix}{url_suffix}"
    
    icones_actives = app_cfg.get("icones_actives", {})
    
    from core.alerts import get_global_alerts
    current_alerts = get_global_alerts()
    st.session_state["global_alerts_list"] = current_alerts
    current_alerts_html = ""
    for al in current_alerts:
        color = "#fecaca" if al['type'] == 'error' else "#fef08a"
        current_alerts_html += f'<div style="padding: 8px; margin-bottom: 5px; background: {color}; color: #1e293b; border-radius: 4px; font-size: 0.8rem; line-height: 1.2;"><strong>{al["icon"]} {al["title"]}</strong><br>{al["message"]}</div>'
    if not current_alerts_html:
        current_alerts_html = '<div style="padding: 10px; color: #94a3b8; font-size: 0.9rem; text-align: center;">Sense alertes</div>'
    
    json_files = get_project_json_files()
    json_items_html = ""
    for jf in json_files:
        json_items_html += f'<a href="?action=edit_json&file={jf}{action_suffix}" target="_self">📄 {jf}</a>\n'
    if not json_items_html:
        json_items_html = '<span style="display:block; padding: 6px 14px; color: #64748b; font-size: 0.78rem;">Cap arxiu trobat</span>'
    
    offline_badge_html = ""
    if st.session_state.get("is_offline"):
        offline_badge_html = f'''<a href="?action=set_online{auth_suffix}{mod_suffix}" target="_self" class="offline-icon-link" title="Mode Offline activat (Fes clic per tornar a Online)" style="font-size: 1.5rem; display: flex; align-items: center; text-decoration: none !important; text-decoration-line: none !important; text-decoration-color: transparent !important; border: none !important; border-bottom: none !important; border-bottom-width: 0 !important; outline: none !important; box-shadow: none !important; background: transparent !important; background-image: none !important; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35)); cursor: pointer; padding: 0 4px; line-height: 1;">
<span style="text-decoration: none !important; border: none !important; outline: none !important;">🔌</span>
</a>'''
    
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
.desktop-menubar .menu-separator {{
    height: 1px;
    background-color: #334155;
    margin: 4px 0;
}}
</style>
<nav class="desktop-menubar">
<div class="menu-item">
<span class="menu-title">Arxiu</span>
<div class="menu-dropdown">
<a href="?action=home{url_suffix}" target="_self">🏠 Pantalla d'inici</a>
<a href="?action=reset{url_suffix}" target="_self">🔄 Reiniciar aplicació / memòria cau</a>
{f'<a href="?action=set_online{auth_suffix}{mod_suffix}" target="_self" style="color: #4ade80 !important;">🌐 Tornar a Mode Online</a>' if st.session_state.get("is_offline") else f'<a href="?action=set_offline{auth_suffix}{mod_suffix}" target="_self" style="color: #f87171 !important;">🔌 Commutar Mode Offline</a>'}
<a href="?action=logout" target="_self">🔒 Tancar sessió</a>
</div>
</div>
<div class="menu-item">
<span class="menu-title">Editar</span>
<div class="menu-dropdown">
<div class="submenu-item">
<a href="?mod=modules.admin{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>⚙️ Configuració general</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.admin{url_suffix}" target="_self">⚙️ Tauler de Configuració</a>
<a href="?mod=modules.admin&tab=admin{url_suffix}" target="_self">👤 Perfil Administrador</a>
<a href="?mod=modules.admin&tab=titol{url_suffix}" target="_self">🏷️ Títol de la casa</a>
<a href="?mod=modules.admin&tab=familia{url_suffix}" target="_self">👨‍👩‍👧‍👦 Membres de la família</a>
<a href="?mod=modules.admin&tab=tutelats{url_suffix}" target="_self">🤝 Persones Tutelades</a>
<a href="?mod=modules.admin&tab=bancs{url_suffix}" target="_self">🏦 Bancs i Comptes</a>
<a href="?mod=modules.admin&tab=tema{url_suffix}" target="_self">🎨 Aspecte i tema</a>
<a href="?mod=modules.admin&tab=icones{url_suffix}" target="_self">🔘 Icones actives d'inici</a>
<a href="?mod=modules.admin&tab=idioma{url_suffix}" target="_self">🌐 Idioma i traducció</a>
</div>
</div>
<div class="submenu-item">
<div class="submenu-title"><span>📂 Arxius JSON</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></div>
<div class="submenu-dropdown">
{json_items_html}
</div>
</div>
<a href="?action=edit_rules{action_suffix}" target="_self">📝 Editar regles súper (OCR)</a>
<a href="?action=clean_orphans{action_suffix}" target="_self">🧹 Neteja Orfes (OCR)</a>
</div>
</div>
<div class="menu-item">
<span class="menu-title">Mòduls</span>
<div class="menu-dropdown">
<a href="?mod=modules.dashboard{url_suffix}" target="_self">📊 Resum General (Dashboard)</a>
{f'''<div class="submenu-item">
<a href="?mod=modules.economic{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>📈 Mòdul Econòmic</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.economic&tab=ingres_despesa{url_suffix}" target="_self">📝 Ingrés / Despesa General</a>
<a href="?mod=modules.economic&tab=prev_despeses{url_suffix}" target="_self">🔴 Prev. Despeses</a>
<a href="?mod=modules.economic&tab=prev_ingressos{url_suffix}" target="_self">🟢 Prev. Ingressos</a>
<a href="?mod=modules.economic&tab=inversions{url_suffix}" target="_self">📈 Inversions</a>
<a href="?mod=modules.economic&tab=estalvis{url_suffix}" target="_self">💰 Estalvis</a>
<a href="?mod=modules.economic&tab=xat_ia{url_suffix}" target="_self">🤖 Xat IA</a>
<div class="menu-separator"></div>
<a href="?mod=modules.economic&action=afegir_any_comptable{url_suffix}" target="_self">📅 Afegir nou any comptable</a>
<a href="?mod=modules.economic&action=show_faq_economic{url_suffix}" target="_self">❓ Preguntes i Respostes</a>
</div>
</div>''' if icones_actives.get('economic', True) else ''}
{f'''<div class="submenu-item">
<a href="?mod=modules.compres{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>🛒 Compres Super i Stock</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.compres&tab=compres_super{url_suffix}" target="_self">📄 Compres Super</a>
<a href="?mod=modules.compres&tab=llista_compra{url_suffix}" target="_self">📋 Llista de la Compra</a>
<a href="?mod=modules.compres&tab=rebost_stock{url_suffix}" target="_self">📦 Rebost / Stock</a>
<a href="?mod=modules.compres&tab=estadistiques{url_suffix}" target="_self">📊 Estadístiques</a>
<a href="?mod=modules.compres&tab=comparador{url_suffix}" target="_self">🔍 Comparador d'Ofertes</a>
<a href="?mod=modules.compres&tab=fulletons{url_suffix}" target="_self">📰 Fulletons</a>
</div>
</div>''' if icones_actives.get('compres', True) else ''}
<div class="submenu-item">
<a href="?mod=modules.cotxe{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>🚗 Cotxe</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.cotxe&tab=km_rutes{url_suffix}" target="_self">🛣️ Km i Rutes</a>
<a href="?mod=modules.cotxe&tab=repostatge{url_suffix}" target="_self">⛽ Repostatge</a>
<a href="?mod=modules.cotxe&tab=manteniment{url_suffix}" target="_self">🔧 Manteniment (Oli i Rodes)</a>
<a href="?mod=modules.cotxe&tab=consum{url_suffix}" target="_self">📊 Consum</a>
<div class="menu-separator"></div>
<a href="?action=edit_routes{action_suffix}" target="_self">📝 Editar Rutes</a>
</div>
</div>
{f'''<div class="submenu-item">
<a href="?mod=modules.menjar{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>🍽️ Menús i cuina</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.menjar&tab=menu_setmanal{url_suffix}" target="_self">📅 Menú Setmanal (Actiu)</a>
<a href="?mod=modules.menjar&tab=mise_en_place{url_suffix}" target="_self">🔪 Mise en place</a>
<a href="?mod=modules.menjar&tab=recomanador{url_suffix}" target="_self">🧠 Recomanador de Menús</a>
<a href="?mod=modules.menjar&tab=llibre_receptes{url_suffix}" target="_self">📖 Llibre de Receptes</a>
<a href="?mod=modules.menjar&tab=afegir_recepta{url_suffix}" target="_self">➕ Afegir Recepta</a>
<a href="?mod=modules.menjar&tab=bustia_peticions{url_suffix}" target="_self">📥 Bústia Peticions</a>
<div class="menu-separator"></div>
<a href="?mod=modules.menjar&action=show_faq_menjar{url_suffix}" target="_self">❓ Preguntes i Respostes</a>
</div>
</div>''' if icones_actives.get('menjar', True) else ''}
{f'''<div class="submenu-item">
<a href="?mod=modules.manteniment{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>🛠️ Manteniment de la llar</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.manteniment&tab=registre{url_suffix}" target="_self">📋 Registre Manteniment</a>
<a href="?mod=modules.manteniment&tab=manuals{url_suffix}" target="_self">📖 Manuals</a>
<a href="?mod=modules.manteniment&tab=garanties{url_suffix}" target="_self">🛡️ Garanties</a>
<div class="menu-separator"></div>
<a href="?mod=modules.manteniment&action=generar_any_manteniment{url_suffix}" target="_self">📅 Generar tasques proper any</a>
</div>
</div>''' if icones_actives.get('manteniment', True) else ''}
{f'<a href="?mod=modules.domotica{url_suffix}" target="_self">📶 Domòtica (Home Assistant)</a>' if icones_actives.get('domotica', True) else ''}
{f'<a href="?mod=modules.seguretat{url_suffix}" target="_self">📹 Seguretat i Càmeres</a>' if icones_actives.get('seguretat', True) else ''}
{f'<a href="?mod=modules.calendari{url_suffix}" target="_self">📅 Agenda i esdeveniments</a>' if icones_actives.get('agenda', True) else ''}
{f'''<div class="submenu-item">
<a href="?mod=modules.medicacio{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>💊 Control de medicació</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.medicacio&tab=avui_supervisio{url_suffix}" target="_self">🕒 Preses d'Avui & Supervisió</a>
<a href="?mod=modules.medicacio&tab=crear_pla{url_suffix}" target="_self">➕ Crear Pla de Medicació</a>
<a href="?mod=modules.medicacio&tab=plans_historial{url_suffix}" target="_self">📋 Plans Actius i Historial</a>
<a href="?mod=modules.medicacio&tab=google_calendar{url_suffix}" target="_self">⚙️ Connexió Google Calendar API</a>
</div>
</div>''' if icones_actives.get('medicacio', True) else ''}
{f'''<div class="submenu-item">
<a href="?mod=modules.llum_aigua{url_suffix}" target="_self" class="submenu-title" style="text-decoration:none; color:inherit;"><span>💡 Llum i Aigua</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></a>
<div class="submenu-dropdown">
<a href="?mod=modules.llum_aigua&tab=llum{url_suffix}" target="_self">⚡ Consum Llum</a>
<a href="?mod=modules.llum_aigua&tab=aigua{url_suffix}" target="_self">💧 Consum Aigua</a>
</div>
</div>''' if icones_actives.get('llum_aigua', icones_actives.get('jocs', True)) else ''}
</div>
</div>
<div class="menu-item">
<span class="menu-title">Bases de dades</span>
<div class="menu-dropdown">
<div class="submenu-item">
<div class="submenu-title"><span>🗄️ Gestor de Bases de Dades</span> <span style="font-size: 0.68rem; margin-left: 10px;">▶</span></div>
<div class="submenu-dropdown">
<a href="?mod=modules.bases_dades&db=despeses{url_suffix}" target="_self">💸 Despeses</a>
<a href="?mod=modules.bases_dades&db=ingressos{url_suffix}" target="_self">💰 Ingressos</a>
<a href="?mod=modules.bases_dades&db=pagaments{url_suffix}" target="_self">💳 Pagaments</a>
<a href="?mod=modules.bases_dades&db=compresSuper{url_suffix}" target="_self">🛒 Compres Super</a>
<a href="?mod=modules.bases_dades&db=tb_productes{url_suffix}" target="_self">📦 Productes (Catàleg)</a>
<a href="?mod=modules.bases_dades{url_suffix}" target="_self">🔍 Totes les taules...</a>
</div>
</div>
<a href="?action=sync_db{url_suffix}" target="_self">🔄 Sincronitzar / Recarregar dades</a>
<a href="?mod=modules.sincronitzacio{url_suffix}" target="_self" style="color: #60a5fa !important;">🌍 Consolidar Dades Offline</a>
<a href="?action=backup_db{url_suffix}" target="_self">💾 Crear Còpia de seguretat (ZIP)</a>
</div>
</div>


<!-- Capçalera dreta: Indicador Offline, Campana Notificacions i Avatar Rol -->
<div style="margin-left: auto; display: flex; align-items: center; gap: 12px;">
{offline_badge_html}
<div class="menu-item" style="position: relative;">
<span class="menu-title" style="font-size: 1.5rem; display: flex; align-items: center; cursor: pointer; padding: 0 4px;">🔔<span style="background: {'red' if len(current_alerts) > 0 else '#888'}; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: bold; position: absolute; top: -5px; right: -5px;">{len(current_alerts)}</span></span>
<div class="menu-dropdown" style="right: 0; left: auto; min-width: 320px; padding: 10px; white-space: normal; cursor: default;">
{current_alerts_html}
</div>
</div>
<!-- Avatar Administrador -->
<div class="role-badge-menubar" title="Rol actual" style="font-size: 1.5rem; display: flex; align-items: center; cursor: default; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35));">
{ "👑" if st.session_state.get("role") == "admin" else ("👁️‍🗨️" if st.session_state.get("role") == "viewer" else "👤") }
</div>
</div>

</nav>"""
    st.markdown(menubar_html, unsafe_allow_html=True)

if st.session_state.current_module is None:
    # ------------------ PANTALLA PRINCIPAL (LOGO INTERACTIU) ------------------
    # Carregar el fons de pantalla completa
    fons_path = os.path.join(os.path.dirname(__file__), "imatges", "Disseny", "fons xiquiHouse.jpg")
    if not os.path.exists(fons_path):
        fons_path = os.path.join(os.path.dirname(__file__), "imatges", "fons xiquiHouse.jpg")
    b64_fons = ""
    if os.path.exists(fons_path):
        with open(fons_path, "rb") as f_img:
            b64_fons = base64.b64encode(f_img.read()).decode()

    # Carregar el logotip horitzontal
    logo_h_path = os.path.join(os.path.dirname(__file__), "imatges", "Disseny", "logo xiquiHouse ampliat.png")
    if not os.path.exists(logo_h_path):
        logo_h_path = os.path.join(os.path.dirname(__file__), "imatges", "Disseny", "logo xiquiHouse.png")
    if not os.path.exists(logo_h_path):
        logo_h_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse ampliat.png")
    if not os.path.exists(logo_h_path):
        logo_h_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse.png")
    b64_logo_h = ""
    if os.path.exists(logo_h_path):
        with open(logo_h_path, "rb") as img_file:
            b64_logo_h = base64.b64encode(img_file.read()).decode()

    # Carregar el logotip vertical
    logo_v_path = os.path.join(os.path.dirname(__file__), "imatges", "Disseny", "logo xiquiHouse vertical.png")
    if not os.path.exists(logo_v_path):
        logo_v_path = os.path.join(os.path.dirname(__file__), "imatges", "logo xiquiHouse vertical.png")
    if not os.path.exists(logo_v_path):
        logo_v_path = logo_h_path
    b64_logo_v = ""
    if os.path.exists(logo_v_path):
        with open(logo_v_path, "rb") as img_file:
            b64_logo_v = base64.b64encode(img_file.read()).decode()

    auth_token = st.query_params.get("auth", "") or st.session_state.get("auth_token", "")
    auth_suffix = f"&auth={auth_token}" if auth_token else ""
    offline_suffix = "&offline=1" if st.session_state.get("is_offline") else ""
    url_suffix = f"{auth_suffix}{offline_suffix}"

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
        is_active = always_active or icones_actives.get(mod_key, True) or (mod_key == "calendari" and icones_actives.get("agenda", True)) or (mod_key == "llum_aigua" and icones_actives.get("jocs", True))
        cls = "hotspot" if is_active else "hotspot-disabled"
        href = f'href="?mod=modules.{mod_key}{url_suffix}" target="_self"' if is_active else ""
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
    width: min(85vw, 140vh);
    aspect-ratio: 1772 / 1181;
    margin: 0 auto;
    line-height: 0;
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
    gap: calc(14 * min(85vw, 140vh) / 1772);
    z-index: 50;
    pointer-events: none;
    user-select: none;
    width: 100%;
}}
.house-custom-title {{
    font-size: calc({tamany_px} * min(85vw, 140vh) / 1024);
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
    font-size: calc({max(11, int(tamany_px * 0.32))} * min(85vw, 140vh) / 1024);
    font-weight: 800;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #407faf;
    letter-spacing: calc(2.2 * min(85vw, 140vh) / 1024);
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
.hs-economic {{ left: 23.90%; top: 21.10%; width: 8.2%; }}
.hs-seguretat {{ left: 10.90%; top: 31.82%; width: 8.2%; }}
.hs-manteniment {{ left: 23.51%; top: 40.44%; width: 8.2%; }}
.hs-domotica {{ left: 10.72%; top: 52.48%; width: 8.2%; }}
.hs-llum_aigua, .hs-jocs {{ left: 23.51%; top: 60.28%; width: 8.2%; }}
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
    .hs-economic {{ left: 10.70%; top: 20.10%; width: 12.3%; }}
    .hs-seguretat {{ left: 10.5%; top: 30.81%; width: 12.3%; }}
    .hs-manteniment {{ left: 10.3%; top: 40.46%; width: 12.3%; }}
    .hs-domotica {{ left: 10.3%; top: 50.56%; width: 12.3%; }}
    .hs-llum_aigua, .hs-jocs {{ left: 10.3%; top: 60.67%; width: 12.3%; }}
    .hs-calendari {{ left: 89.5%; top: 20.09%; width: 12.3%; }}
    .hs-medicacio {{ left: 88.8%; top: 30.76%; width: 12.3%; }}
    .hs-menjar {{ left: 89.0%; top: 40.74%; width: 12.3%; }}
    .hs-cotxe {{ left: 89.2%; top: 51.02%; width: 12.3%; }}
    .hs-compres {{ left: 88.9%; top: 61.34%; width: 12.3%; }}
}}
.bell-dropdown {{ display: none; position: absolute; top: 40px; right: 0; background: #1e293b; border: 1px solid #334155; border-radius: 8px; min-width: 320px; padding: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); z-index: 100000; cursor: default; white-space: normal; text-align: left; }}
.bell-container:hover .bell-dropdown {{ display: block; }}
</style>

<!-- Capçalera dreta: Indicador Offline, Campana Notificacions i Rol d'Usuari -->
<div style="position: fixed; top: 14px; right: 20px; z-index: 99999; display: flex; align-items: center; gap: 8px;">
{f'''<a href="?action=set_online{auth_suffix}" target="_self" class="offline-icon-link" title="Mode Offline activat (Fes clic per tornar a Online)" style="font-size: 1.75rem; display: flex; align-items: center; text-decoration: none !important; text-decoration-line: none !important; text-decoration-color: transparent !important; border: none !important; border-bottom: none !important; border-bottom-width: 0 !important; outline: none !important; box-shadow: none !important; background: transparent !important; background-image: none !important; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35)); cursor: pointer; padding: 0 4px; line-height: 1;">
    <span style="text-decoration: none !important; border: none !important; outline: none !important;">🔌</span>
</a>''' if st.session_state.get("is_offline") else ''}
<div class="bell-container" style="position: relative; cursor: pointer;">
<span style="font-size: 1.75rem; display: flex; align-items: center; position: relative; padding: 5px 6px; color: inherit; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35));">🔔<span style="background: {'red' if len(st.session_state.get('global_alerts_list', [])) > 0 else '#888'}; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: bold; position: absolute; top: 0px; right: 0px;">{len(st.session_state.get('global_alerts_list', []))}</span></span>
<div class="bell-dropdown">{alerts_html}</div>
</div>
<div class="role-badge" title="{role_title}" style="position: static; font-size: 1.75rem; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.35)); cursor: default; padding: 0 4px;">
    <span>{role_icon}</span>
</div>
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
{render_hotspot('llum_aigua', '💡 Llum i Aigua')}

<!-- ================= AMB RODONA PART DRETA (5 NODES) ================= -->
{render_hotspot('calendari', '📅 Agenda i Calendari')}
{render_hotspot('medicacio', '💊 Control de Medicació')}
{render_hotspot('menjar', '🍽️ Menjar, Menús i Rebost')}
{render_hotspot('cotxe', '🚗 Cotxe i Transport')}
{render_hotspot('compres', '🛒 Compres Super i Stock')}

</div>
</div>""")

    st.markdown(html_content, unsafe_allow_html=True)


_MODULE_MTIMES = {}

def render_module_view(module_name):
    from core.db import ensure_session_dfs
    ensure_session_dfs()
    
    mod = sys.modules.get(module_name)
    if mod is None:
        mod = importlib.import_module(module_name)
        if hasattr(mod, "__file__") and mod.__file__:
            try:
                _MODULE_MTIMES[module_name] = os.path.getmtime(mod.__file__)
            except Exception:
                pass
    else:
        # Si el codi font al disc s'ha actualitzat (p. ex. nou commit de git), recarregar-lo automàticament
        if hasattr(mod, "__file__") and mod.__file__:
            try:
                cur_mtime = os.path.getmtime(mod.__file__)
                if cur_mtime > _MODULE_MTIMES.get(module_name, 0):
                    for k in list(sys.modules.keys()):
                        if k.startswith("core."):
                            try:
                                importlib.reload(sys.modules[k])
                            except Exception:
                                pass
                    mod = importlib.reload(mod)
                    _MODULE_MTIMES[module_name] = cur_mtime
            except Exception:
                pass
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

