import streamlit as st
import pandas as pd
from core.db import fetch_table_fast, update_db_row, insert_db_row, delete_db_row

# Diccionari de taules i les seves claus primàries per permetre l'edició
PK_MAP = {
    'despeses': 'ID_mov',
    'ingressos': 'ID_mov',
    'compresSuper': 'IdCompra',
    'gasolina': 'id',
    'kmCotxe': 'id',
    'hipoteca': 'id',
    'tr_cartera': 'idTRCartera',
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
    import modules.avatar_widget as avatar
    avatar.render_header_with_avatar("<div style='font-size: 1.8rem; font-weight: bold; color:#f39c12; margin-top:0;'>🗄️ Gestor de Bases de Dades</div>", "bases_dades")
            
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
        
    ordenar_recent = st.checkbox("Ordenar pel més recent primer", value=True, help="Si està marcat, es mostrarà el més recent a dalt de tot.")
    
    if ordenar_recent:
        if selected_table == 'registre_accions' and 'data_hora' in df.columns:
            try:
                df = df.sort_values(by='data_hora', ascending=False).reset_index(drop=True)
            except Exception:
                pass
        elif pk_col in df.columns:
            try:
                df = df.sort_values(by=pk_col, ascending=False).reset_index(drop=True)
            except Exception:
                pass
    else:
        if selected_table == 'registre_accions' and 'data_hora' in df.columns:
            try:
                df = df.sort_values(by='data_hora', ascending=True).reset_index(drop=True)
            except Exception:
                pass
        elif pk_col in df.columns:
            try:
                df = df.sort_values(by=pk_col, ascending=True).reset_index(drop=True)
            except Exception:
                pass

    st.write("---")
    
    # Key to force re-render if needed
    editor_key = f"db_editor_{selected_table}"
    
    col_config = {}
    for col in df.columns:
        if col.upper() == 'DATA':
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
            col_config[col] = st.column_config.DateColumn(col, format="DD/MM/YYYY")
            
    edited_data = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key,
        hide_index=True,
        column_config=col_config
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
