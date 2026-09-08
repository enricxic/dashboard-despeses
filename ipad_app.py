import os
import json
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
        conn_str = os.environ.get("DATABASE_URL") or os.environ.get("connection_string")
    if not conn_str:
        raise ValueError("No s'ha trobat la cadena de connexió a la base de dades.")
    return psycopg2.connect(conn_str)

def load_categories_and_concepts():
    cats = []
    cat_concept_map = {}
    if os.path.exists("categories_conceptes.json"):
        try:
            with open("categories_conceptes.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k not in ["families_compres", "articles_compres", "bancs", "formes_pago", "supers_tickets"]:
                        cats.append(k)
                        cat_concept_map[k] = v if isinstance(v, list) else []
        except Exception:
            pass
    cats = sorted(list(set(cats)))
    return cats, cat_concept_map

@app.route("/")
def index():
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
        
        # 1. Darrers 15 moviments
        cur.execute('SELECT * FROM "despeses" ORDER BY "ID_mov" DESC LIMIT 15;')
        moviments = cur.fetchall()

        # 2. Resum del mes actual
        cur.execute(
            'SELECT "import ingrés", "Import càrrec" FROM "despeses" WHERE "any" = %s AND (LOWER("mes") = %s OR LOWER("mes") = %s);',
            (any_actual, mes_actual_nom.lower(), mes_actual_nom[:3].lower())
        )
        for r in cur.fetchall():
            total_ing_mes += float(r.get('import ingrés') or 0.0)
            total_desp_mes += float(r.get('Import càrrec') or 0.0)

        # 3. Càlcul de saldos bancaris totals
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
        print(f"Error carregant dades: {e}")

    total_balance = sum(v for k, v in balances.items() if k != 'Pago VISA') + balances.get('Pago VISA', 0.0)
    estalvi_net_mes = total_ing_mes - total_desp_mes

    return render_template(
        "ipad/resum.html",
        active_page="resum",
        balances=balances,
        total_balance=total_balance,
        mes_actual_nom=mes_actual_nom.capitalize(),
        any_actual=any_actual,
        total_ing_mes=total_ing_mes,
        total_desp_mes=total_desp_mes,
        estalvi_net_mes=estalvi_net_mes,
        moviments=moviments
    )

@app.route("/nou", methods=["GET", "POST"])
def nou_moviment():
    categories_list, cat_concept_map = load_categories_and_concepts()
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

        # Extra gasolina
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

                # Get max ID_mov
                cur.execute('SELECT COALESCE(MAX("ID_mov"), 0) FROM "despeses";')
                next_id_mov = cur.fetchone()[0] + 1

                # Insert despeses
                cur.execute(
                    """
                    INSERT INTO "despeses" ("ID_mov", "Banc", "FormaPago", "Data", "mes", "any", "import ingrés", "Import càrrec", "grup", "Idcategoria", "Idconcepte", "Comentari", "ticketPendent")
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (next_id_mov, banc, forma_pago, data_formatted, mes_str, any_int, import_ing, import_carg, grup, cat, concepte, comentari, False)
                )

                # If gasolina, insert into gasolina table too
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
        success_msg=success_msg
    )

@app.route("/gasolina")
def gasolina():
    gasolina_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM "gasolina" ORDER BY "idGasolina" DESC LIMIT 30;')
        for r in cur.fetchall():
            preu_raw = r.get("euros/litre")
            try:
                preu_f = float(str(preu_raw).replace(",", ".")) if preu_raw is not None else 0.0
            except:
                preu_f = 0.0
            r["euros/litre"] = preu_f
            gasolina_list.append(r)
        conn.close()
    except Exception as e:
        print(f"Error gasolina: {e}")

    return render_template("ipad/gasolina.html", active_page="gasolina", gasolina_list=gasolina_list)

@app.route("/km", methods=["GET", "POST"])
def km():
    msg = None
    last_km = 0
    rutes_list = []

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if request.method == "POST":
            data_str = request.form.get("data")
            contador_val = int(request.form.get("contador") or 0)
            ruta_val = request.form.get("ruta", "").strip()

            dt = datetime.strptime(data_str, "%Y-%m-%d")
            data_formatted = dt.strftime("%d/%m/%Y")

            cur.execute('SELECT COALESCE(MAX("contador"), 0) FROM "kmCotxe";')
            prev_km = cur.fetchone()['coalesce']
            km_trajecte = max(0, contador_val - prev_km)

            cur.execute('SELECT COALESCE(MAX("idRuta"), 0) FROM "kmCotxe";')
            next_id = cur.fetchone()['coalesce'] + 1

            cur.execute(
                """
                INSERT INTO "kmCotxe" ("idRuta", "cotxe", "data", "ruta", "contador", "km")
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (next_id, "tívoli", data_formatted, ruta_val, contador_val, km_trajecte)
            )
            conn.commit()
            msg = f"✅ Lectura de {contador_val} km (+{km_trajecte} km) desada correctament!"

        cur.execute('SELECT COALESCE(MAX("contador"), 0) FROM "kmCotxe";')
        last_km = int(cur.fetchone()['coalesce'])

        cur.execute('SELECT * FROM "kmCotxe" ORDER BY "idRuta" DESC LIMIT 25;')
        rutes_list = cur.fetchall()

        conn.close()
    except Exception as e:
        print(f"Error km: {e}")

    default_date = datetime.today().strftime("%Y-%m-%d")
    return render_template("ipad/km.html", active_page="km", last_km=last_km, rutes_list=rutes_list, default_date=default_date, msg=msg)

@app.route("/llista", methods=["GET"])
def llista():
    items_list = []
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM "tb_productes" LIMIT 40;')
        items_list = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"Error llista: {e}")
    return render_template("ipad/llista.html", active_page="llista", items_list=items_list)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
