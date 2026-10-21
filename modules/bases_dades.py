import streamlit as st
import pandas as pd
from core.db import fetch_table_fast, update_db_row, insert_db_row, delete_db_row

# Diccionari de taules i les seves claus primàries per permetre l'edició
PK_MAP = {
    'despeses': 'ID_mov',
    'ingressos': 'idIngres',
    'compresSuper': 'IdCompra',
    'gasolina': 'idGasolina',
    'kmCotxe': 'idRuta',
    'hipoteca': 'id',
    'tr_cartera': 'idTRCartera',
    'estalviDP': 'id',
    'limitsDespeses': 'id',
    'pagaments': 'idPago',
    'tb_productes': 'idProducte',
    'tb_receptes_pro': 'id',
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

    if pk_col not in df.columns:
        candidates = ['idPago', 'idIngres', 'ID_mov', 'IdCompra', 'idGasolina', 'idRuta', 'idTRCartera', 'idProducte', 'id', 'ID']
        for c in candidates:
            if c in df.columns:
                pk_col = c
                break
        
    col_t, col_chk = st.columns([7, 3], vertical_alignment="bottom")
    with col_chk:
        ordenar_recent = st.checkbox("Ordenar pel més recent primer", value=True, help="Si està marcat, es mostrarà el més recent a dalt de tot.")
        
    with st.expander("🔍 Filtres", expanded=False):
        # Determine candidate columns for categorical filters (max 15 unique values)
        candidate_cols = []
        for col in df.columns:
            if col == pk_col or col.lower() in ['data', 'import', 'preu_unitari', 'preu_total', 'comentari', 'id', 'id_mov']:
                continue
            try:
                if df[col].nunique() <= 20:
                    candidate_cols.append(col)
            except TypeError:
                pass
                
        # We limit to 4 dropdowns for layout purposes
        filter_cols = candidate_cols[:4]
        num_cols = len(filter_cols) + 2 # dropdowns + text search + clear btn
        
        cols = st.columns(num_cols, vertical_alignment="bottom")
        
        filters = {}
        for i, col in enumerate(filter_cols):
            with cols[i]:
                unique_vals = ["Tots"] + sorted([str(x) for x in df[col].dropna().unique()])
                filters[col] = st.selectbox(col.capitalize(), unique_vals, key=f"f_{selected_table}_{col}")
                
        with cols[-2]:
            search_term = st.text_input("Cerca text lliure", "", key=f"search_{selected_table}")
            
        with cols[-1]:
            if st.button("🔄 Netejar", use_container_width=True):
                for col in filter_cols:
                    if f"f_{selected_table}_{col}" in st.session_state:
                        del st.session_state[f"f_{selected_table}_{col}"]
                if f"search_{selected_table}" in st.session_state:
                    del st.session_state[f"search_{selected_table}"]
                st.rerun()

    # Apply dropdown filters
    for col, val in filters.items():
        if val != "Tots":
            df = df[df[col].astype(str) == val]
            
    # Apply text search filter
    if search_term:
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask = mask | df[col].astype(str).str.contains(search_term, case=False, na=False)
        df = df[mask]
        
    df = df.reset_index(drop=True)
    
    # Detectar columna de data per a ordenació cronològica autèntica
    date_col = next((c for c in df.columns if c.lower() in ['data', 'data_hora', 'data_inici', 'created_at']), None)
    
    if date_col:
        try:
            if 'hora' in date_col.lower() or 'created_at' in date_col.lower():
                s_dt = pd.to_datetime(df[date_col], errors='coerce')
            else:
                s_dt = pd.to_datetime(df[date_col], format='%d/%m/%Y', errors='coerce')
                if s_dt.isna().sum() > len(df) * 0.5:
                    s_dt = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
            
            df['_sort_dt'] = s_dt
            sort_cols = ['_sort_dt']
            ascending_orders = [not ordenar_recent]
            
            if pk_col in df.columns:
                df['_sort_pk'] = pd.to_numeric(df[pk_col], errors='coerce').fillna(0)
                sort_cols.append('_sort_pk')
                ascending_orders.append(not ordenar_recent)
                
            df = df.sort_values(by=sort_cols, ascending=ascending_orders).drop(columns=['_sort_dt', '_sort_pk'], errors='ignore').reset_index(drop=True)
        except Exception:
            pass
    elif pk_col in df.columns:
        try:
            df['_sort_pk'] = pd.to_numeric(df[pk_col], errors='coerce')
            if df['_sort_pk'].notna().any():
                df = df.sort_values(by='_sort_pk', ascending=not ordenar_recent).drop(columns=['_sort_pk'], errors='ignore').reset_index(drop=True)
            else:
                df = df.sort_values(by=pk_col, ascending=not ordenar_recent).drop(columns=['_sort_pk'], errors='ignore').reset_index(drop=True)
        except Exception:
            pass

    st.write("---")
    
    # Key to force re-render if needed
    editor_key = f"db_editor_{selected_table}_{ordenar_recent}"
    
    col_config = {}
    for col in df.columns:
        if col.upper() == 'DATA':
            s_d = pd.to_datetime(df[col], format="%d/%m/%Y", errors='coerce')
            if s_d.isna().sum() > len(df) * 0.5:
                s_d = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            df[col] = s_d.dt.date
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
                    # Format dates back to string
                    import datetime
                    for k, v in col_updates.items():
                        if isinstance(v, datetime.date):
                            col_updates[k] = v.strftime("%d/%m/%Y")
                            
                    row_idx = int(row_idx_str)
                    if row_idx < len(df):
                        pk_val = df.iloc[row_idx].get(pk_col)
                        if pk_val is not None and str(pk_val).strip() != "":
                            try:
                                update_db_row(selected_table, pk_col, pk_val, col_updates)
                            except Exception as e:
                                st.error(f"Error actualitzant fila ({pk_col} {pk_val}): {e}")
                                success = False
                        else:
                            st.error(f"Error: No s'ha pogut determinar la clau primària '{pk_col}' per a la fila {row_idx}.")
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
                    # Format dates back to string
                    import datetime
                    for k, v in new_row.items():
                        if isinstance(v, datetime.date):
                            new_row[k] = v.strftime("%d/%m/%Y")
                            
                    try:
                        insert_db_row(selected_table, new_row)
                    except Exception as e:
                        st.error(f"Error inserint nova fila: {e}")
                        success = False
                        
                if success:
                    st.success("✅ Tots els canvis s'han desat correctament.")
                    del st.session_state[editor_key]
                    from core.db import load_dashboard_data, get_db_tracker
                    load_dashboard_data.clear()
                    st.cache_data.clear()
                    get_db_tracker().update()
                    st.session_state["last_synced_time"] = get_db_tracker().last_update
                    st.rerun()
    else:
        st.write("📝 *Pots editar les caselles, afegir files a sota, o eliminar-les seleccionant la vora de l'esquerra i prement Suprimir.*")
