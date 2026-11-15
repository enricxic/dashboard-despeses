import streamlit as st
import os
import calendar
import urllib.parse
from datetime import datetime, date, timedelta
import importlib
import core.calendar_manager as cm
try:
    importlib.reload(cm)
except Exception:
    pass
from core.config_manager import load_app_config

def sort_events_by_time(events_list):
    if hasattr(cm, "sort_events_by_time"):
        return cm.sort_events_by_time(events_list)
    def _time_key(e):
        is_timed = bool(not e.get("all_day", False) and e.get("start_time"))
        t_str = e.get("start_time", "") or ""
        if ":" in t_str:
            parts = t_str.split(":")
            try:
                t_str = f"{int(parts[0]):02d}:{parts[1]}"
            except Exception:
                pass
        return (1 if is_timed else 0, t_str)
    return sorted(events_list, key=_time_key)

def get_current_user_name(app_cfg):
    """Determina el nom del membre de la família corresponent a l'usuari actual connectat."""
    familia = app_cfg.get("familia", [])
    membres_noms = [m.get("nom", "Familiar") for m in familia]
    u = (st.session_state.get("username") or "").strip()
    for m in membres_noms:
        if m.lower() == u.lower() or u.lower().startswith(m.lower()):
            return m
    admin_full = app_cfg.get("admin", {}).get("nom", "")
    admin_first = admin_full.split()[0] if admin_full else "Enric"
    if admin_first in membres_noms:
        return admin_first
    return membres_noms[0] if membres_noms else "Enric"

def invalidate_cal_cache():
    for k in list(st.session_state.keys()):
        if k.startswith("cal_events_"):
            del st.session_state[k]

@st.dialog("📅 Gestió d'Esdeveniment", width="large")
def event_modal_dialog(active_user, edit_ev=None, preselected_date=None):
    is_editing = (edit_ev is not None)
    today = date.today()
    
    tab_manual, tab_quick = st.tabs(["📝 Formulari complet", "⚡ Creació ràpida"])
    
    with tab_quick:
        st.markdown("<div style='font-size:0.85rem; color:#94a3b8; margin-bottom:6px;'>Escriu en llenguatge natural (ex: <i>'Demà dinar familiar 14h'</i>, <i>'Divendres sopar 21h'</i>, <i>'Demà 18:30 metge Enric'</i>)</div>", unsafe_allow_html=True)
        c_q1, c_q2 = st.columns([7.5, 2.5])
        with c_q1:
            quick_txt = st.text_input("Descripció de l'esdeveniment", placeholder="Escriu aquí el que vols agendar...", label_visibility="collapsed", key="dialog_quick_txt")
        with c_q2:
            if st.button("⚡ Crear", type="primary", use_container_width=True, key="dialog_btn_quick"):
                if quick_txt.strip():
                    parsed = cm.parse_natural_language_event(quick_txt, default_member=active_user)
                    if parsed:
                        invalidate_cal_cache()
                        cm.add_event(parsed)
                        st.session_state.show_event_modal = False
                        st.session_state.edit_event_data = None
                        st.rerun()
                        
    with tab_manual:
        default_title = edit_ev.get("title", "") if is_editing else ""
        default_member = edit_ev.get("member", active_user) if is_editing else active_user
        default_cat = edit_ev.get("category", "Altres") if is_editing else "Altres"
        
        init_date = today
        if is_editing and edit_ev.get("start_date"):
            try:
                init_date = datetime.strptime(edit_ev.get("start_date"), "%Y-%m-%d").date()
            except Exception:
                pass
        elif preselected_date:
            init_date = preselected_date
            
        default_start_time = "10:00"
        if is_editing and edit_ev.get("start_time"):
            default_start_time = edit_ev.get("start_time")
            
        default_all_day = edit_ev.get("all_day", False) if is_editing else False
        default_loc = edit_ev.get("location", "") if is_editing else ""
        default_desc = edit_ev.get("description", "") if is_editing else ""
        default_rep = edit_ev.get("repeat", "Cap") if is_editing else "Cap"
        
        c_f1, c_f2 = st.columns([6, 4])
        with c_f1:
            f_title = st.text_input("Títol de l'esdeveniment *", value=default_title, key="dia_ev_title", placeholder="Ex: Cita dentista, Dinar familiar, Sopar amb amics...")
        with c_f2:
            all_member_options = [active_user, "Tota la família"]
            idx_m = all_member_options.index(default_member) if default_member in all_member_options else 0
            f_member = st.selectbox("Membre assignat", all_member_options, index=idx_m, key="dia_ev_member")
            
        c_f3, c_f4, c_f5 = st.columns([3.5, 3.5, 3])
        with c_f3:
            cat_keys = list(cm.CATEGORIES.keys())
            cat_idx = cat_keys.index(default_cat) if default_cat in cat_keys else len(cat_keys)-1
            f_cat = st.selectbox("Categoria", cat_keys, index=cat_idx, format_func=lambda k: f"{cm.CATEGORIES[k]['icon']} {cm.CATEGORIES[k]['label']}", key="dia_ev_cat")
        with c_f4:
            f_date = st.date_input("Data de l'esdeveniment", value=init_date, format="DD/MM/YYYY", key="dia_ev_date")
        with c_f5:
            f_allday = st.checkbox("Tot el dia", value=default_all_day, key="dia_ev_allday")
            if not f_allday:
                f_time = st.text_input("Hora (HH:MM)", value=default_start_time, key="dia_ev_time")
            else:
                f_time = ""
                
        c_f6, c_f7 = st.columns([6, 4])
        with c_f6:
            f_loc = st.text_input("📍 Ubicació / Adreça", value=default_loc, placeholder="Ex: Restaurant Can Xic, Hospital de Terrassa...", key="dia_ev_loc")
        with c_f7:
            rep_opts = ["Cap", "Setmanal", "Mensual", "Anual"]
            idx_rep = rep_opts.index(default_rep) if default_rep in rep_opts else 0
            f_rep = st.selectbox("🔁 Repetició", rep_opts, index=idx_rep, key="dia_ev_rep")
            
        f_desc = st.text_area("📝 Notes i detalls", value=default_desc, placeholder="Indicacions, reserves, menú, etc.", key="dia_ev_desc", height=70)
        
        c_act1, c_act2 = st.columns([5, 5])
        with c_act1:
            if st.button("❌ Cancel·lar", use_container_width=True, key="dia_btn_cancel"):
                st.session_state.show_event_modal = False
                st.session_state.edit_event_data = None
                st.rerun()
        with c_act2:
            if st.button("💾 Desar Esdeveniment", type="primary", use_container_width=True, key="dia_btn_save"):
                if not f_title.strip():
                    st.error("El títol és obligatori.")
                else:
                    new_data = {
                        "title": f_title.strip(),
                        "member": f_member,
                        "category": f_cat,
                        "start_date": f_date.strftime("%Y-%m-%d"),
                        "start_time": f_time.strip() if not f_allday else "",
                        "all_day": f_allday,
                        "location": f_loc.strip(),
                        "repeat": f_rep,
                        "description": f_desc.strip()
                    }
                    invalidate_cal_cache()
                    if is_editing and "id" in edit_ev:
                        cm.update_event(edit_ev["id"], new_data, original_event=edit_ev)
                    else:
                        cm.add_event(new_data)
                    st.session_state.show_event_modal = False
                    st.session_state.edit_event_data = None
                    st.rerun()


def render():
    app_cfg = load_app_config()
    is_dark = (app_cfg.get("tema", "Fosc") == "Fosc")
    active_user = get_current_user_name(app_cfg)
    st.session_state.cal_filter_member = active_user
    
    # Colors del tema
    bg_card = "rgba(30, 41, 59, 0.75)" if is_dark else "rgba(255, 255, 255, 0.95)"
    bg_card_sub = "rgba(15, 23, 42, 0.6)" if is_dark else "rgba(241, 245, 249, 0.8)"
    border_color = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.1)"
    text_primary = "#f8fafc" if is_dark else "#0f172a"
    text_secondary = "#94a3b8" if is_dark else "#64748b"
    today = date.today()
    
    # Estat de la navegació de data
    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month
    if "cal_view_mode" not in st.session_state:
        st.session_state.cal_view_mode = "grid" # "grid" o "agenda"
    if "cal_filter_member" not in st.session_state:
        st.session_state.cal_filter_member = "Tots"
    if "cal_filter_cat" not in st.session_state:
        st.session_state.cal_filter_cat = "Totes"
    if "show_event_modal" not in st.session_state:
        st.session_state.show_event_modal = False
    if "edit_event_data" not in st.session_state:
        st.session_state.edit_event_data = None
    if "selected_day_for_new" not in st.session_state:
        st.session_state.selected_day_for_new = today

    # Si l'usuari ha clicat un dia des de la graella del calendari
    if "cal_day" in st.query_params:
        try:
            clicked_date = datetime.strptime(st.query_params["cal_day"], "%Y-%m-%d").date()
            st.session_state.selected_day_for_new = clicked_date
            st.session_state.picker_sel_day = clicked_date
            if clicked_date.month != st.session_state.cal_month or clicked_date.year != st.session_state.cal_year:
                st.session_state.cal_month = clicked_date.month
                st.session_state.cal_year = clicked_date.year
        except Exception:
            pass

    # Mesos en català
    mesos_cat = [
        "", "Gener", "Febrer", "Març", "Abril", "Maig", "Juny",
        "Juliol", "Agost", "Setembre", "Octubre", "Novembre", "Desembre"
    ]
    
    # Membres disponibles
    familia = app_cfg.get("familia", [])
    membres_noms = [m.get("nom", "Familiar") for m in familia]
    
    # CSS avançat estil Google Calendar / Chrome Glassmorphism
    st.markdown(f"""
    <style>
    .cal-header-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: {bg_card};
        backdrop-filter: blur(12px);
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 14px 20px;
        margin-bottom: 16px;
    }}
    /* Amagar el pont de selecció de dia per WebSocket */
    div[data-testid="stTextInput"]:has(input[aria-label="cal_bridge"]) {{
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    .cal-grid-container {{
        width: 100%;
        margin-bottom: 20px;
        user-select: none;
    }}
    .cal-grid-header {{
        display: grid !important;
        grid-template-columns: repeat(7, 1fr) !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
        width: 100% !important;
    }}
    .cal-grid-th {{
        text-align: center;
        padding: 6px 1px !important;
        font-size: 0.76rem !important;
        font-weight: 700;
        text-transform: uppercase;
        background: {bg_card_sub};
        border-radius: 6px;
        border: 1px solid {border_color};
        width: 100% !important;
        box-sizing: border-box;
    }}
    .cal-grid-body {{
        display: grid !important;
        grid-template-columns: repeat(7, 1fr) !important;
        gap: 4px !important;
        width: 100% !important;
    }}
    .cal-grid-cell {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 10px;
        padding: 5px;
        min-height: 95px;
        display: flex;
        flex-direction: column;
        transition: all 0.15s ease;
        text-decoration: none !important;
        color: inherit !important;
        box-sizing: border-box;
        cursor: pointer;
        overflow: hidden;
    }}
    .cal-grid-cell:hover {{
        border-color: #38bdf8 !important;
        background: {bg_card_sub} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
    }}
    .cal-grid-cell.selected-day {{
        border: 2px solid #38bdf8 !important;
        background: rgba(56, 189, 248, 0.15) !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.45) !important;
    }}
    .cal-grid-cell.today {{
        border: 2px solid #f59e0b !important;
    }}
    .cal-grid-cell.other-month {{
        opacity: 0.4;
    }}
    .cal-grid-cell.today.selected-day {{
        border: 2px solid #38bdf8 !important;
        box-shadow: 0 0 14px rgba(56, 189, 248, 0.5);
    }}
    .cal-grid-cell.other-month {{
        opacity: 0.35;
    }}
    .cal-cell-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }}
    .cal-day-num {{
        font-size: 0.9rem;
        font-weight: 800;
        color: {text_primary};
        display: inline-block;
        width: 24px;
        height: 24px;
        line-height: 24px;
        text-align: center;
        border-radius: 50%;
    }}
    .cal-day-num.today-num {{
        background: #0284c7;
        color: #ffffff !important;
    }}
    .today-badge {{
        font-size: 0.65rem;
        font-weight: 800;
        color: #38bdf8;
    }}
    .ev-count-badge {{
        font-size: 0.65rem;
        font-weight: 800;
        background: #38bdf822;
        color: #38bdf8;
        border-radius: 10px;
        padding: 1px 5px;
    }}
    .cal-cell-events {{
        display: flex;
        flex-direction: column;
        gap: 2px;
        flex-grow: 1;
    }}
    .cal-ev-chip {{
        font-size: 0.72rem;
        padding: 2px 5px;
        border-radius: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: flex;
        align-items: center;
        gap: 3px;
        font-weight: 600;
        line-height: 1.2;
    }}
    .ev-chip-txt {{
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .cal-ev-more {{
        font-size: 0.68rem;
        font-weight: 700;
        color: #38bdf8;
        text-align: center;
    }}
    .agenda-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s ease;
    }}
    .agenda-card:hover {{
        border-color: #38bdf8;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }}
    .agenda-date-box {{
        background: {bg_card_sub};
        border-radius: 10px;
        padding: 8px 12px;
        text-align: center;
        min-width: 60px;
        margin-right: 16px;
    }}
    .agenda-date-day {{
        font-size: 1.35rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1;
    }}
    .agenda-date-sub {{
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        color: {text_secondary};
    }}

    /* Badge d'estat a la llista i detall del dia */
    .cal-status-badge {{
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 800;
        margin-left: 6px;
        display: inline-block;
        vertical-align: middle;
        letter-spacing: 0.5px;
    }}
    .cal-status-badge.badge-done {{
        background: rgba(16, 185, 129, 0.22);
        color: #10b981;
        border: 1px solid #10b981;
    }}
    .cal-status-badge.badge-cancelled {{
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid #ef4444;
    }}

    /* Colorejar els botons actius de Fet (verd) i No Fet (vermell) - suport complet stColumn */
    div[data-testid="stColumn"]:has(.cal-btn-done) button,
    .stColumn:has(.cal-btn-done) button {{
        background-color: #10b981 !important;
        border-color: #10b981 !important;
        color: #ffffff !important;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.45) !important;
    }}
    div[data-testid="stColumn"]:has(.cal-btn-done) button:hover,
    .stColumn:has(.cal-btn-done) button:hover {{
        background-color: #059669 !important;
        border-color: #059669 !important;
    }}

    div[data-testid="stColumn"]:has(.cal-btn-cancelled) button,
    .stColumn:has(.cal-btn-cancelled) button {{
        background-color: #ef4444 !important;
        border-color: #ef4444 !important;
        color: #ffffff !important;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.45) !important;
    }}
    div[data-testid="stColumn"]:has(.cal-btn-cancelled) button:hover,
    .stColumn:has(.cal-btn-cancelled) button:hover {{
        background-color: #dc2626 !important;
        border-color: #dc2626 !important;
    }}

    div[data-testid="stColumn"]:has(.cal-btn-pending-chk) button:hover,
    .stColumn:has(.cal-btn-pending-chk) button:hover {{
        border-color: #10b981 !important;
        color: #10b981 !important;
    }}

    div[data-testid="stColumn"]:has(.cal-btn-pending-cross) button:hover,
    .stColumn:has(.cal-btn-pending-cross) button:hover {{
        border-color: #ef4444 !important;
        color: #ef4444 !important;
    }}

    /* Assegurar que els botons d'acció es mantinguin SEMPRE en 1 sola línia horitzontal compacta */
    div[data-testid="stHorizontalBlock"]:has(.cal-action-btn),
    .stHorizontalBlock:has(.cal-action-btn) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 3px !important;
        width: 100% !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-action-btn) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.cal-action-btn) > .stColumn,
    div[data-testid="stHorizontalBlock"]:has(.cal-action-btn) > div,
    .stHorizontalBlock:has(.cal-action-btn) > div[data-testid="stColumn"],
    .stHorizontalBlock:has(.cal-action-btn) > .stColumn,
    .stHorizontalBlock:has(.cal-action-btn) > div {{
        min-width: 0 !important;
        flex: 1 1 0px !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-action-btn) button,
    .stHorizontalBlock:has(.cal-action-btn) button {{
        padding: 2px 2px !important;
        font-size: 0.82rem !important;
        min-height: 30px !important;
        height: 30px !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 6px !important;
        margin: 0 !important;
        width: 100% !important;
    }}

    /* Header superior: fila única de títol i botons d'acció (+ Nou, Sincro, Inici) */
    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker),
    .stHorizontalBlock:has(.cal-main-header-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 6px !important;
        width: 100% !important;
        margin-bottom: 6px !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker) > div[data-testid="stColumn"]:first-child,
    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker) > .stColumn:first-child,
    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker) > div:first-child {{
        min-width: 0 !important;
        flex: 0 0 auto !important;
        width: auto !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker) > div[data-testid="stColumn"]:last-child,
    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker) > .stColumn:last-child,
    div[data-testid="stHorizontalBlock"]:has(.cal-main-header-marker) > div:last-child {{
        min-width: 0 !important;
        flex: 1 1 auto !important;
        width: auto !important;
    }}

    /* Botons d'acció superior (+ Nou, Sincro, Inici) en 1 sola línia */
    div[data-testid="stHorizontalBlock"]:has(.cal-top-btns-marker),
    .stHorizontalBlock:has(.cal-top-btns-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 4px !important;
        width: 100% !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-top-btns-marker) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.cal-top-btns-marker) > .stColumn,
    div[data-testid="stHorizontalBlock"]:has(.cal-top-btns-marker) > div,
    .stHorizontalBlock:has(.cal-top-btns-marker) > div[data-testid="stColumn"],
    .stHorizontalBlock:has(.cal-top-btns-marker) > .stColumn,
    .stHorizontalBlock:has(.cal-top-btns-marker) > div {{
        min-width: 0 !important;
        flex: 1 1 0px !important;
        width: auto !important;
        padding: 0 !important;
        margin: 0 !important;
    }}

    div[data-testid="stColumn"]:has(.cal-btn-nou-wrap) button,
    .stColumn:has(.cal-btn-nou-wrap) button {{
        padding: 3px 6px !important;
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        min-height: 30px !important;
        height: 30px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        width: 100% !important;
    }}

    /* Botons Sincro i Inici MÉS PETITS tal com demana l'usuari i sense truncament */
    div[data-testid="stColumn"]:has(.cal-btn-sync-wrap) button,
    .stColumn:has(.cal-btn-sync-wrap) button,
    div[data-testid="stColumn"]:has(.cal-btn-inici-wrap) button,
    .stColumn:has(.cal-btn-inici-wrap) button {{
        padding: 2px 3px !important;
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        opacity: 0.9 !important;
        width: 100% !important;
    }}

    div[data-testid="stColumn"]:has(.cal-btn-sync-wrap) button p,
    .stColumn:has(.cal-btn-sync-wrap) button p,
    div[data-testid="stColumn"]:has(.cal-btn-today-wrap) button p,
    .stColumn:has(.cal-btn-today-wrap) button p {{
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }}

    /* Barra de navegació mensual (◀ Avui ▶ + Mes + Vista) */
    div[data-testid="stHorizontalBlock"]:has(.cal-navbar-marker),
    .stHorizontalBlock:has(.cal-navbar-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 4px !important;
        width: 100% !important;
        margin-bottom: 6px !important;
    }}

    /* Fila de botons de navegació mensual (◀ Avui ▶) en 1 sola línia */
    div[data-testid="stHorizontalBlock"]:has(.cal-nav-arrows-marker),
    .stHorizontalBlock:has(.cal-nav-arrows-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 4px !important;
        width: 100% !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-nav-arrows-marker) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.cal-nav-arrows-marker) > .stColumn,
    div[data-testid="stHorizontalBlock"]:has(.cal-nav-arrows-marker) > div,
    .stHorizontalBlock:has(.cal-nav-arrows-marker) > div[data-testid="stColumn"],
    .stHorizontalBlock:has(.cal-nav-arrows-marker) > .stColumn,
    .stHorizontalBlock:has(.cal-nav-arrows-marker) > div {{
        min-width: 0 !important;
        flex: 1 1 0px !important;
        width: auto !important;
        padding: 0 !important;
        margin: 0 !important;
    }}

    /* Botons fletxa ◀ ▶ MÉS PETITS */
    div[data-testid="stColumn"]:has(.cal-btn-arrow-wrap) button,
    .stColumn:has(.cal-btn-arrow-wrap) button {{
        padding: 2px 4px !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        width: 100% !important;
    }}

    /* Botó Avui MÉS PETIT */
    div[data-testid="stColumn"]:has(.cal-btn-today-wrap) button,
    .stColumn:has(.cal-btn-today-wrap) button {{
        padding: 2px 6px !important;
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        min-height: 28px !important;
        height: 28px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        width: 100% !important;
    }}

    /* GRAELLA DEL CALENDARI: Capçalera dels 7 dies DLL-DMG */
    div[data-testid="stHorizontalBlock"]:has(.cal-grid-header-wrap),
    .stHorizontalBlock:has(.cal-grid-header-wrap) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 4px !important;
        width: 100% !important;
        margin-bottom: 4px !important;
    }}
    div[data-testid="stHorizontalBlock"]:has(.cal-grid-header-wrap) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.cal-grid-header-wrap) > .stColumn,
    .stHorizontalBlock:has(.cal-grid-header-wrap) > div[data-testid="stColumn"],
    .stHorizontalBlock:has(.cal-grid-header-wrap) > .stColumn {{
        min-width: 0 !important;
        width: calc(100% / 7) !important;
        max-width: calc(100% / 7) !important;
        flex: 1 1 0px !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    .cal-grid-th {{
        text-align: center;
        padding: 6px 1px !important;
        font-size: 0.74rem !important;
        font-weight: 700;
        text-transform: uppercase;
        background: {bg_card_sub};
        border-radius: 6px;
        border: 1px solid {border_color};
        width: 100% !important;
        box-sizing: border-box;
    }}

    /* Fila de les setmanes: 7 columnes espaioses amb requadres i elements visuals */
    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker),
    .stHorizontalBlock:has(.cal-week-row-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: stretch !important;
        gap: 4px !important;
        width: 100% !important;
        margin-bottom: 4px !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > .stColumn,
    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > div,
    .stHorizontalBlock:has(.cal-week-row-marker) > div[data-testid="stColumn"],
    .stHorizontalBlock:has(.cal-week-row-marker) > .stColumn,
    .stHorizontalBlock:has(.cal-week-row-marker) > div {{
        min-width: 0 !important;
        width: calc(100% / 7) !important;
        max-width: calc(100% / 7) !important;
        flex: 1 1 0px !important;
        padding: 4px !important;
        margin: 0 !important;
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 10px;
        min-height: 100px !important;
        display: flex !important;
        flex-direction: column !important;
        box-sizing: border-box;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > div[data-testid="stColumn"]:has(.is-selected),
    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > .stColumn:has(.is-selected) {{
        border: 2px solid #38bdf8 !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.45) !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > div[data-testid="stColumn"]:has(.is-today),
    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > .stColumn:has(.is-today) {{
        border: 2px solid #f59e0b !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > div[data-testid="stColumn"]:has(.other-month),
    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) > .stColumn:has(.other-month) {{
        opacity: 0.4 !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.cal-week-row-marker) button,
    .stHorizontalBlock:has(.cal-week-row-marker) button {{
        padding: 2px 2px !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        min-height: 26px !important;
        height: 26px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        margin-bottom: 3px !important;
        width: 100% !important;
    }}

    .cal-mobile-dots {{
        display: none;
    }}

    @media (max-width: 768px) {{
        .cal-grid-header {{
            gap: 2px !important;
        }}
        .cal-grid-body {{
            gap: 2px !important;
        }}
        .cal-grid-cell {{
            min-height: 78px !important;
            padding: 3px 2px !important;
            border-radius: 6px !important;
        }}
        .cal-day-num {{
            font-size: 0.80rem !important;
            width: 20px !important;
            height: 20px !important;
            line-height: 20px !important;
        }}
        .cal-ev-chip {{
            padding: 1px 2px !important;
            font-size: 0.68rem !important;
            margin-bottom: 2px !important;
        }}
        .ev-chip-txt {{
            display: inline-block !important;
            max-width: 38px !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }}
        .today-badge {{
            font-size: 0.58rem !important;
        }}
        .cal-grid-th {{
            font-size: 0.68rem !important;
            padding: 3px 0px !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # Capçalera compacta d'Agenda amb logo/títol a l'esquerra i botons nets a la dreta (+ Nou, Sincro, Inici)
    c_hdr_l, c_hdr_r = st.columns([3.2, 6.8], vertical_alignment="center")
    with c_hdr_l:
        st.markdown(f"""<span class='cal-main-header-marker'></span>
        <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-size:1.7rem; line-height:1;">📅</span>
            <div style="font-size:1.55rem; font-weight:800; color:{text_primary}; line-height:1;">Agenda</div>
        </div>
        """, unsafe_allow_html=True)
    with c_hdr_r:
        c_b1, c_b2, c_b3 = st.columns([1.1, 1.2, 1.1], vertical_alignment="center")
        with c_b1:
            st.markdown("<span class='cal-top-btns-marker'></span><div class='cal-btn-nou-wrap'></div>", unsafe_allow_html=True)
            if st.button("➕ Nou", type="primary", use_container_width=True, key="btn_open_new_ev"):
                st.session_state.show_event_modal = not st.session_state.show_event_modal
                st.session_state.edit_event_data = None
                st.rerun()
        with c_b2:
            st.markdown("<div class='cal-btn-sync-wrap'></div>", unsafe_allow_html=True)
            if st.button("🔄 Sincro", use_container_width=True, key="btn_sync_feeds", help="Actualitzar calendaris"):
                invalidate_cal_cache(); cm.clear_feeds_cache()
                st.success("✅ Memòria cau alliberada!")
                st.rerun()
        with c_b3:
            st.markdown("<div class='cal-btn-inici-wrap'></div>", unsafe_allow_html=True)
            if st.button("🔙 Inici", use_container_width=True, key="btn_nav_inici_cal", help="Tornar a l'inici"):
                st.session_state.current_module = None
                if "mod" in st.query_params:
                    try:
                        del st.query_params["mod"]
                    except Exception:
                        pass
                st.rerun()

    st.write("")

    # =========================================================================
    # DIÀLEG MODAL D'ESDEVENIMENTS (CENTRAT I NADIU ST.DIALOG)
    # =========================================================================
    if st.session_state.get("show_event_modal") or st.session_state.get("edit_event_data"):
        event_modal_dialog(active_user, edit_ev=st.session_state.get("edit_event_data"), preselected_date=st.session_state.get("selected_day_for_new"))

    # =========================================================================
    # BARRA DE FILTRES I NAVEGACIÓ TEMPORAL    # BARRA DE FILTRES I NAVEGACIÓ TEMPORAL
    # =========================================================================
    cur_year = st.session_state.cal_year
    cur_month = st.session_state.cal_month
    month_name = mesos_cat[cur_month]
    
    # Capçalera de navegació temporal centrada i espaiosa
    st.markdown(f"""
    <div style='text-align:center; margin-bottom:6px;'>
        <div style='font-size:1.35rem; font-weight:800; color:{text_primary}; line-height:1.2;'>{month_name} {cur_year}</div>
        <div style='font-size:0.84rem; font-weight:600; color:{text_secondary}; margin-top:2px;'>
            👤 Agenda de: <span style='color:#38bdf8; font-weight:700;'>{active_user}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c_nav_left, c_nav_right = st.columns([5.2, 4.8], vertical_alignment="center")
    
    with c_nav_left:
        c_prev, c_today, c_next = st.columns([1, 1.8, 1], vertical_alignment="center")
        with c_prev:
            st.markdown("<span class='cal-nav-arrows-marker'></span><div class='cal-btn-arrow-wrap'></div>", unsafe_allow_html=True)
            if st.button("◀", key="cal_prev_month", use_container_width=True, help="Mes anterior"):
                if cur_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
        with c_today:
            st.markdown("<div class='cal-btn-today-wrap'></div>", unsafe_allow_html=True)
            if st.button("Avui", key="cal_btn_today", use_container_width=True, help="Tornar al mes actual"):
                st.session_state.cal_month = today.month
                st.session_state.cal_year = today.year
                st.rerun()
        with c_next:
            st.markdown("<div class='cal-btn-arrow-wrap'></div>", unsafe_allow_html=True)
            if st.button("▶", key="cal_next_month", use_container_width=True, help="Mes següent"):
                if cur_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()
                
    with c_nav_right:
        mode_idx = 0 if st.session_state.cal_view_mode == "grid" else 1
        sel_view = st.radio("Vista", ["📅 Calendari", "📋 Agenda / Llista"], index=mode_idx, horizontal=True, label_visibility="collapsed", key="radio_cal_view")
        new_mode = "grid" if "Calendari" in sel_view else "agenda"
        if new_mode != st.session_state.cal_view_mode:
            st.session_state.cal_view_mode = new_mode
            st.rerun()

    # Carregar tots els esdeveniments per al període actual (amb memòria cau a la sessió per màxima agilitat)
    cal_cache_key = f"cal_events_{cur_year}_{cur_month}_{active_user}"
    if cal_cache_key not in st.session_state:
        st.session_state[cal_cache_key] = cm.get_all_events(app_cfg=app_cfg, target_year=cur_year, target_month=cur_month)
    raw_events = st.session_state[cal_cache_key]
    
    # Cada usuari només veu el seu propi calendari (i esdeveniments de tota la família)
    filtered_events = []
    for ev in raw_events:
        ev_m = ev.get("member") or ""
        if ev_m == active_user or ev_m in ("Tota la família", "Comú", "Familiar", ""):
            filtered_events.append(ev)
        
    # Organitzar esdeveniments per data (clau: "YYYY-MM-DD")
    events_by_date = {}
    for ev in filtered_events:
        d_str = ev.get("start_date", "")
        if d_str:
            if d_str not in events_by_date:
                events_by_date[d_str] = []
            events_by_date[d_str].append(ev)

    st.write("")

    # =========================================================================
    # VISTA 1: CALENDARI (GRAELLA HTML CSS GRID ROBUSTA AMB WEBSOCKET INSTANTANI)
    # =========================================================================
    # Pont de comunicació WebSocket per a la selecció interactiva de dies (zero pantalla blanca)
    bridge_val = st.text_input("cal_bridge", value="", key="cal_day_bridge_hidden", label_visibility="collapsed")
    if bridge_val:
        try:
            d_clean = bridge_val.split("@")[0].strip()
            clicked_date = datetime.strptime(d_clean, "%Y-%m-%d").date()
            st.session_state.selected_day_for_new = clicked_date
            st.session_state.picker_sel_day = clicked_date
            if clicked_date.month != st.session_state.cal_month or clicked_date.year != st.session_state.cal_year:
                st.session_state.cal_month = clicked_date.month
                st.session_state.cal_year = clicked_date.year
        except Exception:
            pass

    if st.session_state.cal_view_mode == "grid":
        setmana_dies = ["Dll", "Dmt", "Dmc", "Djs", "Dvd", "Dss", "Dmg"]
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(cur_year, cur_month)
        
        # Script client per enviar el clic de dia directament per WebSocket sense recàrrega de navegador
        st.markdown("""
        <script>
        function setCalDay(dStr) {
            let el = null;
            try {
                el = window.parent.document.querySelector('input[aria-label="cal_bridge"]') || document.querySelector('input[aria-label="cal_bridge"]');
            } catch(e) {}
            if (el) {
                try {
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    setter.call(el, dStr + '@' + Date.now());
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
                    el.blur();
                    const target = document.getElementById('gestio-dia') || (window.parent && window.parent.document.getElementById('gestio-dia'));
                    if (target) target.scrollIntoView({ behavior: 'smooth' });
                    return;
                } catch(e) {}
            }
            window.location.href = '?mod=modules.calendari&cal_day=' + dStr + '#gestio-dia';
        }
        </script>
        """, unsafe_allow_html=True)
        
        # Construir tot el HTML de la graella en un únic bloc continu i segur
        html_grid = []
        html_grid.append('<div class="cal-grid-container">')
        
        # Capçalera dels 7 dies
        html_grid.append('<div class="cal-grid-header">')
        for idx_th, d_nom in enumerate(setmana_dies):
            is_weekend = (idx_th >= 5)
            th_color = "#38bdf8" if is_weekend else text_secondary
            html_grid.append(f'<div class="cal-grid-th" style="color:{th_color};">{d_nom}</div>')
        html_grid.append('</div>')
        
        # Cos de les setmanes (7 columnes exactes CSS Grid)
        html_grid.append('<div class="cal-grid-body">')
        for week in month_days:
            for d_obj in week:
                d_str = d_obj.strftime("%Y-%m-%d")
                is_current_month = (d_obj.month == cur_month)
                is_today = (d_obj == today)
                is_selected = (d_obj == st.session_state.selected_day_for_new)
                
                cell_classes = ["cal-grid-cell"]
                if not is_current_month:
                    cell_classes.append("other-month")
                if is_today:
                    cell_classes.append("today")
                if is_selected:
                    cell_classes.append("selected-day")
                    
                day_evs = sort_events_by_time(events_by_date.get(d_str, []))
                num_class = "cal-day-num today-num" if is_today else "cal-day-num"
                
                classes_str = " ".join(cell_classes)
                html_grid.append(f'<div class="{classes_str}" onclick="setCalDay(&#39;{d_str}&#39;)" title="Veure gestió del dia {d_obj.day}/{d_obj.month}/{d_obj.year}">')
                html_grid.append('<div class="cal-cell-head">')
                html_grid.append(f'<span class="{num_class}">{d_obj.day}</span>')
                if is_today:
                    html_grid.append('<span class="today-badge">AVUI</span>')
                elif len(day_evs) > 0:
                    html_grid.append(f'<span class="ev-count-badge">{len(day_evs)}</span>')
                html_grid.append('</div>')
                
                # Xips dels esdeveniments
                html_grid.append('<div class="cal-cell-events">')
                for ev in day_evs[:3]:
                    cat_info = cm.CATEGORIES.get(ev.get("category", "Altres"), cm.CATEGORIES["Altres"])
                    ev_color = ev.get("color", cat_info["color"])
                    ev_status = ev.get("status", "pending")
                    ev_time = ev.get("start_time", "")
                    time_pfx = f"<b>{ev_time}</b> " if ev_time else ""
                    ev_icon = cat_info["icon"]
                    ev_title = ev.get("title", "Esdeveniment")
                    
                    chip_border = f"border:1px solid {ev_color}55;"
                    chip_bg = f"background:{ev_color}22;"
                    chip_text_color = ev_color
                    status_prefix = ""
                    if ev_status == "done":
                        chip_border = "border:1px solid #10b981;"
                        chip_bg = "background:rgba(16,185,129,0.25);"
                        chip_text_color = "#10b981"
                        status_prefix = "✅ "
                    elif ev_status == "cancelled":
                        chip_border = "border:1px dashed #ef4444;"
                        chip_bg = "background:rgba(239,68,68,0.2);"
                        chip_text_color = "#ef4444"
                        status_prefix = "❌ "

                    html_grid.append(
                        f'<div class="cal-ev-chip" style="{chip_bg} color:{chip_text_color}; {chip_border}" title="{ev_title} ({ev.get("member", "Família")})">'
                        f'<span>{ev_icon}</span> <span class="ev-chip-txt">{status_prefix}{time_pfx}{ev_title}</span>'
                        f'</div>'
                    )
                if len(day_evs) > 3:
                    html_grid.append(f'<div class="cal-ev-more">+{len(day_evs) - 3} més</div>')
                html_grid.append('</div>')
                html_grid.append('</div>')
                
        html_grid.append('</div>') # end cal-grid-body
        html_grid.append('</div>') # end cal-grid-container
        
        st.markdown("".join(html_grid), unsafe_allow_html=True)
        
        # Secció interactiva de Detalls del Dia i Creació Ràpida
        st.markdown('<div id="gestio-dia" style="margin-top:20px;"></div>', unsafe_allow_html=True)
        c_sel_d1, c_sel_d2 = st.columns([6, 4], vertical_alignment="center")
        with c_sel_d1:
            sel_day = st.date_input("Tria un dia per veure/afegir esdeveniments", value=st.session_state.selected_day_for_new or today, format="DD/MM/YYYY", key="picker_sel_day")
            if sel_day != st.session_state.selected_day_for_new:
                st.session_state.selected_day_for_new = sel_day
                if sel_day.month != cur_month or sel_day.year != cur_year:
                    st.session_state.cal_month = sel_day.month
                    st.session_state.cal_year = sel_day.year
                    st.rerun()
        with c_sel_d2:
            if st.button("➕ Nou Esdeveniment per a aquest dia", type="primary", use_container_width=True, key="btn_add_for_sel_day"):
                st.session_state.show_event_modal = True
                st.session_state.edit_event_data = None
                st.rerun()
                
        sel_day_str = sel_day.strftime("%Y-%m-%d")
        sel_day_evs = sort_events_by_time(events_by_date.get(sel_day_str, []))
        
        weekday_names_full = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
        w_name = weekday_names_full[sel_day.weekday()]
        
        st.markdown(f"#### 🔍 Consulta i Gestió del Dia: <span style='color:#38bdf8;'>{w_name}, {sel_day.strftime('%d/%m/%Y')}</span>", unsafe_allow_html=True)
        
        if not sel_day_evs:
            st.info(f"No hi ha cap esdeveniment agendat per a {w_name}, **{sel_day.strftime('%d/%m/%Y')}**.")
        else:
            visible_evs = sel_day_evs[:15]
            more_evs = sel_day_evs[15:]
            for idx_d, ev in enumerate(visible_evs):
                cat_info = cm.CATEGORIES.get(ev.get("category", "Altres"), cm.CATEGORIES["Altres"])
                time_disp = "Tot el dia" if ev.get("all_day", False) else (ev.get("start_time", "") or "Sense hora")
                loc_disp = f" · 📍 {ev.get('location')}" if ev.get("location") else ""
                raw_ev_id = ev.get("id", f"ev_{sel_day_str}_{ev.get('title')}")
                ev_id = f"{raw_ev_id}_{sel_day_str}_{idx_d}"
                ev_status = ev.get("status", "pending")
                
                title_prefix = ""
                status_badge = ""
                title_style = f"color:{text_primary}; font-weight:700;"
                if ev_status == "done":
                    title_prefix = "✅ "
                    status_badge = " <span class='cal-status-badge badge-done'>FET</span>"
                    title_style = "color:#10b981; font-weight:800;"
                elif ev_status == "cancelled":
                    title_prefix = "❌ "
                    status_badge = " <span class='cal-status-badge badge-cancelled'>NO FET</span>"
                    title_style = "text-decoration:line-through; opacity:0.75; color:#ef4444; font-weight:800;"
                
                with st.container():
                    c1, c2 = st.columns([5.8, 4.2], vertical_alignment="center")
                    with c1:
                        st.markdown(f"""
                        <div style="font-size:1.05rem; {title_style}">
                            {title_prefix}{cat_info['icon']} {ev.get('title')}{status_badge}
                        </div>
                        <div style="font-size:0.85rem; color:{text_secondary};">
                            ⏰ <b>{time_disp}</b> · 👤 {ev.get('member', 'Família')}{loc_disp}
                        </div>
                        """, unsafe_allow_html=True)
                        if ev.get("description"):
                            st.caption(ev.get("description"))
                    with c2:
                        b_chk, b_cross, b_edit, b_del, b_gcal = st.columns([1, 1, 1, 1, 1.4])
                        with b_chk:
                            if ev_status == "done":
                                st.markdown('<div class="cal-action-btn cal-btn-done"></div>', unsafe_allow_html=True)
                                if st.button("✅", key=f"btn_chk_{ev_id}", help="Desmarcar (tornar a pendent)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "pending", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                            else:
                                st.markdown('<div class="cal-action-btn cal-btn-pending-chk"></div>', unsafe_allow_html=True)
                                if st.button("✔️", key=f"btn_chk_{ev_id}", help="Marcar com a fet / completat (verd)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "done", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                        with b_cross:
                            if ev_status == "cancelled":
                                st.markdown('<div class="cal-action-btn cal-btn-cancelled"></div>', unsafe_allow_html=True)
                                if st.button("❌", key=f"btn_cross_{ev_id}", help="Desmarcar (tornar a pendent)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "pending", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                            else:
                                st.markdown('<div class="cal-action-btn cal-btn-pending-cross"></div>', unsafe_allow_html=True)
                                if st.button("✖️", key=f"btn_cross_{ev_id}", help="Marcar com a no fet / cancel·lat (vermell)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "cancelled", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                        with b_edit:
                            st.markdown('<div class="cal-action-btn"></div>', unsafe_allow_html=True)
                            if st.button("✏️", key=f"edit_sel_day_{ev_id}", help="Modificar esdeveniment", use_container_width=True):
                                st.session_state.edit_event_data = ev
                                st.session_state.show_event_modal = True
                                st.rerun()
                        with b_del:
                            st.markdown('<div class="cal-action-btn"></div>', unsafe_allow_html=True)
                            if st.button("🗑️", key=f"del_sel_day_{ev_id}", help="Esborrar esdeveniment", use_container_width=True):
                                invalidate_cal_cache(); cm.delete_event(ev.get("id"), uid=ev.get("uid"), start_date=ev.get("start_date"))
                                st.success("Esdeveniment eliminat correctament!")
                                st.rerun()
                        with b_gcal:
                            st.markdown('<div class="cal-action-btn"></div>', unsafe_allow_html=True)
                            g_url = cm.generate_google_calendar_url(ev)
                            st.markdown(f'<a href="{g_url}" target="_blank" style="text-decoration:none; display:flex; align-items:center; justify-content:center; width:100%; border-radius:6px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-size:0.75rem; font-weight:700; height:30px; min-height:30px; padding:0 2px; cursor:pointer; white-space:nowrap; box-sizing:border-box;" title="Obrir a Google Calendar">📅 GCal</a>', unsafe_allow_html=True)
                    st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:6px 0;'></div>", unsafe_allow_html=True)
            
            if more_evs:
                with st.expander(f"➕ Veure {len(more_evs)} esdeveniments més per a {w_name}, {sel_day.strftime('%d/%m/%Y')}", expanded=False):
                    for idx_m, ev in enumerate(more_evs, start=15):
                        cat_info = cm.CATEGORIES.get(ev.get("category", "Altres"), cm.CATEGORIES["Altres"])
                        time_disp = "Tot el dia" if ev.get("all_day", False) else (ev.get("start_time", "") or "Sense hora")
                        loc_disp = f" · 📍 {ev.get('location')}" if ev.get("location") else ""
                        raw_ev_id = ev.get("id", f"ev_{sel_day_str}_{ev.get('title')}")
                        ev_id = f"{raw_ev_id}_{sel_day_str}_{idx_m}"
                        ev_status = ev.get("status", "pending")
                        title_prefix = "✅ " if ev_status == "done" else ("❌ " if ev_status == "cancelled" else "")
                        status_badge = " <span class='cal-status-badge badge-done'>FET</span>" if ev_status == "done" else (" <span class='cal-status-badge badge-cancelled'>NO FET</span>" if ev_status == "cancelled" else "")
                        title_style = "color:#10b981; font-weight:800;" if ev_status == "done" else ("text-decoration:line-through; opacity:0.75; color:#ef4444; font-weight:800;" if ev_status == "cancelled" else f"color:{text_primary}; font-weight:700;")
                        with st.container():
                            c1, c2 = st.columns([5.8, 4.2], vertical_alignment="center")
                            with c1:
                                st.markdown(f"<div style='font-size:1.05rem; {title_style}'>{title_prefix}{cat_info['icon']} {ev.get('title')}{status_badge}</div><div style='font-size:0.85rem; color:{text_secondary};'>⏰ <b>{time_disp}</b> · 👤 {ev.get('member', 'Família')}{loc_disp}</div>", unsafe_allow_html=True)
                            with c2:
                                b_chk, b_cross, b_edit, b_del, b_gcal = st.columns([1, 1, 1, 1, 1.4])
                                with b_chk:
                                    if ev_status == "done":
                                        if st.button("✅", key=f"btn_chk_{ev_id}", help="Desmarcar (tornar a pendent)", use_container_width=True):
                                            invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "pending", uid=ev.get("uid"), title=ev.get("title"))
                                            st.rerun()
                                    else:
                                        if st.button("✔️", key=f"btn_chk_{ev_id}", help="Marcar com a fet / completat (verd)", use_container_width=True):
                                            invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "done", uid=ev.get("uid"), title=ev.get("title"))
                                            st.rerun()
                                with b_cross:
                                    if ev_status == "cancelled":
                                        if st.button("❌", key=f"btn_cross_{ev_id}", help="Desmarcar (tornar a pendent)", use_container_width=True):
                                            invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "pending", uid=ev.get("uid"), title=ev.get("title"))
                                            st.rerun()
                                    else:
                                        if st.button("✖️", key=f"btn_cross_{ev_id}", help="Marcar com a no fet / cancel·lat (vermell)", use_container_width=True):
                                            invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "cancelled", uid=ev.get("uid"), title=ev.get("title"))
                                            st.rerun()
                                with b_edit:
                                    if st.button("✏️", key=f"edit_ev_{ev_id}", help="Modificar esdeveniment", use_container_width=True):
                                        st.session_state.edit_event_data = ev
                                        st.session_state.show_event_modal = True
                                        st.rerun()
                                with b_del:
                                    if st.button("🗑️", key=f"del_ev_{ev_id}", help="Esborrar esdeveniment", use_container_width=True):
                                        invalidate_cal_cache(); cm.delete_event(ev.get("id"), uid=ev.get("uid"), start_date=ev.get("start_date"))
                                        st.success("Esdeveniment eliminat!")
                                        st.rerun()
                                with b_gcal:
                                    g_url = cm.generate_google_calendar_url(ev)
                                    st.markdown(f'<a href="{g_url}" target="_blank" style="text-decoration:none; display:flex; align-items:center; justify-content:center; width:100%; border-radius:6px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-size:0.75rem; font-weight:700; height:30px; min-height:30px; padding:0 2px; cursor:pointer; white-space:nowrap; box-sizing:border-box;" title="Obrir a Google Calendar">📅 GCal</a>', unsafe_allow_html=True)
                            st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:6px 0;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # VISTA 2: AGENDA / LLISTA CRONOLÒGICA
    # =========================================================================
    else:
        st.markdown(f"### 📋 Llista d'Esdeveniments de {month_name} {cur_year}")
        
        # Filtrar estrictament els esdeveniments que pertanyen al mes i any seleccionat
        month_events = []
        for ev in filtered_events:
            d_str = ev.get("start_date", "")
            try:
                ev_d = datetime.strptime(d_str, "%Y-%m-%d").date()
                if ev_d.year == cur_year and ev_d.month == cur_month:
                    month_events.append(ev)
            except Exception:
                pass
                
        # Ordenar esdeveniments per data i hora
        def _ev_sort_key(x):
            is_timed = bool(not x.get("all_day", False) and x.get("start_time"))
            t_str = x.get("start_time", "") or ""
            if ":" in t_str:
                parts = t_str.split(":")
                try:
                    t_str = f"{int(parts[0]):02d}:{parts[1]}"
                except Exception:
                    pass
            return (x.get("start_date", ""), 1 if is_timed else 0, t_str)
        sorted_events = sorted(month_events, key=_ev_sort_key)
        
        if not sorted_events:
            st.info(f"No hi ha cap esdeveniment registrat per a {month_name} de {cur_year} amb el filtre seleccionat.")
        else:
            for idx, ev in enumerate(sorted_events):
                d_str = ev.get("start_date", "")
                try:
                    ev_date_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                    day_num = ev_date_obj.day
                    month_abbr = mesos_cat[ev_date_obj.month][:3].upper()
                    weekday_name = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"][ev_date_obj.weekday()]
                except Exception:
                    day_num = "?"
                    month_abbr = ""
                    weekday_name = ""
                    
                cat_info = cm.CATEGORIES.get(ev.get("category", "Altres"), cm.CATEGORIES["Altres"])
                ev_color = ev.get("color", cat_info["color"])
                
                # Indicador de proximitat
                status_badge = ""
                if ev_date_obj == today:
                    status_badge = "<span style='background:#ef4444; color:#fff; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:12px; margin-left:8px;'>AVUI</span>"
                elif ev_date_obj == today + timedelta(days=1):
                    status_badge = "<span style='background:#f59e0b; color:#fff; font-size:0.75rem; font-weight:800; padding:2px 8px; border-radius:12px; margin-left:8px;'>DEMÀ</span>"
                    
                time_disp = "Tot el dia" if ev.get("all_day", False) else (ev.get("start_time", "") or "Sense hora")
                source_disp = "Google Calendar" if ev.get("is_external", False) else "Local"
                loc_disp = f" · 📍 {ev.get('location')}" if ev.get("location") else ""
                
                with st.container():
                    c_ag_date, c_ag_info, c_ag_btns = st.columns([1.5, 6, 2.5], vertical_alignment="center")
                    with c_ag_date:
                        st.markdown(f"""
                        <div class="agenda-date-box">
                            <div class="agenda-date-day">{day_num}</div>
                            <div class="agenda-date-sub">{month_abbr}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    ev_status = ev.get("status", "pending")
                    ev_title_prefix = ""
                    ev_status_badge = ""
                    ev_title_style = f"color:{text_primary}; font-weight:800;"
                    if ev_status == "done":
                        ev_title_prefix = "✅ "
                        ev_status_badge = " <span class='cal-status-badge badge-done'>FET</span>"
                        ev_title_style = "color:#10b981; font-weight:800;"
                    elif ev_status == "cancelled":
                        ev_title_prefix = "❌ "
                        ev_status_badge = " <span class='cal-status-badge badge-cancelled'>NO FET</span>"
                        ev_title_style = "text-decoration:line-through; opacity:0.75; color:#ef4444; font-weight:800;"

                    with c_ag_info:
                        st.markdown(f"""
                        <div style="font-size:1.1rem; {ev_title_style}">
                            {ev_title_prefix}{cat_info['icon']} {ev.get('title')}{status_badge}{ev_status_badge}
                        </div>
                        <div style="font-size:0.85rem; color:{text_secondary}; margin-top:2px;">
                            <span style="color:#38bdf8; font-weight:600;">{weekday_name}</span> · ⏰ <b>{time_disp}</b> · 👤 {ev.get('member', 'Família')}{loc_disp}
                        </div>
                        """, unsafe_allow_html=True)
                        if ev.get("description"):
                            st.markdown(f"<div style='font-size:0.8rem; color:{text_secondary}; margin-top:4px;'>{ev.get('description')}</div>", unsafe_allow_html=True)
                    with c_ag_btns:
                        b_chk, b_cross, b_edit, b_del, b_gcal = st.columns([1, 1, 1, 1, 1.4])
                        raw_ev_id = ev.get("id", f"ev_{d_str}_{ev.get('title')}")
                        ev_id = f"{raw_ev_id}_{d_str}_{idx}"
                        with b_chk:
                            if ev_status == "done":
                                st.markdown('<div class="cal-action-btn cal-btn-done"></div>', unsafe_allow_html=True)
                                if st.button("✅", key=f"btn_chk_list_{ev_id}", help="Desmarcar (tornar a pendent)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "pending", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                            else:
                                st.markdown('<div class="cal-action-btn cal-btn-pending-chk"></div>', unsafe_allow_html=True)
                                if st.button("✔️", key=f"btn_chk_list_{ev_id}", help="Marcar com a fet / completat (verd)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "done", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                        with b_cross:
                            if ev_status == "cancelled":
                                st.markdown('<div class="cal-action-btn cal-btn-cancelled"></div>', unsafe_allow_html=True)
                                if st.button("❌", key=f"btn_cross_list_{ev_id}", help="Desmarcar (tornar a pendent)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "pending", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                            else:
                                st.markdown('<div class="cal-action-btn cal-btn-pending-cross"></div>', unsafe_allow_html=True)
                                if st.button("✖️", key=f"btn_cross_list_{ev_id}", help="Marcar com a no fet / cancel·lat (vermell)", use_container_width=True):
                                    invalidate_cal_cache(); cm.set_event_status(ev.get("id", raw_ev_id), ev.get("start_date"), "cancelled", uid=ev.get("uid"), title=ev.get("title"))
                                    st.rerun()
                        with b_edit:
                            st.markdown('<div class="cal-action-btn"></div>', unsafe_allow_html=True)
                            if st.button("✏️", key=f"edit_ev_list_{ev_id}", help="Modificar esdeveniment", use_container_width=True):
                                st.session_state.edit_event_data = ev
                                st.session_state.show_event_modal = True
                                st.rerun()
                        with b_del:
                            st.markdown('<div class="cal-action-btn"></div>', unsafe_allow_html=True)
                            if st.button("🗑️", key=f"del_ev_list_{ev_id}", help="Esborrar esdeveniment", use_container_width=True):
                                invalidate_cal_cache(); cm.delete_event(ev.get("id"), uid=ev.get("uid"), start_date=ev.get("start_date"))
                                st.success("Esdeveniment eliminat!")
                                st.rerun()
                        with b_gcal:
                            st.markdown('<div class="cal-action-btn"></div>', unsafe_allow_html=True)
                            g_url = cm.generate_google_calendar_url(ev)
                            st.markdown(f'<a href="{g_url}" target="_blank" style="text-decoration:none; display:flex; align-items:center; justify-content:center; width:100%; border-radius:6px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-size:0.75rem; font-weight:700; height:30px; min-height:30px; padding:0 2px; cursor:pointer; white-space:nowrap; box-sizing:border-box;" title="Obrir a Google Calendar">📅 GCal</a>', unsafe_allow_html=True)
                    st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:10px 0;'></div>", unsafe_allow_html=True)
                    
    # =========================================================================
    # PEU DE PÀGINA AMB ESTAT DE SINCRONITZACIÓ GOOGLE CALENDAR
    # =========================================================================
    st.write("")
    with st.expander("ℹ️ Estat de sincronització amb Google Calendar dels membres", expanded=False):
        st.markdown("""
        **Com connectar el teu Google Calendar personal:**
        1. Ves a [Google Calendar](https://calendar.google.com) des del navegador.
        2. Fes clic a la roda dentada de **Configuració** > Selecciona el teu calendari a l'esquerra.
        3. Fes scroll fins a **'Adreça secreta en format iCal'** i copia l'enllaç URL que acaba en `.ics`.
        4. Entra al mòdul **⚙️ Configuració > 👨‍👩‍👧‍👦 Família** del Dashboard i enganxa l'enllaç a la casella de Google Calendar de cada membre.
        """)
        user_feed = ""
        for m in familia:
            if m.get("nom") == active_user:
                user_feed = m.get("google_calendar_ical", "").strip()
                break
        status_text = "🟢 Sincronitzat" if user_feed else "⚪ Sense enllaç (Fes servir la configuració per afegir-lo)"
        st.markdown(f"Estat del teu calendari personal (**{active_user}**): {status_text}")
