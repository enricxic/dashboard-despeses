import streamlit as st
import os
import base64
import json
import re
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

from modules.avatar_widget import render_header_with_avatar
from core.llum_manager import (
    get_preu_llum_avui,
    calcular_finestra_acumuladors,
    load_factures_llum,
    save_factures_llum,
    add_factura_llum,
    update_factura_llum,
    delete_factura_llum
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
# PESTANYA 1: CONSUM LLUM I OPTIMITZADOR D'ACUMULADORS
# =========================================================================

def render_consum_llum_tab():
    st.markdown("<p style='color:#94a3b8; font-size:0.95rem; margin:0 0 16px 0;'>Preu de la llum horari en directe (PVPC / Bo Social), optimitzador de càrrega d'acumuladors i gestió de factures per trams.</p>", unsafe_allow_html=True)

    # 1. PREU DE LA LLUM D'AVUI
    with st.container(border=True):
        c_t1, c_t2 = st.columns([3, 1], vertical_alignment="center")
        with c_t1:
            st.markdown("<h4 style='color:#f39c12; margin:0;'>⚡ Preu de la Llum en Directe (PVPC / Bo Social)</h4>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.8rem; color:#94a3b8;'>Dades oficials del mercat regulat (REE) extretes de <code>tarifaluzhora.es</code>. Tarifa 2.0TD.</div>", unsafe_allow_html=True)
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

            # OPTIMITZADOR D'ACUMULADORS
            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("""
                <div style='display:flex; align-items:center; gap:8px;'>
                    <span style='font-size:1.2rem;'>🔥</span>
                    <span style='font-size:1.05rem; font-weight:700; color:#f39c12;'>Optimitzador de Càrrega d'Acumuladors de Calor</span>
                    <span style='background:#065f46; color:#a7f3d0; font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:600;'>5,5 kW Nit</span>
                </div>
                """, unsafe_allow_html=True)

                col_opt1, col_opt2 = st.columns([1.5, 2.5], vertical_alignment="center")
                with col_opt1:
                    hores_carrega = st.slider(
                        "Hores de càrrega necessàries:",
                        min_value=2,
                        max_value=8,
                        value=5,
                        step=1,
                        help="Tria quantes hores de càrrega necessiten els acumuladors segons la temperatura exterior o el fred."
                    )
                    nomes_nit = st.checkbox(
                        "Franja nocturna 00:00 - 08:00h (Potència 5,5 kW)",
                        value=True,
                        help="Restringeix la càrrega a l'horari nocturn quan disposes de 5,5 kW de potència contractada i s'aplica el tram Vall."
                    )

                opt_res = calcular_finestra_acumuladors(hores, durada_hores=hores_carrega, nomes_nit=nomes_nit)

                with col_opt2:
                    if opt_res.get("millor_finestra"):
                        win = opt_res["millor_finestra"]
                        p_win = win["preu_mitja"]
                        estalvi = opt_res.get("estalvi_percent", 0.0)
                        st.markdown(f"""
                        <div style='background:rgba(245,158,11,0.09); border:1px solid rgba(245,158,11,0.35); border-radius:8px; padding:12px 16px;'>
                            <div style='font-size:0.8rem; color:#f59e0b; font-weight:600; text-transform:uppercase;'>✨ Millor finestra recomanada de {hores_carrega}h:</div>
                            <div style='font-size:1.35rem; font-weight:700; color:#fbbf24; margin:4px 0;'>⏰ {win['rang_text']}</div>
                            <div style='display:flex; gap:16px; flex-wrap:wrap; font-size:0.85rem; color:#e2e8f0;'>
                                <div>Preu mitjà finestra: <b style='color:#10b981;'>{p_win:.4f} €/kWh</b></div>
                                <div>Estalvi vs mitjana: <b style='color:#38bdf8;'>-{estalvi}%</b></div>
                                <div>Potència disponible: <b style='color:#f39c12;'>5,5 kW</b></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            # GRÀFIC HORARI 24H (PLOTLY)
            st.markdown("<p style='font-size:0.9rem; font-weight:600; color:#cbd5e1; margin:14px 0 6px 0;'>📊 Corba Horària de Preus del Dia (24h)</p>", unsafe_allow_html=True)
            
            x_slots = [h["slot"] for h in hores]
            y_prices = [h["preu"] for h in hores]
            colors = [h["tram_color"] for h in hores]
            
            opt_win_hours = []
            if opt_res and opt_res.get("millor_finestra"):
                opt_win_hours = [h["slot"] for h in opt_res["millor_finestra"].get("hores", [])]

            border_colors = []
            border_widths = []
            for h in hores:
                if h["slot"] in opt_win_hours:
                    border_colors.append("#fbbf24")
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
                marker=dict(
                    color=colors,
                    line=dict(color=border_colors, width=border_widths)
                ),
                hovertemplate="<b>Hora: %{x}</b><br>Preu: %{y:.4f} €/kWh<extra></extra>",
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

            fig.update_layout(
                margin=dict(l=10, r=10, t=25, b=30),
                height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                xaxis=dict(showgrid=False, color="#94a3b8", tickfont=dict(size=10)),
                yaxis=dict(showgrid=True, gridcolor="#334155", color="#94a3b8", tickformat=".3f", title="€/kWh", title_font=dict(size=11, color="#94a3b8")),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("ℹ️ Informació sobre Trams Horaris i Potències (Bo Social / 2.0TD)"):
                st.markdown("""
                - **🟢 Tram Vall (P3)**: De dilluns a divendres de **00:00 a 08:00 h**, i **les 24 hores dels caps de setmana i festius nacionals**.
                  - *Potència contractada*: **5,5 kW** (ideal per a la càrrega dels acumuladors de calor).
                - **🟡 Tram Pla (P2)**: De dilluns a divendres de **08:00 a 10:00 h**, de **14:00 a 18:00 h** i de **22:00 a 24:00 h**.
                  - *Potència contractada*: **4,4 kW**.
                - **🔴 Tram Punta (P1)**: De dilluns a divendres de **10:00 a 14:00 h** i de **18:00 a 22:00 h**.
                  - *Potència contractada*: **4,4 kW**.
                """)
        else:
            st.warning("⚠️ No s'han pogut carregar les dades de preus en directe en aquest moment. Pots tornar-ho a provar amb el botó d'actualitzar.")

    # 2. HISTÒRIC I FACTURES DE LLUM
    st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
    factures = load_factures_llum()

    c_fac_h, c_fac_btn = st.columns([3, 1], vertical_alignment="center")
    with c_fac_h:
        st.markdown("<h4 style='color:#f39c12; margin:0;'>📄 Registre de Factures i Consum per Tram</h4>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.8rem; color:#94a3b8;'>Evolució mensual dels kWh consumits per tram (Punta, Pla, Vall) i cost total.</div>", unsafe_allow_html=True)
    with c_fac_btn:
        show_add = st.checkbox("➕ Nova Factura Llum", key="chk_show_add_factura_llum")

    # FORMULARI D'ALTA LLUM
    if show_add:
        with st.container(border=True):
            st.markdown("<h5 style='color:#38bdf8; margin-top:0;'>➕ Introduir Nova Factura Elèctrica</h5>", unsafe_allow_html=True)
            
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                in_data_fact = st.date_input("Data Emissió Factura *", value=datetime.today().date(), format="DD/MM/YYYY", key="in_fact_df")
            with f_col2:
                in_mes_any = st.text_input("Mes / Any de Referència *", value=datetime.today().strftime("%m/%Y"), help="Ex: 10/2026", key="in_fact_mes")
            with f_col3:
                in_import = st.number_input("Import Total Factura (€) *", min_value=0.0, step=0.01, format="%.2f", key="in_fact_imp")

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                in_p_inici = st.date_input("Període de Facturació: Des de", value=(datetime.today().date() - timedelta(days=30)), format="DD/MM/YYYY", key="in_fact_pi")
            with p_col2:
                in_p_fi = st.date_input("Fins a", value=datetime.today().date(), format="DD/MM/YYYY", key="in_fact_pf")

            st.markdown("<p style='font-weight:600; color:#cbd5e1; margin:8px 0 2px 0;'>⚡ Consum d'Energia per Tram (kWh)</p>", unsafe_allow_html=True)
            c_k1, c_k2, c_k3, c_k4 = st.columns(4)
            with c_k1:
                in_kwh_punta = st.number_input("🔴 Punta (P1) kWh", min_value=0.0, step=1.0, format="%.1f", key="in_fact_p1")
            with c_k2:
                in_kwh_llano = st.number_input("🟡 Pla (P2) kWh", min_value=0.0, step=1.0, format="%.1f", key="in_fact_p2")
            with c_k3:
                in_kwh_valle = st.number_input("🟢 Vall (P3) kWh", min_value=0.0, step=1.0, format="%.1f", key="in_fact_p3")
            with c_k4:
                sum_kwh = round(in_kwh_punta + in_kwh_llano + in_kwh_valle, 1)
                st.metric("Total kWh", f"{sum_kwh} kWh")

            pot_col1, pot_col2 = st.columns(2)
            with pot_col1:
                in_pot_dia = st.number_input("Potència Dia (kW)", min_value=0.0, value=4.4, step=0.1, key="in_fact_pot_dia")
            with pot_col2:
                in_pot_nit = st.number_input("Potència Nit / Acumuladors (kW)", min_value=0.0, value=5.5, step=0.1, key="in_fact_pot_nit")

            c_extra1, c_extra2 = st.columns(2)
            with c_extra1:
                in_com = st.text_input("Comercialitzadora", value="Energía XXI (Bono Social)", key="in_fact_com")
            with c_extra2:
                in_obs = st.text_input("Observacions", placeholder="Ex: Descompte Bo Social aplicat", key="in_fact_obs")

            pdf_file = st.file_uploader("Adjuntar Factura en PDF (opcional)", type=["pdf"], key="in_fact_pdf")

            if st.button("💾 Desar Factura a la Base de Dades", type="primary", use_container_width=True, key="btn_save_new_fact"):
                pdf_fname = ""
                if pdf_file is not None:
                    try:
                        clean_mes = in_mes_any.replace("/", "_").replace(" ", "_")
                        pdf_fname = f"factura_llum_{clean_mes}_{int(datetime.now().timestamp())}.pdf"
                        dest_dir = get_pdf_dir("Factures_Llum")
                        dest_path = os.path.join(dest_dir, pdf_fname)
                        with open(dest_path, "wb") as f_out:
                            f_out.write(pdf_file.getbuffer())
                    except Exception as err:
                        st.warning(f"No s'ha pogut desar el fitxer PDF: {err}")
                        pdf_fname = ""

                add_factura_llum(
                    data_factura=in_data_fact.strftime("%d/%m/%Y"),
                    periode_inici=in_p_inici.strftime("%d/%m/%Y"),
                    periode_fi=in_p_fi.strftime("%d/%m/%Y"),
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
                st.success("✅ Factura desada correctament a Supabase i a la còpia local!")
                st.rerun()

    # KPIS HISTÒRICS I GRÀFIC LLUM
    if factures:
        tot_despesa = sum(float(f.get("importTotal", 0.0)) for f in factures)
        tot_kwh_all = sum(float(f.get("kwhTotal", 0.0)) for f in factures)
        tot_valle = sum(float(f.get("kwhValle", 0.0)) for f in factures)
        tot_llano = sum(float(f.get("kwhLlano", 0.0)) for f in factures)
        tot_punta = sum(float(f.get("kwhPunta", 0.0)) for f in factures)

        pct_valle = round((tot_valle / tot_kwh_all * 100), 1) if tot_kwh_all > 0 else 0.0
        pct_llano = round((tot_llano / tot_kwh_all * 100), 1) if tot_kwh_all > 0 else 0.0
        pct_punta = round((tot_punta / tot_kwh_all * 100), 1) if tot_kwh_all > 0 else 0.0

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Facturat", f"{tot_despesa:.2f} €", help="Suma d'imports de totes les factures registrades")
        with m2:
            st.metric("Total Energia", f"{tot_kwh_all:.1f} kWh", help="Consum acumulat d'energia")
        with m3:
            st.metric("🟢 Vall / Acumuladors", f"{pct_valle}%", help=f"{tot_valle:.1f} kWh consumits en hores vall")
        with m4:
            st.metric("🟡 Pla / 🔴 Punta", f"{pct_llano}% / {pct_punta}%", help=f"Pla: {tot_llano:.1f} kWh | Punta: {tot_punta:.1f} kWh")

        df_f = pd.DataFrame(factures)
        if "mesAny" in df_f.columns and len(df_f) > 0:
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

            fig_hist.add_trace(go.Scatter(
                name="Import Factura (€)",
                x=df_f["mesAny"],
                y=df_f["importTotal"],
                yaxis="y2",
                mode="lines+markers",
                line=dict(color="#38bdf8", width=3),
                marker=dict(size=8, color="#38bdf8"),
                hovertemplate="Cost: %{y:.2f} €<extra></extra>"
            ))

            fig_hist.update_layout(
                barmode="stack",
                margin=dict(l=10, r=10, t=30, b=30),
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15, 23, 42, 0.4)",
                xaxis=dict(showgrid=False, color="#94a3b8"),
                yaxis=dict(
                    title="Energia (kWh)",
                    title_font=dict(color="#94a3b8", size=11),
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
            st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#f39c12; margin:16px 0 8px 0;'>📋 Històric de Factures de Llum</p>", unsafe_allow_html=True)
        for fac in reversed(factures):
            fid = fac.get("id")
            fname = fac.get("pdfFitxer", "")
            fpath = get_pdf_path("Factures_Llum", fname) if fname else ""
            file_exists = bool(fname and os.path.exists(fpath))

            with st.container(border=True):
                col_d, col_act = st.columns([3.5, 1.5], vertical_alignment="center")
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
                    <div style='display:flex; gap:12px; font-size:0.85rem; color:#94a3b8; margin:6px 0;'>
                        <span>🔴 Punta: <b style='color:#f87171;'>{kp:.1f} kWh</b></span>
                        <span>🟡 Pla: <b style='color:#fbbf24;'>{kl:.1f} kWh</b></span>
                        <span>🟢 Vall (Acum.): <b style='color:#34d399;'>{kv:.1f} kWh</b></span>
                        <span>⚡ Total: <b style='color:#e2e8f0;'>{kt:.1f} kWh</b></span>
                    </div>
                    <div style='font-size:0.8rem; color:#64748b;'>
                        🏢 {fac.get('comercialitzadora', '')} • Potència: <b>{fac.get('potenciaDia', 4.4)} kW (dia)</b> / <b>{fac.get('potenciaNit', 5.5)} kW (nit)</b>
                        {f" • <i>{fac.get('observacions')}</i>" if fac.get('observacions') else ""}
                    </div>
                    """, unsafe_allow_html=True)

                with col_act:
                    c_a1, c_a2 = st.columns(2)
                    with c_a1:
                        if file_exists:
                            if st.button("👁️ Veure", use_container_width=True, key=f"btn_vw_fac_{fid}", help="Veure PDF al visor integrat"):
                                view_pdf_dialog(f"Factura {fac.get('mesAny')}", "Factures_Llum", fname)
                        else:
                            st.button("👁️ Veure", disabled=True, use_container_width=True, key=f"btn_vw_fac_dis_{fid}")
                    with c_a2:
                        if file_exists:
                            with open(fpath, "rb") as f_b:
                                st.download_button(
                                    label="📥 Baixar",
                                    data=f_b.read(),
                                    file_name=fname,
                                    mime="application/pdf",
                                    use_container_width=True,
                                    key=f"btn_dl_fac_{fid}"
                                )
                        else:
                            st.button("📥 Baixar", disabled=True, use_container_width=True, key=f"btn_dl_fac_dis_{fid}")

                    c_a3, c_a4 = st.columns(2)
                    with c_a3:
                        if st.button("✏️ Editar", use_container_width=True, key=f"btn_ed_fac_{fid}"):
                            edit_factura_dialog(fac)
                    with c_a4:
                        if st.button("🗑️ Esborrar", use_container_width=True, key=f"btn_del_fac_{fid}"):
                            delete_factura_dialog(fid, fac.get("mesAny", ""), fname)
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
# FUNCIÓ PRINCIPAL DEL MÒDUL LLUM I AIGUA
# =========================================================================

def render():
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>💡 Llum i Aigua</h2>", "llum_aigua")
    st.write("---")

    tabs_list = ["⚡ Consum Llum", "💧 Consum Aigua"]
    tab_mapping = {
        "llum": "⚡ Consum Llum",
        "consum_llum": "⚡ Consum Llum",
        "electricitat": "⚡ Consum Llum",
        "aigua": "💧 Consum Aigua",
        "consum_aigua": "💧 Consum Aigua"
    }

    tab_param = st.query_params.get("tab")
    default_tab = tab_mapping.get(tab_param)
    if default_tab not in tabs_list:
        default_tab = "⚡ Consum Llum"

    tab_llum, tab_aigua = st.tabs(tabs_list, default=default_tab, key=f"tabs_llum_aigua_{tab_param or 'main'}")

    with tab_llum:
        render_consum_llum_tab()

    with tab_aigua:
        render_consum_aigua_tab()
