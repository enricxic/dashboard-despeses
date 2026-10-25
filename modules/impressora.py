# -*- coding: utf-8 -*-
"""
Mòdul de gestió d'impressió de tiquets per a BIXOLON SRP-275 (USB/Paral·lel).
Permet tant impressió web (window.print() via navegador) com impressió directa
raw ESC/POS (per a entorns locals Windows amb win32print).
"""

import sys
import os
from datetime import datetime
import pandas as pd

DEFAULT_PRINTER_NAME = "BIXOLON_SRP275"


def get_installed_printers():
    """Retorna la llista de noms d'impressores instal·lades a Windows."""
    if os.name != "nt":
        return []
    try:
        import win32print
        return [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
    except Exception:
        return []

def get_printer_config():
    """Recupera la configuració de la impressora des de config_manager o valors per defecte."""
    try:
        from core.config_manager import load_app_config
        cfg = load_app_config().get("periferics", {}).get("impressora", {})
        return cfg if cfg else {}
    except Exception:
        return {}

def is_local_printer_available(printer_name=DEFAULT_PRINTER_NAME):
    """Comprova si win32print està disponible i la impressora està instal·lada."""
    if os.name != "nt":
        return False
    try:
        import win32print
        printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
        return printer_name in printers
    except Exception:
        return False


def normalitzar_per_a_matriu(text):
    """Substitueix caràcters especials per assegurar compatibilitat amb impressores de matriu d'agulles."""
    if not text:
        return ""
    mapping = {
        'à': 'a', 'á': 'a', 'è': 'e', 'é': 'e', 'í': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ç': 'c', 'ñ': 'n',
        'À': 'A', 'Á': 'A', 'È': 'E', 'É': 'E', 'Í': 'I', 'Ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ú': 'U', 'Ü': 'U', 'Ç': 'C', 'Ñ': 'N',
        '·': '.'
    }
    res = []
    for c in str(text):
        res.append(mapping.get(c, c))
    return "".join(res)


def formatar_linies_tiquet(supermercat, items, total_super=0.0):
    """
    Genera una llista de línies de text per al tiquet (amplada estàndard 32 caràcters per 76mm).
    """
    ara = datetime.now().strftime("%d/%m/%Y %H:%M")
    nom_sup = normalitzar_per_a_matriu(str(supermercat).upper())[:18]
    
    linies = [
        "================================",
        "          XIQUIHOUSE            ",
        "     LLISTA DE LA COMPRA        ",
        "================================",
        f"SUPERMERCAT: {nom_sup}",
        f"DATA: {ara}",
        "--------------------------------",
        "QT  ARTICLE              PREU   ",
        "--------------------------------"
    ]
    
    calculated_total = 0.0
    
    if isinstance(items, pd.DataFrame):
        records = items.to_dict('records')
    else:
        records = list(items)
        
    for r in records:
        falta = int(r.get('falta', 1))
        nom = normalitzar_per_a_matriu(str(r.get('nom_estandard', 'Article')))[:16]
        tot_l = float(r.get('total_linia', 0.0))
        if tot_l > 0:
            tot_str = f"{tot_l:>6.2f}E"
            calculated_total += tot_l
        else:
            tot_str = "     -"
            
        linies.append(f"[ ] {falta:>2}x {nom:<16} {tot_str}")

    linies.append("--------------------------------")
    final_total = total_super if total_super > 0 else calculated_total
    linies.append(f"TOTAL ESTIMAT:        {final_total:>7.2f} EUR")
    linies.append(f"TOTAL ARTICLES:       {len(records):>7}")
    linies.append("================================")
    # 6 salts de línia físics amb caràcter final perquè l'impressora avanci el paper obligatòriament
    linies.append(" ")
    linies.append(" ")
    linies.append(" ")
    linies.append(" ")
    linies.append(" ")
    linies.append(".")
    
    return linies


def formatar_tots_els_supermercats(df_shopping):
    """
    Genera un tiquet global amb tots els productes agrupats per supermercat.
    """
    ara = datetime.now().strftime("%d/%m/%Y %H:%M")
    linies = [
        "================================",
        "          XIQUIHOUSE            ",
        "   LLISTA COMPRA (COMPLETA)     ",
        "================================",
        f"DATA: {ara}",
        "================================"
    ]
    
    gran_total = 0.0
    total_articles = 0
    
    if not df_shopping.empty:
        for superm, group in df_shopping.groupby('super_habitual'):
            nom_sup = normalitzar_per_a_matriu(str(superm).upper())[:24]
            linies.append(f">> {nom_sup}")
            linies.append("--------------------------------")
            for _, r in group.iterrows():
                falta = int(r.get('falta', 1))
                nom = normalitzar_per_a_matriu(str(r.get('nom_estandard', 'Article')))[:16]
                tot_l = float(r.get('total_linia', 0.0))
                if tot_l > 0:
                    tot_str = f"{tot_l:>6.2f}E"
                    gran_total += tot_l
                else:
                    tot_str = "     -"
                linies.append(f"[ ] {falta:>2}x {nom:<16} {tot_str}")
                total_articles += 1
            tot_s = float(group['total_linia'].sum()) if 'total_linia' in group else 0.0
            if tot_s > 0:
                linies.append(f"Subtotal {nom_sup[:14]}: {tot_s:>7.2f} EUR")
            linies.append("--------------------------------")
            
    linies.append(f"GRAN TOTAL ESTIMAT:   {gran_total:>7.2f} EUR")
    linies.append("================================")
    # 6 salts de línia físics amb caràcter final perquè l'impressora avanci el paper obligatòriament
    linies.append(" ")
    linies.append(" ")
    linies.append(" ")
    linies.append(" ")
    linies.append(" ")
    linies.append(".")
    return linies


def generar_text_tiquet(supermercat, items, total_super=0.0):
    """Retorna el text complet del tiquet en format pla."""
    if supermercat == "__ALL__":
        linies = formatar_tots_els_supermercats(items)
    else:
        linies = formatar_linies_tiquet(supermercat, items, total_super)
    return "\n".join(linies)


def imprimir_directe_bixolon(supermercat, items, total_super=0.0, printer_name=None):
    """
    Envia el tiquet directament per USB utilitzant comandes raw ESC/POS amb tall de paper.
    Només funciona en entorns locals amb accés al controlador de Windows.
    """
    cfg = get_printer_config()
    if not printer_name:
        printer_name = cfg.get("nom_controlador", DEFAULT_PRINTER_NAME)
    try:
        import win32print
    except ImportError:
        return False, "El mòdul win32print no està disponible en aquest entorn."
        
    try:
        if supermercat == "__ALL__":
            linies = formatar_tots_els_supermercats(items)
            doc_name = "Llista_Completa"
        else:
            linies = formatar_linies_tiquet(supermercat, items, total_super)
            doc_name = f"Llista_{supermercat}"
        
        # Seqüència de comandament ESC/POS:
        # \x1b@  : Inicialitzar impressora
        # \x1ba\x01 : Centrar text
        # \x1bE\x01 : Negreta ON
        # \x1bE\x00 : Negreta OFF
        # \x1ba\x00 : Alinear a l'esquerra
        # \x1dV\x00 : Tall de paper complet
        raw = bytearray()
        raw.extend(b"\x1b@") # Reset / Init
        
        # Capçalera centrada amb negreta
        raw.extend(b"\x1ba\x01\x1bE\x01")
        raw.extend(b"================================\n")
        raw.extend(b"          XIQUIHOUSE            \n")
        if supermercat == "__ALL__":
            raw.extend(b"   LLISTA COMPRA (COMPLETA)     \n")
        else:
            raw.extend(b"     LLISTA DE LA COMPRA        \n")
        raw.extend(b"================================\n")
        raw.extend(b"\x1bE\x00\x1ba\x00")
        
        # Contingut del tiquet
        for l in linies[4:-8]:
            raw.extend((l + "\n").encode('latin-1', 'replace'))
            
        # Peu centrat
        raw.extend(b"--------------------------------\n")
        tot_line = [l for l in linies if "TOTAL ESTIMAT:" in l or "GRAN TOTAL" in l]
        if tot_line:
            raw.extend(b"\x1bE\x01" + (tot_line[0] + "\n").encode('latin-1', 'replace') + b"\x1bE\x00")
            
        raw.extend(b"================================\n")
        
        # Avenç de línies i tall segons configuració
        salts = int(cfg.get("salts_linia_tall", 6))
        raw.extend(b"\n" * (salts + 1))
        if cfg.get("tall_automatic", True):
            raw.extend(b"\x1dV\x00") # GS V 0 (Auto cut)
        
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, (doc_name, None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, bytes(raw))
                win32print.EndPagePrinter(hPrinter)
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
            
        nom_mostra = "Tota la llista" if supermercat == "__ALL__" else supermercat
        return True, f"Tiquet de {nom_mostra} enviat correctament a la BIXOLON!"
    except Exception as e:
        return False, f"Error enviant a la impressora: {str(e)}"


def generar_html_imprimir_tiquet(supermercat, items, total_super=0.0):
    """
    Genera un component HTML/JS que permet imprimir directament des del navegador
    amb estil de tiquet de 76mm, compatible amb Google Chrome, Streamlit Cloud i Local.
    """
    if supermercat == "__ALL__":
        linies = formatar_tots_els_supermercats(items)
    else:
        linies = formatar_linies_tiquet(supermercat, items, total_super)
    text_tiquet = "\n".join(linies)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @page {{
        size: 76mm auto;
        margin: 0;
      }}
      body {{
        font-family: 'Courier New', Courier, monospace;
        font-size: 13px;
        line-height: 1.25;
        margin: 0;
        padding: 8px;
        color: #111;
        background: #fff;
      }}
      .ticket-box {{
        width: 100%;
        max-width: 310px;
        margin: 0 auto;
        background: #fff;
        border: 1px dashed #aaa;
        padding: 10px;
        border-radius: 4px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        box-sizing: border-box;
      }}
      pre {{
        margin: 0;
        font-family: 'Courier New', Courier, monospace;
        font-size: 12.5px;
        white-space: pre-wrap;
        word-break: break-all;
      }}
      .btn-bar {{
        margin-top: 10px;
        display: flex;
        gap: 8px;
        justify-content: center;
      }}
      .print-btn {{
        background: #27ae60;
        color: white;
        border: none;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: bold;
        border-radius: 6px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        transition: background 0.2s;
      }}
      .print-btn:hover {{
        background: #219150;
      }}
      @media print {{
        body {{
          padding: 0;
          margin: 0;
        }}
        .ticket-box {{
          border: none;
          box-shadow: none;
          padding: 2mm;
          padding-bottom: 30mm;
          max-width: 100%;
        }}
        .no-print {{
          display: none !important;
        }}
      }}
    </style>
    <script>
      function doPrint() {{
        window.focus();
        window.print();
      }}
    </script>
    </head>
    <body>
      <div class="ticket-box">
        <pre id="ticket-content">{text_tiquet}</pre>
        <div class="btn-bar no-print">
          <button class="print-btn" onclick="doPrint()">
            🖨️ Imprimir ara
          </button>
        </div>
      </div>
    </body>
    </html>
    """
    return html



def imprimir_tiquet_prova(printer_name=None):
    """
    Imprimeix un tiquet curt de prova per verificar el funcionament de la impressora i el tall de paper.
    """
    items_prova = [
        {"nom_estandard": "Comprovacio USB", "falta": 1, "total_linia": 1.25},
        {"nom_estandard": "Test Guillotina", "falta": 1, "total_linia": 2.50}
    ]
    return imprimir_directe_bixolon("TEST_PERIFERIC", items_prova, total_super=3.75, printer_name=printer_name)

def render_printer_widget(supermercat, items, total_super=0.0, key_prefix="shop"):
    """
    Renderitza a Streamlit la secció d'impressió tant per a web (navegador) com per a USB directe.
    """
    import streamlit as st
    import streamlit.components.v1 as components
    
    is_local = is_local_printer_available()
    
    col_a, col_b = st.columns([1, 1])
    
    # Estat per mostrar la previsualització del tiquet
    safe_sup = str(supermercat).replace(" ", "_")
    state_key = f"show_ticket_{key_prefix}_{safe_sup}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False
        
    with col_a:
        btn_label = f"👁️ Veure / Imprimir Tiquet" if not st.session_state[state_key] else f"❌ Amagar Tiquet"
        if st.button(btn_label, key=f"btn_toggle_{key_prefix}_{safe_sup}"):
            st.session_state[state_key] = not st.session_state[state_key]
            st.rerun()
            
    with col_b:
        if is_local:
            if st.button(f"⚡ Imprimir directe (USB BIXOLON)", key=f"btn_direct_{key_prefix}_{safe_sup}", type="primary"):
                with st.spinner("Enviant a la BIXOLON SRP-275..."):
                    ok, msg = imprimir_directe_bixolon(supermercat, items, total_super)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.caption("ℹ️ Impressió directe USB disponible amb `StartDashboard.py` en local.")
            
    if st.session_state.get(state_key, False):
        st.markdown(f"##### 🧾 Previsualització del tiquet: **{supermercat}**")
        html_code = generar_html_imprimir_tiquet(supermercat, items, total_super)
        if supermercat == "__ALL__":
            num_linies = len(formatar_tots_els_supermercats(items))
        else:
            num_linies = len(formatar_linies_tiquet(supermercat, items, total_super))
        height_px = min(max(num_linies * 20 + 80, 280), 550)
        components.html(html_code, height=height_px, scrolling=True)
