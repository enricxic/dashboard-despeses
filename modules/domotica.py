def render():  
    import streamlit as st  
    col_t1, col_t2 = st.columns([9.2, 0.8], vertical_alignment="center")
    with col_t1:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>🏠 Domòtica (Home Assistant)</h2>", unsafe_allow_html=True)
    with col_t2:
        if st.button("🔙 Inici", use_container_width=True):
            st.session_state.current_module = None
            st.rerun()
