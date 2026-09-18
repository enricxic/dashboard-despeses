import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from core.db import get_supabase_client, load_dashboard_data

def show():
    st.markdown("<h2 style='color:#ef4444; margin-top:-10px;'>🌍 Sincronització de Dades (Offline)</h2>", unsafe_allow_html=True)
    st.markdown("Aquesta pantalla et permet revisar els moviments guardats localment durant una fallada de connexió (Mode Offline) i pujar-los al núvol de cop.")
    
    queue_file = "sync_queue.json"
    queue = []
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except Exception as e:
            st.error(f"Error llegint la cua de sincronització: {e}")
            
    if not queue:
        st.success("✅ Totes les teves dades estan sincronitzades! No hi ha moviments pendents a la cua local.")
        return

    st.info(f"Hi ha **{len(queue)}** moviments pendents d'enviar a Supabase.")
    
    # Taula de moviments
    df_queue = pd.DataFrame(queue)
    if not df_queue.empty:
        # Reordenar columnes i millorar visualització
        df_show = df_queue.copy()
        if 'timestamp' in df_show.columns:
            df_show['Data/Hora'] = pd.to_datetime(df_show['timestamp']).dt.strftime('%d/%m/%Y %H:%M:%S')
            del df_show['timestamp']
        df_show = df_show.rename(columns={'taula': 'Taula Afectada', 'accio': 'Acció', 'detalls': 'Detalls de la Modificació'})
        df_show['Detalls de la Modificació'] = df_show['Detalls de la Modificació'].astype(str)
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        
    st.markdown("---")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🗑️ Netejar Cua (Descartar canvis locals)", type="secondary", use_container_width=True):
            try:
                os.remove(queue_file)
                st.success("Cua esborrada.")
                st.rerun()
            except:
                pass
                
    with c2:
        if st.button("🚀 Pujar Canvis a Supabase i Consolidar", type="primary", use_container_width=True):
            supabase = get_supabase_client(st.session_state.get("role", "admin"))
            success_count = 0
            errors = []
            
            with st.spinner("Pujant dades al núvol..."):
                for item in queue:
                    try:
                        table = item.get("taula")
                        action = item.get("accio")
                        details = item.get("detalls", {})
                        
                        if action == "INSERT":
                            supabase.table(table).insert(details).execute()
                            
                        elif action == "INSERT_BULK":
                            rows = details.get("rows_inserted", [])
                            if rows:
                                supabase.table(table).insert(rows).execute()
                                
                        elif action == "UPDATE":
                            id_col = details.get("id_col")
                            id_val = details.get("id_val")
                            changes = details.get("changes", {})
                            if id_col and changes:
                                supabase.table(table).update(changes).eq(id_col, id_val).execute()
                                
                        elif action == "DELETE":
                            id_col = details.get("id_col")
                            id_val = details.get("id_val")
                            if id_col:
                                supabase.table(table).delete().eq(id_col, id_val).execute()
                                
                        success_count += 1
                    except Exception as e:
                        errors.append(f"Error a l'element de la taula {item.get('taula')}: {e}")
            
            if errors:
                st.error("S'han produït errors durant la sincronització:")
                for err in errors:
                    st.write(err)
                st.warning(f"S'han processat amb èxit {success_count} de {len(queue)} accions. Revisa la cua i torna-ho a provar.")
            else:
                st.success(f"🎉 ÈXIT! S'han sincronitzat {success_count} operacions amb el núvol.")
                # Buidem la cua
                if os.path.exists(queue_file):
                    os.remove(queue_file)
                # Apagar mode offline
                if st.session_state.get("is_offline"):
                    st.session_state["is_offline"] = False
                
                # Recarregar dades fresques del núvol
                st.cache_data.clear()
                load_dashboard_data.clear()
                st.session_state["db_synced_toast"] = True
                
                import time
                time.sleep(1.5)
                st.rerun()

def render():
    show()
