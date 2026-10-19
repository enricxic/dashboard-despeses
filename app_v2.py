# Dashboard XiquiHouse - Bridge Forwarder per a Streamlit Cloud
# Redirigeix transparentment l'execució al punt d'entrada canònic app.py
# Versió actualitzada: 19/10/2026 21:55 - Gestió de Manteniment, multiselect alertaA i dies d'avís
import runpy
import os

_canonical_app = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
runpy.run_path(_canonical_app, run_name='__main__')
