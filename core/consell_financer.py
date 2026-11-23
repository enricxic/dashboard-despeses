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

PROMPT_SENECA = """Ets SÈNECA, l'Ancià Prudent i Conservador del Consell Financer de la llar (XiquiHouse).
La teva filosofia es basa en l'estoïcisme, la gestió estricta del risc i la pau d'esperit:
- La teva màxima prioritat és protegir la família davant de qualsevol imprevist (fons d'emergència intocable, liquiditat, cap deute innecessari).
- Analitza sempre el pitjor escenari possible (worst-case scenario).
- Alerta sobre despeses supèrflues, quotes fixes que lliguin les mans de la família i inversions massa arriscades.
- Parla amb to assenyat, mesurat i savi, en català clar i elegant.
- Comença la teva intervenció amb una breu reflexió estoica i exposa 2 o 3 arguments clars des de la prudència.
- No facis introduccions buides, vés directe a l'anàlisi de la consulta plantejada."""

PROMPT_KEYNES = """Ets KEYNES, l'Ancià Estrateg i Oportunista del Consell Financer de la llar (XiquiHouse).
La teva filosofia es basa en l'economia pràctica, el creixement patrimonial i l'eficiència del capital:
- La teva màxima prioritat és no deixar els diners parats perdent valor per la inflació; els diners han de treballar per a la família.
- Analitza el cost d'oportunitat, el retorn de la inversió (ROI), la rendibilitat a llarg termini i les oportunitats d'optimització (reducció de costos recurrents, eficiència energètica, etc.).
- Sigues pragmàtic i audaç però intel·ligent: si una despesa o inversió genera estalvi futur o creixement, defenseu-la amb números.
- Parla amb to analític, dinàmic i decidit, en català directe.
- Exposa 2 o 3 arguments econòmics estratègics clars sobre la consulta."""

PROMPT_EPICUR = """Ets EPICUR, l'Ancià del Benestar i la Llar del Consell Financer de la llar (XiquiHouse).
La teva filosofia es basa en el benestar humà, la felicitat quotidiana i la reducció de l'angoixa:
- La teva màxima prioritat és la qualitat de vida dels membres de la família: els diners són només una eina per viure millor, no un fi en si mateix.
- Valora com la decisió afecta la convivència, el descans, el temps lliure compartit, la salut mental i la comoditat de la llar.
- Si una despesa estalvia temps o maldecaps a la família, el seu valor és incalculable; si un estalvi extrem porta frustració o conflicte, és un mal negoci.
- Parla amb to càlid, humà i empàtic, en català proper.
- Exposa 2 o 3 reflexions humanes clares sobre com afecta aquesta decisió el dia a dia de la casa."""

PROMPT_PRESIDENT = """Ets el PRESIDENT DEL CONSELL FINANCER de XiquiHouse.
Has escoltat atentament la deliberació dels teus tres consellers (Sèneca la Prudència, Keynes l'Estratègia i Epicur el Benestar).

La teva missió és actuar com a àrbitre neutral i emetre el VEREDICTE FINAL per a la família.

Estructura la teva resposta obligatòriament en aquests 4 punts en català:

1. 🤝 **Punts de Consens**: On coincideixen els consellers? Què és evident i inqüestionable?
2. ⚡ **Tensions i Riscos Clau**: Quin és el gran dilema detectat (ex: prudència vs comoditat, risc vs oportunitat)?
3. ⚖️ **Veredicte i Recomanació Recomanada**: Quina és la millor decisió equilibrada per a XiquiHouse tenint en compte les seves dades reals?
4. 📋 **Full de Ruta (Passos concrets)**: 2 o 3 accions pràctiques i immediates per executar la decisió sense sobresalts."""


def construir_resum_dades(df_desp, df_ing, df_cartera, any_analitzar: Optional[int] = None) -> str:
    """Condensa les dades financeres clau per enviar el context als consellers sense saturar tokens."""
    try:
        import pandas as pd
        any_actual = any_analitzar or 2026
        
        # Filtre any
        desp_any = df_desp[df_desp["any"] == any_actual] if "any" in df_desp.columns else df_desp
        ing_any = df_ing[df_ing["any"] == any_actual] if "any" in df_ing.columns else df_ing
        
        tot_desp = desp_any["Import"].sum() if "Import" in desp_any.columns else 0.0
        tot_ing = ing_any["Import"].sum() if "Import" in ing_any.columns else 0.0
        balanc_any = tot_ing - tot_desp
        
        # Top 3 categories despesa
        top_cat = ""
        if "Categoria" in desp_any.columns and "Import" in desp_any.columns:
            gr = desp_any.groupby("Categoria")["Import"].sum().sort_values(ascending=False).head(4)
            top_cat = ", ".join([f"{c}: {v:.0f}€" for c, v in gr.items()])
            
        # Cartera / fons
        tot_cartera = 0.0
        if df_cartera is not None and not df_cartera.empty and "saldo" in df_cartera.columns:
            try:
                tot_cartera = pd.to_numeric(df_cartera["saldo"], errors="coerce").sum()
            except Exception:
                tot_cartera = 0.0

        resum = (
            f"- Any d'anàlisi: {any_actual}\n"
            f"- Total Ingressos de l'any: {tot_ing:,.2f} €\n"
            f"- Total Despeses de l'any: {tot_desp:,.2f} €\n"
            f"- Saldo acumulat de l'any: {balanc_any:,.2f} €\n"
            f"- Despeses principals: {top_cat}\n"
            f"- Valor total actius/cartera registrat: {tot_cartera:,.2f} €\n"
        )
        return resum
    except Exception as e:
        return f"- Context financer resumit no disponible ({e})"


def _consultar_membre(prompt_sistema: str, consulta: str, context_financier: str, api_key: str, model_name: str, provider: str) -> str:
    """Executa la consulta per a un membre individual del consell."""
    prompt_complet = (
        f"{prompt_sistema}\n\n"
        f"--- CONTEXT FINANCER DE XIQUIHOUSE ---\n{context_financier}\n\n"
        f"--- CONSULTA DE LA FAMÍLIA ---\n{consulta}\n\n"
        f"Emet el teu judici raonat:"
    )
    ok, resp, _ = call_llm_api(prompt_complet, api_key=api_key, model_name=model_name, provider=provider)
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
    model_name: str = "gemini-2.5-flash",
    provider: str = "gemini"
) -> Dict[str, Any]:
    """
    Executa la deliberació completa del Consell d'Ancians:
    1. Crida en paral·lel a Sèneca, Keynes i Epicur.
    2. Recull les 3 opinions.
    3. Convoca el President per emetre el veredicte final ponderat.
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
        f"President, sintetitza la deliberació i emet el veredicte final segons l'estructura demanada:"
    )
    
    ok_p, veredicte_text, _ = call_llm_api(
        f"{PROMPT_PRESIDENT}\n\n{deliberacio_conjunta}",
        api_key=api_key,
        model_name=model_name,
        provider=provider
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
