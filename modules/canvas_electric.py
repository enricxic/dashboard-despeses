"""
modules/canvas_electric.py
Editor interactiu d'Esquemes Elèctrics per a projectes de la llar:
- 3 cables amb codi de colors normatiu: Negre (Fase L), Blau (Neutre N) i Groc/Verd (Terra PE).
- Elements elèctrics comuns: Bombeta, Endoll, Interruptor, Commutador, Magnetotèrmic (PIA),
  Diferencial (ID), Contactor, Termòstat, Caixa de registre i Quadre/IGA.
- Dibuix ortogonal a 90° o lliure, mode continu, snap magnètic a borns/extrems, rotació 90°,
  textos, foto de fons, desfer i exportació a PNG.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Any, Dict

from core.projectes_manager import (
    compress_image_b64,
    decode_image_for_st,
    save_esquema_electric_projecte,
)


def get_electric_canvas_html(project_id: str) -> str:
    """Genera el component HTML5 Canvas + JS per dibuixar esquemes elèctrics en PC i mòbil."""
    return f"""<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
  * {{
    box-sizing: border-box;
    user-select: none;
    -webkit-user-select: none;
  }}
  body {{
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f8fafc;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 100vh;
  }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 7px 10px;
    background: #ffffff;
    border-bottom: 1px solid #cbd5e1;
    align-items: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    z-index: 10;
  }}
  .toolbar-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
    width: 100%;
  }}
  .btn {{
    padding: 5px 9px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #ffffff;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.12s;
  }}
  .btn:hover {{ background: #f1f5f9; }}
  .btn.active {{
    background: #2563eb;
    color: #ffffff;
    border-color: #1d4ed8;
  }}
  .btn-wire-fase.active {{
    background: #111827;
    color: #ffffff;
    border-color: #000000;
  }}
  .btn-wire-neutre.active {{
    background: #2563eb;
    color: #ffffff;
    border-color: #1d4ed8;
  }}
  .btn-wire-terra {{
    border-color: #ca8a04;
  }}
  .btn-wire-terra.active {{
    background: #eab308;
    color: #111827;
    border-color: #854d0e;
  }}
  .btn-toggle-on {{
    background: #059669 !important;
    color: #ffffff !important;
    border-color: #047857 !important;
  }}
  .btn-danger {{ background: #fef2f2; color: #dc2626; border-color: #fecaca; }}
  .btn-undo {{ background: #fffbeb; color: #b45309; border-color: #fde68a; }}
  .btn-save {{ background: #16a34a; color: #ffffff; border-color: #15803d; }}
  .sep {{ height: 18px; width: 1px; background: #cbd5e1; margin: 0 2px; }}
  .swatch {{
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-block;
    border: 1px solid rgba(0,0,0,0.3);
  }}
  .canvas-container {{
    position: relative;
    flex: 1;
    overflow: hidden;
    background: #ffffff;
    background-image:
      linear-gradient(to right, #f1f5f9 1px, transparent 1px),
      linear-gradient(to bottom, #f1f5f9 1px, transparent 1px);
    background-size: 20px 20px;
    touch-action: none;
  }}
  canvas {{
    display: block;
    width: 100%;
    height: 100%;
    touch-action: none;
  }}
  .status-bar {{
    padding: 5px 12px;
    background: #0f172a;
    color: #f8fafc;
    font-size: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }}
  .badge-snap {{
    background: #10b981;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    display: none;
  }}
  .modal-overlay {{
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.65);
    z-index: 1000;
    justify-content: center;
    align-items: center;
    padding: 15px;
  }}
  .modal-box {{
    background: white;
    padding: 16px;
    border-radius: 12px;
    width: 100%;
    max-width: 340px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
    text-align: center;
  }}
  .modal-box h4 {{ margin: 0 0 10px 0; font-size: 15px; color: #0f172a; }}
  .modal-input {{
    width: 100%;
    padding: 9px;
    font-size: 15px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-bottom: 12px;
    text-align: center;
  }}
  .modal-actions {{ display: flex; gap: 8px; }}
  .modal-actions button {{
    flex: 1;
    padding: 9px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
    border: none;
    cursor: pointer;
  }}
</style>
</head>
<body>

<div class="toolbar">
  <!-- Fila 1: Cables (3 colors) + Mode traç + Eines generals -->
  <div class="toolbar-row">
    <span style="font-size:11px; font-weight:700; color:#475569;">CABLES:</span>
    <button class="btn btn-wire-fase active" id="btnWireFase" onclick="selectWire('fase')">
      <span class="swatch" style="background:#111827;"></span> Fase (Negre)
    </button>
    <button class="btn btn-wire-neutre" id="btnWireNeutre" onclick="selectWire('neutre')">
      <span class="swatch" style="background:#2563eb;"></span> Neutre (Blau)
    </button>
    <button class="btn btn-wire-terra" id="btnWireTerra" onclick="selectWire('terra')">
      <span class="swatch" style="background:linear-gradient(135deg,#facc15 50%,#16a34a 50%);"></span> Terra (Groc)
    </button>

    <div class="sep"></div>

    <button class="btn btn-toggle-on" id="btnOrtho" onclick="toggleOrtho()" title="Dibuixar cables en angle recte 90°">📐 90°: SÍ</button>
    <button class="btn btn-toggle-on" id="btnContinuous" onclick="toggleContinuous()" title="Continuar el cable des del darrer punt">🔗 Seguir: SÍ</button>
    <button class="btn" id="btnNewTrace" onclick="resetContinuous()" style="display:none; background:#fee2e2; color:#b91c1c; border-color:#fca5a5;">⏹️ Tallar cable</button>

    <div class="sep"></div>

    <button class="btn" id="btnSelect" onclick="setTool('select')" title="Seleccionar, moure o transformar la mida de qualsevol element"><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" style="vertical-align:-1px;"><path d="M3 1.5l10 6.5-4.3 1.2L11.5 14l-1.8.8-2.8-4.8L3 13V1.5z"/></svg> Seleccionar</button>
    <button class="btn" id="btnText" onclick="setTool('text')">🔤 Text</button>
    <button class="btn" id="btnEraser" onclick="setTool('eraser')">🧹 Goma</button>
    <button class="btn" id="btnPan" onclick="setTool('pan')" title="Desplaçar tota la vista del llenç">🖐️ Vista</button>
    <button class="btn" id="btnRotate" onclick="rotateActive()" title="Girar 90° l'element seleccionat o el proper">🔄 Girar (<span id="rotLbl">0°</span>)</button>
  </div>

  <!-- Fila 2: Elements elèctrics comuns + Zoom + Accions -->
  <div class="toolbar-row">
    <span style="font-size:11px; font-weight:700; color:#475569;">ELEMENTS:</span>
    <button class="btn" id="el_bulb" onclick="selectSymbol('bulb')">💡 Bombeta</button>
    <button class="btn" id="el_socket" onclick="selectSymbol('socket')">🔌 Endoll</button>
    <button class="btn" id="el_switch" onclick="selectSymbol('switch')">🔘 Interruptor</button>
    <button class="btn" id="el_commutator" onclick="selectSymbol('commutator')">🔀 Commutador</button>
    <button class="btn" id="el_mcb" onclick="selectSymbol('mcb')">⚡ Magnetotèrmic</button>
    <button class="btn" id="el_rcd" onclick="selectSymbol('rcd')">🛡️ Diferencial</button>
    <button class="btn" id="el_contactor" onclick="selectSymbol('contactor')">🧲 Contactor</button>
    <button class="btn" id="el_thermostat" onclick="selectSymbol('thermostat')">🌡️ Termòstat</button>
    <button class="btn" id="el_timer" onclick="selectSymbol('timer')">⏰ Programador</button>
    <button class="btn" id="el_junction" onclick="selectSymbol('junction')">📦 Caixa</button>
    <button class="btn" id="el_panel" onclick="selectSymbol('panel')">🔋 Quadre</button>
    <button class="btn" id="el_load" onclick="selectSymbol('load')">⚙️ Càrrega</button>

    <div class="sep"></div>

    <button class="btn" onclick="zoomIn()" title="Apropar">🔍+</button>
    <button class="btn" onclick="zoomOut()" title="Allunyar">🔍-</button>
    <button class="btn" id="btnZoomVal" onclick="resetZoom()">100%</button>

    <button class="btn btn-undo" onclick="undo()">↩️ Desfer</button>
    <label class="btn" style="cursor:pointer;">
      📷 Fons
      <input type="file" id="fileBg" accept="image/*" style="display:none;" onchange="loadBgImage(event)">
    </label>
    <input type="range" id="bgOpacity" min="0.1" max="1" step="0.1" value="0.35" style="width:45px;" onchange="redraw()" title="Opacitat foto fons">
    <button class="btn btn-danger" onclick="clearAll()">🗑️ Netejar</button>
    <button class="btn btn-save" onclick="downloadPNG()">💾 PNG</button>
  </div>
</div>

<div class="canvas-container" id="canvasWrapper">
  <canvas id="elecCanvas"></canvas>
</div>

<div class="status-bar">
  <span id="statusText">Cable actiu: ⚫ Fase (Negre) · Arrossega per traçar cable</span>
  <span class="badge-snap" id="snapBadge">🧲 SNAP BORN</span>
</div>

<!-- Modal confirmació Netejar -->
<div class="modal-overlay" id="confirmClearModal">
  <div class="modal-box">
    <h4>⚠️ Esborrar tot l'esquema?</h4>
    <p style="font-size:13px; color:#475569; margin:0 0 14px 0;">Aquesta acció eliminarà tots els cables, elements i textos dibuixats al llenç actual.</p>
    <div class="modal-actions">
      <button style="background:#e2e8f0; color:#334155;" onclick="closeClearConfirm()">Cancel·lar</button>
      <button style="background:#dc2626; color:white;" onclick="executeClearAll()">Sí, netejar tot</button>
    </div>
  </div>
</div>

<!-- Modal intern segur sense window.prompt() -->
<div class="modal-overlay" id="textModal">
  <div class="modal-box">
    <h4 id="modalTitle">Etiqueta / Text</h4>
    <input type="text" class="modal-input" id="modalInput" placeholder="Ex: PIA 16A, Cuina, L1...">
    <div class="modal-actions">
      <button style="background:#e2e8f0; color:#334155;" onclick="closeModal()">Cancel·lar</button>
      <button style="background:#2563eb; color:white;" onclick="confirmModal()">Acceptar</button>
    </div>
  </div>
</div>

<script>
const PROJECT_ID = "{project_id}";
const STORAGE_KEY = "esquema_electric_" + PROJECT_ID;

const canvas = document.getElementById("elecCanvas");
const ctx = canvas.getContext("2d");
const wrapper = document.getElementById("canvasWrapper");
const statusText = document.getElementById("statusText");
const snapBadge = document.getElementById("snapBadge");

const WIRE_STYLES = {{
  fase:   {{ label: "Fase (L)",   color: "#111827", stripe: null,      code: "L"  }},
  neutre: {{ label: "Neutre (N)", color: "#2563eb", stripe: null,      code: "N"  }},
  terra:  {{ label: "Terra (PE)", color: "#eab308", stripe: "#16a34a", code: "PE" }}
}};

const SYMBOL_DEFAULTS = {{
  bulb:       {{ name: "Bombeta",       defLabel: "Llum" }},
  socket:     {{ name: "Endoll",        defLabel: "Endoll 16A" }},
  switch:     {{ name: "Interruptor",   defLabel: "Int." }},
  commutator: {{ name: "Commutador",    defLabel: "Comm." }},
  mcb:        {{ name: "Magnetotèrmic", defLabel: "PIA 16A" }},
  rcd:        {{ name: "Diferencial",   defLabel: "ID 40A" }},
  contactor:  {{ name: "Contactor",     defLabel: "Contactor" }},
  thermostat: {{ name: "Termòstat",     defLabel: "Termòstat" }},
  timer:      {{ name: "Programador",   defLabel: "Programador" }},
  junction:   {{ name: "Caixa registre",defLabel: "Caixa" }},
  panel:      {{ name: "Quadre / IGA",  defLabel: "Quadre" }},
  load:       {{ name: "Càrrega",       defLabel: "Càrrega" }}
}};

let elements = []; // {{kind:'wire'|'symbol'|'text', ...}}
let toolMode = "wire"; // 'wire' | 'symbol' | 'text' | 'eraser' | 'pan'
let activeWire = "fase";
let activeSymbol = "bulb";
let symbolRotation = 0; // 0, 90, 180, 270
let orthoMode = true;
let continuousMode = true;
let lastWirePoint = null;

let zoom = 1.0;
let panX = 0;
let panY = 0;
let bgImage = null;

let isDrawing = false;
let isPanning = false;
let panStart = null;
let startPt = null;
let curPt = null;
let boxDrawStart = null;
let boxDrawCur = null;
let selectedEl = null;
let dragAction = null; // {{ type: 'move_el'|'move_wire'|'resize_box', el, ... }}
let pendingModalCb = null;

function saveLocal() {{
  try {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(elements));
  }} catch(e) {{}}
}}

function loadLocal() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {{
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) elements = parsed;
    }}
  }} catch(e) {{}}
}}

function resizeCanvas() {{
  canvas.width = wrapper.clientWidth;
  canvas.height = wrapper.clientHeight;
  redraw();
}}
window.addEventListener("resize", resizeCanvas);

function screenToWorld(cx, cy) {{
  return {{ x: (cx - panX) / zoom, y: (cy - panY) / zoom }};
}}

function snapGrid(val) {{
  return Math.round(val / 20) * 20;
}}

function isResizableBox(symType) {{
  return symType === "junction" || symType === "panel" || symType === "load";
}}

const BOX_DEFAULTS = {{
  panel:    {{ w: 180, h: 120, minW: 80, minH: 60 }},
  load:     {{ w: 120, h: 70,  minW: 60, minH: 40 }},
  junction: {{ w: 80,  h: 60,  minW: 60, minH: 40 }}
}};

function getBoxDims(el) {{
  const cfg = BOX_DEFAULTS[el.symType];
  if (!cfg) return {{ w: Math.max(28, el.w || 48), h: Math.max(28, el.h || 48) }};
  return {{ w: Math.max(cfg.minW, el.w || cfg.w), h: Math.max(cfg.minH, el.h || cfg.h) }};
}}

function getElementBounds(el) {{
  if (el.kind === "symbol") {{
    const d = getBoxDims(el);
    return {{ left: el.x - d.w / 2, top: el.y - d.h / 2, w: d.w, h: d.h }};
  }}
  if (el.kind === "text") {{
    const sc = el.scale || 1.0;
    const w = Math.max(36, ((el.text || "").length * 8 + 12) * sc);
    const h = 22 * sc;
    return {{ left: el.x - 4, top: el.y - 15 * sc, w: w, h: h }};
  }}
  if (el.kind === "wire" && el.points && el.points.length > 0) {{
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of el.points) {{
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }}
    return {{ left: minX - 6, top: minY - 6, w: Math.max(16, maxX - minX + 12), h: Math.max(16, maxY - minY + 12) }};
  }}
  return {{ left: 0, top: 0, w: 40, h: 40 }};
}}

function getBoundsHandles(bounds) {{
  const {{ left, top, w, h }} = bounds;
  const cx = left + w / 2, cy = top + h / 2;
  const right = left + w, bottom = top + h;
  return [
    {{ id: "nw",   x: left,  y: top,    cursor: "nwse-resize" }},
    {{ id: "n",    x: cx,    y: top,    cursor: "ns-resize"   }},
    {{ id: "ne",   x: right, y: top,    cursor: "nesw-resize" }},
    {{ id: "e",    x: right, y: cy,     cursor: "ew-resize"   }},
    {{ id: "se",   x: right, y: bottom, cursor: "nwse-resize" }},
    {{ id: "s",    x: cx,    y: bottom, cursor: "ns-resize"   }},
    {{ id: "sw",   x: left,  y: bottom, cursor: "nesw-resize" }},
    {{ id: "w",    x: left,  y: cy,     cursor: "ew-resize"   }},
    {{ id: "move", x: cx,    y: cy,     cursor: "move"        }}
  ];
}}

function getSymbolPorts(el) {{
  const d = getBoxDims(el);
  if (isResizableBox(el.symType)) {{
    const hw = d.w / 2, hh = d.h / 2;
    return [
      {{ x: el.x - hw, y: el.y }},
      {{ x: el.x + hw, y: el.y }},
      {{ x: el.x, y: el.y - hh }},
      {{ x: el.x, y: el.y + hh }},
      {{ x: el.x - hw, y: el.y - hh }},
      {{ x: el.x + hw, y: el.y - hh }},
      {{ x: el.x - hw, y: el.y + hh }},
      {{ x: el.x + hw, y: el.y + hh }}
    ];
  }}
  const sx = d.w / 48, sy = d.h / 48;
  const r = (el.rot || 0) * Math.PI / 180;
  const pts = el.symType === "thermostat"
    ? [{{ dx: -14, dy: -22 }}, {{ dx: 14, dy: -22 }}, {{ dx: -14, dy: 22 }}, {{ dx: 14, dy: 22 }}]
    : [{{ dx: -28, dy: 0 }}, {{ dx: 28, dy: 0 }}, {{ dx: 0, dy: -28 }}, {{ dx: 0, dy: 28 }}];
  return pts.map(p => {{
    const rx = p.dx * sx, ry = p.dy * sy;
    return {{
      x: el.x + rx * Math.cos(r) - ry * Math.sin(r),
      y: el.y + rx * Math.sin(r) + ry * Math.cos(r)
    }};
  }});
}}

function findSnapPoint(wx, wy) {{
  const thresh = 16 / zoom;
  let best = null;
  let bestD = thresh;
  for (const el of elements) {{
    if (el.kind === "wire") {{
      const pts = el.points || [];
      for (const p of pts) {{
        const d = Math.hypot(wx - p.x, wy - p.y);
        if (d < bestD) {{ bestD = d; best = {{ x: p.x, y: p.y }}; }}
      }}
    }} else if (el.kind === "symbol") {{
      for (const p of getSymbolPorts(el)) {{
        const d = Math.hypot(wx - p.x, wy - p.y);
        if (d < bestD) {{ bestD = d; best = {{ x: p.x, y: p.y }}; }}
      }}
    }}
  }}
  if (best) {{
    snapBadge.style.display = "inline-block";
    return best;
  }}
  snapBadge.style.display = "none";
  return {{ x: snapGrid(wx), y: snapGrid(wy) }};
}}

function buildWirePoints(p1, p2) {{
  if (!orthoMode || Math.abs(p1.x - p2.x) < 4 || Math.abs(p1.y - p2.y) < 4) {{
    return [{{ x: p1.x, y: p1.y }}, {{ x: p2.x, y: p2.y }}];
  }}
  // Angle recte net (horitzontal primer si dx >= dy, o vertical primer)
  if (Math.abs(p2.x - p1.x) >= Math.abs(p2.y - p1.y)) {{
    return [{{ x: p1.x, y: p1.y }}, {{ x: p2.x, y: p1.y }}, {{ x: p2.x, y: p2.y }}];
  }} else {{
    return [{{ x: p1.x, y: p1.y }}, {{ x: p1.x, y: p2.y }}, {{ x: p2.x, y: p2.y }}];
  }}
}}

function clearActiveToolbar() {{
  document.querySelectorAll(".toolbar .btn").forEach(b => {{
    if (!["btnOrtho","btnContinuous"].includes(b.id)) b.classList.remove("active");
  }});
}}

function selectWire(wireType) {{
  toolMode = "wire";
  activeWire = wireType;
  clearActiveToolbar();
  const map = {{ fase: "btnWireFase", neutre: "btnWireNeutre", terra: "btnWireTerra" }};
  document.getElementById(map[wireType]).classList.add("active");
  statusText.textContent = "Cable actiu: " + WIRE_STYLES[wireType].label + " · Arrossega per traçar";
  redraw();
}}

function selectSymbol(symType) {{
  toolMode = "symbol";
  activeSymbol = symType;
  lastWirePoint = null;
  document.getElementById("btnNewTrace").style.display = "none";
  clearActiveToolbar();
  document.getElementById("el_" + symType).classList.add("active");
  if (isResizableBox(symType)) {{
    statusText.textContent = "Element: " + SYMBOL_DEFAULTS[symType].name + " · Arrossega per donar-li mida (o toca per mida estàndard)";
  }} else {{
    statusText.textContent = "Element: " + SYMBOL_DEFAULTS[symType].name + " · Toca al plànol per col·locar-lo";
  }}
  redraw();
}}

function setTool(mode) {{
  toolMode = mode;
  clearActiveToolbar();
  const ids = {{ select: "btnSelect", text: "btnText", eraser: "btnEraser", pan: "btnPan" }};
  if (ids[mode]) document.getElementById(ids[mode]).classList.add("active");
  const msgs = {{
    select: "Seleccionar: toca un element per veure els quadrets a les cantonades/mig i moure o canviar la mida",
    text: "Eina Text: toca al plànol per escriure una nota o etiqueta",
    eraser: "Eina Goma: toca un cable o element per esborrar-lo",
    pan: "Moure vista: arrossega per desplaçar tot el llenç"
  }};
  statusText.textContent = msgs[mode] || "";
  redraw();
}}

function toggleOrtho() {{
  orthoMode = !orthoMode;
  const b = document.getElementById("btnOrtho");
  b.textContent = orthoMode ? "📐 90°: SÍ" : "📐 90°: NO";
  b.classList.toggle("btn-toggle-on", orthoMode);
}}

function toggleContinuous() {{
  continuousMode = !continuousMode;
  const b = document.getElementById("btnContinuous");
  b.textContent = continuousMode ? "🔗 Seguir: SÍ" : "🔗 Seguir: NO";
  b.classList.toggle("btn-toggle-on", continuousMode);
  if (!continuousMode) resetContinuous();
}}

function resetContinuous() {{
  lastWirePoint = null;
  document.getElementById("btnNewTrace").style.display = "none";
  redraw();
}}

function rotateActive() {{
  symbolRotation = (symbolRotation + 90) % 360;
  document.getElementById("rotLbl").textContent = symbolRotation + "°";
  const target = (selectedEl && selectedEl.kind === "symbol" && !isResizableBox(selectedEl.symType))
    ? selectedEl
    : (elements.length > 0 && elements[elements.length - 1].kind === "symbol" && !isResizableBox(elements[elements.length - 1].symType) && toolMode === "symbol" ? elements[elements.length - 1] : null);
  if (target) {{
    target.rot = ((target.rot || 0) + 90) % 360;
    saveLocal();
    redraw();
  }}
}}

function zoomIn() {{
  zoom = Math.min(3.0, +(zoom + 0.2).toFixed(2));
  document.getElementById("btnZoomVal").textContent = Math.round(zoom * 100) + "%";
  redraw();
}}
function zoomOut() {{
  zoom = Math.max(0.4, +(zoom - 0.2).toFixed(2));
  document.getElementById("btnZoomVal").textContent = Math.round(zoom * 100) + "%";
  redraw();
}}
function resetZoom() {{
  zoom = 1.0; panX = 0; panY = 0;
  document.getElementById("btnZoomVal").textContent = "100%";
  redraw();
}}

function undo() {{
  if (elements.length > 0) {{
    elements.pop();
    lastWirePoint = null;
    document.getElementById("btnNewTrace").style.display = "none";
    saveLocal();
    redraw();
  }}
}}

function clearAll() {{
  if (elements.length === 0 && !bgImage) return;
  document.getElementById("confirmClearModal").style.display = "flex";
}}
function closeClearConfirm() {{
  document.getElementById("confirmClearModal").style.display = "none";
}}
function executeClearAll() {{
  closeClearConfirm();
  elements = [];
  selectedEl = null;
  lastWirePoint = null;
  bgImage = null;
  document.getElementById("btnNewTrace").style.display = "none";
  saveLocal();
  redraw();
}}

function loadBgImage(ev) {{
  const file = ev.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {{
    const img = new Image();
    img.onload = function() {{ bgImage = img; redraw(); }};
    img.src = e.target.result;
  }};
  reader.readAsDataURL(file);
}}

function openModal(title, defVal, cb) {{
  document.getElementById("modalTitle").textContent = title;
  const inp = document.getElementById("modalInput");
  inp.value = defVal || "";
  pendingModalCb = cb;
  document.getElementById("textModal").style.display = "flex";
  setTimeout(() => {{ inp.focus(); inp.select(); }}, 50);
}}
function closeModal() {{
  document.getElementById("textModal").style.display = "none";
  pendingModalCb = null;
}}
function confirmModal() {{
  const val = document.getElementById("modalInput").value.trim();
  const cb = pendingModalCb;
  closeModal();
  if (cb) cb(val);
}}
document.getElementById("modalInput").addEventListener("keydown", e => {{
  if (e.key === "Enter") confirmModal();
  if (e.key === "Escape") closeModal();
}});

function drawWire(targetCtx, wireType, pts, alpha = 1.0) {{
  if (!pts || pts.length < 2) return;
  const st = WIRE_STYLES[wireType] || WIRE_STYLES.fase;
  targetCtx.save();
  targetCtx.globalAlpha = alpha;
  targetCtx.lineCap = "round";
  targetCtx.lineJoin = "round";

  if (st.stripe) {{
    // Fons verd-fosc sota groc per contrast normatiu terra
    targetCtx.strokeStyle = st.stripe;
    targetCtx.lineWidth = 5;
    targetCtx.beginPath();
    targetCtx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) targetCtx.lineTo(pts[i].x, pts[i].y);
    targetCtx.stroke();

    targetCtx.strokeStyle = st.color;
    targetCtx.lineWidth = 3;
    targetCtx.setLineDash([8, 5]);
    targetCtx.beginPath();
    targetCtx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) targetCtx.lineTo(pts[i].x, pts[i].y);
    targetCtx.stroke();
    targetCtx.setLineDash([]);
  }} else {{
    targetCtx.strokeStyle = st.color;
    targetCtx.lineWidth = 3.5;
    targetCtx.beginPath();
    targetCtx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) targetCtx.lineTo(pts[i].x, pts[i].y);
    targetCtx.stroke();
  }}

  // Nodes d'unió
  targetCtx.fillStyle = st.stripe ? "#16a34a" : st.color;
  for (const idx of [0, pts.length - 1]) {{
    targetCtx.beginPath();
    targetCtx.arc(pts[idx].x, pts[idx].y, 3.5, 0, Math.PI * 2);
    targetCtx.fill();
  }}
  targetCtx.restore();
}}

function drawElectricalSymbol(targetCtx, el) {{
  targetCtx.save();
  targetCtx.translate(el.x, el.y);
  const isBox = isResizableBox(el.symType);
  const d = getBoxDims(el);
  const rad = isBox ? 0 : (((el.rot || 0) * Math.PI) / 180);
  targetCtx.rotate(rad);

  if (!isBox) {{
    targetCtx.scale(d.w / 48, d.h / 48);
  }}

  targetCtx.strokeStyle = "#0f172a";
  targetCtx.fillStyle = "#ffffff";
  targetCtx.lineWidth = 2.2;

  if (!isBox && el.symType !== "thermostat") {{
    // Terminals d'entrada/sortida discrets
    targetCtx.fillStyle = "#64748b";
    for (const pt of [[-28,0],[28,0],[0,-28],[0,28]]) {{
      targetCtx.beginPath();
      targetCtx.arc(pt[0], pt[1], 2.2, 0, Math.PI * 2);
      targetCtx.fill();
    }}
    targetCtx.fillStyle = "#ffffff";
  }}

  const t = el.symType;
  if (t === "bulb") {{
    targetCtx.fillStyle = "#fef9c3";
    targetCtx.beginPath(); targetCtx.arc(0, 0, 18, 0, Math.PI * 2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath();
    targetCtx.moveTo(-12, -12); targetCtx.lineTo(12, 12);
    targetCtx.moveTo(12, -12); targetCtx.lineTo(-12, 12);
    targetCtx.stroke();
  }} else if (t === "socket") {{
    targetCtx.fillStyle = "#f8fafc";
    targetCtx.beginPath(); targetCtx.arc(0, 0, 18, 0, Math.PI * 2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath(); targetCtx.arc(0, 2, 10, Math.PI, 0); targetCtx.stroke();
    targetCtx.fillStyle = "#0f172a";
    targetCtx.beginPath(); targetCtx.arc(-5, 3, 2.3, 0, Math.PI*2); targetCtx.arc(5, 3, 2.3, 0, Math.PI*2); targetCtx.fill();
    targetCtx.beginPath(); targetCtx.moveTo(0, -14); targetCtx.lineTo(0, -7); targetCtx.stroke();
  }} else if (t === "switch") {{
    targetCtx.beginPath(); targetCtx.arc(-14, 4, 3.5, 0, Math.PI*2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath(); targetCtx.arc(14, 4, 3.5, 0, Math.PI*2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath(); targetCtx.moveTo(-11, 2); targetCtx.lineTo(12, -11); targetCtx.stroke();
  }} else if (t === "commutator") {{
    targetCtx.beginPath(); targetCtx.arc(-15, 0, 3.5, 0, Math.PI*2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath(); targetCtx.arc(14, -9, 3.5, 0, Math.PI*2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath(); targetCtx.arc(14, 9, 3.5, 0, Math.PI*2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath(); targetCtx.moveTo(-12, 0); targetCtx.lineTo(11, -8); targetCtx.stroke();
  }} else if (t === "mcb") {{
    targetCtx.fillStyle = "#eff6ff";
    targetCtx.fillRect(-16, -22, 32, 44);
    targetCtx.strokeRect(-16, -22, 32, 44);
    targetCtx.beginPath();
    targetCtx.moveTo(0, -22); targetCtx.lineTo(0, -9);
    targetCtx.moveTo(0, 9); targetCtx.lineTo(0, 22);
    targetCtx.moveTo(-6, 9); targetCtx.lineTo(3, -8);
    targetCtx.stroke();
    targetCtx.fillStyle = "#1d4ed8";
    targetCtx.font = "bold 9px sans-serif";
    targetCtx.textAlign = "center";
    targetCtx.fillText("PIA", 0, -12);
  }} else if (t === "rcd") {{
    targetCtx.fillStyle = "#f0fdf4";
    targetCtx.fillRect(-18, -22, 36, 44);
    targetCtx.strokeRect(-18, -22, 36, 44);
    targetCtx.beginPath(); targetCtx.ellipse(0, 2, 10, 6, 0, 0, Math.PI*2); targetCtx.stroke();
    targetCtx.fillStyle = "#15803d";
    targetCtx.font = "bold 9px sans-serif";
    targetCtx.textAlign = "center";
    targetCtx.fillText("ID 30mA", 0, -11);
  }} else if (t === "contactor") {{
    targetCtx.fillStyle = "#fef3c7";
    targetCtx.fillRect(-20, -22, 40, 44);
    targetCtx.strokeRect(-20, -22, 40, 44);
    targetCtx.strokeRect(-10, -8, 20, 16);
    targetCtx.fillStyle = "#92400e";
    targetCtx.font = "bold 8px sans-serif";
    targetCtx.textAlign = "center";
    targetCtx.fillText("A1 / A2", 0, -12);
    targetCtx.fillText("KM", 0, 3);
  }} else if (t === "thermostat") {{
    targetCtx.fillStyle = "#fff1f2";
    targetCtx.fillRect(-24, -22, 48, 44);
    targetCtx.strokeRect(-24, -22, 48, 44);
    // 4 contactes clarament diferenciats (L, N a dalt; C, NO a baix)
    const terms = [
      [-14, -22, "L", -14, -12],
      [14,  -22, "N", 14,  -12],
      [-14,  22, "C", -14,  18],
      [14,   22, "NO", 14,  18]
    ];
    for (const [tx, ty, tlbl, lx, ly] of terms) {{
      targetCtx.fillStyle = "#0f172a";
      targetCtx.beginPath(); targetCtx.arc(tx, ty, 3, 0, Math.PI * 2); targetCtx.fill();
      targetCtx.fillStyle = "#881337";
      targetCtx.font = "bold 7.5px sans-serif";
      targetCtx.textAlign = "center";
      targetCtx.fillText(tlbl, lx, ly);
    }}
    targetCtx.fillStyle = "#be123c";
    targetCtx.font = "bold 12px sans-serif";
    targetCtx.textAlign = "center";
    targetCtx.fillText("°C", 0, 4);
  }} else if (t === "timer") {{
    targetCtx.fillStyle = "#f5f3ff";
    targetCtx.fillRect(-18, -20, 36, 40);
    targetCtx.strokeRect(-18, -20, 36, 40);
    targetCtx.fillStyle = "#ffffff";
    targetCtx.beginPath(); targetCtx.arc(0, -1, 11, 0, Math.PI * 2); targetCtx.fill(); targetCtx.stroke();
    targetCtx.beginPath();
    targetCtx.moveTo(0, -1); targetCtx.lineTo(0, -8);
    targetCtx.moveTo(0, -1); targetCtx.lineTo(6, 2);
    targetCtx.stroke();
    targetCtx.fillStyle = "#6d28d9";
    targetCtx.font = "bold 7px sans-serif";
    targetCtx.textAlign = "center";
    targetCtx.fillText("TIMER", 0, 16);
  }} else if (t === "junction") {{
    const d = getBoxDims(el);
    const hw = d.w / 2, hh = d.h / 2;
    targetCtx.fillStyle = "rgba(241, 245, 249, 0.55)";
    targetCtx.fillRect(-hw, -hh, d.w, d.h);
    targetCtx.strokeStyle = "#475569";
    targetCtx.setLineDash([5, 3]);
    targetCtx.strokeRect(-hw, -hh, d.w, d.h);
    targetCtx.setLineDash([]);
    targetCtx.fillStyle = "#334155";
    targetCtx.font = "bold 10px sans-serif";
    targetCtx.textAlign = "left";
    targetCtx.fillText(el.label || "Caixa", -hw + 6, -hh + 13);
  }} else if (t === "panel") {{
    const d = getBoxDims(el);
    const hw = d.w / 2, hh = d.h / 2;
    targetCtx.fillStyle = "rgba(226, 232, 240, 0.32)";
    targetCtx.fillRect(-hw, -hh, d.w, d.h);
    targetCtx.strokeStyle = "#1e293b";
    targetCtx.lineWidth = 2.4;
    targetCtx.strokeRect(-hw, -hh, d.w, d.h);
    targetCtx.lineWidth = 1;
    targetCtx.strokeStyle = "#94a3b8";
    targetCtx.strokeRect(-hw + 4, -hh + 4, d.w - 8, d.h - 8);
    // Carril DIN subtil central
    targetCtx.strokeStyle = "rgba(100,116,139,0.35)";
    targetCtx.beginPath();
    targetCtx.moveTo(-hw + 8, 0); targetCtx.lineTo(hw - 8, 0);
    targetCtx.stroke();
    targetCtx.fillStyle = "#0f172a";
    targetCtx.font = "bold 11px sans-serif";
    targetCtx.textAlign = "left";
    targetCtx.fillText(el.label || "Quadre", -hw + 8, -hh + 16);
  }} else if (t === "load") {{
    const d = getBoxDims(el);
    const hw = d.w / 2, hh = d.h / 2;
    targetCtx.fillStyle = "rgba(254, 243, 199, 0.45)";
    targetCtx.fillRect(-hw, -hh, d.w, d.h);
    targetCtx.strokeStyle = "#d97706";
    targetCtx.lineWidth = 2.2;
    targetCtx.strokeRect(-hw, -hh, d.w, d.h);
    targetCtx.fillStyle = "#92400e";
    targetCtx.font = "bold 11px sans-serif";
    targetCtx.textAlign = "center";
    targetCtx.fillText("⚙️ " + (el.label || "Càrrega"), 0, 4);
  }}

  if (!isBox) {{
    targetCtx.scale(48 / d.w, 48 / d.h);
  }}
  targetCtx.rotate(-rad);
  if (!isBox && el.label) {{
    targetCtx.font = "bold 11px sans-serif";
    targetCtx.textAlign = "center";
    const tw = targetCtx.measureText(el.label).width + 8;
    const ly = Math.round(d.h / 2) + 2;
    targetCtx.fillStyle = "rgba(255,255,255,0.9)";
    targetCtx.fillRect(-tw/2, ly, tw, 15);
    targetCtx.fillStyle = "#0f172a";
    targetCtx.fillText(el.label, 0, ly + 11);
  }}
  targetCtx.restore();
}}

function drawTextEl(targetCtx, el) {{
  targetCtx.save();
  const sc = el.scale || 1.0;
  const fSize = Math.round(13 * sc);
  targetCtx.font = "bold " + fSize + "px sans-serif";
  const w = targetCtx.measureText(el.text).width + 10 * sc;
  const h = 20 * sc;
  targetCtx.fillStyle = "rgba(255,255,255,0.92)";
  targetCtx.strokeStyle = "#cbd5e1";
  targetCtx.lineWidth = 1;
  targetCtx.fillRect(el.x - 4, el.y - 14 * sc, w, h);
  targetCtx.strokeRect(el.x - 4, el.y - 14 * sc, w, h);
  targetCtx.fillStyle = "#0f172a";
  targetCtx.fillText(el.text, el.x + 1, el.y);
  targetCtx.restore();
}}

function drawSelectionHandles(targetCtx, el) {{
  if (!el) return;
  const b = getElementBounds(el);
  targetCtx.save();
  targetCtx.strokeStyle = "#2563eb";
  targetCtx.lineWidth = 1.5;
  targetCtx.setLineDash([4, 3]);
  targetCtx.strokeRect(b.left, b.top, b.w, b.h);
  targetCtx.setLineDash([]);

  for (const h of getBoundsHandles(b)) {{
    if (h.id === "move") {{
      targetCtx.fillStyle = "#2563eb";
      targetCtx.strokeStyle = "#ffffff";
      targetCtx.lineWidth = 1.5;
      targetCtx.fillRect(h.x - 4.5, h.y - 4.5, 9, 9);
      targetCtx.strokeRect(h.x - 4.5, h.y - 4.5, 9, 9);
    }} else {{
      targetCtx.fillStyle = "#ffffff";
      targetCtx.strokeStyle = "#2563eb";
      targetCtx.lineWidth = 1.6;
      targetCtx.fillRect(h.x - 4, h.y - 4, 8, 8);
      targetCtx.strokeRect(h.x - 4, h.y - 4, 8, 8);
    }}
  }}
  targetCtx.restore();
}}

function drawLegend(targetCtx, width, height) {{
  targetCtx.save();
  const lx = 12, ly = height - 34;
  targetCtx.fillStyle = "rgba(255,255,255,0.92)";
  targetCtx.strokeStyle = "#cbd5e1";
  targetCtx.lineWidth = 1;
  targetCtx.fillRect(lx, ly, 275, 24);
  targetCtx.strokeRect(lx, ly, 275, 24);
  targetCtx.font = "bold 11px sans-serif";

  targetCtx.fillStyle = "#111827"; targetCtx.fillRect(lx + 10, ly + 10, 18, 4);
  targetCtx.fillText("Fase (L)", lx + 32, ly + 16);

  targetCtx.fillStyle = "#2563eb"; targetCtx.fillRect(lx + 92, ly + 10, 18, 4);
  targetCtx.fillStyle = "#0f172a"; targetCtx.fillText("Neutre (N)", lx + 114, ly + 16);

  targetCtx.fillStyle = "#16a34a"; targetCtx.fillRect(lx + 186, ly + 9, 18, 6);
  targetCtx.fillStyle = "#facc15"; targetCtx.fillRect(lx + 188, ly + 10, 14, 4);
  targetCtx.fillStyle = "#0f172a"; targetCtx.fillText("Terra (PE)", lx + 208, ly + 16);
  targetCtx.restore();
}}

function renderTo(targetCtx, w, h, withBgGrid, isExport = false) {{
  targetCtx.clearRect(0, 0, w, h);
  if (withBgGrid) {{
    targetCtx.fillStyle = "#ffffff";
    targetCtx.fillRect(0, 0, w, h);
  }}
  targetCtx.save();
  targetCtx.translate(panX, panY);
  targetCtx.scale(zoom, zoom);

  if (bgImage) {{
    targetCtx.save();
    targetCtx.globalAlpha = parseFloat(document.getElementById("bgOpacity").value || "0.35");
    targetCtx.drawImage(bgImage, 0, 0, canvas.width / zoom, canvas.height / zoom);
    targetCtx.restore();
  }}

  const showH = !isExport;

  // 1. Caixes i Quadres al fons perquè s'hi puguin posar cables i components a dins
  for (const el of elements) {{
    if (el.kind === "symbol" && isResizableBox(el.symType)) drawElectricalSymbol(targetCtx, el);
  }}
  // 2. Cables al damunt
  for (const el of elements) {{
    if (el.kind === "wire") drawWire(targetCtx, el.wireType, el.points);
  }}
  // 3. Elements elèctrics i textos al primer pla
  for (const el of elements) {{
    if (el.kind === "symbol" && !isResizableBox(el.symType)) drawElectricalSymbol(targetCtx, el);
    else if (el.kind === "text") drawTextEl(targetCtx, el);
  }}

  if (showH && selectedEl && elements.includes(selectedEl)) {{
    drawSelectionHandles(targetCtx, selectedEl);
  }}

  if (boxDrawStart && boxDrawCur && toolMode === "symbol" && isResizableBox(activeSymbol)) {{
    const x1 = Math.min(boxDrawStart.x, boxDrawCur.x);
    const y1 = Math.min(boxDrawStart.y, boxDrawCur.y);
    const bw = Math.max(20, Math.abs(boxDrawCur.x - boxDrawStart.x));
    const bh = Math.max(20, Math.abs(boxDrawCur.y - boxDrawStart.y));
    targetCtx.save();
    targetCtx.strokeStyle = "#2563eb";
    targetCtx.fillStyle = "rgba(37, 99, 235, 0.12)";
    targetCtx.lineWidth = 2;
    targetCtx.setLineDash([6, 4]);
    targetCtx.fillRect(x1, y1, bw, bh);
    targetCtx.strokeRect(x1, y1, bw, bh);
    targetCtx.restore();
  }}

  if (isDrawing && toolMode === "wire" && startPt && curPt) {{
    const previewPts = buildWirePoints(startPt, curPt);
    drawWire(targetCtx, activeWire, previewPts, 0.65);
  }}

  if (toolMode === "wire" && continuousMode && lastWirePoint) {{
    targetCtx.save();
    targetCtx.strokeStyle = "#10b981";
    targetCtx.fillStyle = "rgba(16,185,129,0.2)";
    targetCtx.lineWidth = 2;
    targetCtx.beginPath();
    targetCtx.arc(lastWirePoint.x, lastWirePoint.y, 7, 0, Math.PI * 2);
    targetCtx.fill();
    targetCtx.stroke();
    targetCtx.restore();
  }}
  targetCtx.restore();

  drawLegend(targetCtx, w, h);
}}

function redraw() {{
  renderTo(ctx, canvas.width, canvas.height, false, false);
}}

function distPointSegment(px, py, x1, y1, x2, y2) {{
  const l2 = (x2 - x1) ** 2 + (y2 - y1) ** 2;
  if (l2 === 0) return Math.hypot(px - x1, py - y1);
  let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1)));
}}

function hitTestWire(el, wx, wy, thresh) {{
  if (el.kind !== "wire" || !el.points) return false;
  for (let j = 0; j < el.points.length - 1; j++) {{
    const p1 = el.points[j], p2 = el.points[j + 1];
    if (distPointSegment(wx, wy, p1.x, p1.y, p2.x, p2.y) <= thresh) return true;
  }}
  return false;
}}

function hitTestBox(el, wx, wy, borderOnly = false) {{
  const d = getBoxDims(el);
  const left = el.x - d.w / 2, right = el.x + d.w / 2;
  const top = el.y - d.h / 2, bottom = el.y + d.h / 2;
  const inside = (wx >= left - 10 && wx <= right + 10 && wy >= top - 10 && wy <= bottom + 10);
  if (!inside) return false;
  if (!borderOnly) return true;
  const onLeft = Math.abs(wx - left) <= 18, onRight = Math.abs(wx - right) <= 18;
  const onTop = Math.abs(wy - top) <= 22, onBot = Math.abs(wy - bottom) <= 18;
  return onLeft || onRight || onTop || onBot;
}}

function findTopElementAt(wx, wy) {{
  const hitThresh = 26 / zoom;
  // 1. Textos
  for (let i = elements.length - 1; i >= 0; i--) {{
    const el = elements[i];
    if (el.kind === "text" && Math.hypot(wx - el.x, wy - el.y) <= hitThresh) return i;
  }}
  // 2. Símbols en primer pla (no caixes)
  for (let i = elements.length - 1; i >= 0; i--) {{
    const el = elements[i];
    if (el.kind === "symbol" && !isResizableBox(el.symType) && Math.hypot(wx - el.x, wy - el.y) <= hitThresh) return i;
  }}
  // 3. Cables
  for (let i = elements.length - 1; i >= 0; i--) {{
    if (hitTestWire(elements[i], wx, wy, hitThresh)) return i;
  }}
  // 4. Caixes i quadres (vora/interior)
  for (let i = elements.length - 1; i >= 0; i--) {{
    const el = elements[i];
    if (el.kind === "symbol" && isResizableBox(el.symType) && hitTestBox(el, wx, wy, false)) return i;
  }}
  return -1;
}}

function findSelectionHandleAt(wx, wy) {{
  if (!selectedEl || !elements.includes(selectedEl)) return null;
  const thresh = 14 / zoom;
  const handles = getBoundsHandles(getElementBounds(selectedEl));
  for (const h of handles) {{
    if (Math.hypot(wx - h.x, wy - h.y) <= thresh) return h;
  }}
  return null;
}}

function snapStep(val, step = 10) {{
  return Math.round(val / step) * step;
}}

function startTransformDrag(el, handleId, wx, wy) {{
  const b = getElementBounds(el);
  if (handleId === "move") {{
    if (el.kind === "wire") {{
      return {{ type: "move_wire", el, lastX: snapGrid(wx), lastY: snapGrid(wy) }};
    }}
    return {{ type: "move_el", el, offsetX: wx - el.x, offsetY: wy - el.y }};
  }}
  return {{
    type: "transform_handle",
    el,
    handleId,
    origBounds: {{ left: b.left, top: b.top, right: b.left + b.w, bottom: b.top + b.h, w: b.w, h: b.h }},
    origPoints: (el.kind === "wire" && el.points) ? el.points.map(p => ({{ x: p.x, y: p.y }})) : null
  }};
}}

function eraseNearest(wx, wy) {{
  const idx = findTopElementAt(wx, wy);
  if (idx !== -1) {{
    const removed = elements.splice(idx, 1)[0];
    if (selectedEl === removed) selectedEl = null;
    if (removed.kind === "wire") {{
      lastWirePoint = null;
      document.getElementById("btnNewTrace").style.display = "none";
    }}
    saveLocal();
    redraw();
  }}
}}

function getPointerCoords(e) {{
  const rect = canvas.getBoundingClientRect();
  return {{ cx: e.clientX - rect.left, cy: e.clientY - rect.top }};
}}

canvas.addEventListener("pointerdown", e => {{
  canvas.setPointerCapture(e.pointerId);
  const {{ cx, cy }} = getPointerCoords(e);
  if (toolMode === "pan") {{
    isPanning = true;
    panStart = {{ x: cx - panX, y: cy - panY }};
    return;
  }}
  const w = screenToWorld(cx, cy);
  if (toolMode === "eraser") {{
    eraseNearest(w.x, w.y);
    return;
  }}

  // En mode Seleccionar (o si cliquem un tirador d'un element seleccionat): comprovar els 9 quadrets primer
  if (toolMode === "select" || (selectedEl && elements.includes(selectedEl))) {{
    const hitH = findSelectionHandleAt(w.x, w.y);
    if (hitH && (toolMode === "select" || hitH.id !== "move")) {{
      dragAction = startTransformDrag(selectedEl, hitH.id, w.x, w.y);
      redraw();
      return;
    }}
  }}

  if (toolMode === "select") {{
    const idx = findTopElementAt(w.x, w.y);
    if (idx !== -1) {{
      const el = elements[idx];
      selectedEl = el;
      dragAction = startTransformDrag(el, "move", w.x, w.y);
    }} else {{
      selectedEl = null;
      dragAction = null;
    }}
    redraw();
    return;
  }}

  if (toolMode === "text") {{
    openModal("Text / Nota de l'esquema:", "", txt => {{
      if (txt) {{
        elements.push({{ kind: "text", x: snapGrid(w.x), y: snapGrid(w.y), text: txt }});
        saveLocal(); redraw();
      }}
    }});
    return;
  }}
  if (toolMode === "symbol") {{
    if (isResizableBox(activeSymbol)) {{
      boxDrawStart = {{ x: snapGrid(w.x), y: snapGrid(w.y) }};
      boxDrawCur = {{ x: boxDrawStart.x, y: boxDrawStart.y }};
      redraw();
      return;
    }}
    const pt = {{ x: snapGrid(w.x), y: snapGrid(w.y) }};
    const defLbl = (SYMBOL_DEFAULTS[activeSymbol] || {{}}).defLabel || "";
    const newEl = {{ kind: "symbol", symType: activeSymbol, x: pt.x, y: pt.y, rot: symbolRotation, label: defLbl }};
    elements.push(newEl);
    selectedEl = newEl;
    saveLocal(); redraw();
    return;
  }}
  if (toolMode === "wire") {{
    isDrawing = true;
    if (continuousMode && lastWirePoint) {{
      startPt = {{ x: lastWirePoint.x, y: lastWirePoint.y }};
      curPt = findSnapPoint(w.x, w.y);
    }} else {{
      startPt = findSnapPoint(w.x, w.y);
      curPt = {{ x: startPt.x, y: startPt.y }};
    }}
    redraw();
  }}
}});

canvas.addEventListener("pointermove", e => {{
  const {{ cx, cy }} = getPointerCoords(e);
  if (isPanning && panStart) {{
    panX = cx - panStart.x;
    panY = cy - panStart.y;
    redraw();
    return;
  }}
  const w = screenToWorld(cx, cy);
  if (dragAction) {{
    const el = dragAction.el;
    if (dragAction.type === "transform_handle") {{
      const ob = dragAction.origBounds;
      const hId = dragAction.handleId;
      let minW = 28, minH = 28;
      if (el.kind === "symbol" && isResizableBox(el.symType)) {{
        const cfg = BOX_DEFAULTS[el.symType] || {{ minW: 60, minH: 40 }};
        minW = cfg.minW; minH = cfg.minH;
      }} else if (el.kind === "text") {{
        minW = 30; minH = 14;
      }} else if (el.kind === "wire") {{
        minW = 16; minH = 16;
      }}
      let nL = ob.left, nR = ob.right, nT = ob.top, nB = ob.bottom;
      if (hId.includes("w")) nL = Math.min(ob.right - minW, snapStep(w.x, 10));
      if (hId.includes("e")) nR = Math.max(ob.left + minW, snapStep(w.x, 10));
      if (hId.includes("n")) nT = Math.min(ob.bottom - minH, snapStep(w.y, 10));
      if (hId.includes("s")) nB = Math.max(ob.top + minH, snapStep(w.y, 10));
      const newW = nR - nL, newH = nB - nT;

      if (el.kind === "symbol") {{
        el.w = newW;
        el.h = newH;
        el.x = (nL + nR) / 2;
        el.y = (nT + nB) / 2;
      }} else if (el.kind === "text") {{
        el.scale = Math.max(0.6, Math.min(3.5, newH / 22));
        el.x = nL + 4;
        el.y = nT + 15 * el.scale;
      }} else if (el.kind === "wire" && dragAction.origPoints && el.points) {{
        for (let idx = 0; idx < el.points.length; idx++) {{
          const op = dragAction.origPoints[idx];
          const rx = ob.w > 0 ? (op.x - ob.left) / ob.w : 0;
          const ry = ob.h > 0 ? (op.y - ob.top) / ob.h : 0;
          el.points[idx].x = snapStep(nL + rx * newW, 10);
          el.points[idx].y = snapStep(nT + ry * newH, 10);
        }}
      }}
      redraw();
    }} else if (dragAction.type === "move_el") {{
      el.x = snapGrid(w.x - dragAction.offsetX);
      el.y = snapGrid(w.y - dragAction.offsetY);
      redraw();
    }} else if (dragAction.type === "move_wire" && el.points) {{
      const gx = snapGrid(w.x);
      const gy = snapGrid(w.y);
      const dx = gx - dragAction.lastX;
      const dy = gy - dragAction.lastY;
      if (dx !== 0 || dy !== 0) {{
        for (const p of el.points) {{ p.x += dx; p.y += dy; }}
        dragAction.lastX = gx;
        dragAction.lastY = gy;
        redraw();
      }}
    }}
    return;
  }}
  if (toolMode === "select") {{
    const hitH = findSelectionHandleAt(w.x, w.y);
    if (hitH) canvas.style.cursor = hitH.cursor;
    else if (findTopElementAt(w.x, w.y) !== -1) canvas.style.cursor = "move";
    else canvas.style.cursor = "default";
    return;
  }}
  canvas.style.cursor = toolMode === "pan" ? "grab" : "crosshair";
  if (boxDrawStart && toolMode === "symbol" && isResizableBox(activeSymbol)) {{
    boxDrawCur = {{ x: snapGrid(w.x), y: snapGrid(w.y) }};
    redraw();
    return;
  }}
  if (!isDrawing || toolMode !== "wire") return;
  curPt = findSnapPoint(w.x, w.y);
  redraw();
}});

canvas.addEventListener("pointerup", e => {{
  if (isPanning) {{ isPanning = false; panStart = null; return; }}
  if (dragAction) {{
    dragAction = null;
    saveLocal();
    redraw();
    return;
  }}
  if (boxDrawStart && boxDrawCur && toolMode === "symbol" && isResizableBox(activeSymbol)) {{
    const dx = Math.abs(boxDrawCur.x - boxDrawStart.x);
    const dy = Math.abs(boxDrawCur.y - boxDrawStart.y);
    const cfg = BOX_DEFAULTS[activeSymbol] || {{ w: 80, h: 60 }};
    const w = (dx >= 40 && dy >= 40) ? dx : cfg.w;
    const h = (dx >= 40 && dy >= 40) ? dy : cfg.h;
    const cxBox = (dx >= 40 && dy >= 40) ? (boxDrawStart.x + boxDrawCur.x) / 2 : boxDrawStart.x;
    const cyBox = (dx >= 40 && dy >= 40) ? (boxDrawStart.y + boxDrawCur.y) / 2 : boxDrawStart.y;
    const defLbl = (SYMBOL_DEFAULTS[activeSymbol] || {{}}).defLabel || "";
    const newBox = {{ kind: "symbol", symType: activeSymbol, x: cxBox, y: cyBox, w: w, h: h, rot: 0, label: defLbl }};
    elements.push(newBox);
    selectedEl = newBox;
    boxDrawStart = null;
    boxDrawCur = null;
    saveLocal();
    redraw();
    return;
  }}
  if (!isDrawing || toolMode !== "wire") return;
  isDrawing = false;
  snapBadge.style.display = "none";
  if (startPt && curPt && Math.hypot(curPt.x - startPt.x, curPt.y - startPt.y) >= 8) {{
    const pts = buildWirePoints(startPt, curPt);
    elements.push({{ kind: "wire", wireType: activeWire, points: pts }});
    if (continuousMode) {{
      lastWirePoint = {{ x: curPt.x, y: curPt.y }};
      document.getElementById("btnNewTrace").style.display = "inline-flex";
    }}
    saveLocal();
  }}
  startPt = null; curPt = null;
  redraw();
}});

// Doble clic sobre un element per canviar-li l'etiqueta (ex: PIA 16A -> PIA 20A)
canvas.addEventListener("dblclick", e => {{
  const {{ cx, cy }} = getPointerCoords(e);
  const w = screenToWorld(cx, cy);
  const idx = findTopElementAt(w.x, w.y);
  if (idx !== -1 && elements[idx].kind === "symbol") {{
    const el = elements[idx];
    openModal("Etiqueta del component:", el.label || "", newLbl => {{
      el.label = newLbl;
      saveLocal(); redraw();
    }});
  }} else if (idx !== -1 && elements[idx].kind === "text") {{
    const el = elements[idx];
    openModal("Editar text:", el.text || "", newTxt => {{
      if (newTxt) {{ el.text = newTxt; saveLocal(); redraw(); }}
    }});
  }}
}});

function downloadPNG() {{
  const expCanvas = document.createElement("canvas");
  expCanvas.width = canvas.width;
  expCanvas.height = canvas.height;
  const expCtx = expCanvas.getContext("2d");
  renderTo(expCtx, expCanvas.width, expCanvas.height, true, true);
  const link = document.createElement("a");
  link.download = "esquema_electric_" + PROJECT_ID + ".png";
  link.href = expCanvas.toDataURL("image/png");
  link.click();
}}

loadLocal();
resizeCanvas();
setTimeout(resizeCanvas, 120);
</script>
</body>
</html>"""


def render_esquema_electric_tab(projecte: Dict[str, Any]) -> None:
    """Renderitza la pestanya d'Esquemes Elèctrics dins l'Editor Gràfic del projecte."""
    project_id = projecte.get("id", "nou")
    esq_info = projecte.get("esquema_electric", {}) or {}
    preview_png = esq_info.get("preview_png")

    st.markdown("#### ⚡ Editor d'Esquemes Elèctrics")
    st.caption(
        "Dibuixa esquemes amb **3 colors de cable** (⚫ Fase, 🔵 Neutre, 🟡 Terra) "
        "i col·loca elements elèctrics comuns (💡 Bombeta, 🔌 Endoll, ⚡ Magnetotèrmic, 🔘 Interruptor, 🛡️ Diferencial, 🧲 Contactor, 🌡️ Termòstat 4 contactes, ⏰ Programador, 📦 Caixa, 🔋 Quadre, ⚙️ Càrrega)."
    )

    with st.expander("📖 Guia ràpida: Esquemes Elèctrics", expanded=False):
        st.markdown("""
- **Cables**: Escull **⚫ Fase (Negre)**, **🔵 Neutre (Blau)** o **🟡 Terra (Groc)** i arrossega pel llenç. Amb **`📐 90°: SÍ`** els trams fan colzes rectes automàticament.
- **Elements elèctrics**: Prem qualsevol botó (**💡 Bombeta**, **🔌 Endoll**, **⚡ Magnetotèrmic**, **🔘 Interruptor**, **🔀 Commutador**, **🛡️ Diferencial**, **🧲 Contactor**, **🌡️ Termòstat** de 4 contactes `L/N/C/NO`, **⏰ Programador**, **📦 Caixa**, **🔋 Quadre**, **⚙️ Càrrega**) i toca on el vulguis situar.
- **Redimensionar i Moure elements**: Prem el botó **`↖ Seleccionar`** i toca qualsevol element, requadre, text o cable. Sortiran **8 quadrets petits** a les cantonades i punts mitjans (per transformar amplada/alçada) i un **quadret central** (o arrossegament intern) per moure'l. Amb **📦 Caixa**, **🔋 Quadre** o **⚙️ Càrrega** també pots **arrossegar** directament en crear-los per donar-los la mida desitjada.
- **Editar etiqueta / Girar**: Fes **doble clic** sobre un element per canviar-ne l'etiqueta (ex. *PIA 16A*, *Termo*) o prem **🔄 Girar** per rotar-lo 90°.
- **Desar**: Prem **💾 PNG** a la barra de l'editor i puja el fitxer al formulari inferior per deixar l'esquema desat al projecte.
""")

    if preview_png:
        st.markdown("**Esquema elèctric desat per a aquest projecte:**")
        st.image(decode_image_for_st(preview_png), width="stretch")
        data_act = esq_info.get("data_actualitzacio", "")
        if data_act:
            st.caption(f"Darrera actualització de l'esquema elèctric: {data_act}")

    with st.expander("⚡ Obrir Editor d'Esquemes Elèctrics (Canvas)", expanded=False):
        html_code = get_electric_canvas_html(project_id)
        components.html(html_code, height=660, scrolling=False)

    with st.form(f"form_save_esq_elec_{project_id}", clear_on_submit=True):
        st.markdown("**💾 Desar o Actualitzar Esquema Elèctric al Projecte**")
        up_esq = st.file_uploader(
            "Carrega el PNG generat o una foto d'esquema elèctric:",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"up_esq_elec_{project_id}",
        )
        sub_esq = st.form_submit_button("Guardar Esquema Elèctric", type="primary")
        if sub_esq and up_esq:
            b64_data = compress_image_b64(up_esq, max_dim=1280, quality=85)
            if save_esquema_electric_projecte(project_id, preview_png=b64_data):
                st.session_state["foto_toast_msg"] = "Esquema elèctric desat correctament!"
                st.rerun()
