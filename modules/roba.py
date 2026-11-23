import streamlit as st
import json
import os

DATA_FILE = "data/roba.json"

def _load_roba_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "peces": [
            {
                "id": 1,
                "nom": "Anorac tèrmic impermeable",
                "propietari": "Tota la família",
                "categoria": "🧥 Jaquetes & Abrics",
                "estacio": "Hivern",
                "estat": "Armari actiu",
                "color": "Blau marí",
                "ubicacio": "Armari rebedor",
                "talla": "L"
            },
            {
                "id": 2,
                "nom": "Botes de muntanya Gore-Tex",
                "propietari": "Enric",
                "categoria": "👟 Calçat",
                "estacio": "Tot l'any",
                "estat": "Armari actiu",
                "color": "Marró",
                "ubicacio": "Sabater passadís",
                "talla": "43"
            },
            {
                "id": 3,
                "nom": "Roba d'estiu i banyadors",
                "propietari": "Familiar",
                "categoria": "👕 Samarretes & Tops",
                "estacio": "Estiu",
                "estat": "Guardat canapè / traster",
                "color": "Varis",
                "ubicacio": "Caixa Canapè 2",
                "talla": "M / L"
            }
        ],
        "talles": [
            {"membre": "Enric", "samarreta": "L / XL", "pantalo": "44", "calcat": "43", "jaqueta": "L", "notes": "Prefereix cotó 100%"},
            {"membre": "Isabel", "samarreta": "M", "pantalo": "40 / 42", "calcat": "38", "jaqueta": "M", "notes": "Calçat ample"}
        ]
    }

def _save_roba_data(data):
    os.makedirs("data", exist_ok=True)
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error desant dades de roba: {e}")
        return False

def render():
    try:
        from modules.avatar_widget import render_header_with_avatar
        render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>🧥 Gestió de Roba i Armari</h2>", "roba")
    except Exception:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>🧥 Gestió de Roba i Armari</h2>", unsafe_allow_html=True)

    data = _load_roba_data()
    peces = data.get("peces", [])
    talles = data.get("talles", [])

    # Mètriques superiors
    total_peces = len(peces)
    actives = sum(1 for p in peces if "actiu" in p.get("estat", "").lower())
    guardades = sum(1 for p in peces if "guardat" in p.get("estat", "").lower())
    categories_cnt = len({p.get("categoria") for p in peces})

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("🧥 Total Peces Registrades", total_peces)
    with col_m2:
        st.metric("🚪 A l'Armari Actiu", actives)
    with col_m3:
        st.metric("📦 Guardades (Canvi Estació)", guardades)
    with col_m4:
        st.metric("👥 Fitxes de Talles", len(talles))

    st.write("")
    tab1, tab2, tab3, tab4 = st.tabs(["🚪 Armari i Inventari", "🍂 Canvi d'Estació", "📏 Talles Familiars", "➕ Afegir Peça"])

    # TAB 1: ARMARI I INVENTARI
    with tab1:
        st.markdown("<h4 style='color:#f39c12;'>Inventari de Roba de la Llar</h4>", unsafe_allow_html=True)
        col_f1, col_f2 = st.columns([6, 6])
        with col_f1:
            cat_list = ["Totes les categories"] + sorted(list({p.get("categoria", "Altres") for p in peces}))
            sel_cat = st.selectbox("Filtrar per categoria:", cat_list, key="sel_roba_cat")
        with col_f2:
            est_list = ["Tots els estats", "🚪 Només Armari actiu", "📦 Només Guardat (Canapè/Traster)"]
            sel_est = st.selectbox("Filtrar per ubicació:", est_list, key="sel_roba_est")

        filtrades = peces
        if sel_cat != "Totes les categories":
            filtrades = [p for p in filtrades if p.get("categoria") == sel_cat]
        if "Armari actiu" in sel_est:
            filtrades = [p for p in filtrades if "actiu" in p.get("estat", "").lower()]
        elif "Guardat" in sel_est:
            filtrades = [p for p in filtrades if "guardat" in p.get("estat", "").lower()]

        if not filtrades:
            st.info("No s'ha trobat cap peça amb els filtres seleccionats.")
        else:
            for idx, p in enumerate(filtrades):
                with st.container():
                    col_p, col_b = st.columns([8.5, 1.5], vertical_alignment="center")
                    with col_p:
                        color_border = "#22c55e" if "actiu" in p.get("estat", "").lower() else "#eab308"
                        st.markdown(f"""
                        <div style="background:#1e293b; border-left:4px solid {color_border}; border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:1.05rem; font-weight:700; color:#f8fafc;">{p.get('nom')}</span>
                                <span style="font-size:0.75rem; background:#334155; color:#38bdf8; padding:2px 8px; border-radius:10px;">{p.get('talla', '—')}</span>
                            </div>
                            <div style="font-size:0.85rem; color:#94a3b8; margin-top:4px;">
                                📁 <b>{p.get('categoria', '—')}</b> &nbsp;|&nbsp; 👤 <b>Per a:</b> {p.get('propietari', '—')} &nbsp;|&nbsp; 🎨 <b>Color:</b> {p.get('color', '—')}
                            </div>
                            <div style="font-size:0.83rem; color:#cbd5e1; margin-top:3px;">
                                📍 <b>Ubicació:</b> {p.get('ubicacio', '—')} &nbsp;|&nbsp; 🌤️ <b>Estació:</b> {p.get('estacio', 'Tot l\'any')} &nbsp;|&nbsp; 📌 <i>{p.get('estat', 'Armari actiu')}</i>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_b:
                        if st.button("🗑️", key=f"del_peça_{p.get('id', idx)}", help="Eliminar peça"):
                            peces = [item for item in peces if item.get("id") != p.get("id")]
                            data["peces"] = peces
                            _save_roba_data(data)
                            st.rerun()

    # TAB 2: CANVI D'ESTACIÓ
    with tab2:
        st.markdown("<h4 style='color:#f39c12;'>🍂 Organització de Temporada (Armari vs Canapè / Traster)</h4>", unsafe_allow_html=True)
        st.caption("Gestiona ràpidament el canvi d'armari d'estiu a hivern o viceversa.")

        col_es1, col_es2 = st.columns(2)
        with col_es1:
            st.markdown("##### 🚪 Peces Actualment a l'Armari")
            a_armari = [p for p in peces if "actiu" in p.get("estat", "").lower()]
            for p in a_armari:
                c_t, c_btn = st.columns([7, 3], vertical_alignment="center")
                with c_t:
                    st.write(f"• **{p.get('nom')}** ({p.get('propietari')})")
                with c_btn:
                    if st.button("📦 Guardar", key=f"guardar_{p['id']}", use_container_width=True):
                        p["estat"] = "Guardat canapè / traster"
                        data["peces"] = peces
                        _save_roba_data(data)
                        st.rerun()

        with col_es2:
            st.markdown("##### 📦 Peces Guardades a Caixes / Canapè")
            a_guardat = [p for p in peces if "guardat" in p.get("estat", "").lower()]
            for p in a_guardat:
                c_t, c_btn = st.columns([7, 3], vertical_alignment="center")
                with c_t:
                    st.write(f"• **{p.get('nom')}** ({p.get('ubicacio')})")
                with c_btn:
                    if st.button("🚪 Treure", key=f"treure_{p['id']}", use_container_width=True):
                        p["estat"] = "Armari actiu"
                        data["peces"] = peces
                        _save_roba_data(data)
                        st.rerun()

    # TAB 3: TALLES FAMILIARS
    with tab3:
        st.markdown("<h4 style='color:#f39c12;'>📏 Guia de Talles Familiars</h4>", unsafe_allow_html=True)
        st.caption("Ideal per consultar ràpidament des del mòbil quan vagis a comprar roba o sabates per a la família.")

        if talles:
            import pandas as pd
            df_t = pd.DataFrame(talles)
            df_t.rename(columns={
                "membre": "Membre",
                "samarreta": "Samarreta / Top",
                "pantalo": "Pantalons",
                "calcat": "Calçat",
                "jaqueta": "Jaqueta / Abric",
                "notes": "Observacions"
            }, inplace=True)
            st.dataframe(df_t, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("###### ➕ Afegir / Actualitzar fitxa de talles d'un membre:")
        with st.form("form_talles"):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                t_nom = st.text_input("Nom del familiar", placeholder="Ex: Enric, Isabel...", key="t_nom")
                t_sam = st.text_input("Talla de Samarreta", placeholder="Ex: M, L, XL...", key="t_sam")
                t_pan = st.text_input("Talla de Pantalons", placeholder="Ex: 40, 42, 44...", key="t_pan")
            with col_t2:
                t_sab = st.text_input("Talla de Sabata / Calçat", placeholder="Ex: 38, 42, 43...", key="t_sab")
                t_jaq = st.text_input("Talla de Jaqueta", placeholder="Ex: M, L...", key="t_jaq")
                t_obs = st.text_input("Observacions", placeholder="Prefereix cotó, peus amples...", key="t_obs")

            if st.form_submit_button("💾 Desar Fitxa de Talles", type="primary", use_container_width=True):
                if t_nom.strip():
                    # Update or add
                    existing = next((item for item in talles if item.get("membre", "").lower() == t_nom.strip().lower()), None)
                    if existing:
                        existing["samarreta"] = t_sam.strip()
                        existing["pantalo"] = t_pan.strip()
                        existing["calcat"] = t_sab.strip()
                        existing["jaqueta"] = t_jaq.strip()
                        existing["notes"] = t_obs.strip()
                    else:
                        talles.append({
                            "membre": t_nom.strip(),
                            "samarreta": t_sam.strip(),
                            "pantalo": t_pan.strip(),
                            "calcat": t_sab.strip(),
                            "jaqueta": t_jaq.strip(),
                            "notes": t_obs.strip()
                        })
                    data["talles"] = talles
                    _save_roba_data(data)
                    st.success(f"✅ Talles de {t_nom} desades correctament!")
                    st.rerun()
                else:
                    st.error("Si us plau, indica el nom del familiar.")

    # TAB 4: NOVA PEÇA
    with tab4:
        st.markdown("<h4 style='color:#f39c12;'>➕ Registrar Nova Peça de Roba</h4>", unsafe_allow_html=True)
        if "roba_saved_msg" in st.session_state:
            st.success(st.session_state.pop("roba_saved_msg"))

        with st.form("form_nova_peça", clear_on_submit=True):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                r_nom = st.text_input("Descripció de la peça", placeholder="Ex: Jaqueta impermeable verda, texans...", key="r_nom")
                r_prop = st.text_input("Per a qui és? (Propietari)", placeholder="Ex: Enric, Isabel, Familiar...", key="r_prop")
                r_cat = st.selectbox("Categoria", ["👕 Samarretes & Tops", "👖 Pantalons & Bermudes", "🧥 Jaquetes & Abrics", "👟 Calçat", "🩲 Roba Interior", "🏃 Esport", "👗 Vestits", "🎒 Complements & Altres"], key="r_cat")
                r_talla = st.text_input("Talla", placeholder="Ex: L, 42, 43...", key="r_talla")
            with col_r2:
                r_estat = st.selectbox("Estat actual", ["Armari actiu", "Guardat canapè / traster"], key="r_estat")
                r_estacio = st.selectbox("Estació recomanada", ["Tot l'any", "Primavera / Estiu", "Tardor / Hivern"], key="r_estacio")
                r_color = st.text_input("Color principal", placeholder="Ex: Blau, Negre, Gris...", key="r_color")
                r_ubic = st.text_input("Ubicació / Calaix / Armari", placeholder="Ex: Armari habitació, Caixa 1 canapè...", key="r_ubic")

            if st.form_submit_button("💾 Desar Peça de Roba", type="primary", use_container_width=True):
                if r_nom.strip():
                    next_pid = max([p.get("id", 0) for p in peces], default=0) + 1
                    peces.append({
                        "id": next_pid,
                        "nom": r_nom.strip(),
                        "propietari": r_prop.strip() or "General",
                        "categoria": r_cat,
                        "talla": r_talla.strip(),
                        "estat": r_estat,
                        "estacio": r_estacio,
                        "color": r_color.strip(),
                        "ubicacio": r_ubic.strip()
                    })
                    data["peces"] = peces
                    _save_roba_data(data)
                    for k in ["r_nom", "r_prop", "r_talla", "r_color", "r_ubic"]:
                        if k in st.session_state:
                            st.session_state[k] = ""
                    st.session_state["roba_saved_msg"] = f"✅ Peça '{r_nom.strip()}' desada amb èxit!"
                    st.rerun()
                    _save_roba_data(data)
                    st.success("✅ Peça de roba afegida a l'armari!")
                    st.rerun()
                else:
                    st.error("Si us plau, indica com a mínim la descripció de la peça.")
