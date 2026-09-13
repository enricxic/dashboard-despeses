import streamlit as st
import pandas as pd
from core.db import fetch_table_fast, update_db_row, insert_db_row, delete_db_row

# Diccionari de taules i les seves claus primàries per permetre l'edició
PK_MAP = {
    'despeses': 'ID_mov',
    'ingressos': 'ID_mov',
    'compresSuper': 'id',
    'gasolina': 'id',
    'kmCotxe': 'id',
    'hipoteca': 'id',
    'tr_cartera': 'id',
    'estalviDP': 'id',
    'limitsDespeses': 'id',
    'pagaments': 'id',
    'tb_productes': 'idProducte',
    'tb_receptes': 'id',
    'tb_menus': 'id',
    'tb_supers': 'id',
    'registre_accions': 'id',
    'app_config': 'id'
}

def render():
    st.markdown("<h2 style='color:#f39c12; margin-top:0;'>🗄️ Gestor de Bases de Dades</h2>", unsafe_allow_html=True)
    
    # Check permissions
    if st.session_state.get("role") not in ["admin", "guest"]:
        st.warning("No tens permisos per accedir al gestor de bases de dades.")
        return

    # Check if a db is passed via URL
    url_db = st.query_params.get("db", "")
    
    taules_disponibles = sorted(list(PK_MAP.keys()))
    default_index = 0
    if url_db in taules_disponibles:
        default_index = taules_disponibles.index(url_db)
        
    selected_table = st.selectbox(
        "Selecciona la Base de Dades (Taula)", 
        taules_disponibles, 
        index=default_index,
        help="Tria quina taula de Supabase vols visualitzar i editar."
    )
    
    # Update URL dynamically without rerunning
    if selected_table != st.query_params.get("db", ""):
        st.query_params["db"] = selected_table
        
    pk_col = PK_MAP.get(selected_table, 'id')
    
    st.info(f"Visualitzant i editant la taula **`{selected_table}`**. La clau primària (ID) per desar els canvis és **`{pk_col}`**.")
    
    # Fetch Data
    with st.spinner(f"Carregant dades de {selected_table}..."):
        try:
            _, df = fetch_table_fast(selected_table)
        except Exception as e:
            st.error(f"Error carregant la taula: {e}")
            return
            
    if df is None or df.empty:
        st.warning(f"La taula {selected_table} està buida o no s'ha pogut carregar.")
        # Create an empty dataframe with just the PK column to allow inserts
        df = pd.DataFrame(columns=[pk_col, "nou_camp_exemple"])
        
    # Order by ID descending if it exists to show newest first
    if pk_col in df.columns:
        try:
            df = df.sort_values(by=pk_col, ascending=False).reset_index(drop=True)
        except Exception:
            pass

    st.write("---")
    
    # Key to force re-render if needed
    editor_key = f"db_editor_{selected_table}"
    
    edited_data = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key,
        hide_index=True
    )
    
    # Detect and apply changes manually if the user wants to apply them.
    # st.data_editor stores changes in st.session_state[editor_key]
    
    changes = st.session_state.get(editor_key, {})
    has_changes = any([changes.get("edited_rows"), changes.get("added_rows"), changes.get("deleted_rows")])
    
    if has_changes:
        st.warning("⚠️ Tens canvis pendents. Fes clic a **Aplicar Canvis** per desar-los a la base de dades.")
        if st.button("💾 Aplicar Canvis", type="primary"):
            edits = changes.get("edited_rows", {})
            adds = changes.get("added_rows", [])
            dels = changes.get("deleted_rows", [])
            
            with st.spinner("Desant canvis a Supabase..."):
                success = True
                
                # 1. Update Existing
                for row_idx_str, col_updates in edits.items():
                    row_idx = int(row_idx_str)
                    if row_idx < len(df):
                        pk_val = df.iloc[row_idx].get(pk_col)
                        if pk_val is not None:
                            try:
                                update_db_row(selected_table, pk_col, pk_val, col_updates)
                            except Exception as e:
                                st.error(f"Error actualitzant fila (ID {pk_val}): {e}")
                                success = False
                                
                # 2. Delete Rows
                for row_idx in dels:
                    if row_idx < len(df):
                        pk_val = df.iloc[row_idx].get(pk_col)
                        if pk_val is not None:
                            try:
                                delete_db_row(selected_table, pk_col, pk_val)
                            except Exception as e:
                                st.error(f"Error eliminant fila (ID {pk_val}): {e}")
                                success = False
                                
                # 3. Add Rows
                for new_row in adds:
                    try:
                        insert_db_row(selected_table, new_row)
                    except Exception as e:
                        st.error(f"Error inserint nova fila: {e}")
                        success = False
                        
                if success:
                    st.success("✅ Tots els canvis s'han desat correctament.")
                    del st.session_state[editor_key]
                    st.cache_data.clear()
                    st.rerun()
    else:
        st.write("📝 *Pots editar les caselles, afegir files a sota, o eliminar-les seleccionant la vora de l'esquerra i prement Suprimir.*")
