import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from core.db import (
    get_supabase_client, fetch_all_supabase, update_db_row, log_action, insert_db_row, append_to_db,
    get_config_supers, get_config_banks, get_config_payment_methods, get_config_families, get_config_articles,
    add_super_to_config, get_tb_productes_cached, save_categories_conceptes
)
import re
import urllib.parse
from PIL import Image
import pytesseract
import json
import difflib

CATALAN_MONTHS = [
    "Gener", "Febrer", "Març", "Abril", "Maig", "Juny",
    "Juliol", "Agost", "Setembre", "Octubre", "Novembre", "Desembre"
]

month_translations = {
    "Gener": "enero", "Febrer": "febrero", "Març": "marzo", "Abril": "abril",
    "Maig": "mayo", "Juny": "junio", "Juliol": "julio", "Agost": "agosto",
    "Setembre": "septiembre", "Octubre": "octubre", "Novembre": "noviembre", "Desembre": "diciembre"
}
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
    if pct is None: pct = 0.0
    preu_final = st.session_state.get("manual_preu_num", 0.0)
    if preu_final is None: preu_final = 0.0
    existing_prom = st.session_state.get("manual_prom_num", 0.0)
    if existing_prom is None: existing_prom = 0.0
    
    if pct > 0.0 and pct < 100.0 and preu_final > 0.0:
        qty = st.session_state.get("manual_qty_num", 1.0)
        if qty is None or qty <= 0: qty = 1.0
        
        p_orig = preu_final / (1.0 - (pct / 100.0))
        prom_per_unit = p_orig - preu_final
        prom_from_pct = prom_per_unit * qty
        
        st.session_state["manual_prom_num"] = round(existing_prom + prom_from_pct, 2)
        st.session_state["manual_preu_num"] = round(p_orig, 2)
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
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    if "df_desp" not in st.session_state:
        st.session_state["df_desp"] = fetch_all_supabase(supabase, 'despeses')
    df_desp = st.session_state["df_desp"]
    
    if "df_super" not in st.session_state:
        st.session_state["df_super"] = fetch_all_supabase(supabase, 'compresSuper')
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
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    if "df_desp" not in st.session_state:
        st.session_state["df_desp"] = fetch_all_supabase(supabase, 'despeses')
    df_desp = st.session_state["df_desp"]
    
    if "df_super" not in st.session_state:
        st.session_state["df_super"] = fetch_all_supabase(supabase, 'compresSuper')
    df_super = st.session_state["df_super"]

    
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
        
        st.write("")
        ocr_mode = st.radio("Mètode d'Escaneig", ["⚡ Híbrid (Tesseract+IA, recomanat)", "🤖 Visió Pura (Només Gemini)"], horizontal=True, help="Si la IA dóna error 503 per saturació, el mètode Híbrid sol funcionar gairebé sempre perqué és més lleuger.")
        
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
                        import requests
                        import base64
                        import json
                        from datetime import datetime
                        import pytesseract
                        from PIL import Image
                        import io
                        
                        api_key = st.secrets.get("GEMINI_API_KEY", "")
                        
                        if "Híbrid" in ocr_mode:
                            with st.spinner("1/2 - Llegint tiquet amb Tesseract OCR..."):
                                uploaded_file.seek(0)
                                img = Image.open(io.BytesIO(uploaded_file.read()))
                                try:
                                    raw_text = pytesseract.image_to_string(img, lang='cat+spa')
                                except Exception:
                                    raw_text = pytesseract.image_to_string(img)
                                
                            with st.spinner("2/2 - Endreçant i raonant dades amb IA (Gemini Text)..."):
                                prompt = f"""Ets un expert en extracció de dades de tiquets de compra.
T'han donat aquest text OCR brut d'un tiquet de supermercat (conté errors i soroll):
---
{raw_text}
---
IMPORTANT: En tiquets com els de bonArea / AreaGuissona, sovint apareix el tipus d'IVA (ex: 4.0, 10.0) a la mateixa línia del producte. 
RUTINA DE CONTROL: MAI confonguis aquest tipus d'IVA amb el preu_total. Verifica sempre lògicament que quantitat * preu_unitari sigui aproximadament igual a preu_total (tenint en compte productes a pes). Si no quadra gens i el suposat total és un nombre enter petit com 4.0 o 10.0, descarta'l com a IVA i fes la multiplicació correcta.

Extreu i neteja els productes en un format JSON estricte:
{{
    "supermercat": "Nom del supermercat (ex: bonArea, Mercadona, Dia, Novavenda, Caprabo, etc.)",
    "data": "DD/MM/YYYY (si la trobes)",
    "articles": [
        {{
            "nom_brut": "Nom exacte del producte, corregint errors d'OCR",
            "quantitat": 1,
            "preu_unitari": 0.0,
            "preu_total": 0.0
        }}
    ]
}}
Ignora descomptes genèrics, IVA, Targetes i subtotals. Extreu només productes reals.
"""
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                                payload = {
                                    "contents": [
                                        {
                                            "parts": [
                                                {"text": prompt}
                                            ]
                                        }
                                    ],
                                    "generationConfig": {
                                        "responseMimeType": "application/json"
                                    }
                                }
                        else:
                            with st.spinner("Llegint tiquet amb IA (Gemini Vision)..."):
                                mime_type = "image/jpeg"
                                if uploaded_file.name.lower().endswith(".png"):
                                    mime_type = "image/png"
                                    
                                uploaded_file.seek(0)
                                encoded_image = base64.b64encode(uploaded_file.read()).decode("utf-8")
                                
                                prompt = """
Ets un expert en extracció de dades de tiquets de compra.
Llegeix aquest tiquet de supermercat i retorna les dades en un format JSON net i estricte.

IMPORTANT: En tiquets com els de bonArea / AreaGuissona, sovint apareix el tipus d'IVA (ex: 4.0, 10.0) al final de la línia del producte. 
RUTINA DE CONTROL: MAI confonguis aquest tipus d'IVA amb el preu_total. Verifica sempre que la multiplicació quantitat * preu_unitari tingui sentit respecte al preu_total (admetent variacions per pes). Si el preu llegit no quadra i és 4.00, 10.00 o 21.00, descarta'l i utilitza el resultat lògic de multiplicar la quantitat pel preu.

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
                                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
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
                                st.session_state["ticket_date_widget"] = datetime(y_val, m_val, d_val).date()
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

    # Manual Line Input Section
    st.write("")
    st.markdown("##### ➕ Introduir línia manualment")
    
    editing_idx = st.session_state.get("editing_ticket_item_idx", None)
    if editing_idx is not None and 0 <= editing_idx < len(st.session_state.get("ticket_items", [])):
        ed_item = st.session_state["ticket_items"][editing_idx]
        if ed_item.get('article') == 'pendent':
            st.text_input("Text original (modifica si cal abans de desar per ensenyar al sistema):", value=ed_item.get('nom_brut', ''), key="manual_nom_brut_input")
            
    col_fam, col_art, col_art_btn, col_pes, col_qty, col_preu, col_pct, col_prom, col_tot, col_reb, col_add = st.columns(
        [2, 1.9, 0.3, 1, 1, 1, 0.8, 1, 1.2, 0.6, 1.2], vertical_alignment="bottom"
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
            
        art_sel = st.selectbox("ARTICLE", art_options, key="manual_art_selectbox")
        
    with col_art_btn:
        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)
        if fam_sel:
            if st.button("➕", key="btn_trigger_add_art", help="Afegir nou article", use_container_width=True):
                show_add_article_dialog(fam_sel)
                
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

# ----------------- HEADER AREA -----------------


@st.dialog("📋 Inventari Ràpid", width="large")
def modal_inventari(df_inv):
    st.write("Actualitza ràpidament l'stock agrupat pel lloc on el guardes.")
    
    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    df_llocs = fetch_all_supabase(supabase, 'tb_llocs')
    if not df_llocs.empty:
        df_llocs = df_llocs.sort_values(by='id_lloc')
        llocs_options = df_llocs['nom_lloc'].tolist()
    else:
        llocs_options = ["Sense Assignar"]
    
    # Filter only products that are tracked in Rebost
    if 'select_stock' in df_inv.columns:
        df_inv = df_inv[df_inv['select_stock'] == True].copy()
        
    if df_inv.empty:
        st.warning("No hi ha productes de rebost.")
        return
        
    # Group by lloc
    df_inv['lloc'] = df_inv.get('lloc', 'Sense Assignar').fillna('Sense Assignar')
    df_inv.loc[df_inv['lloc'] == '', 'lloc'] = 'Sense Assignar'
    
    # Track changes
    if "inv_changes" not in st.session_state:
        st.session_state.inv_changes = {}
        
    for lloc, group in df_inv.groupby('lloc'):
        with st.expander(f"📍 {lloc} ({len(group)} productes)", expanded=False):
            # Sort by familia then name
            group = group.sort_values(by=['familia', 'nom_estandard'])
            
            # Prepare data editor df
            cols_to_show = ['familia', 'nom_estandard', 'lloc', 'stock_actual', 'stock_minim']
            df_edit = group[cols_to_show].copy()
            df_edit.set_index(group['idProducte'], inplace=True)
            
            edited_df = st.data_editor(
                df_edit,
                use_container_width=True,
                disabled=['familia', 'nom_estandard'],
                hide_index=True,
                column_config={
                    "lloc": st.column_config.SelectboxColumn(
                        "Lloc",
                        help="Tria la ubicació on es guarda el producte",
                        options=llocs_options,
                        required=True
                    )
                },
                key=f"editor_inv_{lloc}"
            )
            
            for idx, row in edited_df.iterrows():
                old_act = df_edit.at[idx, 'stock_actual']
                new_act = row['stock_actual']
                old_min = df_edit.at[idx, 'stock_minim']
                new_min = row['stock_minim']
                old_loc = df_edit.at[idx, 'lloc']
                new_loc = row['lloc']
                
                if old_act != new_act or old_min != new_min or old_loc != new_loc:
                    st.session_state.inv_changes[idx] = {
                        'stock_actual': new_act,
                        'stock_minim': new_min,
                        'lloc': new_loc if pd.notna(new_loc) else None
                    }
                    
    st.markdown("---")
    if len(st.session_state.inv_changes) > 0:
        st.info(f"Tens {len(st.session_state.inv_changes)} canvis pendents de guardar.")
    else:
        st.write("No has fet canvis.")
        
    if st.button("💾 Guardar Canvis d'Inventari", type="primary", use_container_width=True):
        if len(st.session_state.inv_changes) > 0:
            try:
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                for idx, changes in st.session_state.inv_changes.items():
                    supabase.table('tb_productes').update(changes).eq('idProducte', int(idx)).execute()
                st.success(f"S'han guardat {len(st.session_state.inv_changes)} canvis correctament!")
                st.session_state.inv_changes = {}
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error guardant: {e}")

@st.dialog(" ", width="large")
def modal_recepta(row):
    is_editing = st.session_state.get(f"editing_{row['id']}", False)
    
    if is_editing:
        st.markdown("### ✏️ Editar Recepta")
        c_fields, c_img = st.columns([3, 1])
        with c_fields:
            c1, c2, c3 = st.columns(3)
            with c1:
                e_titol = st.text_input("Títol", value=row.get('titol', ''))
                cat_opts = ["Primer", "Segon", "Plat únic", "Postre", "Complement", "Guarnició", "Salsa"]
                e_cat = st.selectbox("Categoria", cat_opts, index=cat_opts.index(row.get('categoria')) if row.get('categoria') in cat_opts else 0)
                val_temps = row.get('temps_prep_minuts', 0)
                e_temps = st.number_input("Temps (min)", value=int(val_temps) if pd.notna(val_temps) else 0, step=5)
            with c2:
                apat_opts = ["Esmorzar", "Dinar", "Sopar", "Dinar/Sopar"]
                e_apat = st.selectbox("Àpat", apat_opts, index=apat_opts.index(row.get('apat')) if row.get('apat') in apat_opts else 0)
                dif_opts = ["Fàcil", "Mitjana", "Difícil"]
                e_dif = st.selectbox("Dificultat", dif_opts, index=dif_opts.index(row.get('dificultat')) if row.get('dificultat') in dif_opts else 0)
                dia_opts = ["Entre setmana", "Cap de setmana", "Festiu", "Especial"]
                e_dia = st.selectbox("Tipus de dia", dia_opts, index=dia_opts.index(row.get('tipus_dia')) if row.get('tipus_dia') in dia_opts else 0)
                temp_opts = ["Tot l'any", "Primavera", "Estiu", "Tardor", "Hivern"]
                e_temp = st.selectbox("Temporada", temp_opts, index=temp_opts.index(row.get('temporada')) if row.get('temporada') in temp_opts else 0)
            with c3:
                ori_opts = ["Biblioteca/Pròpia", "Externa/Internet"]
                e_ori = st.selectbox("Origen", ori_opts, index=ori_opts.index(row.get('origen')) if row.get('origen') in ori_opts else 0)
                val_salut = row.get('puntuacio_salut', 5)
                e_salut = st.slider("Salut (0-10)", 0, 10, int(val_salut) if pd.notna(val_salut) else 5)
                e_img_url = st.text_input("URL Imatge", value=str(row.get('imatge_url', '')).strip() if pd.notna(row.get('imatge_url')) else "")
                e_vid_url = st.text_input("URL Vídeo", value=str(row.get('video_url', '')).strip() if pd.notna(row.get('video_url')) else "")
                
            tags_opts = ["Sense Gluten", "Sense Lactosa", "Vegetarià", "Vegà", "Baix en Sal", "Baix en Greix", "Alt en Proteïna", "Sense Sucre"]
            curr_tags = row.get('tags_nutricionals')
            if not isinstance(curr_tags, list): curr_tags = []
            curr_tags = [t for t in curr_tags if t in tags_opts]
            e_tags = st.multiselect("Etiquetes / Al·lèrgies (Nutrició)", tags_opts, default=curr_tags, key=f"e_tags_{row['id']}")
            
            e_ing = st.text_area("Ingredients", value=row.get('ingredients', ''))
            e_mise = st.text_area("Mise en place (Preparació prèvia)", value=row.get('mise_en_place', ''))
            e_ins = st.text_area("Instruccions", value=row.get('instruccions', ''))
            
        with c_img:
            st.markdown("**Imatge Actual**")
            if e_img_url:
                st.image(e_img_url, use_container_width=True)
            else:
                st.info("Sense imatge")
                
            e_uploaded = st.file_uploader("Substituir imatge", type=["jpg", "jpeg", "png", "webp"], key=f"e_up_{row['id']}")
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("❌ Cancel·lar", use_container_width=True):
                st.session_state[f"editing_{row['id']}"] = False
                st.rerun()
        with col_btn2:
            if st.button("💾 Desar Canvis", use_container_width=True):
                supabase = get_supabase_client(st.session_state.get("role", "guest"))
                final_img = e_img_url
                if e_uploaded is not None:
                    try:
                        import uuid
                        file_ext = e_uploaded.name.split(".")[-1]
                        file_name = f"{uuid.uuid4()}.{file_ext}"
                        supabase.storage.from_("imatges-receptes").upload(file_name, e_uploaded.getvalue())
                        final_img = supabase.storage.from_("imatges-receptes").get_public_url(file_name)
                    except Exception as e:
                        st.error(f"Error pujant la imatge: {e}")
                
                update_data = {
                    "titol": e_titol, "categoria": e_cat, "temps_prep_minuts": e_temps,
                    "temporada": e_temp, "puntuacio_salut": e_salut, "ingredients": e_ing,
                    "mise_en_place": e_mise,
                    "instruccions": e_ins, "imatge_url": final_img, "video_url": e_vid_url,
                    "dificultat": e_dif, "tipus_dia": e_dia, "origen": e_ori, "apat": e_apat,
                    "tags_nutricionals": e_tags
                }
                
                res = supabase.table('tb_receptes_pro').update(update_data).eq('id', row['id']).execute()
                if res.data:
                    st.session_state[f"editing_{row['id']}"] = False
                    st.success("Recepta actualitzada!")
                    st.rerun()
                else:
                    st.error("Error al actualitzar.")

    else:
        # Mode Lectura
        col_titol, col_btn = st.columns([4, 1])
        with col_titol:
            st.markdown(f"## {row.get('titol', '')}")
            t_prep = int(row['temps_prep_minuts']) if pd.notna(row.get('temps_prep_minuts')) else 0
            d_dif = row['dificultat'] if pd.notna(row.get('dificultat')) else 'No definida'
            t_dia = row['tipus_dia'] if pd.notna(row.get('tipus_dia')) else 'Qualsevol'
            t_apat = row['apat'] if pd.notna(row.get('apat')) else 'Sense definir'
            st.caption(f"🥗 {row.get('categoria', '')} | ⏱️ {t_prep} min | 🔪 {d_dif} | 📅 {t_dia} | 🍽️ {t_apat}")
        with col_btn:
            st.button("✏️ Editar", key=f"edit_top_{row['id']}", on_click=cb_set_editing_recepta, args=(row['id'], True), use_container_width=True)
                
        col_i, col_d = st.columns([1, 1])
        with col_i:
            img_url = row.get('imatge_url')
            if pd.notna(img_url) and str(img_url).strip() != '':
                st.image(img_url, use_container_width=True)
                
            vid_url = row.get('video_url')
            if pd.notna(vid_url) and str(vid_url).strip() != '':
                vid_str = str(vid_url).strip()
                if "3cat.cat" in vid_str or "ccma.cat" in vid_str:
                    import urllib.request
                    import re
                    import streamlit.components.v1 as components
                    try:
                        req = urllib.request.Request(vid_str, headers={'User-Agent': 'Mozilla/5.0'})
                        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
                        match = re.search(r'"embedUrl":\s*"//(www\.3cat\.cat/video/embed/\d+/)"', html)
                        if match:
                            embed_url = f"https://{match.group(1)}"
                            components.iframe(embed_url, height=300)
                        else:
                            st.video(vid_str)
                    except:
                        st.video(vid_str)
                else:
                    st.video(vid_str)
        
        with col_d:
            st.markdown("### Ingredients:")
            ing_val = row.get('ingredients', '')
            ing_raw = str(ing_val) if pd.notna(ing_val) and str(ing_val).strip().lower() != 'nan' else ''
            if ing_raw.strip():
                import re
                lines = [re.sub(r'^[\-\*•\·]\s*', '', line.strip()).strip() for line in ing_raw.split('\n') if line.strip()]
                ing_format = " * ".join(lines)
            else:
                ing_format = "Sense ingredients"
            st.info(ing_format)
            
            mise = row.get('mise_en_place', '')
            if pd.notna(mise) and str(mise).strip() != '' and str(mise).strip().lower() != 'nan':
                st.markdown("### Mise en place:")
                st.info(str(mise).strip())
                
            st.markdown("### Info Addicional:")
            salut = row.get('puntuacio_salut', 0)
            salut_str = int(salut) if pd.notna(salut) and str(salut).strip().lower() != 'nan' else 0
            temp = row.get('temporada', '')
            temp_str = temp if pd.notna(temp) and str(temp).strip().lower() != 'nan' else "Tot l'any"
            ori = row.get('origen', 'Desconegut')
            ori_str = ori if pd.notna(ori) and str(ori).strip().lower() != 'nan' else 'Desconegut'
            
            st.write(f"**Salut:** {salut_str}/10 | **Temporada:** {temp_str}")
            st.write(f"**Origen:** {ori_str}")
            
            st.markdown("### Instruccions:")
            ins_val = row.get('instruccions', '')
            ins_raw = str(ins_val) if pd.notna(ins_val) and str(ins_val).strip().lower() != 'nan' else 'Sense instruccions'
            st.write(ins_raw)



def render():

    
    tab_scanner, tab_llista, tab_rebost = st.tabs(["📄 Escàner Súper", "📋 Llista de la Compra", "📦 Rebost / Stock"])
    
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



    
    with tab_rebost:
        try:
            supabase = get_supabase_client(st.session_state.get("role", "guest"))
            df_prods = fetch_all_supabase(supabase, 'tb_productes')
            
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                st.markdown("<h2 style='color:#3498db;'>📦 Control d'Stock (El teu Rebost)</h2>", unsafe_allow_html=True)
            with col_t2:
                st.write("") # Spacer
                if st.button("📋 Inventari", type="primary", use_container_width=True):
                    modal_inventari(df_prods)
                    
            # ================= LECTOR DE CODIS DE BARRES =================
            st.markdown("### 📷 Escanejar Codi de Barres (Càmera nativa)")
            if True:
                st.write("Clica el botó de sota per obrir la càmera del teu mòbil (o pujar una foto) per escanejar un codi de barres.")
                img_file = st.file_uploader("Fes una foto al codi de barres", type=["png", "jpg", "jpeg"], key="barcode_camera", label_visibility="collapsed")
                if img_file is not None:
                    try:
                        from pyzbar.pyzbar import decode
                        from PIL import Image
                        image = Image.open(img_file)
                        decoded_objects = decode(image)
                        
                        if not decoded_objects:
                            st.error("No s'ha detectat cap codi de barres a la imatge. Prova d'enfocar millor i que hi hagi bona llum.")
                        else:
                            barcode = decoded_objects[0].data.decode('utf-8')
                            barcode_type = decoded_objects[0].type
                            
                            st.success(f"✅ Codi llegit: **{barcode}** ({barcode_type})")
                            
                            # Lookup in database
                            res_codi = supabase.table('tb_codis_barres').select('id_producte').eq('codi_barres', barcode).execute()
                            
                            if res_codi.data:
                                # Found!
                                id_prod = res_codi.data[0]['id_producte']
                                res_prod = supabase.table('tb_productes').select('idProducte, nom_estandard, familia, stock_actual').eq('idProducte', id_prod).execute()
                                
                                if res_prod.data:
                                    prod = res_prod.data[0]
                                    st.info(f"Aquest codi correspon a: **{prod['nom_estandard']}** (Stock actual: {prod['stock_actual']})")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("➕ Afegir 1 a l'stock", type="primary", use_container_width=True, key=f"add_{barcode}"):
                                            new_stock = float(prod['stock_actual']) + 1.0
                                            supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', id_prod).execute()
                                            st.success(f"Afegit! Nou stock: {new_stock}")
                                            st.cache_data.clear()
                                            st.rerun()
                                    with col2:
                                        if st.button("➖ Gastar 1 de l'stock", type="secondary", use_container_width=True, key=f"sub_{barcode}"):
                                            new_stock = max(0.0, float(prod['stock_actual']) - 1.0)
                                            supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', id_prod).execute()
                                            st.success(f"Gastat! Nou stock: {new_stock}")
                                            st.cache_data.clear()
                                            st.rerun()
                            else:
                                # Not found. Ask to associate.
                                st.warning("Aquest codi no està associat a cap producte del teu rebost.")
                                if not df_prods.empty:
                                    df_p = df_prods.sort_values(by=['familia', 'nom_estandard'])
                                    prod_options = df_p.apply(lambda r: f"{r['nom_estandard']} ({r['familia']})", axis=1).tolist()
                                    prod_ids = df_p['idProducte'].tolist()
                                    
                                    selected_idx = st.selectbox("A quin producte correspon?", range(len(prod_options)), format_func=lambda i: prod_options[i])
                                    
                                    if st.button("🔗 Enllaçar Codi i Producte", use_container_width=True):
                                        try:
                                            supabase.table('tb_codis_barres').insert({
                                                'codi_barres': barcode,
                                                'id_producte': prod_ids[selected_idx]
                                            }).execute()
                                            st.success("Enllaçat correctament! Pots prémer els botons per actualitzar l'stock.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error enllaçant: {e}")
                    except Exception as e:
                        st.error(f"Error processant la imatge: {e}")
            
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            if not df_prods.empty:
                # ================= REGISTRE DE BAIXES =================
                st.markdown("### 🍽️ Registrar Baixa d'Stock")
                st.write("Has gastat un producte? Registra-ho aquí perquè l'stock baixi de forma segura.")
                
                # Filter only products that have select_stock == True and stock_actual > 0
                # Wait, df_prods might not have stock_actual as float yet, let's fillna first
                for col in ['stock_actual', 'stock_minim']:
                    if col not in df_prods.columns:
                        df_prods[col] = 0.0
                    else:
                        df_prods[col] = pd.to_numeric(df_prods[col], errors='coerce').fillna(0.0)
                        
                if 'select_stock' not in df_prods.columns:
                    df_prods['select_stock'] = False
                
                df_available = df_prods[(df_prods['select_stock'] == True) & (df_prods['stock_actual'] > 0)].copy()
                
                if not df_available.empty:
                    families = sorted([str(f) for f in df_available['familia'].dropna().unique() if str(f).strip() != ""])
                    families = ["Totes"] + families
                        
                    if 'selected_family_consum' not in st.session_state:
                        st.session_state['selected_family_consum'] = families[0] if families else None
                    elif st.session_state['selected_family_consum'] not in families:
                        st.session_state['selected_family_consum'] = families[0] if families else None
                        
                    # Create horizontal radio for families
                    st.radio(
                        "1️⃣ Tria la família:", 
                        families, 
                        horizontal=True,
                        key='selected_family_consum'
                    )
                    
                    # Generate 6 columns grid for smaller buttons (TPV style)
                    cols_per_row = 6
                    
                    # Inject CSS to make mobile grid 3 columns
                    st.components.v1.html("""
                    <script>
                        const parentDoc = window.parent.document;
                        const spans = parentDoc.querySelectorAll('strong');
                        spans.forEach(span => {
                            if(span.innerText.includes('Què has gastat?')) {
                                const verticalBlock = span.closest('div[data-testid="stVerticalBlock"]');
                                if(verticalBlock) {
                                    verticalBlock.classList.add('stock-grid-container');
                                }
                            }
                        });
                        
                        if (!parentDoc.getElementById('stock-grid-style')) {
                            const style = parentDoc.createElement('style');
                            style.id = 'stock-grid-style';
                            style.innerHTML = `
                                @media (max-width: 576px) {
                                    .stock-grid-container div[data-testid="stHorizontalBlock"] {
                                        flex-wrap: wrap !important;
                                    }
                                    .stock-grid-container div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                                        min-width: calc(33.33% - 1rem) !important;
                                        flex: 1 1 calc(33.33% - 1rem) !important;
                                    }
                                }
                            `;
                            parentDoc.head.appendChild(style);
                        }
                    </script>
                    """, height=0)
                    
                    sel_fam = st.session_state['selected_family_consum']
                    if sel_fam:
                        if sel_fam == "Totes":
                            df_fam = df_available.sort_values('nom_estandard')
                        elif sel_fam == "Sense Família":
                            df_fam = df_available[df_available['familia'].isna() | (df_available['familia'] == "")].sort_values('nom_estandard')
                        else:
                            df_fam = df_available[df_available['familia'] == sel_fam].sort_values('nom_estandard')
                            
                        st.markdown(f"**2️⃣ Què has gastat? (Toca per restar-ne 1)**")
                        
                        for i in range(0, len(df_fam), cols_per_row):
                            cols = st.columns(cols_per_row)
                            chunk = df_fam.iloc[i:i+cols_per_row]
                            for j, (_, row) in enumerate(chunk.iterrows()):
                                prod_name = row['nom_estandard']
                                stock = int(row['stock_actual']) # Convert to int
                                
                                with cols[j]:
                                    # Use HTML to enforce a fixed height for all images/placeholders
                                    # This guarantees all buttons align perfectly at the bottom
                                    if 'foto_url' in row and pd.notna(row['foto_url']) and str(row['foto_url']).strip() != "":
                                        foto_src = str(row['foto_url']).strip()
                                        
                                        # Handle local files by converting to base64 for HTML img tag
                                        import base64
                                        import os
                                        
                                        img_src = foto_src
                                        if not foto_src.startswith("http"):
                                            # It's a local file
                                            if os.path.exists(foto_src):
                                                with open(foto_src, "rb") as f:
                                                    b64_data = base64.b64encode(f.read()).decode("utf-8")
                                                    ext = foto_src.split('.')[-1].lower()
                                                    mime = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                                                    img_src = f"data:{mime};base64,{b64_data}"
                                            else:
                                                img_src = "" # File not found
                                                
                                        if img_src:
                                            st.markdown(f'''
                                                <div style="height: 80px; display: flex; justify-content: center; align-items: center; margin-bottom: 5px;">
                                                    <img src="{img_src}" style="max-height: 100%; max-width: 100%; border-radius: 8px; object-fit: contain; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                                                </div>
                                            ''', unsafe_allow_html=True)
                                        else:
                                            # File was local but not found, show placeholder
                                            st.markdown('''
                                                <div style="height: 80px; display: flex; justify-content: center; align-items: center; margin-bottom: 5px; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #dee2e6;">
                                                    <span style="font-size: 2rem; color: #ced4da;">📦</span>
                                                </div>
                                            ''', unsafe_allow_html=True)
                                    else:
                                        # Placeholder for items without image to maintain alignment
                                        st.markdown('''
                                            <div style="height: 80px; display: flex; justify-content: center; align-items: center; margin-bottom: 5px; background-color: #f8f9fa; border-radius: 8px; border: 1px dashed #dee2e6;">
                                                <span style="font-size: 2rem; color: #ced4da;">📦</span>
                                            </div>
                                        ''', unsafe_allow_html=True)
                                            
                                    btn_label = f"{prod_name}\n📦 {stock}"
                                    
                                    if st.button(btn_label, key=f"btn_consum_{row['idProducte']}", use_container_width=True):
                                        new_stock = stock - 1.0
                                        supabase.table('tb_productes').update({'stock_actual': new_stock}).eq('idProducte', row['idProducte']).execute()
                                        st.success(f"➖ 1x {prod_name} gastat! (Et queden {int(new_stock)})")
                                        st.cache_data.clear() # Clear cache so other devices see it
                                        st.rerun()
                else:
                    st.info("Actualment no tens cap producte controlat amb stock disponible (> 0).")
                


                st.divider()
                st.markdown("### 📋 Taula d'Edició Ràpida")
                st.write("Edita les quantitats i el lloc on guardes cada article directament a la taula.")
                # We need to make sure cols exist in df
                for col in ['stock_actual', 'stock_minim']:
                    if col not in df_prods.columns:
                        df_prods[col] = 0.0
                if 'lloc' not in df_prods.columns:
                    df_prods['lloc'] = ""
                if 'super_habitual' not in df_prods.columns:
                    df_prods['super_habitual'] = None
                
                # Ensure select_stock exists
                if 'select_stock' not in df_prods.columns:
                    df_prods['select_stock'] = False
                    
                # Order by familia and nom
                df_prods = df_prods.sort_values(by=['familia', 'nom_estandard'])
                
                # Filter ONLY items that are in the pantry (select_stock == True)
                df_prods_filtered = df_prods[df_prods['select_stock'] == True].copy()
                
                # Fetch dynamically updated locations
                df_llocs = fetch_all_supabase(supabase, 'tb_llocs')
                if not df_llocs.empty:
                    df_llocs = df_llocs.sort_values(by='id_lloc')
                    llocs_options = df_llocs['nom_lloc'].tolist()
                else:
                    llocs_options = ["Sense Assignar"]
                    
                with st.form("form_edicio_rapida_stock"):
                    edited_df = st.data_editor(
                        df_prods_filtered[['idProducte', 'select_stock', 'nom_estandard', 'familia', 'super_habitual', 'stock_actual', 'stock_minim', 'lloc']],
                        column_config={
                            "idProducte": None,
                            "select_stock": st.column_config.CheckboxColumn("En Rebost?", default=True),
                            "nom_estandard": st.column_config.TextColumn("Producte", disabled=True),
                            "familia": st.column_config.TextColumn("Família", disabled=True),
                            "super_habitual": st.column_config.SelectboxColumn("Súper Habitual", options=get_config_supers() + ["Sense Assignar"], required=False),
                            "stock_actual": st.column_config.NumberColumn("Stock Actual", min_value=0.0, step=1.0),
                            "stock_minim": st.column_config.NumberColumn("Stock Mínim", min_value=0.0, step=1.0),
                            "lloc": st.column_config.SelectboxColumn("Lloc", options=llocs_options, required=False)
                        },
                        hide_index=True,
                        use_container_width=True,
                        key="editor_stock"
                    )
                    
                    submitted = st.form_submit_button("Guardar Estat del Stock", type="primary")
                
                if submitted:
                    # We need to find changed rows and update supabase
                    updates_made = 0
                    for i, row in edited_df.iterrows():
                        orig_row = df_prods_filtered.loc[i]
                        if (row['stock_actual'] != orig_row['stock_actual'] or 
                            row['stock_minim'] != orig_row['stock_minim'] or 
                            row['lloc'] != orig_row['lloc'] or
                            row['super_habitual'] != orig_row['super_habitual'] or
                            row['select_stock'] != orig_row['select_stock']):
                            
                            def s_float(v):
                                try:
                                    val = float(v)
                                    import math
                                    return 0.0 if math.isnan(val) else val
                                except:
                                    return 0.0
                                    
                            supabase.table('tb_productes').update({
                                'select_stock': bool(row['select_stock']),
                                'stock_actual': s_float(row['stock_actual']),
                                'stock_minim': s_float(row['stock_minim']),
                                'lloc': str(row['lloc']) if pd.notna(row['lloc']) and str(row['lloc']).strip().lower() != "none" else None,
                                'super_habitual': str(row['super_habitual']) if pd.notna(row['super_habitual']) and str(row['super_habitual']).strip().lower() != "none" else None
                            }).eq('idProducte', row['idProducte']).execute()
                            updates_made += 1
                            
                    if updates_made > 0:
                        st.success(f"S'han actualitzat {updates_made} productes!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.info("No s'ha detectat cap canvi.")
                        
        except Exception as e:
            st.error(f"Error carregant dades del rebost: {e}")

# ================= TAB 4: BASES DE DADES (Supabase) =================