import streamlit as st
from datetime import datetime, date, timedelta
import core.medication_manager as mm
import core.google_calendar_api as gcal_api
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
    
    # Llista de pacients (Família + Tutelats)
    familia = app_cfg.get("familia", [])
    tutelats = app_cfg.get("tutelats", [])
    
    pacients_opcions = []
    pacients_dict = {}
    
    for m in familia:
        nom = m.get("nom", "Familiar")
        label = f"👨‍👩‍👧‍👦 {nom} ({m.get('rol', 'Família')})"
        pacients_opcions.append(label)
        pacients_dict[label] = {
            "nom": nom,
            "tipus": "Família",
            "icona": m.get("icona", "👤"),
            "gcal_feed": m.get("google_calendar_ical", ""),
            "color": m.get("color", "#3b82f6")
        }
        
    for t in tutelats:
        nom = t.get("nom", "Tutelat")
        label = f"🤝 {nom} (Tutelat/da)"
        pacients_opcions.append(label)
        pacients_dict[label] = {
            "nom": nom,
            "tipus": "Tutelat",
            "icona": t.get("icona", "👴"),
            "gcal_feed": "",
            "color": "#f97316"
        }
        
    if not pacients_opcions:
        pacients_opcions = ["👤 Pacient Principal"]
        pacients_dict["👤 Pacient Principal"] = {
            "nom": "Pacient Principal",
            "tipus": "Família",
            "icona": "👤",
            "gcal_feed": "",
            "color": "#3b82f6"
        }

    # CSS avançat estil Chrome / Glassmorphism
    st.markdown(f"""
    <style>
    .med-metric-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 14px 16px;
        text-align: center;
        transition: transform 0.2s ease;
    }}
    .med-metric-card:hover {{
        transform: translateY(-2px);
        border-color: #38bdf8;
    }}
    .med-metric-val {{
        font-size: 1.8rem;
        font-weight: 800;
        line-height: 1.1;
    }}
    .med-metric-lbl {{
        font-size: 0.78rem;
        font-weight: 700;
        color: {text_secondary};
        text-transform: uppercase;
        margin-top: 4px;
    }}
    .med-intake-card {{
        background: {bg_card};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s ease;
    }}
    .med-intake-card:hover {{
        border-color: #38bdf8;
        box-shadow: 0 4px 14px rgba(0,0,0,0.15);
    }}
    .med-time-box {{
        background: {bg_card_sub};
        border-radius: 10px;
        padding: 8px 12px;
        text-align: center;
        min-width: 70px;
        margin-right: 14px;
    }}
    .med-time-val {{
        font-size: 1.3rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1;
    }}
    </style>
    """, unsafe_allow_html=True)

    # =========================================================================
    # CAPÇALERA SUPERIOR
    # =========================================================================
    from modules.avatar_widget import render_header_with_avatar
    
    def _render_sync_med_btn():
        if st.button("🔄 Comprovar ✅", type="primary", use_container_width=True, help="Sincronitzar amb Google Calendar"):
            with st.spinner("Comprovant Google Calendar..."):
                changes = mm.sync_all_plans_with_google_calendar()
                if changes:
                    st.success("✅ Preses confirmades actualitzades!")
                else:
                    st.info("ℹ️ Sincronitzat (sense nous canvis).")
            st.rerun()

    title_med_html = f"""
    <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-size:2.2rem;">💊</span>
        <div>
            <h2 style="margin:0; font-weight:800; color:{text_primary};">Control de Medicació i Tutelats</h2>
            <div style="font-size:0.85rem; color:{text_secondary};">Plans de dosificació, alarmes i sincronització amb Google Calendar</div>
        </div>
    </div>
    """
    render_header_with_avatar(title_med_html, "medicacio", extra_button_fn=_render_sync_med_btn)

    st.write("")

    # =========================================================================
    # TARGETES DE RESUM D'ADHERÈNCIA D'AVUI
    # =========================================================================
    today_intakes = mm.get_today_intakes(today)
    total_doses = len(today_intakes)
    confirmed_doses = sum(1 for x in today_intakes if x["status"] == "confirmed")
    pending_doses = sum(1 for x in today_intakes if x["status"] == "pending")
    overdue_doses = sum(1 for x in today_intakes if x["status"] == "overdue")
    
    compliance_pct = int((confirmed_doses / total_doses * 100)) if total_doses > 0 else 100
    
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    with c_m1:
        st.markdown(f"""
        <div class="med-metric-card">
            <div class="med-metric-val" style="color:#38bdf8;">{total_doses}</div>
            <div class="med-metric-lbl">Preses Programades d'Avui</div>
        </div>
        """, unsafe_allow_html=True)
    with c_m2:
        st.markdown(f"""
        <div class="med-metric-card">
            <div class="med-metric-val" style="color:#22c55e;">{confirmed_doses}</div>
            <div class="med-metric-lbl">Preses Confirmades (✅)</div>
        </div>
        """, unsafe_allow_html=True)
    with c_m3:
        st.markdown(f"""
        <div class="med-metric-card">
            <div class="med-metric-val" style="color:#f59e0b;">{pending_doses}</div>
            <div class="med-metric-lbl">Preses Pendents</div>
        </div>
        """, unsafe_allow_html=True)
    with c_m4:
        col_overdue = "#ef4444" if overdue_doses > 0 else "#22c55e"
        st.markdown(f"""
        <div class="med-metric-card">
            <div class="med-metric-val" style="color:{col_overdue};">{overdue_doses}</div>
            <div class="med-metric-lbl">En Retard / Sense Marca</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # =========================================================================
    # PESTANYES PRINCIPALS DEL MÒDUL
    # =========================================================================
    tab_avui, tab_nou, tab_plans, tab_config = st.tabs([
        "🕒 Preses d'Avui & Supervisió",
        "➕ Crear Pla de Medicació",
        "📋 Plans Actius i Historial",
        "⚙️ Connexió Google Calendar API"
    ])

    # -------------------------------------------------------------------------
    # 1. PESTANYA: PRESES D'AVUI & SUPERVISIÓ
    # -------------------------------------------------------------------------
    with tab_avui:
        st.markdown(f"### 🕒 Pauta de Preses per a Avui ({today.strftime('%d/%m/%Y')})")
        
        # Filtre per pacient
        c_flt1, c_flt2 = st.columns([6, 4], vertical_alignment="center")
        with c_flt1:
            sel_pacient_filter = st.selectbox("Filtrar per persona:", ["Tots els pacients"] + pacients_opcions, key="filter_med_pacient")
            
        filtered_today = today_intakes
        if sel_pacient_filter != "Tots els pacients":
            pacient_nom_sel = pacients_dict[sel_pacient_filter]["nom"]
            filtered_today = [x for x in today_intakes if x["patient_name"] == pacient_nom_sel]
            
        if not filtered_today:
            st.info("🎉 No hi ha cap presa de medicació programada per a avui amb el filtre seleccionat.")
        else:
            for item in filtered_today:
                st_badge = ""
                st_color = "#38bdf8"
                if item["status"] == "confirmed":
                    conf_txt = f" (a les {item['confirmed_at'].split(' ')[-1]})" if item.get("confirmed_at") else ""
                    st_badge = f"<span style='background:#22c55e22; color:#22c55e; border:1px solid #22c55e55; font-size:0.75rem; font-weight:800; padding:3px 8px; border-radius:12px;'>✅ PRESA CONFIRMADA{conf_txt}</span>"
                    st_color = "#22c55e"
                elif item["status"] == "overdue":
                    st_badge = "<span style='background:#ef444422; color:#ef4444; border:1px solid #ef444455; font-size:0.75rem; font-weight:800; padding:3px 8px; border-radius:12px;'>⚠️ RETARD (>1h)</span>"
                    st_color = "#ef4444"
                else:
                    st_badge = "<span style='background:#f59e0b22; color:#f59e0b; border:1px solid #f59e0b55; font-size:0.75rem; font-weight:800; padding:3px 8px; border-radius:12px;'>⏰ PENDENT</span>"
                    st_color = "#f59e0b"
                    
                instr_txt = f" · ℹ️ {item['instructions']}" if item.get("instructions") else ""
                dosage_txt = f" ({item['dosage']})" if item.get("dosage") else ""
                
                with st.container():
                    c_time, c_info, c_actions = st.columns([1.5, 6, 2.5], vertical_alignment="center")
                    with c_time:
                        st.markdown(f"""
                        <div class="med-time-box">
                            <div class="med-time-val">{item['time']}</div>
                            <div style="font-size:0.7rem; color:{text_secondary}; font-weight:700;">HORA</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_info:
                        st.markdown(f"""
                        <div style="font-size:1.1rem; font-weight:800; color:{text_primary};">
                            💊 {item['medication_name']}{dosage_txt} {st_badge}
                        </div>
                        <div style="font-size:0.85rem; color:{text_secondary}; margin-top:2px;">
                            👤 <b>{item['patient_name']}</b> ({item['patient_type']}){instr_txt}
                        </div>
                        """, unsafe_allow_html=True)
                    with c_actions:
                        c_btn_toggle, c_btn_gcal = st.columns(2)
                        with c_btn_toggle:
                            btn_label = "↩️ Desfer" if item["status"] == "confirmed" else "✅ Prendre"
                            btn_type = "secondary" if item["status"] == "confirmed" else "primary"
                            if st.button(btn_label, key=f"tog_intake_{item['plan_id']}_{item['event_index']}", type=btn_type, use_container_width=True):
                                mm.toggle_intake_manual(item["plan_id"], item["event_index"])
                                st.rerun()
                        with c_btn_gcal:
                            # Link to open Google Calendar
                            from core.calendar_manager import generate_google_calendar_url
                            gcal_url = generate_google_calendar_url({
                                "title": item["title"],
                                "start_date": today.strftime("%Y-%m-%d"),
                                "start_time": item["time"],
                                "description": item["instructions"]
                            })
                            st.markdown(f'<a href="{gcal_url}" target="_blank"><button style="width:100%; border-radius:8px; border:1px solid #4285F4; background:#4285F4; color:#fff; font-size:0.75rem; font-weight:600; padding:6px 0; cursor:pointer;" title="Obrir a Google Calendar">📅 GCal</button></a>', unsafe_allow_html=True)
                    st.markdown(f"<div style='border-bottom:1px solid {border_color}; margin:8px 0;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 2. PESTANYA: CREAR NOU PLA DE MEDICACIÓ
    # -------------------------------------------------------------------------
    with tab_nou:
        st.markdown("### ➕ Programar Nou Pla de Medicació")
        st.markdown(f"<div style='font-size:0.85rem; color:{text_secondary}; margin-bottom:14px;'>Genera les preses i envia-les directament al Google Calendar del familiar o persona tutelada amb alarmes al seu mòbil.</div>", unsafe_allow_html=True)
        
        c_p1, c_p2 = st.columns([6, 4])
        with c_p1:
            sel_pacient_crear = st.selectbox("Pacient / Destinatari del pla *", pacients_opcions, key="crear_med_pacient")
            pacient_info = pacients_dict[sel_pacient_crear]
        with c_p2:
            default_gcal_email = app_cfg.get("admin", {}).get("email", "enricxicars@gmail.com")
            gcal_target_email = st.text_input("Correu de Google Calendar de destí", value=default_gcal_email, placeholder="ex: tutelat@gmail.com", key="crear_med_gcal_email")
            
        c_m1, c_m2 = st.columns([6, 4])
        with c_m1:
            med_nom_input = st.text_input("Nom del medicament *", placeholder="Ex: Paracetamol, Sintrom, Omeprazol, Amoxicil·lina...", key="crear_med_nom")
        with c_m2:
            med_dosi_input = st.text_input("Dosi / Format", placeholder="Ex: 1g, 500mg, 1 comprimit, 1 sobre...", key="crear_med_dosi")
            
        c_freq1, c_freq2 = st.columns([5, 5])
        with c_freq1:
            freq_opts = list(mm.FREQUENCY_PRESETS.keys())
            sel_freq = st.selectbox("Pauta / Freqüència", freq_opts, index=0, key="crear_med_freq")
            preset_times = mm.FREQUENCY_PRESETS[sel_freq]
        with c_freq2:
            if sel_freq == "Personalitzat":
                custom_times_str = st.text_input("Hores de presa (separades per comes)", value="08:00, 16:00, 00:00", key="crear_med_custom_times")
                plan_times = [t.strip() for t in custom_times_str.split(",") if t.strip()]
            else:
                st.write("")
                st.markdown(f"**⏰ Hores de presa:** `{', '.join(preset_times)}`")
                plan_times = preset_times
                
        c_dur1, c_dur2 = st.columns([5, 5])
        with c_dur1:
            start_date_input = st.date_input("Data d'inici del tractament", value=today, format="DD/MM/YYYY", key="crear_med_start_date")
        with c_dur2:
            duration_days_input = st.number_input("Durada del tractament (dies)", min_value=1, max_value=365, value=7, step=1, key="crear_med_duration")
            
        med_instr_input = st.text_area("Instruccions de la presa / Pauta mèdica", placeholder="Ex: Prendre després de l'àpat amb un got d'aigua. No barrejar amb alcohol.", key="crear_med_instr", height=70)
        
        st.write("")
        c_sub1, c_sub2 = st.columns([6, 4])
        with c_sub1:
            if st.button("🚀 Crear i Enviar a Google Calendar", type="primary", use_container_width=True, key="btn_submit_med_plan"):
                if not med_nom_input.strip():
                    st.error("El nom del medicament és obligatori.")
                elif not plan_times:
                    st.error("Cal definir com a mínim una hora de presa.")
                else:
                    new_plan_payload = {
                        "patient_name": pacient_info["nom"],
                        "patient_type": pacient_info["tipus"],
                        "medication_name": med_nom_input.strip(),
                        "dosage": med_dosi_input.strip(),
                        "instructions": med_instr_input.strip(),
                        "frequency_type": sel_freq,
                        "times": plan_times,
                        "start_date": start_date_input.strftime("%Y-%m-%d"),
                        "duration_days": int(duration_days_input),
                        "calendar_id": gcal_target_email.strip()
                    }
                    created = mm.create_plan(new_plan_payload)
                    total_events_created = len(created["events"])
                    if created.get("gcal_synced"):
                        st.success(f"✅ Pla creat correctament! S'han injectat {total_events_created} preses directament a Google Calendar ({gcal_target_email}).")
                    else:
                        st.success(f"✅ Pla creat correctament amb {total_events_created} preses registrades al Dashboard!")
                    st.rerun()
                    
        with c_sub2:
            # Opció de descarregar el paquet ICS
            temp_events = mm.generate_intake_events({
                "patient_name": pacient_info["nom"],
                "medication_name": med_nom_input if med_nom_input else "Medicament",
                "dosage": med_dosi_input,
                "instructions": med_instr_input,
                "start_date": start_date_input.strftime("%Y-%m-%d"),
                "duration_days": int(duration_days_input),
                "times": plan_times
            })
            ics_content = gcal_api.generate_ics_download_content(temp_events, plan_title=f"Pla_{med_nom_input}")
            st.download_button(
                "📥 Descarregar fitxer .ICS del Pla",
                data=ics_content,
                file_name=f"Pla_Medicacio_{med_nom_input or 'Medicament'}.ics",
                mime="text/calendar",
                use_container_width=True,
                help="Descarrega el fitxer per importar totes les preses al teu Google Calendar o calendari mòbil"
            )

    # -------------------------------------------------------------------------
    # 3. PESTANYA: PLANS ACTIUS I HISTORIAL
    # -------------------------------------------------------------------------
    with tab_plans:
        st.markdown("### 📋 Historial de Plans de Medicació")
        all_plans = mm.load_plans()
        
        if not all_plans:
            st.info("No hi ha cap pla de medicació creat actualment. Utilitza la pestanya '➕ Crear Pla de Medicació' per registrar-ne un.")
        else:
            for p in all_plans:
                plan_evs = p.get("events", [])
                tot_p = len(plan_evs)
                conf_p = sum(1 for e in plan_evs if e.get("status") == "confirmed")
                pct_p = int((conf_p / tot_p * 100)) if tot_p > 0 else 0
                
                with st.expander(f"💊 {p.get('medication_name')} · 👤 {p.get('patient_name')} ({conf_p}/{tot_p} preses realitzades · {pct_p}%)", expanded=True):
                    c_det1, c_det2 = st.columns([7, 3])
                    with c_det1:
                        st.markdown(f"**Dosi:** {p.get('dosage', 'No especificada')} | **Freqüència:** {p.get('frequency_type')} (`{', '.join(p.get('times', []))}`)")
                        st.markdown(f"**Període:** Del {p.get('start_date')} ({p.get('duration_days')} dies) | **Google Calendar:** `{p.get('calendar_id', 'No assignat')}`")
                        if p.get("instructions"):
                            st.caption(f"ℹ️ {p.get('instructions')}")
                    with c_det2:
                        st.progress(pct_p / 100.0)
                        st.markdown(f"<div style='text-align:center; font-size:0.85rem; font-weight:700; color:#22c55e;'>Adherència: {pct_p}%</div>", unsafe_allow_html=True)
                        if st.button("🗑️ Eliminar Pla", key=f"del_plan_{p.get('id')}", use_container_width=True):
                            mm.delete_plan(p.get("id"))
                            st.rerun()

    # -------------------------------------------------------------------------
    # 4. PESTANYA: CONNEXIÓ GOOGLE CALENDAR API & GUIA
    # -------------------------------------------------------------------------
    with tab_config:
        st.markdown("### ⚙️ Configuració de la Google Calendar API")
        
        is_cfg = gcal_api.is_service_account_configured()
        if is_cfg:
            sa_email = gcal_api.get_service_account_email()
            st.success(f"🟢 **Compte de Servei Connectat correctament!**\n\nAdreça del servei: `{sa_email}`")
            st.markdown(f"""
            **Com compartir el Google Calendar de qualsevol familiar o persona tutelada:**
            1. Obre [Google Calendar](https://calendar.google.com) amb el compte del familiar.
            2. Vés a **Configuració** > Selecciona el calendari a l'esquerra.
            3. A la secció **'Compartir amb persones o grups específics'**, fes clic a **Afegir persones**.
            4. Enganxa el correu del servei: `{sa_email}`
            5. Selecciona el permís: **'Fer canvis en els esdeveniments'**.
            """)
        else:
            st.warning("🟡 **Compte de Servei no configurat** (S'està utilitzant el mode d'exportació i enllaços web directes).")
            st.markdown("""
            **Com activar la sincronització directa i silenciosa en 2 minuts (Gratuït):**
            1. Vés a [Google Cloud Console](https://console.cloud.google.com).
            2. Crea un nou projecte (ex: *Dashboard Familiar*) i activa la **Google Calendar API**.
            3. Vés a **IAM i Administració > Comptes de Servei** > **Crear compte de servei**.
            4. Fes clic a la pestanya **Claus** > **Afegeix una clau > Crea una clau nova (JSON)**.
            5. Desa el fitxer descarregat com a `core/google_credentials.json` a la carpeta del projecte.
            """)
