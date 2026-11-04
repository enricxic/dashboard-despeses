"""
Mòdul d'Interfície d'Usuari per al Disseny de Mobles en Fusta MD i Optimització de Tall (CutList Optimizer).
Permet crear mobles paramètrics o lliures, visualitzar-los en 3D interactiu (Three.js),
i obtenir el diagrama d'aprofitament i despecejament de planxes de MDF/Fusteria.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, Any, List
import copy

from core.cut_optimizer import (
    PRESETS_PLANXES,
    GRUIXOS_HABITUALS,
    PALETA_PECES,
    generar_peces_plantilla,
    optimitzar_tall_fusta,
    generar_html_visor_3d,
    generar_svg_planxa_tall
)
from core.projectes_manager import get_moble_md, save_moble_md


def render_disseny_moble_tab(projecte: Dict[str, Any]):
    """Pestanya principal de Disseny & Despecejament MD dins la fitxa d'un projecte."""
    project_id = str(projecte.get("id"))
    st.markdown("### 🪚 Disseny de Mobles en Fusta MD & Optimitzador de Tall")
    st.caption("Dissenya el teu moble a mida, visualitza'l en 3D interactiu i calcula el pla de tall (*CutList Optimizer*) amb les planxes de MD necessàries.")

    # Estat inicial del moble desat al projecte o plantilla per defecte
    moble_guardat = get_moble_md(project_id) or {}
    state_key = f"moble_state_{project_id}"

    if state_key not in st.session_state:
        if moble_guardat.get("peces"):
            st.session_state[state_key] = copy.deepcopy(moble_guardat)
        else:
            # Plantilla inicial: Prestatgeria 1800 x 800 x 300 mm
            peces_ini, p3d_ini = generar_peces_plantilla(
                tipus="prestatgeria",
                alt=1800.0,
                ample=800.0,
                fons=300.0,
                gruix_est=19.0,
                gruix_fons=3.0,
                num_prestatges=3,
                amb_fons=True,
                permet_gir_defecte=True
            )
            st.session_state[state_key] = {
                "nom": "Prestatgeria Estàndard",
                "tipus": "prestatgeria",
                "alt": 1800.0,
                "ample": 800.0,
                "fons": 300.0,
                "gruix_est": 19.0,
                "gruix_fons": 3.0,
                "num_prestatges": 3,
                "amb_fons": True,
                "preset_planxa": "Magatzem Gran (2440 × 1220 mm)",
                "planxa_llarg": 2440.0,
                "planxa_ample": 1220.0,
                "kerf": 3.5,
                "permet_gir_global": True,
                "peces": peces_ini,
                "peces_3d": p3d_ini
            }

    moble = st.session_state[state_key]

    # Barra superior d'accions ràpides i desar
    col_hdr1, col_hdr2 = st.columns([7, 3], vertical_alignment="center")
    with col_hdr1:
        st.markdown(f"**Moble actual:** `{moble.get('nom', 'Moble MD')}` ({moble.get('alt', 0):.0f} × {moble.get('ample', 0):.0f} × {moble.get('fons', 0):.0f} mm)")
    with col_hdr2:
        if st.button("💾 Desar Disseny al Projecte", type="primary", use_container_width=True, key=f"btn_save_moble_{project_id}"):
            save_moble_md(project_id, moble)
            st.toast("✅ Disseny de moble desat al projecte!", icon="💾")
            st.success("Disseny desat correctament.")

    # Seccions col·lapsables de configuració
    with st.expander("🛠️ 1. Definir Estructura i Peces del Moble", expanded=True):
        mode_def = st.radio(
            "Mètode de definició:",
            ["📐 Plantilles Ràpides (Prestatgeria, Armari, Taula)", "✏️ Llista de Peces Lliures / Personalitzades"],
            horizontal=True,
            key=f"mode_def_{project_id}"
        )

        if "Plantilles" in mode_def:
            c_p1, c_p2, c_p3 = st.columns([1.5, 1, 1])
            with c_p1:
                tipus_tpl = st.selectbox(
                    "Tipus de moble:",
                    ["Prestatgeria / Llibreria", "Armari bàsic amb portes", "Taula / Escriptori senzill"],
                    key=f"tpl_type_{project_id}"
                )
            with c_p2:
                permet_veta_chk = st.checkbox(
                    "Permetre girar peces (Sense veta / MD)",
                    value=moble.get("permet_gir_global", True),
                    help="Si s'activa, les peces es podran col·locar en qualsevol sentit (MD homogeni). Si es desmarca, es respecta estrictament la direcció de la veta.",
                    key=f"chk_veta_{project_id}"
                )
            with c_p3:
                amb_fons_chk = st.checkbox(
                    "Incloure fons posterior",
                    value=moble.get("amb_fons", True),
                    key=f"chk_fons_{project_id}"
                )

            c_dim1, c_dim2, c_dim3, c_dim4, c_dim5 = st.columns(5)
            with c_dim1:
                alt_val = st.number_input("Alçada total (mm):", min_value=100.0, max_value=3000.0, value=float(moble.get("alt", 1800.0)), step=10.0, key=f"tpl_alt_{project_id}")
            with c_dim2:
                ample_val = st.number_input("Amplada total (mm):", min_value=100.0, max_value=3000.0, value=float(moble.get("ample", 800.0)), step=10.0, key=f"tpl_amp_{project_id}")
            with c_dim3:
                fons_val = st.number_input("Profunditat / Fons (mm):", min_value=50.0, max_value=1500.0, value=float(moble.get("fons", 300.0)), step=10.0, key=f"tpl_fons_{project_id}")
            with c_dim4:
                idx_g_est = GRUIXOS_HABITUALS.index(19.0) if 19.0 in GRUIXOS_HABITUALS else 0
                g_est = st.selectbox("Gruix estructura (mm):", GRUIXOS_HABITUALS, index=idx_g_est, key=f"tpl_gest_{project_id}")
            with c_dim5:
                idx_g_fn = GRUIXOS_HABITUALS.index(3.0) if 3.0 in GRUIXOS_HABITUALS else 0
                g_fn = st.selectbox("Gruix fons posterior (mm):", GRUIXOS_HABITUALS, index=idx_g_fn, disabled=not amb_fons_chk, key=f"tpl_gfn_{project_id}")

            num_div = 3
            if "Prestatgeria" in tipus_tpl:
                num_div = st.slider("Nombre de prestatges interiors:", min_value=0, max_value=10, value=int(moble.get("num_prestatges", 3)), key=f"tpl_div_{project_id}")

            if st.button("⚡ Regenerar Peces segons Plantilla", type="secondary", use_container_width=True, key=f"btn_regen_tpl_{project_id}"):
                tipus_code = "prestatgeria"
                if "Armari" in tipus_tpl:
                    tipus_code = "armari"
                elif "Taula" in tipus_tpl:
                    tipus_code = "taula"

                peces_gen, p3d_gen = generar_peces_plantilla(
                    tipus=tipus_code,
                    alt=alt_val,
                    ample=ample_val,
                    fons=fons_val,
                    gruix_est=g_est,
                    gruix_fons=g_fn,
                    num_prestatges=num_div,
                    amb_fons=amb_fons_chk,
                    permet_gir_defecte=permet_veta_chk
                )
                moble.update({
                    "nom": f"{tipus_tpl} {alt_val:.0f}×{ample_val:.0f}×{fons_val:.0f}",
                    "tipus": tipus_code,
                    "alt": alt_val,
                    "ample": ample_val,
                    "fons": fons_val,
                    "gruix_est": g_est,
                    "gruix_fons": g_fn,
                    "num_prestatges": num_div,
                    "amb_fons": amb_fons_chk,
                    "permet_gir_global": permet_veta_chk,
                    "peces": peces_gen,
                    "peces_3d": p3d_gen
                })
                st.session_state[state_key] = moble
                st.rerun()

        # Taula / Llista interactiva de peces
        st.markdown("#### 📋 Desglossament de Peces a Tallar")
        st.caption("Pots editar les mides directament a la taula, canviar el gruix de cada peça o afegir peces addicionals.")

        peces_actuals = moble.get("peces", [])
        
        # Preparar dades per al data editor
        df_data = []
        for p in peces_actuals:
            df_data.append({
                "Nom": p.get("nom", "Peça"),
                "Llarg (mm)": float(p.get("llarg", 100.0)),
                "Ample (mm)": float(p.get("ample", 100.0)),
                "Gruix (mm)": float(p.get("gruix", 19.0)),
                "Quantitat": int(p.get("quantitat", 1)),
                "Girar (Sense Veta)": bool(p.get("permet_gir", True))
            })

        edited_df = st.data_editor(
            df_data,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_peces_{project_id}",
            column_config={
                "Nom": st.column_config.TextColumn("Nom de la peça", required=True),
                "Llarg (mm)": st.column_config.NumberColumn("Llargada (mm)", min_value=10.0, max_value=3000.0, step=1.0, format="%.0f"),
                "Ample (mm)": st.column_config.NumberColumn("Amplada (mm)", min_value=10.0, max_value=3000.0, step=1.0, format="%.0f"),
                "Gruix (mm)": st.column_config.SelectboxColumn("Gruix (mm)", options=GRUIXOS_HABITUALS, required=True),
                "Quantitat": st.column_config.NumberColumn("Quantitat", min_value=1, max_value=50, step=1),
                "Girar (Sense Veta)": st.column_config.CheckboxColumn("Permetre girar")
            }
        )

        # Si l'usuari fa canvis a la taula, actualitzar l'estat
        if edited_df != df_data:
            noves_peces = []
            for i, row in enumerate(edited_df):
                col = PALETA_PECES[i % len(PALETA_PECES)]
                noves_peces.append({
                    "id": f"p_custom_{i+1}",
                    "nom": row["Nom"],
                    "llarg": float(row["Llarg (mm)"]),
                    "ample": float(row["Ample (mm)"]),
                    "gruix": float(row["Gruix (mm)"]),
                    "quantitat": int(row["Quantitat"]),
                    "permet_gir": bool(row["Girar (Sense Veta)"]),
                    "color": col
                })
            moble["peces"] = noves_peces
            st.session_state[state_key] = moble

    # Configuració de la Planxa de Fusta (Mida comercial i serra)
    with st.expander("🪵 2. Configuració de Planxes Comercials de MD & Serra", expanded=True):
        cp1, cp2, cp3, cp4 = st.columns([2, 1.2, 1.2, 1.2])
        
        with cp1:
            noms_presets = list(PRESETS_PLANXES.keys())
            preset_triat = st.selectbox(
                "Mida comercial de planxa:",
                noms_presets,
                index=0,
                key=f"sel_preset_{project_id}"
            )
            valors_preset = PRESETS_PLANXES[preset_triat]

        is_custom = ("Personalitzada" in preset_triat)
        
        with cp2:
            llarg_pl = st.number_input(
                "Llargada planxa (mm):",
                min_value=300.0,
                max_value=4000.0,
                value=float(valors_preset["llarg"]) if not is_custom else float(moble.get("planxa_llarg", 2440.0)),
                step=50.0,
                disabled=not is_custom,
                key=f"in_llarg_pl_{project_id}"
            )
        with cp3:
            ample_pl = st.number_input(
                "Amplada planxa (mm):",
                min_value=200.0,
                max_value=3000.0,
                value=float(valors_preset["ample"]) if not is_custom else float(moble.get("planxa_ample", 1220.0)),
                step=50.0,
                disabled=not is_custom,
                key=f"in_ample_pl_{project_id}"
            )
        with cp4:
            kerf_val = st.number_input(
                "Pèrdua fulla serra (kerf mm):",
                min_value=0.0,
                max_value=10.0,
                value=float(moble.get("kerf", 3.5)),
                step=0.5,
                help="Gruix del disc de serra (típicament entre 3.0 i 4.0 mm). Es descompta de cada tall.",
                key=f"in_kerf_{project_id}"
            )

        moble["planxa_llarg"] = llarg_pl
        moble["planxa_ample"] = ample_pl
        moble["kerf"] = kerf_val

    # ==============================================================================
    # 3. RESULTATS I VISUALITZACIÓ (3D + DIAGRAMES DE TALL)
    # ==============================================================================
    st.write("")
    pestanyes_vis = st.tabs([
        "🧊 Visualitzador 3D Interactiu",
        "🪚 Diagrames de Tall de les Planxes (CutList)",
        "📋 Resum de Despecejament per Magatzem"
    ])

    # 1. VISOR 3D
    with pestanyes_vis[0]:
        st.markdown("#### Modelat 3D del Moble")
        st.caption("Pots rotar amb el ratolí/dit, apropar/allunyar amb la roda, i clicar 'Vista Explosionada' per veure com encaixa cada tauler.")
        
        peces_3d = moble.get("peces_3d", [])
        if peces_3d:
            html_3d = generar_html_visor_3d(peces_3d)
            components.html(html_3d, height=500)
        else:
            st.info("ℹ️ El model 3D es genera automàticament en triar una plantilla paramètrica (Prestatgeria, Armari, Taula).")

    # Executar optimització de tall
    res_tall = optimitzar_tall_fusta(
        peces_input=moble.get("peces", []),
        mida_planxa={"llarg": moble["planxa_llarg"], "ample": moble["planxa_ample"]},
        kerf=moble["kerf"],
        permet_gir_global=moble.get("permet_gir_global", True)
    )

    # 2. DIAGRAMES DE TALL PER CADA GRUIX
    with pestanyes_vis[1]:
        st.markdown("#### Diagrama de Tall i Aprofitament (CutList Optimizer)")

        if not res_tall.get("ok"):
            for err in res_tall.get("peces_que_no_caben", []):
                st.error(f"⚠️ **{err['nom']}** ({err['llarg']:.0f}×{err['ample']:.0f} mm): {err['motiu']}.")

        # Mètriques globals
        tot_pl = res_tall.get("total_planxes_global", 0)
        tot_pec = res_tall.get("peces_totals_count", 0)
        
        m_c1, m_c2, m_c3 = st.columns(3)
        with m_c1:
            st.metric("Total Planxes Necessàries", f"{tot_pl} planxes", delta=f"{len(res_tall.get('resultats_per_gruix', {}))} gruixos diferents")
        with m_c2:
            st.metric("Total Peces a Tallar", f"{tot_pec} peces")
        with m_c3:
            st.metric("Gruix de Serra (Kerf)", f"{moble['kerf']:.1f} mm")

        st.divider()

        # Desglossar per gruix de planxa
        gruixos_dict = res_tall.get("resultats_per_gruix", {})
        if not gruixos_dict:
            st.info("Afegeix peces a la taula per calcular el pla de tall.")
        else:
            for gruix_nom, data_g in gruixos_dict.items():
                st.markdown(f"### 🪵 Planxes de gruix **{gruix_nom}** — ({data_g['num_planxes']} planxes)")
                st.caption(f"Aprofitament del material: **{data_g['aprofitament_pct']}%** | Àrea útil: **{data_g['area_util_m2']} m²** (de {data_g['area_total_m2']} m² totals de planxa)")
                
                # Barra de progrés d'aprofitament
                st.progress(data_g['aprofitament_pct'] / 100.0)

                for pl in data_g.get("planxes", []):
                    with st.expander(f"📄 Planxa #{pl['idx']} ({pl['llarg']:.0f} × {pl['ample']:.0f} mm) — {pl['peces_count']} peces ({pl['aprofitament_pct']}% aprofitat)", expanded=True):
                        # Dibuix vectorial SVG de la planxa
                        svg_code = generar_svg_planxa_tall(pl, amplada_visual=850)
                        st.components.v1.html(svg_code, height=int(pl['ample'] * (850 / pl['llarg'])) + 90)
                        
                        # Retalls útils si n'hi ha
                        retalls = pl.get("retalls_util", [])
                        if retalls:
                            retalls_txt = ", ".join([f"{r['w']:.0f}×{r['h']:.0f} mm" for r in retalls])
                            st.caption(f"♻️ **Retalls útils sobrants:** {retalls_txt}")

    # 3. RESUM DE DESPECEJAMENT PER PORTAR AL MAGATZEM
    with pestanyes_vis[2]:
        st.markdown("#### 📝 Llista de Tall per a la Fusteria / Magatzem")
        st.caption("Aquesta llista conté el desglossament ordenat per portar directament al servei de tall de fusta (Leroy Merlin, Bauhaus o fusteria local).")

        rows_resum = []
        for p in moble.get("peces", []):
            qty = int(p.get("quantitat", 1))
            rows_resum.append({
                "Peça": p.get("nom", "Peça"),
                "Gruix": f"{p.get('gruix', 19):.0f} mm",
                "Llargada (mm)": f"{p.get('llarg', 0):.0f}",
                "Amplada (mm)": f"{p.get('ample', 0):.0f}",
                "Quantitat": qty,
                "M2 Útils": f"{(float(p.get('llarg', 0)) * float(p.get('ample', 0)) * qty) / 1_000_000.0:.2f} m²",
                "Veta / Gir": "Lliure (MD)" if p.get("permet_gir", True) else "Fixa (Veta)"
            })

        st.table(rows_resum)

        # Resum de compra comercial
        st.markdown("#### 🛒 Planxes a comprar:")
        for gruix_nom, data_g in gruixos_dict.items():
            st.markdown(f"- **{data_g['num_planxes']} planxa/es** de MD gruix **{gruix_nom}** (mida {moble['planxa_llarg']:.0f} × {moble['planxa_ample']:.0f} mm)")
