import streamlit as st
import calendar
from datetime import datetime, date, timedelta
import core.calendar_manager as cm
from core.config_manager import load_app_config

def render():
    app_cfg = load_app_config()
    is_dark = (app_cfg.get("tema", "Fosc") == "Fosc")
    
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
    .cal-grid-container {{
        width: 100%;
        margin-bottom: 20px;
        user-select: none;
    }}
    .cal-grid-header {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 6px;
        margin-bottom: 6px;
    }}
    .cal-grid-th {{
        text-align: center;
        padding: 8px 2px;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        background: {bg_card_sub};
        border-radius: 8px;
        border: 1px solid {border_color};
    }}
    .cal-grid-body {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 6px;
    }}
    .cal-grid-cell {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 6px;
        min-height: 95px;
        display: flex;
        flex-direction: column;
        transition: all 0.2s ease;
        overflow: hidden;
    }}
    .cal-grid-cell:hover {{
        border-color: #38bdf8;
        background: {bg_card_sub};
    }}
    .cal-grid-cell.today {{
        border: 2px solid #38bdf8 !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.35);
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

    @media (max-width: 768px) {{
        .cal-grid-header {{
            gap: 2px !important;
        }}
        .cal-grid-body {{
            gap: 2px !important;
        }}
        .cal-grid-cell {{
            min-height: 52px !important;
            padding: 3px !important;
            border-radius: 6px !important;
        }}
        .cal-day-num {{
            font-size: 0.75rem !important;
            width: 18px !important;
            height: 18px !important;
            line-height: 18px !important;
        }}
        .cal-ev-chip {{
            padding: 1px 2px !important;
        }}
        .ev-chip-txt {{
            display: none !important;
        }}
        .today-badge {{
            display: none !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # =========================================================================
    # BARRA SUPERIOR DE CAPÇALERA
    # =========================================================================
    c_head1, c_head2 = st.columns([7, 3], vertical_alignment="center")
    with c_head1:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-size:2.2rem;">📅</span>
            <div>
                <h2 style="margin:0; font-weight:800; color:{text_primary};">Agenda i Calendari Familiar</h2>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_head2:
        c_btn_new, c_btn_sync, c_btn_back = st.columns([1.2, 1.1, 1.2])
        with c_btn_new:
            if st.button("➕ Esdeveniment", type="primary", use_container_width=True, key="btn_open_new_ev"):
                st.session_state.show_event_modal = not st.session_state.show_event_modal
                st.session_state.edit_event_data = None
                st.rerun()
        with c_btn_sync:
            if st.button("🔄 Sincro", use_container_width=True, key="btn_sync_feeds", help="Actualitzar calendaris de Google"):
                import os
                if os.path.exists("data/feeds_cache.json"):
                    try:
                        os.remove("data/feeds_cache.json")
                    except Exception:
                        pass
                st.success("✅ Sincronitzat!")
                st.rerun()
        with c_btn_back:
            if st.button("🔙 Inici", use_container_width=True, key="btn_back_home"):
                st.session_state.current_module = None
                st.rerun()

    st.write("")

    # =========================================================================
    # GENERADOR / FORMULARI D'ESDEVENIMENTS (MODAL / EXPANDER)
    # =========================================================================
    if st.session_state.show_event_modal or st.session_state.edit_event_data:
        edit_ev = st.session_state.edit_event_data
        is_editing = (edit_ev is not None)
        title_form = "✏️ Modificar Esdeveniment" if is_editing else "➕ Crear Nou Esdeveniment"
        
        with st.container():
            st.markdown(f"""
            <div style="background:{bg_card}; border:2px solid #38bdf8; border-radius:16px; padding:20px; margin-bottom:20px;">
                <h3 style="margin-top:0; color:#38bdf8;">{title_form}</h3>
            """, unsafe_allow_html=True)
            
            tab_manual, tab_quick = st.tabs(["📝 Formulari complet", "⚡ Creació ràpida intel·ligent"])
            
            with tab_quick:
                st.markdown("<div style='font-size:0.85rem; color:#94a3b8; margin-bottom:6px;'>Escriu en llenguatge natural (ex: <i>'Demà dinar familiar 14h'</i>, <i>'Divendres sopar 21h'</i>, <i>'Demà 18:30 metge Enric'</i>)</div>", unsafe_allow_html=True)
                c_q1, c_q2 = st.columns([8, 2])
                with c_q1:
                    quick_txt = st.text_input("Descripció de l'esdeveniment", placeholder="Escriu aquí el que vols agendar...", label_visibility="collapsed", key="quick_input_txt")
                with c_q2:
                    if st.button("⚡ Crear ràpidament", type="primary", use_container_width=True, key="btn_apply_quick"):
                        if quick_txt.strip():
                            parsed = cm.parse_natural_language_event(quick_txt, default_member=membres_noms[0] if membres_noms else "Tota la família")
                            if parsed:
                                cm.add_event(parsed)
                                st.session_state.show_event_modal = False
                                st.success(f"✅ Esdeveniment creat per al {parsed['start_date']}!")
                                st.rerun()
                                
            with tab_manual:
                default_title = edit_ev.get("title", "") if is_editing else ""
                default_member = edit_ev.get("member", "Tota la família") if is_editing else ("Tota la família")
                default_cat = edit_ev.get("category", "Altres") if is_editing else "Altres"
                
                init_date = today
                if is_editing and edit_ev.get("start_date"):
                    try:
                        init_date = datetime.strptime(edit_ev.get("start_date"), "%Y-%m-%d").date()
                    except Exception:
                        pass
                elif st.session_state.selected_day_for_new:
                    init_date = st.session_state.selected_day_for_new
                    
                default_start_time = "10:00"
                if is_editing and edit_ev.get("start_time"):
                    default_start_time = edit_ev.get("start_time")
                    
                default_all_day = edit_ev.get("all_day", False) if is_editing else False
                default_loc = edit_ev.get("location", "") if is_editing else ""
                default_desc = edit_ev.get("description", "") if is_editing else ""
                default_rep = edit_ev.get("repeat", "Cap") if is_editing else "Cap"
                
                c_f1, c_f2 = st.columns([6, 4])
                with c_f1:
                    f_title = st.text_input("Títol de l'esdeveniment *", value=default_title, key="f_ev_title", placeholder="Ex: Cita dentista, Dinar familiar, Sopar amb amics...")
                with c_f2:
                    all_member_options = ["Tota la família"] + membres_noms
                    idx_m = all_member_options.index(default_member) if default_member in all_member_options else 0
                    f_member = st.selectbox("Membre assignat", all_member_options, index=idx_m, key="f_ev_member")
                    
                c_f3, c_f4, c_f5 = st.columns([3.5, 3.5, 3])
                with c_f3:
                    cat_keys = list(cm.CATEGORIES.keys())
                    cat_idx = cat_keys.index(default_cat) if default_cat in cat_keys else len(cat_keys)-1
                    f_cat = st.selectbox("Categoria", cat_keys, index=cat_idx, format_func=lambda k: f"{cm.CATEGORIES[k]['icon']} {cm.CATEGORIES[k]['label']}", key="f_ev_cat")
                with c_f4:
                    f_date = st.date_input("Data de l'esdeveniment", value=init_date, format="DD/MM/YYYY", key="f_ev_date")
                with c_f5:
                    f_allday = st.checkbox("Tot el dia", value=default_all_day, key="f_ev_allday")
                    if not f_allday:
                        f_time = st.text_input("Hora (HH:MM)", value=default_start_time, key="f_ev_time")
                    else:
                        f_time = ""
                        
                c_f6, c_f7 = st.columns([6, 4])
                with c_f6:
                    f_loc = st.text_input("📍 Ubicació / Adreça", value=default_loc, placeholder="Ex: Restaurant Can Xic, Hospital de Terrassa...", key="f_ev_loc")
                with c_f7:
                    rep_opts = ["Cap", "Setmanal", "Mensual", "Anual"]
                    idx_rep = rep_opts.index(default_rep) if default_rep in rep_opts else 0
                    f_rep = st.selectbox("🔁 Repetició", rep_opts, index=idx_rep, key="f_ev_rep")
                    
                f_desc = st.text_area("📝 Notes i detalls", value=default_desc, placeholder="Indicacions, reserves, menú, etc.", key="f_ev_desc", height=70)
                
                c_act1, c_act2, c_act3 = st.columns([3, 4, 3])
                with c_act1:
                    if st.button("❌ Cancel·lar", use_container_width=True, key="btn_cancel_ev"):
                        st.session_state.show_event_modal = False
                        st.session_state.edit_event_data = None
                        st.rerun()
                with c_act2:
                    if st.button("💾 Desar Esdeveniment", type="primary", use_container_width=True, key="btn_save_ev"):
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
                            if is_editing and "id" in edit_ev:
                                cm.update_event(edit_ev["id"], new_data)
                                st.success("✅ Esdeveniment actualitzat!")
                            else:
                                cm.add_event(new_data)
                                st.success("✅ Esdeveniment creat correctament!")
                                
                            st.session_state.show_event_modal = False
                            st.session_state.edit_event_data = None
                            st.rerun()
                with c_act3:
                    # Enllaç ràpid a Google Calendar
                    gcal_temp_ev = {
                        "title": f_title if f_title else "Esdeveniment",
                        "start_date": f_date.strftime("%Y-%m-%d"),
                        "start_time": f_time if not f_allday else "10:00",
                        "all_day": f_allday,
                        "location": f_loc,
                        "description": f_desc
                    }
                    gcal_url = cm.generate_google_calendar_url(gcal_temp_ev)
                    st.markdown(f'<a href="{gcal_url}" target="_blank" style="text-decoration:none;"><button style="width:100%; height:38px; border-radius:8px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-weight:600; cursor:pointer;">📅 Google Calendar</button></a>', unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    # =========================================================================
    # BARRA DE FILTRES I NAVEGACIÓ TEMPORAL
    # =========================================================================
    cur_year = st.session_state.cal_year
    cur_month = st.session_state.cal_month
    month_name = mesos_cat[cur_month]
    
    c_nav1, c_nav2, c_nav3, c_nav4 = st.columns([3.5, 2.5, 3.5, 2.5], vertical_alignment="center")
    
    with c_nav1:
        c_prev, c_today, c_next = st.columns([1, 1.2, 1])
        with c_prev:
            if st.button("◀", key="cal_prev_month", use_container_width=True, help="Mes anterior"):
                if cur_month == 1:
                    st.session_state.cal_month = 12
                    st.session_state.cal_year -= 1
                else:
                    st.session_state.cal_month -= 1
                st.rerun()
        with c_today:
            if st.button("Avui", key="cal_btn_today", use_container_width=True, help="Tornar al mes actual"):
                st.session_state.cal_month = today.month
                st.session_state.cal_year = today.year
                st.rerun()
        with c_next:
            if st.button("▶", key="cal_next_month", use_container_width=True, help="Mes següent"):
                if cur_month == 12:
                    st.session_state.cal_month = 1
                    st.session_state.cal_year += 1
                else:
                    st.session_state.cal_month += 1
                st.rerun()
                
    with c_nav2:
        st.markdown(f"<div style='font-size:1.35rem; font-weight:800; color:{text_primary}; text-align:center;'>{month_name} {cur_year}</div>", unsafe_allow_html=True)
        
    with c_nav3:
        # Filtre per Membre
        filter_member_opts = ["Tots"] + ["Tota la família"] + membres_noms
        sel_mem = st.selectbox("Filtrar per membre", filter_member_opts, index=filter_member_opts.index(st.session_state.cal_filter_member) if st.session_state.cal_filter_member in filter_member_opts else 0, label_visibility="collapsed", key="sel_cal_mem_filter")
        if sel_mem != st.session_state.cal_filter_member:
            st.session_state.cal_filter_member = sel_mem
            st.rerun()
            
    with c_nav4:
        # Commutador de Vista (Calendari vs Agenda)
        mode_idx = 0 if st.session_state.cal_view_mode == "grid" else 1
        sel_view = st.radio("Vista", ["📅 Calendari", "📋 Agenda / Llista"], index=mode_idx, horizontal=True, label_visibility="collapsed", key="radio_cal_view")
        new_mode = "grid" if "Calendari" in sel_view else "agenda"
        if new_mode != st.session_state.cal_view_mode:
            st.session_state.cal_view_mode = new_mode
            st.rerun()

    # Carregar tots els esdeveniments per al període actual
    raw_events = cm.get_all_events(app_cfg=app_cfg, target_year=cur_year, target_month=cur_month)
    
    # Aplicar filtres de membre
    filtered_events = []
    for ev in raw_events:
        if st.session_state.cal_filter_member != "Tots":
            if ev.get("member") != st.session_state.cal_filter_member:
                continue
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
    # VISTA 1: CALENDARI (GOOGLE CALENDAR STYLE CSS GRID)
    # =========================================================================
    if st.session_state.cal_view_mode == "grid":
        setmana_dies = ["Dll", "Dmt", "Dmc", "Djs", "Dvd", "Dss", "Dmg"]
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(cur_year, cur_month)
        
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
        
        # Cos de les setmanes
        html_grid.append('<div class="cal-grid-body">')
        for week in month_days:
            for d_obj in week:
                d_str = d_obj.strftime("%Y-%m-%d")
                is_current_month = (d_obj.month == cur_month)
                is_today = (d_obj == today)
                
                cell_classes = ["cal-grid-cell"]
                if not is_current_month:
                    cell_classes.append("other-month")
                if is_today:
                    cell_classes.append("today")
                    
                day_evs = events_by_date.get(d_str, [])
                num_class = "cal-day-num today-num" if is_today else "cal-day-num"
                
                html_grid.append(f'<div class="{" ".join(cell_classes)}">')
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
                    ev_time = ev.get("start_time", "")
                    time_pfx = f"<b>{ev_time}</b> " if ev_time else ""
                    ev_icon = cat_info["icon"]
                    ev_title = ev.get("title", "Esdeveniment")
                    html_grid.append(
                        f'<div class="cal-ev-chip" style="background:{ev_color}22; color:{ev_color}; border:1px solid {ev_color}55;" title="{ev_title} ({ev.get("member", "Família")})">'
                        f'<span>{ev_icon}</span> <span class="ev-chip-txt">{time_pfx}{ev_title}</span>'
                        f'</div>'
                    )
                if len(day_evs) > 3:
                    html_grid.append(f'<div class="cal-ev-more">+{len(day_evs) - 3} més</div>')
                html_grid.append('</div>') # end cal-cell-events
                
                html_grid.append('</div>') # end cal-grid-cell
                
        html_grid.append('</div>') # end cal-grid-body
        html_grid.append('</div>') # end cal-grid-container
        
        # Renderitzar graella HTML pura
        st.markdown("".join(html_grid), unsafe_allow_html=True)
        
        # Secció interactiva de Detalls del Dia i Creació Ràpida
        st.markdown(f"#### 🔍 Consulta i Gestió del Dia")
        c_sel_d1, c_sel_d2 = st.columns([6, 4], vertical_alignment="center")
        with c_sel_d1:
            sel_day = st.date_input("Tria un dia per veure/afegir esdeveniments", value=st.session_state.selected_day_for_new or today, format="DD/MM/YYYY", key="picker_sel_day")
            st.session_state.selected_day_for_new = sel_day
        with c_sel_d2:
            if st.button("➕ Nou Esdeveniment per a aquest dia", type="primary", use_container_width=True, key="btn_add_for_sel_day"):
                st.session_state.show_event_modal = True
                st.session_state.edit_event_data = None
                st.rerun()
                
        sel_day_str = sel_day.strftime("%Y-%m-%d")
        sel_day_evs = events_by_date.get(sel_day_str, [])
        
        if not sel_day_evs:
            st.info(f"No hi ha cap esdeveniment agendat per al dia **{sel_day.strftime('%d/%m/%Y')}**.")
        else:
            for ev in sel_day_evs:
                cat_info = cm.CATEGORIES.get(ev.get("category", "Altres"), cm.CATEGORIES["Altres"])
                time_disp = "Tot el dia" if ev.get("all_day", False) else (ev.get("start_time", "") or "Sense hora")
                loc_disp = f" · 📍 {ev.get('location')}" if ev.get("location") else ""
                
                with st.container():
                    c1, c2 = st.columns([7.5, 2.5], vertical_alignment="center")
                    with c1:
                        st.markdown(f"""
                        <div style="font-size:1.05rem; font-weight:700; color:{text_primary};">
                            {cat_info['icon']} {ev.get('title')}
                        </div>
                        <div style="font-size:0.85rem; color:{text_secondary};">
                            ⏰ <b>{time_disp}</b> · 👤 {ev.get('member', 'Família')}{loc_disp}
                        </div>
                        """, unsafe_allow_html=True)
                        if ev.get("description"):
                            st.caption(ev.get("description"))
                    with c2:
                        c_act1, c_act2 = st.columns(2)
                        with c_act1:
                            g_url = cm.generate_google_calendar_url(ev)
                            st.markdown(f'<a href="{g_url}" target="_blank"><button style="width:100%; border-radius:6px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-size:0.75rem; padding:4px 0; cursor:pointer;" title="Obrir a Google Calendar">📅 GCal</button></a>', unsafe_allow_html=True)
                        with c_act2:
                            if not ev.get("is_external", False):
                                if st.button("🗑️", key=f"del_sel_day_{ev.get('id')}", use_container_width=True, help="Esborrar esdeveniment"):
                                    cm.delete_event(ev.get("id"))
                                    st.rerun()
                    st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:6px 0;'></div>", unsafe_allow_html=True)

    # =========================================================================
    # VISTA 2: AGENDA / LLISTA CRONOLÒGICA
    # =========================================================================
    else:
        st.markdown(f"### 📋 Llista d'Esdeveniments de {month_name} {cur_year}")
        
        # Ordenar esdeveniments per data i hora
        sorted_events = sorted(filtered_events, key=lambda x: (x.get("start_date", ""), x.get("start_time", "")))
        
        if not sorted_events:
            st.info(f"No hi ha cap esdeveniment registrat per a {month_name} de {cur_year} amb el filtre seleccionat.")
        else:
            for ev in sorted_events:
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
                    with c_ag_info:
                        st.markdown(f"""
                        <div style="font-size:1.1rem; font-weight:800; color:{text_primary};">
                            {cat_info['icon']} {ev.get('title')}{status_badge}
                        </div>
                        <div style="font-size:0.85rem; color:{text_secondary}; margin-top:2px;">
                            <span style="color:#38bdf8; font-weight:600;">{weekday_name}</span> · ⏰ <b>{time_disp}</b> · 👤 {ev.get('member', 'Família')}{loc_disp}
                        </div>
                        """, unsafe_allow_html=True)
                        if ev.get("description"):
                            st.markdown(f"<div style='font-size:0.8rem; color:{text_secondary}; margin-top:4px;'>{ev.get('description')}</div>", unsafe_allow_html=True)
                    with c_ag_btns:
                        c_b1, c_b2 = st.columns(2)
                        with c_b1:
                            g_url = cm.generate_google_calendar_url(ev)
                            st.markdown(f'<a href="{g_url}" target="_blank"><button style="width:100%; border-radius:8px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-size:0.8rem; font-weight:600; padding:6px 0; cursor:pointer;" title="Obrir a Google Calendar">📅 GCal</button></a>', unsafe_allow_html=True)
                        with c_b2:
                            if not ev.get("is_external", False):
                                if st.button("🗑️", key=f"del_ev_list_{ev.get('id')}", help="Esborrar esdeveniment", use_container_width=True):
                                    cm.delete_event(ev.get("id"))
                                    st.rerun()
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
        st.write("Membres amb calendari configurat:")
        for m in familia:
            feed_url = m.get("google_calendar_ical", "").strip()
            status_text = "🟢 Sincronitzat" if feed_url else "⚪ Sense enllaç (Fes servir la configuració per afegir-lo)"
            st.markdown(f"- **{m.get('nom')}**: {status_text}")
