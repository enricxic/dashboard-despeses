"""
modules/canvas_planol.py
Component visual de Plànol Interactiu i Galeria Fotogràfica d'Obra.
Inclou:
 1. Editor gràfic lleuger basat en HTML5 Canvas (parets, espais, cotes en metres, text i foto de fons per calcar/acotar).
 2. Desa i càrrega de plànol del projecte.
 3. Galeria de fotos de seguiment de l'obra (Abans, Durant, Després) amb dates en DD/MM/AAAA.
"""

import streamlit as st
import streamlit.components.v1 as components
import base64
import os
from datetime import datetime
from typing import Dict, Any
from core.projectes_manager import (
    save_planol_projecte,
    add_projecte_foto,
    delete_projecte_foto,
    format_date_cat
)

def get_canvas_html(project_id: str, existing_bg_b64: str = "") -> str:
    """Genera el codi HTML+JS complet per a l'editor de plànol interactiu."""
    return f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="utf-8">
<style>
  body {{
    margin: 0;
    padding: 10px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background-color: #f8fafc;
    color: #1e293b;
    user-select: none;
  }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    background: #ffffff;
    padding: 10px 14px;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    margin-bottom: 10px;
  }}
  .btn {{
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
  }}
  .btn:hover {{
    background: #e2e8f0;
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
  .btn-success:hover {{
    background: #15803d;
  }}
  .canvas-wrapper {{
    position: relative;
    border: 2px solid #cbd5e1;
    border-radius: 10px;
    background: #ffffff;
    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    overflow: hidden;
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
  }}
  #planolCanvas {{
    display: block;
    cursor: crosshair;
    background: #ffffff;
  }}
  .status-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    font-size: 12px;
    color: #64748b;
    background: #ffffff;
    border-top: 1px solid #e2e8f0;
  }}
</style>
</head>
<body>

<div class="toolbar">
  <button class="btn active" id="btnWall" onclick="setTool('wall')">🧱 Paret / Línia</button>
  <button class="btn" id="btnRect" onclick="setTool('rect')">🔲 Espai / Habitació</button>
  <button class="btn" id="btnDim" onclick="setTool('dim')">📏 Cota (mides)</button>
  <button class="btn" id="btnText" onclick="setTool('text')">🔤 Text</button>
  <button class="btn" id="btnEraser" onclick="setTool('eraser')">🧹 Goma</button>
  
  <div style="height: 20px; width: 1px; background: #cbd5e1; margin: 0 4px;"></div>
  
  <label class="btn" style="cursor: pointer;">
    📷 Foto de fons
    <input type="file" id="fileBg" accept="image/*" style="display:none;" onchange="loadBgImage(event)">
  </label>
  
  <span style="font-size: 12px; color: #64748b; margin-left: 5px;">Opacitat fons:</span>
  <input type="range" id="bgOpacity" min="10" max="100" value="60" style="width: 80px;" oninput="drawAll()">
  
  <div style="flex-grow: 1;"></div>
  
  <button class="btn" onclick="clearCanvas()">🗑️ Netejar</button>
  <button class="btn btn-success" onclick="downloadImage()">💾 Descarregar Imatge (PNG)</button>
</div>

<div class="canvas-wrapper">
  <canvas id="planolCanvas" width="880" height="550"></canvas>
  <div class="status-bar">
    <span id="toolStatus">Eina activa: Paret / Línia recta. Fes clic i arrossega per dibuixar.</span>
    <span>Graella: 20px ≈ 0,5m</span>
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
let bgImage = null;
let bgOpacityInput = document.getElementById('bgOpacity');

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
  if (tool === 'wall') status.innerText = "Eina: Paret. Fes clic i arrossega per crear una paret recta.";
  else if (tool === 'rect') status.innerText = "Eina: Espai / Habitació. Arrossega per crear una estança rectangular.";
  else if (tool === 'dim') status.innerText = "Eina: Cota. Arrossega per mesurar i s'obrirà un quadre per indicar els metres.";
  else if (tool === 'text') status.innerText = "Eina: Text. Fes clic on vulguis col·locar el nom de l'habitació o nota.";
  else if (tool === 'eraser') status.innerText = "Eina: Goma. Fes clic sobre elements per eliminar-los.";
}}

function snap(val) {{
  return Math.round(val / GRID_SIZE) * GRID_SIZE;
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
    // Escalar mantenint proporció al canvas
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
  
  // 3. Elements dibuixats
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
    ctx.fillStyle = 'rgba(241, 245, 249, 0.4)';
    ctx.beginPath();
    ctx.rect(el.x, el.y, el.w, el.h);
    ctx.fill();
    ctx.stroke();
  }} else if (el.type === 'dim') {{
    // Cota amb fletxes i text
    ctx.strokeStyle = '#2563eb';
    ctx.fillStyle = '#2563eb';
    ctx.lineWidth = 2;
    
    // Línia principal
    ctx.beginPath();
    ctx.moveTo(el.x1, el.y1);
    ctx.lineTo(el.x2, el.y2);
    ctx.stroke();
    
    // Extrems transversals
    const angle = Math.atan2(el.y2 - el.y1, el.x2 - el.x1);
    const tickLen = 6;
    ctx.beginPath();
    ctx.moveTo(el.x1 - Math.sin(angle)*tickLen, el.y1 + Math.cos(angle)*tickLen);
    ctx.lineTo(el.x1 + Math.sin(angle)*tickLen, el.y1 - Math.cos(angle)*tickLen);
    ctx.moveTo(el.x2 - Math.sin(angle)*tickLen, el.y2 + Math.cos(angle)*tickLen);
    ctx.lineTo(el.x2 + Math.sin(angle)*tickLen, el.y2 - Math.cos(angle)*tickLen);
    ctx.stroke();
    
    // Text de mida
    const midX = (el.x1 + el.x2) / 2;
    const midY = (el.y1 + el.y2) / 2;
    ctx.font = 'bold 12px sans-serif';
    ctx.fillStyle = '#1d4ed8';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(el.text || '', midX, midY - 4);
  }} else if (el.type === 'text') {{
    ctx.font = 'bold 14px sans-serif';
    ctx.fillStyle = '#0f172a';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(el.text, el.x, el.y);
  }}
  ctx.restore();
}}

// Esdeveniments de ratolí
canvas.addEventListener('mousedown', (e) => {{
  const rect = canvas.getBoundingClientRect();
  const rawX = e.clientX - rect.left;
  const rawY = e.clientY - rect.top;
  
  if (currentTool === 'text') {{
    const text = prompt("Escriu el text o nom de l'espai (ex: Dutxa, Bany, 2.5m x 1.8m):");
    if (text) {{
      elements.push({{ type: 'text', x: rawX, y: rawY, text: text }});
      drawAll();
    }}
    return;
  }}
  
  if (currentTool === 'eraser') {{
    // Eliminar element més proper
    elements = elements.filter(el => {{
      const cx = el.x || (el.x1 + el.x2) / 2 || 0;
      const cy = el.y || (el.y1 + el.y2) / 2 || 0;
      return Math.hypot(cx - rawX, cy - rawY) > 25;
    }});
    drawAll();
    return;
  }}
  
  isDrawing = true;
  startX = snap(rawX);
  startY = snap(rawY);
}});

canvas.addEventListener('mousemove', (e) => {{
  if (!isDrawing) return;
  const rect = canvas.getBoundingClientRect();
  const currX = snap(e.clientX - rect.left);
  const currY = snap(e.clientY - rect.top);
  
  drawAll();
  
  // Dibuix de previsualització provisional
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

canvas.addEventListener('mouseup', (e) => {{
  if (!isDrawing) return;
  isDrawing = false;
  const rect = canvas.getBoundingClientRect();
  const endX = snap(e.clientX - rect.left);
  const endY = snap(e.clientY - rect.top);
  
  if (startX === endX && startY === endY) return;
  
  if (currentTool === 'wall') {{
    elements.push({{ type: 'wall', x1: startX, y1: startY, x2: endX, y2: endY }});
  }} else if (currentTool === 'rect') {{
    elements.push({{
      type: 'rect',
      x: Math.min(startX, endX),
      y: Math.min(startY, endY),
      w: Math.abs(endX - startX),
      h: Math.abs(endY - startY)
    }});
  }} else if (currentTool === 'dim') {{
    // Calcular estimació en metres (40px = 1m aprox)
    const pxDist = Math.hypot(endX - startX, endY - startY);
    const mDist = (pxDist / 40).toFixed(2);
    const userM = prompt("Indica la mesura de la cota en metres:", mDist + " m");
    elements.push({{
      type: 'dim',
      x1: startX,
      y1: startY,
      x2: endX,
      y2: endY,
      text: userM || (mDist + " m")
    }});
  }}
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
    elements = [];
    drawAll();
  }}
}}

function downloadImage() {{
  const dataURL = canvas.toDataURL('image/png');
  const a = document.createElement('a');
  a.href = dataURL;
  a.download = 'planol_projecte_{project_id}.png';
  a.click();
}}

// Dibuixar inicialment
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

    # Vista prèvia actual si existeix
    if preview_png:
        st.markdown("**Plànol oficial desat per a aquest projecte:**")
        st.image(preview_png, use_container_width=True)
        data_act = planol_info.get("data_actualitzacio", "")
        if data_act:
            st.caption(f"Darrera actualització del plànol: {data_act}")

    # Editor interactiu Canvas
    with st.expander("✏️ Obrir Editor Gràfic de Plànol (Canvas)", expanded=(preview_png is None)):
        html_code = get_canvas_html(project_id, existing_bg_b64=bg_b64)
        components.html(html_code, height=660, scrolling=False)
        st.info("💡 **Consell:** Pots dibuixar les cotes i descarregar la imatge prement 'Descarregar Imatge (PNG)'. A continuació, carrega-la a sota per desar-la definitivament al projecte.")

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
