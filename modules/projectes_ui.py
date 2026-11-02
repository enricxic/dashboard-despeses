"""
modules/projectes_ui.py
Interfície d'usuari completa per a la gestió de Projectes d'Obra i Reformes de la llar.
Subpestanyes per a cada projecte:
 1. 📐 Plànol & Fotos
 2. 🧱 Materials & Despeses (Visual amb imatges d'arxiu propi i aportades per la IA)
 3. ⏱️ Fases d'Execució i Progrés
 4. 🤖 Assistent IA d'Obra
Totes les dates es mostren i s'introdueixen en format català/europeu DD/MM/AAAA.
"""

import streamlit as st
import pandas as pd
import base64
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

from core.projectes_manager import (
    load_projectes,
    save_projectes,
    get_projecte,
    add_projecte,
    update_projecte,
    delete_projecte,
    add_material,
    update_material,
    delete_material,
    get_llista_proveidors,
    add_proveidor_memoria,
    add_fase,
    update_fase,
    delete_fase,
    marcar_fase_estat,
    toggle_subtasca,
    add_subtasca_a_fase,
    calcular_progres_projecte,
    add_xat_missatge,
    clear_xat_projecte,
    format_date_cat,
    parse_date_cat,
    to_iso_date
)
from core.ai_projectes import (
    consultar_assistent_obra,
    generar_recomanacions_materials,
    generar_recomanacions_fases,
    generar_imatge_material_url
)
from core.llm_ui import render_ai_selector
from modules.canvas_planol import render_planol_tab

# ==========================================
# UTILITATS D'ESTAT DELS PROJECTES
# ==========================================

def _normalize_project_estat(estat: Any) -> str:
    """Normalitza l'estat del projecte a un dels tres grans blocs: 'Pendent', 'En curs' o 'Finalitzat'."""
    s = str(estat or "").lower().strip()
    if any(k in s for k in ["finalitz", "complet", "acabat"]):
        return "Finalitzat"
    elif any(k in s for k in ["curs", "progr", "fent"]):
        return "En curs"
    else:
        # "pendent", "planificació", "en pausa", "", etc.
        return "Pendent"

def _badge_project_estat(estat: Any) -> str:
    """Retorna la icona visual segons l'estat del projecte."""
    norm = _normalize_project_estat(estat)
    if norm == "Finalitzat":
        return "✅"
    elif norm == "En curs":
        return "🔨"
    return "⏳"

# ==========================================
# DIÀLEGS MODALS DE CONFIRMACIÓ I IMATGES
# ==========================================

@st.dialog("🗑️ Confirmar Eliminació del Projecte")
def confirm_delete_project_dialog(project_id: str, project_nom: str):
    """Diàleg segur i visible per confirmar l'esborrat complet d'un projecte."""
    st.error(f"⚠️ Estàs a punt d'esborrar el projecte: **{project_nom}**")
    st.markdown("Aquesta acció eliminarà permanentment:")
    st.markdown("- El plànol i croquis de l'obra\n- Tota la llista de materials i costos\n- Totes les fases i tasques\n- La galeria fotogràfica de seguiment")
    
    col_del1, col_del2 = st.columns(2)
    with col_del1:
        if st.button("Sí, esborrar definitivament", type="primary", use_container_width=True):
            delete_projecte(project_id)
            st.success("Projecte esborrat correctament!")
            st.rerun()
    with col_del2:
        if st.button("Cancel·lar", use_container_width=True):
            st.rerun()

@st.dialog("🏆 Finalitzar l'Obra")
def dialog_finalitzar_obra(project_id: str, project_nom: str):
    """Diàleg modal que pregunta si la feina està acabada un cop fetes totes les fases."""
    st.balloons()
    st.markdown("### 🎉 Totes les fases estan completades!")
    st.write(f"Has enllestit el 100% de les fases i tasques de: **{project_nom}**.")
    st.markdown("**La feina de l'obra està completament acabada?** Vols donar el projecte per finalitzat?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏆 Sí, marcar com a Finalitzat", type="primary", use_container_width=True):
            update_projecte(project_id, {"estat": "Finalitzat"})
            st.success("Projecte marcat com a Finalitzat!")
            st.rerun()
    with col2:
        if st.button("Encara no, deixar en curs", use_container_width=True):
            st.rerun()

@st.dialog("🧱 Fitxa i Detalls del Material")
def dialog_detall_material(project_id: str, material: Dict[str, Any]):
    """Finestra modal completa amb totes les dades del material: foto, estat, stock, proveïdor i preus."""
    mat_id = material.get("id")
    nom_art = material.get("article", "Material")
    cur_img = material.get("imatge")
    cur_prov = str(material.get("proveidor", "Obramat")).strip() or "Obramat"
    cur_qtt = int(material.get("quantitat", 1) or 1)
    cur_pest = float(material.get("preu_estimat", 0.0) or 0.0)
    cur_preal = float(material.get("preu_real", 0.0) or 0.0)
    cur_stock = bool(material.get("en_stock", False))
    cur_comprat = bool(material.get("comprat", False)) and not cur_stock

    col_img_v, col_dat_v = st.columns([1.2, 1.8])
    with col_img_v:
        if cur_img:
            st.image(cur_img, use_container_width=True)
        else:
            st.markdown("<div style='background:#1e293b; height:180px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:48px; border:2px dashed #475569;'>🧱</div>", unsafe_allow_html=True)
        
        with st.expander("📷 Gestionar Foto", expanded=False):
            t_ia, t_up, t_url = st.tabs(["✨ IA", "📁 Arxiu", "🌐 URL"])
            with t_ia:
                if st.button("🎨 Generar amb IA", type="primary", use_container_width=True, key=f"d_gen_ia_{mat_id}"):
                    with st.spinner("Generant fotografia..."):
                        nova_url = generar_imatge_material_url(nom_art)
                        update_material(project_id, mat_id, {"imatge": nova_url})
                        st.success("Foto IA assignada!")
                        st.rerun()
            with t_up:
                up_f = st.file_uploader("Pujar foto (mòbil/fitxer):", type=["png", "jpg", "jpeg", "webp"], key=f"d_up_f_{mat_id}")
                if st.button("Guardar Foto", use_container_width=True, key=f"d_save_f_{mat_id}"):
                    if up_f:
                        b64 = f"data:image/jpeg;base64,{base64.b64encode(up_f.read()).decode('utf-8')}"
                        update_material(project_id, mat_id, {"imatge": b64})
                        st.success("Foto desada!")
                        st.rerun()
            with t_url:
                in_u = st.text_input("Enllaç imatge:", value=cur_img if (cur_img and cur_img.startswith("http")) else "", key=f"d_url_{mat_id}")
                if st.button("Guardar Enllaç", use_container_width=True, key=f"d_save_u_{mat_id}"):
                    if in_u.strip():
                        update_material(project_id, mat_id, {"imatge": in_u.strip()})
                        st.success("Enllaç desat!")
                        st.rerun()
            if cur_img:
                st.write("")
                if st.button("🗑️ Treure foto", key=f"d_del_img_{mat_id}", use_container_width=True):
                    update_material(project_id, mat_id, {"imatge": None})
                    st.rerun()

    with col_dat_v:
        d_nom = st.text_input("Nom de l'article:", value=nom_art, key=f"d_nom_{mat_id}")
        
        # Proveïdors consolidats amb memòria
        llista_provs = get_llista_proveidors()
        if cur_prov and cur_prov not in llista_provs:
            llista_provs.append(cur_prov)
        
        idx_p = llista_provs.index(cur_prov) if cur_prov in llista_provs else 0
        options_prov_select = llista_provs + ["➕ Afegir un altre proveïdor..."]
        d_prov = st.selectbox("Proveïdor:", options=options_prov_select, index=idx_p, key=f"d_prov_{mat_id}")
        
        nou_prov_custom = None
        if d_prov == "➕ Afegir un altre proveïdor...":
            nou_prov_custom = st.text_input("Escriu el nom del nou proveïdor (es guardarà en memòria):", key=f"d_nou_prov_input_{mat_id}", placeholder="Ex: Bauhaus, Obramat, Bricomart...")
        
        # Estat / Stock seleccionable
        opcions_estat = ["⏳ Pendent de compra", "🛒 Comprat / Ja adquirit", "📦 Ja en stock (a casa / reaprofitat)"]
        default_estat_idx = 0
        if cur_stock:
            default_estat_idx = 2
        elif cur_comprat:
            default_estat_idx = 1
        
        d_estat_sel = st.radio("Estat / Disponibilitat:", options=opcions_estat, index=default_estat_idx, key=f"d_estat_{mat_id}")

    st.divider()

    c_q, c_pest, c_preal = st.columns(3)
    with c_q:
        d_qtt = st.number_input("Quantitat:", min_value=1, value=cur_qtt, step=1, key=f"d_qtt_{mat_id}")
    with c_pest:
        d_pest = st.number_input("Preu total estimat (€):", min_value=0.0, value=cur_pest, step=5.0, key=f"d_pest_{mat_id}")
    with c_preal:
        es_comprat = (d_estat_sel == "🛒 Comprat / Ja adquirit")
        es_stock = (d_estat_sel == "📦 Ja en stock (a casa / reaprofitat)")
        d_preal = st.number_input("Preu pagat real (€):", min_value=0.0, value=0.0 if es_stock else cur_preal, step=5.0, disabled=not es_comprat, key=f"d_preal_{mat_id}")

    st.write("")
    col_save, col_del = st.columns([2, 1])
    with col_save:
        if st.button("💾 Desar Canvis del Material", type="primary", use_container_width=True, key=f"d_save_all_{mat_id}"):
            final_prov = nou_prov_custom.strip() if (d_prov == "➕ Afegir un altre proveïdor..." and nou_prov_custom and nou_prov_custom.strip()) else d_prov
            if nou_prov_custom and nou_prov_custom.strip():
                add_proveidor_memoria(nou_prov_custom.strip())
            
            update_material(project_id, mat_id, {
                "article": d_nom.strip() or nom_art,
                "proveidor": final_prov,
                "quantitat": d_qtt,
                "preu_estimat": d_pest,
                "preu_real": d_preal if es_comprat else 0.0,
                "comprat": es_comprat,
                "en_stock": es_stock
            })
            st.success("Dades actualitzades!")
            st.rerun()

    with col_del:
        if st.button("🗑️ Eliminar aquest Material", use_container_width=True, key=f"d_del_all_{mat_id}"):
            delete_material(project_id, mat_id)
            st.success("Material eliminat.")
            st.rerun()

def dialog_imatge_material(project_id: str, material: Dict[str, Any]):
    """Alias retrocompatible per obrir el diàleg de detalls."""
    dialog_detall_material(project_id, material)

# ==========================================
# RENDERITZACIÓ PRINCIPAL DEL MÒDUL
# ==========================================

def render_projectes_tab(family_names: List[str] = None):
    """Pestanya principal de Projectes d'Obra i Reformes al mòdul de manteniment."""
    projectes = load_projectes()

    if not projectes:
        col_nou, _ = st.columns([1.2, 2.8])
        with col_nou:
            if st.button("➕ Nou Projecte d'Obra", use_container_width=True, type="primary"):
                st.session_state["show_modal_nou_projecte"] = True
        st.info("👋 Encara no hi ha cap projecte creat. Prem **➕ Nou Projecte d'Obra** per començar.")
        if st.session_state.get("show_modal_nou_projecte"):
            _render_modal_nou_projecte()
        return

    # Còmput de projectes per estat per als xips de filtratge
    c_tots = len(projectes)
    c_pend = sum(1 for p in projectes if _normalize_project_estat(p.get("estat")) == "Pendent")
    c_curs = sum(1 for p in projectes if _normalize_project_estat(p.get("estat")) == "En curs")
    c_fin = sum(1 for p in projectes if _normalize_project_estat(p.get("estat")) == "Finalitzat")

    filtre_labels = {
        "Tots": f"Tots ({c_tots})",
        "Pendent": f"⏳ Pendent ({c_pend})",
        "En curs": f"🔨 En curs ({c_curs})",
        "Finalitzat": f"✅ Finalitzat ({c_fin})"
    }

    st.caption("🔍 Filtra els projectes per estat:")
    if hasattr(st, "pills"):
        filtre_estat = st.pills(
            "Filtrar per estat:",
            options=["Tots", "Pendent", "En curs", "Finalitzat"],
            format_func=lambda x: filtre_labels.get(x, x),
            default="Tots",
            key="filtre_estat_projectes",
            label_visibility="collapsed"
        )
    elif hasattr(st, "segmented_control"):
        filtre_estat = st.segmented_control(
            "Filtrar per estat:",
            options=["Tots", "Pendent", "En curs", "Finalitzat"],
            format_func=lambda x: filtre_labels.get(x, x),
            default="Tots",
            key="filtre_estat_projectes",
            label_visibility="collapsed"
        )
    else:
        filtre_estat = st.radio(
            "Filtrar per estat:",
            options=["Tots", "Pendent", "En curs", "Finalitzat"],
            format_func=lambda x: filtre_labels.get(x, x),
            horizontal=True,
            key="filtre_estat_projectes",
            label_visibility="collapsed"
        )

    filtre_actiu = filtre_estat or "Tots"

    # Filtrar projectes segons l'estat seleccionat
    if filtre_actiu != "Tots":
        projectes_filtrats = [p for p in projectes if _normalize_project_estat(p.get("estat")) == filtre_actiu]
    else:
        projectes_filtrats = projectes

    opcions_proj = {
        p["id"]: f"{_badge_project_estat(p.get('estat'))} {p.get('nom', 'Sense títol')} ({p.get('ubicacio', 'Llar')}) — {p.get('estat', 'En curs')}"
        for p in projectes_filtrats
    }

    # Barra superior de selecció de projecte
    col_sel, col_nou = st.columns([3, 1])

    with col_nou:
        st.write("")
        if st.button("➕ Nou Projecte d'Obra", use_container_width=True, type="primary"):
            st.session_state["show_modal_nou_projecte"] = True

    # Comprovar si hi ha projecte seleccionat a la sessió o paràmetres URL
    query_proj = st.query_params.get("proj_id")
    cur_sel = st.session_state.get("select_projecte_actiu")
    default_proj_id = None
    if query_proj and query_proj in opcions_proj:
        default_proj_id = query_proj
    elif cur_sel and cur_sel in opcions_proj:
        default_proj_id = cur_sel
    elif projectes_filtrats:
        default_proj_id = projectes_filtrats[0]["id"]

    # Sanejament de session_state per canvis de filtre
    if "select_projecte_actiu" in st.session_state and st.session_state["select_projecte_actiu"] not in opcions_proj:
        if default_proj_id:
            st.session_state["select_projecte_actiu"] = default_proj_id
        else:
            st.session_state.pop("select_projecte_actiu", None)

    with col_sel:
        if opcions_proj:
            selected_proj_id = st.selectbox(
                "🏗️ Selecciona el Projecte Actiu:",
                options=list(opcions_proj.keys()),
                format_func=lambda x: opcions_proj[x],
                index=list(opcions_proj.keys()).index(default_proj_id) if default_proj_id in opcions_proj else 0,
                key="select_projecte_actiu"
            )
        else:
            selected_proj_id = None
            st.info(f"ℹ️ No hi ha cap projecte amb l'estat **{filtre_actiu}** ({c_tots} en total). Canvia el filtre a 'Tots' per veure'ls.")

    # Modal d'Alta de Nou Projecte
    if st.session_state.get("show_modal_nou_projecte"):
        _render_modal_nou_projecte()

    if not selected_proj_id:
        return

    projecte = get_projecte(selected_proj_id)
    if not projecte:
        st.warning("No s'ha trobat el projecte seleccionat.")
        return

    # Panell de Capçalera i KPIs del Projecte
    _render_projecte_header(projecte)

    # 4 Subpestanyes del Projecte
    subtabs = st.tabs([
        "📐 Plànol & Fotos",
        "🧱 Materials & Despeses",
        "⏱️ Fases d'Execució",
        "🤖 Assistent IA d'Obra"
    ])

    with subtabs[0]:
        render_planol_tab(projecte)

    with subtabs[1]:
        _render_materials_tab(projecte)

    with subtabs[2]:
        _render_fases_tab(projecte)

    with subtabs[3]:
        _render_assistent_ia_tab(projecte)

# ==========================================
# SUBPANELLS DE LA VISTA
# ==========================================

def _render_projecte_header(projecte: Dict[str, Any]):
    """Mostra la informació general, estat, dates (DD/MM/AAAA), mètriques i botó d'esborrar."""
    project_id = projecte["id"]
    progres = calcular_progres_projecte(projecte)

    # Càlculs econòmics
    pressupost_est = float(projecte.get("pressupost_estimat", 0.0) or 0.0)
    materials = projecte.get("materials", [])
    cost_comprat = sum(float(m.get("preu_real", 0.0) or 0.0) for m in materials if m.get("comprat", False) and not m.get("en_stock", False))

    d_inici = format_date_cat(projecte.get("data_inici"))
    d_fi = format_date_cat(projecte.get("data_fi_prevista"))

    with st.container():
        c1, c2, c3, c4 = st.columns([1.8, 0.9, 1.0, 1.3])
        with c1:
            st.markdown(f"### 🔨 {projecte.get('nom', 'Projecte')} <span style='font-size:14px; color:#64748b;'>({projecte.get('ubicacio', '')})</span>", unsafe_allow_html=True)
            if projecte.get("descripcio"):
                st.caption(projecte.get("descripcio"))
        with c2:
            norm_est = _normalize_project_estat(projecte.get("estat", "Pendent"))
            badge_icon = _badge_project_estat(norm_est)
            st.metric("Estat", f"{badge_icon} {projecte.get('estat', norm_est)}", delta=None)
        with c3:
            st.metric("Despesa Real", f"{cost_comprat:.2f} €", delta=f"{pressupost_est - cost_comprat:.2f} € disp." if pressupost_est > 0 else None)
        with c4:
            if d_inici and d_fi:
                st.metric(
                    "Calendari d'Obra",
                    d_inici,
                    delta=f"🏁 Fi: {d_fi}",
                    delta_color="off",
                    help=f"Període planificat: de {d_inici} fins a {d_fi} (format DD/MM/AAAA)"
                )
            elif d_inici:
                st.metric("Inici d'Obra", d_inici, help="Data d'inici prevista (DD/MM/AAAA)")
            elif d_fi:
                st.metric("Fi Prevista", d_fi, help="Data límit prevista (DD/MM/AAAA)")
            else:
                st.metric("Calendari", "Sense dates", help="Pots assignar dates editant el projecte")

        # Barra de progrés global
        st.progress(progres / 100.0, text=f"Progrés de l'obra: {progres}% completat")

    # Botó per editar o eliminar projecte
    with st.expander("⚙️ Opcions del Projecte (Editar dades / Eliminar)"):
        # Fila superior amb acció destacada d'esborrar
        col_hdr_op1, col_hdr_op2 = st.columns([2.5, 1.5])
        with col_hdr_op1:
            st.markdown("**Modificació de les dades bàsiques del projecte:**")
        with col_hdr_op2:
            if st.button("🗑️ Esborrar aquest Projecte", key=f"btn_open_del_{project_id}", type="secondary", use_container_width=True):
                confirm_delete_project_dialog(project_id, projecte.get("nom", "Sense títol"))

        st.divider()

        # Formulari d'edició
        with st.form(f"form_edit_proj_{project_id}"):
            f_nom = st.text_input("Nom del projecte:", value=projecte.get("nom", ""))
            f_ubi = st.text_input("Ubicació a la casa:", value=projecte.get("ubicacio", ""))
            f_desc = st.text_area("Descripció dels treballs:", value=projecte.get("descripcio", ""))
            
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                estats = ["Pendent", "En curs", "Finalitzat"]
                cur_est = _normalize_project_estat(projecte.get("estat", "Pendent"))
                f_estat = st.selectbox("Estat actual:", estats, index=estats.index(cur_est) if cur_est in estats else 0)
            with col_d2:
                p_inici = parse_date_cat(projecte.get("data_inici")) or date.today()
                f_inici = st.date_input("Data inici (DD/MM/AAAA):", value=p_inici, format="DD/MM/YYYY")
            with col_d3:
                p_fi = parse_date_cat(projecte.get("data_fi_prevista")) or (date.today() + timedelta(days=30))
                f_fi = st.date_input("Data fi prevista (DD/MM/AAAA):", value=p_fi, format="DD/MM/YYYY")

            f_press = st.number_input("Pressupost màxim estimat (€):", min_value=0.0, value=pressupost_est, step=50.0)

            sub_edit = st.form_submit_button("Desar Canvis del Projecte", type="primary")
            if sub_edit:
                update_projecte(project_id, {
                    "nom": f_nom,
                    "ubicacio": f_ubi,
                    "descripcio": f_desc,
                    "estat": f_estat,
                    "data_inici": to_iso_date(f_inici),
                    "data_fi_prevista": to_iso_date(f_fi),
                    "pressupost_estimat": f_press
                })
                st.success("Dades del projecte actualitzades!")
                st.rerun()

def _render_materials_tab(projecte: Dict[str, Any]):
    """Gestió visual de materials en graella de miniatures. En fer doble clic o clic, s'obren els detalls."""
    project_id = projecte["id"]
    materials = projecte.get("materials", [])

    st.markdown("### 🧱 Galeria Visual de Materials")
    st.caption("Miniatures dels materials de l'obra. Fes **doble clic** (o un clic al botó) sobre qualsevol miniatura per veure i editar totes les seves dades, canviar la foto, posar-lo en stock o assignar proveïdor.")

    # Accions ràpides superiors
    col_act1, col_act2 = st.columns([2.5, 1.5])
    with col_act2:
        if st.button("✨ Suggerir Materials amb IA", key=f"btn_ia_mat_{project_id}", use_container_width=True, type="secondary"):
            st.session_state[f"show_suggest_mat_{project_id}"] = True

    # Si s'ha activat la petició de suggeriment amb IA
    if st.session_state.get(f"show_suggest_mat_{project_id}"):
        with st.status("Generant llista de materials recomanada amb imatges i preus de mercat...", expanded=True) as status:
            prov, mod, key = render_ai_selector(key_prefix=f"mat_ai_{project_id}")
            ok, sugg_list, msg = generar_recomanacions_materials(projecte, prov, mod, key)
            if ok and sugg_list:
                status.update(label="Materials proposats per la IA (amb fotografies):", state="complete")
                st.write(f"S'han identificat **{len(sugg_list)} materials recomanats**:")
                cols_preview = st.columns(min(len(sugg_list), 4))
                for idx, item in enumerate(sugg_list):
                    c_prev = cols_preview[idx % len(cols_preview)]
                    with c_prev:
                        if item.get("imatge"):
                            st.image(item["imatge"], use_container_width=True)
                        st.caption(f"**{item.get('article')}**\nEst: {item.get('preu_estimat', 0)} €")
                
                if st.button("📥 Afegir tots aquests materials amb imatges al projecte", key=f"add_all_mat_{project_id}", type="primary", use_container_width=True):
                    for item in sugg_list:
                        add_material(project_id, {
                            "article": item.get("article"),
                            "quantitat": item.get("quantitat", 1),
                            "proveidor": item.get("proveidor", "Obramat"),
                            "preu_estimat": float(item.get("preu_estimat", 0.0)),
                            "preu_real": 0.0,
                            "comprat": False,
                            "en_stock": False,
                            "imatge": item.get("imatge")
                        })
                    st.session_state[f"show_suggest_mat_{project_id}"] = False
                    st.success("Materials i imatges afegits al projecte!")
                    st.rerun()
            else:
                status.update(label=f"No s'han pogut generar materials: {msg}", state="error")

    # Graella visual de miniatures
    if materials:
        n_stock = sum(1 for m in materials if m.get("en_stock", False))
        n_comprat = sum(1 for m in materials if m.get("comprat", False) and not m.get("en_stock", False))
        n_pendent = len(materials) - n_stock - n_comprat

        st.caption(f"📦 **{n_stock}** en stock &nbsp;|&nbsp; ✅ **{n_comprat}** comprats &nbsp;|&nbsp; ⏳ **{n_pendent}** pendents de compra &nbsp;*(Total: {len(materials)} materials)*")

        # Columnes per fila: 6 miniatures per fila per un format compacte i normalitzat
        num_cols = 6
        rows = [materials[i:i + num_cols] for i in range(0, len(materials), num_cols)]
        for row_idx, row in enumerate(rows):
            cols = st.columns(num_cols)
            for idx, m in enumerate(row):
                mat_id = m.get("id", f"m_{row_idx}_{idx}")
                img_url = m.get("imatge")
                es_stock = m.get("en_stock", False)
                es_comprat = m.get("comprat", False) and not es_stock
                nom_m = m.get("article", "Material")

                with cols[idx]:
                    with st.container(border=True):
                        # 1. Caixa normalitzada de mida fixa (105px d'alçada)
                        # object-fit: contain respecta la proporció vertical/horitzontal original sense deformar-la mai
                        if img_url:
                            st.markdown(
                                f"""
                                <div class="thumb-img-box" style="width: 100%; height: 105px; display: flex; align-items: center; justify-content: center; background: #0f172a; border-radius: 6px; overflow: hidden; margin-bottom: 2px;">
                                    <img src="{img_url}" style="max-width: 100%; max-height: 105px; width: auto; height: auto; object-fit: contain; display: block;" />
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                """
                                <div class="thumb-img-box" style="width: 100%; height: 105px; display: flex; align-items: center; justify-content: center; background: #1e293b; border-radius: 6px; border: 1px dashed #475569; font-size: 28px; margin-bottom: 2px;">
                                    🧱
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        # 2. Etiqueta d'estat
                        if es_stock:
                            badge = "📦 Stock"
                        elif es_comprat:
                            badge = "✅ Comprat"
                        else:
                            badge = "⏳ Pendent"

                        # 3. Botó d'obertura que respon al clic o al doble clic
                        lbl = f"{badge} · {nom_m}" if len(nom_m) <= 13 else f"{badge} · {nom_m[:11]}…"
                        if st.button(lbl, key=f"btn_card_{project_id}_{mat_id}", use_container_width=True, help=f"Fes clic o doble clic per obrir la fitxa de: {nom_m}"):
                            dialog_detall_material(project_id, m)

        # Suport de doble clic directe a les imatges de la graella
        st.markdown(
            """
            <script>
            (function() {
                const doc = window.parent ? window.parent.document : document;
                setTimeout(() => {
                    const boxes = doc.querySelectorAll('.thumb-img-box');
                    boxes.forEach(box => {
                        box.style.cursor = 'pointer';
                        box.setAttribute('title', 'Fes doble clic per obrir la fitxa del material');
                        box.ondblclick = function(e) {
                            e.preventDefault();
                            const block = box.closest('[data-testid="stVerticalBlock"]');
                            if (block) {
                                const btn = block.querySelector('button');
                                if (btn) btn.click();
                            }
                        };
                    });
                }, 300);
            })();
            </script>
            """,
            unsafe_allow_html=True
        )

    else:
        st.info("Encara no hi ha materials afegits. Fes servir el botó **✨ Suggerir Materials amb IA** o el formulari inferior per afegir-ne.")

    # Formulari d'alta manual de material amb proveïdors en memòria i opció de stock
    with st.expander("➕ Afegir Material Manualment"):
        with st.form(f"form_add_mat_{project_id}"):
            ca1, ca2 = st.columns([2, 1])
            with ca1:
                in_art = st.text_input("Nom de l'article / material:", placeholder="Ex: Cinta Enmascarar 50mm")
            
            with ca2:
                prov_llista = get_llista_proveidors()
                opts_prov = prov_llista + ["➕ Afegir un altre proveïdor..."]
                in_prov_sel = st.selectbox("Proveïdor recomanat:", opts_prov)

            nou_prov_custom_add = st.text_input(
                "Escriu el nom del nou proveïdor (es guardarà en memòria):",
                placeholder="Ex: Bricomart, Ferreteria Martínez, Pintures Soler...",
                key=f"nou_prov_add_{project_id}"
            ) if in_prov_sel == "➕ Afegir un altre proveïdor..." else ""

            cb1, cb2, cb3 = st.columns(3)
            with cb1:
                in_qtt = st.number_input("Quantitat:", min_value=1, value=1, step=1)
            with cb2:
                in_pest = st.number_input("Preu total estimat (€):", min_value=0.0, value=0.0, step=5.0)
            with cb3:
                in_preal = st.number_input("Preu pagat real (€, si ja s'ha comprat):", min_value=0.0, value=0.0, step=5.0)

            # Estat de disponibilitat
            st.markdown("**Disponibilitat del Material:**")
            col_est1, col_est2 = st.columns(2)
            with col_est1:
                in_stock = st.checkbox("📦 Ja el tinc en stock a casa (no cal comprar-lo, cost 0 €)", value=False)
            with col_est2:
                in_comprat = st.checkbox("🛒 Ja comprat / pagat", value=(in_preal > 0 and not in_stock))

            # Opcions d'imatge
            st.markdown("**Imatge del Material (opcional):**")
            ci1, ci2 = st.columns(2)
            with ci1:
                up_art_img = st.file_uploader("📁 Pujar foto pròpia (mòbil/fitxer):", type=["png", "jpg", "jpeg", "webp"], key=f"form_img_file_{project_id}")
            with ci2:
                in_art_url = st.text_input("🌐 O enllaç d'imatge web:", placeholder="https://...")
                gen_ai_opt = st.checkbox("✨ Generar automàticament amb IA si no es puja foto", value=True)

            sub_mat = st.form_submit_button("Afegir Material al Projecte", type="primary")
            if sub_mat and in_art:
                final_img = None
                if up_art_img:
                    final_img = f"data:image/jpeg;base64,{base64.b64encode(up_art_img.read()).decode('utf-8')}"
                elif in_art_url.strip():
                    final_img = in_art_url.strip()
                elif gen_ai_opt:
                    final_img = generar_imatge_material_url(in_art)

                final_prov = nou_prov_custom_add.strip() if (in_prov_sel == "➕ Afegir un altre proveïdor..." and nou_prov_custom_add and nou_prov_custom_add.strip()) else in_prov_sel
                if nou_prov_custom_add and nou_prov_custom_add.strip():
                    add_proveidor_memoria(nou_prov_custom_add.strip())

                add_material(project_id, {
                    "article": in_art.strip(),
                    "quantitat": in_qtt,
                    "proveidor": final_prov,
                    "preu_estimat": in_pest,
                    "preu_real": 0.0 if in_stock else in_preal,
                    "comprat": (in_comprat and not in_stock),
                    "en_stock": in_stock,
                    "imatge": final_img
                })
                st.success("Material afegit correctament!")
                st.rerun()

def _render_fases_tab(projecte: Dict[str, Any]):
    """Gestió d'etapes de l'obra, dates (DD/MM/AAAA) i checklist de subtasques."""
    project_id = projecte["id"]
    fases = projecte.get("fases", [])

    # Comprovar si s'ha d'obrir el diàleg de celebració de fi d'obra
    if st.session_state.get(f"show_celebration_dialog_{project_id}"):
        st.session_state[f"show_celebration_dialog_{project_id}"] = False
        dialog_finalitzar_obra(project_id, projecte.get("nom", "Projecte"))

    def _is_fase_done(f: Dict[str, Any]) -> bool:
        t_list = f.get("tasques", [])
        if t_list:
            return all(t.get("feta", False) for t in t_list)
        return f.get("estat") == "Completada"

    all_phases_done = len(fases) > 0 and all(_is_fase_done(f) for f in fases)
    is_proj_finalitzat = (_normalize_project_estat(projecte.get("estat")) == "Finalitzat")

    st.markdown("### ⏱️ Fases d'Execució i Checklist d'Obra")
    st.caption("Estructura l'ordre lògic dels treballs, assigna terminis i marca les fases completades a mesura que avancis.")

    # Banner superior quan totes les fases estan fetes
    if all_phases_done:
        if not is_proj_finalitzat:
            with st.container(border=True):
                c_win1, c_win2 = st.columns([2.8, 1.2])
                with c_win1:
                    st.markdown("### 🎉 Totes les fases estan completades!")
                    st.write("Has assolit el 100% de les fases i treballs d'aquesta obra. **La feina està acabada?**")
                with c_win2:
                    st.write("")
                    if st.button("🏆 Marcar com a Finalitzat", type="primary", use_container_width=True, key=f"btn_mark_proj_done_{project_id}"):
                        update_projecte(project_id, {"estat": "Finalitzat"})
                        st.balloons()
                        st.success("Projecte marcat com a Finalitzat!")
                        st.rerun()
        else:
            with st.container(border=True):
                c_fin1, c_fin2 = st.columns([3, 1])
                with c_fin1:
                    st.markdown("### 🏆 Obra Finalitzada amb Èxit")
                    st.caption("Aquest projecte té l'estat 'Finalitzat' i totes les seves fases completades.")
                with c_fin2:
                    st.write("")
                    if st.button("↩️ Reobrir Projecte", use_container_width=True, key=f"btn_reopen_proj_{project_id}", help="Tornar a posar l'obra en curs"):
                        update_projecte(project_id, {"estat": "En curs"})
                        st.rerun()

    col_f1, col_f2 = st.columns([3, 1])
    with col_f2:
        if st.button("✨ Generar Fases amb IA", key=f"btn_ia_fase_{project_id}", use_container_width=True):
            st.session_state[f"show_suggest_fases_{project_id}"] = True

    # Generació de fases per IA
    if st.session_state.get(f"show_suggest_fases_{project_id}"):
        with st.status("Planificant ordre constructiu lògic amb IA...", expanded=True) as status:
            prov, mod, key = render_ai_selector(key_prefix=f"fase_ai_{project_id}")
            ok, sugg_fases, msg = generar_recomanacions_fases(projecte, prov, mod, key)
            if ok and sugg_fases:
                status.update(label="Fases proposades per la IA:", state="complete")
                for f in sugg_fases:
                    st.markdown(f"**{f.get('nom')}**")
                    for t in f.get("tasques", []):
                        st.caption(f"  • {t.get('titol')}")
                
                if st.button("📥 Incorporar aquestes fases al projecte", key=f"add_all_fases_{project_id}", type="primary"):
                    for f in sugg_fases:
                        add_fase(project_id, f)
                    st.session_state[f"show_suggest_fases_{project_id}"] = False
                    st.success("Fases incorporades correctament!")
                    st.rerun()
            else:
                status.update(label=f"Error generant fases: {msg}", state="error")

    # Llistat de fases existents
    if fases:
        for i, f in enumerate(fases):
            fase_id = f.get("id", str(i))
            tasques = f.get("tasques", [])
            f_done = sum(1 for t in tasques if t.get("feta", False))
            f_tot = len(tasques)
            is_done = _is_fase_done(f)
            f_pct = 100 if is_done else (int((f_done / f_tot) * 100) if f_tot > 0 else 0)

            badge_estat = "🟢" if is_done else ("🟡" if f_pct > 0 else "⚪")
            status_desc = "Completada" if is_done else ("En curs" if f_pct > 0 else "Pendent")

            if f_tot == 0 and is_done:
                label_exp = f"🟢 **{f.get('nom', 'Fase')}** (✅ Acabada — 100%)"
            elif f_tot == 0:
                label_exp = f"⚪ **{f.get('nom', 'Fase')}** (⏳ Pendent — 0%)"
            else:
                label_exp = f"{badge_estat} **{f.get('nom', 'Fase')}** ({f_done}/{f_tot} tasques — {f_pct}%)"

            with st.expander(label_exp, expanded=(not is_done)):
                cf_d1, cf_d2, cf_d3, cf_d4 = st.columns([1.8, 0.9, 1.4, 0.5])
                with cf_d1:
                    d_in = format_date_cat(f.get("data_inici"))
                    d_out = format_date_cat(f.get("data_fi"))
                    if d_in or d_out:
                        st.caption(f"📅 Termini: {d_in or '?'} → {d_out or '?'}")
                with cf_d2:
                    st.markdown(f"Estat: **{status_desc}**")
                
                with cf_d3:
                    if not is_done:
                        if st.button("✅ Marcar Fase Acabada", key=f"btn_done_f_{project_id}_{fase_id}", type="primary", use_container_width=True):
                            marcar_fase_estat(project_id, fase_id, True)
                            other_f = [xf for xf in fases if xf.get("id") != fase_id]
                            if len(other_f) == 0 or all(_is_fase_done(xf) for xf in other_f):
                                st.session_state[f"show_celebration_dialog_{project_id}"] = True
                            st.rerun()
                    else:
                        if st.button("↩️ Reobrir Fase", key=f"btn_reopen_f_{project_id}_{fase_id}", use_container_width=True, help="Tornar a marcar la fase com a pendent"):
                            marcar_fase_estat(project_id, fase_id, False)
                            st.rerun()

                with cf_d4:
                    if st.button("🗑️", key=f"del_fase_{project_id}_{fase_id}", help="Eliminar Fase"):
                        delete_fase(project_id, fase_id)
                        st.rerun()

                st.progress(f_pct / 100.0)

                # Subtasques
                if tasques:
                    for t in tasques:
                        t_id = t.get("id")
                        t_done = t.get("feta", False)
                        chk_t = st.checkbox(
                            t.get("titol", ""),
                            value=t_done,
                            key=f"chk_t_{project_id}_{fase_id}_{t_id}"
                        )
                        if chk_t != t_done:
                            toggle_subtasca(project_id, fase_id, t_id)
                            up_p = get_projecte(project_id)
                            if up_p and all(_is_fase_done(xf) for xf in up_p.get("fases", [])):
                                st.session_state[f"show_celebration_dialog_{project_id}"] = True
                            st.rerun()

                # Formulari per afegir subtasca a aquesta fase
                with st.form(f"form_add_subt_{project_id}_{fase_id}"):
                    c_in_t, c_bt_t = st.columns([3, 1])
                    with c_in_t:
                        nova_subt = st.text_input("Nova subtasca per a aquesta etapa:", placeholder="Ex: Aplicar segona capa d'imprimació", key=f"in_subt_{project_id}_{fase_id}")
                    with c_bt_t:
                        st.write("")
                        sub_t = st.form_submit_button("➕ Afegir Tasca", type="secondary")
                        if sub_t and nova_subt:
                            add_subtasca_a_fase(project_id, fase_id, nova_subt)
                            st.rerun()
    else:
        st.info("Encara no hi ha fases definides. Crea la primera fase de l'obra a continuació.")

    # Formulari d'alta de fase manual
    with st.expander("➕ Crear Nova Fase d'Obra Manualment"):
        with st.form(f"form_add_fase_{project_id}"):
            f_nom = st.text_input("Nom de la fase:", placeholder="Ex: 2. Lampisteria i instal·lació de desguàs")
            col_fd1, col_fd2 = st.columns(2)
            with col_fd1:
                fd_in = st.date_input("Data d'inici prevista (DD/MM/AAAA):", value=date.today(), format="DD/MM/YYYY")
            with col_fd2:
                fd_out = st.date_input("Data de finalització (DD/MM/AAAA):", value=date.today() + timedelta(days=7), format="DD/MM/YYYY")
            
            sub_fase = st.form_submit_button("Crear Fase", type="primary")
            if sub_fase and f_nom:
                add_fase(project_id, {
                    "nom": f_nom,
                    "data_inici": to_iso_date(fd_in),
                    "data_fi": to_iso_date(fd_out),
                    "estat": "Pendent",
                    "tasques": []
                })
                st.success("Fase creada!")
                st.rerun()

def _render_assistent_ia_tab(projecte: Dict[str, Any]):
    """Xat interactiu amb l'assistent IA expert en obres i reformes."""
    project_id = projecte["id"]
    xat = projecte.get("xat_ia", [])

    st.markdown("### 🤖 Assistent IA d'Obra i Reformes")
    st.caption("Consulta qualsevol dubte tècnic: materials recomanats, tutorials d'execució pas a pas, temps d'assecat o preus de referència de mercat.")

    # Selector de model d'IA
    with st.expander("⚙️ Configuració del Motor d'IA", expanded=False):
        prov, mod, key = render_ai_selector(key_prefix=f"xat_ia_{project_id}")

    # Botons ràpids de preguntes freqüents
    st.markdown("**💡 Consultes ràpides:**")
    c_q1, c_q2, c_q3, c_q4 = st.columns(4)
    with c_q1:
        if st.button("🧼 Materials per a zones humides", use_container_width=True):
            st.session_state[f"fast_q_{project_id}"] = "Quins materials i coles especials recomanes per a impermeabilitzar i enrajolar una zona humida com la dutxa?"
    with c_q2:
        if st.button("⏱️ Ordre i temps d'assecat", use_container_width=True):
            st.session_state[f"fast_q_{project_id}"] = "Quin és l'ordre constructiu correcte i quins temps d'assecat cal respectar entre capes?"
    with c_q3:
        if st.button("🏷️ Estimació de cost / m²", use_container_width=True):
            st.session_state[f"fast_q_{project_id}"] = "Quin és el cost mitjà aproximat de materials per metre quadrat per a una reforma d'aquest tipus a Catalunya?"
    with c_q4:
        if st.button("🧹 Netejar conversa", use_container_width=True):
            clear_xat_projecte(project_id)
            st.rerun()

    # Historial de missatges
    for msg in xat:
        role = msg.get("role", "user")
        with st.chat_message("user" if role == "user" else "assistant"):
            st.markdown(msg.get("text", ""))
            if msg.get("data"):
                st.caption(f"*{msg.get('data')}*")

    # Entrada de xat
    user_prompt = st.chat_input("Escriu la teva consulta sobre l'obra...")
    
    # Si s'ha premut un botó ràpid
    if st.session_state.get(f"fast_q_{project_id}"):
        user_prompt = st.session_state.pop(f"fast_q_{project_id}")

    if user_prompt:
        # 1. Desar missatge usuari
        add_xat_missatge(project_id, role="user", text=user_prompt)
        
        # 2. Cridar la IA
        with st.spinner("L'expert en reformes està redactant el consell..."):
            ok, resposta = consultar_assistent_obra(projecte, user_prompt, prov, mod, key)
            if ok:
                add_xat_missatge(project_id, role="assistant", text=resposta)
            else:
                add_xat_missatge(project_id, role="assistant", text=f"⚠️ Error en la consulta d'IA: {resposta}")
        st.rerun()

def _render_modal_nou_projecte():
    """Diàleg modal o expander per donar d'alta un nou projecte."""
    st.markdown("---")
    st.markdown("### ➕ Donar d'Alta un Nou Projecte de Manteniment o Reforma")
    with st.form("form_alta_nou_projecte"):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom del projecte:", placeholder="Ex: Reforma Bany Petit, Canvi terra terrassa")
            ubicacio = st.selectbox("Ubicació a la casa:", ["Bany", "Cuina", "Menjador / Sala", "Habitació", "Terrassa / Balcó", "Jardí / Exterior", "Façana / Teulada", "Garatge / Traster", "Tota la casa"])
        with col2:
            pressupost = st.number_input("Pressupost màxim estimat (€):", min_value=0.0, value=500.0, step=50.0)
            estat = st.selectbox("Estat inicial:", ["Pendent", "En curs"])

        desc = st.text_area("Descripció dels treballs i objectius:", placeholder="Ex: Canviar la banyera per un plat de dutxa de resina, substituir les rajoles de les parets i renovar aixetes.")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            d_in = st.date_input("Data prevista d'inici (DD/MM/AAAA):", value=date.today(), format="DD/MM/YYYY")
        with col_d2:
            d_out = st.date_input("Data prevista de finalització (DD/MM/AAAA):", value=date.today() + timedelta(days=30), format="DD/MM/YYYY")

        col_sub1, col_sub2 = st.columns([1, 1])
        with col_sub1:
            sub = st.form_submit_button("Crear Projecte", type="primary", use_container_width=True)
        with col_sub2:
            cancel = st.form_submit_button("Cancel·lar", use_container_width=True)

        if sub and nom:
            nou_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            add_projecte({
                "id": nou_id,
                "nom": nom,
                "ubicacio": ubicacio,
                "descripcio": desc,
                "estat": estat,
                "data_inici": to_iso_date(d_in),
                "data_fi_prevista": to_iso_date(d_out),
                "pressupost_estimat": pressupost,
                "materials": [],
                "fases": [],
                "fotos": [],
                "xat_ia": [],
                "planol": {"preview_png": None, "canvas_data": None, "background_image": None}
            })
            st.session_state["show_modal_nou_projecte"] = False
            st.session_state["select_projecte_actiu"] = nou_id
            st.session_state["filtre_estat_projectes"] = "Tots"
            st.success(f"Projecte '{nom}' creat correctament!")
            st.rerun()
        elif cancel:
            st.session_state["show_modal_nou_projecte"] = False
            st.rerun()
    st.markdown("---")
