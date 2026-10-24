# Dashboard XiquiHouse - Bridge Forwarder per a Streamlit Cloud
# Redirigeix transparentment l'execució al punt d'entrada canònic app.py
import os
import sys
import runpy
import time

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

_canonical_app = os.path.join(_current_dir, 'app.py')

# Si es produeix una cursa transitòria de mòduls durant un git pull en calent a Streamlit Cloud,
# fem un breu reintent per assegurar que el sistema d'importació està estabilitzat.
max_retries = 3
for attempt in range(max_retries):
    try:
        runpy.run_path(_canonical_app, run_name='__main__')
        break
    except KeyError as e:
        if attempt < max_retries - 1:
            time.sleep(0.5)
        else:
            raise
