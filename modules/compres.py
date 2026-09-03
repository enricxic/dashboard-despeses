import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from core.db import get_supabase_client, fetch_all_supabase, update_db_row, log_action, insert_db_row

import re
import urllib.parse
from PIL import Image
import pytesseract
import json
import base64
import requests

def clear_form_state(prefix: str):
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]

# --- TICKET SUPER FUNCTIONALITY ---
def normalitzar_text(text):
    if not text:
        return ""
    text_str = str(text)
    
    # Fix common OCR mistakes specifically inside words
    # Replace numbers with letters if they look like letters (like 4MB -> AMB, xISGR4 -> XISTORRA, etc.)
    text_str = re.sub(r'\b4MB\b', 'AMB', text_str, flags=re.IGNORECASE)
    text_str = re.sub(r'\b4\b', 'A', text_str, flags=re.IGNORECASE)
    text_str = re.sub(r'xISGR\s*4', 'XISTORRA', text_str, flags=re.IGNORECASE)
    text_str = re.sub(r'xISG\s*R\s*4', 'XISTORRA', text_str, flags=re.IGNORECASE)
    
    import unicodedata
    text_normalitzat = unicodedata.normalize('NFKD', text_str)
    text_sense_diacritics = ''.join(
        c for c in text_normalitzat 
        if not unicodedata.combining(c) and (c.isalnum() or c.isspace())
    )
    return re.sub(r'\s+', ' ', text_sense_diacritics.lower()).strip()

def translate_spanish_to_catalan_for_matching(text):
    text_lower = text.lower()
    translations = {
        'chocolate': 'xocolata',
        'maiz': 'blat de moro',
        'maíz': 'blat de moro',
        'lavavaj': 'rentavaixella',
        'pistacho': 'festuc',
        'conservas': 'sardina',
        'pasta': 'helixs',
        'ocolate': 'xocolata',
    }
    for es, ca in translations.items():
        if es in text_lower:
            text_lower = text_lower.replace(es, ca)
    return text_lower

def map_product_to_category(product_name):
    best_family = "extres"
    best_article = "varis"
    prod_norm = normalitzar_text(product_name)
    
    # Custom OCR repair rules
    if 'tation' in prod_norm or 'temptation' in prod_norm or 'vche' in prod_norm or 'cry' in prod_norm or 'cons nata' in prod_norm:
        return 'extres', 'Gelat'
    if 'seberg' in prod_norm or 'ent am' in prod_norm or 'ciame' in prod_norm or 'enciam' in prod_norm or 'iceberg' in prod_norm:
        return 'verdura', 'Enciam'
    if 'tomaquet' in prod_norm or 'xcemat' in prod_norm or 'xocmat' in prod_norm:
        return 'verdura', 'Tomàquet'
    if 'pebrot' in prod_norm or 'vermell' in prod_norm or 'vermel' in prod_norm or ('2.19' in prod_norm and 'k' in prod_norm) or ('2,19' in prod_norm and 'k' in prod_norm):
        return 'verdura', 'Pebrot'
    if 'melo' in prod_norm or ('1.29' in prod_norm and 'k' in prod_norm) or ('1,29' in prod_norm and 'k' in prod_norm):
        return 'fruita', 'Meló'
    if 'pit' in prod_norm and ('gall' in prod_norm or 'dindi' in prod_norm or 'gal' in prod_norm or 'pinnt' in prod_norm):
        return 'carn', 'Pit Gall dindi'
    if 'trol' in prod_norm or 'truita' in prod_norm or 'tntegral' in prod_norm:
        return 'verdura', 'Amanida' # Maps to the standard family for Truita/Amanida if not exact
    if 'suetatl' in prod_norm or 'lleixiu' in prod_norm:
        return 'neteja', 'Leixiu'
    if 'sunder' in prod_norm or 'sindria' in prod_norm:
        return 'fruita', 'Xindria'
    if 'mantogs' in prod_norm or 'mantega' in prod_norm:
        return 'lactics', 'Mantega'
    if 'rmse' in prod_norm or 'formatge' in prod_norm or 'untar' in prod_norm:
        return 'lactics', 'Formatge'

    articles_map = cat_config.get("articles_compres", {})
    for fam, articles in articles_map.items():
        for art in articles:
            art_norm = normalitzar_text(art)
            if len(art_norm) <= 3:
                if re.search(r'\b' + re.escape(art_norm) + r'\b', prod_norm):
                    return fam, art
            else:
                if art_norm in prod_norm or prod_norm in art_norm:
                    return fam, art
                    
    for fam in cat_config.get("families_compres", []):
        fam_norm = normalitzar_text(fam)
        if len(fam_norm) <= 3:
            if re.search(r'\b' + re.escape(fam_norm) + r'\b', prod_norm):
                articles = articles_map.get(fam, ["varis"])
                return fam, articles[0]
        else:
            if fam_norm in prod_norm:
                articles = articles_map.get(fam, ["varis"])
                return fam, articles[0]
                
    return best_family, best_article
 
def load_product_mappings():
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_nom = fetch_all_supabase(supabase, 'tb_noms_producte')
        df_prod = fetch_all_supabase(supabase, 'tb_productes')
        df_merged = pd.merge(df_nom, df_prod, on='idProducte', how='inner')
        return df_merged
    except Exception as e:
        print(f"Error loading product mappings from database: {e}")
        return pd.DataFrame()
 
def find_product_in_db(product_name, supermercat, df_mapping):
    if df_mapping.empty or not product_name:
        return None
        
    nom_norm = normalitzar_text(product_name)
    if not nom_norm:
        return None
        
    # Filter by supermercat first (case-insensitive)
    df_super = df_mapping[df_mapping['supermercat'].astype(str).str.lower() == str(supermercat).lower()]
    if df_super.empty:
        df_super = df_mapping
        
    # 1. Exact match on nom_super
    for _, row in df_super.iterrows():
        if nom_norm == normalitzar_text(row['nom_super']):
            return {
                'nomEstandard': row['nom_estandard'],
                'familia': row['familia'],
                'article': row['nom_estandard'],
                'nom_super': row['nom_super']
            }
            
    # 2. Partial match on nom_super (one contains the other)
    for _, row in df_super.iterrows():
        super_norm = normalitzar_text(row['nom_super'])
        if super_norm in nom_norm or nom_norm in super_norm:
            return {
                'nomEstandard': row['nom_estandard'],
                'familia': row['familia'],
                'article': row['nom_estandard'],
                'nom_super': row['nom_super']
            }
            
    # 3. Direct match on nom_estandard (standard product name)
    for _, row in df_super.iterrows():
        est_norm = normalitzar_text(row['nom_estandard'])
        if nom_norm == est_norm or est_norm in nom_norm or nom_norm in est_norm:
            return {
                'nomEstandard': row['nom_estandard'],
                'familia': row['familia'],
                'article': row['nom_estandard'],
                'nom_super': row['nom_super']
            }
            
    # 4. Keyword / Word matching (similar to ocr_ticket.py)
    paraules_nom = set(nom_norm.split())
    best_word_match = None
    best_word_ratio = 0.0
    for _, row in df_super.iterrows():
        super_norm = normalitzar_text(row['nom_super'])
        paraules_super = set(super_norm.split())
        
        # Count matching words (length >= 2)
        coincidencies = 0
        for p_nom in paraules_nom:
            if len(p_nom) < 2:
                continue
            for p_super in paraules_super:
                if len(p_super) < 2:
                    continue
                if p_nom == p_super or (len(p_nom) > 4 and len(p_super) > 4 and (p_nom in p_super or p_super in p_nom)):
                    coincidencies += 1
                    break
        
        if len(paraules_nom) > 0:
            ratio = coincidencies / len(paraules_nom)
        else:
            ratio = 0.0
            
        if ratio > best_word_ratio and ratio >= 0.5:
            best_word_ratio = ratio
            best_word_match = row

    if best_word_match is not None:
        return {
            'nomEstandard': best_word_match['nom_estandard'],
            'familia': best_word_match['familia'],
            'article': best_word_match['nom_estandard'],
            'nom_super': best_word_match['nom_super']
        }

    # 5. Fuzzy match using SequenceMatcher (similarity >= 0.7)
    import difflib
    best_match = None
    best_ratio = 0.0
    for _, row in df_super.iterrows():
        super_norm = normalitzar_text(row['nom_super'])
        ratio = difflib.SequenceMatcher(None, nom_norm, super_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = row
            
    if best_ratio >= 0.60:  # Set to a robust 0.60 since the new preprocessing is very clean
        return {
            'nomEstandard': best_match['nom_estandard'],
            'familia': best_match['familia'],
            'article': best_match['nom_estandard'],
            'nom_super': best_match['nom_super']
        }
            
    # 6. Global match fallback (ignore supermarket filter)
    if len(df_super) < len(df_mapping):
        for _, row in df_mapping.iterrows():
            super_norm = normalitzar_text(row['nom_super'])
            if nom_norm == super_norm or super_norm in nom_norm or nom_norm in super_norm:
                return {
                    'nomEstandard': row['nom_estandard'],
                    'familia': row['familia'],
                    'article': row['nom_estandard'],
                    'nom_super': row['nom_super']
                }
            est_norm = normalitzar_text(row['nom_estandard'])
            if nom_norm == est_norm or est_norm in nom_norm or nom_norm in est_norm:
                return {
                    'nomEstandard': row['nom_estandard'],
                    'familia': row['familia'],
                    'article': row['nom_estandard'],
                    'nom_super': row['nom_super']
                }
                
    return None

def group_duplicate_ticket_items(items):
    grouped = {}
    for i, item in enumerate(items):
        if item['article'] == 'pendent':
            key = (item['familia'], item['article'], item['preuUnit'], i)
        else:
            key = (item['familia'], item['article'], item['preuUnit'])
        
        if key not in grouped:
            grouped[key] = {
                'familia': item['familia'],
                'article': item['article'],
                'pes': item['pes'],
                'quantitat': item['quantitat'],
                'preuUnit': item['preuUnit'],
                'prom': item['prom'],
                'totLinea': item['totLinea'],
                'rebost': item['rebost'],
                'nom_brut': item.get('nom_brut', '')
            }
        else:
            grouped[key]['quantitat'] += item['quantitat']
            try:
                grouped[key]['pes'] = float(grouped[key]['pes']) + float(item['pes'])
            except Exception:
                val1 = str(grouped[key]['pes'])
                val2 = str(item['pes'])
                grouped[key]['pes'] = val1 if val1 == val2 else f"{val1}, {val2}"
            grouped[key]['prom'] += item['prom']
            grouped[key]['totLinea'] += item['totLinea']
    return list(grouped.values())


def save_unknown_products(parsed_items, supermercat):
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        df_nom = fetch_all_supabase(supabase, 'tb_noms_producte')
        
        if not df_nom.empty:
            df_super = df_nom[df_nom['supermercat'].astype(str).str.lower() == str(supermercat).lower()]
            existing_names = set(df_super['nom_super'].dropna().apply(lambda x: normalitzar_text(x)))
        else:
            existing_names = set()
            
        new_rows = []
        for item in parsed_items:
            nom_brut = item.get('nom_brut', '').strip()
            if not nom_brut:
                continue
                
            nom_norm = normalitzar_text(nom_brut)
            if not nom_norm:
                continue
                
            # If not in existing names, we need to add it
            if nom_norm not in existing_names:
                new_rows.append({
                    "supermercat": supermercat,
                    "nom_super": nom_brut,
                    "similitud_minima": 0.7,
                    "idProducte": None,
                    "tipus": None,
                    "unitat": None,
                    "mesura": None
                })
                existing_names.add(nom_norm)
                
        if new_rows:
            supabase.table("tb_noms_producte").insert(new_rows).execute()
            print(f"Saved {len(new_rows)} new unknown products to tb_noms_producte for {supermercat}.")
    except Exception as e:
        print(f"Error saving unknown products: {e}")

def parse_default_ticket(text_content):
    # Log Streamlit OCR text
    try:
        import os
        os.makedirs("C:/Users/Usuari/.gemini/antigravity/brain/98896f4c-68da-443a-b920-acd856bccd79/scratch", exist_ok=True)
        with open("C:/Users/Usuari/.gemini/antigravity/brain/98896f4c-68da-443a-b920-acd856bccd79/scratch/debug_ocr.log", "w", encoding="utf-8") as f_log:
            f_log.write("--- NEW PARSE ---\n")
            f_log.write(text_content)
            f_log.write("\n-----------------\n")
    except Exception as e_log:
        pass
        
    df_mapping = load_product_mappings()
    lines = text_content.split('\n')
    
    try:
        st.session_state["ticket_discount"] = 0.0
    except Exception:
        pass
    
    # 1. Determine scan zone: between headers and TOTAL COMPRA GRUPO DIA / OFERTES
    in_products_zone = False
    product_lines_text = []
    coupon_lines_text = []
    in_coupons_zone = False
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        line_upper = line_clean.upper()
        
        # End zone check
        if (any(kw in line_upper for kw in [
            'TOTAL COMPRA', 'TOTAL A PAGAR', 'TOTAL ESTALVI', 'TOTAL ESTALVE', 
            'TOTAL COMPRA GRUPO DIA', 'TOTAL COMPRA GRUPC CTA', 'TOTAL', 
            'TARGETA', 'TARGETA BANCÀRIA', 'TARJETA', 'TUTAL', 'TAROETA', 
            'BANCARTA', 'BANCARIA', 'BASE IMPOSABLE', 'IVA BASE', 'VISA', 
            'DEBIT', 'DEBITE', 'IMPORT:', "DESGLÒS D'IVA", "DESGLOS D'IVA", 'EFECTIU', 'CANVI', 'ENTREGAT', 'IVA %', 'SUBTOTAL', 'IVA INCLOS', 'I.V.A.'
        ]) or any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in [
            'TOTAL COMPRA', 'TOTAL A PAGAR', 'TOTAL ESTALVI', 'TOTAL ESTALVE', 
            'TOTAL COMPRA GRUPO DIA', 'TOTAL COMPRA GRUPC CTA', 'TOTAL', 
            'TARGETA', 'TARGETA BANCÀRIA', 'TARJETA'
        ])):
            break
            
        # Coupons zone transition check
        if any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in ['OFERTES', 'OFERTAS', 'CUPONS', 'CLUBDIA', 'CPERTLS']):
            in_coupons_zone = True
            continue
            
        if in_coupons_zone:
            coupon_lines_text.append(line_clean)
            continue
            
        # Header check to start scan zone
        if not in_products_zone:
            if any(kw in line_upper for kw in ['DESCRIPCIÓ', 'DESCRIPCION', 'QUANTITAT', 'PVP/UNIT', 'IMPORT €', 'DESCRIPC', 'DESCRIPCI', 'VSPRIPC', 'P.UNIT', 'IMP.']):
                in_products_zone = True
            continue
            
        if in_products_zone:
            # Skip duplicate headers
            if any(kw in line_upper for kw in ['DESCRIPCIÓ', 'DESCRIPCION', 'QUANTITAT', 'PVP/UNIT', 'IMPORT €', 'DESCRIPC', 'DESCRIPCI', 'QA TA PAP']):
                continue
            product_lines_text.append(line_clean)
            
    # Fallback: if header detection failed to capture any product lines, treat all lines before coupons/totals as products
    if len(product_lines_text) == 0:
        in_coupons_zone = False
        coupon_lines_text = []
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
            line_upper = line_clean.upper()
            if any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in ['TOTAL COMPRA', 'TOTAL A PAGAR', 'TOTAL ESTALVI', 'TOTAL ESTALVE', 'TOTAL COMPRA GRUPO DIA', 'TOTAL COMPRA GRUPC CTA']):
                break
            if any(re.search(r'\b' + re.escape(kw) + r'\b', line_upper) for kw in ['OFERTES', 'OFERTAS', 'CUPONS', 'CLUBDIA', 'CPERTLS']):
                in_coupons_zone = True
                continue
            if in_coupons_zone:
                coupon_lines_text.append(line_clean)
                continue
            # Skip typical header/metadata lines
            if any(kw in line_upper for kw in ['GRUPO', 'OBRIM', 'HORARI', 'FACTURA', 'N.FACT', 'N.CAIXA', 'N.CATXA', 'TELF', 'TEL.']):
                continue
            product_lines_text.append(line_clean)
            
    # 2. Sequential scanning to count and group lines (product + optional weight line)
    raw_products = []
    idx = 0
    while idx < len(product_lines_text):
        line = product_lines_text[idx]
        line_upper = line.upper()
        
        # Check if it has a price
        preu = 0.0
        price_match = None
        bonarea_qty = 1
        bonarea_match = re.search(r'^(.*?)\s+(?:(\d+)\s*[xX]\s*\d+[,.]\d+\s+)?(\d+)[.,](\d{2})\s+\d+[.,]\d{2}$', line.strip())
        
        if bonarea_match:
            nom_brut = bonarea_match.group(1).replace('.', '').strip()
            if bonarea_match.group(2):
                bonarea_qty = int(bonarea_match.group(2))
            preu = float(f"{bonarea_match.group(3)}.{bonarea_match.group(4)}")
            price_match = bonarea_match
        else:
            # Dia tickets have a price followed by IVA letter (A, B, C). OCR sometimes reads A as 4 or 4/A, B as 8 or 3, etc.
            # Price check with optional trailing IVA character and optional dashes/spaces
            price_match_std = re.search(r'(\d+)\s*[\.,\s;:]\s*(\d{2})(?:\s*[A-Z834\-©]+)?\s*[^a-zA-Z0-9]*$', line.strip())
            if price_match_std:
                preu = float(f"{price_match_std.group(1)}.{price_match_std.group(2)}")
                price_match = price_match_std
            else:
                # Fallback for three/four digits with missed separator, e.g. 222A -> 2.22
                price_match_missed = re.search(r'\s+(\d+)(\d{2})(?:\s*[A-Z834\-©]+)?\s*[^a-zA-Z0-9]*$', line.strip())
                if price_match_missed:
                    preu = float(f"{price_match_missed.group(1)}.{price_match_missed.group(2)}")
                    if preu > 50.0:
                        preu = 0.0
                        price_match = None
                    price_match = price_match_missed
                else:
                    # Fallback for letters like O/G/0 at start of cents (e.g. G95 -> 0.95, G95 - -> 0.95)
                    g_match = re.search(r'\b[GgOo0]\s*[\.,\s;:]*\s*(\d{2})(?:\s*[A-Z834\-©]+)?\s*[^a-zA-Z0-9]*$', line.strip())
                    if g_match:
                        preu = float(f"0.{g_match.group(1)}")
                        price_match = g_match
                
        # Parse product name
        if price_match and not bonarea_match:
            nom_brut = line[:price_match.start()].strip()
        elif not bonarea_match:
            nom_brut = line
            
        # Clean trailing letters/spaces/noise and specifically Dia IVA trailing characters/garbage
        nom_brut = re.sub(r'[\s\-\+\|0-9]+$', '', nom_brut).strip()
        nom_brut = re.sub(r'\s+[A-Z834]$', '', nom_brut).strip()
        nom_brut = re.sub(r'\s+[a-zA-Z]$', '', nom_brut).strip() # strip single trailing letter representing IVA if any left
        
        # Check if the line is a void/annulment (starts with ANUL. or has negative price)
        is_void = False
        if 'ANUL.' in line_upper or 'ANULACIO' in line_upper:
            is_void = True
            nom_brut = re.sub(r'^\s*ANUL\b\.?\s*', '', nom_brut, flags=re.IGNORECASE).strip()
            nom_brut = re.sub(r'^\s*ANULACIO\b\.?\s*', '', nom_brut, flags=re.IGNORECASE).strip()
            
        if price_match:
            prefix = line[:price_match.start()].strip()
            if prefix.endswith('-'):
                is_void = True
                nom_brut = re.sub(r'\s*\-$', '', nom_brut).strip()
                
        # Skip typical "Import linia: 2,98" metadata lines
        if 'IMPORT LIN' in nom_brut.upper():
            idx += 1
            continue
            
        # If name doesn't contain at least 3 letters, or starts with a long number (barcode), it's garbage
        if not nom_brut or len([c for c in nom_brut if c.isalpha()]) < 3 or re.match(r'^\d{5,}', nom_brut):
            idx += 1
            continue
            
        # Skip Novavenda barcode + quantity lines (e.g. "5449000275165 1 x ")
        if re.match(r'^\d{7,14}\s+\d+\s*[xX]$', nom_brut):
            idx += 1
            continue
            
        # Check if the NEXT line is a weight line (starts with digit and contains 'kg')
        pes_kg = 0.0
        tot_val = 0.0
        extracted_preu_kg = 0.0
        has_next_weight = False
        if idx + 1 < len(product_lines_text):
            next_line = product_lines_text[idx + 1]
            if 'kg' in next_line.lower() or 'e/kg' in next_line.lower() or '/kg' in next_line.lower():
                pes_match = re.search(r'(\d+[\.,]\d{3})', next_line)
                if pes_match:
                    pes_kg = float(pes_match.group(1).replace(',', '.'))
                    
                # Extract preu_kg and totLine value from weight line
                match_kg_price = re.search(r'(\d+[\.,]\d{2})\s*(?:€/kg|/kg)', next_line, re.IGNORECASE)
                if match_kg_price:
                    extracted_preu_kg = float(match_kg_price.group(1).replace(',', '.'))
                else:
                    extracted_preu_kg = 0.0
                    
                # The total is usually the last number with exactly 2 decimals (ignoring the 3 decimal weight)
                prices_match = list(re.finditer(r'(\d+)[\.,](\d{2})(?!\d)', next_line))
                if prices_match:
                    last_price = float(f"{prices_match[-1].group(1)}.{prices_match[-1].group(2)}")
                    if match_kg_price and prices_match[-1].start() == match_kg_price.start(1):
                        # The last price found IS the kg price, which means total price is missing from this line
                        tot_val = round(pes_kg * extracted_preu_kg, 2)
                    else:
                        tot_val = last_price
                elif extracted_preu_kg > 0 and pes_kg > 0:
                    tot_val = round(pes_kg * extracted_preu_kg, 2)
                else:
                    tot_val = 0.0
                has_next_weight = True
                
        # Resolve quantities (e.g. '3 x' or just '3 ' at start of line for Mercadona)
        if bonarea_match:
            quantitat = bonarea_qty
        else:
            quantitat = 1
        quant_match = re.search(r'^(\d+)\s*[xX]\s*', nom_brut)
        if quant_match:
            quantitat = int(quant_match.group(1))
            nom_brut = re.sub(r'^(\d+)\s*[xX]\s*', '', nom_brut).strip()
        else:
            # Check for Mercadona style: starts with a number and then space, e.g., "1 PASTÍS TONYINA"
            # We map 'l', 'i', 'I', '1' to 1
            mercadona_quant_match = re.search(r'^([1liI]|\d+)\s+(?![gG]\b|[kK][gG]\b|[mM][lL]\b)([a-zA-Z].*)', nom_brut)
            if mercadona_quant_match:
                q_val = mercadona_quant_match.group(1)
                if q_val in ['l', 'i', 'I', '1']:
                    quantitat = 1
                else:
                    quantitat = int(q_val)
                nom_brut = mercadona_quant_match.group(2).strip()
            
        # 3. Search in TBNomsProducte and match against TBProductes (via df_mapping)
        ticket_super = st.session_state.get("ticket_super_val", "Dia")
        
        # Look up in DB first to check for high confidence match
        db_match = find_product_in_db(nom_brut, ticket_super, df_mapping)
        nom_super_val = ""
        if db_match:
            fam, art = db_match['familia'], db_match['nomEstandard']
            nom_super_val = db_match.get('nom_super', '')
        else:
            fam, art = 'Pendent', 'pendent'
            nom_super_val = nom_brut

        if has_next_weight:
            preu_unitat = round(tot_val / quantitat, 2) if tot_val > 0.0 else 0.0
            import_total = tot_val
        else:
            preu_unitat = preu if preu > 0.0 else (round(tot_val / quantitat, 2) if tot_val > 0.0 else 0.0)
            import_total = quantitat * preu_unitat
        
        if preu_unitat > 1000.0:
            preu_unitat = 0.0
        if import_total > 1000.0:
            import_total = 0.0
        # Duplicate product price fallback
        if preu_unitat == 0.0 and len(raw_products) > 0:
            prev_item = raw_products[-1]
            if prev_item['article'] == art and art != 'pendent' and prev_item['preuUnit'] > 0.0:
                preu_unitat = prev_item['preuUnit']
                
        if is_void:
            quantitat = -quantitat
            import_total = -import_total
        
        raw_products.append({
            'familia': fam,
            'article': art,
            'pes': int(pes_kg * 1000) if pes_kg > 0.0 else 0,
            'quantitat': quantitat,
            'preuUnit': preu_unitat,
            'prom': 0.0,
            'totLinea': import_total,
            'rebost': None,
            'nom_brut': nom_brut,
            'nom_super': nom_super_val
        })
        
        idx += 2 if has_next_weight else 1
        
    # 4. Parse discounts and coupons
    discounts = []
    for line in coupon_lines_text:
        discount_match = re.search(r'([\-\+]\s*\d+[\.,]\d{2})', line)
        if discount_match:
            val = abs(float(re.sub(r'\s+', '', discount_match.group(1)).replace(',', '.')))
            desc_text = line[:discount_match.start()].strip()
            desc_text = re.sub(r'^[\s\-\+\|0OCoO%0-9\.]+', '', desc_text).strip()
            discounts.append({'text': desc_text, 'val': val})
            
    # Apply discounts to parsed products
    for disc in discounts:
        disc_text = disc['text'].lower()
        disc_text_ca = translate_spanish_to_catalan_for_matching(disc_text)
        best_match_idx = -1
        best_ratio = 0.0
        
        for idx, item in enumerate(raw_products):
            art_lower = item['article'].lower()
            orig_lower = item['nom_brut'].lower()
            super_lower = item.get('nom_super', '').lower()
            
            ratio_std = max(
                difflib.SequenceMatcher(None, disc_text, art_lower).ratio(),
                difflib.SequenceMatcher(None, disc_text_ca, art_lower).ratio()
            )
            ratio_orig = max(
                difflib.SequenceMatcher(None, disc_text, orig_lower).ratio(),
                difflib.SequenceMatcher(None, disc_text_ca, orig_lower).ratio()
            )
            ratio_super = 0.0
            if super_lower:
                ratio_super = max(
                    difflib.SequenceMatcher(None, disc_text, super_lower).ratio(),
                    difflib.SequenceMatcher(None, disc_text_ca, super_lower).ratio()
                )
            
            ratio = max(ratio_std, ratio_orig, ratio_super)
            
            # Substring bonus for words >= 4 characters
            if len(disc_text) >= 4:
                if (disc_text in art_lower or disc_text_ca in art_lower or 
                    disc_text in orig_lower or disc_text_ca in orig_lower or
                    (super_lower and (disc_text in super_lower or disc_text_ca in super_lower))):
                    ratio = max(ratio, 0.95)
                    
            # Substring bonus for clean keywords of discount (e.g. split and check)
            clean_words = [w for w in re.split(r'[^a-zA-Z0-9]', disc_text_ca) if len(w) >= 4]
            for w in clean_words:
                if w in art_lower or w in orig_lower or (super_lower and w in super_lower):
                    ratio = max(ratio, 0.90)
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_idx = idx
                
        if best_ratio >= 0.4:
            raw_products[best_match_idx]['prom'] += disc['val']
            raw_products[best_match_idx]['totLinea'] = max(0.0, (raw_products[best_match_idx]['quantitat'] * raw_products[best_match_idx]['preuUnit']) - raw_products[best_match_idx]['prom'])
            
    # Keep recognized items even with 0.0 price, but discard 'pendent' with 0.0 or negative price (typically garbage lines)
    raw_products = [item for item in raw_products if item['article'] != 'pendent' or item['totLinea'] > 0.0]
    
    # 5. Sum duplicate products
    res = group_duplicate_ticket_items(raw_products)
    res = [item for item in res if item['quantitat'] > 0]
    try:
        with open("C:/Users/Usuari/.gemini/antigravity/brain/98896f4c-68da-443a-b920-acd856bccd79/scratch/debug_ocr.log", "a", encoding="utf-8") as f_log:
            f_log.write(f"\nCollected products zone lines: {len(product_lines_text)}\n")
            f_log.write(f"Parsed items count: {len(res)}\n")
            for p_item in res:
                f_log.write(f"  - {p_item['article']} | preu: {p_item['preuUnit']} | tot: {p_item['totLinea']}\n")
    except Exception:
        pass
    return res
 

def parse_novavenda_ticket(text_content):
    import re
    df_mapping = load_product_mappings()
    lines = text_content.split('\n')
    
    try:
        st.session_state["ticket_discount"] = 0.0
    except Exception:
        pass
        
    raw_products = []
    curr_item = None
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean: continue
        line_upper = line_clean.upper()
        
        # Stop processing at TOTAL or VAT section
        if 'TOTAL ' in line_upper or line_upper == 'TOTAL' or 'BASE TYPE' in line_upper or 'QUOTA' in line_upper:
            if curr_item:
                raw_products.append(curr_item)
                curr_item = None
            break
            
        # Ignore NIF, header lines
        if any(kw in line_upper for kw in ['NOVAVENDA', 'COMERBAL', 'NIF', 'C/.', 'FACTURA']):
            continue
            
        # Check if line is barcode + quantity (e.g. "5449000275165 1 x 0,92 €")
        match_barcode = re.search(r'^(\d{7,14})\s+(\d+)\s*[xX]\s*(\d+[\.,]\d{2})', line_clean)
        if match_barcode:
            if curr_item:
                curr_item['quantitat'] = int(match_barcode.group(2))
                curr_item['preuUnit'] = float(match_barcode.group(3).replace(',', '.'))
            continue
            
        # Check if line is an offer (starts with OFERTA)
        if line_upper.startswith('OFERTA') or 'PREU NORMAL' in line_upper:
            continue
            
        # Check if line ends with a price
        match_price = re.search(r'^(.*?)\s+(\d+[\.,]\d{2})(?:\s*[€E])?$', line_clean)
        if match_price:
            nom_brut = match_price.group(1).strip()
            # If name doesn't contain at least 3 letters, or starts with a long number (barcode), it's garbage
            if len([c for c in nom_brut if c.isalpha()]) < 3 or re.match(r'^[\d\s,.]+$', nom_brut) or re.match(r'^\d{5,}', nom_brut):
                continue
                
            tot_val = float(match_price.group(2).replace(',', '.'))
            
            if curr_item:
                # Resolve unit price if quantity wasn't found
                if curr_item['preuUnit'] == curr_item['totLinea'] and curr_item['quantitat'] > 1:
                    curr_item['preuUnit'] = round(curr_item['totLinea'] / curr_item['quantitat'], 2)
                raw_products.append(curr_item)
                
            curr_item = {
                'familia': 'Pendent',
                'article': 'pendent',
                'pes': 0,
                'quantitat': 1,
                'preuUnit': tot_val,
                'prom': 0.0,
                'totLinea': tot_val,
                'rebost': None,
                'nom_brut': nom_brut,
                'nom_super': nom_brut
            }
            
    if curr_item:
        if curr_item['preuUnit'] == curr_item['totLinea'] and curr_item['quantitat'] > 1:
            curr_item['preuUnit'] = round(curr_item['totLinea'] / curr_item['quantitat'], 2)
        raw_products.append(curr_item)
        
    # Match against DB
    for item in raw_products:
        db_match = find_product_in_db(item['nom_brut'], "Novavenda", df_mapping)
        if db_match:
            item['familia'] = db_match['familia']
            item['article'] = db_match['nomEstandard']
            item['nom_super'] = db_match.get('nom_super', item['nom_brut'])
            
    # Remove ghost items with 0 total price
    raw_products = [item for item in raw_products if item['totLinea'] > 0.0]
            
    # Group duplicates
    res = group_duplicate_ticket_items(raw_products)
    return res

def parse_text_ticket(text_content):
    import re
    from datetime import datetime
    
    # 1. Extract Date if possible
    found_date = None
    text_content_date = text_content.replace('2926', '2026').replace('41/07', '11/07')
    for match in re.finditer(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b', text_content_date):
        try:
            d_val, m_val, y_val = map(int, match.groups())
            if 1980 <= y_val <= 2090 and 1 <= m_val <= 12 and 1 <= d_val <= 31:
                found_date = datetime(y_val, m_val, d_val).date()
                break
        except ValueError:
            continue
    
    if not found_date:
        for match in re.finditer(r'\b(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\b', text_content):
            try:
                y_val = int(match.group(1))
                m_val = int(match.group(2))
                d_val = int(match.group(3))
                found_date = datetime(y_val, m_val, d_val).date()
                break
            except ValueError:
                continue
                
    if found_date:
        st.session_state["ticket_date"] = found_date
        st.session_state["ticket_date_widget"] = found_date
        
    # 2. Extract Supermercat
    if not st.session_state.get("ticket_super_val"):
        if re.search(r'\bcomerbal\b', text_content.lower()):
            st.session_state["ticket_super_val"] = "Novavenda"
            st.session_state["ticket_super_widget"] = "Novavenda"
        else:
            for sp in get_config_supers():
                # Use regex for whole word match to prevent "Normal" matching "Preu normal" or "Ous" matching "baixos"
                if re.search(r'\b' + re.escape(sp.lower()) + r'\b', text_content.lower()):
                    st.session_state["ticket_super_val"] = sp
                    st.session_state["ticket_super_widget"] = sp
                    break
            
    ticket_super = st.session_state.get("ticket_super_val", "Dia").lower()
    
    if "novavenda" in ticket_super:
        return parse_novavenda_ticket(text_content)
    
    # Fallback for all other supermarkets (Dia, Mercadona, BonArea, Clarel)
    return parse_default_ticket(text_content)

def simulate_ocr_image(super_name):
    mock_products = {
        "AreaGuissona": [
            ("carn", "Costella porc", 0, 1, 4.50, 0.0, 4.50, None),
            ("carn", "Aletes pollastre", 0, 1, 3.20, 0.0, 3.20, None),
            ("verdura", "Tomàquet Cherry", 0, 1, 1.80, 0.0, 1.80, None),
            ("extres", "varis", 0, 6, 0.23, 0.0, 1.38, None),
        ],
        "Mercadona": [
            ("lactics", "Llet 1,5L", 0, 6, 0.95, 0.0, 5.70, None),
            ("fruita", "Plàtan", 0, 1, 2.15, 0.0, 2.15, None),
            ("neteja", "Detergent", 0, 1, 4.95, 0.0, 4.95, None),
            ("esmorzar", "Galetes", 0, 2, 1.20, 0.0, 2.40, None),
        ],
        "Dia": [
            ("llaunes", "Tonyina", 0, 3, 0.70, 0.0, 2.10, None),
            ("bàsics", "Arròs", 0, 1, 1.15, 0.0, 1.15, None),
            ("begudes", "CocaCola Zero 1.5L", 0, 2, 1.70, 0.0, 3.40, None),
        ],
        "LIDL": [
            ("lactics", "Iogurt grec", 0, 1, 1.95, 0.0, 1.95, None),
            ("pa", "Pa de pagès", 0, 1, 1.45, 0.0, 1.45, None),
            ("xocolata", "Xocolata Negra", 0, 2, 1.30, 0.0, 2.60, None),
        ],
    }
    matched_key = None
    for k in mock_products:
        if k.lower() in super_name.lower():
            matched_key = k
            break
    products_to_use = mock_products[matched_key] if matched_key else [
        ("bàsics", "Ous super", 0, 1, 2.25, 0.0, 2.25, None),
        ("fruita", "Taronja", 0, 1, 3.10, 0.0, 3.10, None),
        ("extres", "varis", 0, 1, 1.50, 0.0, 1.50, None),
    ]
    items = []
    for fam, art, pes, qty, preu, prom, tot, reb in products_to_use:
        items.append({
            'familia': fam,
            'article': art,
            'pes': pes,
            'quantitat': qty,
            'preuUnit': preu,
            'prom': prom,
            'totLinea': tot,
            'rebost': reb
        })
    return items

def cb_edit_ticket_item(idx):
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    item = st.session_state["ticket_items"][idx]
    st.session_state["manual_fam_selectbox"] = item['familia'] if item['familia'] != 'Pendent' else ""
    st.session_state["manual_art_selectbox"] = item['article'] if item['article'] != 'pendent' else ""
    st.session_state["manual_pes_num"] = str(item['pes'])
    st.session_state["manual_qty_num"] = float(item['quantitat'])
    st.session_state["manual_preu_num"] = float(item['preuUnit'])
    st.session_state["manual_prom_num"] = float(item['prom'])
    st.session_state["manual_reb_chk"] = (item['rebost'] == 'rebost')
    st.session_state["editing_ticket_item_idx"] = idx

def cb_del_ticket_item(idx):
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    st.session_state["ticket_items"].pop(idx)
    st.session_state["editing_ticket_item_idx"] = None

def learn_new_mapping(nom_brut, familia, article, supermercat):
    try:
        supabase = get_supabase_client(st.session_state.get("role", "guest"))
        if not supabase: return
        # Trobar id del producte estandard
        res = supabase.table('tb_productes').select('idProducte').eq('nom_estandard', article).execute()
        if res.data:
            id_prod = res.data[0]['idProducte']
        else:
            # Crear el producte estandard si no existeix
            new_prod = {'nom_estandard': article, 'familia': familia}
            ins = supabase.table('tb_productes').insert(new_prod).execute()
            if ins.data:
                id_prod = ins.data[0]['idProducte']
            else:
                return
                
        # Inserir a tb_noms_producte vinculat al supermercat
        clean_name = normalitzar_text(nom_brut)
        exist = supabase.table('tb_noms_producte').select('idNom').eq('nom_super', nom_brut).eq('supermercat', supermercat).execute()
        if not exist.data:
            new_nom = {'supermercat': supermercat, 'nom_super': nom_brut, 'idProducte': id_prod}
            supabase.table('tb_noms_producte').insert(new_nom).execute()
            print(f"Aprés nou producte: {nom_brut} -> {article}")
    except Exception as e:
        print(f"Error aprenent producte nou: {e}")

def cb_add_ticket_line():
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    fam = st.session_state.get("manual_fam_selectbox", "")
    art = st.session_state.get("manual_art_selectbox", "")
    pes_raw = st.session_state.get("manual_pes_num", "0")
    qty_raw = st.session_state.get("manual_qty_num", 1.0)
    qty = float(qty_raw) if qty_raw is not None else 1.0
    preu_raw = st.session_state.get("manual_preu_num", 0.0)
    preu = float(preu_raw) if preu_raw is not None else 0.0
    prom_raw = st.session_state.get("manual_prom_num", 0.0)
    prom = float(prom_raw) if prom_raw is not None else 0.0
    reb = st.session_state.get("manual_reb_chk", False)
    
    if not fam or not art:
        st.session_state["manual_input_error"] = "Si us plau, selecciona una Família i un Article!"
        return
        
    if "manual_input_error" in st.session_state:
        del st.session_state["manual_input_error"]
        
    pes = str(pes_raw).strip()

    tot = (qty * preu) - prom
    new_item = {
        'familia': fam,
        'article': art,
        'pes': pes,
        'quantitat': int(qty),
        'preuUnit': preu,
        'prom': prom,
        'totLinea': tot,
        'rebost': 'rebost' if reb else None,
        'nom_brut': '',
        'nom_super': ''
    }
    
    editing_idx = st.session_state.get("editing_ticket_item_idx", None)
    if editing_idx is not None and 0 <= editing_idx < len(st.session_state["ticket_items"]):
        old_item = st.session_state["ticket_items"][editing_idx]
        new_item['nom_brut'] = old_item.get('nom_brut', '')
        new_item['nom_super'] = old_item.get('nom_super', '')
        
        # Si era un article no reconegut i ara l'usuari l'ha categoritzat, l'aprenem
        if old_item.get('article') == 'pendent' and art != 'pendent' and art != '':
            supermercat = st.session_state.get("ticket_super_val", "Desconegut")
            nom_brut = st.session_state.get("manual_nom_brut_input", new_item['nom_brut'])
            if nom_brut:
                if nom_brut != old_item.get('nom_brut', ''):
                    try:
                        supabase = get_supabase_client(st.session_state.get("role", "guest"))
                        if supabase:
                            supabase.table('tb_noms_producte').delete().eq('nom_super', old_item.get('nom_brut')).eq('supermercat', supermercat).execute()
                    except Exception:
                        pass
                learn_new_mapping(nom_brut, fam, art, supermercat)
                
        st.session_state["ticket_items"][editing_idx] = new_item
        st.session_state["editing_ticket_item_idx"] = None
    else:
        st.session_state["ticket_items"].append(new_item)
    
    # Reset widget states
    st.session_state["manual_pes_num"] = "0"
    st.session_state["manual_qty_num"] = None
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["manual_preu_num"] = None
    st.session_state["manual_prom_num"] = 0.0
    st.session_state["manual_reb_chk"] = False
    st.session_state["manual_fam_selectbox"] = ""
    st.session_state["manual_art_selectbox"] = ""

def cb_recalculate_manual_pct():
    pct = st.session_state.get("manual_pct_num", 0.0)
    preu_final = st.session_state.get("manual_preu_num", 0.0)
    existing_prom = st.session_state.get("manual_prom_num", 0.0)
    if pct > 0.0 and pct < 100.0 and preu_final > 0.0:
        qty = st.session_state.get("manual_qty_num", 1.0)
        if qty is None or qty <= 0: qty = 1.0
        prom_from_pct = round(preu_final * (pct / 100.0) * qty, 2)
        st.session_state["manual_prom_num"] = round(existing_prom + prom_from_pct, 2)
        st.session_state["manual_pct_num"] = 0.0

def cb_set_date_today():
    st.session_state["ticket_date"] = datetime.today().date()
    st.session_state["ticket_date_widget"] = datetime.today().date()

def cb_clear_ticket():
    st.session_state["ticket_items"] = []
    st.session_state["ticket_discount"] = 0.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["editing_ticket_item_idx"] = None
    st.session_state["ticket_date"] = datetime.today().date()
    st.session_state["ticket_date_widget"] = datetime.today().date()
    if "last_ocr_text" in st.session_state:
        del st.session_state["last_ocr_text"]
    st.session_state["ticket_super_val"] = ""
    if "ticket_super_widget" in st.session_state:
        st.session_state["ticket_super_widget"] = ""
    st.session_state["ticket_pay_method_sel"] = ""
    st.session_state["processed_file_id"] = None
    if "scanned_file" in st.session_state:
        del st.session_state["scanned_file"]
    # Reset manual inputs
    st.session_state["manual_pes_num"] = "0"
    st.session_state["manual_qty_num"] = None
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["manual_preu_num"] = None
    st.session_state["manual_prom_num"] = 0.0
    st.session_state["manual_reb_chk"] = False
    st.session_state["manual_fam_selectbox"] = ""
    st.session_state["manual_art_selectbox"] = ""
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
    current_idx = int(st.session_state.get("uploader_key", "ticket_file_uploader_0").split("_")[-1])
    st.session_state["uploader_key"] = f"ticket_file_uploader_{current_idx + 1}"

def cb_finalize_ticket():
    global df_desp, df_super
    df_desp = st.session_state["df_desp"]
    df_super = st.session_state["df_super"]
    
    items = st.session_state.get("ticket_items", [])
    if not items:
        st.session_state["finalize_error"] = "No es pot desar un tiquet buit!"
        return
        
    ticket_super = st.session_state.get("ticket_super_val", "")
    if not ticket_super:
        st.session_state["finalize_error"] = "Si us plau, selecciona un Supermercat abans de desar el tiquet!"
        return
        
    ticket_date = st.session_state.get("ticket_date", None)
    if not ticket_date:
        st.session_state["finalize_error"] = "Si us plau, especifica la Data del tiquet!"
        return
        
    # Salvem els articles desconeguts si n'hi ha (ara que tenim supermercat confirmat)
    save_unknown_products(items, ticket_super)
        
    if "finalize_error" in st.session_state:
        del st.session_state["finalize_error"]
        
    pending_ticket_id = st.session_state.get('pending_ticket_id')
    if pending_ticket_id:
        orig_amt = float(st.session_state.get('pending_import_carrec', 0.0))
        sum_amt = sum(item['totLinea'] for item in items)
        if abs(sum_amt - orig_amt) > 0.001:
            st.session_state["finalize_error"] = f"Desquadrament! El banc diu {orig_amt:.2f} € i els productes sumen {sum_amt:.2f} €. Pots forçar la correcció del banc amb el botó que ha aparegut a dalt."
            st.session_state["pending_ticket_mismatch"] = True
            st.session_state["pending_ticket_sum"] = sum_amt
            return
        
    discount = st.session_state.get("ticket_discount", 0.0)
    send_expense = st.session_state.get("ticket_send_expense", True)
        
    if isinstance(ticket_date, datetime):
        ticket_date = ticket_date.date()
        
    mes_val = month_translations[CATALAN_MONTHS[ticket_date.month - 1]]
    any_val = ticket_date.year
        
    bank_val = st.session_state.get("ticket_bank_sel", "")
    pay_method_val = st.session_state.get("ticket_pay_method_sel", "")
    
    if bank_val is None:
        bank_val = ""
    if pay_method_val is None:
        pay_method_val = ""
        
    bank_val_str = str(bank_val).strip()
    pay_method_val_str = str(pay_method_val).strip()
    
    if send_expense:
        if not bank_val_str or bank_val_str in ["None", "nan", "NaN", ""]:
            st.session_state["finalize_error"] = "Si us plau, selecciona un Banc per a la despesa!"
            return
        if not pay_method_val_str or pay_method_val_str in ["None", "nan", "NaN", ""]:
            st.session_state["finalize_error"] = "Si us plau, selecciona una Forma de Pagament per a la despesa!"
            return
    
    # Separate totals for menjar, neteja, and rebost
    raw_rebost = sum(item['totLinea'] for item in items if item['rebost'] == 'rebost')
    raw_neteja = sum(item['totLinea'] for item in items if item['familia'] == 'neteja' and item['rebost'] != 'rebost')
    raw_menjar = sum(item['totLinea'] for item in items if item['familia'] != 'neteja' and item['rebost'] != 'rebost')
    
    # Distribute discount: apply to menjar first, then rebost, then neteja
    rem_discount = discount
    
    import_menjar = max(0.0, raw_menjar - rem_discount)
    rem_discount = max(0.0, rem_discount - raw_menjar)
    
    import_rebost = max(0.0, raw_rebost - rem_discount)
    rem_discount = max(0.0, rem_discount - raw_rebost)
    
    import_neteja = max(0.0, raw_neteja - rem_discount)
    rem_discount = max(0.0, rem_discount - raw_neteja)
    
    id_despesa_menjar = 0
    id_despesa_neteja = 0
    id_despesa_rebost = 0
    if send_expense:
        new_entries = []
        
        # 1. Food Expense (menjar)
        if import_menjar > 0:
            new_entries.append({
                'Banc': bank_val,
                'FormaPago': pay_method_val,
                'Data': ticket_date.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'import ingrés': 0.0,
                'Import càrrec': import_menjar,
                'grup': 'Càrrec',
                'Idcategoria': 'menjar',
                'Idconcepte': ticket_super,
                'Comentari': None
            })
            
        # 2. Cleaning Expense (neteja)
        if import_neteja > 0:
            new_entries.append({
                'Banc': bank_val,
                'FormaPago': pay_method_val,
                'Data': ticket_date.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'import ingrés': 0.0,
                'Import càrrec': import_neteja,
                'grup': 'Càrrec',
                'Idcategoria': 'neteja',
                'Idconcepte': ticket_super,
                'Comentari': None
            })
            
        # 3. Pantry Expense (rebost)
        if import_rebost > 0:
            new_entries.append({
                'Banc': bank_val,
                'FormaPago': pay_method_val,
                'Data': ticket_date.strftime('%d/%m/%Y'),
                'mes': mes_val,
                'any': any_val,
                'import ingrés': 0.0,
                'Import càrrec': import_rebost,
                'grup': 'Càrrec',
                'Idcategoria': 'rebost',
                'Idconcepte': ticket_super,
                'Comentari': None
            })
            
        # Assign IDs to new_entries
        next_id = int(df_desp['ID_mov'].max() + 1) if not df_desp.empty else 1
        for i, entry in enumerate(new_entries):
            if i == 0 and pending_ticket_id:
                entry['ID_mov'] = pending_ticket_id
                if entry['Idcategoria'] == 'menjar':
                    id_despesa_menjar = pending_ticket_id
                elif entry['Idcategoria'] == 'neteja':
                    id_despesa_neteja = pending_ticket_id
                elif entry['Idcategoria'] == 'rebost':
                    id_despesa_rebost = pending_ticket_id
            else:
                entry['ID_mov'] = next_id
                if entry['Idcategoria'] == 'menjar':
                    id_despesa_menjar = next_id
                elif entry['Idcategoria'] == 'neteja':
                    id_despesa_neteja = next_id
                elif entry['Idcategoria'] == 'rebost':
                    id_despesa_rebost = next_id
                next_id += 1
            
        if new_entries:
            success = append_to_db(pd.DataFrame(new_entries), 'despeses', 'df_desp')
            if success and pending_ticket_id:
                try:
                    supabase = get_supabase_client(st.session_state.get("role", "guest"))
                    supabase.table('despeses').delete().eq('ID_mov', pending_ticket_id).execute()
                    df_desp.drop(df_desp[df_desp['ID_mov'] == pending_ticket_id].index, inplace=True)
                    st.session_state['df_desp'] = df_desp
                except Exception as e:
                    print(f"Error deleting pending ticket {pending_ticket_id}: {e}")
    
    new_rows = []
    base_id = int(df_super['IdCompra'].max() + 1) if not df_super.empty else 1
    for idx, item in enumerate(items):
        line_discount = discount if idx == 0 else 0.0
        # Determine linked expense ID based on category/rebost
        if item['rebost'] == 'rebost':
            linked_id_despesa = id_despesa_rebost
        elif item['familia'] == 'neteja':
            linked_id_despesa = id_despesa_neteja
        else:
            linked_id_despesa = id_despesa_menjar
            
        new_row = {
            'IdCompra': base_id + idx,
            'data': ticket_date.strftime('%d/%m/%Y'),
            'mes': mes_val,
            'any': any_val,
            'super': ticket_super,
            'familia': item['familia'],
            'article': item['article'],
            'pes': str(item['pes']),
            'quantitat': int(item['quantitat']),
            'preuUnit': item['preuUnit'],
            'prom': item['prom'],
            'totLinea': item['totLinea'],
            'IdDespesa': linked_id_despesa,
            'descompte': line_discount,
            'rebost': item['rebost']
        }
        new_rows.append(new_row)

    # Update stock for recognized products and track them
    updated_stocks = []
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    if supabase:
        for item in items:
            article = item.get('article', '').strip()
            if not article or article.lower() in ['pendent', 'varis']:
                continue
            try:
                res = supabase.table('tb_productes').select('idProducte, stock_actual, select_stock').eq('nom_estandard', article).execute()
                if res.data:
                    # Check if the product has select_stock == True
                    if res.data[0].get('select_stock', False) == True:
                        prod_id = res.data[0]['idProducte']
                        current_stock = res.data[0].get('stock_actual', 0)
                        if current_stock is None:
                            current_stock = 0
                        
                        qty_to_add = float(item.get('qty', 1.0))
                        new_stock = current_stock + qty_to_add
                        
                        supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', prod_id).execute()
                        updated_stocks.append(article)
            except Exception as e:
                print(f"Error updating stock for {article}: {e}")

    extra_details = {'partials': {}}
    if import_menjar > 0: extra_details['partials']['menjar'] = round(import_menjar, 2)
    if import_neteja > 0: extra_details['partials']['neteja'] = round(import_neteja, 2)
    if import_rebost > 0: extra_details['partials']['rebost'] = round(import_rebost, 2)
    
    if updated_stocks:
        extra_details['stock_actualitzat'] = updated_stocks

    append_to_db(pd.DataFrame(new_rows), 'compresSuper', 'df_super', extra_details)
    
    st.session_state["finalize_success"] = "Tiquet de súper i despesa associada desats correctament!"
    # Clear all fields and files on successful finalize
    st.session_state["ticket_items"] = []
    st.session_state["ticket_discount"] = 0.0
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["editing_ticket_item_idx"] = None
    st.session_state["ticket_date"] = datetime.today().date()
    st.session_state["ticket_super_val"] = ""
    st.session_state["ticket_bank_sel"] = ""
    st.session_state["ticket_pay_method_sel"] = ""
    st.session_state["processed_file_id"] = None
    if "scanned_file" in st.session_state:
        del st.session_state["scanned_file"]
    # Reset manual inputs
    st.session_state["manual_pes_num"] = "0"
    st.session_state["manual_qty_num"] = None
    st.session_state["manual_pct_num"] = 0.0
    st.session_state["manual_preu_num"] = None
    st.session_state["manual_prom_num"] = 0.0
    st.session_state["manual_reb_chk"] = False
    st.session_state["manual_fam_selectbox"] = ""
    st.session_state["manual_art_selectbox"] = ""
    
    # Clear pending ticket state if any
    for key in ['pending_ticket_id', 'pending_super', 'pending_data', 'pending_banc', 'pending_forma_pago', 'pending_import_carrec', 'pending_ticket_mismatch', 'pending_ticket_sum', 'last_ocr_text']:
        if key in st.session_state:
            del st.session_state[key]
            
    current_idx = int(st.session_state.get("uploader_key", "ticket_file_uploader_0").split("_")[-1])
    st.session_state["uploader_key"] = f"ticket_file_uploader_{current_idx + 1}"
    st.session_state["viewing_compres_super"] = True

def render_compres_super_interface():
    global df_super, df_desp
    
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
                doc.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const target = e.target;
                if (target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.getAttribute('role') === 'combobox') {
                    const inputs = Array.from(doc.querySelectorAll('input:not([type="hidden"]):not([disabled]), select:not([disabled]), [role="combobox"]:not([disabled])'));
                    const index = inputs.indexOf(target);
                    if (index > -1 && index < inputs.length - 1) {
                        e.preventDefault();
                        e.stopPropagation();
                        inputs[index + 1].focus();
                    }
                }
            }
        }, true);
        
        doc.addEventListener('focusin', function(e) {
            const target = e.target;
            if (target.tagName === 'INPUT') {
                const val = target.value.trim();
                if (val === '0' || val === '0,00' || val === '0.00' || val === '0.0' || val === '0,0') {
                    setTimeout(() => {
                        target.select();
                    }, 50);
                }
            }
        }, true);
        </script>
        """,
        height=0,
        width=0
    )
    
    col_t1, col_t2 = st.columns([8.5, 1.5], vertical_alignment="center")
    with col_t1:
        st.markdown("<h2 style='margin:0; color:#f39c12;'>🛒 Compres al Súper</h2>", unsafe_allow_html=True)
    with col_t2:
        if st.button("🔙 Tornar a l'inici", use_container_width=True):
            st.session_state.current_module = None
            st.rerun()
    
    if "ticket_msg_success" in st.session_state:
        st.toast(st.session_state["ticket_msg_success"], icon="✅")
        del st.session_state["ticket_msg_success"]
    if "ticket_msg_error" in st.session_state:
        st.error(st.session_state["ticket_msg_error"])
        del st.session_state["ticket_msg_error"]
    if "finalize_error" in st.session_state:
        st.error(st.session_state["finalize_error"])

    if "ticket_items" not in st.session_state:
        st.session_state["ticket_items"] = []
        
    if st.session_state.get("pending_ticket_mismatch"):
        orig_amt = float(st.session_state.get('pending_import_carrec', 0.0))
        sum_amt = float(st.session_state.get('pending_ticket_sum', 0.0))
        st.warning(f"L'import inicial registrat al banc era de **{orig_amt:.2f} €**, però la suma dels productes és de **{sum_amt:.2f} €**.")
        if st.button(f"Forçar correcció del banc a {sum_amt:.2f} €", type="primary"):
            try:
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                supabase.table("despeses").update({"Import càrrec": sum_amt}).eq("ID_mov", st.session_state.get('pending_ticket_id')).execute()
                if "df_desp" in st.session_state:
                    df_local = st.session_state["df_desp"]
                    idx_orig = df_local.index[df_local['ID_mov'] == st.session_state.get('pending_ticket_id')].tolist()[0]
                    df_local.at[idx_orig, 'Import càrrec'] = round(sum_amt, 2)
                st.session_state['pending_import_carrec'] = sum_amt
                del st.session_state["pending_ticket_mismatch"]
                st.success("Banc actualitzat correctament! Ara pots polsar 'Guardar Ticket de Súper' de nou.")
                st.rerun()
            except Exception as e:
                st.error(f"Error actualitzant banc: {e}")
    if "ticket_discount" not in st.session_state:
        st.session_state["ticket_discount"] = 0.0
    
    # Initialize pending ticket values
    if st.session_state.get('pending_ticket_id'):
        if not st.session_state.get("ticket_super_val") and st.session_state.get('pending_super'):
            st.session_state["ticket_super_val"] = st.session_state['pending_super']
        if not st.session_state.get("ticket_date") and st.session_state.get('pending_data'):
            try:
                st.session_state["ticket_date"] = datetime.strptime(st.session_state['pending_data'], '%d/%m/%Y').date()
            except:
                st.session_state["ticket_date"] = datetime.today().date()
        if not st.session_state.get("ticket_bank_sel") and st.session_state.get('pending_banc'):
            st.session_state["ticket_bank_sel"] = st.session_state['pending_banc']
        if not st.session_state.get("ticket_pay_method_sel") and st.session_state.get('pending_forma_pago'):
            st.session_state["ticket_pay_method_sel"] = st.session_state['pending_forma_pago']
            
    if "ticket_date" not in st.session_state or st.session_state["ticket_date"] is None:
        st.session_state["ticket_date"] = None
    if "ticket_super_val" not in st.session_state:
        st.session_state["ticket_super_val"] = ""
    if "ticket_send_expense" not in st.session_state:
        st.session_state["ticket_send_expense"] = True
    if "ticket_bank_sel" not in st.session_state:
        st.session_state["ticket_bank_sel"] = ""
    if "ticket_pay_method_sel" not in st.session_state:
        st.session_state["ticket_pay_method_sel"] = ""
    if "added_supers" not in st.session_state:
        st.session_state["added_supers"] = []
        
    pending_ticket_id = st.session_state.get('pending_ticket_id')
    if pending_ticket_id:
        st.info(f"🛒 **Desglossant ticket pendent:** de {st.session_state.get('pending_super', '')} el {st.session_state.get('pending_data', '')}")
        
    # Row 1: Send to expense checkbox, Bank, Payment Method, File Uploader
    col_hdr1, col_hdr2, col_hdr3, col_hdr4 = st.columns([2.5, 2.5, 2.5, 4.5], vertical_alignment="bottom")
    with col_hdr1:
        send_expense = st.checkbox("Enviar a despeses", key="ticket_send_expense")
    
    bank_val = ""
    pay_method_val = ""
    if send_expense:
        with col_hdr2:
            bank_val = st.selectbox("Banc:", [""] + get_config_banks(), key="ticket_bank_sel")
        with col_hdr3:
            pay_methods = [""] + get_config_payment_methods()
            if bank_val == "Efectiu":
                pay_methods = ["Efectiu"]
                st.session_state["ticket_pay_method_sel"] = "Efectiu"
            else:
                pay_methods = [m for m in pay_methods if m != "Efectiu"]
                if st.session_state.get("ticket_pay_method_sel") == "Efectiu":
                    st.session_state["ticket_pay_method_sel"] = ""
            pay_method_val = st.selectbox("Forma de Pagament:", pay_methods, key="ticket_pay_method_sel")
    else:
        with col_hdr2:
            st.write("")
        with col_hdr3:
            st.write("")
            
    if send_expense and len(st.session_state.get("ticket_items", [])) > 0:
        b_val_str = str(bank_val).strip()
        p_val_str = str(pay_method_val).strip()
        if not b_val_str or b_val_str in ["None", "nan", "NaN", ""]:
            st.error("Si us plau, selecciona un Banc per a la despesa!")
        if not p_val_str or p_val_str in ["None", "nan", "NaN", ""]:
            st.error("Si us plau, selecciona una Forma de Pagament per a la despesa!")
            
    with col_hdr4:
        uploader_key = st.session_state.get("uploader_key", "ticket_file_uploader_0")
        uploaded_file = st.file_uploader("📷 Llegir ticket", type=["png", "jpg", "jpeg"], label_visibility="collapsed", key=uploader_key)
        
        candidates = [f for f in [uploaded_file, st.session_state.get("scanned_file")] if f is not None]
        chosen_file = None
        for f in candidates:
            fid = f"{f.name}_{f.size}"
            if fid != st.session_state.get("processed_file_id"):
                chosen_file = f
                break
        if chosen_file is None and candidates:
            chosen_file = candidates[0]
            
        uploaded_file = chosen_file
        
        if uploaded_file is not None:
            col_f1, col_f2 = st.columns([3, 1], vertical_alignment="center")
            with col_f1:
                st.caption(f"📁 **Fitxer:** `{uploaded_file.name}`")
            with col_f2:
                file_id = f"{uploaded_file.name}_{uploaded_file.size}"
                if st.session_state.get("ocr_failed", False) or st.session_state.get("processed_file_id") == file_id:
                    if st.button("🔄 Reintentar", key="btn_retry_ocr_ui", help="Torna a passar el tiquet per la IA"):
                        if "processed_file_id" in st.session_state:
                            del st.session_state["processed_file_id"]
                        st.rerun()
        
        if uploaded_file is not None:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get("processed_file_id") != file_id:
                st.session_state["processed_file_id"] = file_id
                if uploaded_file.name.endswith(".txt"):
                    try:
                        text_content = uploaded_file.read().decode("utf-8")
                        st.session_state["last_ocr_text"] = text_content
                        parsed = parse_text_ticket(text_content)
                        
                        if not st.session_state.get("ticket_super_val"):
                            st.session_state["ticket_msg_error"] = "⚠️ No s'ha detectat automàticament el supermercat. Si us plau, selecciona'l al desplegable inferior perquè es puguin processar els articles."
                            st.session_state["ticket_items"] = []
                            st.rerun()
                            
                        st.session_state["ticket_items"] = parsed
                        save_unknown_products(parsed, st.session_state.get("ticket_super_val", ""))
                        st.session_state["ticket_msg_success"] = f"Tiquet de text llegit correctament! S'han trobat {len(parsed)} línies."
                        st.rerun()
                    except Exception as e:
                        st.session_state["ticket_msg_error"] = f"Error al llegir el tiquet de text: {str(e)}"
                        st.rerun()
                else:
                    try:
                        # Run OCR using Google Gemini AI
                        with st.spinner("Llegint tiquet amb IA (Gemini Vision)..."):
                            import requests
                            import base64
                            import json
                            from datetime import datetime
                            
                            api_key = st.secrets.get("GEMINI_API_KEY", "")
                            
                            mime_type = "image/jpeg"
                            if uploaded_file.name.lower().endswith(".png"):
                                mime_type = "image/png"
                                
                            uploaded_file.seek(0)
                            encoded_image = base64.b64encode(uploaded_file.read()).decode("utf-8")
                            
                            prompt = """
Ets un expert en extracció de dades de tiquets de compra.
Llegeix aquest tiquet de supermercat i retorna les dades en un format JSON net i estricte.
L'estructura del JSON ha de ser EXACTAMENT aquesta:
{
    "supermercat": "Nom del supermercat (ex: bonArea, Mercadona, Dia, Novavenda, Caprabo, etc.)",
    "data": "DD/MM/YYYY (si la trobes)",
    "articles": [
        {
            "nom_brut": "Nom exacte del producte que surt al tiquet, respectant lletres",
            "quantitat": 1,
            "preu_unitari": 0.0,
            "preu_total": 0.0
        }
    ]
}
Notes importants:
1. Ignora totalment les línies que no siguin productes (IVA, Base Imposable, Canvi, Targeta, Subtotal, Ofertes, Cupons).
2. Assegura't de capturar bé el 'preu_total' de la línia.
3. Si el preu unitari no surt clar, calcula'l dividint preu_total / quantitat.
"""
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
                            payload = {
                                "contents": [
                                    {
                                        "parts": [
                                            {"text": prompt},
                                            {
                                                "inline_data": {
                                                    "mime_type": mime_type,
                                                    "data": encoded_image
                                                }
                                            }
                                        ]
                                    }
                                ],
                                "generationConfig": {
                                    "responseMimeType": "application/json"
                                }
                            }
                            
                            import time
                            max_retries = 5
                            for attempt in range(max_retries):
                                req = requests.post(url, json=payload, timeout=90)
                                if req.status_code == 503 or req.status_code == 429:
                                    if attempt < max_retries - 1:
                                        time.sleep(3 + (2 ** attempt))
                                        continue
                                if req.status_code != 200:
                                    raise Exception(f"API Error {req.status_code}: {req.text}")
                                break
                                
                            response_data = req.json()
                            try:
                                response_text = response_data['candidates'][0]['content']['parts'][0]['text']
                                response_text = response_text.replace('```json', '').replace('```', '').strip()
                                data = json.loads(response_text)
                            except Exception as e:
                                raise Exception(f"Failed to parse AI response: {str(e)}. Raw: {str(response_data)[:200]}")
                            
                            # 1. Update supermercat
                            super_trobat = data.get("supermercat", "")
                            if super_trobat:
                                valid_supers = get_config_supers()
                                super_definitiu = None
                                for sp in valid_supers:
                                    if sp.lower() in super_trobat.lower() or super_trobat.lower() in sp.lower():
                                        super_definitiu = sp
                                        break
                                
                                if not super_definitiu and 'comerbal' in super_trobat.lower():
                                    super_definitiu = 'Novavenda'
                                    
                                if super_definitiu:
                                    st.session_state["ticket_super_val"] = super_definitiu
                                    st.session_state["ticket_super_widget"] = super_definitiu
                                else:
                                    st.session_state["ticket_super_val"] = super_trobat
                                    st.session_state["ticket_super_widget"] = super_trobat

                            # 2. Update date
                            data_trobada = data.get("data", "")
                            if data_trobada:
                                try:
                                    d_val, m_val, y_val = map(int, data_trobada.split('/'))
                                    st.session_state["ticket_date"] = datetime(y_val, m_val, d_val).date()
                                except Exception:
                                    pass

                            # 3. Mapejar els articles
                            parsed = []
                            df_mapping = load_product_mappings()
                            current_super = st.session_state.get("ticket_super_val", "")
                            
                            for art in data.get("articles", []):
                                nom_brut = art.get("nom_brut", "")
                                if not nom_brut: continue
                                
                                q_val = float(art.get("quantitat", 1))
                                p_unit = float(art.get("preu_unitari", 0.0))
                                p_tot = float(art.get("preu_total", 0.0))
                                
                                if p_tot == 0.0 and p_unit > 0.0:
                                    p_tot = p_unit * q_val
                                    
                                curr_item = {
                                    'familia': 'Pendent',
                                    'article': 'pendent',
                                    'pes': 0,
                                    'quantitat': q_val,
                                    'preuUnit': p_unit,
                                    'prom': 0.0,
                                    'totLinea': p_tot,
                                    'rebost': None,
                                    'nom_brut': nom_brut,
                                    'nom_super': current_super
                                }
                                
                                db_match = find_product_in_db(nom_brut, current_super, df_mapping)
                                if db_match:
                                    curr_item['familia'] = db_match['familia']
                                    curr_item['article'] = db_match['nomEstandard']
                                    curr_item['nom_super'] = db_match.get('nom_super', nom_brut)
                                    
                                parsed.append(curr_item)

                            st.session_state["ticket_items"] = parsed
                            save_unknown_products(parsed, current_super)
                            st.session_state["ocr_failed"] = False
                            st.session_state["ticket_msg_success"] = f"Tiquet processat amb èxit per IA (Gemini)! S'han detectat {len(parsed)} articles."
                            st.rerun()
                    except Exception as e:
                        st.session_state["ocr_failed"] = True
                        st.session_state["ticket_msg_error"] = f"Error al processar l'imatge amb OCR: {str(e)}. Si us plau, introdueix els productes manualment."
                        st.rerun()
        
    # Row 2: Data, Super, Import, Nº Despesa
    col_row2_1, col_row2_2, col_row2_3, col_row2_4 = st.columns([3.5, 3.5, 2.5, 2.5], vertical_alignment="center")
    with col_row2_1:
        col_d1, col_d2 = st.columns([3, 1], vertical_alignment="bottom")
        with col_d1:
            ticket_date = st.date_input("Data:", value=st.session_state.get("ticket_date", None), format="DD/MM/YYYY", key="ticket_date_widget")
            st.session_state["ticket_date"] = ticket_date
        with col_d2:
            st.button("Avui", key="btn_avui", on_click=cb_set_date_today)
                
    with col_row2_2:
        col_s1, col_s2 = st.columns([3, 1.2], vertical_alignment="bottom")
        with col_s1:
            super_options = [""] + get_config_supers()
            for sp in st.session_state["added_supers"]:
                if sp not in super_options:
                    super_options.append(sp)
            default_super = st.session_state.get("ticket_super_val", "")
            if default_super not in super_options:
                super_options.append(default_super)
            def_idx = super_options.index(default_super)
            
            def cb_super_changed():
                new_super = st.session_state["ticket_super_widget"]
                st.session_state["ticket_super_val"] = new_super
                if "last_ocr_text" in st.session_state and st.session_state["last_ocr_text"]:
                    parsed = parse_text_ticket(st.session_state["last_ocr_text"])
                    st.session_state["ticket_items"] = parsed
                    save_unknown_products(parsed, new_super)
                    if "ticket_msg_error" in st.session_state:
                        del st.session_state["ticket_msg_error"]
                    st.session_state["ticket_msg_success"] = f"Tiquet reprocessat correctament com a {new_super}. S'han detectat {len(parsed)} articles."
            
            ticket_super = st.selectbox("Super:", super_options, index=def_idx, key="ticket_super_widget", on_change=cb_super_changed)
            st.session_state["ticket_super_val"] = ticket_super
        with col_s2:
            if st.button("Nou", key="btn_nou_super"):
                st.session_state["show_new_super_popover"] = True
                
        if st.session_state.get("show_new_super_popover", False):
            new_super_name = st.text_input("Nom del nou Súper:", key="new_super_name_input", autocomplete="new-password")
            col_ns1, col_ns2 = st.columns(2)
            with col_ns1:
                if st.button("Afegir", key="btn_add_new_super"):
                    if new_super_name.strip():
                        if new_super_name.strip() not in st.session_state["added_supers"]:
                            st.session_state["added_supers"].append(new_super_name.strip())
                        add_super_to_config(new_super_name.strip())
                        st.session_state["show_new_super_popover"] = False
                        st.rerun()
            with col_ns2:
                if st.button("Tancar", key="btn_close_new_super"):
                    st.session_state["show_new_super_popover"] = False
                    st.rerun()
 
    items = st.session_state["ticket_items"]
    discount = st.session_state["ticket_discount"]
    total_import = sum(item['totLinea'] for item in items) - discount
 
    with col_row2_3:
        st.markdown("**IMPORT TOTAL TICKET**")
        st.markdown(f"<div style='background-color:#1e293b; color:#ffffff; border:1px solid #334155; padding:8px; border-radius:4px; font-size:1.2rem; font-weight:bold; text-align:center;'>{total_import:,.2f} €</div>", unsafe_allow_html=True)
        
    with col_row2_4:
        if pending_ticket_id:
            next_id = pending_ticket_id
        else:
            next_id = int(df_desp['ID_mov'].max() + 1) if not df_desp.empty else 1
        st.markdown("**Nº DESPESA**")
        st.markdown(f"<div style='background-color:#1e293b; color:#ffffff; border:1px solid #334155; padding:8px; border-radius:4px; font-size:1.2rem; font-weight:bold; text-align:center;'>{next_id}</div>", unsafe_allow_html=True)

    # Ensure manual input states are initialized
    if "manual_fam_selectbox" not in st.session_state:
        st.session_state["manual_fam_selectbox"] = ""
    if "manual_art_selectbox" not in st.session_state:
        st.session_state["manual_art_selectbox"] = ""
    if "manual_pes_num" not in st.session_state:
        st.session_state["manual_pes_num"] = "0"
    if "manual_qty_num" not in st.session_state:
        st.session_state["manual_qty_num"] = None
    if "manual_pct_num" not in st.session_state:
        st.session_state["manual_pct_num"] = 0.0
    if "manual_preu_num" not in st.session_state:
        st.session_state["manual_preu_num"] = None
    if "manual_prom_num" not in st.session_state:
        st.session_state["manual_prom_num"] = 0.0
    if "manual_reb_chk" not in st.session_state:
        st.session_state["manual_reb_chk"] = False
    # Dynamic recalculation for manual ticket lines if pct (%) is entered
    pct = st.session_state.get("manual_pct_num", 0.0) or 0.0
    preu_final = st.session_state.get("manual_preu_num", 0.0) or 0.0
    qty = st.session_state.get("manual_qty_num", 1.0) or 1.0
    if qty <= 0.0:
        qty = 1.0
    if pct > 0.0 and pct < 100.0 and preu_final > 0.0:
        existing_prom = st.session_state.get("manual_prom_num", 0.0) or 0.0
        # preu_final = preu_orig * (1 - pct/100)
        # preu_orig = preu_final / (1 - pct/100)
        p_orig = preu_final / (1.0 - (pct / 100.0))
        prom_per_unit = p_orig - preu_final
        prom_from_pct = prom_per_unit * qty
        
        st.session_state["manual_prom_num"] = round(existing_prom + prom_from_pct, 2)
        st.session_state["manual_preu_num"] = round(p_orig, 2)
        st.session_state["manual_pct_num"] = 0.0 # reset pct
        st.rerun()

    # Manual Line Input Section
    st.write("")
    st.markdown("##### ➕ Introduir línia manualment")
    
    editing_idx = st.session_state.get("editing_ticket_item_idx", None)
    if editing_idx is not None and 0 <= editing_idx < len(st.session_state.get("ticket_items", [])):
        ed_item = st.session_state["ticket_items"][editing_idx]
        if ed_item.get('article') == 'pendent':
            st.text_input("Text original (modifica si cal abans de desar per ensenyar al sistema):", value=ed_item.get('nom_brut', ''), key="manual_nom_brut_input")
            
    col_fam, col_art, col_pes, col_qty, col_preu, col_pct, col_prom, col_tot, col_reb, col_add = st.columns(
        [2, 2.2, 1, 1, 1, 0.8, 1, 1.2, 0.6, 1.2], vertical_alignment="bottom"
    )
    
    with col_fam:
        fam_options = [""] + get_config_families()
        fam_sel = st.selectbox("FAMILIA", fam_options, key="manual_fam_selectbox")
        
    with col_art:
        @st.dialog("➕ Afegir nou article")
        def show_add_article_dialog(family):
            st.markdown(f"Introduïu el nom del nou article per a la família **{family}**:")
            new_art_name = st.text_input("Nom de l'article:", key="new_article_name_input_dialog")
            if st.button("Guardar article", key="btn_save_dialog_article", use_container_width=True):
                if new_art_name.strip():
                    new_art = new_art_name.strip()
                    global cat_config
                    if "articles_compres" not in cat_config:
                        cat_config["articles_compres"] = {}
                    if family not in cat_config["articles_compres"]:
                        cat_config["articles_compres"][family] = []
                    if new_art not in cat_config["articles_compres"][family]:
                        try:
                            supabase = get_supabase_client(st.session_state.get("role", "guest"))
                            if supabase:
                                new_prod_db = {'nom_estandard': new_art, 'familia': family}
                                supabase.table('tb_productes').insert(new_prod_db).execute()
                                get_tb_productes_cached.clear()
                                # Actualitzem manualment el json
                                cat_config["articles_compres"][family].append(new_art)
                                cat_config["articles_compres"][family].sort()
                                save_categories_conceptes(cat_config)
                        except Exception as e:
                            print(f"Error saving to tb_productes: {e}")
                            
                        st.toast(f"Article '{new_art}' afegit correctament!")
                    else:
                        st.toast(f"L'article '{new_art}' ja estava afegit prèviament.")
                        
                    st.session_state["force_article_selection"] = new_art
                    st.rerun()
                else:
                    st.error("El nom de l'article no pot estar buit.")

        if fam_sel:
            art_options = [""] + get_config_articles(fam_sel)
        else:
            art_options = [""]
        if "force_article_selection" in st.session_state:
            force_art = st.session_state.pop("force_article_selection")
            if force_art in art_options:
                st.session_state["manual_art_selectbox"] = force_art
                
        curr_art = st.session_state["manual_art_selectbox"]
        if curr_art not in art_options:
            st.session_state["manual_art_selectbox"] = ""
            
        # Draw side-by-side columns: 85% selectbox, 15% small + button
        art_input_cols = st.columns([8, 2])
        with art_input_cols[0]:
            art_sel = st.selectbox("ARTICLE", art_options, key="manual_art_selectbox")
        with art_input_cols[1]:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if fam_sel:
                st.markdown(
                    """
                    <style>
                    .small-add-btn button {
                        padding: 0px !important;
                        font-size: 12px !important;
                        height: 28px !important;
                        width: 28px !important;
                        min-height: 28px !important;
                        line-height: 28px !important;
                        border-radius: 4px !important;
                    }
                    </style>
                    <div class="small-add-btn">
                    """,
                    unsafe_allow_html=True
                )
                if st.button("➕", key="btn_trigger_add_art", help="Afegir nou article"):
                    show_add_article_dialog(fam_sel)
                st.markdown("</div>", unsafe_allow_html=True)
        
    with col_pes:
        pes_val = st.text_input("PES", key="manual_pes_num")
    with col_qty:
        qty_val = st.number_input("QUANTITAT", min_value=0.0, step=1.0, key="manual_qty_num", on_change=cb_recalculate_manual_pct, value=None, placeholder="1")
    with col_preu:
        preu_val = st.number_input("PREU UNIT.", min_value=0.0, step=0.01, key="manual_preu_num", on_change=cb_recalculate_manual_pct, value=None, placeholder="0.0")
    with col_pct:
        pct_val = st.number_input("%", min_value=0.0, max_value=100.0, step=1.0, key="manual_pct_num", on_change=cb_recalculate_manual_pct)
    with col_prom:
        prom_val = st.number_input("PROMOCIÓ", min_value=0.0, step=0.01, key="manual_prom_num")
        
    tot_linea_val = ((qty_val or 1.0) * (preu_val or 0.0)) - prom_val
    with col_tot:
        st.text_input("TOTAL LÍNIA", value=f"{tot_linea_val:,.2f} €", disabled=True)
    with col_reb:
        reb_val = st.checkbox("Reb.", key="manual_reb_chk")
    with col_add:
        st.button("Intro línia", key="btn_add_line", type="secondary", on_click=cb_add_ticket_line)

    # Render error if validation failed in callback
    if "manual_input_error" in st.session_state:
        st.error(st.session_state["manual_input_error"])

    # Table Grid
    if items:
        st.write("")
        st.markdown("##### 📝 Línies del Tiquet")
        
        with st.container(height=300):
            st.markdown("<div class='ticket-lines-container'></div>", unsafe_allow_html=True)
            st.markdown("""
            <style>
            div[data-testid="stVerticalBlock"]:has(.ticket-lines-container) {
                gap: 0rem !important;
            }
            div[data-testid="stVerticalBlock"]:has(.ticket-lines-container) > div {
                padding-top: 0 !important;
                padding-bottom: 0 !important;
            }
            div[data-testid="stVerticalBlock"]:has(.ticket-lines-container) hr {
                margin: 4px 0 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            # Render a beautiful Streamlit grid with row-level buttons
            col_headers = st.columns([0.4, 1.4, 2.0, 0.8, 0.6, 1.0, 0.8, 1.0, 0.6, 0.5, 0.5])
            with col_headers[0]: st.markdown("**#**")
            with col_headers[1]: st.markdown("**FAMÍLIA**")
            with col_headers[2]: st.markdown("**ARTICLE**")
            with col_headers[3]: st.markdown("**PES**")
            with col_headers[4]: st.markdown("**QTY**")
            with col_headers[5]: st.markdown("**PREU U.**")
            with col_headers[6]: st.markdown("**PROM.**")
            with col_headers[7]: st.markdown("**TOTAL**")
            with col_headers[8]: st.markdown("**REB.**")
            with col_headers[9]: st.markdown("")
            with col_headers[10]: st.markdown("")
            
            st.markdown("<hr style='margin: 4px 0 8px 0; border-color: #334155;'/>", unsafe_allow_html=True)
            
            def _cell(text, color="", bold=False):
                fw = "font-weight:bold;" if bold else ""
                c = f"color:{color};" if color else ""
                st.markdown(f"<div style='margin-bottom:-12px; padding-top:6px; font-size:0.9rem; {fw} {c}'>{text}</div>", unsafe_allow_html=True)

            for i, item in enumerate(items):
                cols = st.columns([0.4, 1.4, 2.0, 0.8, 0.6, 1.0, 0.8, 1.0, 0.6, 0.5, 0.5], vertical_alignment="center")
                with cols[0]:
                    _cell(f"{i+1}")
                with cols[1]:
                    if item["familia"] == 'Pendent':
                        _cell("Pendent", color="#ef4444", bold=True)
                    else:
                        _cell(item["familia"])
                with cols[2]:
                    if item["article"] == 'pendent':
                        _cell("pendent", color="#ef4444", bold=True)
                    else:
                        _cell(item["article"])
                with cols[3]:
                    p_str = str(item['pes']).strip()
                    if p_str.replace('.', '', 1).isdigit() and float(p_str) > 0:
                        _cell(f"{p_str}g")
                    else:
                        _cell(p_str if p_str else "0g")
                with cols[4]:
                    _cell(f"{item['quantitat']}")
                with cols[5]:
                    _cell(f"{item['preuUnit']:.2f} €")
                with cols[6]:
                    if item['prom'] > 0:
                        _cell(f"-{item['prom']:.2f} €", color="#ef4444")
                    else:
                        _cell("0.00 €")
                with cols[7]:
                    _cell(f"{item['totLinea']:.2f} €", bold=True)
                with cols[8]:
                    _cell("🧺" if item['rebost'] == 'rebost' else "")
                with cols[9]:
                    st.button("✏️", key=f"btn_edit_row_{i}", on_click=cb_edit_ticket_item, args=(i,), help="Modificar línia")
                with cols[10]:
                    st.button("🗑️", key=f"btn_del_row_{i}", on_click=cb_del_ticket_item, args=(i,), help="Eliminar línia")
                st.markdown("<hr style='margin: 4px 0; border-color: #1e293b;'/>", unsafe_allow_html=True)
            st.write("")
    else:
        st.info("El tiquet està buit. Afegeix línies manualment o puja un tiquet per fitxer o càmara.")



    st.write("---")
    col_desc, col_b1, col_b2, col_b3 = st.columns([3, 2, 2, 5], vertical_alignment="bottom")
    
    with col_desc:
        st.number_input("Descompte global del Tiquet (€):", min_value=0.0, step=0.01, key="ticket_discount")

    with col_b1:
        st.button("Fi Tiquet", key="btn_finalize_ticket", type="primary", on_click=cb_finalize_ticket)
                
    with col_b2:
        st.button("Netejar Tiquet", key="btn_clear_ticket", on_click=cb_clear_ticket)

# ----------------- HEADER AREA -----------------


def render():
    st.title("🛒 Mòdul de Compres")
    
    tab_scanner, tab_llista = st.tabs(["🧾 Escàner Súper", "📋 Llista de la Compra"])
    
    with tab_scanner:
        render_compres_super_interface()

    with tab_llista:
        st.write("Aquesta llista mostra els productes del teu rebost on l'stock actual està per sota de l'stock mínim.")
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_prods = fetch_all_supabase(supabase, 'tb_productes')
            
            # --- SECCIÓ AFEGIR MANUALMENT ---
            if "show_add_manual" not in st.session_state:
                st.session_state.show_add_manual = False
                
            if st.button("➕ Afegir petició puntual", type="primary" if not st.session_state.show_add_manual else "secondary"):
                st.session_state.show_add_manual = not st.session_state.show_add_manual
                st.rerun()
                
            if st.session_state.show_add_manual:
                st.markdown("<div style='padding: 1rem; border: 1px solid #d3d3d3; border-radius: 0.5rem; margin-bottom: 1rem; background-color: #f8f9fa;'>", unsafe_allow_html=True)
                with st.form("form_add_manual", clear_on_submit=True):
                    st.write("Afegeix articles que no tens al rebost o peticions especials.")
                    col1, col2, col3, col4 = st.columns([1.5, 2, 2.5, 1])
                    with col1:
                        if not df_prods.empty and 'super_habitual' in df_prods.columns:
                            supers = ["(Tria supermercat)"] + sorted([str(s) for s in df_prods['super_habitual'].dropna().unique() if str(s).strip() != ""])
                        else:
                            supers = ["(Tria supermercat)", "Mercadona", "BonArea", "Consum", "Ametller", "Esclat"]
                        if "Altres" not in supers:
                            supers.append("Altres")
                        super_sel = st.selectbox("Supermercat", supers)
                    with col2:
                        nom_lliure = st.text_input("📝 Nom lliure (nou)", placeholder="Ex: Piles AA...")
                    with col3:
                        if not df_prods.empty:
                            noms_cataleg = ["(No utilitzar)"] + sorted(df_prods['nom_estandard'].dropna().unique().tolist())
                        else:
                            noms_cataleg = ["(No utilitzar)"]
                        nom_cataleg = st.selectbox("📦 O tria del catàleg:", noms_cataleg)
                    with col4:
                        quantitat_nou = st.number_input("Quantitat", min_value=1, value=1, step=1)
                    
                    submitted_manual = st.form_submit_button("➕ Afegir a la llista")
                    if submitted_manual:
                        nom_final = nom_lliure.strip() if nom_lliure.strip() else (nom_cataleg if nom_cataleg != "(No utilitzar)" else "")
                        
                        super_to_save = "Sense Assignar" if super_sel == "(Tria supermercat)" else super_sel
                        
                        if nom_final:
                            # Insert into tb_pendents_compra
                            try:
                                supabase.table('tb_pendents_compra').insert({
                                    'nom_article': nom_final,
                                    'quantitat': quantitat_nou,
                                    'unitat': 'u.',
                                    'super_habitual': super_to_save
                                }).execute()
                                st.session_state.show_add_manual = False
                                st.success(f"S'ha afegit '{nom_final}' correctament!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error guardant l'article: {e}")
                        else:
                            st.warning("⚠️ Has d'escriure un nom lliure o triar un producte del catàleg.")
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            if not df_prods.empty:
                # Ensure select_stock exists
                if 'select_stock' not in df_prods.columns:
                    df_prods['select_stock'] = False
                
                # Filter ONLY items that are in the pantry (select_stock == True)
                df_prods_filtered = df_prods[df_prods['select_stock'] == True].copy()
                
                for col in ['stock_actual', 'stock_minim']:
                    if col not in df_prods_filtered.columns:
                        df_prods_filtered[col] = 0.0
                if 'super_habitual' not in df_prods_filtered.columns:
                    df_prods_filtered['super_habitual'] = None
                    
                df_shopping = df_prods_filtered[df_prods_filtered['stock_actual'] < df_prods_filtered['stock_minim']].copy()
                
                if not df_shopping.empty:
                    df_shopping['falta'] = df_shopping['stock_minim'] - df_shopping['stock_actual']
                    df_shopping['super_habitual'] = df_shopping['super_habitual'].fillna("Sense Assignar").replace("", "Sense Assignar")
                    df_shopping['is_manual'] = False
                else:
                    df_shopping = pd.DataFrame(columns=['idProducte', 'nom_estandard', 'super_habitual', 'falta', 'unitat', 'is_manual'])
                
                # FETCH tb_pendents_compra
                try:
                    df_manual = fetch_all_supabase(supabase, 'tb_pendents_compra')
                    if not df_manual.empty:
                        # Rename to match df_shopping structure
                        df_manual = df_manual.rename(columns={
                            'id': 'idProducte',
                            'nom_article': 'nom_estandard',
                            'quantitat': 'falta'
                        })
                        df_manual['is_manual'] = True
                        df_shopping = pd.concat([df_shopping, df_manual], ignore_index=True)
                except Exception as e:
                    pass # Taula potser no existeix o error
                    
                if not df_shopping.empty:
                    # Sort by supermarket name
                    df_shopping = df_shopping.sort_values(by=['super_habitual', 'is_manual'])
                    
                    # Group by super_habitual
                    for superm, group in df_shopping.groupby('super_habitual'):
                        # Use expander for each supermarket
                        with st.expander(f"🏪 {superm} ({len(group)} productes)", expanded=(superm == "Sense Assignar")):
                            for _, row in group.iterrows():
                                unit_str = row['unitat'] if 'unitat' in row and pd.notna(row['unitat']) and str(row['unitat']).lower() != 'none' else 'u.'
                                icon = "➕" if row.get('is_manual', False) else "📦"
                                st.checkbox(f"{icon} **{row['nom_estandard']}**: falta **{int(row['falta'])}** {unit_str}", key=f"chk_shop_{row['idProducte']}_{superm}_{row.get('is_manual', False)}")
                                
                            # Botó netejar si hi ha manuals
                            manual_ids = group[group['is_manual'] == True]['idProducte'].tolist()
                            if manual_ids:
                                st.write("")
                                col_btn, _ = st.columns([1, 2])
                                with col_btn:
                                    if st.button(f"🧹 Netejar peticions lliures", key=f"clear_man_{superm}"):
                                        try:
                                            # Esborrar un a un
                                            for mid in manual_ids:
                                                supabase.table('tb_pendents_compra').delete().eq('id', int(mid)).execute()
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error esborrant: {e}")
                                            
                            # Form for moving items if superm is Sense Assignar
                            if superm == "Sense Assignar" and len(group) > 0:
                                st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                                
                                # Llista d'articles seleccionats
                                items_to_move = []
                                for _, r_move in group.iterrows():
                                    chk_key = f"chk_shop_{r_move['idProducte']}_{superm}_{r_move.get('is_manual', False)}"
                                    if st.session_state.get(chk_key, False):
                                        items_to_move.append(r_move)
                                        
                                with st.form(f"move_items_{superm}"):
                                    num_selected = len(items_to_move)
                                    text_title = f"🚚 **Moure els {num_selected} articles seleccionats**" if num_selected > 0 else "🚚 **Moure els articles seleccionats**"
                                    st.write(text_title)
                                    
                                    col_m1, col_m2 = st.columns([3, 1])
                                    with col_m1:
                                        if not df_prods.empty and 'super_habitual' in df_prods.columns:
                                            all_supers_clean = sorted([str(s) for s in df_prods['super_habitual'].dropna().unique() if str(s).strip() not in ["", "Sense Assignar"]])
                                        else:
                                            all_supers_clean = ["Mercadona", "BonArea", "Consum", "Ametller", "Esclat", "Altres"]
                                        if "Altres" not in all_supers_clean:
                                            all_supers_clean.append("Altres")
                                        target_super = st.selectbox("Destí", all_supers_clean)
                                    with col_m2:
                                        st.write("")
                                        st.write("")
                                        move_btn = st.form_submit_button("Moure")
                                    
                                    if move_btn:
                                        if not items_to_move:
                                            st.error("No has seleccionat cap article a la llista de dalt (clica a la casella de l'esquerra).")
                                        else:
                                            try:
                                                updates = 0
                                                for r_move in items_to_move:
                                                    if r_move.get('is_manual'):
                                                        supabase.table('tb_pendents_compra').update({'super_habitual': target_super}).eq('id', int(r_move['idProducte'])).execute()
                                                    else:
                                                        supabase.table('tb_productes').update({'super_habitual': target_super}).eq('idProducte', int(r_move['idProducte'])).execute()
                                                    updates += 1
                                                
                                                st.success(f"S'han mogut {updates} articles a {target_super}!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Error movent: {e}")
                else:
                    st.success("Ho tens tot! El teu stock està per sobre del mínim a tot arreu i no tens peticions puntuals.")
            else:
                st.info("No hi ha productes a la base de dades.")
                
        except Exception as e:
            st.error(f"⚠️ Error carregant la llista de la compra: {str(e)}")

