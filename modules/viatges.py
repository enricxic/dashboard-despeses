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
        from core.db import fetch_table_fast
        _, df = fetch_table_fast('despeses')
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
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

def _normalitzar_categoria_viatge(cat_str, concepte_str=""):
    """Agrupa categories de la BD en categories estàndard de viatge."""
    c = (str(cat_str) + " " + str(concepte_str)).lower()
    if any(k in c for k in ["super", "menjar", "aliment", "compra", "mercat", "fleca", "fruita", "carn", "peix", "pa"]):
        return "🍽️ Menjar / Supermercat"
    elif any(k in c for k in ["gasolina", "carburant", "transport", "peatge", "parking", "tren", "avio", "vol", "taxi"]):
        return "🚗 Transport / Carburant"
    elif any(k in c for k in ["hotel", "apartament", "allotj", "casa", "camping"]):
        return "🏨 Allotjament"
    elif any(k in c for k in ["restaurant", "bar", "terrassa", "oci", "visita", "museu", "tarda", "sopar", "dinar"]):
        return "🎟️ Restauració i Oci"
    return "🎒 Altres / Compres"

def _get_blocs_vacances_disponibles():
    """Retorna una llista de blocs de vacances detectats a la BD per ajudar l'usuari a acotar."""
    df = _get_despeses_reals_df()
    if df is None or df.empty:
        return []
    import pandas as pd
    df_vac = df[df['Comentari'].astype(str).str.contains(r'\[VACANCES\]|vacances', case=False, na=False, regex=True)].copy()
    if df_vac.empty:
        return []

    def _parse_imp(x):
        try: return float(str(x).replace(',', '.').replace('€', '').strip())
        except Exception: return 0.0

    imp_col = next((c for c in ['Import càrrec', 'Import crrec', 'Import carrec'] if c in df_vac.columns), 'Import càrrec')
    df_vac['imp_clean'] = df_vac[imp_col].apply(_parse_imp)

    def _parse_dt(d_str):
        try: return datetime.strptime(str(d_str).strip(), '%d/%m/%Y').date()
        except Exception:
            try: return pd.to_datetime(d_str).date()
            except Exception: return None

    df_vac['dt_obj'] = df_vac['Data'].apply(_parse_dt)
    df_vac = df_vac.dropna(subset=['dt_obj']).sort_values('dt_obj')
    if df_vac.empty:
        return []
    
    # Agrupar per blocs si la distància és <= 7 dies
    blocs = []
    curr_bloc = []
    for _, r in df_vac.iterrows():
        if not curr_bloc:
            curr_bloc.append(r)
        else:
            diff = (r['dt_obj'] - curr_bloc[-1]['dt_obj']).days
            if diff <= 7:
                curr_bloc.append(r)
            else:
                blocs.append(pd.DataFrame(curr_bloc))
                curr_bloc = [r]
    if curr_bloc:
        blocs.append(pd.DataFrame(curr_bloc))
        
    res = []
    for b in reversed(blocs):
        d_min = b['dt_obj'].min()
        d_max = b['dt_obj'].max()
        dies = max(1, (d_max - d_min).days + 1)
        tot = b['imp_clean'].sum()
        movs_pos = len(b[b['imp_clean'] > 0])
        res.append({
            "d_inici": d_min,
            "d_fi": d_max,
            "dies": dies,
            "total": tot,
            "moviments": movs_pos,
            "label": f"🏖️ {d_min.strftime('%d/%m/%Y')} al {d_max.strftime('%d/%m/%Y')} ({dies} dies · {movs_pos} moviments · {tot:,.2f} €)"
        })
    return res

def _estimar_pressupost_historic(destinacio="", d_inici=None, d_fi=None, ref_d_inici=None, ref_d_fi=None):
    """Analitza l'històric de despeses de [VACANCES] per estimar el pressupost del viatge."""
    df = _get_despeses_reals_df()
    if df is None or df.empty:
        return None
    import pandas as pd
    df_vac = df[df['Comentari'].astype(str).str.contains(r'\[VACANCES\]|vacances', case=False, na=False, regex=True)].copy()
    if df_vac.empty:
        return None

    def _parse_imp(val):
        if pd.isna(val) or val is None: return 0.0
        try:
            return float(str(val).replace(',', '.').replace('€', '').strip())
        except Exception:
            return 0.0

    imp_col = next((c for c in ["Import càrrec", "Import crrec", "Import carrec"] if c in df_vac.columns), "Import càrrec")
    df_vac['imp_clean'] = df_vac[imp_col].apply(_parse_imp)
    df_vac = df_vac[df_vac['imp_clean'] > 0].copy()

    def _parse_dt(d_str):
        try:
            return datetime.strptime(str(d_str).strip(), "%d/%m/%Y").date()
        except Exception:
            try:
                return pd.to_datetime(d_str).date()
            except Exception:
                return None

    df_vac['dt_obj'] = df_vac['Data'].apply(_parse_dt)
    df_vac = df_vac.dropna(subset=['dt_obj']).sort_values('dt_obj')
    if df_vac.empty:
        return None

    # Detectar blocs continus de vacances
    blocs = []
    curr_bloc = []
    for _, r in df_vac.iterrows():
        if not curr_bloc:
            curr_bloc.append(r)
        else:
            diff = (r['dt_obj'] - curr_bloc[-1]['dt_obj']).days
            if diff <= 7:
                curr_bloc.append(r)
            else:
                blocs.append(pd.DataFrame(curr_bloc))
                curr_bloc = [r]
    if curr_bloc:
        blocs.append(pd.DataFrame(curr_bloc))

    sub_df = pd.DataFrame()
    # 1. Si s'han especificat dates de referència explícites per acotar
    if ref_d_inici and ref_d_fi:
        sub_df = df_vac[(df_vac['dt_obj'] >= ref_d_inici) & (df_vac['dt_obj'] <= ref_d_fi)]

    # 2. Si no, buscar quin bloc de vacances conté referències a la destinació
    if sub_df.empty:
        dest_cleaned = destinacio.strip().lower()
        if dest_cleaned:
            stopwords = {"de", "del", "a", "la", "el", "les", "els", "al", "als", "per", "en", "viatge"}
            words = [w for w in dest_cleaned.replace("'", " ").replace("-", " ").split() if len(w) > 2 and w not in stopwords]
            matching_block = None
            for b in reversed(blocs):
                b_text = (b['Comentari'].astype(str) + " " + b['Idconcepte'].astype(str)).str.lower()
                full_text = " ".join(b_text)
                if any(w in full_text for w in words):
                    matching_block = b
                    break
            if matching_block is not None:
                sub_df = matching_block

    # 3. Si no s'ha trobat cap bloc coincident per paraula, prenem l'últim bloc complet detectat
    if sub_df.empty:
        if blocs:
            sub_df = blocs[-1]
        else:
            ultim_dt = df_vac['dt_obj'].max()
            sub_df = df_vac[df_vac['dt_obj'] >= (ultim_dt - pd.Timedelta(days=25))]

    if sub_df.empty:
        sub_df = df_vac

    min_d = sub_df['dt_obj'].min()
    max_d = sub_df['dt_obj'].max()
    dies_ref = max(1, (max_d - min_d).days + 1)
    total_ref = sub_df['imp_clean'].sum()
    mitjana_dia = total_ref / dies_ref

    if d_inici and d_fi:
        dies_nou = max(1, (d_fi - d_inici).days + 1)
    else:
        dies_nou = dies_ref

    total_estimat = round(mitjana_dia * dies_nou, 2)

    sub_df['cat_norm'] = sub_df.apply(lambda r: _normalitzar_categoria_viatge(r.get('Idcategoria', ''), r.get('Idconcepte', '')), axis=1)
    cat_totals = sub_df.groupby('cat_norm')['imp_clean'].sum().to_dict()

    partides_suggerides = []
    pid = 1
    for c_nom, c_val in cat_totals.items():
        pct = c_val / total_ref if total_ref > 0 else 0
        partida_imp = round(total_estimat * pct, 2)
        if partida_imp > 0:
            partides_suggerides.append({
                "id": pid,
                "categoria": c_nom,
                "concepte": f"Previsió {c_nom.split()[-1]} ({dies_nou} dies)",
                "import": partida_imp
            })
            pid += 1

    return {
        "total_estimat": total_estimat,
        "mitjana_dia": mitjana_dia,
        "dies_nou": dies_nou,
        "dies_ref": dies_ref,
        "total_ref": total_ref,
        "dt_ref_inici": min_d,
        "dt_ref_fi": max_d,
        "periode_ref": f"{min_d.strftime('%d/%m/%Y')} al {max_d.strftime('%d/%m/%Y')}",
        "partides": partides_suggerides,
        "num_moviments": len(sub_df)
    }

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
        st.markdown("<h4 style='color:#f39c12;'>💰 Pressupost Previst & Despeses Reals per Categories</h4>", unsafe_allow_html=True)
        st.caption("Confronta el pressupost previst amb les despeses reals registrades al Mòdul Econòmic (etiqueta [VACANCES]), agrupades i desglossades per categories.")

        if not viatges:
            st.info("No hi ha viatges planificats. Afegeix-ne un a la pestanya '➕ Nou Viatge' per començar a gestionar el pressupost.")
        else:
            v_noms = [f"{v.get('destinacio', 'Sense nom')} ({v.get('data_inici', '')} al {v.get('data_fi', '')})" for v in viatges]
            sel_idx = 0
            if "sel_viatge_pressupost_idx" in st.session_state and st.session_state["sel_viatge_pressupost_idx"] < len(viatges):
                sel_idx = st.session_state["sel_viatge_pressupost_idx"]

            sel_v_str = st.selectbox("Selecciona el viatge a consultar o gestionar:", v_noms, index=sel_idx, key="sel_viatge_press_box")
            curr_v_idx = v_noms.index(sel_v_str) if sel_v_str in v_noms else 0
            st.session_state["sel_viatge_pressupost_idx"] = curr_v_idx
            curr_v = viatges[curr_v_idx]

            try:
                v_dini = datetime.strptime(curr_v.get("data_inici", ""), "%Y-%m-%d").date()
                v_dfi = datetime.strptime(curr_v.get("data_fi", ""), "%Y-%m-%d").date()
            except Exception:
                v_dini = date.today()
                v_dfi = date.today()

            # Panell d'acotació per dates per a la cerca i auto-estimació
            with st.expander("⚙️ Opcions avançades: Acotar dates de referència o confrontació", expanded=False):
                st.caption("A vegades s'han fet molts viatges al mateix lloc o no es recorda el nom exacte. Aquí pots acotar per dates el període a analitzar:")
                blocs_disp = _get_blocs_vacances_disponibles()
                bloc_labels = ["✨ Automàtic (Segons destinació o últim viatge)"] + [b["label"] for b in blocs_disp] + ["📆 Dates manuals personalitzades"]
                
                sel_b_str = st.selectbox("Període de vacances de referència a la BD:", bloc_labels, key=f"sel_bloc_ref_{curr_v['id']}")
                
                col_ref_d1, col_ref_d2 = st.columns(2)
                d_ref_ini_calc = v_dini
                d_ref_fi_calc = v_dfi
                
                if sel_b_str.startswith("🏖️"):
                    idx_b = bloc_labels.index(sel_b_str) - 1
                    b_sel = blocs_disp[idx_b]
                    d_ref_ini_calc = b_sel["d_inici"]
                    d_ref_fi_calc = b_sel["d_fi"]
                
                with col_ref_d1:
                    d_confront_ini = st.date_input("Data inici confrontació / referència", value=d_ref_ini_calc, format="DD/MM/YYYY", key=f"d_confront_ini_{curr_v['id']}")
                with col_ref_d2:
                    d_confront_fi = st.date_input("Data fi confrontació / referència", value=d_ref_fi_calc, format="DD/MM/YYYY", key=f"d_confront_fi_{curr_v['id']}")

                if st.button("💡 Auto-generar partides a partir d'aquestes dates", key=f"btn_auto_press_custom_{curr_v['id']}", use_container_width=True):
                    est = _estimar_pressupost_historic(curr_v.get("destinacio", ""), v_dini, v_dfi, d_confront_ini, d_confront_fi)
                    if est and est.get("partides"):
                        curr_v["despeses_previstes"] = est["partides"]
                        curr_v["pressupost"] = est["total_estimat"]
                        data["viatges"] = viatges
                        _save_viatges_data(data)
                        st.session_state["flash_auto_press"] = f"✅ S'han generat {len(est['partides'])} partides ({est['total_estimat']:,.2f} €) a partir de les dates acotades ({d_confront_ini.strftime('%d/%m/%Y')} al {d_confront_fi.strftime('%d/%m/%Y')})!"
                        st.rerun()
                    else:
                        st.warning("No s'han trobat despeses en aquest rang de dates per auto-generar el pressupost.")

            if "flash_auto_press" in st.session_state:
                st.success(st.session_state.pop("flash_auto_press"))

            # Inicialitzar partides previstes si no n'hi ha
            if "despeses_previstes" not in curr_v or not isinstance(curr_v["despeses_previstes"], list):
                curr_v["despeses_previstes"] = []
                p_init = float(curr_v.get("pressupost", 0))
                if p_init > 0:
                    curr_v["despeses_previstes"].append({
                        "id": 1,
                        "categoria": "🏨 Allotjament",
                        "concepte": f"Estimació {curr_v.get('allotjament', 'Allotjament')}",
                        "import": round(p_init * 0.45, 2)
                    })
                    curr_v["despeses_previstes"].append({
                        "id": 2,
                        "categoria": "🚗 Transport / Carburant",
                        "concepte": f"Transport ({curr_v.get('transport', 'General')})",
                        "import": round(p_init * 0.25, 2)
                    })
                    curr_v["despeses_previstes"].append({
                        "id": 3,
                        "categoria": "🍽️ Menjar / Supermercat",
                        "concepte": "Compres súper i àpats",
                        "import": round(p_init * 0.30, 2)
                    })
                    data["viatges"] = viatges
                    _save_viatges_data(data)

            partides = curr_v["despeses_previstes"]
            total_previst = sum(float(p.get("import", 0)) for p in partides)
            if total_previst == 0 and float(curr_v.get("pressupost", 0)) > 0:
                total_previst = float(curr_v.get("pressupost", 0))

            # Recuperar i classificar despeses reals del Mòdul Econòmic
            # S'utilitzen les dates acotades si s'han definit a la sessió
            f_ini_eval = st.session_state.get(f"d_confront_ini_{curr_v['id']}", v_dini)
            f_fi_eval = st.session_state.get(f"d_confront_fi_{curr_v['id']}", v_dfi)

            df_desp_all = _get_despeses_reals_df()
            despeses_reals_viatge = []

            if df_desp_all is not None and not df_desp_all.empty and f_ini_eval and f_fi_eval:
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
                    in_range = (f_ini_eval <= row_date <= f_fi_eval)

                    if (in_range and is_vacances) or (is_dest_mention and in_range):
                        imp_carg = 0.0
                        for col_c in ["Import càrrec", "Import crrec", "Import carrec", "import_carrec"]:
                            if col_c in row and pd.notna(row[col_c]):
                                try:
                                    imp_carg = float(str(row[col_c]).replace(",", ".").replace("€", "").strip())
                                    break
                                except Exception:
                                    pass
                        if imp_carg > 0:
                            cat_norm = _normalitzar_categoria_viatge(row.get("Idcategoria", ""), row.get("Idconcepte", ""))
                            despeses_reals_viatge.append({
                                "Data": d_str,
                                "Concepte": str(row.get("Idconcepte", "")),
                                "Categoria_BD": str(row.get("Idcategoria", "")),
                                "Categoria": cat_norm,
                                "Banc": str(row.get("Banc", "")),
                                "FormaPago": str(row.get("FormaPago", "")),
                                "Import": imp_carg,
                                "Comentari": comentari_txt,
                                "row_date": row_date
                            })

            total_real = sum(r["Import"] for r in despeses_reals_viatge)
            diferencia = total_previst - total_real
            pct_consumit = (total_real / total_previst * 100) if total_previst > 0 else 0

            # RESUM SUPERIOR I BALANÇ GLOBAL
            st.markdown(f"##### 📊 Balanç Global: **{curr_v.get('destinacio')}**")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                st.metric("💶 Total Pressupostat (Previst)", f"{total_previst:,.2f} €")
            with col_b2:
                st.metric("💳 Despesa Real Acumulada", f"{total_real:,.2f} €", delta=f"{pct_consumit:.1f}% consumit", delta_color="inverse")
            with col_b3:
                color_dif = "normal" if diferencia >= 0 else "inverse"
                st.metric("⚖️ Romanent / Desviació", f"{diferencia:,.2f} €", delta="Dins del pressupost" if diferencia >= 0 else "Superat", delta_color=color_dif)

            prog_val = min(1.0, max(0.0, total_real / total_previst)) if total_previst > 0 else 0.0
            st.progress(prog_val, text=f"Progrés de la despesa: {total_real:,.2f} € de {total_previst:,.2f} € ({pct_consumit:.1f}%)")

            st.write("")
            st.markdown("---")

            # AGRUPACIÓ I DESGLOSSAMENT PER CATEGORIES
            st.markdown("#### 📂 Desglossament i Comparativa per Categories")
            st.caption("Compara la previsió de cada categoria amb les despeses reals extretes del Mòdul Econòmic.")

            CATEGORIES_ESTANDARD = [
                "🍽️ Menjar / Supermercat",
                "🚗 Transport / Carburant",
                "🏨 Allotjament",
                "🎟️ Restauració i Oci",
                "🎒 Altres / Compres"
            ]

            cat_summary = []
            for c_nom in CATEGORIES_ESTANDARD:
                p_items = [p for p in partides if _normalitzar_categoria_viatge(p.get("categoria", ""), p.get("concepte", "")) == c_nom]
                r_items = [r for r in despeses_reals_viatge if r.get("Categoria") == c_nom]

                c_prev = sum(float(x.get("import", 0)) for x in p_items)
                c_real = sum(float(x.get("Import", 0)) for x in r_items)

                if c_prev > 0 or c_real > 0:
                    c_dif = c_prev - c_real
                    c_pct = (c_real / c_prev * 100) if c_prev > 0 else 0
                    cat_summary.append({
                        "nom": c_nom,
                        "previst": c_prev,
                        "real": c_real,
                        "diferencia": c_dif,
                        "pct": c_pct,
                        "partides": p_items,
                        "reals": r_items
                    })

            if cat_summary:
                import pandas as pd
                df_cat_table = pd.DataFrame([{
                    "Categoria": cs["nom"],
                    "Pressupostat": cs["previst"],
                    "Despesa Real [VACANCES]": cs["real"],
                    "Diferència": cs["diferencia"],
                    "Estat": "🟢 En pressupost" if cs["diferencia"] >= 0 else "🔴 Superat"
                } for cs in cat_summary])

                st.dataframe(
                    df_cat_table.style.format({
                        "Pressupostat": "{:,.2f} €",
                        "Despesa Real [VACANCES]": "{:,.2f} €",
                        "Diferència": "{:,.2f} €"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                st.write("")
                st.markdown("##### 🔍 Detall de Moviments per Categoria")
                for cs in cat_summary:
                    titol_exp = f"{cs['nom']}  —  Previst: {cs['previst']:,.2f} €  |  Real: {cs['real']:,.2f} €  ({cs['diferencia']:+,.2f} €)"
                    with st.expander(titol_exp, expanded=False):
                        c_col_prev, c_col_real = st.columns(2, gap="medium")
                        with c_col_prev:
                            st.markdown("###### 📝 Partides Previstes")
                            if cs["partides"]:
                                for p in cs["partides"]:
                                    st.markdown(f"• **{p.get('concepte')}**: `{float(p.get('import', 0)):,.2f} €`")
                            else:
                                st.caption("Sense partides previstes definides.")

                        with c_col_real:
                            st.markdown(f"###### 💳 Moviments Reals Mòdul Econòmic ({len(cs['reals'])})")
                            if cs["reals"]:
                                for r in cs["reals"]:
                                    banc_info = f"({r.get('Banc')})" if r.get('Banc') else ""
                                    coment_clean = r.get('Comentari', '').replace('[VACANCES]', '').strip()
                                    detall_extra = f" — *{coment_clean}*" if coment_clean else ""
                                    st.markdown(f"• **{r.get('Data')}** | **{r.get('Concepte')}**: `{r.get('Import', 0):,.2f} €` {banc_info}{detall_extra}")
                            else:
                                st.caption("Cap despesa real trobada per a aquesta categoria.")
            else:
                st.info("No s'ha definit cap pressupost per categories ni s'han trobat despeses reals per a aquest viatge.")

            # Formulari per afegir noves partides previstes
            st.write("")
            with st.expander("➕ Afegir / Ampliar Partida Prevista al Pressupost", expanded=False):
                with st.form(f"form_add_partida_{curr_v['id']}", clear_on_submit=True):
                    c_n1, c_n2, c_n3 = st.columns([4, 5, 3], vertical_alignment="bottom")
                    with c_n1:
                        np_cat = st.selectbox("Categoria", CATEGORIES_ESTANDARD, key=f"np_cat_{curr_v['id']}")
                    with c_n2:
                        np_conc = st.text_input("Concepte", placeholder="Ex: Supermercat, Gasolina, Allotjament...", key=f"np_conc_{curr_v['id']}")
                    with c_n3:
                        np_imp = st.number_input("Import (€)", min_value=0.0, step=10.0, value=50.0, key=f"np_imp_{curr_v['id']}")

                    if st.form_submit_button("➕ Afegir Partida", type="primary", use_container_width=True):
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

    # TAB 4: NOU VIATGE
    with tab4:
        st.markdown("<h4 style='color:#f39c12;'>➕ Registrar una Nova Aventura o Escapada</h4>", unsafe_allow_html=True)
        if "viatge_saved_msg" in st.session_state:
            st.success(st.session_state.pop("viatge_saved_msg"))
        if "viatge_estimat_info" in st.session_state:
            st.info(st.session_state.pop("viatge_estimat_info"))

        with st.form("form_nou_viatge", clear_on_submit=False):
            # Fila 1: Destinació i Dates
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_dest = st.text_input("📍 Destinació / Ciutat / Zona", value=st.session_state.get("form_v_dest_val", ""), placeholder="Ex: Roma, La Torre, Pirineus...", key="form_v_dest")
            with col_f2:
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    f_dini = st.date_input("📅 Data d'inici", value=st.session_state.get("form_v_dini_val", date.today()), format="DD/MM/YYYY", key="form_v_dini")
                with col_d2:
                    f_dfi = st.date_input("📅 Data de tornada", value=st.session_state.get("form_v_dfi_val", date.today()), format="DD/MM/YYYY", key="form_v_dfi")

            # Fila 2: País / Regió i Allotjament
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                f_pais = st.text_input("🌍 País / Regió", value=st.session_state.get("form_v_pais_val", ""), placeholder="Ex: Alacant, Itàlia, Illes Balears...", key="form_v_pais")
            with col_g2:
                f_allotj = st.text_input("🏨 Allotjament", value=st.session_state.get("form_v_allotj_val", ""), placeholder="Ex: Hotel, Apartament, Casa Mireia...", key="form_v_allotj")

            # Fila 3: Reordenada: 1) Mitjà de Transport, 2) Botó Estimar per Històric, 3) Valoració de pressupost
            col_m1, col_m2, col_m3 = st.columns([1.2, 1.2, 1.0], vertical_alignment="bottom")
            with col_m1:
                f_transp = st.selectbox("🚗 Mitjà de Transport", ["Cotxe propi", "Avió", "Tren", "Autobús", "Vaixell / Ferri", "Altres"], key="form_v_transp")
            with col_m2:
                btn_est = st.form_submit_button("💡 Estimar per Històric", use_container_width=True, help="Estima el pressupost i activa els camps de dates de referència")
            with col_m3:
                f_press = st.number_input("💶 Valoració de pressupost (€)", min_value=0.0, step=25.0, value=float(st.session_state.get("form_v_press_val", 300.0)), key="form_v_press")

            # Fila 3b: Camps de data inici i fi de referència (s'activen en clicar 'Estimar per Històric')
            if st.session_state.get("activar_dates_ref", False):
                st.caption("⚙️ **Camps de referència activats**: S'ha calculat la despesa amb les dates inferiors. Pots canviar-les per acotar un altre període concret i tornar a prémer '💡 Estimar per Històric'.")
                c_rf1, c_rf2, c_rf3 = st.columns([1.2, 1.2, 1.0], vertical_alignment="bottom")
                with c_rf1:
                    d_ref_i_val = st.date_input("📅 Data inici referència", value=st.session_state.get("ref_dini_custom", date.today()), format="DD/MM/YYYY", key="ref_dini_custom_key")
                with c_rf2:
                    d_ref_f_val = st.date_input("📅 Data final referència", value=st.session_state.get("ref_dfi_custom", date.today()), format="DD/MM/YYYY", key="ref_dfi_custom_key")
                with c_rf3:
                    btn_tancar_ref = st.form_submit_button("✖️ Amagar dates ref.", use_container_width=True)
                    if btn_tancar_ref:
                        st.session_state["activar_dates_ref"] = False
                        st.rerun()

            f_notes = st.text_area("📝 Notes, enllaços o plans a realitzar", value=st.session_state.get("form_v_notes_val", ""), placeholder="Llocs a visitar, restaurants recomanats, reserves...", key="form_v_notes")

            st.write("")
            btn_save_v = st.form_submit_button("💾 Desar Viatge", type="primary", use_container_width=True)

            if btn_est:
                st.session_state["form_v_dest_val"] = f_dest
                st.session_state["form_v_pais_val"] = f_pais
                st.session_state["form_v_dini_val"] = f_dini
                st.session_state["form_v_dfi_val"] = f_dfi
                st.session_state["form_v_allotj_val"] = f_allotj
                st.session_state["form_v_notes_val"] = f_notes
                
                # Activem els camps de data de referència
                st.session_state["activar_dates_ref"] = True

                # Si ja estaven actius a la sessió i l'usuari els ha tocat, agafem aquests
                d_custom_i = st.session_state.get("ref_dini_custom_key", None)
                d_custom_f = st.session_state.get("ref_dfi_custom_key", None)

                est = _estimar_pressupost_historic(f_dest, f_dini, f_dfi, d_custom_i, d_custom_f)
                if est:
                    st.session_state["form_v_press"] = float(est["total_estimat"])
                    st.session_state["form_v_press_val"] = float(est["total_estimat"])
                    st.session_state["form_v_partides_calc"] = est["partides"]
                    if "dt_ref_inici" in est and "dt_ref_fi" in est:
                        st.session_state["ref_dini_custom"] = est["dt_ref_inici"]
                        st.session_state["ref_dfi_custom"] = est["dt_ref_fi"]
                    st.session_state["viatge_estimat_info"] = f"💡 Estimació calculada: **{est['total_estimat']:,.2f} €** per a {est['dies_nou']} dies (~{est['mitjana_dia']:,.2f} €/dia), basat en el període de referència **{est['periode_ref']}** ({est['num_moviments']} moviments registrats amb [VACANCES])."
                    st.rerun()
                else:
                    st.warning("No s'han trobat prous despeses anteriors amb [VACANCES] en aquestes dates per generar una estimació.")

            if btn_save_v:
                if f_dest.strip():
                    next_vid = max([v.get("id", 0) for v in viatges], default=0) + 1
                    partides_inicials = st.session_state.get("form_v_partides_calc", [])
                    if not partides_inicials and float(f_press) > 0:
                        partides_inicials = [
                            {"id": 1, "categoria": "🏨 Allotjament", "concepte": f"Allotjament ({f_allotj.strip() or 'Estada'})", "import": round(float(f_press) * 0.45, 2)},
                            {"id": 2, "categoria": "🚗 Transport / Carburant", "concepte": f"Transport ({f_transp})", "import": round(float(f_press) * 0.25, 2)},
                            {"id": 3, "categoria": "🍽️ Menjar / Supermercat", "concepte": "Compres súper i restaurants", "import": round(float(f_press) * 0.30, 2)}
                        ]

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
                        "estat": "Planificat",
                        "despeses_previstes": partides_inicials
                    }
                    viatges.append(nou_viatge)
                    data["viatges"] = viatges
                    _save_viatges_data(data)

                    for k in ["form_v_dest_val", "form_v_pais_val", "form_v_allotj_val", "form_v_notes_val", "form_v_dest", "form_v_pais", "form_v_allotj", "form_v_notes"]:
                        if k in st.session_state:
                            st.session_state[k] = ""
                    st.session_state["form_v_press"] = 300.0
                    st.session_state["form_v_press_val"] = 300.0
                    st.session_state["form_v_dini_val"] = date.today()
                    st.session_state["form_v_dfi_val"] = date.today()
                    st.session_state["activar_dates_ref"] = False
                    for kr in ["ref_dini_custom", "ref_dfi_custom", "ref_dini_custom_key", "ref_dfi_custom_key"]:
                        if kr in st.session_state:
                            del st.session_state[kr]
                    if "form_v_partides_calc" in st.session_state:
                        del st.session_state["form_v_partides_calc"]

                    st.session_state["viatge_saved_msg"] = f"✅ Viatge a '{nou_viatge['destinacio']}' registrat amb èxit!"
                    st.rerun()
                else:
                    st.error("Si us plau, introdueix com a mínim la destinació del viatge.")
