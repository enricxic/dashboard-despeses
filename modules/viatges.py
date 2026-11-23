import streamlit as st
import json
import os
from datetime import datetime, date

DATA_FILE = "data/viatges.json"

def _load_viatges_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "viatges": [
            {
                "id": 1,
                "destinacio": "Escapada als Pirineus",
                "pais": "Catalunya / Andorra",
                "data_inici": "2027-01-15",
                "data_fi": "2027-01-18",
                "transport": "Cotxe",
                "allotjament": "Hotel de Muntanya",
                "pressupost": 450.0,
                "notes": "Ruta de senderisme, termalisme i descans.",
                "estat": "Planificat"
            }
        ],
        "checklist": [
            {"id": 1, "categoria": "📄 Documentació", "item": "DNI / Passaport vigent", "fet": True},
            {"id": 2, "categoria": "📄 Documentació", "item": "Targeta sanitària / Assegurança", "fet": True},
            {"id": 3, "categoria": "📄 Documentació", "item": "Bitllets / Reserves allotjament", "fet": False},
            {"id": 4, "categoria": "🔌 Electrònica", "item": "Carregador mòbil i bateria externa", "fet": True},
            {"id": 5, "categoria": "🔌 Electrònica", "item": "Adaptador endolls (si cal)", "fet": False},
            {"id": 6, "categoria": "💊 Farmaciola", "item": "Medicació habitual i analgèsics", "fet": False},
            {"id": 7, "categoria": "🧴 Necesser", "item": "Raspall de dents i estris de bany", "fet": False},
            {"id": 8, "categoria": "🧥 Roba & Calçat", "item": "Calçat còmode per caminar", "fet": False},
            {"id": 9, "categoria": "🧥 Roba & Calçat", "item": "Roba d'abric / impermeable", "fet": False}
        ]
    }

def _save_viatges_data(data):
    os.makedirs("data", exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error desant les dades de viatges: {e}")
        return False

def render():
    try:
        from modules.avatar_widget import render_header_with_avatar
        render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>✈️ Planificador de Viatges</h2>", "viatges")
    except Exception:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>✈️ Planificador de Viatges</h2>", unsafe_allow_html=True)

    data = _load_viatges_data()
    viatges = data.get("viatges", [])
    checklist = data.get("checklist", [])

    # Mètriques resum superiors
    avui = date.today()
    propers = []
    for v in viatges:
        try:
            d_ini = datetime.strptime(v["data_inici"], "%Y-%m-%d").date()
            if d_ini >= avui:
                dies_restants = (d_ini - avui).days
                propers.append((dies_restants, v))
        except Exception:
            pass
    propers.sort(key=lambda x: x[0])

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("🗺️ Total Viatges", len(viatges))
    with col_m2:
        if propers:
            st.metric("⏳ Proper Viatge", f"{propers[0][0]} dies", delta=propers[0][1].get("destinacio", ""))
        else:
            st.metric("⏳ Proper Viatge", "Cap planificat")
    with col_m3:
        total_pressupost = sum(float(v.get("pressupost", 0)) for v in viatges)
        st.metric("💳 Pressupost Total", f"{total_pressupost:,.2f} €")
    with col_m4:
        completats = sum(1 for c in checklist if c.get("fet", False))
        pct_chk = (completats / len(checklist) * 100) if checklist else 0
        st.metric("🧳 Maleta Preparada", f"{completats}/{len(checklist)} ({pct_chk:.0f}%)")

    st.write("")
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Viatges i Itineraris", "🧳 Llista d'Equipatge", "💰 Pressupost & Despeses", "➕ Nou Viatge"])

    # TAB 1: VIATGES I ITINERARIS
    with tab1:
        st.markdown("<h4 style='color:#f39c12;'>Destinacions i Escapades Planificades</h4>", unsafe_allow_html=True)
        if not viatges:
            st.info("Encara no hi ha cap viatge planificat. Pots afegir-ne un a la pestanya '➕ Nou Viatge'.")
        else:
            for idx, v in enumerate(viatges):
                with st.container():
                    col_card, col_act = st.columns([8, 2], vertical_alignment="center")
                    with col_card:
                        try:
                            d_ini = datetime.strptime(v["data_inici"], "%Y-%m-%d").strftime("%d/%m/%Y")
                            d_fi = datetime.strptime(v["data_fi"], "%Y-%m-%d").strftime("%d/%m/%Y")
                        except Exception:
                            d_ini = v.get("data_inici", "")
                            d_fi = v.get("data_fi", "")
                        
                        st.markdown(f"""
                        <div style="background:#1e293b; border-left:4px solid #38bdf8; border-radius:8px; padding:12px 16px; margin-bottom:10px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:1.15rem; font-weight:700; color:#f8fafc;">📍 {v.get('destinacio')}</span>
                                <span style="font-size:0.8rem; background:#0284c7; color:#fff; padding:2px 8px; border-radius:12px;">{v.get('estat', 'Planificat')}</span>
                            </div>
                            <div style="font-size:0.88rem; color:#94a3b8; margin-top:4px;">
                                📅 <b>Dates:</b> {d_ini} - {d_fi} &nbsp;|&nbsp; 🌍 <b>Zona:</b> {v.get('pais', '—')} &nbsp;|&nbsp; 🚗 <b>Transport:</b> {v.get('transport', '—')}
                            </div>
                            <div style="font-size:0.85rem; color:#cbd5e1; margin-top:6px;">
                                🏨 <b>Allotjament:</b> {v.get('allotjament', '—')} &nbsp;|&nbsp; 💶 <b>Pressupost previst:</b> {float(v.get('pressupost', 0)):,.2f} €
                            </div>
                            {f'<div style="font-size:0.82rem; color:#64748b; margin-top:4px;">📝 <i>{v.get("notes")}</i></div>' if v.get("notes") else ''}
                        </div>
                        """, unsafe_allow_html=True)
                    with col_act:
                        if st.button("🗑️ Eliminar", key=f"del_viatge_{idx}", use_container_width=True):
                            viatges.pop(idx)
                            data["viatges"] = viatges
                            _save_viatges_data(data)
                            st.rerun()

    # TAB 2: LLISTA D'EQUIPATGE
    with tab2:
        st.markdown("<h4 style='color:#f39c12;'>🧳 Checklist d'Equipatge i Maleta</h4>", unsafe_allow_html=True)
        st.caption("Marca els elements a mesura que els preparis per no descuidar res.")

        # Agrupar per categories
        categories = sorted(list({c.get("categoria", "Altres") for c in checklist}))
        canvi_fets = False
        
        for cat in categories:
            st.markdown(f"##### {cat}")
            items_cat = [c for c in checklist if c.get("categoria") == cat]
            for item in items_cat:
                c_chk, c_del = st.columns([9, 1], vertical_alignment="center")
                with c_chk:
                    chk_val = st.checkbox(item["item"], value=item.get("fet", False), key=f"chk_item_{item['id']}")
                    if chk_val != item.get("fet", False):
                        item["fet"] = chk_val
                        canvi_fets = True
                with c_del:
                    if st.button("❌", key=f"del_chk_{item['id']}", help="Eliminar element"):
                        checklist = [c for c in checklist if c["id"] != item["id"]]
                        data["checklist"] = checklist
                        _save_viatges_data(data)
                        st.rerun()

        if canvi_fets:
            data["checklist"] = checklist
            _save_viatges_data(data)
            st.rerun()

        st.markdown("---")
        st.markdown("###### ➕ Afegir nou element a la llista d'equipatge:")
        c_ncat, c_nitem, c_nbtn = st.columns([3, 6, 2], vertical_alignment="bottom")
        with c_ncat:
            nova_cat = st.selectbox("Categoria", ["📄 Documentació", "🔌 Electrònica", "💊 Farmaciola", "🧴 Necesser", "🧥 Roba & Calçat", "🎒 Altres"], key="sel_chk_cat")
        with c_nitem:
            nou_item_nom = st.text_input("Element a portar", placeholder="Ex: Crema solar, Carregador...", key="inp_chk_item")
        with c_nbtn:
            if st.button("➕ Afegir", key="btn_add_chk", use_container_width=True):
                if nou_item_nom.strip():
                    next_id = max([c["id"] for c in checklist], default=0) + 1
                    checklist.append({"id": next_id, "categoria": nova_cat, "item": nou_item_nom.strip(), "fet": False})
                    data["checklist"] = checklist
                    _save_viatges_data(data)
                    st.rerun()

    # TAB 3: PRESSUPOST & DESPESES
    with tab3:
        st.markdown("<h4 style='color:#f39c12;'>💰 Estimació Econòmica dels Viatges</h4>", unsafe_allow_html=True)
        if viatges:
            import pandas as pd
            df_v = pd.DataFrame(viatges)
            df_show = df_v[["destinacio", "data_inici", "data_fi", "transport", "allotjament", "pressupost", "estat"]].copy()
            
            def _fmt_d(val):
                try:
                    return datetime.strptime(str(val), "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    return str(val)
                    
            df_show["data_inici"] = df_show["data_inici"].apply(_fmt_d)
            df_show["data_fi"] = df_show["data_fi"].apply(_fmt_d)
            
            df_show.rename(columns={
                "destinacio": "Destinació",
                "data_inici": "Inici",
                "data_fi": "Finalització",
                "transport": "Transport",
                "allotjament": "Allotjament",
                "pressupost": "Pressupost (€)",
                "estat": "Estat"
            }, inplace=True)
            st.dataframe(df_show.style.format({"Pressupost (€)": "{:,.2f} €"}), use_container_width=True, hide_index=True)
        else:
            st.info("No hi ha viatges per calcular el pressupost.")

    # TAB 4: NOU VIATGE
    with tab4:
        st.markdown("<h4 style='color:#f39c12;'>➕ Registrar una Nova Aventura o Escapada</h4>", unsafe_allow_html=True)
        if "viatge_saved_msg" in st.session_state:
            st.success(st.session_state.pop("viatge_saved_msg"))

        with st.form("form_nou_viatge", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_dest = st.text_input("📍 Destinació / Ciutat / Zona", placeholder="Ex: Roma, Menorca, Pirineus...", key="form_v_dest")
                f_pais = st.text_input("🌍 País / Regió", placeholder="Ex: Itàlia, Illes Balears...", key="form_v_pais")
                f_transp = st.selectbox("🚗 Mitjà de Transport", ["Cotxe propi", "Avió", "Tren", "Autobús", "Vaixell / Ferri", "Altres"], key="form_v_transp")
            with col_f2:
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    f_dini = st.date_input("📅 Data d'inici", value=date.today(), format="DD/MM/YYYY", key="form_v_dini")
                with col_d2:
                    f_dfi = st.date_input("📅 Data de tornada", value=date.today(), format="DD/MM/YYYY", key="form_v_dfi")
                f_allotj = st.text_input("🏨 Allotjament", placeholder="Ex: Hotel, Apartament, Càmping...", key="form_v_allotj")
                f_press = st.number_input("💶 Pressupost estimat (€)", min_value=0.0, step=50.0, value=300.0, key="form_v_press")

            f_notes = st.text_area("📝 Notes, enllaços o plans a realitzar", placeholder="Llocs a visitar, restaurants recomanats, reserves...", key="form_v_notes")
            
            btn_save_v = st.form_submit_button("💾 Desar Viatge", type="primary", use_container_width=True)
            if btn_save_v:
                if f_dest.strip():
                    next_vid = max([v.get("id", 0) for v in viatges], default=0) + 1
                    nou_viatge = {
                        "id": next_vid,
                        "destinacio": f_dest.strip(),
                        "pais": f_pais.strip(),
                        "data_inici": f_dini.strftime("%Y-%m-%d"),
                        "data_fi": f_dfi.strftime("%Y-%m-%d"),
                        "transport": f_transp,
                        "allotjament": f_allotj.strip(),
                        "pressupost": float(f_press),
                        "notes": f_notes.strip(),
                        "estat": "Planificat"
                    }
                    viatges.append(nou_viatge)
                    data["viatges"] = viatges
                    _save_viatges_data(data)
                    
                    # Buidar explícitament els camps del formulari
                    for k in ["form_v_dest", "form_v_pais", "form_v_allotj", "form_v_notes"]:
                        if k in st.session_state:
                            st.session_state[k] = ""
                    if "form_v_press" in st.session_state:
                        st.session_state["form_v_press"] = 300.0
                    if "form_v_dini" in st.session_state:
                        st.session_state["form_v_dini"] = date.today()
                    if "form_v_dfi" in st.session_state:
                        st.session_state["form_v_dfi"] = date.today()

                    st.session_state["viatge_saved_msg"] = f"✅ Viatge a '{nou_viatge['destinacio']}' registrat amb èxit!"
                    st.rerun()
                else:
                    st.error("Si us plau, introdueix com a mínim la destinació del viatge.")
