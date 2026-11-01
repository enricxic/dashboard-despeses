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
    add_fase,
    update_fase,
    delete_fase,
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

@st.dialog("📷 Imatge del Material")
def dialog_imatge_material(project_id: str, material: Dict[str, Any]):
    """Permet assignar una imatge al material: per arxiu propi, generada per IA o URL."""
    mat_id = material.get("id")
    nom_art = material.get("article", "Material")
    cur_img = material.get("imatge")

    st.markdown(f"### 🧱 {nom_art}")
    if cur_img:
        st.image(cur_img, width=240, caption="Imatge actual del material")

    t_ia, t_up, t_url = st.tabs(["✨ Generar amb IA", "📁 Arxiu Propi (Foto)", "🌐 Enllaç URL"])

    with t_ia:
        st.caption("La IA generarà una imatge realista i neta del producte de construcció/bricolatge.")
        if st.button("🎨 Generar Imatge IA ara", type="primary", use_container_width=True, key=f"gen_ia_btn_{mat_id}"):
            with st.spinner("Generant fotografia del material..."):
                nova_url = generar_imatge_material_url(nom_art)
                update_material(project_id, mat_id, {"imatge": nova_url})
                st.success("Imatge generada i assignada!")
                st.rerun()

    with t_up:
        up_file = st.file_uploader(
            "Selecciona o fes una foto amb el mòbil (caixa, paquet o catàleg):",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"up_mat_file_{mat_id}"
        )
        if st.button("Guardar foto pròpia", use_container_width=True, key=f"save_up_btn_{mat_id}"):
            if up_file:
                b64_data = f"data:image/jpeg;base64,{base64.b64encode(up_file.read()).decode('utf-8')}"
                update_material(project_id, mat_id, {"imatge": b64_data})
                st.success("Foto desada correctament!")
                st.rerun()
            else:
                st.warning("Selecciona primer una imatge.")

    with t_url:
        in_url = st.text_input("Enganxa l'enllaç de la foto (Leroy Merlin, Obramat, Google...):", value=cur_img if (cur_img and cur_img.startswith("http")) else "")
        if st.button("Guardar Enllaç", use_container_width=True, key=f"save_url_btn_{mat_id}"):
            if in_url.strip():
                update_material(project_id, mat_id, {"imatge": in_url.strip()})
                st.success("Enllaç desat!")
                st.rerun()

    if cur_img:
        st.divider()
        if st.button("🗑️ Eliminar aquesta imatge", key=f"del_mat_img_{mat_id}", use_container_width=True):
            update_material(project_id, mat_id, {"imatge": None})
            st.rerun()

# ==========================================
# RENDERITZACIÓ PRINCIPAL DEL MÒDUL
# ==========================================

def render_projectes_tab(family_names: List[str] = None):
    """Pestanya principal de Projectes d'Obra i Reformes al mòdul de manteniment."""
    projectes = load_projectes()

    # Barra superior de selecció de projecte
    col_sel, col_nou = st.columns([3, 1])
    
    opcions_proj = {p["id"]: f"{p.get('nom', 'Sense títol')} ({p.get('ubicacio', 'Llar')}) — {p.get('estat', 'En curs')}" for p in projectes}
    
    # Comprovar si hi ha projecte seleccionat a la sessió o paràmetres URL
    query_proj = st.query_params.get("proj_id")
    default_proj_id = None
    if query_proj and query_proj in opcions_proj:
        default_proj_id = query_proj
    elif projectes:
        default_proj_id = projectes[0]["id"]

    with col_nou:
        st.write("")
        if st.button("➕ Nou Projecte d'Obra", use_container_width=True, type="primary"):
            st.session_state["show_modal_nou_projecte"] = True

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
            st.info("👋 Encara no hi ha cap projecte creat. Prem **➕ Nou Projecte d'Obra** per començar.")

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
    cost_comprat = sum(float(m.get("preu_real", 0.0) or 0.0) for m in materials if m.get("comprat", False))

    d_inici = format_date_cat(projecte.get("data_inici"))
    d_fi = format_date_cat(projecte.get("data_fi_prevista"))

    with st.container():
        c1, c2, c3, c4 = st.columns([1.8, 0.9, 1.0, 1.3])
        with c1:
            st.markdown(f"### 🔨 {projecte.get('nom', 'Projecte')} <span style='font-size:14px; color:#64748b;'>({projecte.get('ubicacio', '')})</span>", unsafe_allow_html=True)
            if projecte.get("descripcio"):
                st.caption(projecte.get("descripcio"))
        with c2:
            st.metric("Estat", projecte.get("estat", "Planificació"), delta=None)
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
                estats = ["Planificació", "En curs", "En pausa", "Completat"]
                cur_est = projecte.get("estat", "Planificació")
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
    """Gestió visual de materials amb imatges (pròpies o IA), proveïdors, preus i casella de compra."""
    project_id = projecte["id"]
    materials = projecte.get("materials", [])

    st.markdown("### 🧱 Llistat de Materials i Control de Pressupost")
    st.caption("Planifica els materials necessaris amb suport fotogràfic, controla els preus de mercat i marca els que ja has adquirit.")

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
                            "imatge": item.get("imatge")
                        })
                    st.session_state[f"show_suggest_mat_{project_id}"] = False
                    st.success("Materials i imatges afegits al projecte!")
                    st.rerun()
            else:
                status.update(label=f"No s'han pogut generar materials: {msg}", state="error")

    # Llistat visual de materials
    if materials:
        st.markdown(f"**Articles del Projecte ({len(materials)}):**")
        for i, m in enumerate(materials):
            mat_id = m.get("id", str(i))
            comprat = m.get("comprat", False)
            img_url = m.get("imatge")
            
            with st.container(border=True):
                c_chk, c_img, c_info, c_preus, c_actions = st.columns([0.4, 1.2, 2.8, 1.6, 1.0])
                
                # 1. Casella Comprat
                with c_chk:
                    st.write("")
                    chk = st.checkbox("", value=comprat, key=f"chk_mat_{project_id}_{mat_id}", help="Marcar com a comprat")
                    if chk != comprat:
                        update_material(project_id, mat_id, {"comprat": chk})
                        st.rerun()

                # 2. Imatge en miniatura
                with c_img:
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.markdown("<div style='background:#f1f5f9; border-radius:8px; height:70px; display:flex; align-items:center; justify-content:center; font-size:26px; border:1px dashed #cbd5e1;'>🧱</div>", unsafe_allow_html=True)

                # 3. Informació de l'article
                with c_info:
                    st.markdown(f"**{m.get('article', '')}**" if not comprat else f"~~{m.get('article', '')}~~")
                    c_det1, c_det2 = st.columns(2)
                    with c_det1:
                        st.caption(f"Quantitat: **{m.get('quantitat', 1)}**")
                    with c_det2:
                        st.caption(f"Proveïdor: **{m.get('proveidor', '-')}**")

                # 4. Preus estimat vs real
                with c_preus:
                    p_est = float(m.get("preu_estimat", 0.0) or 0.0)
                    p_real = float(m.get("preu_real", 0.0) or 0.0)
                    st.caption(f"Estimat: **{p_est:.2f} €**")
                    if comprat:
                        st.markdown(f"Pagat: <span style='color:#16a34a; font-weight:700;'>{p_real:.2f} €</span>", unsafe_allow_html=True)
                    else:
                        st.caption("Estat: *Pendent de compra*")

                # 5. Botons d'acció (Imatge / Esborrar)
                with c_actions:
                    if st.button("📷 Foto", key=f"btn_img_{project_id}_{mat_id}", use_container_width=True, help="Canviar o generar imatge"):
                        dialog_imatge_material(project_id, m)
                    if st.button("🗑️", key=f"del_mat_{project_id}_{mat_id}", use_container_width=True, help="Eliminar material"):
                        delete_material(project_id, mat_id)
                        st.rerun()

    else:
        st.info("Encara no hi ha materials afegits. Fes servir el botó **✨ Suggerir Materials amb IA** o el formulari inferior per afegir-ne amb imatges.")

    # Formulari d'alta manual de material amb suport d'imatge
    with st.expander("➕ Afegir Material Manualment"):
        with st.form(f"form_add_mat_{project_id}"):
            ca1, ca2 = st.columns([2, 1])
            with ca1:
                in_art = st.text_input("Nom de l'article / material:", placeholder="Ex: Plat de dutxa resina 120x80 blanc")
            with ca2:
                in_prov = st.selectbox("Proveïdor recomanat:", ["Obramat", "Leroy Merlin", "Bauhaus", "Brico Depôt", "Ferreteria de barri", "Internet", "Altre"])
            
            cb1, cb2, cb3 = st.columns(3)
            with cb1:
                in_qtt = st.number_input("Quantitat:", min_value=1, value=1, step=1)
            with cb2:
                in_pest = st.number_input("Preu total estimat (€):", min_value=0.0, value=0.0, step=5.0)
            with cb3:
                in_preal = st.number_input("Preu pagat real (€, si ja s'ha comprat):", min_value=0.0, value=0.0, step=5.0)

            # Opcions d'imatge
            st.markdown("**Imatge del Material (opcional):**")
            ci1, ci2 = st.columns(2)
            with ci1:
                up_art_img = st.file_uploader("📁 Pujar foto pròpia (mòbil/fitxer):", type=["png", "jpg", "jpeg", "webp"], key=f"form_img_file_{project_id}")
            with ci2:
                in_art_url = st.text_input("🌐 O enllaç d'imatge web:", placeholder="https://...")
                gen_ai_opt = st.checkbox("✨ Generar automàticament amb IA si no es puja foto", value=True)

            in_comprat = st.checkbox("Ja comprat / a casa", value=(in_preal > 0))

            sub_mat = st.form_submit_button("Afegir Material al Projecte", type="primary")
            if sub_mat and in_art:
                final_img = None
                if up_art_img:
                    final_img = f"data:image/jpeg;base64,{base64.b64encode(up_art_img.read()).decode('utf-8')}"
                elif in_art_url.strip():
                    final_img = in_art_url.strip()
                elif gen_ai_opt:
                    final_img = generar_imatge_material_url(in_art)

                add_material(project_id, {
                    "article": in_art,
                    "quantitat": in_qtt,
                    "proveidor": in_prov,
                    "preu_estimat": in_pest,
                    "preu_real": in_preal,
                    "comprat": in_comprat,
                    "imatge": final_img
                })
                st.success("Material afegit correctament!")
                st.rerun()

def _render_fases_tab(projecte: Dict[str, Any]):
    """Gestió d'etapes de l'obra, dates (DD/MM/AAAA) i checklist de subtasques."""
    project_id = projecte["id"]
    fases = projecte.get("fases", [])

    st.markdown("### ⏱️ Fases d'Execució i Checklist d'Obra")
    st.caption("Estructura l'ordre lògic dels treballs, assigna terminis i marca les fites assolides.")

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
            f_pct = int((f_done / f_tot) * 100) if f_tot > 0 else (100 if f.get("estat") == "Completada" else 0)

            badge_estat = "🟢" if f_pct == 100 else ("🟡" if f_pct > 0 else "⚪")
            
            with st.expander(f"{badge_estat} **{f.get('nom', 'Fase')}** ({f_done}/{f_tot} tasques — {f_pct}%)", expanded=(f_pct < 100)):
                cf_d1, cf_d2, cf_d3 = st.columns([2, 1, 1])
                with cf_d1:
                    d_in = format_date_cat(f.get("data_inici"))
                    d_out = format_date_cat(f.get("data_fi"))
                    if d_in or d_out:
                        st.caption(f"📅 Termini previst: {d_in or '?'} → {d_out or '?'}")
                with cf_d2:
                    st.caption(f"Estat: **{f.get('estat', 'Pendent')}**")
                with cf_d3:
                    if st.button("🗑️ Eliminar Fase", key=f"del_fase_{project_id}_{fase_id}"):
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
            prov, mod, key = render_ai_selector(key_prefix=f"xat_ia_{project_id}")
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
            estat = st.selectbox("Estat inicial:", ["Planificació", "En curs"])

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
            st.success(f"Projecte '{nom}' creat correctament!")
            st.rerun()
        elif cancel:
            st.session_state["show_modal_nou_projecte"] = False
            st.rerun()
    st.markdown("---")
