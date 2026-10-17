import streamlit as st

def render_ai_selector(key_prefix="global", default_model="Gemini (2.5 Flash)", vision_only=False) -> tuple[str, str, str]:
    """
    Renderitza un desplegable per seleccionar el motor d'IA.
    Retorna: provider, model_name, api_key
    Si vision_only=True, només mostra models amb suport de visió multimodal (Gemini).
    """
    if vision_only:
        options = [
            "Gemini (2.5 Flash)",
            "Gemini (3.8 Flash)",
            "Gemini (2.5 Pro)"
        ]
    else:
        options = [
            "Gemini (2.5 Flash)",
            "Gemini (3.8 Flash)",
            "Gemini (2.5 Pro)",
            "DeepSeek (deepseek-chat)",
            "Llama 3.1 70B",
            "Qwen 2.5 72B"
        ]
    
    # Si el valor actual de sessió no està a les opcions (ex: canvi a Visió Pura des de DeepSeek), corregir
    cur_val = st.session_state.get(f"{key_prefix}_ai_selector")
    if cur_val and cur_val not in options:
        st.session_state[f"{key_prefix}_ai_selector"] = options[0]

    # Ens assegurem que el default_model està a la llista
    default_idx = 0
    for i, opt in enumerate(options):
        if default_model in opt:
            default_idx = i
            break
            
    selected = st.selectbox("🤖 Motor d'IA", options, index=default_idx, key=f"{key_prefix}_ai_selector")
    
    if "DeepSeek" in selected:
        prov = "openrouter"
        mod = "deepseek/deepseek-chat"
        ai_key = st.secrets.get("OPENROUTER_API_KEY", "")
    elif "Llama" in selected:
        prov = "openrouter"
        mod = "meta-llama/llama-3.1-70b-instruct"
        ai_key = st.secrets.get("OPENROUTER_API_KEY", "")
    elif "Qwen" in selected:
        prov = "openrouter"
        mod = "qwen/qwen-2.5-72b-instruct"
        ai_key = st.secrets.get("OPENROUTER_API_KEY", "")
    elif "3.8 Flash" in selected:
        prov = "gemini"
        mod = "gemini-3.8-flash"
        ai_key = st.secrets.get("GEMINI_API_KEY", "")
    elif "2.5 Pro" in selected:
        prov = "gemini"
        mod = "gemini-2.5-pro"
        ai_key = st.secrets.get("GEMINI_API_KEY", "")
    else:
        prov = "gemini"
        mod = "gemini-2.5-flash"
        ai_key = st.secrets.get("GEMINI_API_KEY", "")
        
    return prov, mod, ai_key
