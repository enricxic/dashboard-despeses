import streamlit as st
import os
import base64
from datetime import datetime, date
from modules.avatar_widget import render_header_with_avatar
from core.manteniment_manager import (
    load_manteniment_docs,
    save_manteniment_docs,
    sync_pdf_directory,
    get_pdf_path,
    get_pdf_dir,
    calculate_warranty_status,
    get_page_count
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
            data_compra = st.date_input("Data de compra *", value=datetime.today().date(), max_value=datetime.today().date())
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
            data_compra = st.date_input("Data de compra", value=compra_date_val, max_value=datetime.today().date())
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

    tabs_list = ["📖 Manuals", "🛡️ Garanties"]
    tab_mapping = {
        "manuals": "📖 Manuals",
        "manual": "📖 Manuals",
        "garanties": "🛡️ Garanties",
        "garantia": "🛡️ Garanties"
    }
    tab_param = st.query_params.get("tab")
    default_tab = tab_mapping.get(tab_param)
    if default_tab not in tabs_list:
        default_tab = None

    tab_manuals, tab_garanties = st.tabs(tabs_list, default=default_tab, key=f"tabs_manteniment_{tab_param or 'main'}")

    # =========================================================================
    # PESTANYA 1: MANUALS
    # =========================================================================
    with tab_manuals:
        # Barra superior d'accions i mètriques
        col_m1, col_m2, col_m3, col_m_btns = st.columns([1.5, 1.5, 2, 2.5], vertical_alignment="center")
        with col_m1:
            st.metric("📚 Total Manuals", len(manuals))
        with col_m2:
            locations_count = len(set(d.get("ubicacio", "General") for d in manuals if d.get("ubicacio")))
            st.metric("🏠 Ubicacions", locations_count)
        with col_m3:
            latest_man = manuals[-1]["titol"] if manuals else "Cap"
            st.metric("🆕 Últim afegit", latest_man if len(latest_man) <= 22 else latest_man[:20] + "...")
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
