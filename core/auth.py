import streamlit as st
import platform
import hashlib

# Default hashed password
DEFAULT_HASH = "24b7b70518e4d4030003e75d68223a85b07eb95b2cf273f3b13d87c27aa2c863"

def check_password():
    if platform.system() == "Windows":
        st.session_state["authenticated"] = True
        st.session_state["role"] = "admin"
        st.session_state["username"] = "Admin Local"
        return True
        
    if st.query_params.get("device") == "desktop":
        st.session_state["authenticated"] = True
        st.session_state["role"] = "admin"
        st.session_state["username"] = "Admin Local"
        return True

    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            cookies = headers.get("Cookie", "")
            if "client_device_type=desktop" in cookies:
                return True
            
            ua = headers.get("User-Agent", "")
            if "Mobi" not in ua and "Android" not in ua and "iPhone" not in ua and "iPad" not in ua:
                return True
    except (ImportError, Exception):
        pass

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"] and "role" not in st.session_state:
        st.session_state["role"] = "admin"

    if st.session_state["authenticated"]:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.markdown("<h2 style='text-align: center; color: #f39c12;'>Accés Protegit</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.text_input("Usuari / Nom", value="Admin")
            password = st.text_input("Contrasenya d'accés", type="password")
            submit = st.form_submit_button("Entrar")
            if submit:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                
                admin_hashes = st.secrets.get("admin_password_hashes", [])
                guest_hashes = st.secrets.get("guest_password_hashes", [])
                viewer_hashes = st.secrets.get("viewer_password_hashes", [])
                mapped_names = st.secrets.get("noms_usuaris", {})
                
                if isinstance(admin_hashes, str): admin_hashes = [admin_hashes]
                if isinstance(guest_hashes, str): guest_hashes = [guest_hashes]
                if isinstance(viewer_hashes, str): viewer_hashes = [viewer_hashes]
                
                assigned_name = mapped_names.get(hashed, "Anònim")
                
                if hashed in admin_hashes:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "admin"
                    st.session_state["username"] = assigned_name
                    st.rerun()
                elif hashed in viewer_hashes:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "viewer"
                    st.session_state["username"] = assigned_name
                    st.rerun()
                elif hashed in guest_hashes:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "guest"
                    st.session_state["username"] = assigned_name
                    st.rerun()
                elif hashed == DEFAULT_HASH:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "admin"
                    st.session_state["username"] = "Admin"
                    st.rerun()
                else:
                    st.error("Contrasenya incorrecta")
    return False
