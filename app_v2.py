# Dashboard XiquiHouse - Bridge Forwarder per a Streamlit Cloud
# Redirigeix transparentment l'execució al punt d'entrada canònic app.py
# Versió actualitzada: 21/10/2026 13:20 - Suport d'esdeveniments periòdics i repetitius a Manteniment
import runpy
import os

_canonical_app = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
runpy.run_path(_canonical_app, run_name='__main__')
