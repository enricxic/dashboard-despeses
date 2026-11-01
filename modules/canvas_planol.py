"""
modules/canvas_planol.py
Component visual de Plànol Interactiu i Galeria Fotogràfica d'Obra.
Totalment adaptat a mòbils (suport tàctil mitjançant Pointer Events, touch-action: none,
diàlegs emergents interns sense window.prompt() que està blocat en iframes mòbils, i botó Desfer).
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import os
from typing import Dict, Any
from core.projectes_manager import (
    save_planol_projecte,
    add_projecte_foto,
    delete_projecte_foto,
    format_date_cat
)

def get_canvas_html(project_id: str, existing_bg_b64: str = "") -> str:
    """Genera el codi HTML+JS complet per a l'editor de plànol amb suport tàctil mòbil i modal intern."""
    return f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
  * {{
    box-sizing: border-box;
    touch-action: manipulation;
  }}
  body {{
    margin: 0;
    padding: 8px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background-color: #f8fafc;
    color: #1e293b;
    user-select: none;
    -webkit-user-select: none;
  }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    background: #ffffff;
    padding: 8px 10px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    margin-bottom: 8px;
  }}
  .btn {{
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    touch-action: auto;
    transition: all 0.15s ease;
  }}
  .btn:active {{
    transform: scale(0.96);
  }}
  .btn.active {{
    background: #2563eb;
    color: white;
    border-color: #1d4ed8;
  }}
  .btn-success {{
    background: #16a34a;
    color: white;
    border-color: #15803d;
  }}
  .btn-undo {{
    background: #fffbeb;
    border-color: #fde68a;
    color: #b45309;
  }}
  .canvas-wrapper {{
    position: relative;
    border: 2px solid #cbd5e1;
    border-radius: 10px;
    background: #ffffff;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    overflow: hidden;
    width: 100%;
    margin: 0 auto;
  }}
  #planolCanvas {{
    display: block;
    width: 100%;
    height: auto;
    cursor: crosshair;
    background: #ffffff;
    touch-action: none; /* Bloqueja l'scroll al tocar sobre el canvas per poder dibuixar */
  }}
  .status-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    font-size: 12px;
    color: #475569;
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
    font-weight: 500;
  }}
  /* Modal intern tàctil */
  .modal-overlay {{
    display: none;
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.6);
    z-index: 100;
    justify-content: center;
    align-items: center;
    padding: 15px;
  }}
  .modal-box {{
    background: white;
    padding: 16px;
    border-radius: 12px;
    width: 100%;
    max-width: 320px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    text-align: center;
  }}
  .modal-box h4 {{
    margin: 0 0 10px 0;
    font-size: 15px;
    color: #0f172a;
  }}
  .modal-input {{
    width: 100%;
    padding: 10px;
    font-size: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-bottom: 12px;
    text-align: center;
  }}
  .preset-btns {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: center;
    margin-bottom: 12px;
  }}
  .preset-btn {{
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
  }}
  .modal-actions {{
    display: flex;
    gap: 8px;
  }}
  .modal-actions button {{
    flex: 1;
    padding: 10px;
    font-size: 14px;
    font-weight: 600;
    border-radius: 8px;
    border: none;
    cursor: pointer;
  }}
  .btn-confirm {{
    background: #2563eb;
    color: white;
  }}
  .btn-cancel {{
    background: #e2e8f0;
    color: #334155;
  }}
</style>
</head>
<body>

<div class="toolbar">
  <button class="btn active" id="btnWall" onclick="setTool('wall')">🧱 Paret</button>
  <button class="btn" id="btnRect" onclick="setTool('rect')">🔲 Espai</button>
  <button class="btn" id="btnDim" onclick="setTool('dim')">📏 Cota</button>
  <button class="btn" id="btnText" onclick="setTool('text')">🔤 Text</button>
  <button class="btn" id="btnEraser" onclick="setTool('eraser')">🧹 Goma</button>
  
  <div style="height: 20px; width: 1px; background: #cbd5e1; margin: 0 2px;"></div>
  
  <button class="btn btn-undo" onclick="undo()">↩️ Desfer</button>
  
  <label class="btn" style="cursor: pointer;">
    📷 Foto fons
    <input type="file" id="fileBg" accept="image/*" style="display:none;" onchange="loadBgImage(event)">
  </label>
  
  <span style="font-size: 11px; color: #64748b; margin-left: 2px;">Opacitat:</span>
  <input type="range" id="bgOpacity" min="10" max="100" value="60" style="width: 60px;" oninput="drawAll()">
  
  <button class="btn" style="color:#ef4444;" onclick="clearCanvas()">🗑️</button>
  <button class="btn btn-success" onclick="downloadImage()">💾 Descarregar PNG</button>
</div>

<div class="canvas-wrapper">
  <!-- Resolució nativa nítida 800x520 escalada per CSS a la pantalla del mòbil -->
  <canvas id="planolCanvas" width="800" height="520"></canvas>
  <div class="status-bar">
    <span id="toolStatus">👉 Arrossega el dit per dibuixar una paret recta</span>
    <span>Graella: 20px ≈ 0,5m</span>
  </div>

  <!-- Modal emergent intern per Cotes i Textos (Compatible 100% mòbils) -->
  <div class="modal-overlay" id="customModal">
    <div class="modal-box">
      <h4 id="modalTitle">Indica la mesura de la cota</h4>
      <div class="preset-btns" id="modalPresets"></div>
      <input type="text" class="modal-input" id="modalInput" autofocus>
      <div class="modal-actions">
        <button class="btn-cancel" onclick="closeModal(false)">Cancel·lar</button>
        <button class="btn-confirm" onclick="closeModal(true)">Acceptar</button>
      </div>
    </div>
  </div>
</div>

<script>
const canvas = document.getElementById('planolCanvas');
const ctx = canvas.getContext('2d');
const GRID_SIZE = 20;

let currentTool = 'wall';
let isDrawing = false;
let startX = 0, startY = 0;
let elements = [];
let history = [];
let bgImage = null;
let bgOpacityInput = document.getElementById('bgOpacity');
let pendingModalCallback = null;

// Si hi ha imatge de fons preexistent
const preBg = "{existing_bg_b64}";
if (preBg && preBg.length > 50) {{
  const img = new Image();
  img.onload = () => {{
    bgImage = img;
    drawAll();
  }};
  img.src = preBg;
}}

function setTool(tool) {{
  currentTool = tool;
  document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('btn' + tool.charAt(0).toUpperCase() + tool.slice(1));
  if (btn) btn.classList.add('active');
  
  const status = document.getElementById('toolStatus');
  if (tool === 'wall') status.innerText = "👉 Paret: Arrossega el dit/ratolí per traçar una paret recta.";
  else if (tool === 'rect') status.innerText = "👉 Espai: Arrossega en diagonal per crear una habitació o moble.";
  else if (tool === 'dim') status.innerText = "👉 Cota: Arrossega d'un extrem a l'altre per mesurar la distància.";
  else if (tool === 'text') status.innerText = "👉 Text: Toca sobre l'estança per posar-li nom o nota.";
  else if (tool === 'eraser') status.innerText = "👉 Goma: Toca sobre qualsevol línia per esborrar-la.";
}}

function snap(val) {{
  return Math.round(val / GRID_SIZE) * GRID_SIZE;
}}

function getPointerCoords(e) {{
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {{
    x: snap((e.clientX - rect.left) * scaleX),
    y: snap((e.clientY - rect.top) * scaleY),
    rawX: (e.clientX - rect.left) * scaleX,
    rawY: (e.clientY - rect.top) * scaleY
  }};
}}

function saveHistory() {{
  history.push(JSON.stringify(elements));
  if (history.length > 20) history.shift();
}}

function undo() {{
  if (history.length > 0) {{
    elements = JSON.parse(history.pop());
    drawAll();
  }} else if (elements.length > 0) {{
    elements.pop();
    drawAll();
  }}
}}

function drawGrid() {{
  ctx.strokeStyle = '#f1f5f9';
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += GRID_SIZE) {{
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }}
  for (let y = 0; y < canvas.height; y += GRID_SIZE) {{
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }}
}}

function drawAll() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 1. Dibuixar foto de fons si existeix
  if (bgImage) {{
    ctx.save();
    ctx.globalAlpha = parseInt(bgOpacityInput.value) / 100;
    const hRatio = canvas.width / bgImage.width;
    const vRatio = canvas.height / bgImage.height;
    const ratio = Math.min(hRatio, vRatio);
    const centerShiftX = (canvas.width - bgImage.width * ratio) / 2;
    const centerShiftY = (canvas.height - bgImage.height * ratio) / 2;
    ctx.drawImage(bgImage, 0, 0, bgImage.width, bgImage.height,
                  centerShiftX, centerShiftY, bgImage.width * ratio, bgImage.height * ratio);
    ctx.restore();
  }}
  
  // 2. Graella
  drawGrid();
  
  // 3. Elements
  for (const el of elements) {{
    drawElement(el);
  }}
}}

function drawElement(el) {{
  ctx.save();
  if (el.type === 'wall') {{
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 6;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(el.x1, el.y1);
    ctx.lineTo(el.x2, el.y2);
    ctx.stroke();
  }} else if (el.type === 'rect') {{
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 4;
    ctx.fillStyle = 'rgba(241, 245, 249, 0.45)';
    ctx.beginPath();
    ctx.rect(el.x, el.y, el.w, el.h);
    ctx.fill();
    ctx.stroke();
  }} else if (el.type === 'dim') {{
    ctx.strokeStyle = '#2563eb';
    ctx.fillStyle = '#2563eb';
    ctx.lineWidth = 2.5;
    
    // Línia principal
    ctx.beginPath();
    ctx.moveTo(el.x1, el.y1);
    ctx.lineTo(el.x2, el.y2);
    ctx.stroke();
    
    // Fletxes / ticks transversals
    const angle = Math.atan2(el.y2 - el.y1, el.x2 - el.x1);
    const tickLen = 7;
    ctx.beginPath();
    ctx.moveTo(el.x1 - Math.sin(angle)*tickLen, el.y1 + Math.cos(angle)*tickLen);
    ctx.lineTo(el.x1 + Math.sin(angle)*tickLen, el.y1 - Math.cos(angle)*tickLen);
    ctx.moveTo(el.x2 - Math.sin(angle)*tickLen, el.y2 + Math.cos(angle)*tickLen);
    ctx.lineTo(el.x2 + Math.sin(angle)*tickLen, el.y2 - Math.cos(angle)*tickLen);
    ctx.stroke();
    
    // Text de mida
    const midX = (el.x1 + el.x2) / 2;
    const midY = (el.y1 + el.y2) / 2;
    ctx.font = 'bold 13px sans-serif';
    ctx.fillStyle = '#1d4ed8';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(el.text || '', midX, midY - 4);
  }} else if (el.type === 'text') {{
    ctx.font = 'bold 15px sans-serif';
    ctx.fillStyle = '#0f172a';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(el.text, el.x, el.y);
  }}
  ctx.restore();
}}

// GESTIÓ DE MODAL INTERN (Compatible 100% amb mòbils sense alertes blocades)
function showInputModal(title, presets, defaultVal, callback) {{
  const modal = document.getElementById('customModal');
  const titleEl = document.getElementById('modalTitle');
  const inputEl = document.getElementById('modalInput');
  const presetsEl = document.getElementById('modalPresets');
  
  titleEl.innerText = title;
  inputEl.value = defaultVal || '';
  presetsEl.innerHTML = '';
  
  presets.forEach(p => {{
    const b = document.createElement('button');
    b.className = 'preset-btn';
    b.innerText = p;
    b.onclick = () => {{ inputEl.value = p; }};
    presetsEl.appendChild(b);
  }});
  
  pendingModalCallback = callback;
  modal.style.display = 'flex';
  setTimeout(() => inputEl.focus(), 100);
}}

function closeModal(confirm) {{
  const modal = document.getElementById('customModal');
  const inputEl = document.getElementById('modalInput');
  modal.style.display = 'none';
  if (confirm && pendingModalCallback) {{
    pendingModalCallback(inputEl.value.trim());
  }}
  pendingModalCallback = null;
}}

// ESDEVENIMENTS TÀCTILS I RATOLÍ UNIFICATS (Pointer Events)
canvas.addEventListener('pointerdown', (e) => {{
  e.preventDefault();
  const c = getPointerCoords(e);
  
  if (currentTool === 'text') {{
    showInputModal(
      "Etiqueta de l'espai o nota:",
      ["Bany", "Dutxa", "Moble lavabo", "Porta", "Paret mestra", "Finestra"],
      "",
      (val) => {{
        if (val) {{
          saveHistory();
          elements.push({{ type: 'text', x: c.rawX, y: c.rawY, text: val }});
          drawAll();
        }}
      }}
    );
    return;
  }}
  
  if (currentTool === 'eraser') {{
    saveHistory();
    elements = elements.filter(el => {{
      const cx = el.x || (el.x1 + el.x2) / 2 || 0;
      const cy = el.y || (el.y1 + el.y2) / 2 || 0;
      return Math.hypot(cx - c.rawX, cy - c.rawY) > 30;
    }});
    drawAll();
    return;
  }}
  
  isDrawing = true;
  startX = c.x;
  startY = c.y;
  canvas.setPointerCapture(e.pointerId);
}});

canvas.addEventListener('pointermove', (e) => {{
  if (!isDrawing) return;
  e.preventDefault();
  const c = getPointerCoords(e);
  const currX = c.x;
  const currY = c.y;
  
  drawAll();
  
  // Previsualització en curs
  ctx.save();
  ctx.strokeStyle = '#94a3b8';
  ctx.setLineDash([4, 4]);
  if (currentTool === 'wall') {{
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(currX, currY);
    ctx.stroke();
  }} else if (currentTool === 'rect') {{
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, currX - startX, currY - startY);
  }} else if (currentTool === 'dim') {{
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(currX, currY);
    ctx.stroke();
  }}
  ctx.restore();
}});

canvas.addEventListener('pointerup', (e) => {{
  if (!isDrawing) return;
  e.preventDefault();
  isDrawing = false;
  try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
  
  const c = getPointerCoords(e);
  const endX = c.x;
  const endY = c.y;
  
  if (startX === endX && startY === endY) return;
  
  saveHistory();
  
  if (currentTool === 'wall') {{
    elements.push({{ type: 'wall', x1: startX, y1: startY, x2: endX, y2: endY }});
    drawAll();
  }} else if (currentTool === 'rect') {{
    elements.push({{
      type: 'rect',
      x: Math.min(startX, endX),
      y: Math.min(startY, endY),
      w: Math.abs(endX - startX),
      h: Math.abs(endY - startY)
    }});
    drawAll();
  }} else if (currentTool === 'dim') {{
    // Càlcul orientatiu: 40px ≈ 1m
    const pxDist = Math.hypot(endX - startX, endY - startY);
    const mDist = (pxDist / 40).toFixed(2);
    
    showInputModal(
      "Indica la mesura de la cota:",
      [mDist + " m", "1,00 m", "1,20 m", "1,50 m", "2,00 m", "2,40 m"],
      mDist + " m",
      (userM) => {{
        elements.push({{
          type: 'dim',
          x1: startX,
          y1: startY,
          x2: endX,
          y2: endY,
          text: userM || (mDist + " m")
        }});
        drawAll();
      }}
    );
  }}
}});

canvas.addEventListener('pointercancel', (e) => {{
  isDrawing = false;
  drawAll();
}});

function loadBgImage(e) {{
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (event) => {{
    const img = new Image();
    img.onload = () => {{
      bgImage = img;
      drawAll();
    }};
    img.src = event.target.result;
  }};
  reader.readAsDataURL(file);
}}

function clearCanvas() {{
  if (confirm("Vols buidar tot el plànol dibuixat?")) {{
    saveHistory();
    elements = [];
    drawAll();
  }}
}}

function downloadImage() {{
  const dataURL = canvas.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = dataURL;
  a.download = 'planol_{project_id}.png';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}}

// Inicialització
drawAll();
</script>

</body>
</html>"""

def render_planol_tab(projecte: Dict[str, Any]):
    """Renderitza la subpestanya de Plànol i Galeria de Fotos del projecte."""
    project_id = projecte.get("id", "nou")
    planol_info = projecte.get("planol", {})
    preview_png = planol_info.get("preview_png")
    bg_b64 = planol_info.get("background_image", "")

    st.markdown("### 📐 Plànol i Croquis de l'Obra")
    st.caption("Dibuixa parets, habitacions i cotes amb mides en metres, o carrega una foto real de l'estança per utilitzar-la com a fons.")

    # Guia d'ús desplegable integrada al projecte
    with st.expander("📖 Guia d'Ús: Com funciona l'editor de plànols?", expanded=False):
        st.markdown("""
        #### 📱 Com funciona l'editor de plànols pas a pas

        1. **🧱 Paret / Línia:**
           - Toca el botó **`🧱 Paret`**.
           - Posa el dit (o ratolí) sobre la quadreta i **arrossega** fins on acabi la paret. En aixecar el dit, es traçarà la línia negra.

        2. **🔲 Espai / Habitació:**
           - Toca el botó **`🔲 Espai`**.
           - **Arrossega en diagonal** per crear una habitació, envà o moble rectangular.

        3. **📏 Cota (mesures en metres):**
           - Toca el botó **`📏 Cota`**.
           - **Arrossega d'un extrem a l'altre** del tram que vulguis mesurar.
           - S'obrirà un selector emergent: tria una mesura ràpida (*1,00 m, 1,50 m, 2,00 m...*) o escriu la teva mida exacta (ex: *2,40 m*).

        4. **🔤 Text:**
           - Toca el botó **`🔤 Text`** i després toca sobre l'espai del plànol.
           - Tria una etiqueta ràpida (*Bany, Dutxa, Moble lavabo, Porta, Finestra*) o escriu el text lliure que vulguis.

        5. **🧹 Goma d'esborrar i ↩️ Desfer:**
           - Toca **`🧹 Goma`** i després toca sobre qualsevol línia o element per eliminar-lo.
           - Si t'has equivocat en l'últim traç, prem directament **`↩️ Desfer`**.

        6. **📷 Foto de fons:**
           - Prem **`📷 Foto fons`** per carregar una foto de l'estança real o d'un esbós en paper.
           - Mou la barra d'**Opacitat** per poder calcar i afegir cotes/parets exactament per sobre.

        7. **💾 Desar al Projecte:**
           - Un cop tinguis el plànol fet, prem el botó verd **`💾 Descarregar PNG`**.
           - Tot seguit, al formulari inferior **'Desar o Actualitzar Plànol'**, carrega aquesta imatge i prem **`Guardar Plànol Oficial`** perquè quedi gravat permanentment a la fitxa del projecte.
        """)

    # Vista prèvia actual si existeix
    if preview_png:
        st.markdown("**Plànol oficial desat per a aquest projecte:**")
        st.image(preview_png, use_container_width=True)
        data_act = planol_info.get("data_actualitzacio", "")
        if data_act:
            st.caption(f"Darrera actualització del plànol: {data_act}")

    # Editor interactiu Canvas
    with st.expander("✏️ Obrir Editor Gràfic de Plànol (Canvas)", expanded=(preview_png is None)):
        st.info("📱 **Com utilitzar-lo al mòbil:**\n- **🧱 Paret / 🔲 Espai:** Arrossega el dit sobre la quadreta per traçar la línia o habitació.\n- **📏 Cota:** Arrossega el dit d'un extrem a l'altre per indicar una mesura en metres (s'obrirà un diàleg per posar la mida).\n- **🔤 Text:** Toca sobre l'estança per posar-li nom (ex: *Bany*, *Dutxa*).\n- **📷 Foto de fons:** Carrega una foto de l'estança o d'un croquis en paper per dibuixar-hi al damunt.\n- **↩️ Desfer:** Elimina el darrer traç si t'has equivocat.")
        html_code = get_canvas_html(project_id, existing_bg_b64=bg_b64)
        components.html(html_code, height=650, scrolling=False)

    # Selector per desar el plànol oficial
    with st.form(f"form_save_planol_{project_id}"):
        st.markdown("**💾 Desar o Actualitzar Plànol al Projecte**")
        up_file = st.file_uploader(
            "Selecciona la imatge del plànol (PNG generat per l'editor o foto d'un croquis físic):",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"up_planol_{project_id}"
        )
        sub_planol = st.form_submit_button("Guardar Plànol Oficial", type="primary")
        if sub_planol and up_file:
            b64_data = f"data:image/png;base64,{base64.b64encode(up_file.read()).decode('utf-8')}"
            save_planol_projecte(project_id, preview_png=b64_data)
            st.success("Plànol oficial desat correctament!")
            st.rerun()

    st.markdown("---")

    # Galeria Fotogràfica de Seguiment
    st.markdown("### 📷 Galeria Fotogràfica de l'Obra")
    st.caption("Fes fotos del progrés de l'obra per documentar l'estat inicial (*Abans*), l'evolució (*Durant*) i el resultat final (*Després*).")

    fotos = projecte.get("fotos", [])
    if fotos:
        cols = st.columns(3)
        for i, f in enumerate(fotos):
            col = cols[i % 3]
            with col:
                tipus_badge = {
                    "abans": "🔴 Abans",
                    "durant": "🟡 Durant l'obra",
                    "despres": "🟢 Resultat Final",
                    "altre": "⚪ Altre"
                }.get(f.get("tipus", "altre"), "⚪ Foto")
                
                st.markdown(f"**{tipus_badge}** — *{f.get('data', '')}*")
                if f.get("path"):
                    st.image(f.get("path"), use_container_width=True)
                if f.get("descripcio"):
                    st.caption(f.get("descripcio"))
                if st.button("🗑️ Eliminar foto", key=f"del_foto_{project_id}_{f.get('id', i)}"):
                    delete_projecte_foto(project_id, f.get("id"))
                    st.rerun()
    else:
        st.info("Encara no s'ha afegit cap fotografia a aquest projecte.")

    with st.expander("➕ Afegir Nova Fotografia de l'Obra"):
        with st.form(f"form_add_foto_{project_id}"):
            c1, c2 = st.columns([1, 2])
            with c1:
                tipus_foto = st.selectbox(
                    "Fase de la foto:",
                    ["abans", "durant", "despres", "altre"],
                    format_func=lambda x: {"abans": "🔴 Abans de l'obra", "durant": "🟡 Durant els treballs", "despres": "🟢 Després / Acabat", "altre": "⚪ Altra imatge"}[x],
                    key=f"tipus_foto_{project_id}"
                )
            with c2:
                desc_foto = st.text_input("Descripció o comentari:", placeholder="Ex: Estat inicial de les canonades abans d'enderrocar", key=f"desc_foto_{project_id}")
            
            foto_file = st.file_uploader("Carrega la foto (mòbil o càmera):", type=["jpg", "jpeg", "png", "webp"], key=f"file_foto_{project_id}")
            sub_foto = st.form_submit_button("Pujar Fotografia", type="primary")
            if sub_foto and foto_file:
                b64_foto = f"data:image/jpeg;base64,{base64.b64encode(foto_file.read()).decode('utf-8')}"
                add_projecte_foto(project_id, tipus=tipus_foto, data_url_or_path=b64_foto, descripcio=desc_foto)
                st.success("Fotografia afegida a la galeria!")
                st.rerun()
