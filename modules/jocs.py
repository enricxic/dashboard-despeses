def render():
    import streamlit as st
    from modules.avatar_widget import render_header_with_avatar
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>🎲 Jocs i Oci Familiar</h2>", "jocs")

    st.write("---")
    st.info("Espai d'oci, jocs familiars i activitats.")

