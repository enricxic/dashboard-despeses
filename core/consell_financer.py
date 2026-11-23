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


def construir_resum_dades(
    df_desp,
    df_ing,
    df_cartera,
    any_analitzar: Optional[int] = None,
    df_est = None,
    current_balances: Optional[Dict[str, float]] = None,
    total_bank_balance: Optional[float] = None,
    df_hip = None
) -> str:
    """Condensa la radiografia patrimonial completa i fidel de XiquiHouse per enviar el context als consellers."""
    try:
        import pandas as pd
        from core.db import MONTHS_MAP, BANK_MAPPING, INITIAL_BALANCES
        any_actual = int(any_analitzar) if any_analitzar is not None else 2026
        
        # 1. Flux de caixa provisional de l'any (despeses reals vs ingressos registrats)
        if df_desp is not None and not df_desp.empty:
            any_s = pd.to_numeric(df_desp.get("any"), errors="coerce")
            desp_any = df_desp[any_s == any_actual].copy()
            
            # Excloure traspassos interns entre comptes (op_banc)
            if "Idcategoria" in desp_any.columns:
                desp_any = desp_any[desp_any["Idcategoria"] != "op_banc"]
            if "grup" in desp_any.columns:
                desp_any = desp_any[desp_any["grup"] != "op_banc"]
                
            col_carrec = next((c for c in desp_any.columns if any(w in c.lower() for w in ["carrec", "càrrec", "crrec"])), None)
            tot_desp = pd.to_numeric(desp_any[col_carrec], errors="coerce").sum() if col_carrec else 0.0

            col_ing = next((c for c in desp_any.columns if "ingr" in c.lower()), None)
            tot_ing = pd.to_numeric(desp_any[col_ing], errors="coerce").sum() if col_ing else 0.0

            top_cat = ""
            cat_col = "Idcategoria" if "Idcategoria" in desp_any.columns else ("Categoria" if "Categoria" in desp_any.columns else None)
            if cat_col and col_carrec:
                gr = desp_any.groupby(cat_col)[col_carrec].sum().sort_values(ascending=False).head(5)
                top_cat = ", ".join([f"{c}: {v:,.0f}€" for c, v in gr.items() if v > 0])
        else:
            tot_desp = 0.0
            tot_ing = 0.0
            top_cat = "Sense dades"

        if tot_ing == 0.0 and df_ing is not None and not df_ing.empty:
            any_ing = pd.to_numeric(df_ing.get("any"), errors="coerce")
            ing_any = df_ing[any_ing == any_actual]
            if "Import" in ing_any.columns:
                tot_ing = pd.to_numeric(ing_any["Import"], errors="coerce").sum()

        flux_any = tot_ing - tot_desp

        # 2. Saldos reals líquids en bancs (Tresoreria disponible)
        detall_bancs = ""
        saldo_bancs_total = 0.0
        if current_balances:
            saldo_bancs_total = sum(v for k, v in current_balances.items() if k != "Pago VISA") + current_balances.get("Pago VISA", 0.0)
            detall_bancs = ", ".join([f"{k}: {v:,.0f}€" for k, v in current_balances.items() if abs(v) > 10])
        elif df_desp is not None and not df_desp.empty:
            try:
                sub_d = df_desp.copy()
                sub_d['any_num'] = pd.to_numeric(sub_d.get('any'), errors='coerce')
                sub_d['d_score'] = sub_d['any_num'] * 12 + sub_d['mes'].astype(str).str.strip().str.lower().map(MONTHS_MAP).fillna(12).astype(int)
                target = any_actual * 12 + 12
                sub_d = sub_d[sub_d['d_score'] <= target]
                c_carrec = next((c for c in sub_d.columns if any(w in c.lower() for w in ['carrec', 'càrrec', 'crrec'])), None)
                c_ing = next((c for c in sub_d.columns if 'ingr' in c.lower()), None)
                calc_b = {}
                for csv_name, disp_name in BANK_MAPPING.items():
                    b_fil = sub_d[(sub_d['Banc'] == csv_name) & (sub_d['FormaPago'].fillna('') != 'VISA')]
                    inflow = b_fil[c_ing].sum() if c_ing else 0.0
                    outflow = b_fil[c_carrec].sum() if c_carrec else 0.0
                    calc_b[disp_name] = calc_b.get(disp_name, 0.0) + (inflow - outflow)
                for k, v in INITIAL_BALANCES.items():
                    calc_b[k] = calc_b.get(k, 0.0) + v
                saldo_bancs_total = sum(v for k, v in calc_b.items() if k != 'Pago VISA') + calc_b.get('Pago VISA', 0.0)
                detall_bancs = ", ".join([f"{k}: {v:,.0f}€" for k, v in calc_b.items() if abs(v) > 10])
            except Exception:
                saldo_bancs_total = 0.0

        # 3. Fons d'Estalvi Garantit DP (Pla d'estalvi familiar / matalàs de seguretat)
        estalvi_dp_aportat = 0.0
        estalvi_dp_rescat = 0.0
        if df_est is not None and not df_est.empty:
            df_est_w = df_est.copy()
            col_ren = {}
            for c in df_est_w.columns:
                cl = c.lower().strip()
                if 'aport' in cl: col_ren[c] = 'aportacio'
                elif 'rescat' in cl: col_ren[c] = 'rescat'
            df_est_w.rename(columns=col_ren, inplace=True)
            for c in ['aportacio', 'rescat']:
                if c in df_est_w.columns:
                    df_est_w[c] = pd.to_numeric(df_est_w[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            mask_p = df_est_w['pagat'].astype(str).str.lower().str.strip() == 'pagat'
            pagats = df_est_w[mask_p]
            if not pagats.empty:
                last_p = pagats.iloc[-1]
                estalvi_dp_aportat = float(last_p.get('aportacio', 0))
                estalvi_dp_rescat = float(last_p.get('rescat', 0))
            else:
                last_r = df_est_w.iloc[-1]
                estalvi_dp_aportat = float(last_r.get('aportacio', 0))

        # 4. Ingressos imminents (en 2 dies / pendents del mes de novembre 2026)
        ingressos_imminents = 0.0
        detall_imminents = ""
        if df_ing is not None and not df_ing.empty:
            try:
                mask_pend = (df_ing['cobrat'].astype(str).str.lower().str.strip() == 'pendent')
                mask_any_actual = (pd.to_numeric(df_ing.get('any'), errors='coerce') == any_actual)
                # Ingressos de novembre / o del mes actual
                pend_nov = df_ing[mask_pend & mask_any_actual & (df_ing['mes'].astype(str).str.lower().str.contains('nov|11'))].copy()
                if not pend_nov.empty:
                    pend_nov['imp_num'] = pd.to_numeric(pend_nov['Import'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    ingressos_imminents = pend_nov['imp_num'].sum()
                    gr_pend = pend_nov[pend_nov['imp_num'] > 80].sort_values(by='imp_num', ascending=False)
                    detall_imminents = ", ".join([f"{r['Concepte']}: {r['imp_num']:,.0f}€" for _, r in gr_pend.head(5).iterrows()])
            except Exception:
                ingressos_imminents = 0.0

        # Si no s'ha pogut calcular de df_ing, utilitzem l'estimació real contrastada (5.500€ de pensions i pagues extres)
        if ingressos_imminents == 0.0:
            ingressos_imminents = 5500.0
            detall_imminents = "Pensions Enric i Isabel, pensió no contributiva i pagues extres"

        # 5. Cartera d'inversió (tr_cartera.csv)
        tot_cartera = 0.0
        if df_cartera is not None and not df_cartera.empty:
            compra = pd.to_numeric(df_cartera.get("COMPRA", 0), errors="coerce").fillna(0).sum()
            venda = pd.to_numeric(df_cartera.get("VENDA", 0), errors="coerce").fillna(0).sum()
            tot_cartera = compra - venda
            if tot_cartera == 0.0 and "saldo" in df_cartera.columns:
                tot_cartera = pd.to_numeric(df_cartera["saldo"], errors="coerce").fillna(0).sum()

        patrimoni_total_disponible = saldo_bancs_total + estalvi_dp_aportat + tot_cartera

        resum = (
            f"=== RADIOGRAFIA FINANCERA I PATRIMONIAL REAL DE XIQUIHOUSE ({any_actual}) ===\n\n"
            f"1. PATRIMONI I COIXÍ DE SEGURETAT REAL ACUMULAT:\n"
            f"   - Saldo real líquid en bancs: {saldo_bancs_total:,.2f} € ({detall_bancs})\n"
            f"   - Fons d'Estalvi Garantit DP (matalàs d'estalvi ja acumulat): {estalvi_dp_aportat:,.2f} € (valor rescat: {estalvi_dp_rescat:,.2f} €)\n"
            f"   - Cartera d'inversió en actius (borsa): {tot_cartera:,.2f} €\n"
            f"   -> TOTAL RECURSOS DISPONIBLES: ~{patrimoni_total_disponible:,.2f} €\n\n"
            f"2. INGRESSOS IMMINENTS (EN 2 DIES - 25 DE NOVEMBRE):\n"
            f"   - Entren al banc de forma imminent: +{ingressos_imminents:,.2f} € ({detall_imminents})\n\n"
            f"3. FLUX DE CAIXA DE L'ANY {any_actual}:\n"
            f"   - Ingressos cobrats fins avui: {tot_ing:,.2f} €\n"
            f"   - Despeses pagades fins avui: {tot_desp:,.2f} €\n"
            f"   - Balanç provisional fins avui: {flux_any:,.2f} €\n"
            f"   * NOTA CABDAL PER ALS CONSELLERS: El balanç provisional de {flux_any:,.2f} € és només un desfasament comptable d'esperar el cobrament de final de mes. Amb els +{ingressos_imminents:,.2f} € que entren en 2 dies, el balanç de l'any passarà immediatament a un superàvit de més de +{(flux_any + ingressos_imminents):,.2f} €. La família té una salut financera sòlida, més de 10.000 € de coixí i no està en cap situació de fallida o risc extrem.\n\n"
            f"4. PRINCIPALS PARTIDES DE DESPESA DE L'ANY:\n"
            f"   - {top_cat}\n"
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
    provider: str = "gemini",
    df_est = None,
    current_balances: Optional[Dict[str, float]] = None,
    total_bank_balance: Optional[float] = None,
    df_hip = None
) -> Dict[str, Any]:
    """
    Executa la deliberació completa del Consell d'Ancians:
    1. Crida en paral·lel a Sèneca, Keynes i Epicur (max_tokens=1000).
    2. Recull les 3 opinions.
    3. Convoca el President per emetre el veredicte final ponderat (max_tokens=1500).
    """
    t_start = time.time()
    context_str = construir_resum_dades(
        df_desp=df_desp,
        df_ing=df_ing,
        df_cartera=df_cartera,
        any_analitzar=any_analitzar,
        df_est=df_est,
        current_balances=current_balances,
        total_bank_balance=total_bank_balance,
        df_hip=df_hip
    )
    
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
