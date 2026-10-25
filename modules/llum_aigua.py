import streamlit as st
import os
import base64
import json
import re
import io
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

try:
    import pypdf
except ImportError:
    pypdf = None

from modules.avatar_widget import render_header_with_avatar
from core.llum_manager import (
    get_energia_llar_config,
    save_energia_llar_config,
    get_preu_llum_avui,
    calcular_finestra_acumuladors,
    load_acumuladors_config,
    save_acumuladors_config,
    load_factures_llum,
    save_factures_llum,
    add_factura_llum,
    update_factura_llum,
    delete_factura_llum,
    simular_estudi_solar
)
from core.aigua_manager import (
    load_factures_aigua,
    save_factures_aigua,
    add_factura_aigua,
    update_factura_aigua,
    delete_factura_aigua
)
from core.manteniment_manager import get_pdf_path, get_pdf_dir

# =========================================================================
# VISOR INTERACTIU DE PDF (PDF.js Canvas)
# =========================================================================

@st.dialog("📄 Visor de Document", width="large")
def view_pdf_dialog(doc_title: str, category: str, filename: str):
    """Diàleg gran per visualitzar el PDF incrustat amb PDF.js i permetre la descàrrega directa."""
    fpath = get_pdf_path(category, filename)
    st.markdown(f"<h3 style='margin-top:0; color:#f39c12;'>📄 {doc_title}</h3>", unsafe_allow_html=True)
    
    if not os.path.exists(fpath):
        st.error(f"⚠️ El fitxer no s'ha trobat a la ruta: `{fpath}`")
        return
        
    try:
        with open(fpath, "rb") as f:
            pdf_bytes = f.read()
            
        c_dl, c_ext, c_info = st.columns([1.5, 1.5, 2], vertical_alignment="center")
        with c_dl:
            st.download_button(
                label=f"📥 Descarregar {filename}",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key=f"dl_viewer_{category}_{filename}"
            )
        with c_ext:
            if os.name == 'nt' and os.path.exists(fpath):
                if st.button("🖥️ Obrir al lector extern", use_container_width=True, key=f"open_ext_{category}_{filename}"):
                    try:
                        os.startfile(fpath)
                    except Exception as err:
                        st.warning(f"No s'ha pogut obrir: {err}")
        with c_info:
            size_kb = len(pdf_bytes) / 1024
            st.markdown(f"<div style='text-align:right; color:#94a3b8; font-size:0.9rem;'>📁 <code>{category}/{filename}</code> • <b>{size_kb:.1f} KB</b></div>", unsafe_allow_html=True)
            
        b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        pdfjs_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
          <style>
            * {{ box-sizing: border-box; }}
            body {{
              margin: 0;
              padding: 0;
              background: #0f172a;
              color: #f8fafc;
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
              display: flex;
              flex-direction: column;
              align-items: center;
              min-height: 100vh;
            }}
            .toolbar {{
              position: sticky;
              top: 8px;
              z-index: 100;
              background: #1e293b;
              border: 1px solid #334155;
              padding: 6px 14px;
              border-radius: 30px;
              display: flex;
              gap: 10px;
              align-items: center;
              margin-bottom: 12px;
              box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            }}
            .toolbar button {{
              background: #334155;
              color: #f8fafc;
              border: none;
              padding: 4px 10px;
              border-radius: 6px;
              cursor: pointer;
              font-size: 0.85rem;
            }}
            .toolbar button:hover {{ background: #475569; }}
            .toolbar span {{ font-size: 0.85rem; color: #cbd5e1; }}
            #canvas-container {{
              width: 100%;
              display: flex;
              justify-content: center;
              padding: 4px;
            }}
            canvas {{
              max-width: 100%;
              box-shadow: 0 6px 20px rgba(0,0,0,0.6);
              border-radius: 4px;
              background: white;
            }}
          </style>
        </head>
        <body>
          <div class="toolbar">
            <button id="prev-page">◀</button>
            <span>Pàg. <span id="page-num">1</span> / <span id="page-count">-</span></span>
            <button id="next-page">▶</button>
            <span style="border-left: 1px solid #475569; height: 16px; margin: 0 4px;"></span>
            <button id="zoom-out">🔍-</button>
            <span id="zoom-val">100%</span>
            <button id="zoom-in">🔍+</button>
          </div>
          <div id="canvas-container">
            <canvas id="pdf-render"></canvas>
          </div>

          <script>
            const pdfData = atob("{b64}");
            pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

            let pdfDoc = null,
                pageNum = 1,
                pageRendering = false,
                pageNumPending = null,
                scale = 1.25,
                canvas = document.getElementById('pdf-render'),
                ctx = canvas.getContext('2d');

            function renderPage(num) {{
              pageRendering = true;
              pdfDoc.getPage(num).then(function(page) {{
                const viewport = page.getViewport({{ scale: scale }});
                canvas.height = viewport.height;
                canvas.width = viewport.width;

                const renderContext = {{
                  canvasContext: ctx,
                  viewport: viewport
                }};
                const renderTask = page.render(renderContext);

                renderTask.promise.then(function() {{
                  pageRendering = false;
                  if (pageNumPending !== null) {{
                    renderPage(pageNumPending);
                    pageNumPending = null;
                  }}
                }});
              }});
              document.getElementById('page-num').textContent = num;
              document.getElementById('zoom-val').textContent = Math.round(scale * 80) + "%";
            }}

            function queueRenderPage(num) {{
              if (pageRendering) {{
                pageNumPending = num;
              }} else {{
                renderPage(num);
              }}
            }}

            document.getElementById('prev-page').addEventListener('click', function() {{
              if (pageNum <= 1) return;
              pageNum--;
              queueRenderPage(pageNum);
            }});

            document.getElementById('next-page').addEventListener('click', function() {{
              if (pageNum >= pdfDoc.numPages) return;
              pageNum++;
              queueRenderPage(pageNum);
            }});

            document.getElementById('zoom-in').addEventListener('click', function() {{
              scale += 0.15;
              queueRenderPage(pageNum);
            }});

            document.getElementById('zoom-out').addEventListener('click', function() {{
              if (scale <= 0.4) return;
              scale -= 0.15;
              queueRenderPage(pageNum);
            }});

            pdfjsLib.getDocument({{ data: pdfData }}).promise.then(function(pdfDoc_) {{
              pdfDoc = pdfDoc_;
              document.getElementById('page-count').textContent = pdfDoc.numPages;
              renderPage(pageNum);
            }}).catch(function(err) {{
              document.body.innerHTML = "<div style='color:#ef4444; padding:20px;'>Error carregant el visor PDF: " + err.message + "</div>";
            }});
          </script>
        </body>
        </html>
        """
        st.components.v1.html(pdfjs_html, height=720, scrolling=True)
    except Exception as e:
        st.error(f"Error llegint el PDF: {e}")


# =========================================================================
# DIÀLEGS EDITAR / ESBORRAR FACTURA DE LLUM
# =========================================================================

@st.dialog("✏️ Editar Factura de Llum", width="medium")
def edit_factura_dialog(factura: dict):
    st.markdown(f"<h3 style='margin-top:0; color:#f39c12;'>✏️ Editar Factura #{factura.get('id')} ({factura.get('mesAny')})</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        try:
            dt_factura = datetime.strptime(factura.get("dataFactura", datetime.today().strftime("%d/%m/%Y")), "%d/%m/%Y").date()
        except Exception:
            dt_factura = datetime.today().date()
        new_df = st.date_input("Data Factura", value=dt_factura, format="DD/MM/YYYY", key="ed_fact_df")
    with col2:
        new_mes = st.text_input("Mes / Any (ex: 10/2026)", value=factura.get("mesAny", ""), key="ed_fact_mes")
        
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        try:
            dt_pi = datetime.strptime(factura.get("periodeInici", ""), "%d/%m/%Y").date()
        except Exception:
            dt_pi = datetime.today().date()
        new_pi = st.date_input("Període Inici", value=dt_pi, format="DD/MM/YYYY", key="ed_fact_pi")
    with c_p2:
        try:
            dt_pf = datetime.strptime(factura.get("periodeFi", ""), "%d/%m/%Y").date()
        except Exception:
            dt_pf = datetime.today().date()
        new_pf = st.date_input("Període Fi", value=dt_pf, format="DD/MM/YYYY", key="ed_fact_pf")
        
    new_imp = st.number_input("Import Total Factura (€) *", min_value=0.0, value=float(factura.get("importTotal", 0.0)), step=0.01, format="%.2f", key="ed_fact_imp")
    
    st.markdown("<p style='font-weight:600; color:#38bdf8; margin: 10px 0 4px 0;'>⚡ Consum d'Energia per Trams (kWh)</p>", unsafe_allow_html=True)
    ck1, ck2, ck3 = st.columns(3)
    with ck1:
        new_punta = st.number_input("🔴 Punta (P1)", min_value=0.0, value=float(factura.get("kwhPunta", 0.0)), step=1.0, format="%.1f", key="ed_fact_p1")
    with ck2:
        new_llano = st.number_input("🟡 Pla (P2)", min_value=0.0, value=float(factura.get("kwhLlano", 0.0)), step=1.0, format="%.1f", key="ed_fact_p2")
    with ck3:
        new_valle = st.number_input("🟢 Vall (P3)", min_value=0.0, value=float(factura.get("kwhValle", 0.0)), step=1.0, format="%.1f", key="ed_fact_p3")
        
    tot_kwh = round(new_punta + new_llano + new_valle, 1)
    st.caption(f"Total recalculat: **{tot_kwh} kWh**")
    
    cp1, cp2 = st.columns(2)
    with cp1:
        new_pot_dia = st.number_input("Potència Dia (kW)", min_value=0.0, value=float(factura.get("potenciaDia", 4.4)), step=0.1, key="ed_fact_pot_dia")
    with cp2:
        new_pot_nit = st.number_input("Potència Nit / Acumuladors (kW)", min_value=0.0, value=float(factura.get("potenciaNit", 5.5)), step=0.1, key="ed_fact_pot_nit")
        
    new_com = st.text_input("Comercialitzadora", value=factura.get("comercialitzadora", "Energía XXI (Bono Social)"), key="ed_fact_com")
    new_obs = st.text_input("Observacions", value=factura.get("observacions", ""), key="ed_fact_obs")
    
    if st.button("💾 Desar Canvis", type="primary", use_container_width=True, key="btn_save_ed_fact"):
        update_factura_llum(factura.get("id"), {
            "dataFactura": new_df.strftime("%d/%m/%Y"),
            "periodeInici": new_pi.strftime("%d/%m/%Y"),
            "periodeFi": new_pf.strftime("%d/%m/%Y"),
            "mesAny": new_mes.strip(),
            "importTotal": new_imp,
            "kwhPunta": new_punta,
            "kwhLlano": new_llano,
            "kwhValle": new_valle,
            "potenciaDia": new_pot_dia,
            "potenciaNit": new_pot_nit,
            "comercialitzadora": new_com.strip(),
            "observacions": new_obs.strip()
        })
        st.success("✅ Factura actualitzada correctament!")
        st.rerun()


@st.dialog("🗑️ Esborrar Factura de Llum", width="small")
def delete_factura_dialog(factura_id: int, mes_any: str, fname: str = ""):
    st.markdown(f"<h3 style='margin-top:0; color:#ef4444;'>🗑️ Eliminar Factura</h3>", unsafe_allow_html=True)
    st.write(f"Estàs segur que vols eliminar la factura de **{mes_any}** (ID #{factura_id})?")
    
    del_pdf = False
    if fname:
        del_pdf = st.checkbox(f"Esborrar també el fitxer PDF (`{fname}`)", value=True)
        
    c_yes, c_no = st.columns(2)
    with c_yes:
        if st.button("🗑️ Sí, esborrar", type="primary", use_container_width=True, key=f"btn_confirm_del_fact_{factura_id}"):
            delete_factura_llum(factura_id)
            if del_pdf and fname:
                try:
                    p = get_pdf_path("Factures_Llum", fname)
                    if os.path.exists(p):
                        os.remove(p)
                except Exception as err:
                    print(f"Error esborrant PDF factura: {err}")
            st.success("Factura eliminada!")
            st.rerun()
    with c_no:
        if st.button("Cancel·lar", use_container_width=True, key="btn_cancel_del_fact"):
            st.rerun()


# =========================================================================
# DIÀLEGS EDITAR / ESBORRAR FACTURA D'AIGUA
# =========================================================================

@st.dialog("✏️ Editar Factura d'Aigua", width="medium")
def edit_factura_aigua_dialog(factura: dict):
    st.markdown(f"<h3 style='margin-top:0; color:#0284c7;'>✏️ Editar Factura #{factura.get('id')} ({factura.get('mesAny')})</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        try:
            dt_factura = datetime.strptime(factura.get("dataFactura", datetime.today().strftime("%d/%m/%Y")), "%d/%m/%Y").date()
        except Exception:
            dt_factura = datetime.today().date()
        new_df = st.date_input("Data Factura", value=dt_factura, format="DD/MM/YYYY", key="ed_fact_aigua_df")
    with col2:
        new_mes = st.text_input("Mes / Any (ex: 10/2026)", value=factura.get("mesAny", ""), key="ed_fact_aigua_mes")
        
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        try:
            dt_pi = datetime.strptime(factura.get("periodeInici", ""), "%d/%m/%Y").date()
        except Exception:
            dt_pi = datetime.today().date()
        new_pi = st.date_input("Període Inici", value=dt_pi, format="DD/MM/YYYY", key="ed_fact_aigua_pi")
    with c_p2:
        try:
            dt_pf = datetime.strptime(factura.get("periodeFi", ""), "%d/%m/%Y").date()
        except Exception:
            dt_pf = datetime.today().date()
        new_pf = st.date_input("Període Fi", value=dt_pf, format="DD/MM/YYYY", key="ed_fact_aigua_pf")
        
    c_c1, c_c2 = st.columns(2)
    with c_c1:
        new_imp = st.number_input("Import Total Factura (€) *", min_value=0.0, value=float(factura.get("importTotal", 0.0)), step=0.01, format="%.2f", key="ed_fact_aigua_imp")
    with c_c2:
        new_m3 = st.number_input("Consum d'Aigua (m³) *", min_value=0.0, value=float(factura.get("m3Consum", 0.0)), step=0.1, format="%.2f", key="ed_fact_aigua_m3")
        
    c_lec1, c_lec2 = st.columns(2)
    with c_lec1:
        new_lec_ant = st.number_input("Lectura Anterior (m³)", min_value=0.0, value=float(factura.get("lecturaAnterior", 0.0)), step=1.0, key="ed_fact_aigua_la")
    with c_lec2:
        new_lec_act = st.number_input("Lectura Actual (m³)", min_value=0.0, value=float(factura.get("lecturaActual", 0.0)), step=1.0, key="ed_fact_aigua_lact")
        
    new_com = st.text_input("Comercialitzadora / Subministrador", value=factura.get("comercialitzadora", "Aigües de Girona"), key="ed_fact_aigua_com")
    new_obs = st.text_input("Observacions", value=factura.get("observacions", ""), key="ed_fact_aigua_obs")
    
    if st.button("💾 Desar Canvis", type="primary", use_container_width=True, key="btn_save_ed_fact_aigua"):
        update_factura_aigua(factura.get("id"), {
            "dataFactura": new_df.strftime("%d/%m/%Y"),
            "periodeInici": new_pi.strftime("%d/%m/%Y"),
            "periodeFi": new_pf.strftime("%d/%m/%Y"),
            "mesAny": new_mes.strip(),
            "importTotal": new_imp,
            "m3Consum": new_m3,
            "lecturaAnterior": new_lec_ant,
            "lecturaActual": new_lec_act,
            "comercialitzadora": new_com.strip(),
            "observacions": new_obs.strip()
        })
        st.success("✅ Factura d'aigua actualitzada correctament!")
        st.rerun()


@st.dialog("🗑️ Esborrar Factura d'Aigua", width="small")
def delete_factura_aigua_dialog(factura_id: int, mes_any: str, fname: str = ""):
    st.markdown(f"<h3 style='margin-top:0; color:#ef4444;'>🗑️ Eliminar Factura d'Aigua</h3>", unsafe_allow_html=True)
    st.write(f"Estàs segur que vols eliminar la factura de **{mes_any}** (ID #{factura_id})?")
    
    del_pdf = False
    if fname:
        del_pdf = st.checkbox(f"Esborrar també el fitxer PDF (`{fname}`)", value=True)
        
    c_yes, c_no = st.columns(2)
    with c_yes:
        if st.button("🗑️ Sí, esborrar", type="primary", use_container_width=True, key=f"btn_confirm_del_fact_aigua_{factura_id}"):
            delete_factura_aigua(factura_id)
            if del_pdf and fname:
                try:
                    p = get_pdf_path("Factures_Aigua", fname)
                    if os.path.exists(p):
                        os.remove(p)
                except Exception as err:
                    print(f"Error esborrant PDF factura aigua: {err}")
            st.success("Factura d'aigua eliminada!")
            st.rerun()
    with c_no:
        if st.button("Cancel·lar", use_container_width=True, key="btn_cancel_del_fact_aigua"):
            st.rerun()


# =========================================================================
# FUNCIONS AUXILIARS D'EXTRACCIÓ DE PDF
# =========================================================================

MESOS_CA_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'setiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
    'gener': '01', 'febrer': '02', 'març': '03', 'marc': '03', 'maig': '05', 'juny': '06', 'juliol': '07',
    'agost': '08', 'setembre': '09', 'desembre': '12'
}

def parse_spanish_date(text: str) -> str:
    m = re.search(r'(\d{1,2})\s+de\s+([a-zA-Zç]+)\s+de\s+(\d{4})', text, re.I)
    if m:
        day = int(m.group(1))
        mes_str = m.group(2).lower()
        year = int(m.group(3))
        month = MESOS_CA_ES.get(mes_str)
        if month:
            return f"{year:04d}-{month}-{day:02d}"
    return ""

def extract_data_from_pdf_bytes(pdf_bytes: bytes, filename: str = "") -> dict:
    """Extreu automàticament les dades d'una factura d'Energía XXI / PVPC."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        txt = '\n'.join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        m_imp = re.search(r'TOTAL\s+IMPORTE\s+FACTURA\s*[\n:]*\s*([\d,.]+)\s*€', txt, re.I)
        if not m_imp:
            m_imp = re.search(r'IMPORTE\s+FACTURA:?\s*[\n:]*\s*([\d,.]+)\s*€', txt, re.I)
        imp = float(m_imp.group(1).replace('.', '').replace(',', '.')) if m_imp else 0.0
        
        m_df = re.search(r'emitida\s+el\s*[\n:]*\s*([^\n]+)', txt, re.I)
        data_factura = parse_spanish_date(m_df.group(1)) if m_df else ""
        
        m_per = re.search(r'Periodo\s+de\s+consumo:?\s*[\n:]*\s*([^\n(]+)', txt, re.I)
        p_inici, p_fi = "", ""
        if m_per:
            parts = m_per.group(1).split(' a ')
            if len(parts) == 2:
                p_inici = parse_spanish_date(parts[0])
                p_fi = parse_spanish_date(parts[1])
                
        m_fn = re.match(r'(\d{2})_(\d{2})', filename)
        if m_fn:
            mes_any = f"20{m_fn.group(2)}-{m_fn.group(1)}"
        elif p_fi:
            mes_any = p_fi[:7]
        elif data_factura:
            mes_any = data_factura[:7]
        else:
            mes_any = datetime.today().strftime("%Y-%m")
            
        pot_dia = 4.4
        pot_nit = 4.4
        m_pot_p = re.search(r'Potencia\s+contratada\s+en\s+(?:punta|punta-llano):?\s*([\d,.]+)\s*kW', txt, re.I)
        if m_pot_p:
            pot_dia = float(m_pot_p.group(1).replace(',', '.'))
        m_pot_v = re.search(r'Potencia\s+contratada\s+en\s+valle:?\s*([\d,.]+)\s*kW', txt, re.I)
        if m_pot_v:
            pot_nit = float(m_pot_v.group(1).replace(',', '.'))
            
        m_c1 = re.search(r'Consumo\s+en\s+P1:?\s*[\n:]*\s*([\d,.]+)\s*kWh', txt, re.I)
        m_c2 = re.search(r'Consumo\s+en\s+P2:?\s*[\n:]*\s*([\d,.]+)\s*kWh', txt, re.I)
        m_c3 = re.search(r'Consumo\s+en\s+P3:?\s*[\n:]*\s*([\d,.]+)\s*kWh', txt, re.I)
        
        c1 = float(m_c1.group(1).replace('.', '').replace(',', '.')) if m_c1 else 0.0
        c2 = float(m_c2.group(1).replace('.', '').replace(',', '.')) if m_c2 else 0.0
        c3 = float(m_c3.group(1).replace('.', '').replace(',', '.')) if m_c3 else 0.0
        
        return {
            "data_factura": data_factura,
            "periode_inici": p_inici,
            "periode_fi": p_fi,
            "mes_any": mes_any,
            "import_total": imp,
            "kwh_punta": round(c1, 1),
            "kwh_llano": round(c2, 1),
            "kwh_valle": round(c3, 1),
            "potencia_dia": pot_dia,
            "potencia_nit": pot_nit,
            "comercialitzadora": "Energía XXI (Bono Social)",
            "observacions": "PVPC Bono Social 80%"
        }
    except Exception:
        return {}


# =========================================================================
# PESTANYA 1: CONSUM LLUM I OPTIMITZADOR D'ACUMULADORS
# =========================================================================

def render_consum_llum_tab():
    st.markdown("<p style='color:#94a3b8; font-size:0.95rem; margin:0 0 16px 0;'>Preu de la llum horari en directe (PVPC / Bo Social), optimitzador de càrrega d'acumuladors i gestió de factures per trams.</p>", unsafe_allow_html=True)

    # 1. PREU DE LA LLUM D'AVUI
    with st.container(border=True):
        c_t1, c_t2 = st.columns([3, 1], vertical_alignment="center")
        with c_t1:
            st.markdown("<h4 style='color:#f39c12; margin:0;'>⚡ Preu de la Llum en Directe (PVPC / Bo Social)</h4>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.82rem; color:#94a3b8; margin-top:4px;'>Dades oficials del mercat regulat (REE) extretes de <code>tarifaluzhora.es</code> • Tarifa 2.0TD.</div>", unsafe_allow_html=True)
        with c_t2:
            if st.button("🔄 Actualitzar Preus", use_container_width=True, key="btn_refresh_llum"):
                st.session_state.pop("cache_preu_llum", None)
                st.rerun()

        preu_data = st.session_state.get("cache_preu_llum")
        if not preu_data:
            with st.spinner("Obtenint tarifes de la llum en directe..."):
                preu_data = get_preu_llum_avui()
                st.session_state["cache_preu_llum"] = preu_data

        if preu_data and preu_data.get("hores"):
            hores = preu_data["hores"]
            preu_act = preu_data.get("preu_actual", 0.0)
            slot_act = preu_data.get("slot_actual", "")
            tram_act_lbl = preu_data.get("tram_actual_label", "")
            tram_act_col = preu_data.get("tram_actual_color", "#10b981")
            avg_pr = preu_data.get("preu_mitja", 0.0)
            h_barata = preu_data.get("hora_barata", {})
            h_cara = preu_data.get("hora_cara", {})

            # Separació clara perquè el text de dades oficials mai quedi tapat pels KPIs
            st.markdown("<div style='margin-top:14px; margin-bottom:12px;'></div>", unsafe_allow_html=True)

            # 4 KPIs
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.03); border:1px solid #334155; border-radius:8px; padding:10px 14px;'>
                    <div style='font-size:0.75rem; color:#94a3b8; text-transform:uppercase;'>Hora Actual ({slot_act})</div>
                    <div style='font-size:1.4rem; font-weight:700; color:{tram_act_col}; margin:2px 0;'>{preu_act:.4f} <span style='font-size:0.85rem;'>€/kWh</span></div>
                    <div style='font-size:0.8rem; font-weight:600; color:{tram_act_col};'>{tram_act_lbl}</div>
                </div>
                """, unsafe_allow_html=True)

            with k2:
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.03); border:1px solid #334155; border-radius:8px; padding:10px 14px;'>
                    <div style='font-size:0.75rem; color:#94a3b8; text-transform:uppercase;'>Mitjana del Dia</div>
                    <div style='font-size:1.4rem; font-weight:700; color:#38bdf8; margin:2px 0;'>{avg_pr:.4f} <span style='font-size:0.85rem;'>€/kWh</span></div>
                    <div style='font-size:0.8rem; color:#94a3b8;'>📅 {preu_data.get('data', '')}</div>
                </div>
                """, unsafe_allow_html=True)

            with k3:
                st.markdown(f"""
                <div style='background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:8px; padding:10px 14px;'>
                    <div style='font-size:0.75rem; color:#10b981; text-transform:uppercase;'>🟢 Hora Més Barata</div>
                    <div style='font-size:1.4rem; font-weight:700; color:#10b981; margin:2px 0;'>{h_barata.get('preu', 0.0):.4f} <span style='font-size:0.85rem;'>€/kWh</span></div>
                    <div style='font-size:0.8rem; font-weight:600; color:#cbd5e1;'>⏰ {h_barata.get('slot', '')}</div>
                </div>
                """, unsafe_allow_html=True)

            with k4:
                st.markdown(f"""
                <div style='background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:8px; padding:10px 14px;'>
                    <div style='font-size:0.75rem; color:#ef4444; text-transform:uppercase;'>🔴 Hora Més Cara</div>
                    <div style='font-size:1.4rem; font-weight:700; color:#ef4444; margin:2px 0;'>{h_cara.get('preu', 0.0):.4f} <span style='font-size:0.85rem;'>€/kWh</span></div>
                    <div style='font-size:0.8rem; font-weight:600; color:#cbd5e1;'>⏰ {h_cara.get('slot', '')}</div>
                </div>
                """, unsafe_allow_html=True)

            # OPTIMITZADOR D'ACUMULADORS (DINÀMIC I MODULAR)
            st.markdown("<div style='margin-top:32px; margin-bottom:8px;'></div>", unsafe_allow_html=True)
            cfg_acum = load_acumuladors_config()
            energia_cfg = get_energia_llar_config()
            pot_punta = float(energia_cfg.get("potencia_punta_kw", 4.4))
            pot_vall = float(energia_cfg.get("potencia_vall_kw", 5.5))
            acumuladors_llista = energia_cfg.get("acumuladors", [])
            if not acumuladors_llista:
                acumuladors_llista = [
                    {"id": "acum_1", "nom": "Menjador", "zona": "Menjador / Planta Baixa", "watts": 4000, "franja": "nit", "hores_defecte": 5, "color": "#fbbf24", "icona": "🛋️"},
                    {"id": "acum_2", "nom": "Passadís 2a Planta", "zona": "Passadís 2a Planta", "watts": 2000, "franja": "migdia", "hores_defecte": 3, "color": "#38bdf8", "icona": "🪜"}
                ]

            with st.container(border=True):
                st.markdown(f"""
                <div style='display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; margin-bottom:12px; gap:8px;'>
                    <div style='display:flex; align-items:center; gap:8px;'>
                        <span style='font-size:1.25rem;'>🔥</span>
                        <span style='font-size:1.1rem; font-weight:700; color:#f39c12;'>Optimitzador de Càrrega d'Acumuladors de Calor</span>
                    </div>
                    <div style='font-size:0.8rem; color:#94a3b8;'>Càlcul independent i emmagatzematge d'hores per a cadascun dels teus {len(acumuladors_llista)} acumuladors</div>
                </div>
                """, unsafe_allow_html=True)

                cols_ac = st.columns(len(acumuladors_llista), gap="large")
                opt_finestres_acum = {}

                for idx_ac, (col_ac, acum) in enumerate(zip(cols_ac, acumuladors_llista)):
                    with col_ac:
                        ac_id = acum.get("id", f"acum_{idx_ac+1}")
                        ac_nom = acum.get("nom", f"Acumulador {idx_ac+1}")
                        ac_watts = int(acum.get("watts", 2000))
                        ac_franja = acum.get("franja", "nit")
                        ac_color = acum.get("color", "#fbbf24" if idx_ac == 0 else "#38bdf8")
                        ac_icona = acum.get("icona", "🔥")
                        ac_def_h = int(acum.get("hores_defecte", 4))

                        if ac_franja == "nit":
                            p_contractada = pot_vall
                            franja_tag = f"{p_contractada:,.1f} kW Nit (Vall)"
                            desc_franja = "Franja nocturna (00:00 - 08:00h)"
                            badge_bg = "#065f46"
                            badge_fg = "#a7f3d0"
                        else:
                            p_contractada = pot_punta
                            franja_tag = f"{p_contractada:,.1f} kW Migdia Solar"
                            desc_franja = "Franja solar (11:00 - 19:00h)"
                            badge_bg = "#075985"
                            badge_fg = "#bae6fd"

                        marge_lliure = max(0.0, p_contractada - (ac_watts / 1000.0))

                        st.markdown(f"""
                        <div style='background:rgba(255,255,255,0.03); border:1px solid {ac_color}55; border-radius:8px; padding:10px 12px; margin-bottom:10px;'>
                            <div style='display:flex; justify-content:space-between; align-items:center;'>
                                <b style='color:{ac_color}; font-size:0.95rem;'>{ac_icona} {ac_nom} ({ac_watts:,} W)</b>
                                <span style='background:{badge_bg}; color:{badge_fg}; font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:600;'>{franja_tag}</span>
                            </div>
                            <div style='font-size:0.75rem; color:#94a3b8; margin-top:4px;'>{desc_franja} • Resten {marge_lliure:,.1f} kW lliures per a la casa.</div>
                        </div>
                        """, unsafe_allow_html=True)

                        key_cfg = f"hores_{ac_id}"
                        if key_cfg not in cfg_acum and f"hores_{ac_watts}w" in cfg_acum:
                            key_cfg = f"hores_{ac_watts}w"

                        cur_h = int(cfg_acum.get(key_cfg, ac_def_h))
                        new_h = st.slider(
                            f"Hores de càrrega ({ac_nom}):",
                            min_value=1,
                            max_value=8,
                            value=min(max(cur_h, 1), 8),
                            step=1,
                            key=f"slider_h_{ac_id}_{idx_ac}",
                            help=f"Tria quantes hores necessita carregar l'aparell {ac_nom} ({ac_watts} W)."
                        )
                        if new_h != cur_h:
                            cfg_acum[key_cfg] = new_h
                            save_acumuladors_config(cfg_acum)

                        opt_res = calcular_finestra_acumuladors(hores, durada_hores=new_h, franja=ac_franja)
                        if opt_res.get("millor_finestra"):
                            w = opt_res["millor_finestra"]
                            cost_cicle = w['preu_mitja'] * (ac_watts / 1000.0) * new_h
                            icona_franja = "✨" if ac_franja == "nit" else "☀️"
                            st.markdown(f"""
                            <div style='background:rgba(255,255,255,0.04); border:1px solid {ac_color}66; border-radius:8px; padding:12px 14px; margin-top:8px;'>
                                <div style='font-size:0.75rem; color:{ac_color}; font-weight:700; text-transform:uppercase;'>{icona_franja} Finestra Òptima ({new_h}h):</div>
                                <div style='font-size:1.3rem; font-weight:700; color:{ac_color}; margin:4px 0;'>⏰ {w['rang_text']}</div>
                                <div style='font-size:0.83rem; color:#e2e8f0; line-height:1.4;'>
                                    Preu mitjà finestra: <b style='color:#10b981;'>{w['preu_mitja']:.4f} €/kWh</b><br>
                                    Estalvi vs mitjana: <b style='color:#38bdf8;'>-{opt_res.get('estalvi_percent', 0.0)}%</b> • Potència: <b style='color:{ac_color};'>{p_contractada:,.1f} kW</b><br>
                                    Cost estimat cicle ({new_h}h a {ac_watts/1000.0:,.1f}kW): <b style='color:{ac_color};'>{cost_cicle:.2f} €</b>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            opt_finestres_acum[ac_id] = {
                                "nom": ac_nom,
                                "watts": ac_watts,
                                "color": ac_color,
                                "franja_label": franja_tag,
                                "hores": [h_item["slot"] for h_item in w.get("hores", [])]
                            }

            # CONFIGURADOR MODULAR DE POTÈNCIES I ACUMULADORS
            st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
            with st.expander("⚙️ Configurar Potències Contractades i Aparells Acumuladors", expanded=False):
                st.markdown("<p style='font-size:0.85rem; color:#94a3b8; margin-bottom:10px;'>Ajusta les potències contractades de la teva instal·lació i personalitza els acumuladors/radiadors de càrrega.</p>", unsafe_allow_html=True)
                c_p1, c_p2 = st.columns(2)
                with c_p1:
                    edit_p_punta = st.number_input("Potència Punta / Dia (kW):", min_value=1.0, max_value=15.0, value=float(pot_punta), step=0.1, key="num_pot_punta")
                with c_p2:
                    edit_p_vall = st.number_input("Potència Vall / Nit (kW):", min_value=1.0, max_value=15.0, value=float(pot_vall), step=0.1, key="num_pot_vall")

                st.markdown("<b style='color:#cbd5e1; font-size:0.9rem;'>Llista d'Aparells Acumuladors:</b>", unsafe_allow_html=True)
                acum_actualitzats = []
                for j_ac, ac_item in enumerate(acumuladors_llista):
                    c_e1, c_e2, c_e3, c_e4 = st.columns([2.2, 1.2, 1.3, 0.8])
                    e_nom = c_e1.text_input(f"Nom #{j_ac+1}", value=ac_item.get("nom", f"Acumulador {j_ac+1}"), key=f"ac_nom_edit_{j_ac}")
                    e_watts = c_e2.number_input(f"Watts #{j_ac+1}", min_value=200, max_value=10000, value=int(ac_item.get("watts", 2000)), step=100, key=f"ac_watts_edit_{j_ac}")
                    f_idx = 0 if ac_item.get("franja", "nit") == "nit" else 1
                    e_franja = c_e3.selectbox(f"Franja #{j_ac+1}", ["nit", "migdia"], index=f_idx, key=f"ac_franja_edit_{j_ac}")
                    e_col = c_e4.color_picker(f"Color #{j_ac+1}", value=ac_item.get("color", "#fbbf24" if j_ac == 0 else "#38bdf8"), key=f"ac_col_edit_{j_ac}")
                    acum_actualitzats.append({
                        "id": ac_item.get("id", f"acum_{j_ac+1}"),
                        "nom": e_nom.strip(),
                        "zona": ac_item.get("zona", e_nom.strip()),
                        "watts": int(e_watts),
                        "franja": e_franja,
                        "hores_defecte": ac_item.get("hores_defecte", 4),
                        "color": e_col,
                        "icona": ac_item.get("icona", "🔥")
                    })

                if st.button("💾 Desar Paràmetres d'Energia i Acumuladors", key="btn_save_energia_llar_cfg"):
                    nova_cfg_e = {
                        "potencia_punta_kw": round(float(edit_p_punta), 2),
                        "potencia_vall_kw": round(float(edit_p_vall), 2),
                        "acumuladors": acum_actualitzats
                    }
                    if save_energia_llar_config(nova_cfg_e):
                        st.success("✅ Configuració d'energia desada correctament!")
                        st.rerun()
                    else:
                        st.error("❌ Error en desar la configuració d'energia.")

            # GUIA ESTRATÈGICA I CONSELLS (DESPLEGABLE MODULAR)
            st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
            with st.expander("💡 Guia Estratègica i Consells d'Ús dels Acumuladors", expanded=False):
                st.markdown(f"""
                ### 🎯 Estratègia Òptima d'Ús de la Potència i Acumuladors
                
                Tens una configuració amb **doble potència contractada** ({pot_vall:,.1f} kW nit / {pot_punta:,.1f} kW dia) i acumuladors tèrmics:
                - **Càrrega Nocturna (Vall):** Aprofita les hores de menor peatge (00:00 - 08:00h) i la major potència contractada ({pot_vall:,.1f} kW) per carregar els aparells de major potència.
                - **Càrrega Migdia Solar (Vall solar):** Aprofita la gran aportació de parcs fotovoltaics (14:00 - 17:00h), on el cost real del mercat elèctric s'enfonsa a valors mínims.
                - **Prevenció de sobrecàrrega (ICP):** Distribuir la càrrega entre la nit i el migdia evita encendre tots els equips simultàniament i garanteix no superar la potència màxima del comptador.
                """, unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # GRÀFIC HORARI 24H (PLOTLY) AMB SELECTOR DE COLOR I LLEGENDA
            # -----------------------------------------------------------------
            c_gh1, c_gh2 = st.columns([1.5, 2.5], vertical_alignment="center")
            with c_gh1:
                st.markdown("<p style='font-size:0.95rem; font-weight:700; color:#cbd5e1; margin:0;'>📊 Corba Horària de Preus del Dia (24h)</p>", unsafe_allow_html=True)
            with c_gh2:
                mode_color = st.radio(
                    "Colors de les barres:",
                    ["🕒 Trams Regulats (Vall / Pla / Punta)", "💶 Preu Real (Barata 🟢 / Mitjana 🟡 / Cara 🔴)"],
                    horizontal=True,
                    index=0,
                    key="rad_color_mode_llum",
                    help="Tria si vols veure les barres segons els trams oficials de potència/peatges 2.0TD o segons el preu real de l'energia."
                )

            # Càlcul de llindars per a la coloració per preu real
            all_prices = sorted([h["preu"] for h in hores])
            th_low = all_prices[7] if len(all_prices) >= 8 else 0.10
            th_high = all_prices[15] if len(all_prices) >= 16 else 0.20

            x_slots = [h["slot"] for h in hores]
            y_prices = [h["preu"] for h in hores]
            
            # Tria de colors segons el mode
            if "Preu Real" in mode_color:
                colors = []
                hover_texts = []
                for h in hores:
                    p = h["preu"]
                    if p <= th_low:
                        colors.append("#10b981") # Verd
                        nivell_txt = "🟢 Molt Barata" if p == min(all_prices) else "🟢 Barata"
                    elif p > th_high:
                        colors.append("#ef4444") # Vermell
                        nivell_txt = "🔴 Molt Cara" if p == max(all_prices) else "🔴 Cara"
                    else:
                        colors.append("#f59e0b") # Groc/Ambre
                        nivell_txt = "🟡 Mitjana / Normal"
                    hover_texts.append(f"<b>Hora: {h['slot']}</b><br>Preu: <b>{p:.4f} €/kWh</b><br>Nivell: {nivell_txt}<br>Tram 2.0TD: {h['tram_label']}")
            else:
                colors = [h["tram_color"] for h in hores]
                hover_texts = [f"<b>Hora: {h['slot']}</b><br>Preu: <b>{h['preu']:.4f} €/kWh</b><br>Tram 2.0TD: {h['tram_label']}" for h in hores]
            
            border_colors = []
            border_widths = []
            for h in hores:
                slot = h["slot"]
                matched_color = None
                for ac_info in opt_finestres_acum.values():
                    if slot in ac_info.get("hores", []):
                        matched_color = ac_info["color"]
                        break
                if matched_color:
                    border_colors.append(matched_color)
                    border_widths.append(3)
                elif h.get("actual"):
                    border_colors.append("#ffffff")
                    border_widths.append(2)
                else:
                    border_colors.append("rgba(0,0,0,0)")
                    border_widths.append(0)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=x_slots,
                y=y_prices,
                text=[f"{p:.3f}€" for p in y_prices],
                textposition="outside",
                textfont=dict(size=9, color="#cbd5e1"),
                cliponaxis=False,
                marker=dict(
                    color=colors,
                    line=dict(color=border_colors, width=border_widths)
                ),
                hovertext=hover_texts,
                hoverinfo="text",
                name="Preu €/kWh"
            ))

            fig.add_hline(
                y=avg_pr,
                line_dash="dash",
                line_color="#38bdf8",
                annotation_text=f"Mitjana: {avg_pr:.4f} €/kWh",
                annotation_position="top left",
                annotation_font=dict(color="#38bdf8", size=10)
            )

            max_y_val = max(y_prices) if y_prices else 0.4
            fig.update_layout(
                margin=dict(l=10, r=10, t=30, b=25),
                height=310,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                xaxis=dict(showgrid=False, color="#94a3b8", tickfont=dict(size=10)),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="#334155",
                    color="#94a3b8",
                    tickformat=".3f",
                    title="€/kWh",
                    title_font=dict(size=11, color="#94a3b8"),
                    range=[0, max_y_val * 1.18]
                ),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            # LLEGENDA EXPLICATIVA DELS COLORS
            badge_items = []
            for ac_id, ac_info in opt_finestres_acum.items():
                badge_items.append(
                    f"<div><span style='border:2px solid {ac_info['color']}; border-radius:3px; padding:0 4px; font-weight:700; color:{ac_info['color']};'>🔲 Vora {ac_info['nom']}</span>: <b>Finestra {ac_info['watts']:,}W {ac_info['nom']}</b> ({ac_info['franja_label']}).</div>"
                )
            badge_items.append(f"<div><span style='border:2px solid #ffffff; border-radius:3px; padding:0 4px; font-weight:700; color:#ffffff;'>🔲 Vora blanca</span>: <b>Hora actual</b> ({slot_act}).</div>")

            vora_notes_html = f"""
                <div style='margin-top:8px; padding-top:6px; border-top:1px dashed #334155; display:flex; gap:20px; flex-wrap:wrap; font-size:0.8rem; color:#94a3b8;'>
                    {''.join(badge_items)}
                </div>
            """

            if "Preu Real" in mode_color:
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.02); border:1px solid #334155; border-radius:8px; padding:8px 14px; margin-top:2px;'>
                    <div style='font-size:0.8rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;'>📖 Llegenda de Colors (Segons el Preu Real de l'Energia):</div>
                    <div style='display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; font-size:0.82rem;'>
                        <div><span style='color:#10b981; font-weight:700;'>🟢 Barata (≤ {th_low:.4f} €/kWh)</span>: Hores amb el cost mínim (ideal per a rentadores i consums).</div>
                        <div><span style='color:#f59e0b; font-weight:700;'>🟡 Mitjana ({th_low:.4f} - {th_high:.4f} €)</span>: Cost moderat al voltant de la mitjana.</div>
                        <div><span style='color:#ef4444; font-weight:700;'>🔴 Cara (> {th_high:.4f} €/kWh)</span>: Hores de màxim preu (evitar grans electrodomèstics).</div>
                    </div>
                    {vora_notes_html}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:rgba(255,255,255,0.02); border:1px solid #334155; border-radius:8px; padding:8px 14px; margin-top:2px;'>
                    <div style='font-size:0.8rem; font-weight:700; color:#cbd5e1; margin-bottom:4px;'>📖 Llegenda de Colors (Trams Oficials 2.0TD de Peatges i Potència):</div>
                    <div style='display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; font-size:0.82rem;'>
                        <div><span style='color:#10b981; font-weight:700;'>🟢 Tram Vall (00h-08h i caps de setmana)</span>: Peatge mínim i <b>potència de {pot_vall:,.1f} kW</b> (acumuladors).</div>
                        <div><span style='color:#f59e0b; font-weight:700;'>🟡 Tram Pla (08-10h, 14-18h, 22-24h)</span>: Peatge mig i <b>{pot_punta:,.1f} kW</b>. <i>(Nota: 14h-17h sol ser molt barat per l'energia solar!)</i></div>
                        <div><span style='color:#ef4444; font-weight:700;'>🔴 Tram Punta (10-14h i 18-22h)</span>: Peatge màxim i <b>{pot_punta:,.1f} kW</b>.</div>
                    </div>
                    {vora_notes_html}
                </div>
                """, unsafe_allow_html=True)

            with st.expander("ℹ️ Informació sobre Trams Horaris i Potències (Bo Social / 2.0TD)"):
                st.markdown(f"""
                - **🟢 Tram Vall (P3)**: De dilluns a divendres de **00:00 a 08:00 h**, i **les 24 hores dels caps de setmana i festius nacionals**.
                  - *Potència contractada*: **{pot_vall:,.1f} kW** (ideal per a la càrrega dels acumuladors de calor).
                - **🟡 Tram Pla (P2)**: De dilluns a divendres de **08:00 a 10:00 h**, de **14:00 a 18:00 h** i de **22:00 a 24:00 h**.
                  - *Potència contractada*: **{pot_punta:,.1f} kW**.
                - **🔴 Tram Punta (P1)**: De dilluns a divendres de **10:00 a 14:00 h** i de **18:00 a 22:00 h**.
                  - *Potència contractada*: **{pot_punta:,.1f} kW**.
                """)
        else:
            st.warning("⚠️ No s'han pogut carregar les dades de preus en directe en aquest moment. Pots tornar-ho a provar amb el botó d'actualitzar.")

    # 2. HISTÒRIC I FACTURES DE LLUM
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    factures = load_factures_llum()

    if "show_add_factura_llum" not in st.session_state:
        st.session_state.show_add_factura_llum = False

    c_fac_h, c_fac_btn = st.columns([3, 1], vertical_alignment="center")
    with c_fac_h:
        st.markdown("<h4 style='color:#f39c12; margin:0;'>📄 Registre de Factures i Consum per Tram</h4>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; color:#94a3b8;'>Evolució mensual dels kWh consumits per tram (Punta, Pla, Vall) i cost total.</div>", unsafe_allow_html=True)
    with c_fac_btn:
        if not st.session_state.show_add_factura_llum:
            if st.button("➕ Nova Factura Llum", type="primary", use_container_width=True, key="btn_open_add_factura_llum"):
                st.session_state.show_add_factura_llum = True
                st.rerun()
        else:
            if st.button("✖️ Tancar formulari", type="secondary", use_container_width=True, key="btn_close_add_factura_llum"):
                st.session_state.show_add_factura_llum = False
                st.rerun()

    # FORMULARI D'ALTA LLUM
    if st.session_state.show_add_factura_llum:
        with st.container(border=True):
            st.markdown("<h5 style='color:#38bdf8; margin-top:0;'>➕ Introduir Nova Factura Elèctrica</h5>", unsafe_allow_html=True)
            
            # File uploader en primer lloc per permetre l'autoextracció
            pdf_file = st.file_uploader(
                "📄 Selecciona o arrossega la factura en PDF:",
                type=["pdf"],
                key="uploader_nova_factura_llum",
                help="Si adjuntes el PDF d'Energía XXI, el sistema n'extraurà automàticament totes les dades i arxivarà el fitxer."
            )

            if "last_processed_llum_pdf" not in st.session_state:
                st.session_state.last_processed_llum_pdf = None

            if pdf_file is not None and pdf_file.name != st.session_state.last_processed_llum_pdf:
                st.session_state.last_processed_llum_pdf = pdf_file.name
                ext = extract_data_from_pdf_bytes(pdf_file.getvalue(), pdf_file.name)
                if ext:
                    st.session_state.in_fact_mes = ext.get("mes_any", "")
                    st.session_state.in_fact_imp = float(ext.get("import_total", 0.0))
                    st.session_state.in_fact_p1 = float(ext.get("kwh_punta", 0.0))
                    st.session_state.in_fact_p2 = float(ext.get("kwh_llano", 0.0))
                    st.session_state.in_fact_p3 = float(ext.get("kwh_valle", 0.0))
                    st.session_state.in_fact_pot_dia = float(ext.get("potencia_dia", 4.4))
                    st.session_state.in_fact_pot_nit = float(ext.get("potencia_nit", 5.5))
                    st.session_state.in_fact_com = ext.get("comercialitzadora", "Energía XXI (Bono Social)")
                    st.session_state.in_fact_obs = ext.get("observacions", "PVPC Bono Social 80%")
                    if ext.get("data_factura"):
                        try:
                            st.session_state.in_fact_df = datetime.strptime(ext["data_factura"], "%Y-%m-%d").date()
                        except Exception:
                            pass
                    if ext.get("periode_inici"):
                        try:
                            st.session_state.in_fact_pi = datetime.strptime(ext["periode_inici"], "%Y-%m-%d").date()
                        except Exception:
                            pass
                    if ext.get("periode_fi"):
                        try:
                            st.session_state.in_fact_pf = datetime.strptime(ext["periode_fi"], "%Y-%m-%d").date()
                        except Exception:
                            pass

            if pdf_file is not None and st.session_state.get("in_fact_imp", 0.0) > 0:
                st.success("✨ S'han detectat i extret automàticament les dades del PDF! Revisa-les a continuació.")

            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                in_data_fact = st.date_input("Data Emissió Factura *", value=st.session_state.get("in_fact_df", datetime.today().date()), format="DD/MM/YYYY", key="in_fact_df")
            with f_col2:
                in_mes_any = st.text_input("Mes / Any de Referència *", value=st.session_state.get("in_fact_mes", datetime.today().strftime("%Y-%m")), help="Ex: 2026-09", key="in_fact_mes")
            with f_col3:
                in_import = st.number_input("Import Total Factura (€) *", min_value=0.0, value=float(st.session_state.get("in_fact_imp", 0.0)), step=0.01, format="%.2f", key="in_fact_imp")

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                in_p_inici = st.date_input("Període de Facturació: Des de", value=st.session_state.get("in_fact_pi", datetime.today().date() - timedelta(days=30)), format="DD/MM/YYYY", key="in_fact_pi")
            with p_col2:
                in_p_fi = st.date_input("Fins a", value=st.session_state.get("in_fact_pf", datetime.today().date()), format="DD/MM/YYYY", key="in_fact_pf")

            st.markdown("<p style='font-weight:600; color:#cbd5e1; margin:8px 0 2px 0;'>⚡ Consum d'Energia per Tram (kWh)</p>", unsafe_allow_html=True)
            c_k1, c_k2, c_k3, c_k4 = st.columns(4)
            with c_k1:
                in_kwh_punta = st.number_input("🔴 Punta (P1) kWh", min_value=0.0, value=float(st.session_state.get("in_fact_p1", 0.0)), step=0.1, format="%.1f", key="in_fact_p1")
            with c_k2:
                in_kwh_llano = st.number_input("🟡 Pla (P2) kWh", min_value=0.0, value=float(st.session_state.get("in_fact_p2", 0.0)), step=0.1, format="%.1f", key="in_fact_p2")
            with c_k3:
                in_kwh_valle = st.number_input("🟢 Vall (P3) kWh", min_value=0.0, value=float(st.session_state.get("in_fact_p3", 0.0)), step=0.1, format="%.1f", key="in_fact_p3")
            with c_k4:
                sum_kwh = round(in_kwh_punta + in_kwh_llano + in_kwh_valle, 1)
                st.metric("Total kWh", f"{sum_kwh} kWh")

            pot_col1, pot_col2 = st.columns(2)
            with pot_col1:
                in_pot_dia = st.number_input("Potència Dia (kW)", min_value=0.0, value=float(st.session_state.get("in_fact_pot_dia", 4.4)), step=0.1, key="in_fact_pot_dia")
            with pot_col2:
                in_pot_nit = st.number_input("Potència Nit / Acumuladors (kW)", min_value=0.0, value=float(st.session_state.get("in_fact_pot_nit", 5.5)), step=0.1, key="in_fact_pot_nit")

            c_extra1, c_extra2 = st.columns(2)
            with c_extra1:
                in_com = st.text_input("Comercialitzadora", value=st.session_state.get("in_fact_com", "Energía XXI (Bono Social)"), key="in_fact_com")
            with c_extra2:
                in_obs = st.text_input("Observacions", value=st.session_state.get("in_fact_obs", "PVPC Bono Social 80%"), key="in_fact_obs")

            c_save, c_cancel = st.columns([2, 1])
            with c_save:
                if st.button("💾 Desar Factura a la Base de Dades", type="primary", use_container_width=True, key="btn_save_new_fact"):
                    pdf_fname = ""
                    if pdf_file is not None:
                        try:
                            dest_dir = get_pdf_dir("Factures_Llum")
                            os.makedirs(dest_dir, exist_ok=True)
                            pdf_fname = pdf_file.name
                            dest_path = os.path.join(dest_dir, pdf_fname)
                            with open(dest_path, "wb") as f_out:
                                f_out.write(pdf_file.getbuffer())
                        except Exception as err:
                            st.warning(f"No s'ha pogut desar el fitxer PDF: {err}")
                            pdf_fname = ""

                    add_factura_llum(
                        data_factura=in_data_fact.strftime("%Y-%m-%d"),
                        periode_inici=in_p_inici.strftime("%Y-%m-%d"),
                        periode_fi=in_p_fi.strftime("%Y-%m-%d"),
                        mes_any=in_mes_any.strip(),
                        import_total=in_import,
                        kwh_punta=in_kwh_punta,
                        kwh_llano=in_kwh_llano,
                        kwh_valle=in_kwh_valle,
                        potencia_dia=in_pot_dia,
                        potencia_nit=in_pot_nit,
                        comercialitzadora=in_com.strip(),
                        pdf_fitxer=pdf_fname,
                        observacions=in_obs.strip()
                    )
                    st.session_state.show_add_factura_llum = False
                    st.session_state.last_processed_llum_pdf = None
                    st.success("✅ Factura desada correctament a Supabase i a la còpia local!")
                    st.rerun()
            with c_cancel:
                if st.button("❌ Cancel·lar", use_container_width=True, key="btn_cancel_add_llum"):
                    st.session_state.show_add_factura_llum = False
                    st.session_state.last_processed_llum_pdf = None
                    st.rerun()

    # KPIS HISTÒRICS I GRÀFIC LLUM
    if factures:
        df_f = pd.DataFrame(factures)
        if "mesAny" in df_f.columns and len(df_f) > 0:
            max_imp = float(df_f["importTotal"].max()) if len(df_f) > 0 else 100.0
            max_kwh = float(df_f["kwhTotal"].max()) if len(df_f) > 0 else 1000.0

            fig_hist = go.Figure()
            fig_hist.add_trace(go.Bar(
                name="🟢 Vall (P3)",
                x=df_f["mesAny"],
                y=df_f["kwhValle"],
                marker_color="#10b981",
                hovertemplate="Vall: %{y:.1f} kWh<extra></extra>"
            ))
            fig_hist.add_trace(go.Bar(
                name="🟡 Pla (P2)",
                x=df_f["mesAny"],
                y=df_f["kwhLlano"],
                marker_color="#f59e0b",
                hovertemplate="Pla: %{y:.1f} kWh<extra></extra>"
            ))
            fig_hist.add_trace(go.Bar(
                name="🔴 Punta (P1)",
                x=df_f["mesAny"],
                y=df_f["kwhPunta"],
                marker_color="#ef4444",
                hovertemplate="Punta: %{y:.1f} kWh<extra></extra>"
            ))

            # Etiquetes de preu total per sobre de les barres (per sobre de tots els colors)
            fig_hist.add_trace(go.Scatter(
                name="Preu Factura (€)",
                x=df_f["mesAny"],
                y=df_f["kwhTotal"],
                mode="text",
                text=[f"<b>{float(v):.1f}€</b>" for v in df_f["importTotal"]],
                textposition="top center",
                textfont=dict(size=9.5, color="#38bdf8"),
                showlegend=False,
                cliponaxis=False,
                hoverinfo="skip"
            ))

            # Línia de tendència d'import (sense text a dins per evitar solapaments)
            fig_hist.add_trace(go.Scatter(
                name="Import Factura (€)",
                x=df_f["mesAny"],
                y=df_f["importTotal"],
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="rgba(56, 189, 248, 0.55)", width=2),
                marker=dict(size=5, color="#38bdf8"),
                hovertemplate="Cost: %{y:.2f} €<extra></extra>"
            ))

            fig_hist.update_layout(
                barmode="stack",
                margin=dict(l=10, r=10, t=35, b=30),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                xaxis=dict(showgrid=False, color="#94a3b8"),
                yaxis=dict(
                    title="Energia (kWh)",
                    title_font=dict(color="#94a3b8", size=11),
                    showgrid=True,
                    gridcolor="#334155",
                    color="#94a3b8",
                    range=[0, max_kwh * 1.18]
                ),
                yaxis2=dict(
                    title="Import (€)",
                    title_font=dict(color="#38bdf8", size=11),
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    color="#38bdf8",
                    range=[0, max_imp * 1.25]
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color="#cbd5e1", size=11)
                )
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#f39c12; margin:16px 0 8px 0;'>📋 Històric de Factures de Llum</p>", unsafe_allow_html=True)
        for fac in reversed(factures):
            fid = fac.get("id")
            fname = fac.get("pdfFitxer", "")
            fpath = get_pdf_path("Factures_Llum", fname) if fname else ""
            file_exists = bool(fname and os.path.exists(fpath))

            with st.container(border=True):
                col_d, col_act = st.columns([4.2, 0.8], vertical_alignment="center")
                with col_d:
                    st.markdown(f"""
                    <div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>
                        <span style='font-size:1.1rem; font-weight:700; color:#e2e8f0;'>📅 {fac.get('mesAny', '')}</span>
                        <span style='background:#1e293b; color:#38bdf8; font-size:0.8rem; padding:2px 8px; border-radius:12px; font-weight:600;'>Període: {fac.get('periodeInici', '')} - {fac.get('periodeFi', '')}</span>
                        <span style='font-size:1.15rem; font-weight:700; color:#10b981; margin-left:auto;'>{float(fac.get('importTotal', 0.0)):.2f} €</span>
                    </div>
                    """, unsafe_allow_html=True)

                    kp = float(fac.get("kwhPunta", 0.0))
                    kl = float(fac.get("kwhLlano", 0.0))
                    kv = float(fac.get("kwhValle", 0.0))
                    kt = float(fac.get("kwhTotal", 0.0))
                    st.markdown(f"""
                    <div style='display:flex; gap:12px; font-size:0.85rem; color:#94a3b8; margin:6px 0 0 0;'>
                        <span>🔴 Punta: <b style='color:#f87171;'>{kp:.1f} kWh</b></span>
                        <span>🟡 Pla: <b style='color:#fbbf24;'>{kl:.1f} kWh</b></span>
                        <span>🟢 Vall (Acum.): <b style='color:#34d399;'>{kv:.1f} kWh</b></span>
                        <span>⚡ Total: <b style='color:#e2e8f0;'>{kt:.1f} kWh</b></span>
                    </div>
                    """, unsafe_allow_html=True)

                with col_act:
                    if file_exists:
                        if st.button("👁️ Veure", use_container_width=True, key=f"btn_vw_fac_{fid}", help="Veure PDF al visor integrat"):
                            view_pdf_dialog(f"Factura {fac.get('mesAny')}", "Factures_Llum", fname)
                    else:
                        st.button("👁️ Veure", disabled=True, use_container_width=True, key=f"btn_vw_fac_dis_{fid}", help="Fitxer PDF no disponible")
    else:
        st.info("💡 Encara no hi ha cap factura elèctrica registrada. Fes clic a **➕ Nova Factura Llum** per començar a registrar els consums per tram.")


# =========================================================================
# PESTANYA 2: CONSUM AIGUA
# =========================================================================

def render_consum_aigua_tab():
    st.markdown("<p style='color:#94a3b8; font-size:0.95rem; margin:0 0 16px 0;'>Registre de factures d'aigua, lectures de comptador i evolució dels metres cúbics (m³) consumits.</p>", unsafe_allow_html=True)

    factures_aigua = load_factures_aigua()

    c_aig_h, c_aig_btn = st.columns([3, 1], vertical_alignment="center")
    with c_aig_h:
        st.markdown("<h4 style='color:#0284c7; margin:0;'>💧 Històric de Factures i Consum d'Aigua</h4>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; color:#94a3b8;'>Control periòdic del consum d'aigua de la llar en m³ i cost per factura.</div>", unsafe_allow_html=True)
    with c_aig_btn:
        show_add_aigua = st.checkbox("➕ Nova Factura Aigua", key="chk_show_add_factura_aigua")

    # FORMULARI D'ALTA AIGUA
    if show_add_aigua:
        with st.container(border=True):
            st.markdown("<h5 style='color:#0284c7; margin-top:0;'>➕ Introduir Nova Factura d'Aigua</h5>", unsafe_allow_html=True)
            
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                in_data_fact = st.date_input("Data Emissió Factura *", value=datetime.today().date(), format="DD/MM/YYYY", key="in_fact_aigua_df")
            with f_col2:
                in_mes_any = st.text_input("Mes / Trimestre (ex: 3T/2026 o 10/2026) *", value=datetime.today().strftime("%m/%Y"), key="in_fact_aigua_mes")
            with f_col3:
                in_import = st.number_input("Import Total Factura (€) *", min_value=0.0, step=0.01, format="%.2f", key="in_fact_aigua_imp")

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                in_p_inici = st.date_input("Període de Facturació: Des de", value=(datetime.today().date() - timedelta(days=60)), format="DD/MM/YYYY", key="in_fact_aigua_pi")
            with p_col2:
                in_p_fi = st.date_input("Fins a", value=datetime.today().date(), format="DD/MM/YYYY", key="in_fact_aigua_pf")

            st.markdown("<p style='font-weight:600; color:#cbd5e1; margin:8px 0 2px 0;'>💧 Consum i Lectures (m³)</p>", unsafe_allow_html=True)
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
                in_m3 = st.number_input("Consum Facturat (m³) *", min_value=0.0, step=0.1, format="%.2f", key="in_fact_aigua_m3")
            with c_m2:
                in_lec_ant = st.number_input("Lectura Anterior (m³)", min_value=0.0, step=1.0, format="%.0f", key="in_fact_aigua_la")
            with c_m3:
                in_lec_act = st.number_input("Lectura Actual (m³)", min_value=0.0, step=1.0, format="%.0f", key="in_fact_aigua_lact")

            c_extra1, c_extra2 = st.columns(2)
            with c_extra1:
                in_com = st.text_input("Comercialitzadora / Empresa", value="Aigües de Girona", key="in_fact_aigua_com")
            with c_extra2:
                in_obs = st.text_input("Observacions", placeholder="Ex: Consum habitual o reg de jardí", key="in_fact_aigua_obs")

            pdf_file = st.file_uploader("Adjuntar Factura en PDF (opcional)", type=["pdf"], key="in_fact_aigua_pdf")

            if st.button("💾 Desar Factura d'Aigua", type="primary", use_container_width=True, key="btn_save_new_fact_aigua"):
                pdf_fname = ""
                if pdf_file is not None:
                    try:
                        clean_mes = in_mes_any.replace("/", "_").replace(" ", "_")
                        pdf_fname = f"factura_aigua_{clean_mes}_{int(datetime.now().timestamp())}.pdf"
                        dest_dir = get_pdf_dir("Factures_Aigua")
                        dest_path = os.path.join(dest_dir, pdf_fname)
                        with open(dest_path, "wb") as f_out:
                            f_out.write(pdf_file.getbuffer())
                    except Exception as err:
                        st.warning(f"No s'ha pogut desar el fitxer PDF d'aigua: {err}")
                        pdf_fname = ""

                add_factura_aigua(
                    data_factura=in_data_fact.strftime("%d/%m/%Y"),
                    periode_inici=in_p_inici.strftime("%d/%m/%Y"),
                    periode_fi=in_p_fi.strftime("%d/%m/%Y"),
                    mes_any=in_mes_any.strip(),
                    import_total=in_import,
                    m3_consum=in_m3,
                    lectura_anterior=in_lec_ant,
                    lectura_actual=in_lec_act,
                    comercialitzadora=in_com.strip(),
                    pdf_fitxer=pdf_fname,
                    observacions=in_obs.strip()
                )
                st.success("✅ Factura d'aigua desada correctament!")
                st.rerun()

    # KPIS HISTÒRICS I GRÀFIC AIGUA
    if factures_aigua:
        tot_despesa_aig = sum(float(f.get("importTotal", 0.0)) for f in factures_aigua)
        tot_m3 = sum(float(f.get("m3Consum", 0.0)) for f in factures_aigua)
        mitjana_cost_m3 = round(tot_despesa_aig / tot_m3, 2) if tot_m3 > 0 else 0.0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Facturat", f"{tot_despesa_aig:.2f} €", help="Cost acumulat de factures d'aigua")
        with m2:
            st.metric("Total Aigua Consumida", f"{tot_m3:.1f} m³", help="Metres cúbics acumulats")
        with m3:
            st.metric("Cost Mitjà / m³", f"{mitjana_cost_m3:.2f} €/m³", help="Preu mig resultant per metre cúbic")
        with m4:
            st.metric("Nº Factures", f"{len(factures_aigua)}", help="Total de factures registrades")

        df_aig = pd.DataFrame(factures_aigua)
        if "mesAny" in df_aig.columns and len(df_aig) > 0:
            fig_aig = go.Figure()
            fig_aig.add_trace(go.Bar(
                name="Consum Aigua (m³)",
                x=df_aig["mesAny"],
                y=df_aig["m3Consum"],
                marker_color="#0284c7",
                hovertemplate="Consum: %{y:.1f} m³<extra></extra>"
            ))
            fig_aig.add_trace(go.Scatter(
                name="Import Factura (€)",
                x=df_aig["mesAny"],
                y=df_aig["importTotal"],
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="#38bdf8", width=3),
                marker=dict(size=8, color="#38bdf8"),
                hovertemplate="Cost: %{y:.2f} €<extra></extra>"
            ))

            fig_aig.update_layout(
                margin=dict(l=10, r=10, t=30, b=30),
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                xaxis=dict(showgrid=False, color="#94a3b8"),
                yaxis=dict(
                    title="Aigua (m³)",
                    title_font=dict(color="#0284c7", size=11),
                    showgrid=True,
                    gridcolor="#334155",
                    color="#94a3b8"
                ),
                yaxis2=dict(
                    title="Import (€)",
                    title_font=dict(color="#38bdf8", size=11),
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    color="#38bdf8"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color="#cbd5e1", size=11)
                )
            )
            st.plotly_chart(fig_aig, use_container_width=True)

        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0284c7; margin:16px 0 8px 0;'>📋 Històric de Factures d'Aigua</p>", unsafe_allow_html=True)
        for fac in reversed(factures_aigua):
            fid = fac.get("id")
            fname = fac.get("pdfFitxer", "")
            fpath = get_pdf_path("Factures_Aigua", fname) if fname else ""
            file_exists = bool(fname and os.path.exists(fpath))

            with st.container(border=True):
                col_d, col_act = st.columns([3.5, 1.5], vertical_alignment="center")
                with col_d:
                    st.markdown(f"""
                    <div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>
                        <span style='font-size:1.1rem; font-weight:700; color:#e2e8f0;'>💧 {fac.get('mesAny', '')}</span>
                        <span style='background:#1e293b; color:#38bdf8; font-size:0.8rem; padding:2px 8px; border-radius:12px; font-weight:600;'>Període: {fac.get('periodeInici', '')} - {fac.get('periodeFi', '')}</span>
                        <span style='font-size:1.15rem; font-weight:700; color:#0284c7; margin-left:auto;'>{float(fac.get('importTotal', 0.0)):.2f} €</span>
                    </div>
                    """, unsafe_allow_html=True)

                    m3_val = float(fac.get("m3Consum", 0.0))
                    la_val = float(fac.get("lecturaAnterior", 0.0))
                    lact_val = float(fac.get("lecturaActual", 0.0))
                    st.markdown(f"""
                    <div style='display:flex; gap:14px; font-size:0.85rem; color:#94a3b8; margin:6px 0;'>
                        <span>💧 Consum: <b style='color:#38bdf8;'>{m3_val:.2f} m³</b></span>
                        {f"<span>Lectures: <b>{la_val:.0f}</b> ➔ <b>{lact_val:.0f}</b></span>" if lact_val > 0 else ""}
                    </div>
                    <div style='font-size:0.8rem; color:#64748b;'>
                        🏢 {fac.get('comercialitzadora', '')}
                        {f" • <i>{fac.get('observacions')}</i>" if fac.get('observacions') else ""}
                    </div>
                    """, unsafe_allow_html=True)

                with col_act:
                    c_a1, c_a2 = st.columns(2)
                    with c_a1:
                        if file_exists:
                            if st.button("👁️ Veure", use_container_width=True, key=f"btn_vw_fac_aig_{fid}", help="Veure PDF al visor integrat"):
                                view_pdf_dialog(f"Factura Aigua {fac.get('mesAny')}", "Factures_Aigua", fname)
                        else:
                            st.button("👁️ Veure", disabled=True, use_container_width=True, key=f"btn_vw_fac_aig_dis_{fid}")
                    with c_a2:
                        if file_exists:
                            with open(fpath, "rb") as f_b:
                                st.download_button(
                                    label="📥 Baixar",
                                    data=f_b.read(),
                                    file_name=fname,
                                    mime="application/pdf",
                                    use_container_width=True,
                                    key=f"btn_dl_fac_aig_{fid}"
                                )
                        else:
                            st.button("📥 Baixar", disabled=True, use_container_width=True, key=f"btn_dl_fac_aig_dis_{fid}")

                    c_a3, c_a4 = st.columns(2)
                    with c_a3:
                        if st.button("✏️ Editar", use_container_width=True, key=f"btn_ed_fac_aig_{fid}"):
                            edit_factura_aigua_dialog(fac)
                    with c_a4:
                        if st.button("🗑️ Esborrar", use_container_width=True, key=f"btn_del_fac_aig_{fid}"):
                            delete_factura_aigua_dialog(fid, fac.get("mesAny", ""), fname)
    else:
        st.info("💡 Encara no hi ha cap factura d'aigua registrada. Fes clic a **➕ Nova Factura Aigua** per començar a registrar els consums en m³.")


# =========================================================================
# PESTANYA 3: ESTUDI SOLAR FOTOVOLTAIC I IDONEÏTAT
# =========================================================================

def render_estudi_solar_tab():
    energia_cfg = get_energia_llar_config()
    estudi_cfg = energia_cfg.get("estudi_solar", {})
    municipi = estudi_cfg.get("municipi", "Arbúcies")
    comarca = estudi_cfg.get("comarca", "La Selva, Girona")
    sup_teulada = int(estudi_cfg.get("superficie_teulada_m2", 45))
    ori_label = estudi_cfg.get("orientacio_label", "29° Nord-Est (Teulada actual)")
    watts_panell_cfg = int(estudi_cfg.get("watts_panell", 450))
    descompte_tarifa_pct = int(estudi_cfg.get("descompte_tarifa_pct", 80))

    # Càlcul del consum històric a partir de les factures registrades
    factures_llum = load_factures_llum()
    n_factures = len(factures_llum)
    if factures_llum:
        try:
            total_kwh_registrat = sum(float(f.get("kwhTotal", 0.0)) for f in factures_llum)
            consum_anual_calc = round((total_kwh_registrat / max(1, n_factures)) * 12)
        except Exception:
            consum_anual_calc = 5661
    else:
        consum_anual_calc = 5661

    st.markdown(f"<p style='color:#94a3b8; font-size:0.95rem; margin:0 0 16px 0;'>Estudi tècnic i econòmic per a la instal·lació de plaques solars fotovoltaiques a {municipi}, amb dades reals de consum ({n_factures} factures) i integració amb els acumuladors de calor.</p>", unsafe_allow_html=True)

    # Badges resum de la propietat
    st.markdown(f"""
    <div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px;'>
        <div style='background:#1e293b; border:1px solid #334155; border-radius:8px; padding:6px 14px; font-size:0.83rem; color:#cbd5e1;'>
            📍 <b>Ubicació:</b> {municipi} ({comarca})
        </div>
        <div style='background:#1e293b; border:1px solid #334155; border-radius:8px; padding:6px 14px; font-size:0.83rem; color:#cbd5e1;'>
            📐 <b>Teulada:</b> {sup_teulada} m² de teula ({ori_label})
        </div>
        <div style='background:#1e293b; border:1px solid #334155; border-radius:8px; padding:6px 14px; font-size:0.83rem; color:#cbd5e1;'>
            ⚡ <b>Consum Històric:</b> {consum_anual_calc:,.0f} kWh / any ({n_factures} factures)
        </div>
        <div style='background:#065f46; border:1px solid #059669; border-radius:8px; padding:6px 14px; font-size:0.83rem; color:#a7f3d0;'>
            🏷️ <b>Tarifa:</b> PVPC Bo Social ({descompte_tarifa_pct}% descompte)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # CONFIGURADOR INTERACTIU
    with st.container(border=True):
        st.markdown("<h4 style='color:#f39c12; margin:0 0 12px 0;'>⚙️ Configurador del Sistema Solar Fotovoltaic</h4>", unsafe_allow_html=True)

        c_s1, c_s2, c_s3, c_s4 = st.columns([1.2, 1.1, 1.4, 1.3])
        with c_s1:
            num_panells = st.slider(
                "Nombre de Panells:",
                min_value=4,
                max_value=24,
                value=12,
                step=1,
                help=f"Cada panell ocupa ~2,1 m² de teulada. Amb {12} panells ocupes ~25 m² dels {sup_teulada} m² disponibles."
            )
        with c_s2:
            opcions_watts = [400, 450, 500, 550]
            idx_w = opcions_watts.index(watts_panell_cfg) if watts_panell_cfg in opcions_watts else 1
            potencia_panell = st.selectbox(
                "Potència Panell (W):",
                opcions_watts,
                index=idx_w,
                help="Potència pic de cada panell solar monocristal·lí."
            )
        with c_s3:
            opt_orientacio = st.selectbox(
                "Orientació a la teulada:",
                [
                    f"📐 Vessant única ({ori_label})",
                    "🔄 Dues aigües (Repartiment Est/Oest)",
                    "☀️ Correcció d'estructura cap al Sud (100% òptim)"
                ],
                index=0,
                help="Orientació dels panells a la teulada."
            )
            key_orientacio = "ne_pur"
            if "Dues aigües" in opt_orientacio:
                key_orientacio = "est_oest"
            elif "Sud" in opt_orientacio:
                key_orientacio = "sud_optim"

        with c_s4:
            opt_bateria = st.selectbox(
                "Bateria Física (Liti):",
                [
                    "❌ Sense bateria (Només acumuladors)",
                    "🔋 Bateria Liti 5 kWh",
                    "🔋 Bateria Liti 10 kWh (Recomanada)",
                    "🔋 Bateria Liti 15 kWh (Autonomia màxima)"
                ],
                index=0,
                help="La bateria de liti emmagatzema l'energia solar excedentària de dia per a la nit."
            )
            val_bateria = 0.0
            if "5 kWh" in opt_bateria:
                val_bateria = 5.0
            elif "10 kWh" in opt_bateria:
                val_bateria = 10.0
            elif "15 kWh" in opt_bateria:
                val_bateria = 15.0

        c_ac_check1, c_ac_check2 = st.columns([1.8, 1.2], vertical_alignment="center")
        with c_ac_check1:
            chk_desviar_acum = st.checkbox(
                "🔥 Desviar excedents solars als acumuladors de calor (Bateria Tèrmica)",
                value=True,
                help="Aprofita els acumuladors de calor com a gran dipòsit tèrmic gratuït durant les hores centrals de sol (11h a 16h)."
            )
        with c_ac_check2:
            st.caption("ℹ️ A l'hivern, carregar els acumuladors amb el sol augmenta l'autoconsum directe més d'un 35% a cost zero.")

    # PERSONALITZACIÓ DE DADES GEOGRÀFIQUES I DE TEULADA
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    with st.expander("⚙️ Personalitzar Ubicació, Teulada i Paràmetres del Model Solar", expanded=False):
        c_u1, c_u2, c_u3 = st.columns(3)
        with c_u1:
            e_mun = st.text_input("Municipi:", value=municipi, key="sol_mun_input")
            e_com = st.text_input("Comarca / Província:", value=comarca, key="sol_com_input")
        with c_u2:
            e_sup = st.number_input("Superfície teulada disponible (m²):", min_value=10, max_value=500, value=sup_teulada, step=5, key="sol_sup_input")
            e_watts_def = st.selectbox("Potència panell per defecte (W):", [400, 450, 500, 550], index=idx_w, key="sol_w_def_input")
        with c_u3:
            e_desc = st.number_input("Descompte Tarifa / Bo Social (%):", min_value=0, max_value=100, value=descompte_tarifa_pct, step=5, key="sol_desc_input")
            e_ori_desc = st.text_input("Descripció de la teulada:", value=ori_label, key="sol_ori_desc_input")

        if st.button("💾 Desar Dades de l'Estudi Solar", key="btn_save_solar_model_cfg"):
            nova_cfg_solar = dict(estudi_cfg)
            nova_cfg_solar.update({
                "municipi": e_mun.strip(),
                "comarca": e_com.strip(),
                "superficie_teulada_m2": int(e_sup),
                "watts_panell": int(e_watts_def),
                "descompte_tarifa_pct": int(e_desc),
                "orientacio_label": e_ori_desc.strip()
            })
            cfg_global = get_energia_llar_config()
            cfg_global["estudi_solar"] = nova_cfg_solar
            if save_energia_llar_config(cfg_global):
                st.success("✅ Dades de l'estudi solar desades correctament!")
                st.rerun()
            else:
                st.error("❌ Error en desar les dades de l'estudi solar.")

    # Executar simulació
    res_solar = simular_estudi_solar(
        num_panells=num_panells,
        potencia_panell_w=potencia_panell,
        orientacio=key_orientacio,
        bateria_kwh=val_bateria,
        carregar_acumuladors_sol=chk_desviar_acum
    )

    # 4 TARGETES MÈTRIQUES
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Potència del Camp Solar",
            f"{res_solar['kwp']} kWp",
            f"{res_solar['num_panells']} panells ({res_solar['superficie_m2']} m² ocupats)"
        )
    with m2:
        st.metric(
            "Generació Anual Estimada",
            f"{res_solar['tot_generacio_anual']:,.0f} kWh",
            f"Consum anual: {res_solar['tot_consum_anual']:,.0f} kWh"
        )
    with m3:
        st.metric(
            "Grau d'Autosuficiència",
            f"{res_solar['autosuficiencia_pct']}%",
            f"{res_solar['tot_autoconsum_anual']:,.0f} kWh aprofitats directament"
        )
    with m4:
        st.metric(
            "Excedents Anuals a Xarxa",
            f"{res_solar['tot_excedents_anual']:,.0f} kWh",
            f"{res_solar['autoconsum_ratio_pct']}% d'autoconsum directe"
        )

    # GRÀFIC BALANÇ MENSUAL
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#38bdf8; margin:0 0 4px 0;'>📊 Balanç Mensual: Producció Solar vs. El teu Consum Real</h4>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:0.82rem; color:#94a3b8; margin-bottom:12px;'>Simulació mes a mes segons les teves factures reals ({n_factures} registrades) i la radiació solar a {municipi}.</div>", unsafe_allow_html=True)

    df_solar = pd.DataFrame(res_solar["mensual_dades"])
    fig_solar = go.Figure()

    fig_solar.add_trace(go.Bar(
        name="⚡ Autoconsum Directe + Bateria",
        x=df_solar["mes_nom"],
        y=df_solar["autoconsum_kwh"],
        marker_color="#10b981",
        hovertemplate="Autoconsum: %{y:.1f} kWh<extra></extra>"
    ))

    fig_solar.add_trace(go.Bar(
        name="🔌 Importat de la Xarxa",
        x=df_solar["mes_nom"],
        y=df_solar["xarxa_kwh"],
        marker_color="#ef4444",
        hovertemplate="De xarxa: %{y:.1f} kWh<extra></extra>"
    ))

    fig_solar.add_trace(go.Scatter(
        name="☀️ Generació Solar Total",
        x=df_solar["mes_nom"],
        y=df_solar["produccio_kwh"],
        mode="lines+markers",
        line=dict(color="#f59e0b", width=3),
        marker=dict(size=8, color="#f59e0b"),
        hovertemplate="Generació Solar: %{y:.1f} kWh<extra></extra>"
    ))

    fig_solar.update_layout(
        barmode="stack",
        margin=dict(l=10, r=10, t=30, b=30),
        height=330,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.4)",
        xaxis=dict(showgrid=False, color="#94a3b8"),
        yaxis=dict(
            title="Energia (kWh/mes)",
            title_font=dict(color="#94a3b8", size=11),
            showgrid=True,
            gridcolor="#334155",
            color="#94a3b8"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1", size=11)
        )
    )
    st.plotly_chart(fig_solar, use_container_width=True)

    # ANÀLISI DEL BO SOCIAL
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"""
        <h4 style='color:#f39c12; margin-top:0;'>🏷️ La Particularitat Econòmica del Bo Social ({descompte_tarifa_pct}% Descompte)</h4>
        <div style='font-size:0.87rem; color:#cbd5e1; line-height:1.6;'>
            Actualment gaudeixes d'una tarifa bonificada (<b>{descompte_tarifa_pct}% de descompte</b>):
            <ul>
                <li><b>Cost elèctric actual mínim:</b> Pagant entre 0,02 € i 0,04 € pel kWh de la xarxa, el cost anual total de la factura se situa en xifres reduïdes malgrat un consum elevat.</li>
                <li><b>Com funciona la compensació d'excedents (RD 244/2019):</b> La llei estipula que els excedents solars abocats a la xarxa només poden compensar el terme variable de l'energia de la factura del mes (mai el terme fix de potència ni els impostos, i la factura mai pot sortir negativa). Amb el gran descompte aplicat a la teva tarifa, el valor monetari que rebràs per abocar a la xarxa és moderat.</li>
                <li><b>La clau d'or: La "Bateria Tèrmica":</b> Com que abocar energia a la xarxa té un retorn econòmic limitat amb el Bo Social, <b>desviar l'excedent als acumuladors de calor durant el migdia</b> és l'estratègia més rendible: escalfes la llar gratuïtament sense haver de consumir energia de la xarxa durant les nits.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # COMPARATIVA D'EXECUCIÓ: EMPRESA VS BRICOLATGE
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown("<h4 style='color:#f39c12; margin:0 0 12px 0;'>🛠️ Comparativa d'Execució: Empresa Especialitzada vs. Què pots fer tu mateix</h4>", unsafe_allow_html=True)

    col_emp, col_diy = st.columns(2, gap="medium")
    with col_emp:
        st.markdown(f"""
        <div style='background:rgba(255,255,255,0.02); border:1px solid #334155; border-radius:10px; padding:16px;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'>
                <b style='color:#38bdf8; font-size:1.05rem;'>🏢 Opció A: Claus en Mà (Empresa Certificada)</b>
                <span style='background:#075985; color:#bae6fd; font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:600;'>100% Garantit</span>
            </div>
            <div style='font-size:0.83rem; color:#cbd5e1; line-height:1.5;'>
                L'empresa subministra materials de 1a marca (panells Tier 1, inversor híbrid), realitza el muntatge a la teulada de teules amb assegurança de responsabilitat civil i goteres, cablejat, quadre de proteccions AC/DC, emissió del <b>Butlletí CIE</b> i <b>legalització al RAC (Generalitat)</b>.
            </div>
            <hr style='border-color:#334155; margin:12px 0;'>
            <div style='font-size:0.9rem;'>
                <div>Pressupost estimat complet (amb IVA): <b style='color:#f39c12; font-size:1.15rem;'>{res_solar['cost_total_empresa']:,.2f} €</b></div>
                <div style='color:#10b981; margin-top:4px;'>- Deducció IRPF (40%): <b>-{res_solar['deduccio_irpf_40']:,.2f} €</b></div>
                <div style='color:#10b981;'>- Bonificació IBI {municipi} (~3 anys): <b>-{res_solar['bonificacio_ibi_estimada']:,.2f} €</b></div>
                <hr style='border-color:#334155; margin:8px 0;'>
                <div style='font-size:1rem; color:#e2e8f0;'>Cost net real aproximat: <b style='color:#10b981; font-size:1.25rem;'>{res_solar['cost_net_empresa_amb_ajudes']:,.2f} €</b></div>
            </div>
            <div style='font-size:0.78rem; color:#94a3b8; margin-top:10px;'>
                ✅ <b>Avantatges:</b> Seguretat total en alçada, garantia d'estanquitat a les teules i certificació energètica oficial per aplicar la deducció a la Renda sense problemes.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_diy:
        st.markdown(f"""
        <div style='background:rgba(255,255,255,0.02); border:1px solid #334155; border-radius:10px; padding:16px;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'>
                <b style='color:#f59e0b; font-size:1.05rem;'>🔧 Opció B: Fórmula Mixta (Bricolatge + Professional)</b>
                <span style='background:#78350f; color:#fde68a; font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:600;'>Estalvi Mà d'Obra</span>
            </div>
            <div style='font-size:0.83rem; color:#cbd5e1; line-height:1.5;'>
                <b>Què fas tu:</b> Fixar els ganxos salvateules d'acer inoxidable a les bigues, muntar els perfils d'alumini, carregar i fixar els panells a la teulada, i passar els tubs corrugats amb cable solar DC de 6 mm² fins a l'inversor.<br>
                <b>Què fa el professional:</b> Connexió del quadre AC/DC, connexió a xarxa, posada en marxa, butlletí CIE i legalització administrativa.
            </div>
            <hr style='border-color:#334155; margin:12px 0;'>
            <div style='font-size:0.9rem;'>
                <div>Cost estimat materials + instal·lador: <b style='color:#f59e0b; font-size:1.15rem;'>{res_solar['cost_total_bricolatge']:,.2f} €</b></div>
                <div style='color:#10b981; margin-top:4px;'>- Deducció IRPF (40%): <b>-{(res_solar['cost_total_bricolatge'] * 0.40):,.2f} €</b></div>
                <div style='color:#10b981;'>- Bonificació IBI {municipi}: <b>-{res_solar['bonificacio_ibi_estimada']:,.2f} €</b></div>
                <hr style='border-color:#334155; margin:8px 0;'>
                <div style='font-size:1rem; color:#e2e8f0;'>Cost net real aproximat: <b style='color:#10b981; font-size:1.25rem;'>{res_solar['cost_net_bricolatge_amb_ajudes']:,.2f} €</b></div>
            </div>
            <div style='font-size:0.78rem; color:#94a3b8; margin-top:10px;'>
                💡 <b>Estalvi directe:</b> T'estalvies entre <b>1.200 € i 1.800 € de mà d'obra</b> de teulada, assumint tu el temps i la feina mecànica.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # GUIA DE SEGURETAT I TEULADA
    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    with st.expander(f"🦺 Guia Pràctica de Seguretat i Consells per Treballar a la Teulada de Teules ({municipi})", expanded=False):
        st.markdown(f"""
        Si optes per fer el muntatge mecànic tu mateix a la teulada de teules ({ori_label}):
        
        1. **Ganxos Salvateules (Salvatejas d'acer inoxidable):**
           - *Regla d'or:* **No foradis mai la teula per la part superior** (amb el temps és font segura de filtracions i goteres).
           - S'aixeca la teula superior, es caragola la platina d'acer inoxidable directament al forjat o biga de suport amb tac químic o caragol barraquero, i es rebaixa lleugerament amb disc de diamant la panxa inferior de la teula per no picar-la en tornar-la a encaixar.
        
        2. **Estructura i Perfileria d'Alumini:**
           - Utilitza perfils d'alumini anoditzat estructural (mínim 40x40 mm) i cargols d'acer inoxidable A2.
           - Assegura't de respectar la distància de seguretat de **mínim 30-40 cm respecte a la carena i als ràfecs** per minimitzar l'efecte vela del vent.
        
        3. **Connexions elèctriques a la teulada (DC):**
           - Fes totes les unions amb connectors originals **MC4 crimpats amb alicates especials** (evita fer-ho amb alicates planes normals).
           - Fixa tot el cablejat solar resistent a raigs UV (6 mm²) amb brides inoxidables a l'estructura, mai descansant directament a les teules o zones d'evacuació d'aigua.
        
        4. **Mesures de Seguretat Personal (EPIs):**
           - Arnés de seguretat homologat fixat a línia de vida o punt d'ancoratge segur a l'obra.
           - Treballa sempre acompanyat d'una segona persona que supervise des de baix o doni suport amb materials.
           - **No pugis mai a la teulada amb pluja, humitat matinal (rosada) o ratxes de vent.**
        """, unsafe_allow_html=True)

# =========================================================================
# FUNCIÓ PRINCIPAL DEL MÒDUL LLUM I AIGUA
# =========================================================================

def render():
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>💡 Llum i Aigua</h2>", "llum_aigua")
    st.write("---")

    tabs_list = ["⚡ Consum Llum", "💧 Consum Aigua", "☀️ Estudi Solar"]
    tab_mapping = {
        "llum": "⚡ Consum Llum",
        "consum_llum": "⚡ Consum Llum",
        "electricitat": "⚡ Consum Llum",
        "aigua": "💧 Consum Aigua",
        "consum_aigua": "💧 Consum Aigua",
        "solar": "☀️ Estudi Solar",
        "plaques": "☀️ Estudi Solar",
        "estudi_solar": "☀️ Estudi Solar"
    }

    tab_param = st.query_params.get("tab")
    default_tab = tab_mapping.get(tab_param)
    if default_tab not in tabs_list:
        default_tab = "⚡ Consum Llum"

    tab_llum, tab_aigua, tab_solar = st.tabs(tabs_list, default=default_tab, key=f"tabs_llum_aigua_{tab_param or 'main'}")

    with tab_llum:
        render_consum_llum_tab()

    with tab_aigua:
        render_consum_aigua_tab()

    with tab_solar:
        render_estudi_solar_tab()
