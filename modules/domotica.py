import streamlit as st
from modules.avatar_widget import render_header_with_avatar
from core.config_manager import get_estances_casa, IOT_CATEGORIES

def render():
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>🏠 Domòtica i Elements IoT de la Llar</h2>", "domotica")
    
    estances = get_estances_casa()
    total_estances = len(estances)
    total_iot = sum(len(e.get("iot_elements", [])) for e in estances)
    
    # Barra de resum KPI
    col_k1, col_k2, col_k3 = st.columns([3, 3, 4])
    with col_k1:
        st.metric("🏡 Estances a la Casa", total_estances)
    with col_k2:
        st.metric("📶 Dispositius IoT Actius", total_iot)
    with col_k3:
        st.write("")
        if st.button("⚙️ Gestionar Estances i Elements IoT", type="primary", use_container_width=True):
            st.session_state["current_module"] = "admin"
            st.session_state["admin_active_section"] = "estances"
            st.rerun()
            
    st.markdown("---")
    
    if total_iot == 0:
        st.info("ℹ️ Encara no s'han associat dispositius IoT a les estances de la casa. Pots afegir sensors de temperatura, llums, endolls, bombes d'aigua o detectors d'inundació des de la secció de Configuració.")
    else:
        st.markdown("### 📋 Estat de la Llar per Estances")
        
        # Grid per estances
        for est in estances:
            iot_elements = est.get("iot_elements", [])
            num_devs = len(iot_elements)
            ico = est.get("icona", "🏠")
            nom = est.get("nom", "Estança")
            
            with st.expander(f"{ico} **{nom}** — ({num_devs} dispositius IoT)", expanded=(num_devs > 0)):
                if not iot_elements:
                    st.caption("Aquesta estança no té dispositius IoT configurats.")
                else:
                    for item in iot_elements:
                        it_ico = item.get("icona", "📦")
                        it_nom = item.get("nom", "Dispositiu")
                        it_cat = item.get("categoria", "altres")
                        it_cat_nom = IOT_CATEGORIES.get(it_cat, {}).get("nom", "Dispositiu")
                        it_proto = item.get("protocol", "Wi-Fi")
                        it_ent = item.get("entitat", "")
                        
                        c1, c2, c3, c4 = st.columns([1.5, 4.5, 3.0, 3.0])
                        with c1:
                            st.markdown(f"<span style='font-size:1.4rem;'>{it_ico}</span>", unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"**{it_nom}**<br><span style='font-size:0.8rem; color:#94a3b8;'>{it_cat_nom}</span>", unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"<span style='background:#1e293b; border:1px solid #334155; padding:2px 8px; border-radius:10px; font-size:0.8rem; color:#38bdf8;'>{it_proto}</span>", unsafe_allow_html=True)
                        with c4:
                            if it_ent:
                                st.markdown(f"<code>{it_ent}</code>", unsafe_allow_html=True)
                            else:
                                st.caption("Sense referència")
                        st.markdown("<hr style='margin:4px 0; border:0; border-top:1px solid #1e293b;'>", unsafe_allow_html=True)
