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
    update_projecte_foto,
    delete_projecte_foto,
    format_date_cat,
    compress_image_b64,
    decode_image_for_st
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
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    width: 100%;
    height: 380px; /* Alçada fixa de finestra que permet scroll lliure tant vertical com horitzontal */
    margin: 0 auto;
  }}
  #planolCanvas {{
    display: block;
    width: 100%;
    aspect-ratio: 1 / 1;
    height: auto;
    cursor: crosshair;
    background: #ffffff;
    touch-action: none; /* Bloqueja l'scroll nadiu per gestionar-lo amb l'eina Moure */
    transition: width 0.15s ease-out;
  }}
  #planolCanvas.pan-mode {{
    cursor: grab;
  }}
  #planolCanvas.grabbing {{
    cursor: grabbing !important;
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
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.65);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 15px;
    overflow-y: auto;
  }}
  .modal-box {{
    background: white;
    padding: 16px;
    border-radius: 12px;
    width: 100%;
    max-width: 360px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
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
    padding: 5px 9px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
  }}
  .preset-btn.active {{
    background: #2563eb;
    color: white;
    border-color: #1d4ed8;
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
  <!-- Mode de Vista: Planta (Terra) vs Alçat (Paret) -->
  <div style="display: inline-flex; gap: 3px; background: #e2e8f0; padding: 2px; border-radius: 8px;">
    <button class="btn active" id="btnModePlanta" onclick="setViewMode('planta')" style="padding: 6px 10px; font-size: 12px;">📐 Planta (Terra)</button>
    <button class="btn" id="btnModeParet" onclick="setViewMode('paret')" style="padding: 6px 10px; font-size: 12px;">🧱 Alçat (Paret)</button>
  </div>

  <div style="height: 20px; width: 1px; background: #cbd5e1; margin: 0 2px;"></div>

  <!-- Eines de Dibuix -->
  <button class="btn active" id="btnWall" onclick="setTool('wall')">🧱 Paret</button>
  <button class="btn" id="btnLine" onclick="setTool('line')" title="Dibuixa una línia recta fina">╱ Línia</button>
  <button class="btn" id="btnCurve" onclick="setTool('curve')" title="Dibuixa una línia corba en 2 passos">〰️ Corba</button>
  <button class="btn" id="btnRoomPreset" onclick="openRoomPresetModal()" style="background: #eff6ff; color: #1d4ed8; border-color: #bfdbfe;" title="Crea una habitació amb mides exactes en metres">🏠 Habitació</button>
  <button class="btn" id="btnRect" onclick="setTool('rect')">🔲 Espai</button>
  <button class="btn" id="btnBucket" onclick="openTexturePicker()" title="Aplica textura a un espai o habitació">🪣 Textura</button>
  <button class="btn" id="btnDim" onclick="setTool('dim')">📏 Cota</button>
  <button class="btn" id="btnText" onclick="setTool('text')">🔤 Text</button>
  <button class="btn" id="btnEraser" onclick="toggleEraser()" title="Activa o desactiva la goma d'esborrar">🧹 Goma</button>
  <button class="btn" id="btnPan" onclick="togglePan()" title="Activa o desactiva el mode de moure la vista">🖐️ Moure</button>
  <button class="btn active" id="btnToggleDrawing" onclick="toggleDrawingVisibility()" style="background: #0f766e; color: white; border-color: #115e59;" title="Amaga o mostra el dibuix fet per veure només les fotos">👁️ Dibuix: SÍ</button>
  
  <div style="height: 20px; width: 1px; background: #cbd5e1; margin: 0 2px;"></div>
  
  <!-- Opcions de Paret Contínua (Seguir traç automàtic) -->
  <div style="display: inline-flex; gap: 3px; align-items: center;">
    <button class="btn active" id="btnContinuous" onclick="toggleContinuous()" style="padding: 6px 9px; font-size: 12px; background: #059669; color: white; border-color: #047857;" title="Enllaça cada nova paret amb l'anterior automàticament">🔗 Seguir: SÍ</button>
    <button class="btn" id="btnNewTrace" onclick="resetContinuous()" style="display:none; padding: 6px 8px; font-size: 11px; background: #fee2e2; color: #b91c1c; border-color: #fca5a5;" title="Allibera el punt actiu per començar una paret en un altre lloc">⏹️ Desconnectar</button>
  </div>

  <div style="height: 20px; width: 1px; background: #cbd5e1; margin: 0 2px;"></div>
  
  <!-- Controls de Zoom -->
  <div style="display: inline-flex; gap: 2px; align-items: center; background: #f1f5f9; padding: 2px 4px; border-radius: 8px; border: 1px solid #cbd5e1;">
    <button class="btn" onclick="zoomIn()" style="padding: 5px 8px; font-size: 12px;" title="Apropar plànol">🔍+</button>
    <button class="btn" onclick="zoomOut()" style="padding: 5px 8px; font-size: 12px;" title="Allunyar plànol">🔍-</button>
    <button class="btn" id="btnZoomVal" onclick="resetZoom()" style="padding: 5px 8px; font-size: 11px;" title="Restablir zoom a 100%">100%</button>
  </div>

  <button class="btn btn-undo" onclick="undo()">↩️ Desfer</button>
  
  <label class="btn" style="cursor: pointer;" title="Afegeix una o més fotos de fons">
    📷 + Foto
    <input type="file" id="fileBg" accept="image/*" multiple style="display:none;" onchange="loadBgImage(event)">
  </label>
  
  <select id="bgPhotoSelect" onchange="selectBgPhoto(this.value)" style="display:none; padding: 6px 8px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 12px; font-weight: 600; background: #f8fafc; color: #1e293b;" title="Selecciona quina foto de fons vols ajustar"></select>
  <span id="bgOpacityLabel" style="font-size: 11px; color: #64748b; margin-left: 2px;">Opacitat:</span>
  <input type="range" id="bgOpacity" min="10" max="100" value="60" style="width: 50px;" oninput="onBgOpacityChange(this.value)">
  <button class="btn" id="btnBgEdit" onclick="toggleBgEdit()" style="display:none; background:#eff6ff; color:#1d4ed8; border-color:#93c5fd;" title="Mou, redimensiona o deforma les 4 cantonades de la foto activa">🖼️ Ajustar Foto</button>
  <button class="btn" id="btnBgReset" onclick="resetBgQuad()" style="display:none; padding: 5px 8px; font-size: 11px;" title="Restablir la forma original de la foto activa">↺ Foto</button>
  <button class="btn" id="btnBgDelete" onclick="deleteActiveBgPhoto()" style="display:none; padding: 5px 8px; font-size: 11px; color:#dc2626; border-color:#fca5a5; background:#fef2f2;" title="Elimina la foto de fons activa">✖ Foto</button>
  
  <button class="btn" style="color:#ef4444;" onclick="clearCanvas()">🗑️</button>
  <button class="btn btn-success" onclick="downloadImage()">💾 Descarregar PNG</button>
</div>

<div class="canvas-wrapper">
  <!-- Resolució nativa nítida 800x800 escalada per CSS a la pantalla del mòbil -->
  <canvas id="planolCanvas" width="800" height="800"></canvas>

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

  <!-- Modal per triar Textura (Galleda) -->
  <div class="modal-overlay" id="textureModal">
    <div class="modal-box" style="max-width: 330px;">
      <h4 style="margin-bottom: 12px;">🪣 Tria la textura a aplicar</h4>
      <div id="textureOptions" style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px;"></div>
      <div class="modal-actions">
        <button class="btn-cancel" onclick="closeTextureModal()">Tancar</button>
      </div>
    </div>
  </div>

  <!-- Modal per Crear Habitació amb Mides Exactes -->
  <div class="modal-overlay" id="roomPresetModal">
    <div class="modal-box" style="max-width: 360px; text-align: left;">
      <h4 style="text-align: center; margin-bottom: 12px; color: #1e3a8a;">🏠 Nova Habitació amb Mides</h4>
      
      <label style="font-size: 12px; font-weight: 600; color: #475569;">📐 Amplada (metres):</label>
      <input type="number" id="roomWidthInput" class="modal-input" value="3.50" step="0.1" min="0.5" max="30" style="margin: 3px 0 6px 0; text-align: center;">
      <div class="preset-btns" style="justify-content: center; margin-bottom: 8px;">
        <button type="button" class="preset-btn" onclick="document.getElementById('roomWidthInput').value='2.00'">2,00</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomWidthInput').value='2.50'">2,50</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomWidthInput').value='3.00'">3,00</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomWidthInput').value='3.50'">3,50</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomWidthInput').value='4.00'">4,00</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomWidthInput').value='5.00'">5,00</button>
      </div>

      <label style="font-size: 12px; font-weight: 600; color: #475569;">📐 Llargada (metres):</label>
      <input type="number" id="roomHeightInput" class="modal-input" value="3.00" step="0.1" min="0.5" max="30" style="margin: 3px 0 6px 0; text-align: center;">
      <div class="preset-btns" style="justify-content: center; margin-bottom: 8px;">
        <button type="button" class="preset-btn" onclick="document.getElementById('roomHeightInput').value='2.00'">2,00</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomHeightInput').value='2.50'">2,50</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomHeightInput').value='3.00'">3,00</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomHeightInput').value='3.50'">3,50</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomHeightInput').value='4.00'">4,00</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomHeightInput').value='5.00'">5,00</button>
      </div>

      <label style="font-size: 12px; font-weight: 600; color: #475569;">🏷️ Nom de l'Estança:</label>
      <input type="text" id="roomNameInput" class="modal-input" value="Dormitori" style="margin: 3px 0 6px 0; text-align: center;">
      <div class="preset-btns" style="justify-content: center; margin-bottom: 8px;">
        <button type="button" class="preset-btn" onclick="document.getElementById('roomNameInput').value='Dormitori'">Dormitori</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomNameInput').value='Bany'">Bany</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomNameInput').value='Cuina'">Cuina</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomNameInput').value='Menjador'">Menjador</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomNameInput').value='Rebedor'">Rebedor</button>
        <button type="button" class="preset-btn" onclick="document.getElementById('roomNameInput').value='Terrassa'">Terrassa</button>
      </div>

      <label style="font-size: 12px; font-weight: 600; color: #475569;">🪵 Textura de Terra:</label>
      <div class="preset-btns" id="roomTexturePresets" style="justify-content: center; margin-bottom: 14px;">
        <button type="button" class="preset-btn active" id="texBtn_parquet" onclick="selectRoomPresetTexture('parquet', this)">🪵 Parquet</button>
        <button type="button" class="preset-btn" id="texBtn_rajola" onclick="selectRoomPresetTexture('rajola', this)">🔲 Rajola</button>
        <button type="button" class="preset-btn" id="texBtn_ciment" onclick="selectRoomPresetTexture('ciment', this)">⚪ Microciment</button>
        <button type="button" class="preset-btn" id="texBtn_gespa" onclick="selectRoomPresetTexture('gespa', this)">🌿 Gespa</button>
        <button type="button" class="preset-btn" id="texBtn_none" onclick="selectRoomPresetTexture('none', this)">❌ Sense</button>
      </div>

      <div class="modal-actions">
        <button type="button" class="btn-cancel" onclick="closeRoomPresetModal()">Cancel·lar</button>
        <button type="button" class="btn-confirm" onclick="createPresetRoom()" style="background: #16a34a;">✨ Crear Habitació</button>
      </div>
    </div>
  </div>
</div>

<div class="status-bar">
  <span id="toolStatus">👉 Mode Planta: Arrossega el dit per dibuixar una paret recta</span>
  <span id="modeStatus">Graella: 20px ≈ 0,5m</span>
</div>

<script>
const canvas = document.getElementById('planolCanvas');
const canvasWrapper = document.querySelector('.canvas-wrapper');
const ctx = canvas.getContext('2d');
const GRID_SIZE = 20;

let currentTool = 'wall';
let previousDrawingTool = 'wall';
let currentViewMode = 'planta'; // 'planta' (terra) o 'paret' (alçat)
let currentZoom = 1.0;
let isDrawing = false;
let isPanning = false;
let panStartX = 0, panStartY = 0;
let scrollStartLeft = 0, scrollStartTop = 0;
let isContinuous = true; // Mode enllaçar parets actiu per defecte
let lastWallEnd = null; // Últim extrem de paret per continuar traç automàtic
let startX = 0, startY = 0;
let elements = [];
let history = [];
let bgPhotos = []; // [{{ id, name, img, quad, opacity }}]
let activeBgIdx = -1;
let bgDragState = null;
let pendingCurve = null;
let showDrawing = true;
let isExporting = false;
let bgOpacityInput = document.getElementById('bgOpacity');
let pendingModalCallback = null;

// Gestió de Zoom
function setZoom(val) {{
  currentZoom = Math.max(0.75, Math.min(2.5, Math.round(val * 100) / 100));
  canvas.style.width = (currentZoom * 100) + '%';
  const btnZ = document.getElementById('btnZoomVal');
  if (btnZ) btnZ.innerText = Math.round(currentZoom * 100) + '%';
}}
function zoomIn() {{ setZoom(currentZoom + 0.25); }}
function zoomOut() {{ setZoom(currentZoom - 0.25); }}
function resetZoom() {{
  setZoom(1.0);
  canvasWrapper.scrollLeft = (canvasWrapper.scrollWidth - canvasWrapper.clientWidth) / 2;
  canvasWrapper.scrollTop = (canvasWrapper.scrollHeight - canvasWrapper.clientHeight) / 2;
}}

// Commutador ràpid de l'eina Moure
function togglePan() {{
  if (currentTool === 'pan') {{
    setTool(previousDrawingTool || 'wall');
  }} else {{
    previousDrawingTool = (currentTool !== 'eraser') ? currentTool : 'wall';
    setTool('pan');
  }}
}}

// Commutador ràpid de la Goma d'esborrar
function toggleEraser() {{
  if (currentTool === 'eraser') {{
    setTool(previousDrawingTool || 'wall');
  }} else {{
    previousDrawingTool = (currentTool !== 'pan') ? currentTool : 'wall';
    setTool('eraser');
  }}
}}

// Gestió de Mode de Vista: Planta (Terra) vs Alçat (Paret)
function setViewMode(mode) {{
  currentViewMode = mode;
  document.getElementById('btnModePlanta').classList.toggle('active', mode === 'planta');
  document.getElementById('btnModeParet').classList.toggle('active', mode === 'paret');
  
  const status = document.getElementById('toolStatus');
  const modeStatus = document.getElementById('modeStatus');
  if (mode === 'paret') {{
    status.innerText = "🧱 Mode Alçat (Paret): Dibuixa alçades, amples i cotes d'una paret o façana vertical.";
    modeStatus.innerText = "Vista: Alçat vertical (Sòl a Sostre)";
  }} else {{
    status.innerText = "📐 Mode Planta (Terra): Dibuixa la distribució horitzontal del terra.";
    modeStatus.innerText = "Vista: Planta horitzontal (Terra)";
  }}
  drawAll();
}}

// Inicialització i gestió de deformació de múltiples fotos de fons
function createBgQuad(img, offsetIdx = 0) {{
  if (!img) return null;
  const hRatio = canvas.width / img.width;
  const vRatio = canvas.height / img.height;
  const ratio = Math.min(hRatio, vRatio) * (offsetIdx > 0 ? 0.65 : 1.0);
  const w = img.width * ratio;
  const h = img.height * ratio;
  const shift = (offsetIdx % 4) * 24;
  const x = Math.max(0, Math.min(canvas.width - w, (canvas.width - w) / 2 + shift));
  const y = Math.max(0, Math.min(canvas.height - h, (canvas.height - h) / 2 + shift));
  return {{
    tl: {{ x: x, y: y }},
    tr: {{ x: x + w, y: y }},
    br: {{ x: x + w, y: y + h }},
    bl: {{ x: x, y: y + h }}
  }};
}}

function getActiveBgPhoto() {{
  if (activeBgIdx >= 0 && activeBgIdx < bgPhotos.length) {{
    return bgPhotos[activeBgIdx];
  }}
  return null;
}}

function updateBgControlsUI() {{
  const hasImg = bgPhotos.length > 0;
  if (hasImg && (activeBgIdx < 0 || activeBgIdx >= bgPhotos.length)) {{
    activeBgIdx = bgPhotos.length - 1;
  }} else if (!hasImg) {{
    activeBgIdx = -1;
  }}

  const sel = document.getElementById('bgPhotoSelect');
  if (sel) {{
    sel.style.display = hasImg ? 'inline-block' : 'none';
    sel.innerHTML = '';
    bgPhotos.forEach((p, idx) => {{
      const opt = document.createElement('option');
      opt.value = String(idx);
      opt.text = p.name || `Foto ${{idx + 1}}`;
      if (idx === activeBgIdx) opt.selected = true;
      sel.appendChild(opt);
    }});
  }}

  const active = getActiveBgPhoto();
  if (active && bgOpacityInput) {{
    bgOpacityInput.value = String(active.opacity ?? 60);
  }}

  const btnE = document.getElementById('btnBgEdit');
  const btnR = document.getElementById('btnBgReset');
  const btnD = document.getElementById('btnBgDelete');
  if (btnE) btnE.style.display = hasImg ? 'inline-flex' : 'none';
  if (btnR) btnR.style.display = hasImg ? 'inline-flex' : 'none';
  if (btnD) btnD.style.display = hasImg ? 'inline-flex' : 'none';
}}

function selectBgPhoto(val) {{
  const idx = parseInt(val, 10);
  if (!isNaN(idx) && idx >= 0 && idx < bgPhotos.length) {{
    activeBgIdx = idx;
    updateBgControlsUI();
    drawAll();
  }}
}}

function onBgOpacityChange(val) {{
  const active = getActiveBgPhoto();
  if (active) {{
    active.opacity = parseInt(val, 10) || 60;
  }}
  drawAll();
}}

function resetBgQuad() {{
  const active = getActiveBgPhoto();
  if (!active) return;
  active.quad = createBgQuad(active.img, 0);
  drawAll();
  const status = document.getElementById('toolStatus');
  if (status) status.innerText = "↺ Foto restablerta a la posició i proporció originals.";
}}

function deleteActiveBgPhoto() {{
  if (activeBgIdx < 0 || activeBgIdx >= bgPhotos.length) return;
  bgPhotos.splice(activeBgIdx, 1);
  if (bgPhotos.length === 0) {{
    activeBgIdx = -1;
    if (currentTool === 'bg_edit') setTool(previousDrawingTool || 'wall');
  }} else {{
    activeBgIdx = Math.min(activeBgIdx, bgPhotos.length - 1);
  }}
  updateBgControlsUI();
  drawAll();
  const status = document.getElementById('toolStatus');
  if (status) status.innerText = bgPhotos.length ? "🗑️ Foto eliminada." : "🗑️ Totes les fotos de fons eliminades.";
}}

function toggleBgEdit() {{
  if (bgPhotos.length === 0) return;
  if (currentTool === 'bg_edit') {{
    setTool(previousDrawingTool || 'wall');
  }} else {{
    if (currentTool !== 'pan' && currentTool !== 'eraser' && currentTool !== 'bg_edit') {{
      previousDrawingTool = currentTool;
    }}
    setTool('bg_edit');
  }}
}}

function toggleDrawingVisibility() {{
  showDrawing = !showDrawing;
  const btn = document.getElementById('btnToggleDrawing');
  if (btn) {{
    if (showDrawing) {{
      btn.classList.add('active');
      btn.innerHTML = '👁️ Dibuix: SÍ';
      btn.style.background = '#0f766e';
      btn.style.borderColor = '#115e59';
      btn.style.color = '#ffffff';
    }} else {{
      btn.classList.remove('active');
      btn.innerHTML = '🙈 Dibuix: NO';
      btn.style.background = '#f1f5f9';
      btn.style.borderColor = '#cbd5e1';
      btn.style.color = '#475569';
    }}
  }}
  drawAll();
  const status = document.getElementById('toolStatus');
  if (status) {{
    status.innerText = showDrawing
      ? "👁️ Dibuix visible sobre el plànol."
      : "🙈 Dibuix amagat: només es veuen les fotos de fons i la graella.";
  }}
}}

// Si hi ha imatge de fons preexistent
const preBg = "{existing_bg_b64}";
if (preBg && preBg.length > 50) {{
  const img = new Image();
  img.onload = () => {{
    bgPhotos.push({{
      id: Date.now(),
      name: 'Foto 1',
      img: img,
      quad: createBgQuad(img, 0),
      opacity: parseInt(bgOpacityInput.value, 10) || 60
    }});
    activeBgIdx = 0;
    updateBgControlsUI();
    drawAll();
  }};
  img.src = preBg;
}}

let selectedTexture = 'parquet';
let selectedTextureName = '🪵 Parquet';
let selectedRoomTexture = 'parquet';
const patterns = {{}};

function getPattern(type) {{
  if (!type || type === 'none') return 'rgba(241, 245, 249, 0.45)';
  if (patterns[type]) return patterns[type];
  const pCanvas = document.createElement('canvas');
  const pCtx = pCanvas.getContext('2d');
  
  if (type === 'parquet') {{
    pCanvas.width = 40;
    pCanvas.height = 20;
    pCtx.fillStyle = '#fef3c7';
    pCtx.fillRect(0, 0, 40, 20);
    pCtx.strokeStyle = '#d97706';
    pCtx.lineWidth = 1;
    pCtx.strokeRect(0, 0, 40, 10);
    pCtx.strokeRect(20, 10, 40, 10);
    pCtx.strokeRect(-20, 10, 40, 10);
    pCtx.strokeStyle = 'rgba(180, 83, 9, 0.25)';
    pCtx.beginPath();
    pCtx.moveTo(4, 5); pCtx.lineTo(36, 5);
    pCtx.moveTo(24, 15); pCtx.lineTo(36, 15);
    pCtx.stroke();
  }} else if (type === 'rajola') {{
    pCanvas.width = 24;
    pCanvas.height = 24;
    pCtx.fillStyle = '#f8fafc';
    pCtx.fillRect(0, 0, 24, 24);
    pCtx.strokeStyle = '#94a3b8';
    pCtx.lineWidth = 1.2;
    pCtx.strokeRect(0, 0, 24, 24);
  }} else if (type === 'dutxa') {{
    pCanvas.width = 16;
    pCanvas.height = 16;
    pCtx.fillStyle = '#bae6fd';
    pCtx.fillRect(0, 0, 16, 16);
    pCtx.strokeStyle = '#0284c7';
    pCtx.lineWidth = 1;
    pCtx.strokeRect(0, 0, 8, 8);
    pCtx.strokeRect(8, 0, 8, 8);
    pCtx.strokeRect(0, 8, 8, 8);
    pCtx.strokeRect(8, 8, 8, 8);
  }} else if (type === 'gespa') {{
    pCanvas.width = 24;
    pCanvas.height = 24;
    pCtx.fillStyle = '#dcfce7';
    pCtx.fillRect(0, 0, 24, 24);
    pCtx.fillStyle = '#16a34a';
    pCtx.beginPath();
    pCtx.arc(6, 6, 1.5, 0, Math.PI * 2);
    pCtx.arc(18, 16, 1.5, 0, Math.PI * 2);
    pCtx.arc(14, 5, 1.2, 0, Math.PI * 2);
    pCtx.arc(7, 18, 1.2, 0, Math.PI * 2);
    pCtx.fill();
  }} else if (type === 'ciment') {{
    pCanvas.width = 20;
    pCanvas.height = 20;
    pCtx.fillStyle = '#e2e8f0';
    pCtx.fillRect(0, 0, 20, 20);
    pCtx.fillStyle = 'rgba(100, 116, 139, 0.2)';
    pCtx.fillRect(2, 2, 4, 3);
    pCtx.fillRect(12, 10, 5, 2);
  }} else if (type === 'mao') {{
    pCanvas.width = 36;
    pCanvas.height = 18;
    pCtx.fillStyle = '#fca5a5';
    pCtx.fillRect(0, 0, 36, 18);
    pCtx.strokeStyle = '#b91c1c';
    pCtx.lineWidth = 1.2;
    pCtx.strokeRect(0, 0, 36, 9);
    pCtx.strokeRect(18, 9, 36, 9);
    pCtx.strokeRect(-18, 9, 36, 9);
  }} else if (type === 'subway') {{
    pCanvas.width = 30;
    pCanvas.height = 14;
    pCtx.fillStyle = '#ffffff';
    pCtx.fillRect(0, 0, 30, 14);
    pCtx.strokeStyle = '#94a3b8';
    pCtx.lineWidth = 1;
    pCtx.strokeRect(0, 0, 30, 7);
    pCtx.strokeRect(15, 7, 30, 7);
    pCtx.strokeRect(-15, 7, 30, 7);
  }} else if (type === 'pedra') {{
    pCanvas.width = 32;
    pCanvas.height = 24;
    pCtx.fillStyle = '#e5e5e5';
    pCtx.fillRect(0, 0, 32, 24);
    pCtx.strokeStyle = '#737373';
    pCtx.lineWidth = 1.2;
    pCtx.strokeRect(1, 1, 20, 10);
    pCtx.strokeRect(22, 1, 9, 10);
    pCtx.strokeRect(1, 12, 13, 11);
    pCtx.strokeRect(15, 12, 16, 11);
  }} else {{
    return 'rgba(241, 245, 249, 0.45)';
  }}
  
  const pattern = ctx.createPattern(pCanvas, 'repeat');
  patterns[type] = pattern;
  return pattern;
}}

function openTexturePicker() {{
  const modal = document.getElementById('textureModal');
  const container = document.getElementById('textureOptions');
  container.innerHTML = '';
  
  const isParet = (currentViewMode === 'paret');
  const options = isParet
    ? [
        {{ id: 'mao', name: '🧱 Maó vist', desc: 'Totxo rústic vermell' }},
        {{ id: 'subway', name: '🔲 Rajola blanca', desc: 'Cuina o bany' }},
        {{ id: 'pedra', name: '🪨 Pedra rústica', desc: 'Mur tradicional' }},
        {{ id: 'parquet', name: '🪵 Llistons fusta', desc: 'Revestiment fusta' }},
        {{ id: 'ciment', name: '⚪ Calç / Ciment', desc: 'Paret arrebossada' }},
        {{ id: 'none', name: '❌ Sense textura', desc: 'Fons transparent' }}
      ]
    : [
        {{ id: 'parquet', name: '🪵 Parquet', desc: 'Fusta càlida roure' }},
        {{ id: 'rajola', name: '🔲 Rajola / Gres', desc: 'Ceràmica bany/cuina' }},
        {{ id: 'dutxa', name: '🟦 Dutxa / Gresite', desc: 'Aigua / zona humida' }},
        {{ id: 'gespa', name: '🌿 Gespa / Pati', desc: 'Terrassa o jardí' }},
        {{ id: 'ciment', name: '⚪ Microciment', desc: 'Formigó modern' }},
        {{ id: 'none', name: '❌ Sense textura', desc: 'Fons transparent' }}
      ];

  options.forEach(opt => {{
    const b = document.createElement('button');
    b.className = 'preset-btn' + (selectedTexture === opt.id ? ' active' : '');
    b.style.padding = '8px 10px';
    b.style.textAlign = 'left';
    b.style.display = 'flex';
    b.style.flexDirection = 'column';
    b.innerHTML = `<span style="font-weight:600; font-size:13px;">${{opt.name}}</span><span style="font-size:10px; color:#64748b;">${{opt.desc}}</span>`;
    b.onclick = () => {{
      selectedTexture = opt.id;
      selectedTextureName = opt.name;
      closeTextureModal();
      setTool('bucket');
    }};
    container.appendChild(b);
  }});

  modal.style.display = 'flex';
}}

function closeTextureModal() {{
  document.getElementById('textureModal').style.display = 'none';
}}

function openRoomPresetModal() {{
  document.getElementById('roomPresetModal').style.display = 'flex';
}}

function closeRoomPresetModal() {{
  document.getElementById('roomPresetModal').style.display = 'none';
}}

function selectRoomPresetTexture(tex, btn) {{
  selectedRoomTexture = tex;
  document.querySelectorAll('#roomTexturePresets .preset-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
}}

function createPresetRoom() {{
  const wInput = parseFloat(document.getElementById('roomWidthInput').value) || 3.5;
  const hInput = parseFloat(document.getElementById('roomHeightInput').value) || 3.0;
  const nameInput = document.getElementById('roomNameInput').value.trim() || 'Habitació';
  const texInput = selectedRoomTexture || 'parquet';

  // 40px = 1m
  const wPx = Math.round((wInput * 40) / GRID_SIZE) * GRID_SIZE;
  const hPx = Math.round((hInput * 40) / GRID_SIZE) * GRID_SIZE;

  // Trobar posició centrada a l'espai visible del canvas
  let rx = snap((canvas.width - wPx) / 2);
  let ry = snap((canvas.height - hPx) / 2);

  // Si ja hi ha un espai a la mateixa coordenada, desplaçar lleugerament
  while (elements.some(el => el.type === 'rect' && Math.abs(el.x - rx) < 20 && Math.abs(el.y - ry) < 20)) {{
    rx += GRID_SIZE * 2;
    ry += GRID_SIZE * 2;
  }}

  saveHistory();

  // 1. L'espai interior amb textura i etiqueta
  elements.push({{
    type: 'rect',
    x: rx,
    y: ry,
    w: wPx,
    h: hPx,
    texture: texInput,
    label: nameInput + " (" + wInput.toFixed(2) + " x " + hInput.toFixed(2) + " m)"
  }});

  // 2. Les 4 parets de contorn
  elements.push({{ type: 'wall', x1: rx, y1: ry, x2: rx + wPx, y2: ry }});
  elements.push({{ type: 'wall', x1: rx + wPx, y1: ry, x2: rx + wPx, y2: ry + hPx }});
  elements.push({{ type: 'wall', x1: rx + wPx, y1: ry + hPx, x2: rx, y2: ry + hPx }});
  elements.push({{ type: 'wall', x1: rx, y1: ry + hPx, x2: rx, y2: ry }});

  // 3. Les cotes de mesura automàtiques
  elements.push({{
    type: 'dim',
    x1: rx,
    y1: ry - 16,
    x2: rx + wPx,
    y2: ry - 16,
    text: wInput.toFixed(2) + " m"
  }});
  elements.push({{
    type: 'dim',
    x1: rx - 16,
    y1: ry,
    x2: rx - 16,
    y2: ry + hPx,
    text: hInput.toFixed(2) + " m"
  }});

  closeRoomPresetModal();
  drawAll();
  
  const status = document.getElementById('toolStatus');
  if (status) status.innerText = `✅ Habitació '${{nameInput}}' (${{wInput.toFixed(2)}}m x ${{hInput.toFixed(2)}}m) afegida correctament!`;
}}

function setTool(tool) {{
  // Commutador si es torna a prémer la mateixa eina especial activa
  if (tool === 'pan' && currentTool === 'pan') {{
    tool = previousDrawingTool || 'wall';
  }}
  if (tool === 'eraser' && currentTool === 'eraser') {{
    tool = previousDrawingTool || 'wall';
  }}
  
  if (tool !== 'curve' && pendingCurve) {{
    pendingCurve = null;
  }}

  if (currentTool !== 'pan' && currentTool !== 'eraser' && currentTool !== 'bg_edit') {{
    previousDrawingTool = currentTool;
  }}

  currentTool = tool;
  isPanning = false;
  isDrawing = false;
  bgDragState = null;
  canvas.classList.remove('grabbing');

  document.querySelectorAll('.btn').forEach(b => {{
    if (['btnWall', 'btnLine', 'btnCurve', 'btnRect', 'btnDim', 'btnText', 'btnEraser', 'btnPan', 'btnBucket', 'btnBgEdit'].includes(b.id)) {{
      b.classList.remove('active');
    }}
  }});
  
  const btn = document.getElementById('btn' + tool.charAt(0).toUpperCase() + tool.slice(1));
  if (btn) btn.classList.add('active');

  const btnBgEdit = document.getElementById('btnBgEdit');
  if (btnBgEdit) {{
    if (tool === 'bg_edit') {{
      btnBgEdit.classList.add('active');
      btnBgEdit.innerHTML = '🖼️ Ajustar Foto: ON';
      btnBgEdit.style.background = '#2563eb';
      btnBgEdit.style.borderColor = '#1d4ed8';
      btnBgEdit.style.color = '#ffffff';
    }} else {{
      btnBgEdit.classList.remove('active');
      btnBgEdit.innerHTML = '🖼️ Ajustar Foto';
      btnBgEdit.style.background = '#eff6ff';
      btnBgEdit.style.borderColor = '#93c5fd';
      btnBgEdit.style.color = '#1d4ed8';
    }}
  }}
  
  const btnPan = document.getElementById('btnPan');
  if (btnPan) {{
    if (tool === 'pan') {{
      btnPan.classList.add('active');
      btnPan.innerHTML = '🖐️ Moure: ON';
      btnPan.style.background = '#0284c7';
      btnPan.style.borderColor = '#0369a1';
      btnPan.style.color = '#ffffff';
    }} else {{
      btnPan.classList.remove('active');
      btnPan.innerHTML = '🖐️ Moure';
      btnPan.style.background = '';
      btnPan.style.borderColor = '';
      btnPan.style.color = '';
    }}
  }}

  const btnEraser = document.getElementById('btnEraser');
  if (btnEraser) {{
    if (tool === 'eraser') {{
      btnEraser.classList.add('active');
      btnEraser.innerHTML = '🧹 Goma: ON';
      btnEraser.style.background = '#dc2626';
      btnEraser.style.borderColor = '#b91c1c';
      btnEraser.style.color = '#ffffff';
    }} else {{
      btnEraser.classList.remove('active');
      btnEraser.innerHTML = '🧹 Goma';
      btnEraser.style.background = '';
      btnEraser.style.borderColor = '';
      btnEraser.style.color = '';
    }}
  }}

  if (tool === 'pan') {{
    canvas.classList.add('pan-mode');
  }} else {{
    canvas.classList.remove('pan-mode');
  }}

  // Si canviem a eines que no són paret ni moure, desactivem el punt d'ancoratge
  if (tool !== 'wall' && tool !== 'pan') {{
    lastWallEnd = null;
    updateContinuousUI();
  }}
  
  const status = document.getElementById('toolStatus');
  const esParet = (currentViewMode === 'paret');
  if (tool === 'wall') {{
    status.innerText = (isContinuous && lastWallEnd)
      ? "👉 Paret contínua: Arrossega o toca la propera cantonada per seguir l'habitació des del punt marcat."
      : (esParet ? "👉 Paret: Arrossega per traçar els límits o seccions de la paret." : "👉 Paret: Arrossega el dit per traçar una paret recta al terra.");
  }}
  else if (tool === 'line') status.innerText = "👉 Línia: Arrossega d'un extrem a l'altre per traçar una línia recta fina.";
  else if (tool === 'curve') status.innerText = "👉 Corba (Pas 1/2): Arrossega d'un extrem a l'altre i després estira el punt central per corbar.";
  else if (tool === 'bg_edit') status.innerText = "🖼️ Ajustar Foto: Arrossega les 4 cantonades blaves per deformar en perspectiva, els punts mitjans per estirar o el centre per moure.";
  else if (tool === 'rect') status.innerText = esParet ? "👉 Espai: Arrossega per dibuixar una finestra, porta o moble suspès a la paret." : "👉 Espai: Arrossega per crear una habitació o moble.";
  else if (tool === 'dim') status.innerText = esParet ? "👉 Cota: Arrossega verticalment per alçada (sostre/sòcol) o horitzontalment per amplada." : "👉 Cota: Arrossega d'un extrem a l'altre per mesurar la distància.";
  else if (tool === 'text') status.innerText = esParet ? "👉 Text: Toca per anotar rajoles, forats a tapar, calç, ciment o canonades." : "👉 Text: Toca per posar nom a l'estança o nota.";
  else if (tool === 'eraser') status.innerText = "👉 Goma activada: Toca o passa el dit sobre qualsevol línia per esborrar-la. Toca 'Goma: ON' o 'Paret' per tornar a dibuixar.";
  else if (tool === 'pan') status.innerText = "👉 Moure activat: Arrossega per desplaçar el plànol. Toca 'Moure: ON' o 'Paret' per tornar a dibuixar.";
  else if (tool === 'bucket') status.innerText = `👉 Galleda (${{selectedTextureName || 'Textura'}}): Toca un espai per omplir-lo o arrossega per crear una zona texturada.`;
}}

function snap(val) {{
  return Math.round(val / GRID_SIZE) * GRID_SIZE;
}}

// Càlcul de distància matemàtica exacta entre un punt (px, py) i un segment de línia
function distToSegment(px, py, x1, y1, x2, y2) {{
  const dx = x2 - x1;
  const dy = y2 - y1;
  const l2 = dx * dx + dy * dy;
  if (l2 === 0) return Math.hypot(px - x1, py - y1);
  let t = ((px - x1) * dx + (py - y1) * dy) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}}

// Detecció intel·ligent si el toc cau sobre qualsevol element dibuixat (amb tolerància tàctil)
function hitTestElement(el, px, py) {{
  const HIT_RADIUS = 26; // 26px de tolerància per al dit al mòbil
  if (el.type === 'wall' || el.type === 'line' || el.type === 'dim') {{
    return distToSegment(px, py, el.x1, el.y1, el.x2, el.y2) <= HIT_RADIUS;
  }}
  if (el.type === 'curve') {{
    const STEPS = 16;
    let prevX = el.x1, prevY = el.y1;
    for (let i = 1; i <= STEPS; i++) {{
      const t = i / STEPS;
      const mt = 1 - t;
      const bx = mt * mt * el.x1 + 2 * mt * t * el.cx + t * t * el.x2;
      const by = mt * mt * el.y1 + 2 * mt * t * el.cy + t * t * el.y2;
      if (distToSegment(px, py, prevX, prevY, bx, by) <= HIT_RADIUS) return true;
      prevX = bx; prevY = by;
    }}
    return false;
  }}
  if (el.type === 'rect') {{
    const dTop = distToSegment(px, py, el.x, el.y, el.x + el.w, el.y);
    const dBottom = distToSegment(px, py, el.x, el.y + el.h, el.x + el.w, el.y + el.h);
    const dLeft = distToSegment(px, py, el.x, el.y, el.x, el.y + el.h);
    const dRight = distToSegment(px, py, el.x + el.w, el.y, el.x + el.w, el.y + el.h);
    if (Math.min(dTop, dBottom, dLeft, dRight) <= HIT_RADIUS) return true;
    if (px >= el.x && px <= el.x + el.w && py >= el.y && py <= el.y + el.h) return true;
    return false;
  }}
  if (el.type === 'text') {{
    const txt = el.text || '';
    const estW = Math.max(40, txt.length * 9 + 16);
    if (px >= el.x - estW / 2 - 14 && px <= el.x + estW / 2 + 14 && py >= el.y - 24 && py <= el.y + 24) return true;
    return Math.hypot(el.x - px, el.y - py) <= 30;
  }}
  return false;
}}

// Funció per esborrar elements tocats per la goma
function eraseAt(px, py) {{
  const prevLen = elements.length;
  elements = elements.filter(el => !hitTestElement(el, px, py));
  if (elements.length !== prevLen) {{
    saveHistory();
    const lastWall = [...elements].reverse().find(el => el.type === 'wall');
    lastWallEnd = lastWall ? {{ x: lastWall.x2, y: lastWall.y2 }} : null;
    updateContinuousUI();
    drawAll();
    return true;
  }}
  return false;
}}

function findSnapPoint(rawX, rawY) {{
  const SNAP_THRESHOLD = 26; // Radi magnètic en px per enllaçar cantonades
  let bestPt = null;
  let minDist = SNAP_THRESHOLD;
  
  for (const el of elements) {{
    if (el.type === 'wall' || el.type === 'line' || el.type === 'dim' || el.type === 'curve') {{
      const pts = [{{ x: el.x1, y: el.y1 }}, {{ x: el.x2, y: el.y2 }}];
      for (const p of pts) {{
        const d = Math.hypot(p.x - rawX, p.y - rawY);
        if (d < minDist) {{
          minDist = d;
          bestPt = {{ x: p.x, y: p.y }};
        }}
      }}
    }} else if (el.type === 'rect') {{
      const corners = [
        {{ x: el.x, y: el.y }},
        {{ x: el.x + el.w, y: el.y }},
        {{ x: el.x, y: el.y + el.h }},
        {{ x: el.x + el.w, y: el.y + el.h }}
      ];
      for (const p of corners) {{
        const d = Math.hypot(p.x - rawX, p.y - rawY);
        if (d < minDist) {{
          minDist = d;
          bestPt = {{ x: p.x, y: p.y }};
        }}
      }}
    }}
  }}
  return bestPt;
}}

function getPointerCoords(e) {{
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const rawX = (e.clientX - rect.left) * scaleX;
  const rawY = (e.clientY - rect.top) * scaleY;

  // 1. Cercar vèrtex o cantonada existent propera per fer snap magnètic
  const snapPt = findSnapPoint(rawX, rawY);
  if (snapPt) {{
    return {{
      x: snapPt.x,
      y: snapPt.y,
      rawX: rawX,
      rawY: rawY,
      isSnapped: true
    }};
  }}

  // 2. Si no hi ha cantonada propera, ajustar a la graella estàndard
  return {{
    x: snap(rawX),
    y: snap(rawY),
    rawX: rawX,
    rawY: rawY,
    isSnapped: false
  }};
}}

function toggleContinuous() {{
  isContinuous = !isContinuous;
  if (!isContinuous) {{
    lastWallEnd = null;
  }}
  updateContinuousUI();
  drawAll();
}}

function resetContinuous() {{
  lastWallEnd = null;
  updateContinuousUI();
  drawAll();
  const status = document.getElementById('toolStatus');
  if (status) status.innerText = "👉 Paret: Desconnectat. Toca o arrossega per començar una paret separada.";
}}

function updateContinuousUI() {{
  const btnC = document.getElementById('btnContinuous');
  const btnN = document.getElementById('btnNewTrace');
  if (btnC) {{
    if (isContinuous) {{
      btnC.classList.add('active');
      btnC.innerHTML = '🔗 Seguir: SÍ';
      btnC.style.background = '#059669';
      btnC.style.borderColor = '#047857';
      btnC.style.color = '#ffffff';
    }} else {{
      btnC.classList.remove('active');
      btnC.innerHTML = '🔗 Seguir: NO';
      btnC.style.background = '#f1f5f9';
      btnC.style.borderColor = '#cbd5e1';
      btnC.style.color = '#334155';
    }}
  }}
  if (btnN) {{
    btnN.style.display = (isContinuous && lastWallEnd) ? 'inline-flex' : 'none';
  }}
}}

function saveHistory() {{
  history.push(JSON.stringify(elements));
  if (history.length > 20) history.shift();
}}

function undo() {{
  if (pendingCurve) {{
    pendingCurve = null;
    drawAll();
    const status = document.getElementById('toolStatus');
    if (status) status.innerText = "👉 Corba (Pas 1/2): Arrossega d'un extrem a l'altre i després estira el punt central per corbar.";
    return;
  }}
  if (history.length > 0) {{
    elements = JSON.parse(history.pop());
  }} else if (elements.length > 0) {{
    elements.pop();
  }}
  
  // Trobar l'última paret que quedi per poder seguir el traç
  const lastWall = [...elements].reverse().find(el => el.type === 'wall');
  lastWallEnd = lastWall ? {{ x: lastWall.x2, y: lastWall.y2 }} : null;
  updateContinuousUI();
  drawAll();
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

  // Guies visuals de referència quan estem en mode Alçat (Paret)
  if (currentViewMode === 'paret') {{
    ctx.save();
    // Línia de Sòl / Terra (part inferior)
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, canvas.height - 30);
    ctx.lineTo(canvas.width, canvas.height - 30);
    ctx.stroke();

    ctx.font = 'bold 11px sans-serif';
    ctx.fillStyle = '#059669';
    ctx.textAlign = 'left';
    ctx.fillText('⬇️ LÍNIA DE TERRA / SÒL (0,00 m)', 10, canvas.height - 36);

    // Línia de Sostre (part superior)
    ctx.strokeStyle = '#64748b';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(0, 50);
    ctx.lineTo(canvas.width, 50);
    ctx.stroke();

    ctx.fillStyle = '#475569';
    ctx.fillText('⬆️ LÍNIA DE SOSTRE (Alçada: ~2,50 m)', 10, 42);
    ctx.restore();
  }}
}}

function drawTexturedTriangle(img, sx0, sy0, sx1, sy1, sx2, sy2, dx0, dy0, dx1, dy1, dx2, dy2) {{
  const denom = sx0 * (sy2 - sy1) - sx1 * sy2 + sx2 * sy1 + (sx1 - sx2) * sy0;
  if (Math.abs(denom) < 1e-6) return;
  const m11 = -(sy0 * (dx2 - dx1) - sy1 * dx2 + sy2 * dx1 + (sy1 - sy2) * dx0) / denom;
  const m12 = (sy1 * dy2 + sy0 * (dy1 - dy2) - sy2 * dy1 + (sy2 - sy1) * dy0) / denom;
  const m21 = (sx0 * (dx2 - dx1) - sx1 * dx2 + sx2 * dx1 + (sx1 - sx2) * dx0) / denom;
  const m22 = -(sx1 * dy2 + sx0 * (dy1 - dy2) - sx2 * dy1 + (sx2 - sx1) * dy0) / denom;
  const dx = (sx0 * (sy2 * dx1 - sy1 * dx2) + sy0 * (sx1 * dx2 - sx2 * dx1) + (sx2 * sy1 - sx1 * sy2) * dx0) / denom;
  const dy = (sx0 * (sy2 * dy1 - sy1 * dy2) + sy0 * (sx1 * dy2 - sx2 * dy1) + (sx2 * sy1 - sx1 * sy2) * dy0) / denom;

  // Lleugera expansió de 0.45px des del centroide per evitar micro-fissures entre triangles
  const cx = (dx0 + dx1 + dx2) / 3;
  const cy = (dy0 + dy1 + dy2) / 3;
  const expand = (x, y) => {{
    const vx = x - cx, vy = y - cy;
    const len = Math.hypot(vx, vy) || 1;
    return [x + (vx / len) * 0.45, y + (vy / len) * 0.45];
  }};
  const [ex0, ey0] = expand(dx0, dy0);
  const [ex1, ey1] = expand(dx1, dy1);
  const [ex2, ey2] = expand(dx2, dy2);

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(ex0, ey0);
  ctx.lineTo(ex1, ey1);
  ctx.lineTo(ex2, ey2);
  ctx.closePath();
  ctx.clip();
  ctx.transform(m11, m12, m21, m22, dx, dy);
  ctx.drawImage(img, 0, 0);
  ctx.restore();
}}

function drawWarpedImage(img, quad, subdivisions) {{
  const N = subdivisions || 8;
  const iw = img.width;
  const ih = img.height;
  const bilerp = (u, v) => {{
    const topX = quad.tl.x + (quad.tr.x - quad.tl.x) * u;
    const topY = quad.tl.y + (quad.tr.y - quad.tl.y) * u;
    const botX = quad.bl.x + (quad.br.x - quad.bl.x) * u;
    const botY = quad.bl.y + (quad.br.y - quad.bl.y) * u;
    return {{
      x: topX + (botX - topX) * v,
      y: topY + (botY - topY) * v
    }};
  }};
  for (let i = 0; i < N; i++) {{
    const u0 = i / N, u1 = (i + 1) / N;
    const su0 = u0 * iw, su1 = u1 * iw;
    for (let j = 0; j < N; j++) {{
      const v0 = j / N, v1 = (j + 1) / N;
      const sv0 = v0 * ih, sv1 = v1 * ih;
      const p00 = bilerp(u0, v0);
      const p10 = bilerp(u1, v0);
      const p11 = bilerp(u1, v1);
      const p01 = bilerp(u0, v1);
      drawTexturedTriangle(img, su0, sv0, su1, sv0, su1, sv1, p00.x, p00.y, p10.x, p10.y, p11.x, p11.y);
      drawTexturedTriangle(img, su0, sv0, su1, sv1, su0, sv1, p00.x, p00.y, p11.x, p11.y, p01.x, p01.y);
    }}
  }}
}}

function getBgEdgeMidpoints(q) {{
  return {{
    t: {{ x: (q.tl.x + q.tr.x) / 2, y: (q.tl.y + q.tr.y) / 2 }},
    r: {{ x: (q.tr.x + q.br.x) / 2, y: (q.tr.y + q.br.y) / 2 }},
    b: {{ x: (q.bl.x + q.br.x) / 2, y: (q.bl.y + q.br.y) / 2 }},
    l: {{ x: (q.tl.x + q.bl.x) / 2, y: (q.tl.y + q.bl.y) / 2 }}
  }};
}}

function drawBgEditOverlay() {{
  if (isExporting || currentTool !== 'bg_edit') return;
  const active = getActiveBgPhoto();
  if (!active || !active.quad) return;

  // Marc subtil per a la resta de fotos inactives (per poder-les tocar i seleccionar)
  bgPhotos.forEach((p, idx) => {{
    if (idx === activeBgIdx || !p.quad) return;
    const pq = p.quad;
    ctx.save();
    ctx.strokeStyle = 'rgba(100, 116, 139, 0.55)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pq.tl.x, pq.tl.y);
    ctx.lineTo(pq.tr.x, pq.tr.y);
    ctx.lineTo(pq.br.x, pq.br.y);
    ctx.lineTo(pq.bl.x, pq.bl.y);
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }});

  const q = active.quad;
  ctx.save();
  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.moveTo(q.tl.x, q.tl.y);
  ctx.lineTo(q.tr.x, q.tr.y);
  ctx.lineTo(q.br.x, q.br.y);
  ctx.lineTo(q.bl.x, q.bl.y);
  ctx.closePath();
  ctx.stroke();
  ctx.setLineDash([]);

  // Punts mitjans de costats (per estirar costats)
  const mids = getBgEdgeMidpoints(q);
  for (const k of ['t', 'r', 'b', 'l']) {{
    const p = mids[k];
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 2;
    ctx.fillRect(p.x - 6, p.y - 6, 12, 12);
    ctx.strokeRect(p.x - 6, p.y - 6, 12, 12);
  }}

  // 4 cantonades (per deformar lliurement)
  for (const k of ['tl', 'tr', 'br', 'bl']) {{
    const p = q[k];
    ctx.beginPath();
    ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);
    ctx.fillStyle = '#2563eb';
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();
  }}
  ctx.restore();
}}

function drawAll() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 1. Dibuixar totes les fotos de fons (amb deformació lliure 4 cantonades)
  for (let i = 0; i < bgPhotos.length; i++) {{
    const p = bgPhotos[i];
    if (!p || !p.img) continue;
    if (!p.quad) p.quad = createBgQuad(p.img, i);
    ctx.save();
    ctx.globalAlpha = (p.opacity ?? 60) / 100;
    drawWarpedImage(p.img, p.quad, 8);
    ctx.restore();
  }}
  
  // 2. Graella
  drawGrid();
  
  // 3. Elements (només si el dibuix és visible)
  if (showDrawing) {{
    for (const el of elements) {{
      drawElement(el);
    }}
  }}

  // 4. Overlay d'edició/deformació de foto de fons
  drawBgEditOverlay();

  // 5. Overlay de corba pendent (Pas 2: ajustar curvatura)
  if (showDrawing && pendingCurve) {{
    ctx.save();
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 6;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(pendingCurve.x1, pendingCurve.y1);
    ctx.quadraticCurveTo(pendingCurve.cx, pendingCurve.cy, pendingCurve.x2, pendingCurve.y2);
    ctx.stroke();

    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pendingCurve.x1, pendingCurve.y1);
    ctx.lineTo(pendingCurve.cx, pendingCurve.cy);
    ctx.lineTo(pendingCurve.x2, pendingCurve.y2);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.beginPath();
    ctx.arc(pendingCurve.cx, pendingCurve.cy, 10, 0, Math.PI * 2);
    ctx.fillStyle = '#10b981';
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#ffffff';
    ctx.stroke();
    ctx.restore();
  }}

  // 4. Indicador visual del punt d'ancoratge per a la propera paret (Mode continu)
  if (showDrawing && isContinuous && currentTool === 'wall' && lastWallEnd && !isDrawing) {{
    ctx.save();
    // Halo verd maragda
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 3;
    ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
    ctx.beginPath();
    ctx.arc(lastWallEnd.x, lastWallEnd.y, 11, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Etiqueta flotant "🔗 Propera paret"
    ctx.font = 'bold 11px sans-serif';
    const tag = "🔗 Propera paret";
    const tw = ctx.measureText(tag).width;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
    ctx.fillRect(lastWallEnd.x - tw/2 - 4, lastWallEnd.y - 25, tw + 8, 16);
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(tag, lastWallEnd.x, lastWallEnd.y - 17);
    ctx.restore();
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
  }} else if (el.type === 'line') {{
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(el.x1, el.y1);
    ctx.lineTo(el.x2, el.y2);
    ctx.stroke();
  }} else if (el.type === 'curve') {{
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 6;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(el.x1, el.y1);
    ctx.quadraticCurveTo(el.cx, el.cy, el.x2, el.y2);
    ctx.stroke();
  }} else if (el.type === 'rect') {{
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 4;
    
    if (el.texture && el.texture !== 'none') {{
      const pat = getPattern(el.texture);
      ctx.fillStyle = pat ? pat : 'rgba(241, 245, 249, 0.45)';
    }} else {{
      ctx.fillStyle = 'rgba(241, 245, 249, 0.45)';
    }}

    ctx.beginPath();
    ctx.rect(el.x, el.y, el.w, el.h);
    ctx.fill();
    ctx.stroke();

    if (el.label) {{
      ctx.font = 'bold 13px sans-serif';
      const txt = el.label;
      const tw = ctx.measureText(txt).width;
      const cx = el.x + el.w / 2;
      const cy = el.y + el.h / 2;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.fillRect(cx - tw / 2 - 6, cy - 11, tw + 12, 22);
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 1;
      ctx.strokeRect(cx - tw / 2 - 6, cy - 11, tw + 12, 22);
      ctx.fillStyle = '#0f172a';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(txt, cx, cy);
    }}
  }} else if (el.type === 'dim') {{
    const isParetCota = el.isWall || false;
    ctx.strokeStyle = isParetCota ? '#0284c7' : '#2563eb';
    ctx.fillStyle = isParetCota ? '#0284c7' : '#2563eb';
    ctx.lineWidth = 2.5;
    
    // Línia principal
    ctx.beginPath();
    ctx.moveTo(el.x1, el.y1);
    ctx.lineTo(el.x2, el.y2);
    ctx.stroke();
    
    // Ticks transversals
    const angle = Math.atan2(el.y2 - el.y1, el.x2 - el.x1);
    const tickLen = 7;
    ctx.beginPath();
    ctx.moveTo(el.x1 - Math.sin(angle)*tickLen, el.y1 + Math.cos(angle)*tickLen);
    ctx.lineTo(el.x1 + Math.sin(angle)*tickLen, el.y1 - Math.cos(angle)*tickLen);
    ctx.moveTo(el.x2 - Math.sin(angle)*tickLen, el.y2 + Math.cos(angle)*tickLen);
    ctx.lineTo(el.x2 + Math.sin(angle)*tickLen, el.y2 - Math.cos(angle)*tickLen);
    ctx.stroke();
    
    // Text de mida amb fons protector per a fotos de paret
    const midX = (el.x1 + el.x2) / 2;
    const midY = (el.y1 + el.y2) / 2;
    ctx.font = 'bold 13px sans-serif';
    
    const txt = el.text || '';
    const tw = ctx.measureText(txt).width;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.fillRect(midX - tw/2 - 4, midY - 14, tw + 8, 16);
    
    ctx.fillStyle = isParetCota ? '#0369a1' : '#1d4ed8';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(txt, midX, midY - 1);
  }} else if (el.type === 'text') {{
    ctx.font = 'bold 14px sans-serif';
    const txt = el.text || '';
    const tw = ctx.measureText(txt).width;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.fillRect(el.x - 3, el.y - 10, tw + 6, 18);
    
    ctx.fillStyle = '#0f172a';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(txt, el.x, el.y);
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

function pointInQuad(px, py, q) {{
  const pts = [q.tl, q.tr, q.br, q.bl];
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {{
    const xi = pts[i].x, yi = pts[i].y;
    const xj = pts[j].x, yj = pts[j].y;
    const intersect = ((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / ((yj - yi) || 1e-6) + xi);
    if (intersect) inside = !inside;
  }}
  return inside;
}}

// ESDEVENIMENTS TÀCTILS I RATOLÍ UNIFICATS (Pointer Events)
canvas.addEventListener('pointerdown', (e) => {{
  e.preventDefault();

  // Eina Ajustar / Deformar Foto de fons (suporta múltiples fotos)
  if (currentTool === 'bg_edit' && bgPhotos.length > 0) {{
    const c = getPointerCoords(e);
    const rx = c.rawX, ry = c.rawY;
    const active = getActiveBgPhoto();
    if (active && active.quad) {{
      const q = active.quad;
      for (const k of ['tl', 'tr', 'br', 'bl']) {{
        if (Math.hypot(q[k].x - rx, q[k].y - ry) <= 24) {{
          bgDragState = {{ mode: k, lastX: rx, lastY: ry }};
          try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
          return;
        }}
      }}
      const mids = getBgEdgeMidpoints(q);
      for (const k of ['t', 'r', 'b', 'l']) {{
        if (Math.hypot(mids[k].x - rx, mids[k].y - ry) <= 22) {{
          bgDragState = {{ mode: k, lastX: rx, lastY: ry }};
          try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
          return;
        }}
      }}
      if (pointInQuad(rx, ry, q)) {{
        bgDragState = {{ mode: 'move', lastX: rx, lastY: ry }};
        try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
        return;
      }}
    }}
    // Si toquem dins d'una altra foto de fons, la seleccionem automàticament
    for (let i = bgPhotos.length - 1; i >= 0; i--) {{
      if (i === activeBgIdx) continue;
      const p = bgPhotos[i];
      if (p && p.quad && pointInQuad(rx, ry, p.quad)) {{
        activeBgIdx = i;
        updateBgControlsUI();
        drawAll();
        bgDragState = {{ mode: 'move', lastX: rx, lastY: ry }};
        try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
        return;
      }}
    }}
    return;
  }}

  // Eina Pan / Moure plànol
  if (currentTool === 'pan') {{
    isPanning = true;
    panStartX = e.clientX;
    panStartY = e.clientY;
    scrollStartLeft = canvasWrapper.scrollLeft;
    scrollStartTop = canvasWrapper.scrollTop;
    canvas.classList.add('grabbing');
    try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  // Si no és eina pan, garantir que isPanning està apagat
  isPanning = false;
  canvas.classList.remove('grabbing');

  const c = getPointerCoords(e);
  
  if (currentTool === 'text') {{
    const isParet = (currentViewMode === 'paret');
    const presetsTxt = isParet
      ? ["Forat / Clivella", "Ciment cola", "Calç", "Pintura antihumitat", "Sòcol", "Rajola", "Finestra", "Aixeta", "Endoll"]
      : ["Bany", "Dutxa", "Moble lavabo", "Porta", "Paret mestra", "Finestra"];
    
    showInputModal(
      isParet ? "Etiqueta o detall de la paret:" : "Etiqueta de l'espai o estança:",
      presetsTxt,
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
    if (currentTool === 'curve' && pendingCurve) {{
    isDrawing = true;
    pendingCurve.cx = c.rawX;
    pendingCurve.cy = c.rawY;
    drawAll();
    try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  isDrawing = true;
    eraseAt(c.rawX, c.rawY);
    try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  if (currentTool === 'bucket') {{
    const clickedRect = [...elements].reverse().find(el => el.type === 'rect' && (
      c.rawX >= el.x && c.rawX <= el.x + el.w &&
      c.rawY >= el.y && c.rawY <= el.y + el.h
    ));
    if (clickedRect) {{
      saveHistory();
      clickedRect.texture = selectedTexture;
      drawAll();
      const status = document.getElementById('toolStatus');
      if (status) status.innerText = `✅ Textura '${{selectedTextureName || selectedTexture}}' aplicada correctament!`;
      return;
    }}
    if (currentTool === 'curve' && pendingCurve) {{
    isDrawing = true;
    pendingCurve.cx = c.rawX;
    pendingCurve.cy = c.rawY;
    drawAll();
    try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  isDrawing = true;
    startX = c.x;
    startY = c.y;
    try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}
  
  if (currentTool === 'curve' && pendingCurve) {{
    isDrawing = true;
    pendingCurve.cx = c.rawX;
    pendingCurve.cy = c.rawY;
    drawAll();
    try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  isDrawing = true;

  // Si estem traçant paret contínua i tenim un extrem anterior guardat
  if (currentTool === 'wall' && isContinuous && lastWallEnd) {{
    startX = lastWallEnd.x;
    startY = lastWallEnd.y;
  }} else {{
    startX = c.x;
    startY = c.y;
  }}

  try {{ canvas.setPointerCapture(e.pointerId); }} catch(err) {{}}
}});

canvas.addEventListener('pointermove', (e) => {{
  const activeBg = getActiveBgPhoto();
  if (currentTool === 'bg_edit' && bgDragState && activeBg && activeBg.quad) {{
    e.preventDefault();
    const q = activeBg.quad;
    const c = getPointerCoords(e);
    const rx = c.rawX, ry = c.rawY;
    const dx = rx - bgDragState.lastX;
    const dy = ry - bgDragState.lastY;
    bgDragState.lastX = rx;
    bgDragState.lastY = ry;
    const m = bgDragState.mode;
    if (['tl', 'tr', 'br', 'bl'].includes(m)) {{
      q[m].x = rx;
      q[m].y = ry;
    }} else if (m === 't') {{
      q.tl.x += dx; q.tl.y += dy;
      q.tr.x += dx; q.tr.y += dy;
    }} else if (m === 'b') {{
      q.bl.x += dx; q.bl.y += dy;
      q.br.x += dx; q.br.y += dy;
    }} else if (m === 'l') {{
      q.tl.x += dx; q.tl.y += dy;
      q.bl.x += dx; q.bl.y += dy;
    }} else if (m === 'r') {{
      q.tr.x += dx; q.tr.y += dy;
      q.br.x += dx; q.br.y += dy;
    }} else if (m === 'move') {{
      for (const k of ['tl', 'tr', 'br', 'bl']) {{
        q[k].x += dx;
        q[k].y += dy;
      }}
    }}
    drawAll();
    return;
  }}

  if (isPanning && currentTool === 'pan') {{
    e.preventDefault();
    const dx = e.clientX - panStartX;
    const dy = e.clientY - panStartY;
    canvasWrapper.scrollLeft = scrollStartLeft - dx;
    canvasWrapper.scrollTop = scrollStartTop - dy;
    return;
  }}

  if (currentTool === 'eraser') {{
    if (isDrawing) {{
      const c = getPointerCoords(e);
      eraseAt(c.rawX, c.rawY);
    }}
    return;
  }}

  if (currentTool === 'pan' || !isDrawing) return;
  e.preventDefault();
  const c = getPointerCoords(e);
  const currX = c.x;
  const currY = c.y;
  
  if (currentTool === 'curve' && pendingCurve) {{
    pendingCurve.cx = c.rawX;
    pendingCurve.cy = c.rawY;
    drawAll();
    return;
  }}

  drawAll();
  
  // Previsualització en curs
  ctx.save();
  ctx.strokeStyle = '#94a3b8';
  ctx.setLineDash([4, 4]);
  if (currentTool === 'wall' || currentTool === 'line' || currentTool === 'curve') {{
    ctx.lineWidth = currentTool === 'line' ? 2.5 : 6;
    ctx.strokeStyle = currentTool === 'curve' ? '#2563eb' : '#0f172a';
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(currX, currY);
    ctx.stroke();

    // Mida dinàmica en metres durant el traç
    const pxLen = Math.hypot(currX - startX, currY - startY);
    if (pxLen > 10) {{
      const mLen = (pxLen / 40).toFixed(2) + " m";
      const midX = (startX + currX) / 2;
      const midY = (startY + currY) / 2;
      ctx.font = 'bold 12px sans-serif';
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      const tw = ctx.measureText(mLen).width;
      ctx.fillRect(midX - tw/2 - 4, midY - 10, tw + 8, 16);
      ctx.fillStyle = '#1e293b';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(mLen, midX, midY - 2);
    }}
  }} else if (currentTool === 'rect' || currentTool === 'bucket') {{
    ctx.lineWidth = 2;
    if (currentTool === 'bucket' && selectedTexture && selectedTexture !== 'none') {{
      const pat = getPattern(selectedTexture);
      if (pat) {{
        ctx.fillStyle = pat;
        ctx.fillRect(startX, startY, currX - startX, currY - startY);
      }}
    }}
    ctx.strokeRect(startX, startY, currX - startX, currY - startY);
  }} else if (currentTool === 'dim') {{
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(currX, currY);
    ctx.stroke();
  }}

  // Si està enganxat a un vèrtex magnètic existent
  if (c.isSnapped) {{
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2.5;
    ctx.fillStyle = 'rgba(16, 185, 129, 0.45)';
    ctx.beginPath();
    ctx.arc(currX, currY, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    // Creueta central
    ctx.beginPath();
    ctx.moveTo(currX - 12, currY);
    ctx.lineTo(currX + 12, currY);
    ctx.moveTo(currX, currY - 12);
    ctx.lineTo(currX, currY + 12);
    ctx.stroke();
  }}
  ctx.restore();
}});

canvas.addEventListener('pointerup', (e) => {{
  if (currentTool === 'bg_edit' && bgDragState) {{
    bgDragState = null;
    try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  if (isPanning || currentTool === 'pan') {{
    isPanning = false;
    canvas.classList.remove('grabbing');
    try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  if (currentTool === 'eraser') {{
    isDrawing = false;
    try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
    return;
  }}

  if (!isDrawing) return;
  e.preventDefault();
  isDrawing = false;
  try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
  
  const c = getPointerCoords(e);
  const endX = c.x;
  const endY = c.y;

  if (currentTool === 'curve' && pendingCurve) {{
    pendingCurve.cx = c.rawX;
    pendingCurve.cy = c.rawY;
    saveHistory();
    elements.push({{
      type: 'curve',
      x1: pendingCurve.x1,
      y1: pendingCurve.y1,
      cx: pendingCurve.cx,
      cy: pendingCurve.cy,
      x2: pendingCurve.x2,
      y2: pendingCurve.y2
    }});
    pendingCurve = null;
    drawAll();
    const status = document.getElementById('toolStatus');
    if (status) status.innerText = "👉 Corba afegida! Arrossega per traçar una altra corba.";
    return;
  }}
  
  if (startX === endX && startY === endY) return;
  
  if (currentTool === 'curve') {{
    pendingCurve = {{
      x1: startX,
      y1: startY,
      x2: endX,
      y2: endY,
      cx: (startX + endX) / 2,
      cy: (startY + endY) / 2
    }};
    drawAll();
    const status = document.getElementById('toolStatus');
    if (status) status.innerText = "👉 Corba (Pas 2/2): Toca o arrossega on vulguis corbar la línia!";
    return;
  }}

  saveHistory();
  
  if (currentTool === 'wall') {{
    elements.push({{ type: 'wall', x1: startX, y1: startY, x2: endX, y2: endY }});
    if (isContinuous) {{
      lastWallEnd = {{ x: endX, y: endY }};
      updateContinuousUI();
    }}
    drawAll();
  }} else if (currentTool === 'line') {{
    elements.push({{ type: 'line', x1: startX, y1: startY, x2: endX, y2: endY }});
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
  }} else if (currentTool === 'bucket') {{
    const rw = Math.abs(endX - startX);
    const rh = Math.abs(endY - startY);
    if (rw >= 10 && rh >= 10) {{
      elements.push({{
        type: 'rect',
        x: Math.min(startX, endX),
        y: Math.min(startY, endY),
        w: rw,
        h: rh,
        texture: selectedTexture
      }});
      drawAll();
    }}
  }} else if (currentTool === 'dim') {{
    const pxDist = Math.hypot(endX - startX, endY - startY);
    const mDist = (pxDist / 40).toFixed(2);
    const isParet = (currentViewMode === 'paret');
    const isVertical = Math.abs(endY - startY) > Math.abs(endX - startX);
    
    let modalTitle = "Indica la mesura de la cota (Terra / Planta):";
    let modalPresets = [mDist + " m", "1,00 m", "1,50 m", "2,00 m", "2,50 m", "3,00 m", "4,00 m"];
    let defaultVal = mDist + " m";
    
    if (isParet) {{
      if (isVertical) {{
        modalTitle = "📐 Alçada de la Paret (Cota vertical):";
        modalPresets = ["Alt: " + mDist + " m", "Alt: 2,50 m (Sostre)", "Alt: 2,20 m", "Alt: 1,80 m (Dutxa)", "Alt: 1,20 m (Sòcol)", "Alt: 0,90 m (Lavabo)"];
        defaultVal = "Alt: " + mDist + " m";
      }} else {{
        modalTitle = "📐 Amplada de la Paret (Cota horitzontal):";
        modalPresets = ["Ampl: " + mDist + " m", "Ampl: 1,00 m", "Ampl: 1,50 m", "Ampl: 2,00 m", "Ampl: 2,50 m", "Ampl: 3,00 m", "Ampl: 4,00 m"];
        defaultVal = "Ampl: " + mDist + " m";
      }}
    }}
    
    showInputModal(
      modalTitle,
      modalPresets,
      defaultVal,
      (userM) => {{
        elements.push({{
          type: 'dim',
          x1: startX,
          y1: startY,
          x2: endX,
          y2: endY,
          text: userM || defaultVal,
          isWall: isParet
        }});
        drawAll();
      }}
    );
  }}
}});

canvas.addEventListener('pointercancel', (e) => {{
  if (isPanning) {{
    isPanning = false;
    canvas.classList.remove('grabbing');
    try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
  }}
  isDrawing = false;
  drawAll();
}});

// Seguretat global: alliberar arrossegament i esborrat fins i tot si el dit s'aixeca fora del canvas
window.addEventListener('pointerup', (e) => {{
  if (isPanning) {{
    isPanning = false;
    canvas.classList.remove('grabbing');
    try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
  }}
  isDrawing = false;
}});

window.addEventListener('pointercancel', (e) => {{
  if (isPanning) {{
    isPanning = false;
    canvas.classList.remove('grabbing');
    try {{ canvas.releasePointerCapture(e.pointerId); }} catch(err) {{}}
  }}
  isDrawing = false;
}});

function loadBgImage(e) {{
  const files = Array.from(e.target.files || []);
  if (files.length === 0) return;
  const defaultOpacity = parseInt(bgOpacityInput.value, 10) || 60;
  files.forEach((file) => {{
    const reader = new FileReader();
    reader.onload = (event) => {{
      const img = new Image();
      img.onload = () => {{
        const idx = bgPhotos.length;
        bgPhotos.push({{
          id: Date.now() + idx,
          name: `Foto ${{idx + 1}}`,
          img: img,
          quad: createBgQuad(img, idx),
          opacity: defaultOpacity
        }});
        activeBgIdx = bgPhotos.length - 1;
        updateBgControlsUI();
        setTool('bg_edit');
        drawAll();
      }};
      img.src = event.target.result;
    }};
    reader.readAsDataURL(file);
  }});
  e.target.value = '';
}}

function clearCanvas() {{
  if (confirm("Vols buidar tot el plànol dibuixat?")) {{
    saveHistory();
    elements = [];
    lastWallEnd = null;
    updateContinuousUI();
    drawAll();
  }}
}}

function downloadImage() {{
  isExporting = true;
  drawAll();
  const dataURL = canvas.toDataURL('image/png');
  isExporting = false;
  drawAll();
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

@st.dialog("📷 Fotografia de l'Obra")
def dialog_veure_foto_gran(foto_path: str, titol: str, descripcio: str = ""):
    """Finestra modal per veure la fotografia a mida completa."""
    st.markdown(f"### {titol}")
    if foto_path:
        st.image(decode_image_for_st(foto_path), width="stretch")
    if descripcio:
        st.info(descripcio)

def render_planol_tab(projecte: Dict[str, Any]):
    """Renderitza les 3 pestanyes de l'Editor Gràfic (Plànol, Disseny MD, Esquemes Elèctrics) i la Galeria de Fotos."""
    if st.session_state.get("foto_toast_msg"):
        st.toast(st.session_state.pop("foto_toast_msg"), icon="✅")

    project_id = projecte.get("id", "nou")
    planol_info = projecte.get("planol", {})
    preview_png = planol_info.get("preview_png")
    bg_b64 = planol_info.get("background_image", "")

    st.markdown("### 📐 Editors Gràfics, Disseny i Fotos de l'Obra")
    ed_tab_planol, ed_tab_moble, ed_tab_elec = st.tabs([
        "📐 Editor Gràfic de Plànol",
        "🪚 Disseny & Despecejament MD",
        "⚡ Esquemes Elèctrics",
    ])

    with ed_tab_planol:
        st.markdown("#### 📐 Plànol i Croquis de l'Obra")
        st.caption("Dibuixa parets, habitacions i cotes amb mides en metres, o carrega una foto real de l'estança per utilitzar-la com a fons.")

        # Guia d'ús desplegable integrada al projecte
        with st.expander("📖 Guia d'Ús: Com funciona l'editor de plànols?", expanded=False):
            st.info("""📱 **Com utilitzar-lo al mòbil (tacte directe):**
- **🧱 Paret / 🔗 Seguir traç:** Arrossega el dit per fer la primera paret. Les següents s'enllaçaran automàticament des de l'última cantonada (ideal per dibuixar habitacions senceres sense buscar on continua).
- **🧲 Snap Magnètic:** En acostar el dit a qualsevol cantonada o extrem, s'activa un imant verd (`🟢`) que fixa la posició exacta i permet tancar l'habitació a la perfecció.
- **🖐️ Moure:** Activa aquesta eina per desplaçar el plànol lliurement amb el dit quan hagis ampliat la vista amb zoom.
- **🔍 Controls de Zoom:** Prem `🔍+`, `🔍-` o `100%` per apropar detalls o veure tota l'estança.
- **📏 Cota:** Arrossega d'un extrem a l'altre per indicar mides en metres (a paret detecta alçades com sostre, dutxa o sòcols).
- **🔤 Text:** Toca sobre l'estança o paret per posar etiquetes d'obra (*Bany, Forat, Ciment cola, Sòcol*).
- **📷 Foto de fons i 🖼️ Ajustar Foto:** Carrega una foto real, ajusta'n l'opacitat i activa **🖼️ Ajustar Foto** per moure-la, estirar-la o deformar-ne lliurement les 4 cantonades en perspectiva.
- **〰️ Corba:** Arrossega d'un extrem a l'altre i després toca o arrossega el punt verd central per donar-li la curvatura desitjada.
- **↩️ Desfer:** Elimina el darrer traç si t'has equivocat.
""")
            st.markdown("""
            #### 📋 Guia d'eines pas a pas

            1. **🧱 Paret i 🔗 Mode Continu (Habitacions fàcils):**
               - Amb el botó **`🔗 Seguir: SÍ`** actiu, traça la primera paret.
               - Veuràs un cercle maragda marcat com a *'Propera paret'*. Per fer la segona paret de l'habitació, només cal que toquis o arrosseguis cap a la següent cantonada: s'iniciarà automàticament des de l'extrem anterior!
               - Quan arribis a l'inici per tancar l'habitació, l'**imant magnètic (`🟢`)** s'ajustarà a la cantonada inicial.
               - Si vols dibuixar una paret separada en un altre lloc, prem **`⏹️ Desconnectar`**.

            2. **🖐️ Moure el plànol:**
               - Toca **`🖐️ Moure`**. Ara pots arrossegar el dit o el ratolí en qualsevol direcció per navegar còmodament pel plànol ampliat sense perill de dibuixar línies accidentals.

            3. **🔲 Espai / Habitació rectangular:**
               - Toca **`🔲 Espai`** i arrossega en diagonal per crear una estança o moble rectangular d'un sol cop.

            4. **📏 Cota (mesures en metres):**
               - Toca **`📏 Cota`** i arrossega d'un extrem a l'altre.
               - En *Mode Planta* ofereix mides de terra; en *Mode Alçat* detecta si és alçada (sostre, sòcol) o amplada amb fons blanc d'alta visibilitat.

            5. **🔤 Text:**
               - Toca sobre qualsevol punt per col·locar noms d'habitació o anotacions d'obra de paret.

            6. **🧹 Goma d'esborrar i ↩️ Desfer:**
               - Toca **`🧹 Goma`** per esborrar línies o **`↩️ Desfer`** per anul·lar l'últim moviment.

            7. **📷 Foto de fons:**
               - Prem **`📷 Foto fons`** i ajusta l'**Opacitat** per calcar un plànol real o croquis en paper.

            8. **💾 Desar al Projecte:**
               - Prem **`💾 Descarregar PNG`** i guarda la imatge resultant al formulari inferior com a Plànol Oficial del projecte.
            """)

        # Vista prèvia actual si existeix
        if preview_png:
            st.markdown("**Plànol oficial desat per a aquest projecte:**")
            st.image(decode_image_for_st(preview_png), width="stretch")
            data_act = planol_info.get("data_actualitzacio", "")
            if data_act:
                st.caption(f"Darrera actualització del plànol: {data_act}")

        # Editor interactiu Canvas (sempre col·lapsat per defecte)
        with st.expander("✏️ Obrir Editor Gràfic de Plànol (Canvas)", expanded=False):
            html_code = get_canvas_html(project_id, existing_bg_b64=bg_b64)
            components.html(html_code, height=650, scrolling=False)

        # Selector per desar el plànol oficial
        with st.form(f"form_save_planol_{project_id}", clear_on_submit=True):
            st.markdown("**💾 Desar o Actualitzar Plànol al Projecte**")
            up_file = st.file_uploader(
                "Selecciona la imatge del plànol (PNG generat per l'editor o foto d'un croquis físic):",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"up_planol_{project_id}"
            )
            sub_planol = st.form_submit_button("Guardar Plànol Oficial", type="primary")
            if sub_planol and up_file:
                b64_data = compress_image_b64(up_file, max_dim=1280, quality=80)
                if save_planol_projecte(project_id, preview_png=b64_data):
                    st.session_state["foto_toast_msg"] = "Plànol oficial desat correctament!"
                    st.rerun()

    with ed_tab_moble:
        from modules.moble_disseny_ui import render_disseny_moble_tab
        render_disseny_moble_tab(projecte)

    with ed_tab_elec:
        from modules.canvas_electric import render_esquema_electric_tab
        render_esquema_electric_tab(projecte)

    st.markdown("---")

    # Galeria Fotogràfica de Seguiment
    st.markdown("### 📷 Galeria Fotogràfica de l'Obra")
    st.caption("Fes fotos del progrés de l'obra per documentar l'estat inicial (*Abans*), l'evolució (*Durant*) i el resultat final (*Després*).")

    # Panell de vista ampliada d'alta definició (segur, sense tel gris ni tancaments)
    zoom_key = f"active_zoom_foto_{project_id}"
    active_zoom = st.session_state.get(zoom_key)
    if active_zoom:
        with st.container(border=True):
            cz_h, cz_close = st.columns([3, 1])
            with cz_h:
                st.markdown(f"#### 🔍 Vista Ampliada: {active_zoom.get('titol', 'Fotografia')}")
            with cz_close:
                if st.button("❌ Tancar", key=f"btn_close_zoom_{project_id}", use_container_width=True):
                    st.session_state.pop(zoom_key, None)
                    st.rerun()
            if active_zoom.get("path"):
                st.image(decode_image_for_st(active_zoom["path"]), width="stretch")
            if active_zoom.get("desc"):
                st.info(active_zoom["desc"])

    fotos = projecte.get("fotos", [])
    edit_foto_key = f"editing_foto_{project_id}"
    active_edit_id = st.session_state.get(edit_foto_key)
    if active_edit_id and fotos:
        foto_obj = next((x for x in fotos if x.get("id") == active_edit_id), None)
        if foto_obj:
            with st.container(border=True):
                st.markdown("#### ✏️ Canviar / Editar Fotografia Pujada")
                with st.form(f"form_edit_foto_{project_id}_{active_edit_id}"):
                    ef_c1, ef_c2 = st.columns([1, 2])
                    tipus_opts = ["abans", "durant", "despres", "altre"]
                    cur_tip = foto_obj.get("tipus", "altre")
                    with ef_c1:
                        new_tipus = st.selectbox(
                            "Fase:",
                            tipus_opts,
                            index=tipus_opts.index(cur_tip) if cur_tip in tipus_opts else 3,
                            format_func=lambda x: {"abans": "🔴 Abans", "durant": "🟡 Durant", "despres": "🟢 Resultat", "altre": "⚪ Altre"}[x],
                        )
                    with ef_c2:
                        new_desc = st.text_input("Descripció:", value=foto_obj.get("descripcio", ""))
                    new_file = st.file_uploader(
                        "Substituir per una nova foto (opcional):",
                        type=["jpg", "jpeg", "png", "webp", "jfif", "bmp"],
                        key=f"replace_foto_file_{project_id}_{active_edit_id}",
                    )
                    sb1, sb2 = st.columns(2)
                    with sb1:
                        save_ed = st.form_submit_button("💾 Desar canvis", type="primary", use_container_width=True)
                    with sb2:
                        cancel_ed = st.form_submit_button("Cancel·lar", use_container_width=True)

                    if cancel_ed:
                        st.session_state.pop(edit_foto_key, None)
                        st.rerun()
                    if save_ed:
                        payload_img = new_file.getvalue() if new_file is not None else None
                        if update_projecte_foto(
                            project_id,
                            active_edit_id,
                            tipus=new_tipus,
                            descripcio=new_desc.strip(),
                            new_data_url_or_path=payload_img,
                        ):
                            st.session_state.pop(edit_foto_key, None)
                            if active_zoom and active_zoom.get("path") == foto_obj.get("path"):
                                st.session_state.pop(zoom_key, None)
                            st.success("Fotografia actualitzada!")
                            st.rerun()
                        else:
                            st.error("No s'ha pogut actualitzar la fotografia.")

    if fotos:
        num_cols = 4  # 4 columnes per fila per una mida compacta i equilibrada
        rows = [fotos[i:i + num_cols] for i in range(0, len(fotos), num_cols)]
        for r_idx, row in enumerate(rows):
            cols = st.columns(num_cols)
            for idx, f in enumerate(row):
                col = cols[idx]
                with col:
                    with st.container(border=True):
                        tipus_badge = {
                            "abans": "🔴 Abans",
                            "durant": "🟡 Durant",
                            "despres": "🟢 Resultat",
                            "altre": "⚪ Foto"
                        }.get(f.get("tipus", "altre"), "⚪ Foto")
                        
                        f_path = f.get("path")
                        f_data = f.get("data", "")
                        f_desc = f.get("descripcio", "")
                        f_id = f.get("id", f"{r_idx}_{idx}")

                        # Miniatura de la fotografia de l'obra (descodificada a bytes reals per st.image)
                        img_obj = decode_image_for_st(f_path)
                        if img_obj:
                            st.image(img_obj, width="stretch")
                        else:
                            st.markdown(
                                """
                                <div style="width: 100%; height: 180px; display: flex; align-items: center; justify-content: center; background: #1e293b; border-radius: 6px; font-size: 32px; margin-bottom: 4px;">
                                    📷
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        st.caption(f"**{tipus_badge}** · *{f_data}*")
                        if f_desc:
                            st.caption(f_desc[:40] + ("…" if len(f_desc) > 40 else ""))

                        col_b1, col_b2, col_b3 = st.columns([1.2, 0.7, 0.7])
                        with col_b1:
                            if st.button("🔍 Veure", key=f"zoom_foto_{project_id}_{f_id}_{r_idx}_{idx}", use_container_width=True, help="Veure foto a pantalla gran"):
                                st.session_state[zoom_key] = {
                                    "path": f_path,
                                    "titol": f"{tipus_badge} — {f_data}",
                                    "desc": f_desc
                                }
                                st.rerun()
                        with col_b2:
                            if st.button("✏️", key=f"edit_foto_{project_id}_{f_id}_{r_idx}_{idx}", use_container_width=True, help="Canviar foto, fase o descripció"):
                                st.session_state[edit_foto_key] = f.get("id")
                                st.rerun()
                        with col_b3:
                            if st.button("🗑️", key=f"del_foto_{project_id}_{f_id}_{r_idx}_{idx}", use_container_width=True, help="Eliminar aquesta foto"):
                                delete_projecte_foto(project_id, f.get("id"))
                                if active_zoom and active_zoom.get("path") == f_path:
                                    st.session_state.pop(zoom_key, None)
                                if active_edit_id == f.get("id"):
                                    st.session_state.pop(edit_foto_key, None)
                                st.rerun()
    else:
        st.info("Encara no s'ha afegit cap fotografia a aquest projecte.")

    with st.expander("➕ Afegir Nova Fotografia de l'Obra"):
        with st.form(f"form_add_foto_{project_id}", clear_on_submit=True):
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
            
            foto_files = st.file_uploader(
                "Carrega una o més fotos (mòbil o PC):",
                type=["jpg", "jpeg", "png", "webp", "jfif", "bmp"],
                accept_multiple_files=True,
                key=f"file_foto_{project_id}"
            )
            sub_foto = st.form_submit_button("Pujar Fotografia", type="primary")
            if sub_foto:
                if not foto_files:
                    st.warning("⚠️ Selecciona primer almenys una fotografia.")
                else:
                    saved_count = 0
                    with st.spinner("Comprimint i desant fotografia..."):
                        for ff in foto_files:
                            b64_foto = compress_image_b64(ff, max_dim=1280, quality=80)
                            if b64_foto and add_projecte_foto(project_id, tipus=tipus_foto, data_url_or_path=b64_foto, descripcio=desc_foto):
                                saved_count += 1
                    if saved_count > 0:
                        st.session_state["foto_toast_msg"] = f"S'ha{'n' if saved_count > 1 else ''} afegit {saved_count} fotografia{'es' if saved_count > 1 else ''} correctament!"
                        st.rerun()
                    else:
                        st.error("❌ No s'ha pogut processar o desar la fotografia al núvol.")
