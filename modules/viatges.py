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

def _get_despeses_reals_df():
    """Recupera el DataFrame de despeses reals del mòdul econòmic."""
    if "df_desp" in st.session_state and st.session_state["df_desp"] is not None and not st.session_state["df_desp"].empty:
        return st.session_state["df_desp"]
    try:
        from core.db import get_data_with_metadata
        _, df = get_data_with_metadata('despeses')
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    import os, pandas as pd
    for p in ["csv/despeses.csv", os.path.join(os.path.dirname(os.path.dirname(__file__)), "csv", "despeses.csv")]:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, sep=";")
            except Exception:
                pass
    return None

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
                    col_card, col_act = st.columns([7.8, 2.2], vertical_alignment="center")
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
                        is_editing = (st.session_state.get("editing_viatge_id") == v.get("id"))
                        btn_edit_label = "✖️ Tancar" if is_editing else "✏️ Modificar"
                        if st.button(btn_edit_label, key=f"edit_viatge_{v.get('id', idx)}", use_container_width=True):
                            st.session_state["editing_viatge_id"] = None if is_editing else v.get("id")
                            st.rerun()
                        if st.button("🗑️ Eliminar", key=f"del_viatge_{v.get('id', idx)}", use_container_width=True):
                            if st.session_state.get("editing_viatge_id") == v.get("id"):
                                st.session_state["editing_viatge_id"] = None
                            viatges.pop(idx)
                            data["viatges"] = viatges
                            _save_viatges_data(data)
                            st.rerun()

                    # Formulari desplegable de modificació
                    if st.session_state.get("editing_viatge_id") == v.get("id"):
                        with st.container():
                            st.markdown(f"""
                            <div style="background:#0f172a; border:1px solid #38bdf8; border-radius:8px; padding:16px; margin: 0 0 16px 0;">
                                <div style="font-size:1rem; font-weight:700; color:#38bdf8; margin-bottom:12px;">✏️ Modificant: {v.get('destinacio')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            with st.form(f"form_edit_viatge_{v.get('id', idx)}"):
                                ce1, ce2 = st.columns(2)
                                with ce1:
                                    e_dest = st.text_input("📍 Destinació", value=v.get("destinacio", ""), key=f"e_dest_{v.get('id')}")
                                    e_pais = st.text_input("🌍 País / Regió", value=v.get("pais", ""), key=f"e_pais_{v.get('id')}")
                                    t_opts = ["Cotxe propi", "Avió", "Tren", "Autobús", "Vaixell / Ferri", "Altres"]
                                    cur_t = v.get("transport", "Cotxe propi")
                                    idx_t = t_opts.index(cur_t) if cur_t in t_opts else 0
                                    e_transp = st.selectbox("🚗 Mitjà de Transport", t_opts, index=idx_t, key=f"e_transp_{v.get('id')}")
                                    
                                    estats = ["Planificat", "En curs", "Completat", "Cancel·lat"]
                                    cur_e = v.get("estat", "Planificat")
                                    idx_e = estats.index(cur_e) if cur_e in estats else 0
                                    e_estat = st.selectbox("📌 Estat del Viatge", estats, index=idx_e, key=f"e_estat_{v.get('id')}")
                                with ce2:
                                    ce_d1, ce_d2 = st.columns(2)
                                    try:
                                        val_dini = datetime.strptime(v.get("data_inici", ""), "%Y-%m-%d").date()
                                    except Exception:
                                        val_dini = date.today()
                                    try:
                                        val_dfi = datetime.strptime(v.get("data_fi", ""), "%Y-%m-%d").date()
                                    except Exception:
                                        val_dfi = date.today()
                                    with ce_d1:
                                        e_dini = st.date_input("📅 Data d'inici", value=val_dini, format="DD/MM/YYYY", key=f"e_dini_{v.get('id')}")
                                    with ce_d2:
                                        e_dfi = st.date_input("📅 Data de tornada", value=val_dfi, format="DD/MM/YYYY", key=f"e_dfi_{v.get('id')}")
                                    e_allotj = st.text_input("🏨 Allotjament", value=v.get("allotjament", ""), key=f"e_allotj_{v.get('id')}")
                                    e_press = st.number_input("💶 Pressupost estimat (€)", min_value=0.0, step=50.0, value=float(v.get("pressupost", 0.0)), key=f"e_press_{v.get('id')}")

                                e_notes = st.text_area("📝 Notes, enllaços o plans", value=v.get("notes", ""), key=f"e_notes_{v.get('id')}")

                                c_save, c_cancel = st.columns([2, 1])
                                with c_save:
                                    if st.form_submit_button("💾 Desar Canvis", type="primary", use_container_width=True):
                                        if e_dest.strip():
                                            v["destinacio"] = e_dest.strip()
                                            v["pais"] = e_pais.strip()
                                            v["transport"] = e_transp
                                            v["estat"] = e_estat
                                            v["data_inici"] = e_dini.strftime("%Y-%m-%d")
                                            v["data_fi"] = e_dfi.strftime("%Y-%m-%d")
                                            v["allotjament"] = e_allotj.strip()
                                            v["pressupost"] = float(e_press)
                                            v["notes"] = e_notes.strip()
                                            data["viatges"] = viatges
                                            _save_viatges_data(data)
                                            st.session_state["editing_viatge_id"] = None
                                            st.rerun()
                                        else:
                                            st.error("La destinació no pot estar buida.")
                                with c_cancel:
                                    if st.form_submit_button("❌ Cancel·lar", use_container_width=True):
                                        st.session_state["editing_viatge_id"] = None
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
        with st.form("form_add_chk_item", clear_on_submit=True):
            c_ncat, c_nitem, c_nbtn = st.columns([3, 6, 2], vertical_alignment="bottom")
            with c_ncat:
                nova_cat = st.selectbox("Categoria", ["📄 Documentació", "🔌 Electrònica", "💊 Farmaciola", "🧴 Necesser", "🧥 Roba & Calçat", "🎒 Altres"], key="sel_chk_cat")
            with c_nitem:
                nou_item_nom = st.text_input("Element a portar", placeholder="Ex: Crema solar, Carregador...", key="inp_chk_item")
            with c_nbtn:
                if st.form_submit_button("➕ Afegir", use_container_width=True):
                    if nou_item_nom.strip():
                        next_id = max([c["id"] for c in checklist], default=0) + 1
                        checklist.append({"id": next_id, "categoria": nova_cat, "item": nou_item_nom.strip(), "fet": False})
                        data["checklist"] = checklist
                        _save_viatges_data(data)
                        if "inp_chk_item" in st.session_state:
                            st.session_state["inp_chk_item"] = ""
                        st.rerun()

    # TAB 3: PRESSUPOST & DESPESES
    with tab3:
        st.markdown("<h4 style='color:#f39c12;'>💰 Pressupost Previst & Despeses Reals del Viatge</h4>", unsafe_allow_html=True)
        st.caption("Gestiona les partides de despesa previstes per a cada escapada i confronta-les amb les despeses reals registrades al Mòdul Econòmic (etiqueta [VACANCES]).")

        if not viatges:
            st.info("No hi ha viatges planificats. Afegeix-ne un a la pestanya '➕ Nou Viatge' per començar a gestionar el pressupost.")
        else:
            # Selector de viatge
            v_noms = [f"{v.get('destinacio', 'Sense nom')} ({v.get('data_inici', '')} al {v.get('data_fi', '')})" for v in viatges]
            sel_idx = 0
            if "sel_viatge_pressupost_idx" in st.session_state and st.session_state["sel_viatge_pressupost_idx"] < len(viatges):
                sel_idx = st.session_state["sel_viatge_pressupost_idx"]
            
            sel_v_str = st.selectbox("Selecciona el viatge a consultar o gestionar:", v_noms, index=sel_idx, key="sel_viatge_press_box")
            curr_v_idx = v_noms.index(sel_v_str) if sel_v_str in v_noms else 0
            st.session_state["sel_viatge_pressupost_idx"] = curr_v_idx
            curr_v = viatges[curr_v_idx]

            # Inicialitzar partides previstes si no n'hi ha
            if "despeses_previstes" not in curr_v or not isinstance(curr_v["despeses_previstes"], list):
                curr_v["despeses_previstes"] = []
                p_init = float(curr_v.get("pressupost", 0))
                if p_init > 0:
                    curr_v["despeses_previstes"].append({
                        "id": 1,
                        "categoria": "🏨 Allotjament",
                        "concepte": f"Estimació {curr_v.get('allotjament', 'Allotjament')}",
                        "import": p_init * 0.5
                    })
                    curr_v["despeses_previstes"].append({
                        "id": 2,
                        "categoria": "🚗 Transport / Carburant",
                        "concepte": f"Transport ({curr_v.get('transport', 'General')})",
                        "import": p_init * 0.3
                    })
                    curr_v["despeses_previstes"].append({
                        "id": 3,
                        "categoria": "🍽️ Menjar / Restaurants",
                        "concepte": "Compres i restaurants de vacances",
                        "import": p_init * 0.2
                    })
                    data["viatges"] = viatges
                    _save_viatges_data(data)

            partides = curr_v["despeses_previstes"]
            total_previst = sum(float(p.get("import", 0)) for p in partides)
            if total_previst == 0 and float(curr_v.get("pressupost", 0)) > 0:
                total_previst = float(curr_v.get("pressupost", 0))

            # Recuperar despeses reals des del Mòdul Econòmic
            df_desp_all = _get_despeses_reals_df()
            despeses_reals_viatge = []
            
            try:
                v_dini = datetime.strptime(curr_v.get("data_inici", ""), "%Y-%m-%d").date()
                v_dfi = datetime.strptime(curr_v.get("data_fi", ""), "%Y-%m-%d").date()
            except Exception:
                v_dini = None
                v_dfi = None

            if df_desp_all is not None and not df_desp_all.empty and v_dini and v_dfi:
                import pandas as pd
                for _, row in df_desp_all.iterrows():
                    d_str = str(row.get("Data", "")).strip()
                    row_date = None
                    try:
                        row_date = datetime.strptime(d_str, "%d/%m/%Y").date()
                    except Exception:
                        try:
                            row_date = pd.to_datetime(d_str).date()
                        except Exception:
                            pass
                    
                    if not row_date:
                        continue

                    comentari_txt = str(row.get("Comentari", ""))
                    is_vacances = ("[VACANCES]" in comentari_txt.upper()) or ("VACANCES" in comentari_txt.upper())
                    is_dest_mention = curr_v.get("destinacio", "").lower() in comentari_txt.lower()
                    in_range = (v_dini <= row_date <= v_dfi)

                    if (in_range and is_vacances) or is_dest_mention:
                        imp_carg = 0.0
                        for col_c in ["Import càrrec", "Import crrec", "Import carrec", "import_carrec"]:
                            if col_c in row and pd.notna(row[col_c]):
                                try:
                                    imp_carg = float(str(row[col_c]).replace(",", ".").replace("€", "").strip())
                                    break
                                except Exception:
                                    pass
                        if imp_carg > 0:
                            despeses_reals_viatge.append({
                                "Data": d_str,
                                "Concepte": str(row.get("Idconcepte", "")),
                                "Categoria": str(row.get("Idcategoria", "")),
                                "Banc": str(row.get("Banc", "")),
                                "FormaPago": str(row.get("FormaPago", "")),
                                "Import": imp_carg,
                                "Comentari": comentari_txt,
                                "row_date": row_date
                            })

            total_real = sum(r["Import"] for r in despeses_reals_viatge)
            diferencia = total_previst - total_real
            pct_consumit = (total_real / total_previst * 100) if total_previst > 0 else 0

            # RESUM I METRIQUES COMPARATIVES
            st.markdown(f"##### 📊 Balanç del Viatge: **{curr_v.get('destinacio')}**")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                st.metric("💶 Total Pressupostat (Previst)", f"{total_previst:,.2f} €")
            with col_b2:
                st.metric("💳 Despesa Real (Mòdul Econòmic)", f"{total_real:,.2f} €", delta=f"{pct_consumit:.1f}% gastat", delta_color="inverse")
            with col_b3:
                color_dif = "normal" if diferencia >= 0 else "inverse"
                st.metric("⚖️ Romanent / Desviació", f"{diferencia:,.2f} €", delta="Dins del pressupost" if diferencia >= 0 else "Superat", delta_color=color_dif)

            prog_val = min(1.0, max(0.0, total_real / total_previst)) if total_previst > 0 else 0.0
            st.progress(prog_val, text=f"Progrés de la despesa: {total_real:,.2f} € de {total_previst:,.2f} € ({pct_consumit:.1f}%)")

            st.write("")
            col_partides, col_reals = st.columns([1, 1], gap="medium")

            # COLUMNA ESQUERRA: PARTIDES PREVISTES (OBERTA I ACTUALITZABLE)
            with col_partides:
                st.markdown("##### 📝 Despeses Previstes (Pressupost Desglossat)")
                st.caption("Afegeix o modifica les partides que estimes que costarà el viatge:")

                if partides:
                    for p_idx, p in enumerate(partides):
                        with st.container():
                            cp1, cp2, cp3 = st.columns([6, 3, 1], vertical_alignment="center")
                            with cp1:
                                st.markdown(f"**{p.get('concepte')}**  \n<span style='font-size:0.8rem; color:#94a3b8;'>📂 {p.get('categoria')}</span>", unsafe_allow_html=True)
                            with cp2:
                                st.markdown(f"<span style='font-size:1rem; font-weight:700; color:#38bdf8;'>{float(p.get('import', 0)):,.2f} €</span>", unsafe_allow_html=True)
                            with cp3:
                                if st.button("🗑️", key=f"del_partida_{curr_v['id']}_{p_idx}", help="Eliminar partida"):
                                    partides.pop(p_idx)
                                    curr_v["despeses_previstes"] = partides
                                    curr_v["pressupost"] = sum(float(x.get("import", 0)) for x in partides)
                                    data["viatges"] = viatges
                                    _save_viatges_data(data)
                                    st.rerun()
                            st.markdown("<hr style='margin:4px 0 8px 0; border:none; border-top:1px solid #334155;'>", unsafe_allow_html=True)
                else:
                    st.info("Encara no has afegit cap partida prevista per a aquest viatge.")

                with st.expander("➕ Afegir Nova Despesa Prevista", expanded=True):
                    with st.form(f"form_add_partida_{curr_v['id']}", clear_on_submit=True):
                        np_cat = st.selectbox("Categoria", ["🏨 Allotjament", "🚗 Transport / Carburant", "🍽️ Menjar / Restaurants", "🎟️ Oci / Entrades", "🛍️ Compres / Souvenirs", "🎒 Altres"], key=f"np_cat_{curr_v['id']}")
                        np_conc = st.text_input("Concepte", placeholder="Ex: Hotel 3 nits, Gasolina anada, Sopar...", key=f"np_conc_{curr_v['id']}")
                        np_imp = st.number_input("Import estimat (€)", min_value=0.0, step=10.0, value=50.0, key=f"np_imp_{curr_v['id']}")
                        
                        if st.form_submit_button("➕ Afegir al Pressupost", type="primary", use_container_width=True):
                            if np_conc.strip() and np_imp > 0:
                                next_p_id = max([x.get("id", 0) for x in partides], default=0) + 1
                                partides.append({
                                    "id": next_p_id,
                                    "categoria": np_cat,
                                    "concepte": np_conc.strip(),
                                    "import": float(np_imp)
                                })
                                curr_v["despeses_previstes"] = partides
                                curr_v["pressupost"] = sum(float(x.get("import", 0)) for x in partides)
                                data["viatges"] = viatges
                                _save_viatges_data(data)
                                st.rerun()
                            else:
                                st.error("Introdueix un concepte i un import major que 0.")

            # COLUMNA DRETA: DESPESES REALS DEL MÒDUL ECONÒMIC
            with col_reals:
                st.markdown("##### 💳 Despeses Reals del Mòdul Econòmic")
                st.caption(f"Despeses registrades durant les dates ({curr_v.get('data_inici')} - {curr_v.get('data_fi')}) amb etiqueta `[VACANCES]`:")

                if despeses_reals_viatge:
                    import pandas as pd
                    df_r = pd.DataFrame(despeses_reals_viatge)
                    df_r_show = df_r[["Data", "Concepte", "Categoria", "Import", "Comentari"]].copy()
                    df_r_show.rename(columns={"Import": "Import (€)"}, inplace=True)
                    st.dataframe(df_r_show.style.format({"Import (€)": "{:,.2f} €"}), use_container_width=True, hide_index=True)
                    st.success(f"**Total Real Gastat:** {total_real:,.2f} € ({len(despeses_reals_viatge)} moviments)")
                else:
                    st.info("Encara no s'han trobat despeses reals associades a aquest viatge. Quan afegeixis moviments al Mòdul Econòmic marcant la casella **'Compra de viatge / vacances'**, apareixeran automàticament aquí.")
                    
                    if df_desp_all is not None and not df_desp_all.empty and v_dini and v_dfi:
                        with st.expander("🔍 Cercar totes les despeses reals ocorregudes en aquestes dates"):
                            totes_en_dates = []
                            for _, r in df_desp_all.iterrows():
                                try:
                                    rd = datetime.strptime(str(r.get("Data", "")).strip(), "%d/%m/%Y").date()
                                    if v_dini <= rd <= v_dfi:
                                        ic = 0.0
                                        for c in ["Import càrrec", "Import crrec", "Import carrec"]:
                                            if c in r and pd.notna(r[c]):
                                                ic = float(str(r[c]).replace(",", ".").replace("€", "").strip())
                                                break
                                        if ic > 0:
                                            totes_en_dates.append({
                                                "Data": str(r.get("Data", "")),
                                                "Concepte": str(r.get("Idconcepte", "")),
                                                "Categoria": str(r.get("Idcategoria", "")),
                                                "Import (€)": ic,
                                                "Comentari": str(r.get("Comentari", ""))
                                            })
                                except Exception:
                                    pass
                            if totes_en_dates:
                                df_totes = pd.DataFrame(totes_en_dates)
                                st.dataframe(df_totes.style.format({"Import (€)": "{:,.2f} €"}), use_container_width=True, hide_index=True)
                                st.caption(f"S'han trobat {len(totes_en_dates)} moviments durant les dates del viatge ({sum(x['Import (€)'] for x in totes_en_dates):,.2f} €).")
                            else:
                                st.caption("No hi ha cap moviment registrat en aquest rang de dates al Mòdul Econòmic.")

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
