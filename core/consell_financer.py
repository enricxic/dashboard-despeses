"""
core/consell_financer.py
Motor del 'Consell d'Ancians' financer per a XiquiHouse.
Inspirat en l'arquitectura multi-agent de Google ADK (Council of Ancients):
- 3 Consellers especialitzats amb filosofies contraposades:
    1. Sèneca (Prudència, gestió de riscos, fons d'emergència)
    2. Keynes (Estratègia, ROI, optimització de capital, cost d'oportunitat)
    3. Epicur (Benestar familiar, qualitat de vida, reducció d'estrès)
- 1 President del Consell (Facilitador / Sintetitzador que extreu consensos, riscos i veredicte final).
Execució concurrent via ThreadPoolExecutor per minimitzar la latència.
"""

from concurrent.futures import ThreadPoolExecutor
import time
from typing import Dict, Any, Optional
import streamlit as st

from core.llm import call_llm_api

# ----------------- PROMPTS DELS CONSELLERS -----------------

PROMPT_SENECA = """Ets SÈNECA, l'Ancià Prudent del Consell Financer de XiquiHouse.
La teva filosofia: estoïcisme, gestió del risc, fons d'emergència i tranquil·litat familiar davant de qualsevol imprevist.
REGLA D'OR DE BREVETAT I CLARETAT (MOLT IMPORTANT):
- Vés DIRECTE al gra, sense salutacions ni introduccions buides.
- Respon OBLIGATÒRIAMENT en un màxim de 3 punts curts (bullets).
- Longitud total: Màxim 70-90 paraules en total. Prohibit allargar-te.
- To: assenyat, estoic i realista, en català."""

PROMPT_KEYNES = """Ets KEYNES, l'Ancià Estrateg del Consell Financer de XiquiHouse.
La teva filosofia: inversió intel·ligent, no deixar diners parats perdent per la inflació, retorn (ROI) i cost d'oportunitat.
REGLA D'OR DE BREVETAT I CLARETAT (MOLT IMPORTANT):
- Vés DIRECTE al gra, sense salutacions ni teoria econòmica abstracta.
- Respon OBLIGATÒRIAMENT en un màxim de 3 punts curts (bullets) amb criteris i recomanacions pràctiques.
- Longitud total: Màxim 70-90 paraules en total. Prohibit allargar-te.
- To: àgil, pragmàtic i analític, en català."""

PROMPT_EPICUR = """Ets EPICUR, l'Ancià del Benestar del Consell Financer de XiquiHouse.
La teva filosofia: benestar de la llar, qualitat de vida familiar, pau mental i gaudi raonable del present.
REGLA D'OR DE BREVETAT I CLARETAT (MOLT IMPORTANT):
- Vés DIRECTE al gra, sense salutacions ni preàmbuls.
- Respon OBLIGATÒRIAMENT en un màxim de 3 punts curts (bullets) enfocats a la convivència, descans i felicitat familiar.
- Longitud total: Màxim 70-90 paraules en total. Prohibit allargar-te.
- To: càlid, empàtic i humà, en català."""

PROMPT_PRESIDENT = """Ets el PRESIDENT DEL CONSELL FINANCER de XiquiHouse.
Has d'arbitrar i sintetitzar les deliberacions dels 3 ancians (Sèneca la Prudència, Keynes l'Estratègia i Epicur el Benestar) per donar un veredicte clar i executable a la família.

REGLA D'OR DE BREVETAT (MOLT IMPORTANT):
- Màxim 110-130 paraules en total per a tota la teva resposta. Sigues concís, contundent i pràctic.
- Respon OBLIGATÒRIAMENT estructurat en aquests 4 punts clau:
1. 🤝 **Consens**: En què coincideixen els 3 consellers? (1 frase curta)
2. ⚡ **Tensió clau**: Quin és el dilema principal (ex: risc vs oportunitat, estalvi vs confort)? (1 frase curta)
3. ⚖️ **Veredicte**: Quina decisió recomana el Consell tenint en compte les dades reals? (1 o 2 frases curtes)
4. 📋 **Passos immediats**: 2 accions pràctiques per executar avui o demà. (2 punts curts)"""


def construir_resum_dades(df_desp, df_ing, df_cartera, any_analitzar: Optional[int] = None) -> str:
    """Condensa les dades financeres clau per enviar el context als consellers sense saturar tokens."""
    try:
        import pandas as pd
        any_actual = int(any_analitzar) if any_analitzar is not None else 2026
        
        # 1. Anàlisi taula despeses.csv (Import càrrec i import ingrés)
        if df_desp is not None and not df_desp.empty:
            any_s = pd.to_numeric(df_desp.get("any"), errors="coerce")
            desp_any = df_desp[any_s == any_actual].copy()
            
            # Excloure traspassos interns entre comptes (op_banc)
            if "Idcategoria" in desp_any.columns:
                desp_any = desp_any[desp_any["Idcategoria"] != "op_banc"]
            if "grup" in desp_any.columns:
                desp_any = desp_any[desp_any["grup"] != "op_banc"]
                
            # Trobar columna de càrrecs (despeses reals)
            col_carrec = next((c for c in desp_any.columns if any(w in c.lower() for w in ["carrec", "càrrec", "crrec"])), None)
            tot_desp = pd.to_numeric(desp_any[col_carrec], errors="coerce").sum() if col_carrec else 0.0

            # Trobar columna d'ingressos bancaris
            col_ing = next((c for c in desp_any.columns if "ingr" in c.lower()), None)
            tot_ing = pd.to_numeric(desp_any[col_ing], errors="coerce").sum() if col_ing else 0.0

            # Categories principals de despesa
            top_cat = ""
            cat_col = "Idcategoria" if "Idcategoria" in desp_any.columns else ("Categoria" if "Categoria" in desp_any.columns else None)
            if cat_col and col_carrec:
                gr = desp_any.groupby(cat_col)[col_carrec].sum().sort_values(ascending=False).head(5)
                top_cat = ", ".join([f"{c}: {v:,.0f}€" for c, v in gr.items() if v > 0])
        else:
            tot_desp = 0.0
            tot_ing = 0.0
            top_cat = "Sense dades"

        # 2. Ingressos des de la taula ingressos.csv si no en tenim a despeses
        if tot_ing == 0.0 and df_ing is not None and not df_ing.empty:
            any_ing = pd.to_numeric(df_ing.get("any"), errors="coerce")
            ing_any = df_ing[any_ing == any_actual]
            if "Import" in ing_any.columns:
                tot_ing = pd.to_numeric(ing_any["Import"], errors="coerce").sum()

        balanc_any = tot_ing - tot_desp

        # 3. Cartera d'inversió (tr_cartera.csv)
        tot_cartera = 0.0
        if df_cartera is not None and not df_cartera.empty:
            compra = pd.to_numeric(df_cartera.get("COMPRA", 0), errors="coerce").fillna(0).sum()
            venda = pd.to_numeric(df_cartera.get("VENDA", 0), errors="coerce").fillna(0).sum()
            tot_cartera = compra - venda
            if tot_cartera == 0.0 and "saldo" in df_cartera.columns:
                tot_cartera = pd.to_numeric(df_cartera["saldo"], errors="coerce").fillna(0).sum()

        resum = (
            f"- Any d'anàlisi: {any_actual}\n"
            f"- Total Ingressos de l'any: {tot_ing:,.2f} €\n"
            f"- Total Despeses de l'any: {tot_desp:,.2f} €\n"
            f"- Balanç de l'any (Ingressos - Despeses): {balanc_any:,.2f} €\n"
            f"- Categories de despesa principals: {top_cat}\n"
            f"- Valor total invertit en cartera (actius): {tot_cartera:,.2f} €\n"
        )
        return resum
    except Exception as e:
        return f"- Context financer resumit no disponible ({e})"


def _consultar_membre(prompt_sistema: str, consulta: str, context_financier: str, api_key: str, model_name: str, provider: str) -> str:
    """Executa la consulta per a un membre individual del consell amb límit de seguretat de tokens."""
    prompt_complet = (
        f"{prompt_sistema}\n\n"
        f"--- CONTEXT FINANCER DE XIQUIHOUSE ---\n{context_financier}\n\n"
        f"--- CONSULTA DE LA FAMÍLIA ---\n{consulta}\n\n"
        f"Emet la teva resposta breu (màxim 3 punts curts):"
    )
    ok, resp, _ = call_llm_api(
        prompt_complet,
        api_key=api_key,
        model_name=model_name,
        provider=provider,
        max_tokens=1000
    )
    if ok and resp.strip():
        return resp.strip()
    return f"⚠️ No s'ha pogut obtenir l'opinió del conseller (Error de resposta)."


def deliberar_consell(
    consulta: str,
    df_desp,
    df_ing,
    df_cartera,
    any_analitzar: Optional[int] = None,
    api_key: str = "",
    model_name: str = "gemini-flash-lite-latest",
    provider: str = "gemini"
) -> Dict[str, Any]:
    """
    Executa la deliberació completa del Consell d'Ancians:
    1. Crida en paral·lel a Sèneca, Keynes i Epicur (max_tokens=1000).
    2. Recull les 3 opinions.
    3. Convoca el President per emetre el veredicte final ponderat (max_tokens=1500).
    """
    t_start = time.time()
    context_str = construir_resum_dades(df_desp, df_ing, df_cartera, any_analitzar)
    
    # 1. Execució paral·lela dels 3 consellers
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_seneca = executor.submit(_consultar_membre, PROMPT_SENECA, consulta, context_str, api_key, model_name, provider)
        f_keynes = executor.submit(_consultar_membre, PROMPT_KEYNES, consulta, context_str, api_key, model_name, provider)
        f_epicur = executor.submit(_consultar_membre, PROMPT_EPICUR, consulta, context_str, api_key, model_name, provider)
        
        op_seneca = f_seneca.result()
        op_keynes = f_keynes.result()
        op_epicur = f_epicur.result()

    # 2. Crida final de síntesi al President
    deliberacio_conjunta = (
        f"--- DELIBERACIÓ DELS 3 CONSELLERS ---\n\n"
        f"🏛️ OPINIÓ DE SÈNECA (Prudència i Risc):\n{op_seneca}\n\n"
        f"📈 OPINIÓ DE KEYNES (Estratègia i Creixement):\n{op_keynes}\n\n"
        f"🏡 OPINIÓ D'EPICUR (Benestar i Família):\n{op_epicur}\n\n"
        f"--- CONTEXT DE LA CASA ---\n{context_str}\n\n"
        f"--- PREGUNTA DE LA FAMÍLIA ---\n{consulta}\n\n"
        f"President, sintetitza la deliberació i emet el veredicte final segons l'estructura demanada (màxim 120 paraules):"
    )
    
    ok_p, veredicte_text, _ = call_llm_api(
        f"{PROMPT_PRESIDENT}\n\n{deliberacio_conjunta}",
        api_key=api_key,
        model_name=model_name,
        provider=provider,
        max_tokens=1500
    )
    if not ok_p or not veredicte_text.strip():
        veredicte_text = "⚠️ No s'ha pogut generar el veredicte del President."

    elapsed = round(time.time() - t_start, 2)

    return {
        "consulta": consulta,
        "temps": elapsed,
        "seneca": {
            "nom": "Sèneca",
            "titol": "L'Ancià Prudent (Risc & Seguretat)",
            "icona": "🛡️",
            "color": "#2980b9",
            "opinio": op_seneca
        },
        "keynes": {
            "nom": "Keynes",
            "titol": "L'Ancià Estrateg (ROI & Oportunitat)",
            "icona": "📈",
            "color": "#d35400",
            "opinio": op_keynes
        },
        "epicur": {
            "nom": "Epicur",
            "titol": "L'Ancià del Benestar (Qualitat de Vida)",
            "icona": "🏡",
            "color": "#27ae60",
            "opinio": op_epicur
        },
        "president": {
            "nom": "President del Consell",
            "titol": "Veredicte Final de Síntesi",
            "icona": "⚖️",
            "color": "#8e44ad",
            "veredicte": veredicte_text
        }
    }
