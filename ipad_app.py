import os
import json
import random
import toml
from datetime import datetime
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "dashboard_ipad_secret_key_2026"

INITIAL_BALANCES = {
    'BBVA': -2157.00,
    'La Caixa': 102.28,
    'TRADE REPUB.': 0.0,
    'Casa': 267.28,
    'Tg.Moneder': 0.0,
    'CORTEINGLÉS': 1566.69,
    'Pago VISA': -2995.45
}

BANK_MAPPING = {
    'BBVA': 'BBVA',
    'LaCaixa': 'La Caixa',
    'La Caixa': 'La Caixa',
    'LA CAIXA': 'La Caixa',
    'TR Cartera': 'TR Cartera',
    'TradeRep.': 'TRADE REPUB.',
    'Trade Repub.': 'TRADE REPUB.',
    'TRADE REPUB.': 'TRADE REPUB.',
    'Casa': 'Casa',
    'CASA': 'Casa',
    'Efectiu': 'Casa',
    'T.Moneder': 'Tg.Moneder',
    'Tg.Moneder': 'Tg.Moneder',
    'T.CorteInglés': 'CORTEINGLÉS',
    't.CorteInglés': 'CORTEINGLÉS',
    'Pago VISA': 'Pago VISA'
}

CATALAN_MONTHS = [
    'gener', 'febrer', 'març', 'abril', 'maig', 'juny',
    'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre'
]

def get_db_connection():
    conn_str = None
    if os.path.exists(".streamlit/secrets.toml"):
        try:
            sec = toml.load(".streamlit/secrets.toml")
            conn_str = sec.get("connection_string")
        except Exception:
            pass
    if not conn_str:
        raw_env = os.environ.get("DATABASE_URL") or os.environ.get("connection_string")
        if raw_env:
            import re
            m = re.search(r'(postgresql://[^\s"\']+)', raw_env)
            if m:
                conn_str = m.group(1).strip()
            else:
                conn_str = raw_env.strip()
    if not conn_str:
        raise ValueError("No s'ha trobat la cadena de connexió a la base de dades.")
    return psycopg2.connect(conn_str)

def get_total_recipes_count():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM "tb_receptes_pro";')
        cnt = cur.fetchone()[0]
        conn.close()
        return cnt
    except Exception:
        return 0

# ----------------------------------------------------
# 1. LLIBRE DE RECEPTES (PÀGINA PRINCIPAL)
# ----------------------------------------------------
@app.route("/")
def receptes():
    query = request.args.get("q", "").strip()
    sel_cat = request.args.get("cat", "").strip()
    sel_apat = request.args.get("apat", "").strip()

    receptes_list = []
    categories = ["Primer", "Segon", "Plat únic", "Postre", "Complement", "Guarnició", "Salsa"]
    apats = ["Dinar", "Sopar", "Dinar/Sopar", "Esmorzar"]

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        sql = 'SELECT * FROM "tb_receptes_pro" WHERE 1=1'
        params = []

        if query:
            sql += ' AND (LOWER("titol") LIKE %s OR LOWER("ingredients") LIKE %s)'
            params.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
        if sel_cat:
            sql += ' AND "categoria" = %s'
            params.append(sel_cat)
        if sel_apat:
            sql += ' AND ("apat" = %s OR "apat" = \'Dinar/Sopar\')'
            params.append(sel_apat)

        sql += ' ORDER BY "titol" ASC;'
        cur.execute(sql, params)
        receptes_list = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error carregant receptes: {e}")

    total_cnt = get_total_recipes_count()

    return render_template(
        "ipad/receptes.html",
        active_page="receptes",
        receptes=receptes_list,
        query=query,
        sel_cat=sel_cat,
        sel_apat=sel_apat,
        categories=categories,
        apats=apats,
        total_recipes=total_cnt
    )

# ----------------------------------------------------
# 2. DETALL DE RECEPTA (MODE CUINA)
# ----------------------------------------------------
@app.route("/recepta/<int:recipe_id>")
def recepta_detall(recipe_id):
    recipe = None
    ingredients_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM "tb_receptes_pro" WHERE "id" = %s;', (recipe_id,))
        recipe = cur.fetchone()
        conn.close()

        if recipe and recipe.get("ingredients"):
            raw_ing = recipe["ingredients"]
            for line in raw_ing.split("\n"):
                line_clean = line.strip()
                if line_clean.startswith("-") or line_clean.startswith("*"):
                    line_clean = line_clean[1:].strip()
                if line_clean:
                    ingredients_list.append(line_clean)
    except Exception as e:
        print(f"Error recepta: {e}")

    if not recipe:
        flash("No s'ha trobat la recepta.")
        return redirect(url_for("receptes"))

    total_cnt = get_total_recipes_count()

    return render_template(
        "ipad/recepta_detall.html",
        active_page="receptes",
        r=recipe,
        ingredients_list=ingredients_list,
        total_recipes=total_cnt
    )

# ----------------------------------------------------
# 3. PREVISIÓ / GENERADOR DE MENÚS SETMANALS
# ----------------------------------------------------
@app.route("/menu", methods=["GET", "POST"])
def menu():
    menu_plan = []
    total_cnt = get_total_recipes_count()
    
    if request.method == "POST":
        sel_temp = request.form.get("temporada", "Tot l'any")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute('SELECT * FROM "tb_receptes_pro";')
            all_recipes = cur.fetchall()
            conn.close()

            # Pools per categoria i apat
            pool_dinar_1 = [r for r in all_recipes if r.get('categoria') == 'Primer' and (r.get('apat') in ['Dinar', 'Dinar/Sopar', None])]
            pool_dinar_2 = [r for r in all_recipes if r.get('categoria') in ['Segon', 'Plat únic'] and (r.get('apat') in ['Dinar', 'Dinar/Sopar', None])]
            pool_postres = [r for r in all_recipes if r.get('categoria') == 'Postre']
            pool_sopar = [r for r in all_recipes if r.get('apat') in ['Sopar', 'Dinar/Sopar', None]]

            random.shuffle(pool_dinar_1)
            random.shuffle(pool_dinar_2)
            random.shuffle(pool_postres)
            random.shuffle(pool_sopar)

            for i in range(7):
                d1 = pool_dinar_1[i % len(pool_dinar_1)] if pool_dinar_1 else None
                d2 = pool_dinar_2[i % len(pool_dinar_2)] if pool_dinar_2 else None
                dp = pool_postres[i % len(pool_postres)] if pool_postres else None
                sp = pool_sopar[i % len(pool_sopar)] if pool_sopar else None

                menu_plan.append({
                    "dinar_1": d1,
                    "dinar_2": d2,
                    "dinar_postre": dp,
                    "sopar": sp
                })
        except Exception as e:
            print(f"Error generant menu: {e}")

    return render_template(
        "ipad/menu.html",
        active_page="menu",
        menu_plan=menu_plan,
        total_recipes=total_cnt
    )

# ----------------------------------------------------
# 4. LLISTA DE LA COMPRA
# ----------------------------------------------------
@app.route("/llista", methods=["GET"])
def llista():
    items_list = []
    total_cnt = get_total_recipes_count()
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Select items where stock_actual <= stock_minim or all products
        cur.execute('SELECT * FROM "tb_productes" ORDER BY "nom_estandard" ASC LIMIT 50;')
        items_list = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error llista: {e}")

    return render_template("ipad/llista.html", active_page="llista", items_list=items_list, total_recipes=total_cnt)

@app.route("/llista/afegir", methods=["POST"])
def llista_afegir():
    article = request.form.get("article", "").strip()
    super_habitual = request.form.get("super", "General").strip()

    if article:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT COALESCE(MAX("idProducte"), 0) FROM "tb_productes";')
            next_id = cur.fetchone()[0] + 1

            cur.execute(
                """
                INSERT INTO "tb_productes" ("idProducte", "nom_estandard", "familia", "unitat", "stock_actual", "stock_minim", "super_habitual")
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (next_id, article, "General", "unitat", 0, 1, super_habitual)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error afegint article: {e}")

    return redirect(url_for("llista"))

# ----------------------------------------------------
# 5. AFEGIR NOVA RECEPTA
# ----------------------------------------------------
@app.route("/receptes/nova", methods=["GET", "POST"])
def recepta_nova():
    total_cnt = get_total_recipes_count()
    error_msg = None
    success_msg = None

    if request.method == "POST":
        titol = request.form.get("titol", "").strip()
        categoria = request.form.get("categoria", "Primer")
        apat = request.form.get("apat", "Dinar")
        temps = int(request.form.get("temps") or 30)
        dificultat = request.form.get("dificultat", "Fàcil")
        imatge_url = request.form.get("imatge_url", "").strip() or None
        ingredients = request.form.get("ingredients", "").strip()
        mise_en_place = request.form.get("mise_en_place", "").strip()
        instruccions = request.form.get("instruccions", "").strip()

        if not titol:
            error_msg = "⚠️ El títol de la recepta és obligatori."
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO "tb_receptes_pro" ("titol", "categoria", "temps_prep_minuts", "dificultat", "apat", "ingredients", "mise_en_place", "instruccions", "imatge_url", "temporada", "puntuacio_salut")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (titol, categoria, temps, dificultat, apat, ingredients, mise_en_place, instruccions, imatge_url, "Tot l'any", 7)
                )
                conn.commit()
                conn.close()
                success_msg = f"✅ Recepta '{titol}' guardada correctament a Supabase!"
            except Exception as e:
                error_msg = f"❌ Error guardant la recepta: {e}"

    return render_template(
        "ipad/recepta_nova.html",
        active_page="nova_recepta",
        error_msg=error_msg,
        success_msg=success_msg,
        total_recipes=total_cnt
    )

# ----------------------------------------------------
# 6. RESUM FINANCES / DESPESES (INTEGRAT)
# ----------------------------------------------------
@app.route("/despeses")
def despeses():
    total_cnt = get_total_recipes_count()
    now = datetime.now()
    mes_idx = now.month - 1
    mes_actual_nom = CATALAN_MONTHS[mes_idx]
    any_actual = now.year

    balances = {k: float(v) for k, v in INITIAL_BALANCES.items()}
    moviments = []
    total_ing_mes = 0.0
    total_desp_mes = 0.0

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute('SELECT * FROM "despeses" ORDER BY "ID_mov" DESC LIMIT 15;')
        moviments = cur.fetchall()

        cur.execute(
            'SELECT "import ingrés", "Import càrrec" FROM "despeses" WHERE "any" = %s AND (LOWER("mes") = %s OR LOWER("mes") = %s);',
            (any_actual, mes_actual_nom.lower(), mes_actual_nom[:3].lower())
        )
        for r in cur.fetchall():
            total_ing_mes += float(r.get('import ingrés') or 0.0)
            total_desp_mes += float(r.get('Import càrrec') or 0.0)

        cur.execute('SELECT "Banc", "FormaPago", "import ingrés", "Import càrrec", "Idcategoria", "Idconcepte" FROM "despeses";')
        all_desp = cur.fetchall()

        visa_charges = 0.0
        visa_refunds = 0.0
        visa_settlements = 0.0

        for r in all_desp:
            banc_raw = str(r.get('Banc') or '').strip()
            forma_pago = str(r.get('FormaPago') or '').strip()
            cat = str(r.get('Idcategoria') or '').strip().lower()
            concepte = str(r.get('Idconcepte') or '').strip()
            ing = float(r.get('import ingrés') or 0.0)
            carg = float(r.get('Import càrrec') or 0.0)

            disp_banc = BANK_MAPPING.get(banc_raw)

            if forma_pago == 'VISA':
                if cat == 'op_banc' and 'pago visa' in concepte.lower():
                    visa_settlements += (carg + ing)
                else:
                    visa_charges += carg
                    visa_refunds += ing
            else:
                if disp_banc and disp_banc in balances:
                    balances[disp_banc] += (ing - carg)

        balances['Pago VISA'] = INITIAL_BALANCES.get('Pago VISA', 0.0) + visa_settlements + visa_refunds - visa_charges

        for k in balances:
            if abs(balances[k]) < 0.05:
                balances[k] = 0.0

        conn.close()
    except Exception as e:
        print(f"Error despeses: {e}")

    total_balance = sum(v for k, v in balances.items() if k != 'Pago VISA') + balances.get('Pago VISA', 0.0)
    estalvi_net_mes = total_ing_mes - total_desp_mes

    return render_template(
        "ipad/resum.html",
        active_page="despeses",
        balances=balances,
        total_balance=total_balance,
        mes_actual_nom=mes_actual_nom.capitalize(),
        any_actual=any_actual,
        total_ing_mes=total_ing_mes,
        total_desp_mes=total_desp_mes,
        estalvi_net_mes=estalvi_net_mes,
        moviments=moviments,
        total_recipes=total_cnt
    )

# ----------------------------------------------------
# 7. NOU MOVIMENT REAL
# ----------------------------------------------------
@app.route("/nou", methods=["GET", "POST"])
def nou_moviment():
    total_cnt = get_total_recipes_count()
    categories_list = []
    cat_concept_map = {}
    if os.path.exists("categories_conceptes.json"):
        try:
            with open("categories_conceptes.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k not in ["families_compres", "articles_compres", "bancs", "formes_pago", "supers_tickets"]:
                        categories_list.append(k)
                        cat_concept_map[k] = v if isinstance(v, list) else []
        except Exception:
            pass
    categories_list = sorted(list(set(categories_list)))
    bancs_list = ["BBVA", "LaCaixa", "TradeRep.", "Efectiu", "T.Moneder", "T.CorteInglés", "Pago VISA"]

    error_msg = None
    success_msg = None

    if request.method == "POST":
        data_str = request.form.get("data")
        banc = request.form.get("banc")
        forma_pago = request.form.get("forma_pago") or "Dèbit"
        grup = request.form.get("grup") or "Càrrec"
        cat = request.form.get("categoria")
        concepte = request.form.get("concepte")
        import_val = float(request.form.get("import_val") or 0.0)
        comentari = request.form.get("comentari", "").strip()

        gas_cotxe = request.form.get("gas_cotxe") or "tívoli"
        gas_preu_l = float(request.form.get("gas_preu_l") or 0.0)

        if not banc or not cat or not concepte or import_val <= 0:
            error_msg = "⚠️ Tots els camps obligatoris han d'estar omplerts."
        elif "gasolina" in cat.lower() and gas_preu_l <= 0:
            error_msg = "⚠️ Heu d'introduir un preu per litre vàlid per a la gasolina."
        else:
            try:
                dt = datetime.strptime(data_str, "%Y-%m-%d")
                data_formatted = dt.strftime("%d/%m/%Y")
                mes_str = CATALAN_MONTHS[dt.month - 1]
                any_int = dt.year

                import_carg = import_val if grup == "Càrrec" else 0.0
                import_ing = import_val if grup == "Ingrés" else 0.0
                if grup == "op_banc":
                    import_carg = import_val

                conn = get_db_connection()
                cur = conn.cursor()

                cur.execute('SELECT COALESCE(MAX("ID_mov"), 0) FROM "despeses";')
                next_id_mov = cur.fetchone()[0] + 1

                cur.execute(
                    """
                    INSERT INTO "despeses" ("ID_mov", "Banc", "FormaPago", "Data", "mes", "any", "import ingrés", "Import càrrec", "grup", "Idcategoria", "Idconcepte", "Comentari", "ticketPendent")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (next_id_mov, banc, forma_pago, data_formatted, mes_str, any_int, import_ing, import_carg, grup, cat, concepte, comentari, False)
                )

                if "gasolina" in cat.lower():
                    cur.execute('SELECT COALESCE(MAX("idGasolina"), 0) FROM "gasolina";')
                    next_id_gas = cur.fetchone()[0] + 1
                    litres_calc = round(import_carg / gas_preu_l, 2) if gas_preu_l > 0 else 0.0

                    cur.execute(
                        """
                        INSERT INTO "gasolina" ("idGasolina", "cotxe", "data", "mes", "any", "import", "euros/litre", "litres", "lloc")
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (next_id_gas, gas_cotxe, data_formatted, mes_str, any_int, import_carg, str(gas_preu_l), litres_calc, concepte)
                    )

                conn.commit()
                conn.close()
                success_msg = f"✅ Moviment de {import_val:.2f} € desat correctament!"
            except Exception as e:
                error_msg = f"❌ Error guardant a la base de dades: {e}"

    default_date = datetime.today().strftime("%Y-%m-%d")

    return render_template(
        "ipad/nou_moviment.html",
        active_page="nou",
        categories_list=categories_list,
        bancs_list=bancs_list,
        cat_concept_json=json.dumps(cat_concept_map),
        default_date=default_date,
        error_msg=error_msg,
        success_msg=success_msg,
        total_recipes=total_cnt
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
