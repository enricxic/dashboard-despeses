def render():
    import streamlit as st
    from modules.avatar_widget import render_header_with_avatar
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>📹 Seguretat i Càmeres</h2>", "seguretat")

    st.write("---")
    st.info("Gestió de càmeres de vigilància, alarmes i estat de la llar.")

