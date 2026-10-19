import streamlit as st
import os
import base64
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
    update_manteniment_task,
    delete_manteniment_task,
    toggle_manteniment_acompliment
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
    st.markdown(f"<h3 style='margin-top:0; color:#f39c12;'>✏️ Editar: {doc.get('titol')}</h3>", unsafe_allow_html=True)
    
    with st.form("form_edit_manual"):
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
        
        submitted = st.form_submit_button("💾 Desar canvis", use_container_width=True)
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
    st.markdown(f"<h3 style='margin-top:0; color:#10b981;'>✏️ Editar: {doc.get('titol')}</h3>", unsafe_allow_html=True)
    
    with st.form("form_edit_garantia"):
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
        
        submitted = st.form_submit_button("💾 Desar canvis", use_container_width=True)
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

@st.dialog("✏️ Editar Tasca de Manteniment", width="large")
def edit_task_dialog(task: dict, family_names: list):
    """Diàleg modal per editar una tasca de manteniment existent."""
    task_id = task.get("idManteniment", "")
    st.markdown(f"<h3 style='margin-top:0; color:#f39c12;'>✏️ Editar Tasca #{task_id}</h3>", unsafe_allow_html=True)
    
    with st.form(f"form_edit_task_{task_id}"):
        c1, c2, c3 = st.columns(3)
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
            tipus_opts = ["Reparació", "Manteniment", "Feina casa", "Revisió periòdica", "Instal·lació / Millora", "Neteja a fons", "Altres"]
            cur_tip = task.get("tipus", "Manteniment")
            tip_idx = tipus_opts.index(cur_tip) if cur_tip in tipus_opts else 1
            tipus = st.selectbox("Tipus *", tipus_opts, index=tip_idx)
        with c3:
            cur_alerta = task.get("alertaA", "Tothom")
            al_idx = family_names.index(cur_alerta) if cur_alerta in family_names else 0
            alertaA = st.selectbox("Alerta a *", family_names, index=al_idx)
            
        feina = st.text_input("Feina concreta a realitzar *", value=task.get("feina", ""), placeholder="Ex: Purgar radiadors, canviar bombeta, netejar filtres...")
            
        c4, c5 = st.columns([1, 2], vertical_alignment="center")
        with c4:
            cur_acomp = str(task.get("acompliment", "No")).strip().lower()
            ac_idx = 1 if cur_acomp in ["sí", "si", "true"] else 0
            acompliment = st.selectbox("Acompliment", ["No", "Sí"], index=ac_idx)
        with c5:
            sync_cal = st.checkbox("Actualitzar / Enviar a l'Agenda (Calendari)", value=bool(task.get("calendar_event_id")))

        observacions = st.text_area("Observacions / Detalls addicionals", value=task.get("observacions", ""), height=75)
        
        submitted = st.form_submit_button("💾 Desar canvis", type="primary", use_container_width=True)
        if submitted:
            if not feina.strip():
                st.error("Cal indicar la feina concreta a realitzar.")
                return
            d_str = d_manteniment.strftime("%d/%m/%Y")
            upd = {
                "dataManteniment": d_str,
                "feina": feina.strip(),
                "tipus": tipus,
                "alertaA": alertaA,
                "acompliment": acompliment,
                "observacions": observacions.strip()
            }
            if sync_cal:
                try:
                    from core.calendar_manager import add_event, update_event
                    ev_id = task.get("calendar_event_id")
                    desc_curta = feina.strip() if feina.strip() else observacions.strip()
                    tit = f"[{tipus}] {desc_curta[:35]}..." if len(desc_curta) > 35 else f"[{tipus}] {desc_curta}"
                    iso_date = d_manteniment.strftime("%Y-%m-%d")
                    cal_desc = f"Tasca de Manteniment #{task_id}\nFeina: {feina.strip()}\nTipus: {tipus}\nAlerta a: {alertaA}"
                    if observacions.strip():
                        cal_desc += f"\n\nObservacions:\n{observacions.strip()}"
                    if ev_id:
                        update_event(ev_id, {
                            "title": tit,
                            "date": iso_date,
                            "time": "09:00",
                            "category": "Llar",
                            "description": cal_desc,
                            "assigned_to": alertaA,
                            "notify": True
                        })
                    else:
                        ev = add_event({
                            "title": tit,
                            "date": iso_date,
                            "time": "09:00",
                            "category": "Llar",
                            "description": cal_desc,
                            "assigned_to": alertaA,
                            "notify": True
                        })
                        if ev and isinstance(ev, dict) and "id" in ev:
                            upd["calendar_event_id"] = ev["id"]
                except Exception as e_cal:
                    print("Error actualitzant esdeveniment a calendari:", e_cal)

            update_manteniment_task(task_id, upd)
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
        # 1. FORMULARI D'ENTRADA
        with st.container(border=True):
            st.markdown("<h4 style='color:#f39c12; margin-top:0; margin-bottom:12px;'>➕ Nova Tasca de Manteniment</h4>", unsafe_allow_html=True)
            with st.form("form_alta_tasca_manteniment", clear_on_submit=True):
                c_f1, c_f2, c_f3, c_f4 = st.columns([1.5, 1.5, 1.5, 1])
                with c_f1:
                    data_manteniment_input = st.date_input(
                        "Data Prevista *",
                        value=datetime.today().date(),
                        format="DD/MM/YYYY",
                        help="Data en què s'ha de dur a terme la tasca de manteniment"
                    )
                with c_f2:
                    tipus_input = st.selectbox(
                        "Tipus *",
                        ["Reparació", "Manteniment", "Feina casa", "Revisió periòdica", "Instal·lació / Millora", "Neteja a fons", "Altres"],
                        index=1
                    )
                with c_f3:
                    alerta_input = st.selectbox(
                        "Alerta a *",
                        family_names,
                        index=0,
                        help="Persona o grup a qui li apareixerà com a avís a la campaneta"
                    )
                with c_f4:
                    acompliment_input = st.selectbox(
                        "Acompliment",
                        ["No", "Sí"],
                        index=0
                    )
                
                feina_input = st.text_input(
                    "Feina concreta a realitzar *",
                    placeholder="Ex: Canviar filtre campana extractora, purgar radiadors, revisar pressió caldera...",
                    help="Indica la feina o actuació concreta que cal dur a terme"
                )

                observacions_input = st.text_area(
                    "Observacions / Detalls addicionals",
                    placeholder="Instruccions addicionals, eines necessàries, telèfon de contacte, passos...",
                    height=75
                )

                c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="center")
                with c_sub1:
                    send_cal_input = st.checkbox("📅 Enviar directament a l'Agenda (Calendari familiar)", value=True)
                with c_sub2:
                    sub_btn = st.form_submit_button("💾 Desar Tasca al Registre", type="primary", use_container_width=True)

                if sub_btn:
                    if not feina_input.strip():
                        st.error("Cal indicar la feina concreta a realitzar.")
                    else:
                        d_prev_str = data_manteniment_input.strftime("%d/%m/%Y")
                        nova_tasca = {
                            "dataAlta": datetime.now().strftime("%d/%m/%Y"),
                            "dataManteniment": d_prev_str,
                            "feina": feina_input.strip(),
                            "tipus": tipus_input,
                            "alertaA": alerta_input,
                            "acompliment": acompliment_input,
                            "observacions": observacions_input.strip()
                        }
                        res = add_manteniment_task(nova_tasca, send_to_calendar=send_cal_input)
                        st.success(f"Tasca #{res.get('idManteniment')} registrada correctament!")
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
            cerca_text = st.text_input("🔍 Cercar per observació o tipus...", placeholder="Ex: caldera, radiadors, filtre...", key="search_reg_manteniment")
        with col_c2:
            filtre_estat = st.selectbox("Estat", ["Tots", "⏳ Pendents", "✅ Acomplertes", "⚠️ Vençudes"], key="filtre_estat_mant")
        with col_c3:
            all_tipus = ["Tots"] + sorted(list(set(t.get("tipus", "") for t in tasks if t.get("tipus"))))
            filtre_tipus = st.selectbox("Tipus", all_tipus, key="filtre_tipus_mant")
        with col_c4:
            all_alerta = ["Tothom"] + sorted(list(set(t.get("alertaA", "") for t in tasks if t.get("alertaA") and t.get("alertaA") != "Tothom")))
            filtre_persona = st.selectbox("Persona", all_alerta, key="filtre_persona_mant")

        # Filtrar tasques
        filtered_tasks = tasks
        if cerca_text.strip():
            q = cerca_text.strip().lower()
            filtered_tasks = [t for t in filtered_tasks if q in str(t.get("feina", "")).lower() or q in str(t.get("observacions", "")).lower() or q in str(t.get("tipus", "")).lower() or q in str(t.get("alertaA", "")).lower()]
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
            filtered_tasks = [t for t in filtered_tasks if t.get("alertaA") == filtre_persona]

        # Selector de format de visualització
        c_mode1, c_mode2 = st.columns([3, 1], vertical_alignment="center")
        with c_mode1:
            view_mode = st.radio("Format de visualització", ["📇 Targetes interactives", "📊 Taula de dades (Dataframe / CSV)"], horizontal=True, key="view_mode_mant")
        with c_mode2:
            if filtered_tasks:
                df_export = pd.DataFrame(filtered_tasks)
                cols_order = ["idManteniment", "dataAlta", "dataManteniment", "feina", "tipus", "alertaA", "acompliment", "observacions"]
                for c in cols_order:
                    if c not in df_export.columns: df_export[c] = ""
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
                cols_order = ["idManteniment", "dataAlta", "dataManteniment", "feina", "tipus", "alertaA", "acompliment", "observacions"]
                for c in cols_order:
                    if c not in df_display.columns: df_display[c] = ""
                df_display = df_display[cols_order]
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "idManteniment": st.column_config.NumberColumn("ID", width="small"),
                        "dataAlta": st.column_config.TextColumn("Data Alta", width="small"),
                        "dataManteniment": st.column_config.TextColumn("Data Prevista", width="small"),
                        "feina": st.column_config.TextColumn("Feina Concreta", width="medium"),
                        "tipus": st.column_config.TextColumn("Tipus", width="small"),
                        "alertaA": st.column_config.TextColumn("Alerta a", width="small"),
                        "acompliment": st.column_config.TextColumn("Acomplert", width="small"),
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

                    with st.container(border=True):
                        c_card_left, c_card_right = st.columns([7.5, 2.5], vertical_alignment="center")
                        with c_card_left:
                            st.markdown(f"""
                            <div style='display:flex; gap:8px; align-items:center; margin-bottom:6px; flex-wrap:wrap;'>
                                <span style='background:#0f172a; color:#f8fafc; border:1px solid #334155; padding:2px 8px; border-radius:8px; font-weight:700; font-size:0.8rem;'>#{task_id}</span>
                                {status_html}
                                <span style='background:#1e293b; color:#cbd5e1; border:1px solid #475569; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>🏷️ {task.get('tipus', 'Manteniment')}</span>
                                <span style='background:#1e293b; color:#f59e0b; border:1px solid #d97706; padding:2px 8px; border-radius:10px; font-size:0.75rem;'>👤 Alerta: {task.get('alertaA', 'Tothom')}</span>
                                <span style='color:#64748b; font-size:0.75rem; margin-left:auto;'>Alta: {task.get('dataAlta', '')}</span>
                            </div>
                            <div style='font-size:1.05rem; font-weight:700; color:#f8fafc; margin-top:4px;'>
                                🔨 {main_title}
                            </div>
                            {f"<div style='font-size:0.9rem; color:#94a3b8; margin-top:3px;'>📝 {task_obs}</div>" if (task_feina and task_obs) else ""}
                            """, unsafe_allow_html=True)
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
                                if st.button("📅 Agenda", key=f"btn_cal_task_{task_id}", use_container_width=True, help="Enviar o actualitzar a l'agenda"):
                                    try:
                                        from core.calendar_manager import add_event
                                        tit_cal = f"[{task.get('tipus')}] {main_title[:35]}..." if len(main_title) > 35 else f"[{task.get('tipus')}] {main_title}"
                                        d_raw = task.get("dataManteniment", "")
                                        iso_d = datetime.today().strftime("%Y-%m-%d")
                                        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                                            try:
                                                iso_d = datetime.strptime(d_raw, fmt).strftime("%Y-%m-%d")
                                                break
                                            except Exception:
                                                pass
                                        cal_desc = f"Tasca #{task_id}\nFeina: {task_feina}\nTipus: {task.get('tipus')}\nAlerta a: {task.get('alertaA')}"
                                        if task_obs:
                                            cal_desc += f"\n\nObservacions:\n{task_obs}"
                                        ev = add_event({
                                            "title": tit_cal,
                                            "date": iso_d,
                                            "time": "09:00",
                                            "category": "Llar",
                                            "description": cal_desc,
                                            "assigned_to": task.get("alertaA", "Tothom"),
                                            "notify": True
                                        })
                                        if ev and isinstance(ev, dict) and "id" in ev:
                                            update_manteniment_task(task_id, {"calendar_event_id": ev["id"]})
                                        st.success("Enviat a l'Agenda correctament!")
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
