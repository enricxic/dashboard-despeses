import streamlit as st
import json
import os
from core.db import get_supabase_client, fetch_all_supabase, delete_from_db, update_db_row, log_action, insert_db_row

CONFIG_FILE = "core/config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "membres_familia": [{"nom": "Adult 1", "circunstancies": ""}, {"nom": "Adult 2", "circunstancies": ""}],
            "bancs_dashboard": ["CaixaBank", "Sabadell", "TR Cartera", "Efectiu"],
            "columna_proveidors": True,
            "columnes_resum": ["menjar", "gasolina", "restaurant", "farmacia", "neteja", "varis"],
            "activar_ia": True
        }
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

def render():
    st.title("⚙️ Administració i Configuració")
    
    tab_conf, tab_bd, tab_pap = st.tabs(["🎛️ Configuració Global", "🗄️ Bases de Dades", "🗑️ Paperera"])
    
    with tab_conf:
        st.markdown("### Configuració del Sistema")
        cfg = load_config()
        
        with st.expander("👨‍👩‍👧‍👦 Membres de la Família", expanded=True):
            st.write("Gestiona els membres i les seves preferències/al·lèrgies (Aquesta info l'usarà el Recomanador de Menús i la IA).")
            
            # Simple form to edit members
            new_members = []
            for i, mem in enumerate(cfg.get("membres_familia", [])):
                c1, c2, c3 = st.columns([2, 3, 1])
                with c1:
                    nom = st.text_input("Nom", value=mem.get("nom", ""), key=f"mem_nom_{i}")
                with c2:
                    circ = st.text_input("Circumstàncies / Al·lèrgies", value=mem.get("circunstancies", ""), key=f"mem_circ_{i}")
                with c3:
                    st.write("")
                    del_btn = st.checkbox("Esborrar", key=f"mem_del_{i}")
                if not del_btn:
                    new_members.append({"nom": nom, "circunstancies": circ})
            
            st.markdown("---")
            c1, c2 = st.columns([2, 4])
            with c1:
                add_nom = st.text_input("Nou membre (Nom)")
            with c2:
                add_circ = st.text_input("Noves circumstàncies")
            if st.button("➕ Afegir Membre"):
                if add_nom:
                    new_members.append({"nom": add_nom, "circunstancies": add_circ})
                    cfg["membres_familia"] = new_members
                    save_config(cfg)
                    st.rerun()
            
            if st.button("💾 Desar Membres", type="primary"):
                cfg["membres_familia"] = new_members
                save_config(cfg)
                st.success("Membres desats!")
                
        with st.expander("🏦 Bancs del Dashboard"):
            st.write("Selecciona quins bancs es veuran sumats al càlcul de saldo total del Dashboard.")
            bancs_text = st.text_area("Bancs (un per línia)", value="\n".join(cfg.get("bancs_dashboard", [])))
            if st.button("Desar Bancs"):
                cfg["bancs_dashboard"] = [b.strip() for b in bancs_text.split('\n') if b.strip()]
                save_config(cfg)
                st.success("Bancs actualitzats!")
                
        with st.expander("📊 Resum Mensual i Vistes"):
            c1, c2 = st.columns(2)
            with c1:
                show_prov = st.toggle("Activar Columna Proveïdors a la taula resum", value=cfg.get("columna_proveidors", True))
            with c2:
                show_ia = st.toggle("Activar Xat IA (Conseller Financer)", value=cfg.get("activar_ia", True))
                
            cols_text = st.text_area("Columnes del resum (una per línia, p. ex: menjar, gasolina)", value="\n".join(cfg.get("columnes_resum", [])))
            
            if st.button("Desar Vistes"):
                cfg["columna_proveidors"] = show_prov
                cfg["activar_ia"] = show_ia
                cfg["columnes_resum"] = [c.strip() for c in cols_text.split('\n') if c.strip()]
                save_config(cfg)
                st.success("Configuració visual actualitzada!")

    with tab_bd:
        st.markdown("### 🗄️ Visor i Editor de Bases de Dades (V2)")
        st.warning("Per fer: Moure el codi del db_editor des de l'app original aquí.")
        
    with tab_pap:
        st.markdown("### 🗑️ Registre d'Accions i Paperera")
        st.warning("Per fer: Moure el codi de la paperera aquí.")
