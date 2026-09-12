def render():
    import streamlit as st
    from modules.avatar_widget import render_header_with_avatar
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>🛠️ Manteniment de la Llar</h2>", "manteniment")

    st.write("---")
    st.info("Seguiment de tasques de manteniment, reparacions i revisions.")
