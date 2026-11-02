import streamlit as st
from modules.avatar_widget import render_header_with_avatar
from core.config_manager import get_estances_casa, save_estances_casa, IOT_CATEGORIES

def render():
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>🏠 Domòtica i Eines IoT de la Llar</h2>", "domotica")
    
    estances = get_estances_casa()
    total_estances = len(estances)
    total_iot = sum(len(e.get("iot_elements", [])) for e in estances)
    total_actius = sum(sum(1 for dev in e.get("iot_elements", []) if dev.get("actiu", True)) for e in estances)
    
    # Barra de resum KPI
    col_k1, col_k2, col_k3, col_k4 = st.columns([2.5, 2.5, 2.5, 2.5])
    with col_k1:
        st.metric("🏡 Estances a la Casa", total_estances)
    with col_k2:
        st.metric("📶 Total Eines IoT", total_iot)
    with col_k3:
        st.metric("🟢 Eines Actives", total_actius)
    with col_k4:
        st.write("")
        if st.button("⚙️ Gestionar Eines", type="primary", use_container_width=True):
            st.session_state["current_module"] = "admin"
            st.session_state["admin_active_section"] = "estances"
            st.rerun()
            
    st.markdown("---")
    
    if total_iot == 0:
        st.info("ℹ️ Encara no s'han activat eines IoT a les estances de la casa. Pots activar càmeres, detectors de presència, acumuladors Tuya, llums, endolls o sensors des de Configuració > Estances de la casa.")
    else:
        st.markdown("### 📋 Eines i Dispositius per Estances")
        
        # Grid per estances
        for idx_est, est in enumerate(estances):
            iot_elements = est.get("iot_elements", [])
            num_devs = len(iot_elements)
            ico = est.get("icona", "🏠")
            nom = est.get("nom", "Estança")
            e_id = est.get("id", f"est_{idx_est}")
            
            with st.expander(f"{ico} **{nom}** — ({num_devs} eines / sensors)", expanded=(num_devs > 0)):
                if not iot_elements:
                    st.caption("Aquesta estança no té cap eina activada.")
                else:
                    for it_idx, item in enumerate(iot_elements):
                        it_id = item.get("id", f"iot_{it_idx}")
                        it_ico = item.get("icona", "📦")
                        it_nom = item.get("nom", "Dispositiu")
                        it_cat = item.get("categoria", "altres")
                        it_cat_nom = IOT_CATEGORIES.get(it_cat, {}).get("nom", "Dispositiu")
                        it_proto = item.get("protocol", "Wi-Fi")
                        it_ent = item.get("entitat", "")
                        it_act = item.get("actiu", True)
                        
                        c_tog, c1, c2, c3, c4 = st.columns([1.5, 0.8, 4.0, 3.0, 2.7])
                        with c_tog:
                            new_tog = st.toggle("Actiu", value=it_act, key=f"dom_tog_{e_id}_{it_id}", help="Activar o desactivar aquesta eina")
                            if new_tog != it_act:
                                item["actiu"] = new_tog
                                save_estances_casa(estances)
                                st.rerun()
                        with c1:
                            st.markdown(f"<span style='font-size:1.3rem;'>{it_ico}</span>", unsafe_allow_html=True)
                        with c2:
                            estat_txt = "<span style='color:#10b981; font-weight:600;'>🟢 Actiu</span>" if it_act else "<span style='color:#64748b;'>⚪ Inactiu</span>"
                            st.markdown(f"**{it_nom}** &nbsp;{estat_txt}<br><span style='font-size:0.8rem; color:#94a3b8;'>{it_cat_nom}</span>", unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"<span style='background:#1e293b; border:1px solid #334155; padding:2px 8px; border-radius:10px; font-size:0.8rem; color:#38bdf8;'>{it_proto}</span>", unsafe_allow_html=True)
                        with c4:
                            if it_ent:
                                st.markdown(f"<code>{it_ent}</code>", unsafe_allow_html=True)
                            else:
                                st.caption("Sense referència")
                        st.markdown("<hr style='margin:3px 0; border:0; border-top:1px solid #1e293b;'>", unsafe_allow_html=True)
