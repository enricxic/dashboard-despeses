import os
import re
import unicodedata
import pandas as pd
from typing import List, Dict, Any, Tuple
from core.db import get_supabase_client, load_categories_conceptes, save_categories_conceptes

TABLE_SPECS = {
    "despeses": {
        "pk": "ID_mov",
        "date_cols": ["Data"],
        "cat_col": "Idcategoria",
        "concept_col": "Idconcepte",
        "bank_col": "Banc",
        "forma_col": "FormaPago",
        "csv": "csv/despeses.csv"
    },
    "ingressos": {
        "pk": "idIngres",
        "date_cols": ["Data"],
        "cat_col": "Categoria",
        "concept_col": "Concepte",
        "bank_col": "Banc",
        "forma_col": None,
        "csv": "csv/ingressos.csv"
    },
    "pagaments": {
        "pk": "idPago",
        "date_cols": ["Data"],
        "cat_col": "Categoria",
        "concept_col": "Concepte",
        "bank_col": "Banc",
        "forma_col": "Formapago",
        "csv": "csv/pagaments.csv"
    },
    "tr_cartera": {
        "pk": "idTRCartera",
        "date_cols": ["DATA"],
        "cat_col": None,
        "concept_col": "CONCEPTE",
        "bank_col": "CARTERA",
        "forma_col": None,
        "csv": "csv/tr_cartera.csv"
    },
    "compresSuper": {
        "pk": "IdCompra",
        "date_cols": ["data"],
        "cat_col": None,
        "concept_col": None,
        "bank_col": None,
        "forma_col": None,
        "csv": "csv/compresSuper.csv"
    },
    "kmCotxe": {
        "pk": "idRuta",
        "date_cols": ["data"],
        "cat_col": None,
        "concept_col": None,
        "bank_col": None,
        "forma_col": None,
        "csv": "csv/kmCotxe.csv"
    }
}

EXPLICIT_CAT_MAP = {
    "butà": "buta",
    "farmàcia": "farmacia",
    "ingrés_general": "ingres_general",
    "ingrés_extra": "ingres_extra",
    "Parallar": "parallar",
    "mant_netej": "manteniment",
    "assegurança": "asseguranca",
    "assegurana": "asseguranca"
}

def remove_accents(input_str: str) -> str:
    if not isinstance(input_str, str):
        return input_str
    nfkd = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).replace('ç', 'c').replace('Ç', 'C')

def normalitzar_data_str(val: Any) -> Tuple[str, bool]:
    if val is None or pd.isna(val):
        return "", False
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "nat"):
        return "", False
    
    # Treure part d'hora si n'hi ha (e.g. 2026-10-13 00:00:00 o 2026-10-13T00:00:00)
    if " " in s:
        s = s.split(" ")[0].strip()
    elif "t" in s.lower():
        s = re.split(r'[tT]', s)[0].strip()

    # Si ja és estrictament DD/MM/AAAA
    m_ddmmyyyy = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m_ddmmyyyy:
        d, m, y = m_ddmmyyyy.groups()
        canon = f"{int(d):02d}/{int(m):02d}/{int(y):04d}"
        return (canon, canon != s)

    # Format ISO: YYYY-MM-DD o YYYY/MM/DD
    m_iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", s)
    if m_iso:
        y, m, d = m_iso.groups()
        canon = f"{int(d):02d}/{int(m):02d}/{int(y):04d}"
        return canon, True

    # Format DD-MM-YYYY
    m_dmy_dash = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", s)
    if m_dmy_dash:
        d, m, y = m_dmy_dash.groups()
        canon = f"{int(d):02d}/{int(m):02d}/{int(y):04d}"
        return canon, True

    # Intent de parsing amb pandas com a darrer recurs
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            canon = dt.strftime("%d/%m/%Y")
            return canon, (canon != s)
    except Exception:
        pass

    return s, False

def normalitzar_categoria_str(val: Any, categories_canoniques: List[str]) -> Tuple[str, bool]:
    if val is None or pd.isna(val):
        return "", False
    s = str(val).strip()
    if not s:
        return "", False
    
    # 1. Comprovació al mapa explícit
    if s in EXPLICIT_CAT_MAP:
        return EXPLICIT_CAT_MAP[s], True

    # 2. Minúscula sense accent
    s_clean = remove_accents(s).lower()
    if s_clean != s and s_clean in categories_canoniques:
        return s_clean, True
    
    if s in categories_canoniques:
        return s, False

    if s_clean in categories_canoniques:
        return s_clean, True

    return s, False

def normalitzar_concepte_str(val: Any) -> Tuple[str, bool]:
    if val is None or pd.isna(val):
        return "", False
    s = str(val).strip()
    if not s:
        return "", False
    
    # Harmonitzacions conegudes
    if s == "Gestions Banc":
        return "Gestions banc", True
    
    return s, False

def diagnosticar_taula(nom_taula: str, ambits: List[str], supabase=None) -> List[Dict[str, Any]]:
    if nom_taula not in TABLE_SPECS:
        return []
    
    spec = TABLE_SPECS[nom_taula]
    pk_col = spec["pk"]
    
    # Carregar dades: primer supabase, si falla o offline -> CSV
    df = None
    if supabase:
        try:
            res = supabase.table(nom_taula).select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
        except Exception as e:
            print(f"Error llegint {nom_taula} de Supabase: {e}")
    
    if df is None or df.empty:
        csv_path = spec.get("csv")
        if csv_path and os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                print(f"Error llegint CSV {csv_path}: {e}")
    
    if df is None or df.empty:
        return []

    cats_cfg = load_categories_conceptes()
    categories_canoniques = [remove_accents(k).lower() for k in cats_cfg.keys()]

    discrepancies = []

    for idx, row in df.iterrows():
        pk_val = row.get(pk_col)
        if pd.isna(pk_val):
            continue

        # 1. Dates
        if "dates" in ambits:
            for d_col in spec.get("date_cols", []):
                if d_col in df.columns:
                    val_act = row.get(d_col)
                    val_nou, mod = normalitzar_data_str(val_act)
                    if mod and val_nou != str(val_act):
                        discrepancies.append({
                            "taula": nom_taula,
                            "pk_col": pk_col,
                            "pk_val": pk_val,
                            "columna": d_col,
                            "valor_actual": "" if pd.isna(val_act) else str(val_act),
                            "valor_nou": val_nou,
                            "motiu": "Format data no normalitzat (convertir a DD/MM/AAAA)",
                            "ambit": "dates"
                        })

        # 2. Categories
        if "categories" in ambits:
            c_col = spec.get("cat_col")
            if c_col and c_col in df.columns:
                val_act = row.get(c_col)
                val_nou, mod = normalitzar_categoria_str(val_act, categories_canoniques)
                if mod and val_nou != str(val_act):
                    discrepancies.append({
                        "taula": nom_taula,
                        "pk_col": pk_col,
                        "pk_val": pk_val,
                        "columna": c_col,
                        "valor_actual": "" if pd.isna(val_act) else str(val_act),
                        "valor_nou": val_nou,
                        "motiu": "Categoria amb accent o format no canònic",
                        "ambit": "categories"
                    })

        # 3. Conceptes
        if "conceptes" in ambits:
            conc_col = spec.get("concept_col")
            if conc_col and conc_col in df.columns:
                val_act = row.get(conc_col)
                val_nou, mod = normalitzar_concepte_str(val_act)
                if mod and val_nou != str(val_act):
                    discrepancies.append({
                        "taula": nom_taula,
                        "pk_col": pk_col,
                        "pk_val": pk_val,
                        "columna": conc_col,
                        "valor_actual": "" if pd.isna(val_act) else str(val_act),
                        "valor_nou": val_nou,
                        "motiu": "Concepte no harmonitzat",
                        "ambit": "conceptes"
                    })

        # 4. Bancs i Formes de Pagament
        if "bancs" in ambits:
            b_col = spec.get("bank_col")
            if b_col and b_col in df.columns:
                val_act = row.get(b_col)
                if pd.notna(val_act) and isinstance(val_act, str):
                    val_clean = val_act.strip()
                    if val_clean != val_act:
                        discrepancies.append({
                            "taula": nom_taula,
                            "pk_col": pk_col,
                            "pk_val": pk_val,
                            "columna": b_col,
                            "valor_actual": str(val_act),
                            "valor_nou": val_clean,
                            "motiu": "Espais sobrants al nom del banc",
                            "ambit": "bancs"
                        })
            f_col = spec.get("forma_col")
            if f_col and f_col in df.columns:
                val_act = row.get(f_col)
                if pd.notna(val_act) and isinstance(val_act, str):
                    val_clean = val_act.strip()
                    if val_clean != val_act:
                        discrepancies.append({
                            "taula": nom_taula,
                            "pk_col": pk_col,
                            "pk_val": pk_val,
                            "columna": f_col,
                            "valor_actual": str(val_act),
                            "valor_nou": val_clean,
                            "motiu": "Espais sobrants a la forma de pagament",
                            "ambit": "bancs"
                        })

    return discrepancies

def aplicar_discrepancies(discrepancies: List[Dict[str, Any]], supabase=None) -> Dict[str, Any]:
    if not discrepancies:
        return {"actualitzats": 0, "errors": []}

    # Agrupar canvis per (taula, pk_col, pk_val)
    grouped = {}
    for item in discrepancies:
        key = (item["taula"], item["pk_col"], item["pk_val"])
        if key not in grouped:
            grouped[key] = {}
        grouped[key][item["columna"]] = item["valor_nou"]

    actualitzats = 0
    errors = []

    # Actualitzar a Supabase si tenim connexió
    if supabase:
        for (taula, pk_col, pk_val), updates in grouped.items():
            try:
                res = supabase.table(taula).update(updates).eq(pk_col, pk_val).execute()
                actualitzats += 1
            except Exception as e:
                errors.append(f"Error actualitzant {taula} ({pk_col}={pk_val}): {e}")
    else:
        actualitzats = len(grouped)

    # Actualitzar CSVs locals també per consistència
    tables_involved = set(t for (t, _, _) in grouped.keys())
    for t in tables_involved:
        spec = TABLE_SPECS.get(t)
        if not spec:
            continue
        csv_path = spec.get("csv")
        if csv_path and os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                pk_col = spec["pk"]
                modified = False
                for (taula, p_col, pk_val), updates in grouped.items():
                    if taula != t:
                        continue
                    # Match row
                    mask = (df[pk_col].astype(str) == str(pk_val))
                    if mask.any():
                        for col, new_val in updates.items():
                            if col in df.columns:
                                df.loc[mask, col] = new_val
                                modified = True
                if modified:
                    df.to_csv(csv_path, index=False)
            except Exception as e:
                errors.append(f"Error actualitzant CSV {csv_path}: {e}")

    return {"actualitzats": actualitzats, "errors": errors}
