import streamlit as st
import os
import base64
import json
import re
import copy
import pandas as pd
from datetime import datetime, date, timedelta
from modules.avatar_widget import render_header_with_avatar
from core.config_manager import load_app_config
from core.manteniment_manager import (
    load_manteniment_docs,
    save_manteniment_docs,
    sync_pdf_directory,
    get_pdf_path,
    get_pdf_dir,
    calculate_warranty_status,
    get_page_count,
    load_registre_manteniment,
    save_registre_manteniment,
    add_manteniment_task,
    add_manteniment_tasks_batch,
    compute_recurring_dates,
    compute_recurring_dates_for_year,
    filter_subtasks_for_occurrence,
    parse_task_recurrence,
    update_manteniment_task_with_recurrence,
    update_manteniment_task,
    delete_manteniment_task,
    toggle_manteniment_acompliment,
    toggle_subtask_acompliment,
    get_recurring_task_templates
)

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
              box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
              margin-bottom: 12px;
            }}
            .btn {{
              background: #334155;
              color: #f8fafc;
              border: 1px solid #475569;
              padding: 5px 12px;
              border-radius: 16px;
              cursor: pointer;
              font-size: 13px;
              font-weight: 600;
              transition: all 0.2s ease;
            }}
            .btn:hover {{
              background: #0284c7;
              border-color: #38bdf8;
            }}
            .page-info {{
              font-size: 13px;
              color: #cbd5e1;
              min-width: 120px;
              text-align: center;
              font-weight: 500;
            }}
            #canvas-wrapper {{
              width: 100%;
              display: flex;
              justify-content: center;
              overflow-x: auto;
              padding-bottom: 20px;
            }}
            canvas {{
              box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6);
              border-radius: 6px;
              background: #ffffff;
              max-width: 98%;
              height: auto;
            }}
            #loading {{
              padding: 40px;
              font-size: 14px;
              color: #94a3b8;
            }}
          </style>
        </head>
        <body>
          <div class="toolbar">
            <button class="btn" id="prev">◀ Anterior</button>
            <span class="page-info">Pàgina <b id="page-num" style="color:#38bdf8;">1</b> de <b id="page-count">-</b></span>
            <button class="btn" id="next">Següent ▶</button>
            <span style="border-left:1px solid #475569; height:18px; margin:0 4px;"></span>
            <button class="btn" id="zoom-out" title="Reduir mida">🔍 -</button>
            <span id="zoom-val" style="font-size:12px; color:#94a3b8;">100%</span>
            <button class="btn" id="zoom-in" title="Augmentar mida">🔍 +</button>
          </div>
          <div id="loading">Carregant document...</div>
          <div id="canvas-wrapper">
            <canvas id="pdf-canvas" style="display:none;"></canvas>
          </div>

          <script>
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            const b64Data = "{b64}";
            const rawData = atob(b64Data);
            const uint8Array = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; i++) {{
              uint8Array[i] = rawData.charCodeAt(i);
            }}

            let pdfDoc = null;
            let pageNum = 1;
            let pageRendering = false;
            let pageNumPending = null;
            let scale = 1.35;
            const canvas = document.getElementById('pdf-canvas');
            const ctx = canvas.getContext('2d');
            const loadingDiv = document.getElementById('loading');

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
                  loadingDiv.style.display = 'none';
                  canvas.style.display = 'block';
                  if (pageNumPending !== null) {{
                    renderPage(pageNumPending);
                    pageNumPending = null;
                  }}
                }});
              }});
              document.getElementById('page-num').textContent = num;
              document.getElementById('zoom-val').textContent = Math.round((scale / 1.35) * 100) + '%';
            }}

            function queueRenderPage(num) {{
              if (pageRendering) {{
                pageNumPending = num;
              }} else {{
                renderPage(num);
              }}
            }}

            document.getElementById('prev').addEventListener('click', function() {{
              if (pageNum <= 1) return;
              pageNum--;
              queueRenderPage(pageNum);
            }});

            document.getElementById('next').addEventListener('click', function() {{
              if (!pdfDoc || pageNum >= pdfDoc.numPages) return;
              pageNum++;
              queueRenderPage(pageNum);
            }});

            document.getElementById('zoom-in').addEventListener('click', function() {{
              if (scale < 3.0) {{
                scale += 0.25;
                queueRenderPage(pageNum);
              }}
            }});

            document.getElementById('zoom-out').addEventListener('click', function() {{
              if (scale > 0.6) {{
                scale -= 0.25;
                queueRenderPage(pageNum);
              }}
            }});

            pdfjsLib.getDocument({{ data: uint8Array }}).promise.then(function(pdfDoc_) {{
              pdfDoc = pdfDoc_;
              document.getElementById('page-count').textContent = pdfDoc.numPages;
              renderPage(pageNum);
            }}).catch(function(err) {{
              loadingDiv.innerHTML = '<div style="color:#ef4444;">Error interpretant el document: ' + err.message + '</div>';
            }});
          </script>
        </body>
        </html>
        """
        st.components.v1.html(pdfjs_html, height=800, scrolling=True)
    except Exception as e:
        st.error(f"Error obrint el fitxer PDF: {e}")

@st.dialog("➕ Afegir Document a Manuals", width="large")
def add_manual_dialog():
    """Diàleg per registrar un nou manual i opcionalment pujar el fitxer PDF."""
    st.markdown("<h3 style='margin-top:0; color:#3b82f6;'>📖 Nou Manual d'Instruccions</h3>", unsafe_allow_html=True)
    
    with st.form("form_nou_manual", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            titol = st.text_input("Títol del manual *", placeholder="Ex: Programador Horari Digital HBT 100")
            dispositiu = st.text_input("Dispositiu / Aparell *", placeholder="Ex: Termòstat, Forn, Rentadora...")
        with c2:
            marca = st.text_input("Marca", placeholder="Ex: Bosch, Siemens, HBT...")
            model = st.text_input("Model", placeholder="Ex: HBT-100F")
            
        c3, c4 = st.columns(2)
        with c3:
            ubicacio = st.selectbox("Ubicació a la llar", [
                "General", "Menjador", "Cuina", "Bany", "Dormitori",
                "Calefacció / Climatització", "Garatge", "Terrassa / Exterior", "Quadre Elèctric"
            ])
        with c4:
            subcat = st.selectbox("Àmbit / Subcategoria", [
                "Climatització i Calefacció", "Electrodomèstics", "Electricitat i Domòtica",
                "Il·luminació", "Fontaneria", "Mobiliari", "Eines", "General"
            ])
            
        descripcio = st.text_area("Descripció o observacions", placeholder="Notes sobre el funcionament, configuració bàsica, manteniment...", height=80)
        etiquetes_str = st.text_input("Etiquetes (separades per comes)", placeholder="calefacció, termòstat, digital, piles")
        
        uploaded_pdf = st.file_uploader("Pujar fitxer PDF del manual *", type=["pdf"], key="upload_manual_pdf")
        
        submitted = st.form_submit_button("💾 Desar Manual", use_container_width=True)
        if submitted:
            if not titol.strip() or not dispositiu.strip():
                st.error("Si us plau, omple com a mínim el Títol i el Dispositiu.")
                return
            if not uploaded_pdf:
                st.error("Cal seleccionar o pujar un fitxer PDF.")
                return
                
            fname = uploaded_pdf.name
            target_path = get_pdf_path("Manuals", fname)
            try:
                with open(target_path, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                pages = get_page_count(target_path)
            except Exception as e:
                st.error(f"Error desant el fitxer PDF: {e}")
                return
                
            docs = load_manteniment_docs()
            doc_id = f"man_{int(datetime.now().timestamp() * 1000)}"
            etiquetes = [t.strip().lower() for t in etiquetes_str.split(",") if t.strip()]
            
            docs["manuals"].append({
                "id": doc_id,
                "titol": titol.strip(),
                "dispositiu": dispositiu.strip(),
                "marca": marca.strip() or "General",
                "model": model.strip(),
                "ubicacio": ubicacio,
                "subcategoria": subcat,
                "fitxer": fname,
                "categoria": "Manuals",
                "pagines": pages,
                "descripcio": descripcio.strip(),
                "data_afegit": datetime.now().strftime("%d/%m/%Y"),
                "etiquetes": etiquetes
            })
            
            if save_manteniment_docs(docs):
                st.success("Manual registrat i desat correctament!")
                st.rerun()
            else:
                st.error("Error desant el registre JSON.")

@st.dialog("➕ Afegir Document a Garanties", width="large")
def add_garantia_dialog():
    """Diàleg per registrar una nova garantia i opcionalment pujar el fitxer PDF."""
    st.markdown("<h3 style='margin-top:0; color:#10b981;'>🛡️ Nova Garantia de Compra</h3>", unsafe_allow_html=True)
    
    with st.form("form_nova_garantia", clear_on_submit=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            titol = st.text_input("Títol de la garantia *", placeholder="Ex: Garantia Rentadora Bosch Sèrie 6")
            dispositiu = st.text_input("Dispositiu / Article *", placeholder="Ex: Rentadora, Televisor, Aspirador...")
        with c2:
            marca = st.text_input("Marca", placeholder="Ex: Bosch, Samsung, Philips...")
            model = st.text_input("Model / Nº Sèrie", placeholder="Ex: WAU28T44ES")
            
        c3, c4, c5 = st.columns(3)
        with c3:
            establiment = st.text_input("Establiment / Botiga *", placeholder="Ex: MediaMarkt, Amazon, El Corte Inglés")
        with c4:
            num_factura = st.text_input("Nº Factura / Tiquet", placeholder="Ex: FRA-2026-9812")
        with c5:
            import_compra = st.number_input("Preu / Import (€)", min_value=0.0, step=1.0, format="%.2f")
            
        c6, c7, c8 = st.columns(3)
        with c6:
            data_compra = st.date_input("Data de compra *", value=datetime.today().date(), max_value=datetime.today().date(), format="DD/MM/YYYY")
        with c7:
            anys_garantia = st.number_input("Anys de cobertura *", min_value=1, max_value=20, value=3, step=1)
        with c8:
            ubicacio = st.selectbox("Ubicació", [
                "Cuina", "Menjador", "Bany", "Dormitori", "Garatge", "General", "Terrassa / Exterior"
            ])
            
        descripcio = st.text_area("Notes de garantia o cobertura", placeholder="Condicions d'ampliació de garantia, telèfon d'assistència tècnica, cobertura de peces...", height=80)
        etiquetes_str = st.text_input("Etiquetes (separades per comes)", placeholder="electrodomèstic, cuina, motor 10 anys")
        
        uploaded_pdf = st.file_uploader("Pujar fitxer PDF de la garantia / factura *", type=["pdf"], key="upload_garantia_pdf")
        
        submitted = st.form_submit_button("💾 Desar Garantia", use_container_width=True)
        if submitted:
            if not titol.strip() or not dispositiu.strip() or not establiment.strip():
                st.error("Si us plau, omple com a mínim el Títol, el Dispositiu i l'Establiment.")
                return
            if not uploaded_pdf:
                st.error("Cal seleccionar o pujar un fitxer PDF.")
                return
                
            fname = uploaded_pdf.name
            target_path = get_pdf_path("Garanties", fname)
            try:
                with open(target_path, "wb") as f:
                    f.write(uploaded_pdf.getbuffer())
                pages = get_page_count(target_path)
            except Exception as e:
                st.error(f"Error desant el fitxer PDF: {e}")
                return
                
            docs = load_manteniment_docs()
            doc_id = f"gar_{int(datetime.now().timestamp() * 1000)}"
            etiquetes = [t.strip().lower() for t in etiquetes_str.split(",") if t.strip()]
            
            d_compra_str = data_compra.strftime("%d/%m/%Y")
            try:
                venc_date = data_compra.replace(year=data_compra.year + int(anys_garantia))
            except ValueError:
                venc_date = data_compra.replace(year=data_compra.year + int(anys_garantia), day=28)
            d_venc_str = venc_date.strftime("%d/%m/%Y")
            
            docs["garanties"].append({
                "id": doc_id,
                "titol": titol.strip(),
                "dispositiu": dispositiu.strip(),
                "marca": marca.strip() or "General",
                "model": model.strip(),
                "establiment": establiment.strip(),
                "num_factura": num_factura.strip(),
                "ubicacio": ubicacio,
                "fitxer": fname,
                "categoria": "Garanties",
                "pagines": pages,
                "data_compra": d_compra_str,
                "anys_garantia": int(anys_garantia),
                "data_venciment": d_venc_str,
                "import_compra": float(import_compra),
                "descripcio": descripcio.strip(),
                "data_afegit": datetime.now().strftime("%d/%m/%Y"),
                "etiquetes": etiquetes
            })
            
            if save_manteniment_docs(docs):
                st.success("Garantia registrada i desada correctament!")
                st.rerun()
            else:
                st.error("Error desant el registre JSON.")

@st.dialog("✏️ Editar Manual", width="large")
def edit_manual_dialog(doc: dict):
    """Diàleg per editar les dades d'un manual existent."""
    doc_id = doc.get('id', '')
    st.markdown(f"<h3 style='margin-top:0; color:#f39c12;'>✏️ Editar: {doc.get('titol')}</h3>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        titol = st.text_input("Títol del manual", value=doc.get("titol", ""))
        dispositiu = st.text_input("Dispositiu / Aparell", value=doc.get("dispositiu", ""))
    with c2:
        marca = st.text_input("Marca", value=doc.get("marca", ""))
        model = st.text_input("Model", value=doc.get("model", ""))
        
    c3, c4 = st.columns(2)
    locations = [
        "General", "Menjador", "Cuina", "Bany", "Dormitori",
        "Calefacció / Climatització", "Garatge", "Terrassa / Exterior", "Quadre Elèctric"
    ]
    cur_loc = doc.get("ubicacio", "General")
    loc_idx = locations.index(cur_loc) if cur_loc in locations else 0
    with c3:
        ubicacio = st.selectbox("Ubicació", locations, index=loc_idx)
        
    subcats = [
        "Climatització i Calefacció", "Electrodomèstics", "Electricitat i Domòtica",
        "Il·luminació", "Fontaneria", "Mobiliari", "Eines", "General"
    ]
    cur_sub = doc.get("subcategoria", "General")
    sub_idx = subcats.index(cur_sub) if cur_sub in subcats else 0
    with c4:
        subcat = st.selectbox("Àmbit / Subcategoria", subcats, index=sub_idx)
        
    descripcio = st.text_area("Descripció o observacions", value=doc.get("descripcio", ""), height=100)
    tags_str = ", ".join(doc.get("etiquetes", []))
    etiquetes_str = st.text_input("Etiquetes (separades per comes)", value=tags_str)
    
    st.caption(f"📁 Fitxer associat: <code>PDF/Manuals/{doc.get('fitxer')}</code> ({doc.get('pagines', 0)} pàgines)")
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    c_can, c_sub = st.columns([1, 2])
    with c_can:
        if st.button("Cancel·lar", key=f"btn_cancel_man_{doc_id}", use_container_width=True):
            st.rerun()
    with c_sub:
        submitted = st.button("💾 Desar canvis", key=f"btn_save_man_{doc_id}", type="primary", use_container_width=True)
    if submitted:
        docs = load_manteniment_docs()
        for idx, item in enumerate(docs.get("manuals", [])):
            if item.get("id") == doc.get("id"):
                docs["manuals"][idx].update({
                    "titol": titol.strip(),
                    "dispositiu": dispositiu.strip(),
                    "marca": marca.strip(),
                    "model": model.strip(),
                    "ubicacio": ubicacio,
                    "subcategoria": subcat,
                    "descripcio": descripcio.strip(),
                    "etiquetes": [t.strip().lower() for t in etiquetes_str.split(",") if t.strip()]
                })
                break
        save_manteniment_docs(docs)
        st.success("Manual actualitzat correctament!")
        st.rerun()

@st.dialog("✏️ Editar Garantia", width="large")
def edit_garantia_dialog(doc: dict):
    """Diàleg per editar les dades d'una garantia existent."""
    doc_id = doc.get('id', '')
    st.markdown(f"<h3 style='margin-top:0; color:#10b981;'>✏️ Editar: {doc.get('titol')}</h3>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        titol = st.text_input("Títol de la garantia", value=doc.get("titol", ""))
        dispositiu = st.text_input("Dispositiu / Article", value=doc.get("dispositiu", ""))
    with c2:
        marca = st.text_input("Marca", value=doc.get("marca", ""))
        model = st.text_input("Model / Nº Sèrie", value=doc.get("model", ""))
        
    c3, c4, c5 = st.columns(3)
    with c3:
        establiment = st.text_input("Establiment / Botiga", value=doc.get("establiment", ""))
    with c4:
        num_factura = st.text_input("Nº Factura / Tiquet", value=doc.get("num_factura", ""))
    with c5:
        import_compra = st.number_input("Preu (€)", min_value=0.0, value=float(doc.get("import_compra", 0.0)), step=1.0, format="%.2f")
        
    c6, c7, c8 = st.columns(3)
    d_compra_raw = doc.get("data_compra", "")
    compra_date_val = datetime.today().date()
    if d_compra_raw:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                compra_date_val = datetime.strptime(d_compra_raw, fmt).date()
                break
            except Exception:
                pass
    with c6:
        data_compra = st.date_input("Data de compra", value=compra_date_val, max_value=datetime.today().date(), format="DD/MM/YYYY")
    with c7:
        anys_garantia = st.number_input("Anys de cobertura", min_value=1, max_value=20, value=int(doc.get("anys_garantia", 3)), step=1)
    with c8:
        locations = ["Cuina", "Menjador", "Bany", "Dormitori", "Garatge", "General", "Terrassa / Exterior"]
        cur_loc = doc.get("ubicacio", "General")
        loc_idx = locations.index(cur_loc) if cur_loc in locations else 0
        ubicacio = st.selectbox("Ubicació", locations, index=loc_idx)
        
    descripcio = st.text_area("Notes de garantia o cobertura", value=doc.get("descripcio", ""), height=80)
    tags_str = ", ".join(doc.get("etiquetes", []))
    etiquetes_str = st.text_input("Etiquetes (separades per comes)", value=tags_str)
    
    st.caption(f"📁 Fitxer associat: <code>PDF/Garanties/{doc.get('fitxer')}</code>")
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    c_can, c_sub = st.columns([1, 2])
    with c_can:
        if st.button("Cancel·lar", key=f"btn_cancel_gar_{doc_id}", use_container_width=True):
            st.rerun()
    with c_sub:
        submitted = st.button("💾 Desar canvis", key=f"btn_save_gar_{doc_id}", type="primary", use_container_width=True)
    if submitted:
        docs = load_manteniment_docs()
        d_compra_str = data_compra.strftime("%d/%m/%Y")
        try:
            venc_date = data_compra.replace(year=data_compra.year + int(anys_garantia))
        except ValueError:
            venc_date = data_compra.replace(year=data_compra.year + int(anys_garantia), day=28)
        d_venc_str = venc_date.strftime("%d/%m/%Y")
        
        for idx, item in enumerate(docs.get("garanties", [])):
            if item.get("id") == doc.get("id"):
                docs["garanties"][idx].update({
                    "titol": titol.strip(),
                    "dispositiu": dispositiu.strip(),
                    "marca": marca.strip(),
                    "model": model.strip(),
                    "establiment": establiment.strip(),
                    "num_factura": num_factura.strip(),
                    "ubicacio": ubicacio,
                    "data_compra": d_compra_str,
                    "anys_garantia": int(anys_garantia),
                    "data_venciment": d_venc_str,
                    "import_compra": float(import_compra),
                    "descripcio": descripcio.strip(),
                    "etiquetes": [t.strip().lower() for t in etiquetes_str.split(",") if t.strip()]
                })
                break
        save_manteniment_docs(docs)
        st.success("Garantia actualitzada correctament!")
        st.rerun()

@st.dialog("🗑️ Eliminar Document", width="small")
def delete_document_dialog(category: str, doc_id: str, doc_title: str, filename: str):
    """Diàleg de confirmació per eliminar un document del registre i opcionalment del disc."""
    st.markdown(f"<h3 style='margin-top:0; color:#ef4444;'>🗑️ Eliminar Document</h3>", unsafe_allow_html=True)
    st.write(f"Segur que vols eliminar **{doc_title}** del registre?")
    
    esborrar_fitxer = st.checkbox(f"Eliminar també el fitxer PDF del disc (`PDF/{category}/{filename}`)", value=False)
    
    c_cancel, c_ok = st.columns(2)
    with c_cancel:
        if st.button("Cancel·lar", use_container_width=True):
            st.rerun()
    with c_ok:
        if st.button("Sí, eliminar", type="primary", use_container_width=True):
            docs = load_manteniment_docs()
            cat_key = "manuals" if category.lower() in ["manuals", "manual"] else "garanties"
            docs[cat_key] = [d for d in docs.get(cat_key, []) if d.get("id") != doc_id]
            save_manteniment_docs(docs)
            
            if esborrar_fitxer:
                fpath = get_pdf_path(category, filename)
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception as e:
                        st.warning(f"No s'ha pogut esborrar el fitxer físic: {e}")
                        
            st.success("Document eliminat correctament!")
            st.rerun()

OPCIONS_FEINA = [
    "Canvi llençols",
    "Neteja general",
    "Netejar banys",
    "Netejar cuina a fons",
    "Netejar vidres",
    "Passar aspirador i fregar",
    "Posar rentadora i estendre",
    "Planxar roba",
    "Buidar / posar rentaplats",
    "Treure brossa i reciclatge",
    "Neteja de terrassa / pati",
    "Purgar radiadors",
    "Revisar pressió i caldera",
    "Canviar filtre campana extractora",
    "Netejar filtres aire condicionat",
    "Descalcificar cafetera / electrodomèstics",
    "Netejar filtre rentadora / rentaplats",
    "Canviar bombeta / llum",
    "Reparar cisterna / aixeta",
    "Petites reparacions i bricolatge",
    "Pintura i arranjaments",
    "Regar plantes i jardineria",
    "Revisió detector de fum / seguretat",
    "Altres (especificar al costat)..."
]

@st.dialog("✏️ Editar Tasca de Manteniment", width="large")
def edit_task_dialog(task: dict, family_names: list):
    """Diàleg modal per editar una tasca de manteniment existent."""
    task_id = task.get("idManteniment", "")
    st.markdown(f"<h3 style='margin-top:0; color:#f39c12;'>✏️ Editar Tasca #{task_id}</h3>", unsafe_allow_html=True)
    if task.get("recurrencia"):
        st.info(f"🔁 Aquesta tasca forma part d'una sèrie periòdica: **{task.get('recurrencia')}**")
    
    c1, c2, c_avis = st.columns([1.5, 1.5, 1])
    with c1:
        d_raw = str(task.get("dataManteniment", "")).strip()
        d_val = datetime.today().date()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                d_val = datetime.strptime(d_raw, fmt).date()
                break
            except Exception:
                pass
        d_manteniment = st.date_input("Data Prevista (Manteniment) *", value=d_val, format="DD/MM/YYYY")
    with c2:
        tipus_opts = ["Feina casa", "Manteniment", "Reparació", "Neteja a fons", "Revisió periòdica", "Instal·lació / Millora", "Altres"]
        cur_tip = task.get("tipus", "Feina casa")
        tip_idx = tipus_opts.index(cur_tip) if cur_tip in tipus_opts else 0
        tipus = st.selectbox("Tipus Feina *", tipus_opts, index=tip_idx)
    with c_avis:
        cur_avis = task.get("diesAvis", 2)
        try:
            cur_avis = int(cur_avis)
        except (ValueError, TypeError):
            cur_avis = 2
        dies_avis = st.number_input("Dies d'avís", min_value=0, max_value=60, value=cur_avis, step=1, help="Dies abans de la tasca en què sortirà l'alerta")
        
    cur_feina = str(task.get("feina", "")).strip()
    c_feina1, c_feina2 = st.columns([1.5, 1.5])
    with c_feina1:
        feina_idx = OPCIONS_FEINA.index(cur_feina) if cur_feina in OPCIONS_FEINA else (len(OPCIONS_FEINA) - 1)
        feina_sel = st.selectbox("Feina concreta *", OPCIONS_FEINA, index=feina_idx)
    with c_feina2:
        default_custom = cur_feina if cur_feina not in OPCIONS_FEINA else ""
        feina_custom = st.text_input("O una altra feina concreta:", value=default_custom, placeholder="Escriu si vols canviar-la...")

    c3, c4 = st.columns([2, 1])
    with c3:
        raw_alerta = task.get("alertaA", ["Tothom"])
        if isinstance(raw_alerta, str):
            default_alerta = [x.strip() for x in raw_alerta.split(",") if x.strip()]
        elif isinstance(raw_alerta, list):
            default_alerta = raw_alerta
        else:
            default_alerta = ["Tothom"]
        default_alerta = [x for x in default_alerta if x in family_names]
        if not default_alerta:
            default_alerta = ["Tothom"]
        alertaA = st.multiselect("Alerta a *", options=family_names, default=default_alerta, help="Membre(s) de la família que rebran l'alerta")
    with c4:
        cur_acomp = str(task.get("acompliment", "No")).strip().lower()
        ac_idx = 1 if cur_acomp in ["sí", "si", "true"] else 0
        acompliment = st.selectbox("Acompliment", ["No", "Sí"], index=ac_idx)

    # SECCIÓ DE PERIODICITAT I REPETICIONS
    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#a78bfa; margin-top:0; margin-bottom:8px;'>🔄 Repetició / Periodicitat de la Tasca</h5>", unsafe_allow_html=True)

    cur_rec_str = task.get("recurrencia", "")
    cur_freq_guess, cur_int_guess, cur_unit_guess, cur_count_guess = parse_task_recurrence(cur_rec_str)
    
    freq_opts = [
        "Puntual (una sola vegada)",
        "Cada dia",
        "Cada setmana",
        "Cada 2 setmanes (quinzenal)",
        "Cada mes",
        "Cada 2 mesos",
        "Cada 3 mesos (trimestral)",
        "Cada 6 mesos (semestral)",
        "Cada any",
        "Personalitzat..."
    ]
    def_idx = freq_opts.index(cur_freq_guess) if cur_freq_guess in freq_opts else 0

    c_rec1, c_rec2 = st.columns([1.5, 1.5])
    with c_rec1:
        edit_freq_sel = st.selectbox(
            "Freqüència de repetició",
            freq_opts,
            index=def_idx,
            key=f"edit_freq_{task_id}"
        )

    edit_is_recurring = (edit_freq_sel != "Puntual (una sola vegada)")
    edit_custom_interval = cur_int_guess
    edit_custom_unit = cur_unit_guess
    edit_end_mode_code = "vegades"
    edit_rep_count = cur_count_guess if cur_count_guess > 1 else 4
    edit_until_date = None
    regenerate_future = False

    if edit_is_recurring:
        if edit_freq_sel == "Personalitzat...":
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                edit_custom_interval = st.number_input(
                    "Repetir cada (número):",
                    min_value=1,
                    max_value=365,
                    value=max(1, int(cur_int_guess)),
                    step=1,
                    key=f"edit_cint_{task_id}"
                )
            with c_p2:
                units = ["Dies", "Setmanes", "Mesos", "Anys"]
                u_idx = units.index(cur_unit_guess) if cur_unit_guess in units else 1
                edit_custom_unit = st.selectbox("Unitat de temps:", units, index=u_idx, key=f"edit_cunit_{task_id}")

        year_end_edit = date(d_manteniment.year, 12, 31)
        dates_until_end_year_edit = compute_recurring_dates(
            d_manteniment,
            edit_freq_sel,
            custom_interval=edit_custom_interval,
            custom_unit=edit_custom_unit,
            end_mode="data",
            until_date=year_end_edit,
            max_limit=370
        )
        max_fins_any_edit = len(dates_until_end_year_edit)

        with c_rec2:
            edit_mode_end = st.radio(
                "Com vols limitar la repetició?",
                ["Fins a final d'any (31/12)", "Per nombre de vegades", "Fins a una data límit"],
                index=0,
                horizontal=True,
                key=f"edit_modeend_{task_id}"
            )

        if edit_mode_end == "Fins a final d'any (31/12)":
            edit_end_mode_code = "data"
            edit_until_date = year_end_edit
            edit_rep_count = max_fins_any_edit
            st.caption(f"🗓️ Se seleccionen automàticament totes les ocurrències fins a final d'any (**{max_fins_any_edit} vegades** fins al 31/12/{d_manteniment.year}).")
        elif edit_mode_end == "Per nombre de vegades":
            c_n1, c_n2 = st.columns([1.5, 1.5], vertical_alignment="bottom")
            with c_n1:
                max_allowed_edit = max(1, max_fins_any_edit)
                cur_val_edit = int(cur_count_guess) if cur_count_guess >= 1 else max_allowed_edit
                cur_val_edit = min(cur_val_edit, max_allowed_edit)
                edit_rep_count = st.number_input(
                    f"Nombre total de vegades a generar (màx {max_allowed_edit}):",
                    min_value=1,
                    max_value=max_allowed_edit,
                    value=cur_val_edit,
                    step=1,
                    help=f"El màxim és {max_allowed_edit} perquè les tasques es generen any per any (fins al 31/12/{d_manteniment.year})",
                    key=f"edit_repcount_{task_id}"
                )
            with c_n2:
                st.caption(f"🏁 Fins a final d'any ({d_manteniment.year}) hi caben com a màxim **{max_fins_any_edit} vegades**.")
            edit_end_mode_code = "vegades"
        else:
            c_n1, c_n2 = st.columns([1.5, 1.5])
            with c_n1:
                default_until = min(year_end_edit, d_manteniment + timedelta(days=90))
                edit_until_date = st.date_input(
                    "Fins a la data límit:",
                    value=default_until,
                    min_value=d_manteniment,
                    max_value=year_end_edit,
                    format="DD/MM/YYYY",
                    help=f"Data límit màxima: 31/12/{d_manteniment.year}",
                    key=f"edit_until_{task_id}"
                )
            edit_end_mode_code = "data"

        edit_preview_dates = compute_recurring_dates(
            d_manteniment,
            edit_freq_sel,
            custom_interval=edit_custom_interval,
            custom_unit=edit_custom_unit,
            end_mode=edit_end_mode_code,
            occurrences=edit_rep_count,
            until_date=edit_until_date
        )
        if edit_freq_sel == "Personalitzat...":
            edit_freq_label = f"Cada {edit_custom_interval} {edit_custom_unit.lower()}"
        else:
            edit_freq_label = edit_freq_sel

        prev_dates_str = ", ".join([d.strftime("%d/%m/%Y") for d in edit_preview_dates[:6]])
        if len(edit_preview_dates) > 6:
            prev_dates_str += f"... (+{len(edit_preview_dates) - 6} dates més)"
        st.info(f"🔁 **Sèrie periòdica ({edit_freq_label}):** Es programaran **{len(edit_preview_dates)} esdeveniments**: {prev_dates_str}")

        if task.get("serie_id"):
            regenerate_future = st.checkbox("🔄 Actualitzar i regenerar les properes tasques d'aquesta sèrie", value=True, help="Si està marcat, substituirà les properes tasques pendents d'aquesta sèrie per les noves dates calculades", key=f"chk_regen_{task_id}")
        else:
            regenerate_future = True
    else:
        edit_preview_dates = [d_manteniment]
        edit_freq_label = ""
        if task.get("serie_id"):
            regenerate_future = st.checkbox("🗑️ Desvincular i eliminar les properes tasques pendents d'aquesta sèrie", value=True, help="Converteix aquesta tasca en puntual i suprimeix les ocurrències futures pendents de la sèrie", key=f"chk_unlink_{task_id}")

    sync_cal = st.checkbox("Actualitzar / Enviar a l'Agenda (Calendari)", value=bool(task.get("calendar_event_id")), key=f"edit_cal_{task_id}")
    
    # SECCIÓ DE SUBTASQUES
    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#38bdf8; margin-top:0; margin-bottom:6px;'>📎 Subtasques associades (opcional)</h5>", unsafe_allow_html=True)
    st.caption("Pots afegir subtasques amb cadència pròpia (ex: rentar el protector de llençols cada 6 mesos).")
    
    edit_subs_key = f"edit_subtasks_{task_id}"
    if edit_subs_key not in st.session_state:
        raw_subs = task.get("subtasques_template", [])
        if not raw_subs and task.get("subtasques"):
            raw_subs = task.get("subtasques")
        st.session_state[edit_subs_key] = copy.deepcopy(raw_subs) if raw_subs else []

    current_edit_subs = st.session_state[edit_subs_key]
    for s_idx, s_item in enumerate(current_edit_subs):
        c_sub_info, c_sub_del = st.columns([0.88, 0.12], vertical_alignment="center")
        with c_sub_info:
            cad_label = s_item.get("cadencia") or ("A cada repetició" if s_item.get("cadencia_tipus") == "sempre" else f"Cada {s_item.get('cadencia_valor', 1)} {s_item.get('cadencia_tipus', '')}")
            st.markdown(f"• **{s_item.get('titol', '')}** &nbsp; <span style='background:#1e293b; color:#38bdf8; border:1px solid #0284c7; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🔁 {cad_label}</span>", unsafe_allow_html=True)
        with c_sub_del:
            if st.button("🗑️", key=f"del_edit_sub_{task_id}_{s_idx}", help="Eliminar subtasca"):
                current_edit_subs.pop(s_idx)
                st.session_state[edit_subs_key] = current_edit_subs
                st.rerun()

    c_add_es1, c_add_es2, c_add_es3 = st.columns([1.5, 1.2, 0.6], vertical_alignment="bottom")
    with c_add_es1:
        edit_new_sub_title = st.text_input("Nova subtasca:", placeholder="Ex: Rentar protector de llençols...", key=f"inp_edit_subtitle_{task_id}")
    with c_add_es2:
        sub_cad_options = [
            "A cada repetició",
            "Cada 6 mesos",
            "Cada 3 mesos (trimestral)",
            "Cada 2 mesos",
            "Cada any",
            "Cada 2 repeticions",
            "Cada 3 repeticions",
            "Cada 4 repeticions",
            "Cada 12 repeticions (ex: 6 mesos si és quinzenal)"
        ]
        edit_new_sub_cad = st.selectbox("Cadència subtasca:", sub_cad_options, key=f"sel_edit_subcad_{task_id}")
    with c_add_es3:
        if st.button("➕ Afegir", key=f"btn_edit_addsub_{task_id}", use_container_width=True):
            if edit_new_sub_title.strip():
                cad_tipus = "sempre"
                cad_valor = 1
                if "mesos" in edit_new_sub_cad.lower():
                    cad_tipus = "mesos"
                    if "6" in edit_new_sub_cad: cad_valor = 6
                    elif "3" in edit_new_sub_cad: cad_valor = 3
                    elif "2" in edit_new_sub_cad: cad_valor = 2
                elif "any" in edit_new_sub_cad.lower():
                    cad_tipus = "mesos"
                    cad_valor = 12
                elif "repeticions" in edit_new_sub_cad.lower():
                    cad_tipus = "repeticions"
                    m_rep = re.search(r'cada\s+(\d+)', edit_new_sub_cad.lower())
                    cad_valor = int(m_rep.group(1)) if m_rep else 2
                    
                current_edit_subs.append({
                    "id": f"sub_{int(datetime.now().timestamp() * 1000)}_{len(current_edit_subs) + 1}",
                    "titol": edit_new_sub_title.strip(),
                    "cadencia": edit_new_sub_cad,
                    "cadencia_tipus": cad_tipus,
                    "cadencia_valor": cad_valor
                })
                st.session_state[edit_subs_key] = current_edit_subs
                st.rerun()

    observacions = st.text_area("Observacions / Detalls addicionals", value=task.get("observacions", ""), height=75, key=f"edit_obs_{task_id}")
    
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    c_can, c_sub = st.columns([1, 2])
    with c_can:
        if st.button("Cancel·lar", key=f"btn_cancel_edit_{task_id}", use_container_width=True):
            st.rerun()
    with c_sub:
        submitted = st.button("💾 Desar canvis", key=f"btn_save_edit_{task_id}", type="primary", use_container_width=True)

    if submitted:
        feina_final = feina_custom.strip() if feina_custom.strip() else (feina_sel if feina_sel != "Altres (especificar al costat)..." else "")
        if not feina_final.strip():
            st.error("Cal indicar la feina concreta a realitzar.")
            return
        d_str = d_manteniment.strftime("%d/%m/%Y")
        alerta_final = alertaA if alertaA else ["Tothom"]
        upd = {
            "dataManteniment": d_str,
            "diesAvis": int(dies_avis),
            "feina": feina_final.strip(),
            "tipus": tipus,
            "alertaA": alerta_final,
            "acompliment": acompliment,
            "observacions": observacions.strip(),
            "subtasques_template": current_edit_subs,
            "subtasques": filter_subtasks_for_occurrence(current_edit_subs, 0, d_manteniment, {})
        }
        update_manteniment_task_with_recurrence(
            task_id=task_id,
            updated_fields=upd,
            new_dates=edit_preview_dates,
            freq_label=edit_freq_label,
            regenerate_future=regenerate_future,
            send_to_calendar=sync_cal
        )
        st.success("Tasca actualitzada correctament!")
        st.rerun()

@st.dialog("🗑️ Eliminar Tasca de Manteniment", width="small")
def delete_task_dialog(task_id: int, task_title: str):
    """Diàleg de confirmació per eliminar una tasca del registre."""
    st.markdown(f"<h3 style='margin-top:0; color:#ef4444;'>🗑️ Eliminar Tasca</h3>", unsafe_allow_html=True)
    st.write(f"Segur que vols eliminar la tasca **#{task_id}**?")
    if task_title:
        st.caption(f"*{task_title}*")
        
    c_cancel, c_ok = st.columns(2)
    with c_cancel:
        if st.button("Cancel·lar", use_container_width=True):
            st.rerun()
    with c_ok:
        if st.button("Sí, eliminar", type="primary", use_container_width=True):
            delete_manteniment_task(task_id)
            st.success("Tasca eliminada correctament!")
            st.rerun()

@st.dialog("📅 Programar Tasques de Manteniment per al Proper Any", width="large")
def show_generar_any_manteniment_dialog(existing_tasks: list, family_names: list):
    """
    Diàleg interactiu (similar a Afegir Nou Any Comptable) per projectar i afegir
    totes les tasques de manteniment del proper any amb comprovació i camps editables.
    """
    st.markdown("<p style='color:#94a3b8; font-size:0.95rem; margin-bottom:12px;'>Aquesta rutina projecta i prepara el calendari de manteniment i feines de la llar per a tot el proper any. Pots revisar cadascuna de les tasques periòdiques proposades, activar o desactivar-les amb el check i modificar qualsevol paràmetre abans de desar-les.</p>", unsafe_allow_html=True)
    
    # 1. Determinar l'any a proposar
    existing_years = set()
    for t in existing_tasks:
        d_raw = str(t.get("dataManteniment", "")).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                existing_years.add(datetime.strptime(d_raw, fmt).year)
                break
            except Exception:
                pass
    curr_yr = datetime.today().year
    proposat_any = (max(existing_years) + 1) if existing_years else (curr_yr + 1)
    if proposat_any <= curr_yr:
        proposat_any = curr_yr + 1
        
    col_y1, col_y2 = st.columns([3, 5], vertical_alignment="center")
    with col_y1:
        target_year = st.number_input("📅 Any a programar:", min_value=2025, max_value=2050, value=proposat_any, step=1, key="target_mant_year_input")
    with col_y2:
        tasks_in_year = [t for t in existing_tasks if any(f"/{target_year}" in str(t.get("dataManteniment", "")) or f"-{target_year}" in str(t.get("dataManteniment", "")) for _ in [1])]
        if tasks_in_year:
            st.warning(f"⚠️ Ja hi ha {len(tasks_in_year)} tasques programades per al {target_year}. Les tasques seleccionades s'afegiran com a noves sèries.")
        else:
            st.success(f"✨ L'any {target_year} és nou al registre. Revisa les tasques recomanades a continuació:")

    # 2. Obtenir plantilles
    templates = get_recurring_task_templates(existing_tasks)
    
    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#38bdf8; margin-top:0; margin-bottom:10px;'>📋 Tasques de Manteniment proposades per a l'Any:</h5>", unsafe_allow_html=True)

    freq_opts = [
        "Cada 2 setmanes (quinzenal)",
        "Cada setmana",
        "Cada mes",
        "Cada 2 mesos",
        "Cada 3 mesos (trimestral)",
        "Cada 6 mesos (semestral)",
        "Cada any",
        "Personalitzat...",
        "Cada dia"
    ]
    tipus_opts = ["Feina casa", "Manteniment", "Reparació", "Neteja a fons", "Revisió periòdica", "Instal·lació / Millora", "Altres"]

    selected_plans = []
    total_projected_events = 0

    for idx, tpl in enumerate(templates):
        feina_nom = tpl["feina"]
        f_type = tpl["freq_type"]
        if f_type not in freq_opts:
            f_type = "Personalitzat..." if "personalitzat" in str(f_type).lower() else "Cada 2 setmanes (quinzenal)"
            
        with st.container(border=True):
            col_chk, col_tit = st.columns([0.08, 0.92], vertical_alignment="center")
            is_active = col_chk.checkbox("", value=True, key=f"plan_chk_{idx}")
            with col_tit:
                st.markdown(f"<span style='font-weight:700; font-size:1.05rem; color:#f8fafc;'>{feina_nom}</span> &nbsp;<span style='background:#1e293b; color:#c084fc; border:1px solid #9333ea; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🔁 {tpl['freq_type']}</span>", unsafe_allow_html=True)
            
            if is_active:
                c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.3, 1.1])
                with c1:
                    feina_val = st.text_input("Feina concreta", value=feina_nom, key=f"plan_feina_{idx}")
                with c2:
                    t_idx = tipus_opts.index(tpl["tipus"]) if tpl["tipus"] in tipus_opts else 0
                    tip_val = st.selectbox("Tipus Feina", tipus_opts, index=t_idx, key=f"plan_tip_{idx}")
                with c3:
                    fr_idx = freq_opts.index(f_type) if f_type in freq_opts else 0
                    freq_val = st.selectbox("Freqüència", freq_opts, index=fr_idx, key=f"plan_freq_{idx}")
                with c4:
                    def_m = tpl.get("def_month", 1)
                    def_d = tpl.get("def_day", 5)
                    try:
                        init_d = date(int(target_year), def_m, min(def_d, 28))
                    except Exception:
                        init_d = date(int(target_year), 1, 5)
                    start_d_val = st.date_input("Data inicial", value=init_d, format="DD/MM/YYYY", key=f"plan_date_{idx}")

                c_cust1, c_cust2 = st.columns([1.5, 2.5])
                c_int_val = tpl.get("custom_interval", 15)
                c_unit_val = tpl.get("custom_unit", "Dies")
                if freq_val == "Personalitzat...":
                    with c_cust1:
                        c_int_val = st.number_input("Repetir cada:", min_value=1, max_value=365, value=int(c_int_val), step=1, key=f"plan_cint_{idx}")
                    with c_cust2:
                        units = ["Dies", "Setmanes", "Mesos", "Anys"]
                        u_idx = units.index(c_unit_val) if c_unit_val in units else 0
                        c_unit_val = st.selectbox("Unitat:", units, index=u_idx, key=f"plan_cunit_{idx}")

                c_al1, c_al2 = st.columns([2, 1])
                with c_al1:
                    raw_alerta = tpl.get("alertaA", ["Tothom"])
                    if isinstance(raw_alerta, str):
                        raw_alerta = [x.strip() for x in raw_alerta.split(",") if x.strip()]
                    def_alerta = [x for x in raw_alerta if x in family_names] or ["Tothom"]
                    alerta_val = st.multiselect("Alerta a", family_names, default=def_alerta, key=f"plan_alerta_{idx}")
                with c_al2:
                    avis_val = st.number_input("Dies d'avís", min_value=0, max_value=60, value=int(tpl.get("diesAvis", 2)), step=1, key=f"plan_avis_{idx}")

                # Subtasques de la plantilla
                sub_list = tpl.get("subtasques_template", [])
                if sub_list:
                    subs_str = " | ".join([f"• {s.get('titol', '')} ({s.get('cadencia', 'Periòdic')})" for s in sub_list])
                    st.markdown(f"<div style='font-size:0.85rem; color:#93c5fd; background:#172554; padding:4px 8px; border-radius:6px; margin-top:4px;'>📎 <b>Subtasques:</b> {subs_str}</div>", unsafe_allow_html=True)

                # Calcular dates projectades per a l'any
                calc_dates = compute_recurring_dates_for_year(
                    start_date=start_d_val,
                    freq_type=freq_val,
                    custom_interval=c_int_val,
                    custom_unit=c_unit_val,
                    target_year=int(target_year)
                )
                total_projected_events += len(calc_dates)
                
                prev_text = ", ".join([d.strftime("%d/%m") for d in calc_dates[:5]])
                if len(calc_dates) > 5:
                    prev_text += f"... (+{len(calc_dates)-5} més)"
                st.caption(f"🗓️ Se'n generaran **{len(calc_dates)} tasques** al llarg de l'any {target_year} ({prev_text})")

                selected_plans.append({
                    "feina": feina_val.strip(),
                    "tipus": tip_val,
                    "diesAvis": int(avis_val),
                    "alertaA": alerta_val or ["Tothom"],
                    "acompliment": "No",
                    "observacions": tpl.get("observacions", ""),
                    "subtasques_template": sub_list,
                    "dates": calc_dates,
                    "freq_label": f"Cada {c_int_val} {c_unit_val.lower()}" if freq_val == "Personalitzat..." else freq_val
                })

    st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
    c_bot1, c_bot2 = st.columns([2, 1], vertical_alignment="center")
    with c_bot1:
        sync_calendar_all = st.checkbox("📅 Sincronitzar totes les tasques generades amb l'Agenda (Calendari familiar)", value=True, key="chk_plan_synccal")
        st.markdown(f"<b>Total tasques a generar per al {target_year}: <span style='color:#f39c12; font-size:1.1rem;'>{total_projected_events} esdeveniments</span></b> ({len(selected_plans)} sèries)", unsafe_allow_html=True)
    with c_bot2:
        btn_generate = st.button(f"💾 Generar tasques per al {target_year}", type="primary", use_container_width=True, key="btn_submit_year_plans")

    if btn_generate:
        if not selected_plans or total_projected_events == 0:
            st.error("No s'ha seleccionat cap tasca per generar.")
            return

        with st.spinner(f"Generant {total_projected_events} tasques de manteniment per al {target_year}..."):
            created_count = 0
            for plan in selected_plans:
                plan_dates = plan["dates"]
                if not plan_dates:
                    continue
                task_base = {
                    "feina": plan["feina"],
                    "tipus": plan["tipus"],
                    "diesAvis": plan["diesAvis"],
                    "alertaA": plan["alertaA"],
                    "acompliment": "No",
                    "observacions": plan["observacions"],
                    "subtasques_template": plan["subtasques_template"]
                }
                res = add_manteniment_tasks_batch(
                    task_data=task_base,
                    dates=plan_dates,
                    send_to_calendar=sync_calendar_all,
                    freq_label=plan["freq_label"]
                )
                created_count += len(res)

        st.success(f"🎉 S'han generat i programat correctament {created_count} tasques de manteniment per a l'any {target_year}!")
        st.rerun()

def render():
    render_header_with_avatar("<h2 style='margin:0; color:#f39c12;'>🛠️ Manteniment de la Llar</h2>", "manteniment")
    st.write("---")

    # Inicialitzar i auto-sincronitzar fitxers nous de disc en carregar la primera vegada
    if "manteniment_synced" not in st.session_state:
        try:
            sync_pdf_directory()
        except Exception as e:
            print("Auto-sync error:", e)
        st.session_state["manteniment_synced"] = True

    docs_data = load_manteniment_docs()
    manuals = docs_data.get("manuals", [])
    garanties = docs_data.get("garanties", [])

    app_cfg = load_app_config()
    fam_members = app_cfg.get("familia", [])
    family_names = ["Tothom"] + [m.get("nom") for m in fam_members if m.get("nom")]
    if len(family_names) == 1:
        family_names = ["Tothom", "Enric", "Isabel", "Jordi", "Mireia"]

    tasks = load_registre_manteniment()

    if st.session_state.get("show_generar_any_manteniment"):
        st.session_state["show_generar_any_manteniment"] = False
        show_generar_any_manteniment_dialog(tasks, family_names)

    tabs_list = ["📋 Registre Manteniment", "📖 Manuals", "🛡️ Garanties"]
    tab_mapping = {
        "registre": "📋 Registre Manteniment",
        "registre_manteniment": "📋 Registre Manteniment",
        "tasques": "📋 Registre Manteniment",
        "manuals": "📖 Manuals",
        "manual": "📖 Manuals",
        "garanties": "🛡️ Garanties",
        "garantia": "🛡️ Garanties"
    }
    tab_param = st.query_params.get("tab")
    default_tab = tab_mapping.get(tab_param)
    if default_tab not in tabs_list:
        default_tab = "📋 Registre Manteniment"

    tab_registre, tab_manuals, tab_garanties = st.tabs(tabs_list, default=default_tab, key=f"tabs_manteniment_{tab_param or 'main'}")

    # =========================================================================
    # PESTANYA 1: REGISTRE DE MANTENIMENT
    # =========================================================================
    with tab_registre:
        st.markdown("<p style='color:#94a3b8; font-size:0.95rem; margin:0 0 12px 0;'>Gestió i planificació de manteniment periòdic i tasques de la llar.</p>", unsafe_allow_html=True)

        # 1. FORMULARI D'ENTRADA
        with st.container(border=True):
            st.markdown("<h4 style='color:#f39c12; margin-top:0; margin-bottom:12px;'>➕ Nova Tasca de Manteniment</h4>", unsafe_allow_html=True)
            form_counter = st.session_state.get("mant_form_count", 0)

            c_f1, c_f2, c_f3 = st.columns([1.5, 1.5, 1])
            with c_f1:
                data_manteniment_input = st.date_input(
                    "Data Prevista *",
                    value=datetime.today().date(),
                    format="DD/MM/YYYY",
                    help="Data inicial en què s'ha de dur a terme la tasca de manteniment",
                    key=f"new_dmant_{form_counter}"
                )
            with c_f2:
                tipus_input = st.selectbox(
                    "Tipus Feina *",
                    ["Feina casa", "Manteniment", "Reparació", "Neteja a fons", "Revisió periòdica", "Instal·lació / Millora", "Altres"],
                    index=0,
                    key=f"new_tipus_{form_counter}"
                )
            with c_f3:
                dies_avis_input = st.number_input(
                    "Dies d'avís",
                    min_value=0,
                    max_value=60,
                    value=2,
                    step=1,
                    help="Dies abans de la tasca en què començarà a sortir l'alerta a la campaneta",
                    key=f"new_avis_{form_counter}"
                )
            
            c_feina1, c_feina2 = st.columns([1.5, 1.5])
            with c_feina1:
                feina_sel = st.selectbox(
                    "Feina concreta *",
                    OPCIONS_FEINA,
                    index=0,
                    help="Tria la feina concreta de la llista (ex: Canvi llençols, Neteja general...)",
                    key=f"new_feinasel_{form_counter}"
                )
            with c_feina2:
                feina_custom = st.text_input(
                    "O una altra feina concreta (opcional):",
                    placeholder="Escriu aquí si vols especificar una feina diferent...",
                    help="Si escrius aquí, s'utilitzarà aquest text en lloc del desplegable",
                    key=f"new_feinacust_{form_counter}"
                )

            c_al1, c_al2 = st.columns([2, 1])
            with c_al1:
                alerta_input = st.multiselect(
                    "Alerta a *",
                    options=family_names,
                    default=["Tothom"],
                    help="Membre(s) de la família a qui li apareixerà com a avís a la campaneta",
                    key=f"new_alerta_{form_counter}"
                )
            with c_al2:
                acompliment_input = st.selectbox(
                    "Acompliment inicial",
                    ["No", "Sí"],
                    index=0,
                    key=f"new_acomp_{form_counter}"
                )

            # SECCIÓ DE PERIODICITAT I EVENTS REPETITIUS
            st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
            st.markdown("<h5 style='color:#a78bfa; margin-top:0; margin-bottom:8px;'>🔄 Repetició / Periodicitat de la Tasca</h5>", unsafe_allow_html=True)

            freq_opts = [
                "Puntual (una sola vegada)",
                "Cada dia",
                "Cada setmana",
                "Cada 2 setmanes (quinzenal)",
                "Cada mes",
                "Cada 2 mesos",
                "Cada 3 mesos (trimestral)",
                "Cada 6 mesos (semestral)",
                "Cada any",
                "Personalitzat..."
            ]

            c_rec1, c_rec2 = st.columns([1.5, 1.5])
            with c_rec1:
                freq_sel = st.selectbox(
                    "Freqüència de repetició",
                    freq_opts,
                    index=0,
                    help="Tria si aquesta tasca s'ha de repetir periòdicament en el calendari",
                    key=f"new_freq_{form_counter}"
                )

            is_recurring = (freq_sel != "Puntual (una sola vegada)")
            custom_interval = 1
            custom_unit = "Dies"
            end_mode_code = "vegades"
            rep_count = 1
            until_date = None

            if is_recurring:
                if freq_sel == "Personalitzat...":
                    c_p1, c_p2 = st.columns(2)
                    with c_p1:
                        custom_interval = st.number_input(
                            "Repetir cada (número):",
                            min_value=1,
                            max_value=365,
                            value=2,
                            step=1,
                            help="Ex: 2 per a cada 2 setmanes, 15 per a cada 15 dies, 3 per a cada 3 mesos...",
                            key=f"new_cint_{form_counter}"
                        )
                    with c_p2:
                        custom_unit = st.selectbox(
                            "Unitat de temps:",
                            ["Dies", "Setmanes", "Mesos", "Anys"],
                            index=1,
                            key=f"new_cunit_{form_counter}"
                        )

                year_end_new = date(data_manteniment_input.year, 12, 31)
                dates_until_end_year_new = compute_recurring_dates(
                    data_manteniment_input,
                    freq_sel,
                    custom_interval=custom_interval,
                    custom_unit=custom_unit,
                    end_mode="data",
                    until_date=year_end_new,
                    max_limit=370
                )
                max_fins_any_new = len(dates_until_end_year_new)

                with c_rec2:
                    mode_end = st.radio(
                        "Com vols limitar la repetició?",
                        ["Fins a final d'any (31/12)", "Per nombre de vegades", "Fins a una data límit"],
                        index=0,
                        horizontal=True,
                        key=f"new_modeend_{form_counter}"
                    )

                if mode_end == "Fins a final d'any (31/12)":
                    end_mode_code = "data"
                    until_date = year_end_new
                    rep_count = max_fins_any_new
                    st.caption(f"🗓️ Se seleccionen automàticament totes les ocurrències fins a final d'any (**{max_fins_any_new} vegades** fins al 31/12/{data_manteniment_input.year}).")
                elif mode_end == "Per nombre de vegades":
                    c_n1, c_n2 = st.columns([1.5, 1.5], vertical_alignment="bottom")
                    with c_n1:
                        max_allowed_new = max(1, max_fins_any_new)
                        rep_count = st.number_input(
                            f"Nombre total de vegades a generar (màx {max_allowed_new}):",
                            min_value=1,
                            max_value=max_allowed_new,
                            value=max_allowed_new,
                            step=1,
                            help=f"El màxim és {max_allowed_new} perquè les tasques es generen any per any (fins al 31/12/{data_manteniment_input.year})",
                            key=f"new_repcount_{form_counter}"
                        )
                    with c_n2:
                        st.caption(f"🏁 Fins a final d'any ({data_manteniment_input.year}) hi caben com a màxim **{max_fins_any_new} vegades**.")
                    end_mode_code = "vegades"
                else:
                    c_n1, c_n2 = st.columns([1.5, 1.5])
                    with c_n1:
                        default_until = min(year_end_new, data_manteniment_input + timedelta(days=90))
                        until_date = st.date_input(
                            "Fins a la data límit:",
                            value=default_until,
                            min_value=data_manteniment_input,
                            max_value=year_end_new,
                            format="DD/MM/YYYY",
                            help=f"Data límit màxima: 31/12/{data_manteniment_input.year}",
                            key=f"new_until_{form_counter}"
                        )
                    end_mode_code = "data"

                preview_dates = compute_recurring_dates(
                    data_manteniment_input,
                    freq_sel,
                    custom_interval=custom_interval,
                    custom_unit=custom_unit,
                    end_mode=end_mode_code,
                    occurrences=rep_count,
                    until_date=until_date
                )

                if freq_sel == "Personalitzat...":
                    freq_label_text = f"Cada {custom_interval} {custom_unit.lower()}"
                else:
                    freq_label_text = freq_sel

                preview_str = ", ".join([d.strftime("%d/%m/%Y") for d in preview_dates[:6]])
                if len(preview_dates) > 6:
                    preview_str += f"... (+{len(preview_dates) - 6} dates més)"
                st.info(f"🔁 **Sèrie periòdica ({freq_label_text}):** Es generaran **{len(preview_dates)} esdeveniments**: {preview_str}")
            else:
                preview_dates = [data_manteniment_input]
                freq_label_text = ""

            # SECCIÓ DE SUBTASQUES ASSOCIADES
            st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
            st.markdown("<h5 style='color:#38bdf8; margin-top:0; margin-bottom:6px;'>📎 Subtasques associades (opcional)</h5>", unsafe_allow_html=True)
            st.caption("Pots afegir subtasques amb la seva pròpia cadència (ex: Canvi de llençols cada 15 dies, però rentar el protector de llençols cada 6 mesos).")

            new_subs_key = f"new_subtasks_{form_counter}"
            if new_subs_key not in st.session_state:
                st.session_state[new_subs_key] = []

            current_new_subs = st.session_state[new_subs_key]
            for s_idx, s_item in enumerate(current_new_subs):
                c_sub_info, c_sub_del = st.columns([0.88, 0.12], vertical_alignment="center")
                with c_sub_info:
                    cad_label = s_item.get("cadencia") or ("A cada repetició" if s_item.get("cadencia_tipus") == "sempre" else f"Cada {s_item.get('cadencia_valor', 1)} {s_item.get('cadencia_tipus', '')}")
                    st.markdown(f"• **{s_item.get('titol', '')}** &nbsp; <span style='background:#1e293b; color:#38bdf8; border:1px solid #0284c7; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🔁 {cad_label}</span>", unsafe_allow_html=True)
                with c_sub_del:
                    if st.button("🗑️", key=f"del_newsub_{form_counter}_{s_idx}", help="Eliminar subtasca"):
                        current_new_subs.pop(s_idx)
                        st.session_state[new_subs_key] = current_new_subs
                        st.rerun()

            c_add_ns1, c_add_ns2, c_add_ns3 = st.columns([1.5, 1.2, 0.6], vertical_alignment="bottom")
            with c_add_ns1:
                new_sub_title = st.text_input("Nom de la subtasca:", placeholder="Ex: Rentar protector de llençols...", key=f"inp_newsub_title_{form_counter}")
            with c_add_ns2:
                sub_cad_options = [
                    "A cada repetició",
                    "Cada 6 mesos",
                    "Cada 3 mesos (trimestral)",
                    "Cada 2 mesos",
                    "Cada any",
                    "Cada 2 repeticions",
                    "Cada 3 repeticions",
                    "Cada 4 repeticions",
                    "Cada 12 repeticions (ex: 6 mesos si és quinzenal)"
                ]
                new_sub_cad = st.selectbox("Cadència subtasca:", sub_cad_options, key=f"sel_newsub_cad_{form_counter}")
            with c_add_ns3:
                if st.button("➕ Afegir", key=f"btn_add_newsub_{form_counter}", use_container_width=True):
                    if new_sub_title.strip():
                        cad_tipus = "sempre"
                        cad_valor = 1
                        if "mesos" in new_sub_cad.lower():
                            cad_tipus = "mesos"
                            if "6" in new_sub_cad: cad_valor = 6
                            elif "3" in new_sub_cad: cad_valor = 3
                            elif "2" in new_sub_cad: cad_valor = 2
                        elif "any" in new_sub_cad.lower():
                            cad_tipus = "mesos"
                            cad_valor = 12
                        elif "repeticions" in new_sub_cad.lower():
                            cad_tipus = "repeticions"
                            m_rep = re.search(r'cada\s+(\d+)', new_sub_cad.lower())
                            cad_valor = int(m_rep.group(1)) if m_rep else 2

                        current_new_subs.append({
                            "id": f"sub_{int(datetime.now().timestamp() * 1000)}_{len(current_new_subs) + 1}",
                            "titol": new_sub_title.strip(),
                            "cadencia": new_sub_cad,
                            "cadencia_tipus": cad_tipus,
                            "cadencia_valor": cad_valor
                        })
                        st.session_state[new_subs_key] = current_new_subs
                        st.rerun()

            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            observacions_input = st.text_area(
                "Observacions / Detalls addicionals",
                placeholder="Instruccions addicionals, eines necessàries, telèfon de contacte, passos...",
                height=75,
                key=f"new_obs_{form_counter}"
            )

            c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="center")
            with c_sub1:
                send_cal_input = st.checkbox("📅 Enviar directament a l'Agenda (Calendari familiar)", value=True, key=f"new_sendcal_{form_counter}")
            with c_sub2:
                btn_label = f"💾 Desar {len(preview_dates)} Tasques al Registre" if len(preview_dates) > 1 else "💾 Desar Tasca al Registre"
                sub_btn = st.button(btn_label, type="primary", use_container_width=True, key=f"btn_sub_alta_{form_counter}")

            if sub_btn:
                feina_final = feina_custom.strip() if feina_custom.strip() else (feina_sel if feina_sel != "Altres (especificar al costat)..." else "")
                if not feina_final.strip():
                    st.error("Cal indicar la feina concreta a realitzar.")
                else:
                    alerta_members = alerta_input if alerta_input else ["Tothom"]
                    task_base = {
                        "feina": feina_final.strip(),
                        "tipus": tipus_input,
                        "diesAvis": int(dies_avis_input),
                        "alertaA": alerta_members,
                        "acompliment": acompliment_input,
                        "observacions": observacions_input.strip(),
                        "subtasques_template": current_new_subs
                    }
                    res_tasks = add_manteniment_tasks_batch(
                        task_base,
                        preview_dates,
                        send_to_calendar=send_cal_input,
                        freq_label=freq_label_text
                    )
                    st.session_state["mant_form_count"] = form_counter + 1
                    st.session_state.pop(new_subs_key, None)
                    if len(res_tasks) > 1:
                        st.success(f"S'han creat correctament {len(res_tasks)} tasques periòdiques de manteniment (#{res_tasks[0].get('idManteniment')} a #{res_tasks[-1].get('idManteniment')})!")
                    else:
                        st.success(f"Tasca #{res_tasks[0].get('idManteniment')} registrada correctament!")
                    st.rerun()

        # 2. LLISTAT DE LA BD
        st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#38bdf8; margin-bottom:12px;'>📋 Llistat de la Base de Dades de Manteniment</h4>", unsafe_allow_html=True)

        # Càlcul de mètriques
        total_tasques = len(tasks)
        pendents_count = 0
        acomplertes_count = 0
        vencudes_count = 0
        avui = datetime.today().date()

        for t in tasks:
            is_done = str(t.get("acompliment", "No")).strip().lower() in ["sí", "si", "true"]
            if is_done:
                acomplertes_count += 1
            else:
                pendents_count += 1
                d_str = str(t.get("dataManteniment", "")).strip()
                d_obj = None
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        d_obj = datetime.strptime(d_str, fmt).date()
                        break
                    except Exception:
                        pass
                if d_obj and d_obj < avui:
                    vencudes_count += 1

        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            st.metric("📌 Total Tasques", total_tasques)
        with col_t2:
            st.metric("⏳ Pendents", pendents_count)
        with col_t3:
            st.metric("✅ Acomplertes", acomplertes_count)
        with col_t4:
            st.metric("⚠️ Vençudes", vencudes_count)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Filtres
        col_c1, col_c2, col_c3, col_c4 = st.columns([2.5, 1.3, 1.3, 1.3])
        with col_c1:
            cerca_text = st.text_input("🔍 Cercar per feina, tipus o observació...", placeholder="Ex: llençols, neteja, caldera, radiadors...", key="search_reg_manteniment")
        with col_c2:
            filtre_estat = st.selectbox("Estat", ["Tots", "⏳ Pendents", "✅ Acomplertes", "⚠️ Vençudes"], key="filtre_estat_mant")
        with col_c3:
            all_tipus = ["Tots"] + sorted(list(set(t.get("tipus", "") for t in tasks if t.get("tipus"))))
            filtre_tipus = st.selectbox("Tipus Feina", all_tipus, key="filtre_tipus_mant")
        with col_c4:
            filtre_persona = st.selectbox("Persona", family_names, key="filtre_persona_mant")

        # Filtrar tasques
        filtered_tasks = tasks
        if cerca_text.strip():
            q = cerca_text.strip().lower()
            filtered_tasks = [t for t in filtered_tasks if q in str(t.get("feina", "")).lower() or q in str(t.get("observacions", "")).lower() or q in str(t.get("tipus", "")).lower() or q in str(t.get("alertaA", "")).lower() or q in str(t.get("recurrencia", "")).lower()]
        if filtre_estat == "⏳ Pendents":
            filtered_tasks = [t for t in filtered_tasks if str(t.get("acompliment", "No")).strip().lower() not in ["sí", "si", "true"]]
        elif filtre_estat == "✅ Acomplertes":
            filtered_tasks = [t for t in filtered_tasks if str(t.get("acompliment", "No")).strip().lower() in ["sí", "si", "true"]]
        elif filtre_estat == "⚠️ Vençudes":
            def _is_vencuda(t):
                if str(t.get("acompliment", "No")).strip().lower() in ["sí", "si", "true"]: return False
                d_str = str(t.get("dataManteniment", "")).strip()
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(d_str, fmt).date() < avui
                    except Exception:
                        pass
                return False
            filtered_tasks = [t for t in filtered_tasks if _is_vencuda(t)]

        if filtre_tipus != "Tots":
            filtered_tasks = [t for t in filtered_tasks if t.get("tipus") == filtre_tipus]
        if filtre_persona != "Tothom":
            def _member_match(t, person):
                a = t.get("alertaA", "")
                if isinstance(a, list):
                    return person in a or "Tothom" in a
                elif isinstance(a, str):
                    parts = [p.strip() for p in a.split(",") if p.strip()]
                    return person in parts or "Tothom" in parts
                return False
            filtered_tasks = [t for t in filtered_tasks if _member_match(t, filtre_persona)]

        # Selector de format de visualització
        c_mode1, c_mode2 = st.columns([3, 1], vertical_alignment="center")
        with c_mode1:
            view_mode = st.radio("Format de visualització", ["📇 Targetes interactives", "📊 Taula de dades (Dataframe / CSV)"], horizontal=True, key="view_mode_mant")
        with c_mode2:
            if filtered_tasks:
                df_export = pd.DataFrame(filtered_tasks)
                cols_order = ["idManteniment", "dataAlta", "dataManteniment", "diesAvis", "feina", "tipus", "alertaA", "recurrencia", "acompliment", "subtasques", "observacions"]
                for c in cols_order:
                    if c not in df_export.columns: df_export[c] = ""
                df_export["alertaA"] = df_export["alertaA"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                df_export["subtasques"] = df_export["subtasques"].apply(
                    lambda subs: ", ".join([f"{s.get('titol')} ({'Fet' if s.get('fet') else 'Pendent'})" for s in subs]) if isinstance(subs, list) else str(subs)
                )
                df_export = df_export[cols_order]
                csv_data = df_export.to_csv(sep=';', index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv_data,
                    file_name="manteniment.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="dl_csv_manteniment"
                )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        if not filtered_tasks:
            if not tasks:
                st.info("Encara no hi ha cap tasca de manteniment registrada. Fes servir el formulari superior per afegir-ne una.")
            else:
                st.info("No hi ha cap tasca que coincideixi amb els filtres seleccionats.")
        else:
            if view_mode == "📊 Taula de dades (Dataframe / CSV)":
                df_display = pd.DataFrame(filtered_tasks)
                cols_order = ["idManteniment", "dataAlta", "dataManteniment", "diesAvis", "feina", "tipus", "alertaA", "recurrencia", "acompliment", "subtasques", "observacions"]
                for c in cols_order:
                    if c not in df_display.columns: df_display[c] = ""
                df_display["alertaA"] = df_display["alertaA"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                df_display["subtasques"] = df_display["subtasques"].apply(
                    lambda subs: ", ".join([f"{s.get('titol')} ({'Fet' if s.get('fet') else 'Pendent'})" for s in subs]) if isinstance(subs, list) else ""
                )
                df_display = df_display[cols_order]
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "idManteniment": st.column_config.NumberColumn("ID", width="small"),
                        "dataAlta": st.column_config.TextColumn("Data Alta", width="small"),
                        "dataManteniment": st.column_config.TextColumn("Data Prevista", width="small"),
                        "diesAvis": st.column_config.NumberColumn("Dies Avís", width="small", help="Dies abans en què començarà l'avís"),
                        "feina": st.column_config.TextColumn("Feina Concreta", width="medium"),
                        "tipus": st.column_config.TextColumn("Tipus Feina", width="small"),
                        "alertaA": st.column_config.TextColumn("Alerta a", width="medium"),
                        "recurrencia": st.column_config.TextColumn("Periodicitat", width="medium"),
                        "acompliment": st.column_config.TextColumn("Acomplert", width="small"),
                        "subtasques": st.column_config.TextColumn("Subtasques", width="medium"),
                        "observacions": st.column_config.TextColumn("Observacions")
                    }
                )
            else:
                for task in filtered_tasks:
                    task_id = task.get("idManteniment", "")
                    is_done = str(task.get("acompliment", "No")).strip().lower() in ["sí", "si", "true"]
                    
                    d_prev_str = str(task.get("dataManteniment", "")).strip()
                    d_obj = None
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            d_obj = datetime.strptime(d_prev_str, fmt).date()
                            break
                        except Exception:
                            pass
                            
                    delta = (d_obj - avui).days if d_obj else 999
                    
                    if is_done:
                        status_html = "<span style='background:#14532d; color:#86efac; border:1px solid #22c55e; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.75rem;'>✅ Acomplerta</span>"
                    elif delta < 0:
                        status_html = f"<span style='background:#7f1d1d; color:#fca5a5; border:1px solid #ef4444; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.75rem;'>⚠️ Vençuda fa {abs(delta)} dies ({d_prev_str})</span>"
                    elif delta == 0:
                        status_html = f"<span style='background:#7c2d12; color:#fdba74; border:1px solid #f97316; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.75rem;'>🔔 Prevista per a AVUI!</span>"
                    else:
                        status_html = f"<span style='background:#1e3a8a; color:#93c5fd; border:1px solid #3b82f6; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.75rem;'>⏳ Pendent (en {delta} dies - {d_prev_str})</span>"

                    task_feina = str(task.get("feina", "")).strip()
                    task_obs = str(task.get("observacions", "")).strip()
                    main_title = task_feina if task_feina else task_obs

                    alerta_raw = task.get("alertaA", "Tothom")
                    alerta_txt = ", ".join(alerta_raw) if isinstance(alerta_raw, list) else str(alerta_raw)
                    dies_av_badge = task.get("diesAvis", 2)
                    rec_val = task.get("recurrencia", "")
                    rec_badge = f"<span style='background:#1e293b; color:#c084fc; border:1px solid #9333ea; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🔁 {rec_val}</span>" if rec_val else ""

                    with st.container(border=True):
                        c_card_left, c_card_right = st.columns([7.5, 2.5], vertical_alignment="center")
                        with c_card_left:
                            badges_list = [
                                f"<span style='background:#0f172a; color:#f8fafc; border:1px solid #334155; padding:2px 8px; border-radius:8px; font-weight:700; font-size:0.8rem;'>#{task_id}</span>",
                                status_html,
                                f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #475569; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🏷️ {task.get('tipus', 'Feina casa')}</span>"
                            ]
                            if rec_badge:
                                badges_list.append(rec_badge)
                            badges_list.extend([
                                f"<span style='background:#1e293b; color:#f59e0b; border:1px solid #d97706; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>👤 Alerta: {alerta_txt}</span>",
                                f"<span style='background:#1e293b; color:#38bdf8; border:1px solid #0284c7; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🔔 Avís: {dies_av_badge}d abans</span>",
                                f"<span style='color:#64748b; font-size:0.75rem; margin-left:auto;'>Alta: {task.get('dataAlta', '')}</span>"
                            ])
                            badges_html = "".join(badges_list)
                            obs_html = f"<div style='font-size:0.9rem; color:#94a3b8; margin-top:3px;'>📝 {task_obs}</div>" if (task_feina and task_obs) else ""

                            card_html = (
                                f"<div style='display:flex; gap:8px; align-items:center; margin-bottom:6px; flex-wrap:wrap;'>{badges_html}</div>"
                                f"<div style='font-size:1.05rem; font-weight:700; color:#f8fafc; margin-top:4px;'>🔨 {main_title}</div>"
                                f"{obs_html}"
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

                            # Subtasques de la targeta
                            card_subs = task.get("subtasques", [])
                            if card_subs and isinstance(card_subs, list):
                                done_s = sum(1 for s in card_subs if s.get("fet", False))
                                tot_s = len(card_subs)
                                prog_color = "#22c55e" if done_s == tot_s else "#38bdf8"
                                st.markdown(f"<div style='font-size:0.82rem; font-weight:600; color:{prog_color}; margin-top:8px; margin-bottom:4px;'>📋 Subtasques ({done_s}/{tot_s} completades):</div>", unsafe_allow_html=True)
                                for s_idx, s_item in enumerate(card_subs):
                                    s_id = s_item.get("id", f"sub_{s_idx+1}")
                                    s_title = s_item.get("titol", "")
                                    s_fet = bool(s_item.get("fet", False))
                                    s_cad = s_item.get("cadencia", "")
                                    badge_c = f" <span style='font-size:0.75rem; color:#94a3b8;'>({s_cad})</span>" if s_cad else ""
                                    
                                    chk_val = st.checkbox(
                                        f"{s_title}{badge_c}",
                                        value=s_fet,
                                        key=f"card_subchk_{task_id}_{s_id}"
                                    )
                                    if chk_val != s_fet:
                                        toggle_subtask_acompliment(task_id, s_id)
                                        st.rerun()

                            if task.get("calendar_event_id"):
                                st.caption("📅 Tasca sincronitzada amb l'Agenda")
                        with c_card_right:
                            c_btn1, c_btn2 = st.columns(2)
                            with c_btn1:
                                if is_done:
                                    if st.button("↩️ Pendent", key=f"btn_toggle_{task_id}", use_container_width=True, help="Marcar com a pendent"):
                                        toggle_manteniment_acompliment(task_id)
                                        st.rerun()
                                else:
                                    if st.button("✅ Fet", key=f"btn_toggle_{task_id}", type="primary", use_container_width=True, help="Marcar com a acomplerta"):
                                        toggle_manteniment_acompliment(task_id)
                                        st.rerun()
                            with c_btn2:
                                if st.button("✏️ Editar", key=f"btn_edit_task_{task_id}", use_container_width=True):
                                    edit_task_dialog(task, family_names)
                            
                            c_btn3, c_btn4 = st.columns(2)
                            with c_btn3:
                                has_cal = bool(task.get("calendar_event_id"))
                                btn_cal_label = "📅 Veure Agenda" if has_cal else "📅 Sincro Agenda"
                                if st.button(btn_cal_label, key=f"btn_cal_task_{task_id}", use_container_width=True, help="Obrir l'Agenda o sincronitzar la tasca"):
                                    try:
                                        from core.calendar_manager import add_event, update_event
                                        tit_cal = f"[{task.get('tipus')}] {main_title[:35]}..." if len(main_title) > 35 else f"[{task.get('tipus')}] {main_title}"
                                        d_raw = task.get("dataManteniment", "")
                                        iso_d = datetime.today().strftime("%Y-%m-%d")
                                        d_target = datetime.today().date()
                                        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                                            try:
                                                d_target = datetime.strptime(d_raw, fmt).date()
                                                iso_d = d_target.strftime("%Y-%m-%d")
                                                break
                                            except Exception:
                                                pass
                                        cal_desc = f"Tasca #{task_id}\nFeina: {task_feina}\nTipus: {task.get('tipus')}\nAlerta a: {alerta_txt}\nAvís amb {dies_av_badge} dies d'antelació"
                                        if task_obs:
                                            cal_desc += f"\n\nObservacions:\n{task_obs}"
                                        al_list = task.get("alertaA", [])
                                        first_m = al_list[0] if isinstance(al_list, list) and al_list else str(al_list)
                                        if first_m == "Tothom":
                                            first_m = "Tota la família"

                                        cal_payload = {
                                            "title": tit_cal,
                                            "start_date": iso_d,
                                            "date": iso_d,
                                            "start_time": "09:00",
                                            "time": "09:00",
                                            "category": "Llar",
                                            "description": cal_desc,
                                            "member": first_m,
                                            "assigned_to": alerta_txt,
                                            "notify": True
                                        }

                                        if task.get("calendar_event_id"):
                                            update_event(task.get("calendar_event_id"), cal_payload)
                                        else:
                                            ev = add_event(cal_payload)
                                            if ev and isinstance(ev, dict) and "id" in ev:
                                                update_manteniment_task(task_id, {"calendar_event_id": ev["id"]})

                                        # Obrir directament l'Agenda situant el mes i el dia exacte de la tasca
                                        st.session_state["cal_year"] = d_target.year
                                        st.session_state["cal_month"] = d_target.month
                                        st.session_state["selected_day_for_new"] = d_target
                                        st.session_state["current_module"] = "modules.calendari"
                                        st.rerun()
                                    except Exception as e_cal:
                                        st.error(f"Error: {e_cal}")
                            with c_btn4:
                                if st.button("🗑️ Esborrar", key=f"btn_del_task_{task_id}", use_container_width=True):
                                    delete_task_dialog(task_id, main_title)

    # =========================================================================
    # PESTANYA 2: MANUALS
    # =========================================================================
    with tab_manuals:
        # Barra superior d'accions i mètriques
        col_m1, col_m2, col_m_btns = st.columns([2, 2, 3], vertical_alignment="center")
        with col_m1:
            st.metric("📚 Total Manuals", len(manuals))
        with col_m2:
            locations_count = len(set(d.get("ubicacio", "General") for d in manuals if d.get("ubicacio")))
            st.metric("🏠 Ubicacions", locations_count)
        with col_m_btns:
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("➕ Nou Manual", type="primary", use_container_width=True, key="btn_add_manual"):
                    add_manual_dialog()
            with btn_col2:
                if st.button("🔄 Sincronitzar", use_container_width=True, help="Detecta fitxers PDF afegits directament a la carpeta PDF/Manuals", key="btn_sync_manuals"):
                    with st.spinner("Sincronitzant carpeta PDF/Manuals..."):
                        n_man, n_gar = sync_pdf_directory()
                        if n_man > 0:
                            st.success(f"S'han detectat {n_man} nous manuals a la carpeta!")
                        else:
                            st.info("La carpeta PDF/Manuals ja està al dia.")
                    st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Filtres i Cercador
        col_cerca, col_filtre_loc = st.columns([3, 1.5])
        with col_cerca:
            cerca_manual = st.text_input("🔍 Cercar per títol, dispositiu, marca o paraula clau...", placeholder="Ex: termòstat, horari, calder...", key="search_manuals")
        with col_filtre_loc:
            all_locs = sorted(list(set(d.get("ubicacio", "General") for d in manuals if d.get("ubicacio"))))
            filtre_loc = st.selectbox("📍 Filtrar per ubicació", ["Totes"] + all_locs, key="filter_manual_loc")

        # Aplicar filtres
        filtered_manuals = manuals
        if cerca_manual.strip():
            query = cerca_manual.strip().lower()
            filtered_manuals = [
                m for m in filtered_manuals
                if query in m.get("titol", "").lower()
                or query in m.get("dispositiu", "").lower()
                or query in m.get("marca", "").lower()
                or query in m.get("model", "").lower()
                or query in m.get("descripcio", "").lower()
                or any(query in tag for tag in m.get("etiquetes", []))
                or query in m.get("fitxer", "").lower()
            ]
        if filtre_loc != "Totes":
            filtered_manuals = [m for m in filtered_manuals if m.get("ubicacio") == filtre_loc]

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        if not filtered_manuals:
            st.info("No s'ha trobat cap manual que coincideixi amb la cerca.")
        else:
            for doc in filtered_manuals:
                fname = doc.get("fitxer", "")
                fpath = get_pdf_path("Manuals", fname)
                file_exists = os.path.exists(fpath)
                file_size_kb = (os.path.getsize(fpath) / 1024) if file_exists else 0
                pages = doc.get("pagines", 0)

                with st.container(border=True):
                    c_info, c_actions = st.columns([7, 3], vertical_alignment="center")
                    with c_info:
                        # Títol i subtítol
                        brand_model = f" • {doc.get('marca')}" if doc.get('marca') and doc.get('marca') != 'General' else ""
                        if doc.get('model'):
                            brand_model += f" ({doc.get('model')})"
                        st.markdown(f"<div style='font-size:1.15rem; font-weight:700; color:#38bdf8;'>📖 {doc.get('titol')}<span style='font-size:0.9rem; font-weight:400; color:#94a3b8;'>{brand_model}</span></div>", unsafe_allow_html=True)
                        
                        # Badges
                        loc_badge = f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #475569; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>📍 {doc.get('ubicacio', 'General')}</span>"
                        sub_badge = f"<span style='background:#0f172a; color:#38bdf8; border:1px solid #0284c7; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>⚙️ {doc.get('subcategoria', 'General')}</span>"
                        pages_badge = f"<span style='background:#1e293b; color:#94a3b8; border:1px solid #334155; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>📄 {pages} pàg.</span>" if pages > 0 else ""
                        size_badge = f"<span style='background:#1e293b; color:#94a3b8; border:1px solid #334155; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>💾 {file_size_kb:.1f} KB</span>" if file_exists else "<span style='background:#7f1d1d; color:#fca5a5; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>⚠️ Fitxer no trobat al disc</span>"
                        
                        st.markdown(f"<div style='margin: 6px 0 8px 0; display:flex; gap:6px; flex-wrap:wrap;'>{loc_badge} {sub_badge} {pages_badge} {size_badge}</div>", unsafe_allow_html=True)
                        
                        # Descripció
                        if doc.get("descripcio"):
                            st.markdown(f"<div style='color:#e2e8f0; font-size:0.9rem; margin-bottom:6px;'>{doc.get('descripcio')}</div>", unsafe_allow_html=True)
                            
                        # Etiquetes i fitxer
                        tags_html = " ".join([f"<span style='color:#64748b; font-size:0.75rem;'>#{t}</span>" for t in doc.get("etiquetes", [])])
                        st.markdown(f"<div style='font-size:0.8rem; color:#64748b;'>📁 <code>PDF/Manuals/{fname}</code> {tags_html}</div>", unsafe_allow_html=True)

                    with c_actions:
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            if file_exists:
                                if st.button("👁️ Veure", use_container_width=True, key=f"view_man_{doc.get('id')}", help="Visualitzar el PDF complet a l'aplicació"):
                                    view_pdf_dialog(doc.get("titol", "Manual"), "Manuals", fname)
                            else:
                                st.button("👁️ Veure", disabled=True, use_container_width=True, key=f"view_man_dis_{doc.get('id')}")
                        with col_a2:
                            if file_exists:
                                with open(fpath, "rb") as f_bytes:
                                    st.download_button(
                                        label="📥 Baixar",
                                        data=f_bytes.read(),
                                        file_name=fname,
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key=f"dl_man_{doc.get('id')}"
                                    )
                            else:
                                st.button("📥 Baixar", disabled=True, use_container_width=True, key=f"dl_man_dis_{doc.get('id')}")

                        col_a3, col_a4 = st.columns(2)
                        with col_a3:
                            if st.button("✏️ Editar", use_container_width=True, key=f"edit_man_{doc.get('id')}"):
                                edit_manual_dialog(doc)
                        with col_a4:
                            if st.button("🗑️ Esborrar", use_container_width=True, key=f"del_man_{doc.get('id')}"):
                                delete_document_dialog("Manuals", doc.get("id"), doc.get("titol", "Manual"), fname)

    # =========================================================================
    # PESTANYA 2: GARANTIES
    # =========================================================================
    with tab_garanties:
        # Calcular estats de garanties per a les mètriques
        vigents_count = 0
        aviso_count = 0
        caducades_count = 0
        for g in garanties:
            status = calculate_warranty_status(g)
            if status["estat"] == "vigente":
                vigents_count += 1
            elif status["estat"] == "aviso":
                aviso_count += 1
            elif status["estat"] == "caducada":
                caducades_count += 1

        # Barra superior d'accions i mètriques
        col_g1, col_g2, col_g3, col_g4, col_g_btns = st.columns([1.3, 1.3, 1.4, 1.3, 2.5], vertical_alignment="center")
        with col_g1:
            st.metric("🛡️ Total Garanties", len(garanties))
        with col_g2:
            st.metric("🟢 Vigents", vigents_count)
        with col_g3:
            st.metric("⚠️ A punt de vèncer", aviso_count)
        with col_g4:
            st.metric("🔴 Caducades", caducades_count)
        with col_g_btns:
            btn_g_col1, btn_g_col2 = st.columns(2)
            with btn_g_col1:
                if st.button("➕ Nova Garantia", type="primary", use_container_width=True, key="btn_add_garantia"):
                    add_garantia_dialog()
            with btn_g_col2:
                if st.button("🔄 Sincronitzar", use_container_width=True, help="Detecta fitxers PDF afegits directament a la carpeta PDF/Garanties", key="btn_sync_garanties"):
                    with st.spinner("Sincronitzant carpeta PDF/Garanties..."):
                        n_man, n_gar = sync_pdf_directory()
                        if n_gar > 0:
                            st.success(f"S'han detectat {n_gar} noves garanties a la carpeta!")
                        else:
                            st.info("La carpeta PDF/Garanties ja està al dia.")
                    st.rerun()

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Filtres i Cercador
        col_cerca_g, col_filtre_estat, col_filtre_botiga = st.columns([2.5, 1.3, 1.2])
        with col_cerca_g:
            cerca_garantia = st.text_input("🔍 Cercar garantia per article, establiment o factura...", placeholder="Ex: Rentadora, MediaMarkt, Bosch...", key="search_garanties")
        with col_filtre_estat:
            filtre_estat = st.selectbox("Estat de cobertura", ["Totes", "🟢 Vigents", "⚠️ A punt de vèncer", "🔴 Caducades"], key="filter_gar_estat")
        with col_filtre_botiga:
            all_botigues = sorted(list(set(d.get("establiment", "") for d in garanties if d.get("establiment"))))
            filtre_botiga = st.selectbox("Establiment", ["Tots"] + all_botigues, key="filter_gar_botiga")

        # Aplicar filtres
        filtered_garanties = garanties
        if cerca_garantia.strip():
            query_g = cerca_garantia.strip().lower()
            filtered_garanties = [
                g for g in filtered_garanties
                if query_g in g.get("titol", "").lower()
                or query_g in g.get("dispositiu", "").lower()
                or query_g in g.get("establiment", "").lower()
                or query_g in g.get("marca", "").lower()
                or query_g in g.get("model", "").lower()
                or query_g in g.get("num_factura", "").lower()
                or query_g in g.get("descripcio", "").lower()
                or any(query_g in tag for tag in g.get("etiquetes", []))
                or query_g in g.get("fitxer", "").lower()
            ]
        if filtre_estat == "🟢 Vigents":
            filtered_garanties = [g for g in filtered_garanties if calculate_warranty_status(g)["estat"] == "vigente"]
        elif filtre_estat == "⚠️ A punt de vèncer":
            filtered_garanties = [g for g in filtered_garanties if calculate_warranty_status(g)["estat"] == "aviso"]
        elif filtre_estat == "🔴 Caducades":
            filtered_garanties = [g for g in filtered_garanties if calculate_warranty_status(g)["estat"] == "caducada"]

        if filtre_botiga != "Tots":
            filtered_garanties = [g for g in filtered_garanties if g.get("establiment") == filtre_botiga]

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        if not filtered_garanties:
            if not garanties:
                st.info("Encara no hi ha cap document de garantia registrat. Pots afegir-ne una amb el botó '➕ Nova Garantia' o dipositar arxius PDF a la carpeta `PDF/Garanties` i prémer '🔄 Sincronitzar'.")
            else:
                st.info("No s'ha trobat cap garantia que compleixi els filtres seleccionats.")
        else:
            for doc in filtered_garanties:
                fname = doc.get("fitxer", "")
                fpath = get_pdf_path("Garanties", fname)
                file_exists = os.path.exists(fpath)
                file_size_kb = (os.path.getsize(fpath) / 1024) if file_exists else 0
                status = calculate_warranty_status(doc)

                with st.container(border=True):
                    c_info, c_actions = st.columns([7, 3], vertical_alignment="center")
                    with c_info:
                        # Títol i establiment
                        botiga_txt = f" • {doc.get('establiment')}" if doc.get('establiment') else ""
                        st.markdown(f"<div style='font-size:1.15rem; font-weight:700; color:#10b981;'>🛡️ {doc.get('titol')}<span style='font-size:0.9rem; font-weight:400; color:#94a3b8;'>{botiga_txt}</span></div>", unsafe_allow_html=True)

                        # Badges d'estat i característiques
                        status_badge = f"<span style='background:{status['color']}22; color:{status['color']}; border:1px solid {status['color']}; padding:3px 10px; border-radius:12px; font-weight:700; font-size:0.75rem;'>{status['text']}</span>"
                        
                        compra_badge = f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #475569; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>📅 Compra: {doc.get('data_compra', 'Sense data')}</span>"
                        anys_badge = f"<span style='background:#1e293b; color:#cbd5e1; border:1px solid #475569; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>⏳ Cobertura: {doc.get('anys_garantia', 3)} anys</span>"
                        
                        preu_val = float(doc.get("import_compra", 0.0))
                        preu_badge = f"<span style='background:#0f172a; color:#fbbf24; border:1px solid #d97706; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>💶 {preu_val:.2f} €</span>" if preu_val > 0 else ""
                        factura_badge = f"<span style='background:#1e293b; color:#94a3b8; border:1px solid #334155; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🧾 Factura: {doc.get('num_factura')}</span>" if doc.get("num_factura") else ""
                        size_badge = f"<span style='background:#1e293b; color:#94a3b8; border:1px solid #334155; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>💾 {file_size_kb:.1f} KB</span>" if file_exists else "<span style='background:#7f1d1d; color:#fca5a5; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>⚠️ Fitxer no trobat al disc</span>"

                        st.markdown(f"<div style='margin: 6px 0 8px 0; display:flex; gap:6px; flex-wrap:wrap; align-items:center;'>{status_badge} {compra_badge} {anys_badge} {preu_badge} {factura_badge} {size_badge}</div>", unsafe_allow_html=True)

                        # Descripció
                        if doc.get("descripcio"):
                            st.markdown(f"<div style='color:#e2e8f0; font-size:0.9rem; margin-bottom:6px;'>{doc.get('descripcio')}</div>", unsafe_allow_html=True)

                        # Etiquetes i fitxer
                        tags_html = " ".join([f"<span style='color:#64748b; font-size:0.75rem;'>#{t}</span>" for t in doc.get("etiquetes", [])])
                        st.markdown(f"<div style='font-size:0.8rem; color:#64748b;'>📁 <code>PDF/Garanties/{fname}</code> {tags_html}</div>", unsafe_allow_html=True)

                    with c_actions:
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            if file_exists:
                                if st.button("👁️ Veure", use_container_width=True, key=f"view_gar_{doc.get('id')}", help="Visualitzar el PDF complet a l'aplicació"):
                                    view_pdf_dialog(doc.get("titol", "Garantia"), "Garanties", fname)
                            else:
                                st.button("👁️ Veure", disabled=True, use_container_width=True, key=f"view_gar_dis_{doc.get('id')}")
                        with col_a2:
                            if file_exists:
                                with open(fpath, "rb") as f_bytes:
                                    st.download_button(
                                        label="📥 Baixar",
                                        data=f_bytes.read(),
                                        file_name=fname,
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key=f"dl_gar_{doc.get('id')}"
                                    )
                            else:
                                st.button("📥 Baixar", disabled=True, use_container_width=True, key=f"dl_gar_dis_{doc.get('id')}")

                        col_a3, col_a4 = st.columns(2)
                        with col_a3:
                            if st.button("✏️ Editar", use_container_width=True, key=f"edit_gar_{doc.get('id')}"):
                                edit_garantia_dialog(doc)
                        with col_a4:
                            if st.button("🗑️ Esborrar", use_container_width=True, key=f"del_gar_{doc.get('id')}"):
                                delete_document_dialog("Garanties", doc.get("id"), doc.get("titol", "Garantia"), fname)
