"""
Motor d'Optimització de Tall de Fusta (Cut List Optimizer) i Modelat de Mobles MD/Fusteria.
Suporta:
- Despecejament de mobles paramètrics (plantilles) o lliures.
- Agrupació automàtica de peces per gruix (MDF 3mm, 10mm, 16mm, 19mm, etc.).
- Algorisme Guillotine 2D Bin Packing amb pèrdua de fulla de serra (kerf).
- Respecte de la veta de la fusta (permet gir o orientació fixa).
- Generació de dades per a visualitzador 3D (Three.js) i diagrames de tall 2D (SVG/Canvas).
"""

from typing import List, Dict, Any, Tuple, Optional
import math
import json

# Mides estàndard de planxes comercials (en mm)
PRESETS_PLANXES = {
    "Magatzem Gran (2440 × 1220 mm)": {"llarg": 2440.0, "ample": 1220.0, "nom": "Planxa Gran 2440x1220"},
    "Mitjana Bricolatge (1220 × 600 mm)": {"llarg": 1220.0, "ample": 600.0, "nom": "Planxa Mitjana 1220x600"},
    "Bricolatge 1200 × 600 mm": {"llarg": 1200.0, "ample": 600.0, "nom": "Planxa 1200x600"},
    "Bricolatge 800 × 400 mm": {"llarg": 800.0, "ample": 400.0, "nom": "Tauler 800x400"},
    "Bricolatge 600 × 300 mm": {"llarg": 600.0, "ample": 300.0, "nom": "Tauler 600x300"},
    "Personalitzada (a mida)": {"llarg": 2000.0, "ample": 1000.0, "nom": "Personalitzada"}
}

# Gruixos habituals de MDF/Aglomerat/Contraplacat (en mm)
GRUIXOS_HABITUALS = [3.0, 5.0, 10.0, 12.0, 16.0, 18.0, 19.0, 22.0, 25.0, 30.0]

# Paleta de colors per distingir peces als diagrames
PALETA_PECES = [
    "#D97706", "#2563EB", "#059669", "#DC2626", "#7C3AED",
    "#DB2777", "#4F46E5", "#0891B2", "#CA8A04", "#16A34A",
    "#9333EA", "#EA580C", "#0284C7", "#65A30D", "#BE123C"
]

# ==============================================================================
# 1. PLANTILLES PARAMÈTRIQUES DE MOBLES
# ==============================================================================

def generar_peces_plantilla(
    tipus: str,
    alt: float,
    ample: float,
    fons: float,
    gruix_est: float = 19.0,
    gruix_fons: float = 3.0,
    num_prestatges: int = 3,
    amb_fons: bool = True,
    permet_gir_defecte: bool = True
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Genera les peces 2D i les posicions 3D per a una plantilla donada.
    Retorna: (peces_2d, peces_3d)
    Totes les dimensions en mil·límetres (mm).
    """
    peces: List[Dict[str, Any]] = []
    peces_3d: List[Dict[str, Any]] = []
    
    # Assignador de color consecutiu
    c_idx = 0
    def seguent_color():
        nonlocal c_idx
        col = PALETA_PECES[c_idx % len(PALETA_PECES)]
        c_idx += 1
        return col

    if tipus == "prestatgeria":
        # Amplada interior lliure
        ample_int = max(50.0, ample - (2 * gruix_est))
        alcada_int = max(50.0, alt - (2 * gruix_est))
        fons_prestatge = fons - (gruix_fons if amb_fons else 0.0)
        
        # 1. Costats laterals (2 unitats)
        c_col = seguent_color()
        peces.append({
            "id": "p_costat_esq",
            "nom": "Costat Lateral",
            "llarg": alt,
            "ample": fons,
            "gruix": gruix_est,
            "quantitat": 2,
            "permet_gir": permet_gir_defecte,
            "color": c_col
        })
        # 3D: Costat esquerre i dret
        peces_3d.append({
            "nom": "Costat Esquerre",
            "x": 0.0, "y": alt / 2.0, "z": fons / 2.0,
            "w": gruix_est, "h": alt, "d": fons,
            "color": c_col
        })
        peces_3d.append({
            "nom": "Costat Dret",
            "x": ample - gruix_est, "y": alt / 2.0, "z": fons / 2.0,
            "w": gruix_est, "h": alt, "d": fons,
            "color": c_col
        })

        # 2. Base i Sostre (2 unitats)
        tb_col = seguent_color()
        peces.append({
            "id": "p_sostre_base",
            "nom": "Sostre i Base",
            "llarg": ample_int,
            "ample": fons,
            "gruix": gruix_est,
            "quantitat": 2,
            "permet_gir": permet_gir_defecte,
            "color": tb_col
        })
        # 3D: Base i Sostre
        peces_3d.append({
            "nom": "Base Inferior",
            "x": gruix_est, "y": gruix_est / 2.0, "z": fons / 2.0,
            "w": ample_int, "h": gruix_est, "d": fons,
            "color": tb_col
        })
        peces_3d.append({
            "nom": "Sostre Superior",
            "x": gruix_est, "y": alt - (gruix_est / 2.0), "z": fons / 2.0,
            "w": ample_int, "h": gruix_est, "d": fons,
            "color": tb_col
        })

        # 3. Prestatges interiors (N unitats)
        if num_prestatges > 0:
            pr_col = seguent_color()
            peces.append({
                "id": "p_prestatges",
                "nom": "Prestatge Interior",
                "llarg": ample_int,
                "ample": fons_prestatge,
                "gruix": gruix_est,
                "quantitat": num_prestatges,
                "permet_gir": permet_gir_defecte,
                "color": pr_col
            })
            pas_y = alcada_int / (num_prestatges + 1)
            for i in range(num_prestatges):
                pos_y = gruix_est + ((i + 1) * pas_y)
                peces_3d.append({
                    "nom": f"Prestatge {i+1}",
                    "x": gruix_est, "y": pos_y, "z": fons_prestatge / 2.0,
                    "w": ample_int, "h": gruix_est, "d": fons_prestatge,
                    "color": pr_col
                })

        # 4. Panell posterior de fons (opcional)
        if amb_fons:
            fn_col = "#9CA3AF"  # Gris fons
            peces.append({
                "id": "p_fons_post",
                "nom": "Fons Posterior (Gruix prim)",
                "llarg": alt,
                "ample": ample,
                "gruix": gruix_fons,
                "quantitat": 1,
                "permet_gir": permet_gir_defecte,
                "color": fn_col
            })
            peces_3d.append({
                "nom": "Fons Posterior",
                "x": 0.0, "y": alt / 2.0, "z": fons - (gruix_fons / 2.0),
                "w": ample, "h": alt, "d": gruix_fons,
                "color": fn_col
            })

    elif tipus == "armari":
        # Armari amb portes frontals
        ample_int = max(50.0, ample - (2 * gruix_est))
        alcada_int = max(50.0, alt - (2 * gruix_est))
        fons_util = fons - gruix_est - (gruix_fons if amb_fons else 0.0) # Reserva per portes
        
        c_col = seguent_color()
        peces.append({
            "id": "p_costat_armari", "nom": "Costat Lateral",
            "llarg": alt, "ample": fons, "gruix": gruix_est, "quantitat": 2,
            "permet_gir": permet_gir_defecte, "color": c_col
        })
        peces_3d.append({"nom": "Costat Esquerre", "x": 0.0, "y": alt / 2.0, "z": fons / 2.0, "w": gruix_est, "h": alt, "d": fons, "color": c_col})
        peces_3d.append({"nom": "Costat Dret", "x": ample - gruix_est, "y": alt / 2.0, "z": fons / 2.0, "w": gruix_est, "h": alt, "d": fons, "color": c_col})

        tb_col = seguent_color()
        peces.append({
            "id": "p_sostre_base_armari", "nom": "Sostre i Base",
            "llarg": ample_int, "ample": fons, "gruix": gruix_est, "quantitat": 2,
            "permet_gir": permet_gir_defecte, "color": tb_col
        })
        peces_3d.append({"nom": "Base Inferior", "x": gruix_est, "y": gruix_est / 2.0, "z": fons / 2.0, "w": ample_int, "h": gruix_est, "d": fons, "color": tb_col})
        peces_3d.append({"nom": "Sostre Superior", "x": gruix_est, "y": alt - (gruix_est / 2.0), "z": fons / 2.0, "w": ample_int, "h": gruix_est, "d": fons, "color": tb_col})

        # Prestatge divisor superior
        pr_col = seguent_color()
        peces.append({
            "id": "p_prestatge_armari", "nom": "Prestatge Divisor",
            "llarg": ample_int, "ample": fons_util, "gruix": gruix_est, "quantitat": 1,
            "permet_gir": permet_gir_defecte, "color": pr_col
        })
        peces_3d.append({"nom": "Prestatge Maleter", "x": gruix_est, "y": alt - 350.0, "z": fons_util / 2.0, "w": ample_int, "h": gruix_est, "d": fons_util, "color": pr_col})

        # Portes frontals (2 unitats)
        porta_ample = (ample / 2.0) - 2.0
        porta_alt = alt - (gruix_est * 2.0) - 4.0
        po_col = seguent_color()
        peces.append({
            "id": "p_portes_armari", "nom": "Porta Batent",
            "llarg": porta_alt, "ample": porta_ample, "gruix": gruix_est, "quantitat": 2,
            "permet_gir": permet_gir_defecte, "color": po_col
        })
        peces_3d.append({"nom": "Porta Esquerra", "x": 2.0, "y": (alt / 2.0), "z": gruix_est / 2.0, "w": porta_ample, "h": porta_alt, "d": gruix_est, "color": po_col})
        peces_3d.append({"nom": "Porta Dreta", "x": porta_ample + 4.0, "y": (alt / 2.0), "z": gruix_est / 2.0, "w": porta_ample, "h": porta_alt, "d": gruix_est, "color": po_col})

        if amb_fons:
            fn_col = "#9CA3AF"
            peces.append({
                "id": "p_fons_armari", "nom": "Fons Posterior",
                "llarg": alt, "ample": ample, "gruix": gruix_fons, "quantitat": 1,
                "permet_gir": permet_gir_defecte, "color": fn_col
            })
            peces_3d.append({"nom": "Fons Posterior", "x": 0.0, "y": alt / 2.0, "z": fons - (gruix_fons / 2.0), "w": ample, "h": alt, "d": gruix_fons, "color": fn_col})

    elif tipus == "taula":
        # Taula / Escriptori senzill
        so_col = seguent_color()
        # Sobre de la taula
        peces.append({
            "id": "p_sobre_taula", "nom": "Sobre Taula / Escriptori",
            "llarg": ample, "ample": fons, "gruix": gruix_est, "quantitat": 1,
            "permet_gir": permet_gir_defecte, "color": so_col
        })
        peces_3d.append({"nom": "Sobre Taula", "x": 0.0, "y": alt - (gruix_est / 2.0), "z": fons / 2.0, "w": ample, "h": gruix_est, "d": fons, "color": so_col})

        pt_col = seguent_color()
        # Potes en panell lateral
        alt_pota = alt - gruix_est
        peces.append({
            "id": "p_potes_taula", "nom": "Pota Lateral Panell",
            "llarg": alt_pota, "ample": fons - 40.0, "gruix": gruix_est, "quantitat": 2,
            "permet_gir": permet_gir_defecte, "color": pt_col
        })
        peces_3d.append({"nom": "Pota Esquerra", "x": 20.0, "y": alt_pota / 2.0, "z": fons / 2.0, "w": gruix_est, "h": alt_pota, "d": fons - 40.0, "color": pt_col})
        peces_3d.append({"nom": "Pota Dreta", "x": ample - 20.0 - gruix_est, "y": alt_pota / 2.0, "z": fons / 2.0, "w": gruix_est, "h": alt_pota, "d": fons - 40.0, "color": pt_col})

        tr_col = seguent_color()
        # Faldó / Travesser posterior de reforç
        ample_trav = ample - 40.0 - (2 * gruix_est)
        peces.append({
            "id": "p_faldo_taula", "nom": "Faldó de Reforç Posterior",
            "llarg": ample_trav, "ample": 250.0, "gruix": gruix_est, "quantitat": 1,
            "permet_gir": permet_gir_defecte, "color": tr_col
        })
        peces_3d.append({"nom": "Faldó Posterior", "x": 20.0 + gruix_est, "y": alt - gruix_est - 125.0, "z": fons - 40.0, "w": ample_trav, "h": 250.0, "d": gruix_est, "color": tr_col})

    return peces, peces_3d


# ==============================================================================
# 2. ALGORISME D'OPTIMITZACIÓ DE TALL (2D GUILLOTINE BIN PACKING)
# ==============================================================================

class RectFree:
    """Representa un rectangle lliure disponible a la planxa."""
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def area(self) -> float:
        return self.w * self.h

class FullPlanxa:
    """Representa una planxa comercial física on s'aniran col·locant les peces."""
    def __init__(self, idx: int, llarg: float, ample: float, gruix: float, kerf: float):
        self.idx = idx
        self.llarg = llarg      # Dimensió en l'eix X (mm)
        self.ample = ample      # Dimensió en l'eix Y (mm)
        self.gruix = gruix      # Gruix de la planxa (mm)
        self.kerf = kerf        # Pèrdua de la serra (mm)
        self.free_rects: List[RectFree] = [RectFree(0.0, 0.0, llarg, ample)]
        self.placed_pieces: List[Dict[str, Any]] = []

    @property
    def total_area(self) -> float:
        return self.llarg * self.ample

    @property
    def used_area(self) -> float:
        return sum(p["w"] * p["h"] for p in self.placed_pieces)

    @property
    def aprofitament_pct(self) -> float:
        if self.total_area <= 0:
            return 0.0
        return round((self.used_area / self.total_area) * 100.0, 1)

    @property
    def residu_area(self) -> float:
        return max(0.0, self.total_area - self.used_area)


def optimitzar_tall_fusta(
    peces_input: List[Dict[str, Any]],
    mida_planxa: Dict[str, float],
    kerf: float = 3.5,
    permet_gir_global: bool = True
) -> Dict[str, Any]:
    """
    Executa l'algorisme de tall per a totes les peces.
    Agrupa per gruix automàticament i genera planxes independents per cada gruix.
    
    mida_planxa: {"llarg": 2440.0, "ample": 1220.0}
    kerf: gruix del disc de serra (3.0 a 4.0 mm)
    permet_gir_global: Si és True, s'aplica el camp permet_gir de cada peça.
                       Si és False, es respecta estrictament la veta (cap peça es gira).
    """
    planxa_w = float(mida_planxa.get("llarg", 2440.0))
    planxa_h = float(mida_planxa.get("ample", 1220.0))
    
    # 1. Expandir peces segons quantitat
    peces_expandides = []
    peces_totals_count = 0
    for p in peces_input:
        qty = int(p.get("quantitat", 1))
        peces_totals_count += qty
        for i in range(qty):
            peces_expandides.append({
                "id": f"{p.get('id', 'p')}_{i+1}",
                "nom": p.get("nom", "Peça"),
                "llarg": float(p.get("llarg", 100.0)),
                "ample": float(p.get("ample", 100.0)),
                "gruix": float(p.get("gruix", 19.0)),
                "permet_gir": bool(p.get("permet_gir", True)) and permet_gir_global,
                "color": p.get("color", "#D97706")
            })

    # 2. Agrupar peces per gruix
    gruixos_dict: Dict[float, List[Dict[str, Any]]] = {}
    for p in peces_expandides:
        g = p["gruix"]
        if g not in gruixos_dict:
            gruixos_dict[g] = []
        gruixos_dict[g].append(p)

    resultats_per_gruix = {}
    peces_que_no_caben = []
    total_planxes_global = 0

    # 3. Optimitzar cada grup de gruix de forma aïllada
    for gruix, llista_peces in sorted(gruixos_dict.items()):
        # Ordenar peces de més gran a més petita (Best-Fit Decreasing)
        # Prioritat: àrea descendent, després dimensió màxima descendent
        llista_peces.sort(key=lambda x: (x["llarg"] * x["ample"], max(x["llarg"], x["ample"])), reverse=True)

        planxes: List[FullPlanxa] = []
        
        for p in llista_peces:
            pw, ph = p["llarg"], p["ample"]
            can_rot = p["permet_gir"]
            
            # Comprovar si cap a la planxa en absolut
            fits_normal = (pw <= planxa_w and ph <= planxa_h)
            fits_rot = (ph <= planxa_w and pw <= planxa_h) if can_rot else False
            
            if not fits_normal and not fits_rot:
                peces_que_no_caben.append({
                    "nom": p["nom"],
                    "llarg": pw,
                    "ample": ph,
                    "gruix": gruix,
                    "motiu": f"Massa gran ({pw:.0f}×{ph:.0f} mm) per la planxa ({planxa_w:.0f}×{planxa_h:.0f} mm)"
                })
                continue

            # Buscar el millor buit lliure entre les planxes existents
            best_planxa = None
            best_rect_idx = -1
            best_fit_score = float("inf")
            best_rotated = False

            for pl in planxes:
                for r_idx, r in enumerate(pl.free_rects):
                    # Prova orientació normal
                    if pw <= r.w and ph <= r.h:
                        rem_w = r.w - pw
                        rem_h = r.h - ph
                        score = min(rem_w, rem_h)
                        if score < best_fit_score:
                            best_fit_score = score
                            best_planxa = pl
                            best_rect_idx = r_idx
                            best_rotated = False

                    # Prova orientació girada (90 graus) si es permet
                    if can_rot and ph <= r.w and pw <= r.h:
                        rem_w = r.w - ph
                        rem_h = r.h - pw
                        score = min(rem_w, rem_h)
                        if score < best_fit_score:
                            best_fit_score = score
                            best_planxa = pl
                            best_rect_idx = r_idx
                            best_rotated = True

            # Si no ha cabut a cap planxa existent, obrir una planxa nova
            if best_planxa is None:
                nou_idx = len(planxes) + 1
                nova_pl = FullPlanxa(nou_idx, planxa_w, planxa_h, gruix, kerf)
                planxes.append(nova_pl)
                best_planxa = nova_pl
                best_rect_idx = 0
                
                # Comprovar orientació a la nova planxa
                if pw <= planxa_w and ph <= planxa_h:
                    best_rotated = False
                elif can_rot and ph <= planxa_w and pw <= planxa_h:
                    best_rotated = True
                else:
                    best_rotated = False

            # Col·locar la peça al rectangle triat
            target_r = best_planxa.free_rects.pop(best_rect_idx)
            w_real = ph if best_rotated else pw
            h_real = pw if best_rotated else ph

            best_planxa.placed_pieces.append({
                "id": p["id"],
                "nom": p["nom"],
                "x": target_r.x,
                "y": target_r.y,
                "w": w_real,
                "h": h_real,
                "girada": best_rotated,
                "color": p["color"],
                "gruix": gruix
            })

            # Partició Guillotina del buit restant (incloent el kerf de la fulla de serra)
            # Retall horitzontal i vertical
            rem_x = target_r.x + w_real + kerf
            rem_w = max(0.0, target_r.w - w_real - kerf)
            
            rem_y = target_r.y + h_real + kerf
            rem_h = max(0.0, target_r.h - h_real - kerf)

            # Heurística de tall guillotinat més llarg (Shorter Axis Split)
            if rem_w > 0:
                best_planxa.free_rects.append(RectFree(rem_x, target_r.y, rem_w, target_r.h))
            if rem_h > 0:
                best_planxa.free_rects.append(RectFree(target_r.x, rem_y, target_r.w if rem_w <= 0 else (w_real + kerf), rem_h))

        # Recopilar estadístiques per aquest gruix
        planxes_data = []
        area_total_g = 0.0
        area_util_g = 0.0

        for pl in planxes:
            area_total_g += pl.total_area
            area_util_g += pl.used_area
            
            # Retalls útils (rectangles lliures amb mida superior a 150x150 mm)
            retalls_util = [
                {"x": r.x, "y": r.y, "w": r.w, "h": r.h}
                for r in pl.free_rects if r.w >= 150.0 and r.h >= 150.0
            ]

            planxes_data.append({
                "idx": pl.idx,
                "llarg": pl.llarg,
                "ample": pl.ample,
                "gruix": pl.gruix,
                "aprofitament_pct": pl.aprofitament_pct,
                "peces": pl.placed_pieces,
                "retalls_util": retalls_util,
                "peces_count": len(pl.placed_pieces)
            })

        total_planxes_global += len(planxes)
        aprofitament_global_g = round((area_util_g / area_total_g) * 100.0, 1) if area_total_g > 0 else 0.0

        resultats_per_gruix[f"{gruix:.0f}mm"] = {
            "gruix": gruix,
            "num_planxes": len(planxes),
            "area_total_m2": round(area_total_g / 1_000_000.0, 2),
            "area_util_m2": round(area_util_g / 1_000_000.0, 2),
            "aprofitament_pct": aprofitament_global_g,
            "planxes": planxes_data
        }

    return {
        "ok": len(peces_que_no_caben) == 0,
        "mida_planxa": {"llarg": planxa_w, "ample": planxa_h},
        "kerf": kerf,
        "permet_gir_global": permet_gir_global,
        "total_planxes_global": total_planxes_global,
        "peces_totals_count": peces_totals_count,
        "resultats_per_gruix": resultats_per_gruix,
        "peces_que_no_caben": peces_que_no_caben
    }


# ==============================================================================
# 3. GENERADOR DE VISOR 3D (HTML / THREE.JS)
# ==============================================================================

def generar_html_visor_3d(peces_3d: List[Dict[str, Any]], amplada_max: float = 1200.0) -> str:
    """
    Genera un visor 3D interactiu basat en Three.js i OrbitControls.
    Permet gir 360°, zoom, perspectiva, i botó per explosionar peces.
    """
    peces_json = json.dumps(peces_3d)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                color: #f1f5f9;
            }}
            #canvas-container {{
                width: 100%;
                height: 480px;
                position: relative;
            }}
            .toolbar {{
                position: absolute;
                top: 12px;
                left: 12px;
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(8px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 14px;
                display: flex;
                gap: 10px;
                align-items: center;
                z-index: 10;
                font-size: 13px;
            }}
            .btn-3d {{
                background: #3b82f6;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                transition: background 0.2s;
            }}
            .btn-3d:hover {{
                background: #2563eb;
            }}
            .btn-secondary {{
                background: rgba(255, 255, 255, 0.12);
                color: #f1f5f9;
            }}
            .btn-secondary:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
            .tooltip {{
                position: absolute;
                bottom: 12px;
                right: 12px;
                background: rgba(15, 23, 42, 0.75);
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 11px;
                color: #94a3b8;
                pointer-events: none;
            }}
        </style>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    </head>
    <body>
        <div id="canvas-container">
            <div class="toolbar">
                <span>🧊 <b>Model 3D Fusteria</b></span>
                <button class="btn-3d" id="btn-explode">💥 Vista Explosionada</button>
                <button class="btn-3d btn-secondary" id="btn-reset">🎯 Centrar Vista</button>
            </div>
            <div class="tooltip">🖱️ Clic esquerre: Girar | Roda: Zoom | Clic dret: Desplaçar</div>
        </div>

        <script>
            const peces = {peces_json};
            const container = document.getElementById('canvas-container');

            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0f172a);

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 10000);
            const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            // Il·luminació realista
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
            scene.add(ambientLight);

            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(1500, 2500, 1500);
            dirLight.castShadow = true;
            scene.add(dirLight);

            const dirLight2 = new THREE.DirectionalLight(0x93c5fd, 0.4);
            dirLight2.position.set(-1500, 1000, -1000);
            scene.add(dirLight2);

            // Terra subtil
            const gridHelper = new THREE.GridHelper(3000, 30, 0x334155, 0x1e293b);
            gridHelper.position.y = -2;
            scene.add(gridHelper);

            // Grup per contenir totes les peces
            const furnitureGroup = new THREE.Group();
            scene.add(furnitureGroup);

            // Calcular centre de masses per centrar càmera
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;

            const meshList = [];

            peces.forEach((p, idx) => {{
                const w = p.w || 100;
                const h = p.h || 100;
                const d = p.d || 100;

                const posX = p.x + (w / 2);
                const posY = p.y;
                const posZ = p.z;

                minX = Math.min(minX, p.x);
                maxX = Math.max(maxX, p.x + w);
                minY = Math.min(minY, p.y - (h / 2));
                maxY = Math.max(maxY, p.y + (h / 2));
                minZ = Math.min(minZ, p.z - (d / 2));
                maxZ = Math.max(maxZ, p.z + (d / 2));

                const geometry = new THREE.BoxGeometry(w, h, d);
                
                // Color càlid de fusta / MDF
                const baseColor = p.color || '#D97706';
                const material = new THREE.MeshStandardMaterial({{
                    color: new THREE.Color(baseColor),
                    roughness: 0.55,
                    metalness: 0.05
                }});

                const mesh = new THREE.Mesh(geometry, material);
                mesh.position.set(posX, posY, posZ);
                mesh.castShadow = true;
                mesh.receiveShadow = true;

                // Arestes definides per claredat tècnica
                const edges = new THREE.EdgesGeometry(geometry);
                const lineMaterial = new THREE.LineBasicMaterial({{ color: 0x1e293b, linewidth: 1.5 }});
                const wireframe = new THREE.LineSegments(edges, lineMaterial);
                mesh.add(wireframe);

                mesh.userData = {{
                    origX: posX,
                    origY: posY,
                    origZ: posZ,
                    nom: p.nom
                }};

                meshList.push(mesh);
                furnitureGroup.add(mesh);
            }});

            const centerX = (minX + maxX) / 2 || 0;
            const centerY = (minY + maxY) / 2 || 300;
            const centerZ = (minZ + maxZ) / 2 || 0;

            // Centrar el moble a l'origen
            furnitureGroup.position.set(-centerX, 0, -centerZ);

            const maxDim = Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 800;
            camera.position.set(maxDim * 1.5, maxDim * 1.2, maxDim * 1.8);
            controls.target.set(0, centerY, 0);
            controls.update();

            // Vista Explosionada
            let isExploded = false;
            document.getElementById('btn-explode').addEventListener('click', () => {{
                isExploded = !isExploded;
                document.getElementById('btn-explode').textContent = isExploded ? '📦 Vista Encaixada' : '💥 Vista Explosionada';
                
                meshList.forEach(m => {{
                    if (isExploded) {{
                        const dx = (m.userData.origX - centerX) * 0.45;
                        const dy = (m.userData.origY - centerY) * 0.45;
                        const dz = (m.userData.origZ - centerZ) * 0.45;
                        m.position.set(m.userData.origX + dx, m.userData.origY + dy, m.userData.origZ + dz);
                    }} else {{
                        m.position.set(m.userData.origX, m.userData.origY, m.userData.origZ);
                    }}
                }});
            }});

            // Reset de Càmera
            document.getElementById('btn-reset').addEventListener('click', () => {{
                camera.position.set(maxDim * 1.5, maxDim * 1.2, maxDim * 1.8);
                controls.target.set(0, centerY, 0);
                controls.update();
            }});

            // Responsive
            window.addEventListener('resize', () => {{
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }});

            // Animació
            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
        </script>
    </body>
    </html>
    """
    return html


# ==============================================================================
# 4. GENERADOR DE DIAGRAMA DE TALL DE PLANXES (SVG / HTML)
# ==============================================================================

def generar_svg_planxa_tall(planxa: Dict[str, Any], amplada_visual: int = 850) -> str:
    """
    Genera un diagrama vectorial SVG de la planxa amb totes les peces col·locades,
    les línies de tall i les cotes principals.
    """
    llarg_real = float(planxa.get("llarg", 2440.0))
    ample_real = float(planxa.get("ample", 1220.0))
    peces = planxa.get("peces", [])
    retalls = planxa.get("retalls_util", [])
    
    # Escala SVG
    escala = amplada_visual / llarg_real
    alcada_visual = int(ample_real * escala)
    
    margin_top = 35
    margin_left = 45
    svg_w = amplada_visual + margin_left + 40
    svg_h = alcada_visual + margin_top + 45

    svg_parts = [
        f'<svg viewBox="0 0 {svg_w} {svg_h}" width="100%" height="{svg_h}px" xmlns="http://www.w3.org/2000/svg" style="background:#0f172a; border-radius:8px; font-family:-apple-system, sans-serif;">',
        # Fons de la planxa
        f'<rect x="{margin_left}" y="{margin_top}" width="{amplada_visual}" height="{alcada_visual}" fill="#1e293b" stroke="#475569" stroke-width="2" rx="4"/>',
        # Cotes de la planxa
        f'<text x="{margin_left + amplada_visual/2}" y="{margin_top - 12}" fill="#94a3b8" font-size="12" font-weight="600" text-anchor="middle">← {llarg_real:.0f} mm →</text>',
        f'<text x="{margin_left - 12}" y="{margin_top + alcada_visual/2}" fill="#94a3b8" font-size="12" font-weight="600" text-anchor="middle" transform="rotate(-90 {margin_left - 12},{margin_top + alcada_visual/2})">← {ample_real:.0f} mm →</text>'
    ]

    # Dibuixar retalls sobrants (gris amb tramat suau)
    for r in retalls:
        rx = margin_left + (r["x"] * escala)
        ry = margin_top + (r["y"] * escala)
        rw = r["w"] * escala
        rh = r["h"] * escala
        if rw > 15 and rh > 15:
            svg_parts.append(
                f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="#334155" opacity="0.4" stroke="#64748b" stroke-dasharray="3,3"/>'
                f'<text x="{rx + rw/2:.1f}" y="{ry + rh/2 + 4:.1f}" fill="#94a3b8" font-size="10" text-anchor="middle">Retall ({r["w"]:.0f}×{r["h"]:.0f})</text>'
            )

    # Dibuixar peces col·locades
    for p in peces:
        px = margin_left + (p["x"] * escala)
        py = margin_top + (p["y"] * escala)
        pw = p["w"] * escala
        ph = p["h"] * escala
        col = p.get("color", "#D97706")
        nom = p.get("nom", "Peça")
        rot = " 🔄" if p.get("girada") else ""
        
        # Rectangle de la peça
        svg_parts.append(f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="{ph:.1f}" fill="{col}" opacity="0.88" stroke="#ffffff" stroke-width="1.5" rx="3"/>')
        
        # Etiqueta de text si cap
        if pw > 45 and ph > 25:
            font_sz = 11 if (pw > 70 and ph > 40) else 9
            svg_parts.append(f'<text x="{px + pw/2:.1f}" y="{py + ph/2 - 2:.1f}" fill="#ffffff" font-size="{font_sz}" font-weight="600" text-anchor="middle">{nom}{rot}</text>')
            svg_parts.append(f'<text x="{px + pw/2:.1f}" y="{py + ph/2 + 12:.1f}" fill="#fef08a" font-size="{font_sz - 1}" font-weight="500" text-anchor="middle">{p["w"]:.0f} × {p["h"]:.0f}</text>')

    svg_parts.append('</svg>')
    return "".join(svg_parts)
