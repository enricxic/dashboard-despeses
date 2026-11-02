import streamlit as st
import pandas as pd
from core.db import get_supabase_client, load_categories_conceptes, save_categories_conceptes
from core.normalitzador import (
    TABLE_SPECS,
    diagnosticar_taula,
    aplicar_discrepancies,
    remove_accents
)

@st.dialog("🧹 Normalitzar Dades (BD & JSON)", width="large")
def show_normalitzador_dialog():
    st.markdown("""
    Aquesta eina permet **analitzar i corregir** discrepàncies de format a les taules de la base de dades i fitxers de configuració:
    - **Minúscules sense accents** per a categories (`buta`, `farmacia`, `ingres_general`, etc.).
    - Format estricte de dates a **`DD/MM/AAAA`**.
    - Harmonització de conceptes i formes de pagament.
    """)

    role = st.session_state.get("role", "admin")
    supabase = get_supabase_client(role)

    tab_bd, tab_json = st.tabs(["🔍 Anàlisi i Normalització de BD", "📂 Categories & Conceptes (JSON)"])

    with tab_bd:
        st.subheader("⚙️ Configuració de l'Anàlisi")
        col_t, col_a = st.columns([1, 1])

        with col_t:
            opcions_taules = ["Totes les taules"] + list(TABLE_SPECS.keys())
            taula_sel = st.selectbox(
                "Tria la taula a analitzar:",
                opcions_taules,
                index=0,
                help="Pots triar una taula concreta per anar pas a pas o analitzar-les totes alhora."
            )

        with col_a:
            st.markdown("**Àmbits a verificar:**")
            chk_dates = st.checkbox("📅 Dates (garantir format DD/MM/AAAA)", value=True)
            chk_cats = st.checkbox("🏷️ Categories (minúscula sense accents)", value=True)
            chk_conc = st.checkbox("📝 Conceptes (harmonització de noms)", value=True)
            chk_bancs = st.checkbox("🏦 Bancs i Formes de Pagament", value=False)

        ambits_seleccionats = []
        if chk_dates:
            ambits_seleccionats.append("dates")
        if chk_cats:
            ambits_seleccionats.append("categories")
        if chk_conc:
            ambits_seleccionats.append("conceptes")
        if chk_bancs:
            ambits_seleccionats.append("bancs")

        st.markdown("<br/>", unsafe_allow_html=True)
        btn_analitzar = st.button("🔍 Executar Anàlisi de Discrepàncies", type="primary", use_container_width=True)

        if btn_analitzar:
            if not ambits_seleccionats:
                st.warning("Has de seleccionar com a mínim un àmbit a verificar.")
            else:
                taules_a_revisar = list(TABLE_SPECS.keys()) if taula_sel == "Totes les taules" else [taula_sel]
                totes_discrepancies = []

                with st.spinner("Analitzant dades a la base de dades..."):
                    for t in taules_a_revisar:
                        disc = diagnosticar_taula(t, ambits_seleccionats, supabase)
                        totes_discrepancies.extend(disc)

                st.session_state["discrepancies_pendents"] = totes_discrepancies
                st.session_state["discrepancies_taula_filtre"] = taula_sel

        # Mostrar resultats de l'anàlisi si estan carregats
        if "discrepancies_pendents" in st.session_state:
            discs = st.session_state["discrepancies_pendents"]
            if not discs:
                st.success("🎉 Excel·lent! No s'ha trobat cap discrepància amb els filtres seleccionats.")
            else:
                st.info(f"S'han detectat **{len(discs)}** discrepàncies que requereixen normalització.")

                # Preparar DataFrame per al data_editor
                df_editor = pd.DataFrame(discs)
                df_editor.insert(0, "Aplicar", True)

                # Columnes a mostrar
                columnes_visibles = ["Aplicar", "taula", "pk_val", "columna", "valor_actual", "valor_nou", "motiu"]
                col_rename = {
                    "Aplicar": "Aplicar",
                    "taula": "Taula",
                    "pk_val": "ID Registre",
                    "columna": "Columna",
                    "valor_actual": "Valor Actual",
                    "valor_nou": "Valor Normalitzat",
                    "motiu": "Motiu"
                }

                edited_df = st.data_editor(
                    df_editor[columnes_visibles],
                    column_config={
                        "Aplicar": st.column_config.CheckboxColumn("Aplicar", default=True),
                        "Taula": st.column_config.TextColumn("Taula", disabled=True),
                        "ID Registre": st.column_config.TextColumn("ID", disabled=True),
                        "Columna": st.column_config.TextColumn("Columna", disabled=True),
                        "Valor Actual": st.column_config.TextColumn("Actual", disabled=True),
                        "Valor Normalitzat": st.column_config.TextColumn("Normalitzat", disabled=True),
                        "Motiu": st.column_config.TextColumn("Motiu", disabled=True)
                    },
                    hide_index=True,
                    use_container_width=True
                )

                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    if st.button("▶️ Aplicar Normalització als seleccionats", type="primary", use_container_width=True):
                        # Filtrar seleccionats
                        files_a_aplicar = edited_df[edited_df["Aplicar"] == True]
                        if files_a_aplicar.empty:
                            st.warning("No has seleccionat cap element per normalitzar.")
                        else:
                            # Reconstruir llista d'objectes originals seleccionats
                            indices_seleccionats = files_a_aplicar.index.tolist()
                            items_to_apply = [discs[i] for i in indices_seleccionats]

                            with st.spinner(f"Aplicant canvis a {len(items_to_apply)} registres..."):
                                res = aplicar_discrepancies(items_to_apply, supabase)

                            if res["errors"]:
                                st.error(f"S'han produït alguns errors:\n" + "\n".join(res["errors"]))
                            else:
                                st.success(f"✅ S'han normalitzat correctament {res['actualitzats']} registres!")
                                st.cache_data.clear()
                                # Netejar llista de la sessió per recarregar si es vol
                                del st.session_state["discrepancies_pendents"]
                                st.rerun()

                with col_btn2:
                    if st.button("🗑️ Netejar resultats de l'anàlisi", use_container_width=True):
                        del st.session_state["discrepancies_pendents"]
                        st.rerun()

    with tab_json:
        st.subheader("📂 Categories Canòniques (Minúscules sense accents)")
        cats_dict = load_categories_conceptes()
        
        # Llistat de categories i estat
        st.markdown("Estat actual de les categories a `categories_conceptes.json`:")
        
        cats_info = []
        for cat_k, conceptes in cats_dict.items():
            es_canonica = (cat_k == remove_accents(cat_k).lower())
            cats_info.append({
                "Categoria": cat_k,
                "Minúscula sense accent": "✅ Sí" if es_canonica else "⚠️ Cal corregir",
                "Total Conceptes": len(conceptes) if isinstance(conceptes, list) else 0
            })
        
        st.dataframe(pd.DataFrame(cats_info), use_container_width=True, hide_index=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🔄 Sincronitzar Categories & Conceptes amb Supabase (app_config)", use_container_width=True):
            with st.spinner("Sincronitzant amb Supabase..."):
                ok = save_categories_conceptes(cats_dict)
            if ok:
                st.success("✅ `categories_conceptes.json` sincronitzat correctament amb la base de dades!")
            else:
                st.error("Error en la sincronització amb Supabase.")

    st.markdown("<hr style='margin: 15px 0;'/>", unsafe_allow_html=True)
    if st.button("❌ Tancar", use_container_width=True):
        if "normalitzant_dades" in st.session_state:
            del st.session_state["normalitzant_dades"]
        if "discrepancies_pendents" in st.session_state:
            del st.session_state["discrepancies_pendents"]
        st.rerun()
