import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from core.db import (
    get_supabase_client, fetch_all_supabase, parse_excel_date, clean_numeric,
    get_config_routes, add_route_to_config, init_routes_config, append_to_db,
    save_to_csv, load_dashboard_data, get_csv_mtimes
)

def render():
    # Hide header anchors
    st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    a[data-testid="stHeaderActionLink"] {
        display: none !important;
    }
    .stHeading a, h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    from modules.avatar_widget import render_header_with_avatar
    render_header_with_avatar("<div style='font-size: 1.8rem; font-weight: bold; color:#f39c12; margin-top:0;'>🚗 Cotxe</div>", "cotxe")

    st.write("---")

    supabase = get_supabase_client(st.session_state.get("role", "guest"))
    
    # Ensure data is loaded
    from core.db import ensure_session_dfs
    ensure_session_dfs()

    df_km = st.session_state.get("df_km", pd.DataFrame())
    df_gas = st.session_state.get("df_gas", pd.DataFrame())

    tabs_list = ["🛣️ Km i Rutes", "⛽ Repostatge", "🔧 Manteniment (Oli i Rodes)", "📊 Consum"]
    tab_mapping = {
        "km_rutes": "🛣️ Km i Rutes",
        "km": "🛣️ Km i Rutes",
        "repostatge": "⛽ Repostatge",
        "manteniment": "🔧 Manteniment (Oli i Rodes)",
        "oli_rodes": "🔧 Manteniment (Oli i Rodes)",
        "consum": "📊 Consum"
    }
    tab_param = st.query_params.get("tab")
    default_tab = tab_mapping.get(tab_param)
    if default_tab not in tabs_list:
        default_tab = None

    tab_km, tab_repostatge, tab_oli, tab_consum = st.tabs(tabs_list, default=default_tab, key=f"tabs_cotxe_{tab_param or 'main'}")

    # ----------------------------------------------------
    # TAB 1: REGISTRE DE KM I RUTES
    # ----------------------------------------------------
    with tab_km:
        st.markdown("<h4 style='color:#f39c12;'>➕ Nou Registre de Quilòmetres</h4>", unsafe_allow_html=True)
        
        km_version = st.session_state.get("km_version", 0)
        cotxe_val = "tívoli"
        
        # Last odometer
        last_km = 0.0
        df_km_car = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km
        if not df_km_car.empty:
            df_km_car_sorted = df_km_car.copy()
            df_km_car_sorted['parsed_date'] = df_km_car_sorted['data'].apply(parse_excel_date)
            df_km_car_sorted = df_km_car_sorted.sort_values(by='parsed_date', ascending=False)
            val_last = df_km_car_sorted.dropna(subset=['contador'])['contador']
            if not val_last.empty:
                last_km = float(val_last.iloc[0])
            max_cont = pd.to_numeric(df_km_car['contador'], errors='coerce').max()
            if pd.notna(max_cont) and float(max_cont) > last_km:
                last_km = float(max_cont)

        # --- Lectura per foto del comptaquilòmetres ---
        odo_key = f"km_odo_{km_version}"
        with st.expander("📸 Llegir km amb una foto del comptaquilòmetres", expanded=False):
            st.caption("Al mòbil, toca el botó i tria **Càmera** per fer la foto directament.")
            foto = st.file_uploader("Foto del quadre", type=["jpg", "jpeg", "png", "webp", "heic"], key=f"km_foto_{km_version}", label_visibility="collapsed")
            if foto is not None:
                st.image(foto, width=220)
                if st.button("🔍 Llegir quilòmetres", key=f"km_ocr_btn_{km_version}", type="primary"):
                    try:
                        import io, json, re
                        from PIL import Image, ImageOps
                        img = ImageOps.exif_transpose(Image.open(foto)).convert("RGB")
                        img.thumbnail((1600, 1600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=85)
                        from core.llm import call_llm_api
                        prompt = (
                            "Aquesta és una foto del quadre d'instruments d'un cotxe. Llegeix el valor del "
                            "COMPTAQUILÒMETRES TOTAL (odòmetre, normalment un número de 5-6 xifres seguit de 'km'). "
                            "Ignora rpm, velocitat, hora, temperatura, pressió de pneumàtics i parcials (TRIP). "
                            f"Com a referència, l'última lectura registrada és {int(last_km)} km, i el valor hauria de ser igual o una mica superior. "
                            "Respon NOMÉS amb JSON: {\"km\": <enter>, \"confianca\": \"alta|mitjana|baixa\"}"
                        )
                        with st.spinner("Llegint el comptaquilòmetres..."):
                            ok, resp, _ = call_llm_api(prompt, st.secrets["GEMINI_API_KEY"], json_mode=True, image_bytes=buf.getvalue())
                        if not ok:
                            st.error(f"No s'ha pogut llegir: {resp[:300]}")
                        else:
                            m = re.search(r"\{.*\}", resp, re.S)
                            data_ocr = json.loads(m.group(0) if m else resp)
                            km_llegit = float(data_ocr.get("km"))
                            st.session_state[odo_key] = km_llegit
                            st.session_state["km_ocr_info"] = (km_llegit, data_ocr.get("confianca", ""))
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error llegint la foto: {e}")
            info = st.session_state.get("km_ocr_info")
            if info:
                km_l, conf = info
                if km_l <= last_km:
                    st.warning(f"⚠️ Llegit {int(km_l):,} km, però és igual o inferior a l'última lectura registrada ({int(last_km):,} km). Revisa-ho.")
                else:
                    st.success(f"✅ Llegit: **{int(km_l):,} km** (confiança {conf}). S'ha omplert la lectura de l'odòmetre; revisa-la abans de desar.")

        r1_col1, r1_col2, r1_col3 = st.columns([2, 4, 4])
        with r1_col1:
            data_val = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key=f"km_data_{km_version}")
        with r1_col2:
            placeholder_odo = f"Última: {int(last_km):,}".replace(",", ".") if last_km > 0 else "0"
            contador_val = st.number_input(
                "Lectura Odòmetre (km totals)",
                min_value=0.0,
                value=None,
                placeholder=placeholder_odo,
                step=1.0,
                key=f"km_odo_{km_version}",
                help=f"Ha de ser estrictament superior a l'última quantitat registrada de l'odòmetre ({int(last_km):,} km)"
            )
            if contador_val is not None and contador_val <= last_km:
                st.markdown(
                    f"<div style='color: #ef4444; font-size: 0.8rem; font-weight: 600; margin-top: -8px; margin-bottom: 6px;'>"
                    f"⚠️ Els km han de ser superiors a l'última lectura ({int(last_km):,} km)"
                    f"</div>",
                    unsafe_allow_html=True
                )
        with r1_col3:
            is_valid_odo = (contador_val is not None and contador_val > last_km)
            km_val = (contador_val - last_km) if is_valid_odo else 0.0
            if contador_val is not None and contador_val <= last_km:
                trajecte_label = "0 km (⚠️ Invàlid: ≤ odòmetre)"
            elif contador_val is not None:
                trajecte_label = f"{int(km_val):,} km"
            else:
                trajecte_label = "0 km"
            st.text_input("Kilòmetres del trajecte", value=trajecte_label, disabled=True)

        ruta_opts = get_config_routes(df_km)
        if "Nova ruta..." not in ruta_opts:
            ruta_opts.insert(0, "Nova ruta...")
            
        ruta_sel_key = f"km_ruta_sel_{km_version}"
        current_sel = st.session_state.get(ruta_sel_key, "Nova ruta...")
        
        r2_col1, r2_col2 = st.columns(2)
        with r2_col1:
            ruta_sel = st.selectbox("Ruta / Destinació", ruta_opts, key=ruta_sel_key)
        
        if current_sel == "Nova ruta...":
            with r2_col2:
                ruta_val = st.text_input("Escriu la nova ruta:", key=f"km_ruta_{km_version}")
                save_ruta_template = st.checkbox("💾 Afegir a la llista de rutes", value=True, key=f"km_save_ruta_{km_version}")
        else:
            with r2_col2:
                st.write("")
            ruta_val = ruta_sel

        col_btns = st.columns([2.5, 2.0, 7.5])
        with col_btns[0]:
            submitted = st.button("💾 Desar Kilòmetres", type="primary", use_container_width=True)
        with col_btns[1]:
            cancelled = st.button("Cancel·lar", key=f"cancel_km_{km_version}", use_container_width=True)
            
        if cancelled:
            st.session_state.pop("km_ocr_info", None)
            st.session_state["km_version"] = st.session_state.get("km_version", 0) + 1
            st.rerun()
            
        if submitted:
            if contador_val is None or contador_val <= 0:
                st.error("⚠️ Heu d'introduir una lectura d'odòmetre vàlida.")
            elif contador_val <= last_km:
                st.error(f"⚠️ **Error de validació**: Els kilòmetres entrats ({int(contador_val):,} km) mai poden ser iguals o inferiors a l'última quantitat registrada de l'odòmetre ({int(last_km):,} km). El nou registre ha de ser estrictament superior.")
            elif not ruta_val or not ruta_val.strip():
                st.error("⚠️ Heu d'especificar la ruta.")
            else:
                # Consultem l'ID màxim directament al núvol per esquivar la memòria cau
                max_id = 1
                try:
                    res = supabase.table('kmCotxe').select('idRuta').order('idRuta', desc=True).limit(1).execute()
                    if res.data and len(res.data) > 0:
                        max_id = int(res.data[0]['idRuta']) + 1
                except:
                    max_id = int(df_km['idRuta'].max() + 1) if not df_km.empty and 'idRuta' in df_km.columns else 1

                new_row = {
                    'idRuta': max_id,
                    'cotxe': cotxe_val,
                    'data': data_val.strftime('%d/%m/%Y'),
                    'ruta': ruta_val.strip(),
                    'contador': int(contador_val),
                    'km': int(km_val)
                }
                ok = append_to_db(pd.DataFrame([new_row]), 'kmCotxe', 'df_km')
                if ok:
                    if current_sel == "Nova ruta...":
                        if st.session_state.get(f"km_save_ruta_{km_version}", True):
                            add_route_to_config(ruta_val.strip(), df_km)
                        else:
                            init_routes_config(df_km)
                    st.success("Ruta desada correctament!")
                    st.session_state.pop("km_ocr_info", None)
                    st.session_state["km_version"] = st.session_state.get("km_version", 0) + 1
                    st.rerun()

        st.markdown("<hr style='margin:15px 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#f39c12;'>📋 Històric de Rutes Registrades</h4>", unsafe_allow_html=True)
        if not df_km.empty:
            df_km_show = df_km.copy()
            df_km_show['parsed_date'] = df_km_show['data'].apply(parse_excel_date)
            sort_cols = [c for c in ['parsed_date', 'idRuta'] if c in df_km_show.columns]
            if sort_cols:
                df_km_show = df_km_show.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
            cols_avail = [c for c in ['data', 'cotxe', 'ruta', 'km', 'contador'] if c in df_km_show.columns]
            df_km_show = df_km_show[cols_avail].head(50)
            df_km_show.rename(columns={'data': 'Data', 'cotxe': 'Cotxe', 'ruta': 'Ruta', 'km': 'Km trajecte', 'contador': 'Odòmetre'}, inplace=True)
            st.dataframe(df_km_show, use_container_width=True, hide_index=True)
        else:
            st.info("No hi ha rutes registrades.")

    # ----------------------------------------------------
    # TAB 2: REPOSTATGE (BBDD GASOLINA)
    # ----------------------------------------------------
    with tab_repostatge:
        st.markdown("<h4 style='color:#f39c12;'>⛽ Històric de Repostatges de Gasolina</h4>", unsafe_allow_html=True)
        st.caption("💡 Les dades de proveïment s'alimenten automàticament des del formulari d'Ingressos / Despeses en seleccionar la categoria Gasolina.")
        
        if not df_gas.empty:
            df_gas_work = df_gas.copy()
            df_gas_work['parsed_date'] = df_gas_work['data'].apply(parse_excel_date)
            df_gas_work['import_val'] = clean_numeric(df_gas_work.get('import', 0))
            df_gas_work['litres_val'] = clean_numeric(df_gas_work.get('litres', 0))
            df_gas_work['preu_l_val'] = clean_numeric(df_gas_work.get('euros/litre', df_gas_work.get('€/l', 0)))
            
            # Sort descending by date and idGasolina
            sort_cols = [c for c in ['parsed_date', 'idGasolina'] if c in df_gas_work.columns]
            df_gas_work = df_gas_work.sort_values(by=sort_cols, ascending=[False] * len(sort_cols))
            
            # Metrics: Preu últim repostatge, Preu més alt, Preu més baix
            valid_preus = df_gas_work[df_gas_work['preu_l_val'] > 0.0]
            
            ultim_preu = df_gas_work.iloc[0]['preu_l_val'] if not df_gas_work.empty else 0.0
            max_preu = valid_preus['preu_l_val'].max() if not valid_preus.empty else 0.0
            min_preu = valid_preus['preu_l_val'].min() if not valid_preus.empty else 0.0
            
            c_k1, c_k2, c_k3 = st.columns(3)
            with c_k1:
                st.metric("Preu Últim Repostatge", f"{ultim_preu:.3f} €/l")
            with c_k2:
                st.metric("Preu Més Alt", f"{max_preu:.3f} €/l")
            with c_k3:
                st.metric("Preu Més Baix", f"{min_preu:.3f} €/l")

            st.write("")
            cols_g = [c for c in ['data', 'cotxe', 'lloc', 'import', 'euros/litre', '€/l', 'litres'] if c in df_gas_work.columns]
            df_gas_show = df_gas_work[cols_g].copy()
            df_gas_show.rename(columns={'data': 'Data', 'cotxe': 'Cotxe', 'lloc': 'Benzinera', 'import': 'Import (€)', 'euros/litre': 'Preu/L', '€/l': 'Preu/L', 'litres': 'Litres'}, inplace=True)
            
            st.dataframe(
                df_gas_show.style.format({'Import (€)': '{:,.2f} €', 'Preu/L': '{:.3f} €/l', 'Litres': '{:.2f} l'}, na_rep=""),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hi ha registres de repostatge a la base de dades.")

    # ----------------------------------------------------
    # TAB 3: CANVI D'OLI I MANTENIMENT
    # ----------------------------------------------------
    with tab_oli:
        from core.config_manager import load_app_config, save_app_config, DEFAULT_CONFIG
        import copy

        car_kms_actuals = 0.0
        df_km_oli = df_km[df_km['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km.columns else df_km
        if not df_km_oli.empty and 'contador' in df_km_oli.columns:
            car_kms_actuals = pd.to_numeric(df_km_oli['contador'], errors='coerce').max()
            if pd.isna(car_kms_actuals): car_kms_actuals = 0.0

        from core.config_manager import DEFAULT_PLANIFICACIONS_INFLAT, get_inflat_occurrences
        _DEF_MANT = {
            "oli": {"ultim_canvi_km": 30000, "interval_km": 16000, "data_ultim_canvi": ""},
            "rodes": {"ultim_canvi_km": None, "interval_km": 40000, "previst": {"km": 39600, "quantes": 2, "posicio": "Davanteres", "data": "Nadal 2026"}},
            "inflat_rodes": {
                "propera_data": "22/12/2026",
                "repeticions_any": 2,
                "avis_dies_abans": 15,
                "data_ultim_inflat": "",
                "km_ultim_inflat": None,
                "pressio": "2.4 bar",
                "planificacions": copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
            },
            "control_nivells": {
                "propera_data": "22/12/2026",
                "repeticions_any": 2,
                "avis_dies_abans": 15,
                "data_ultim_control": "",
                "km_ultim_control": None,
                "estat_nivells": "Tots correctes (Oli, refrigerant, parabrises, frens)",
                "planificacions": copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
            },
            "historic": []
        }
        app_cfg = load_app_config()
        mant = copy.deepcopy(app_cfg.get("manteniment_cotxe") or DEFAULT_CONFIG.get("manteniment_cotxe") or _DEF_MANT)
        mant.setdefault("oli", copy.deepcopy(_DEF_MANT["oli"]))
        mant.setdefault("rodes", copy.deepcopy(_DEF_MANT["rodes"]))
        mant.setdefault("inflat_rodes", copy.deepcopy(_DEF_MANT["inflat_rodes"]))
        if "planificacions" not in mant["inflat_rodes"] or not isinstance(mant["inflat_rodes"]["planificacions"], list) or len(mant["inflat_rodes"]["planificacions"]) == 0:
            mant["inflat_rodes"]["planificacions"] = copy.deepcopy(DEFAULT_PLANIFICACIONS_INFLAT)
        if "pressio" not in mant["inflat_rodes"] or not mant["inflat_rodes"]["pressio"]:
            mant["inflat_rodes"]["pressio"] = "2.4 bar"
        mant.setdefault("control_nivells", copy.deepcopy(_DEF_MANT["control_nivells"]))
        if "planificacions" not in mant["control_nivells"] or not isinstance(mant["control_nivells"]["planificacions"], list) or len(mant["control_nivells"]["planificacions"]) == 0:
            mant["control_nivells"]["planificacions"] = copy.deepcopy(_DEF_MANT["control_nivells"]["planificacions"])
        if "estat_nivells" not in mant["control_nivells"] or not mant["control_nivells"]["estat_nivells"]:
            mant["control_nivells"]["estat_nivells"] = "Tots correctes (Oli, refrigerant, parabrises, frens)"
        mant.setdefault("historic", [])
        avis_km = float(mant.get("avis_km", 20000))

        col_hdr, col_toggle = st.columns([3, 1])
        with col_hdr:
            st.markdown("<p style='color:#94a3b8; font-size:0.95rem; margin:0 0 8px 0;'>Revisions d'oli, rodes, inflat, nivells, taller i històric de manteniment del vehicle.</p>", unsafe_allow_html=True)
        with col_toggle:
            expand_all = st.checkbox("Desplegar totes les seccions", value=False, key="expand_all_mant_cotxe")

        with st.expander(f"🔔 Configuració d'avisos (ara: {int(avis_km):,} km abans)", expanded=expand_all):
            a1, a2 = st.columns([3, 1])
            nou_avis = a1.number_input("Avisar quan faltin (km)", min_value=0, value=int(avis_km), step=500)
            a2.write("")
            if a2.button("💾 Desar", key="save_avis"):
                mant["avis_km"] = int(nou_avis)
                cfg_tmp = copy.deepcopy(load_app_config())
                cfg_tmp["manteniment_cotxe"] = mant
                save_app_config(cfg_tmp)
                try:
                    from core.alerts import get_global_alerts
                    get_global_alerts.clear()
                except Exception:
                    pass
                st.rerun()

        def _save_mant(new_mant):
            cfg = copy.deepcopy(load_app_config())
            cfg["manteniment_cotxe"] = new_mant
            save_app_config(cfg)
            try:
                from core.alerts import get_global_alerts
                get_global_alerts.clear()
            except Exception:
                pass

        def _estat(left, interval):
            usat = 1 - (left / interval) if interval else 1
            usat = min(max(usat, 0.0), 1.0)
            st.progress(usat, text=f"Desgast: {usat*100:.0f}%")
            if left <= 0:
                st.error(f"🚨 Canvi superat per {int(abs(left)):,} km!")
            elif left <= avis_km:
                st.warning(f"⚠️ Queden només {int(left):,} km!")
            else:
                st.success(f"✅ Tot correcte. Queden {int(left):,} km.")

        # ---------- OLI ----------
        oli = mant["oli"]
        oli_last = float(oli.get("ultim_canvi_km", 30000))
        oli_int = float(oli.get("interval_km", 16000))
        oli_next = oli_last + oli_int
        oli_left = oli_next - car_kms_actuals
        oli_tag = f" · {int(oli_left):,} km restants" if oli_left > 0 else f" · 🚨 Superat per {int(abs(oli_left)):,} km"

        with st.expander(f"🛢️ Canvi d'Oli{oli_tag}", expanded=expand_all):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kms actuals", f"{int(car_kms_actuals):,}")
            c2.metric("Últim canvi", f"{int(oli_last):,} km", help=oli.get("data_ultim_canvi") or None)
            c3.metric("Proper canvi", f"{int(oli_next):,} km", help=f"{int(oli_last):,} + {int(oli_int):,}")
            c4.metric("Kms restants", f"{int(oli_left):,}")
            _estat(oli_left, oli_int)

            with st.expander("✏️ Registrar canvi d'oli"):
                with st.form("form_oli"):
                    f1, f2, f3 = st.columns(3)
                    n_km = f1.number_input("Km del canvi", min_value=0, value=int(oli_last), step=100)
                    n_int = f2.number_input("Interval (km)", min_value=1000, value=int(oli_int), step=1000)
                    n_data = f3.date_input("Data", value=datetime.today(), format="DD/MM/YYYY")
                    n_nota = st.text_input("Observacions", value="Oli i filtre")
                    afegir_hist = st.checkbox("Afegir a l'històric", value=True)
                    if st.form_submit_button("💾 Desar canvi d'oli", type="primary"):
                        d = n_data.strftime("%d/%m/%Y")
                        mant["oli"] = {"ultim_canvi_km": int(n_km), "interval_km": int(n_int), "data_ultim_canvi": d}
                        if afegir_hist:
                            mant["historic"].append({"data": d, "tipus": "Oli", "km": int(n_km), "rodes": "", "detall": n_nota})
                        _save_mant(mant)
                        st.success(f"Desat! Proper canvi als {int(n_km + n_int):,} km.")
                        st.rerun()

        # ---------- RODES ----------
        rodes = mant["rodes"]
        r_last_raw = rodes.get("ultim_canvi_km")
        r_int = float(rodes.get("interval_km", 40000))
        previst = rodes.get("previst") or {}
        if previst.get("km"):
            r_next = float(previst["km"])
        elif r_last_raw:
            r_next = float(r_last_raw) + r_int
        else:
            r_next = None
        r_left = (r_next - car_kms_actuals) if r_next is not None else None
        rodes_tag = f" · {int(r_left):,} km restants" if r_left is not None else ""

        with st.expander(f"🛞 Canvi de Rodes{rodes_tag}", expanded=expand_all):
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Últim canvi", f"{int(r_last_raw):,} km" if r_last_raw else "Sense registre",
                      help=(f"{rodes.get('quantes_rodes', '')} rodes ({rodes.get('posicio', '')}) - {rodes.get('data_ultim_canvi', '')}" if r_last_raw else None))
            if previst.get("km"):
                d2.metric("Canvi previst", f"{previst.get('quantes', 2)} rodes", help=f"{previst.get('posicio', '')} · {previst.get('data', '')}")
            else:
                d2.metric("Rodes canviades", f"{rodes.get('quantes_rodes', '-')}" if r_last_raw else "-")
            d3.metric("Proper canvi", f"{int(r_next):,} km" if r_next else "-", help=previst.get("data") or None)
            d4.metric("Kms restants", f"{int(r_left):,}" if r_left is not None else "-")
            if r_left is not None:
                if previst.get("km"):
                    if r_left <= 0:
                        st.error(f"🚨 Ja has superat els km previstos per al canvi de rodes ({int(abs(r_left)):,} km).")
                    elif r_left <= avis_km:
                        st.warning(f"⚠️ Queden {int(r_left):,} km per al canvi previst de {previst.get('quantes', 2)} rodes.")
                    else:
                        st.info(f"📅 Previst canviar {previst.get('quantes', 2)} rodes ({previst.get('posicio', '')}) cap a {previst.get('data', '')} · queden {int(r_left):,} km.")
                else:
                    _estat(r_left, r_int)

            with st.expander("📅 Planificar canvi de rodes"):
                with st.form("form_rodes_previst"):
                    p1, p2, p3, p4 = st.columns(4)
                    pv_km = p1.number_input("Km previstos", min_value=0, value=int(previst.get("km") or (car_kms_actuals + 4000)), step=100)
                    pv_q = p2.radio("Quantes rodes?", [1, 2, 4], index=[1, 2, 4].index(int(previst.get("quantes", 2))) if int(previst.get("quantes", 2)) in [1, 2, 4] else 1, horizontal=True, key="pv_q")
                    pv_pos = p3.selectbox("Posició", ["Davanteres", "Posteriors", "Totes 4", "Davantera esquerra", "Davantera dreta", "Posterior esquerra", "Posterior dreta"], key="pv_pos")
                    pv_data = p4.text_input("Data aproximada", value=previst.get("data", "Nadal 2026"))
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Desar previsió", type="primary"):
                        mant["rodes"]["previst"] = {"km": int(pv_km), "quantes": int(pv_q), "posicio": pv_pos, "data": pv_data}
                        _save_mant(mant)
                        st.rerun()
                    if b2.form_submit_button("🗑️ Esborrar previsió"):
                        mant["rodes"].pop("previst", None)
                        _save_mant(mant)
                        st.rerun()

            with st.expander("✏️ Registrar canvi de rodes fet"):
                with st.form("form_rodes"):
                    g1, g2, g3 = st.columns(3)
                    nr_km = g1.number_input("Km del canvi", min_value=0, value=int(car_kms_actuals), step=100, key="r_km")
                    nr_q = g2.radio("Quantes rodes?", [1, 2, 4], index=1, horizontal=True)
                    nr_pos = g3.selectbox("Posició", ["Davanteres", "Posteriors", "Totes 4", "Davantera esquerra", "Davantera dreta", "Posterior esquerra", "Posterior dreta"])
                    h1, h2 = st.columns(2)
                    nr_int = h1.number_input("Interval estimat (km)", min_value=1000, value=int(r_int), step=1000)
                    nr_data = h2.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key="r_data")
                    nr_nota = st.text_input("Observacions (marca, model...)", key="r_nota")
                    if st.form_submit_button("💾 Desar canvi de rodes", type="primary"):
                        d = nr_data.strftime("%d/%m/%Y")
                        mant["rodes"] = {"ultim_canvi_km": int(nr_km), "interval_km": int(nr_int), "quantes_rodes": int(nr_q), "posicio": nr_pos, "data_ultim_canvi": d}
                        mant["historic"].append({"data": d, "tipus": "Rodes", "km": int(nr_km), "rodes": f"{nr_q} ({nr_pos})", "detall": nr_nota})
                        _save_mant(mant)
                        st.success("Canvi de rodes desat!")
                        st.rerun()

        # ---------- INFLAT DE RODES ----------
        inflat = mant.get("inflat_rodes") or {}
        inf_last_str = inflat.get("data_ultim_inflat", "")
        inf_last_km = inflat.get("km_ultim_inflat")
        inf_pressio = inflat.get("pressio") or "2.4 bar"
        planificacions = inflat.get("planificacions") or []

        avui = datetime.today().date()
        occurrences = get_inflat_occurrences(planificacions, inf_last_str, avui)

        # Proxim inflat
        upcoming = [occ for occ in occurrences if occ["dies_left"] >= 0]
        upcoming.sort(key=lambda x: x["dies_left"])
        proxim_occ = upcoming[0] if upcoming else None

        inf_proper_str = proxim_occ["next_date"].strftime("%d/%m/%Y") if proxim_occ else ""
        proxim_titol = proxim_occ["titol"] if proxim_occ else "Sense planificar"
        proxim_dies = proxim_occ["dies_left"] if proxim_occ else None
        proxim_avis = proxim_occ["avis_dies"] if proxim_occ else 15

        if inf_proper_str and mant["inflat_rodes"].get("propera_data") != inf_proper_str:
            mant["inflat_rodes"]["propera_data"] = inf_proper_str

        inflat_tag = f" · Proper: {inf_proper_str} ({proxim_titol})" if proxim_occ else ""
        exp_inflat = expand_all or (st.session_state.get("editing_plan_idx") is not None)

        with st.expander(f"💨 Inflat de Rodes (Pressió){inflat_tag}", expanded=exp_inflat):
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Últim inflat", inf_last_str if inf_last_str else "Sense registre",
                      help=(f"Pressió: {inf_pressio}" if inf_pressio else None))
            
            active_plans = [p for p in planificacions if p.get("actiu", True)]
            e2.metric("Planificació", f"{len(active_plans)} viatges/any", help="Viatges anuals i dates fixes programades")
            e3.metric("Proper inflat", f"{inf_proper_str}" if inf_proper_str else "Sense planificar", help=f"{proxim_titol} (Avisar {proxim_avis} dies abans)")
            e4.metric("Dies restants", f"{proxim_dies} dies" if proxim_dies is not None else "-")

            # Avisos d'inflat
            has_banner = False
            for occ in occurrences:
                dies = occ["dies_left"]
                titol = occ["titol"]
                d_str = occ["next_date"].strftime("%d/%m/%Y")
                avis = occ["avis_dies"]
                status = occ["status"]
                if status == "superat" or (dies < 0 and status not in ("fet_enguany", "fet", "proper_any")):
                    st.error(f"🚨 Inflat de rodes superat per {abs(dies)} dies per al **{titol}**! (data prevista: {d_str})")
                    has_banner = True
                elif dies <= avis and status == "pendent":
                    st.warning(f"⚠️ Toca revisar la pressió / inflar les rodes per al **{titol}**! Queden només {dies} dies (data prevista: {d_str}).")
                    has_banner = True

            if not has_banner:
                if proxim_occ:
                    st.success(f"✅ Tot correcte. Queden {proxim_dies} dies per al proper inflat planificat: **{proxim_titol}** ({inf_proper_str}).")
                else:
                    st.info("ℹ️ Encara no s'ha planificat cap data per al proper inflat de rodes.")

            # 1. Expandible de planificació de viatges i alertes (SENSE st.form per evitar submissions involuntàries amb Enter)
            with st.expander("📅 Planificació de dates d'inflat (Viatges fixes i alertes)"):
                st.markdown("##### 📋 Viatges i manteniments programats")
                mesos_noms = ["Gener", "Febrer", "Març", "Abril", "Maig", "Juny", "Juliol", "Agost", "Setembre", "Octubre", "Novembre", "Desembre"]
                
                if not planificacions:
                    st.info("No hi ha cap viatge o data planificada.")
                else:
                    to_delete = None
                    for idx, p in enumerate(planificacions):
                        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns([3.5, 2.5, 2.2, 0.9, 0.9])
                        p_tit = p.get("titol", "Inflat")
                        p_rec = p.get("recurrent", True)
                        p_avis = p.get("avis_dies_abans", 15)
                        if p_rec:
                            d_info = f"Cada any el {p.get('dia', 1):02d}/{p.get('mes', 1):02d}"
                        else:
                            d_info = f"Data puntual: {p.get('data_puntual', '-')}"
                            
                        occ_p = next((o for o in occurrences if o.get("id") == p.get("id")), None)
                        rest_info = f"({occ_p['dies_left']} dies)" if occ_p else ""
                        
                        col_p1.markdown(f"**{p_tit}**")
                        col_p2.write(f"📅 {d_info}")
                        col_p3.caption(f"🔔 Avís {p_avis}d abans {rest_info}")
                        
                        is_editing = (st.session_state.get("editing_plan_idx") == idx)
                        if col_p4.button("✏️" if not is_editing else "🔼", key=f"edit_plan_{idx}", help=f"Modificar {p_tit}"):
                            if is_editing:
                                del st.session_state["editing_plan_idx"]
                            else:
                                st.session_state["editing_plan_idx"] = idx
                            st.rerun()

                        if col_p5.button("🗑️", key=f"del_plan_{idx}", help=f"Eliminar {p_tit}"):
                            to_delete = idx

                        # Editor en línia si aquest viatge està en mode edició
                        if is_editing:
                            with st.container(border=True):
                                st.markdown(f"###### ✏️ Modificar planificació: **{p_tit}**")
                                m_c1, m_c2 = st.columns([2, 1])
                                edit_titol = m_c1.text_input("Motiu o viatge", value=p.get("titol", ""), key=f"ed_tit_{idx}")
                                edit_tipus = m_c2.radio("Tipus", ["Recurrent cada any", "Data única puntual"],
                                                         index=0 if p_rec else 1, key=f"ed_tip_{idx}", horizontal=True)

                                m_c3, m_c4, m_c5 = st.columns(3)
                                if edit_tipus == "Recurrent cada any":
                                    cur_dia = int(p.get("dia", 20))
                                    cur_mes = int(p.get("mes", 7))
                                    edit_dia = m_c3.number_input("Dia del mes", min_value=1, max_value=31, value=cur_dia, step=1, key=f"ed_dia_{idx}")
                                    edit_mes = m_c4.selectbox("Mes de l'any", range(1, 13), format_func=lambda m: f"{m:02d} - {mesos_noms[m-1]}", index=cur_mes-1, key=f"ed_mes_{idx}")
                                    edit_data_punt_val = ""
                                else:
                                    init_d = avui + timedelta(days=30)
                                    if p.get("data_puntual"):
                                        try:
                                            init_d = datetime.strptime(str(p.get("data_puntual")).strip(), "%d/%m/%Y").date()
                                        except Exception:
                                            pass
                                    edit_dt = m_c3.date_input("Data de l'inflat", value=init_d, format="DD/MM/YYYY", key=f"ed_dt_{idx}")
                                    edit_data_punt_val = edit_dt.strftime("%d/%m/%Y")
                                    edit_dia = edit_dt.day
                                    edit_mes = edit_dt.month

                                edit_avis = m_c5.number_input("Avisar amb antelació (dies)", min_value=1, max_value=60, value=int(p.get("avis_dies_abans", 15)), step=1, key=f"ed_avis_{idx}")

                                b_ed1, b_ed2 = st.columns([1.5, 4])
                                if b_ed1.button("💾 Desar canvis", type="primary", key=f"btn_save_ed_{idx}"):
                                    if not edit_titol.strip():
                                        st.error("El motiu o viatge no pot estar buit.")
                                    else:
                                        p["titol"] = edit_titol.strip()
                                        p["recurrent"] = (edit_tipus == "Recurrent cada any")
                                        p["dia"] = int(edit_dia)
                                        p["mes"] = int(edit_mes)
                                        p["data_puntual"] = edit_data_punt_val
                                        p["avis_dies_abans"] = int(edit_avis)
                                        mant["inflat_rodes"]["planificacions"] = planificacions
                                        _save_mant(mant)
                                        del st.session_state["editing_plan_idx"]
                                        st.success(f"S'han desat els canvis per a '{edit_titol.strip()}'!")
                                        st.rerun()

                                if b_ed2.button("❌ Cancel·lar", key=f"btn_cancel_ed_{idx}"):
                                    del st.session_state["editing_plan_idx"]
                                    st.rerun()
                            
                    if to_delete is not None:
                        if st.session_state.get("editing_plan_idx") == to_delete:
                            del st.session_state["editing_plan_idx"]
                        planificacions.pop(to_delete)
                        mant["inflat_rodes"]["planificacions"] = planificacions
                        _save_mant(mant)
                        st.rerun()

                st.write("---")
                st.markdown("##### ➕ Afegir nova data de planificació")
                plan_form_ver = st.session_state.get("plan_form_ver", 0)
                np_c1, np_c2 = st.columns([2, 1])
                nou_titol = np_c1.text_input("Motiu o viatge", placeholder="Ex: Viatge d'estiu, Viatge de Nadal, Setmana Santa...", key=f"nou_plan_titol_{plan_form_ver}")
                nou_tipus = np_c2.radio("Tipus", ["Recurrent cada any", "Data única puntual"], key=f"nou_plan_tipus_{plan_form_ver}", horizontal=True)

                np_c3, np_c4, np_c5 = st.columns(3)

                if nou_tipus == "Recurrent cada any":
                    nou_dia = np_c3.number_input("Dia del mes", min_value=1, max_value=31, value=20, step=1, key=f"nou_plan_dia_{plan_form_ver}")
                    nou_mes_idx = np_c4.selectbox("Mes de l'any", range(1, 13), format_func=lambda m: f"{m:02d} - {mesos_noms[m-1]}", index=6, key=f"nou_plan_mes_{plan_form_ver}")
                    data_punt_val = ""
                else:
                    data_punt_dt = np_c3.date_input("Data de l'inflat", value=avui + timedelta(days=30), format="DD/MM/YYYY", key=f"nou_plan_dt_{plan_form_ver}")
                    data_punt_val = data_punt_dt.strftime("%d/%m/%Y")
                    nou_dia = data_punt_dt.day
                    nou_mes_idx = data_punt_dt.month

                nou_avis_dies = np_c5.number_input("Avisar amb antelació (dies)", min_value=1, max_value=60, value=15, step=1, key=f"nou_plan_avis_{plan_form_ver}")

                if st.button("➕ Afegir a la planificació", type="primary", key="btn_afegir_plan"):
                    if not nou_titol.strip():
                        st.error("Si us plau, introdueix un motiu o nom per al viatge / manteniment.")
                    else:
                        nou_item = {
                            "id": str(int(datetime.now().timestamp())),
                            "titol": nou_titol.strip(),
                            "dia": int(nou_dia),
                            "mes": int(nou_mes_idx),
                            "recurrent": (nou_tipus == "Recurrent cada any"),
                            "data_puntual": data_punt_val,
                            "avis_dies_abans": int(nou_avis_dies),
                            "actiu": True
                        }
                        planificacions.append(nou_item)
                        mant["inflat_rodes"]["planificacions"] = planificacions
                        _save_mant(mant)
                        st.session_state["plan_form_ver"] = plan_form_ver + 1
                        st.success(f"S'ha afegit '{nou_titol.strip()}' a la planificació!")
                        st.rerun()

            # 2. Expandible de registre d'inflat fet (SENSE st.form per evitar enviaments involuntaris amb la tecla Enter)
            inflat_fet_ver = st.session_state.get("inflat_fet_ver", 0)
            with st.expander("✏️ Registrar inflat de rodes fet"):
                j1, j2, j3 = st.columns(3)
                r_data = j1.date_input("Data de l'inflat", value=avui, format="DD/MM/YYYY", key=f"inf_fet_data_{inflat_fet_ver}")
                r_km = j2.number_input("Km del cotxe (opcional)", min_value=0, value=int(car_kms_actuals), step=100, key=f"inf_fet_km_{inflat_fet_ver}")
                r_pressio = j3.text_input("Pressió aplicada", value=inf_pressio or "2.4 bar", placeholder="Ex: 2.4 bar", key=f"inf_fet_pressio_{inflat_fet_ver}")

                r_nota = st.text_input("Observacions", value="Revisió i inflat de pressió de les rodes", key=f"inf_fet_nota_{inflat_fet_ver}")

                opcions_plans = ["Revisió / inflat puntual entre mig (manté intactes els viatges planificats)"]
                for p in planificacions:
                    opcions_plans.append(f"Compleix planificació: {p.get('titol', 'Inflat')}")

                correspon = st.selectbox("Aquest inflat correspon a:", opcions_plans, key=f"inf_fet_correspon_{inflat_fet_ver}",
                                         help="Si fas una revisió puntual entre viatges, selecciona l'opció puntual per no cancel·lar els viatges anuals programats.")

                afegir_hist = st.checkbox("Afegir a l'històric de manteniment", value=True, key=f"inf_fet_hist_{inflat_fet_ver}")

                if st.button("💾 Desar inflat fet", type="primary", key="btn_desar_inflat"):
                    d_fet_str = r_data.strftime("%d/%m/%Y")
                    mant["inflat_rodes"]["data_ultim_inflat"] = d_fet_str
                    mant["inflat_rodes"]["km_ultim_inflat"] = int(r_km) if r_km > 0 else None
                    mant["inflat_rodes"]["pressio"] = r_pressio.strip() or "2.4 bar"

                    # Si correspon a un viatge o planificació concreta, marcar-lo com a complert
                    if correspon != opcions_plans[0]:
                        nom_sel = correspon.replace("Compleix planificació: ", "").strip()
                        for p in planificacions:
                            if p.get("titol", "").strip() == nom_sel:
                                if p.get("recurrent", True):
                                    p["ultim_fet_any"] = r_data.year
                                else:
                                    p["fet"] = True
                        mant["inflat_rodes"]["planificacions"] = planificacions

                    if afegir_hist:
                        mant["historic"].append({
                            "data": d_fet_str,
                            "tipus": "Inflat Rodes",
                            "km": int(r_km),
                            "rodes": "Totes 4",
                            "detall": f"{r_nota.strip()} ({r_pressio.strip() or '2.4 bar'})"
                        })

                    _save_mant(mant)
                    st.session_state["inflat_fet_ver"] = inflat_fet_ver + 1
                    st.success(f"Inflat desat correctament! Pressió registrada: {r_pressio.strip() or '2.4 bar'}.")
                    st.rerun()

        # ---------- CONTROL DE NIVELLS ----------
        nivells = mant.get("control_nivells") or {}
        niv_last_str = nivells.get("data_ultim_control", "")
        niv_last_km = nivells.get("km_ultim_control")
        niv_estat = nivells.get("estat_nivells") or "Tots correctes (Oli, refrigerant, parabrises, frens)"
        plan_nivells = nivells.get("planificacions") or []

        occ_nivells = get_inflat_occurrences(plan_nivells, niv_last_str, avui)

        # Proxim control
        upcoming_niv = [occ for occ in occ_nivells if occ["dies_left"] >= 0]
        upcoming_niv.sort(key=lambda x: x["dies_left"])
        proxim_occ_niv = upcoming_niv[0] if upcoming_niv else None

        niv_proper_str = proxim_occ_niv["next_date"].strftime("%d/%m/%Y") if proxim_occ_niv else ""
        proxim_titol_niv = proxim_occ_niv["titol"] if proxim_occ_niv else "Sense planificar"
        proxim_dies_niv = proxim_occ_niv["dies_left"] if proxim_occ_niv else None
        proxim_avis_niv = proxim_occ_niv["avis_dies"] if proxim_occ_niv else 15

        if niv_proper_str and mant["control_nivells"].get("propera_data") != niv_proper_str:
            mant["control_nivells"]["propera_data"] = niv_proper_str

        niv_tag = f" · Proper: {niv_proper_str} ({proxim_titol_niv})" if proxim_occ_niv else ""
        exp_niv = expand_all or (st.session_state.get("editing_niv_idx") is not None)

        with st.expander(f"🧪 Control de Nivells{niv_tag}", expanded=exp_niv):
            n1, n2, n3, n4 = st.columns(4)
            n1.metric("Últim control", niv_last_str if niv_last_str else "Sense registre",
                      help=(f"Estat: {niv_estat}" if niv_estat else None))
            
            active_plans_niv = [p for p in plan_nivells if p.get("actiu", True)]
            n2.metric("Planificació", f"{len(active_plans_niv)} controls/any", help="Viatges anuals i dates fixes programades")
            n3.metric("Proper control", f"{niv_proper_str}" if niv_proper_str else "Sense planificar", help=f"{proxim_titol_niv} (Avisar {proxim_avis_niv} dies abans)")
            n4.metric("Dies restants", f"{proxim_dies_niv} dies" if proxim_dies_niv is not None else "-")

            # Avisos de nivells
            has_banner_niv = False
            for occ in occ_nivells:
                dies = occ["dies_left"]
                titol = occ["titol"]
                d_str = occ["next_date"].strftime("%d/%m/%Y")
                avis = occ["avis_dies"]
                status = occ["status"]
                if status == "superat" or (dies < 0 and status not in ("fet_enguany", "fet", "proper_any")):
                    st.error(f"🚨 Control de nivells superat per {abs(dies)} dies per al **{titol}**! (data prevista: {d_str})")
                    has_banner_niv = True
                elif dies <= avis and status == "pendent":
                    st.warning(f"⚠️ Toca revisar els nivells del cotxe per al **{titol}**! Queden només {dies} dies (data prevista: {d_str}).")
                    has_banner_niv = True

            if not has_banner_niv:
                if proxim_occ_niv:
                    st.success(f"✅ Tot correcte. Queden {proxim_dies_niv} dies per al proper control planificat: **{proxim_titol_niv}** ({niv_proper_str}).")
                else:
                    st.info("ℹ️ Encara no s'ha planificat cap data per al proper control de nivells.")

            # 1. Expandible de planificació de controls de nivells
            with st.expander("📅 Planificació de dates de control de nivells (Viatges fixes i alertes)"):
                st.markdown("##### 📋 Viatges i controls de nivells programats")
                if not plan_nivells:
                    st.info("No hi ha cap viatge o control planificat.")
                else:
                    to_delete_niv = None
                    for idx, p in enumerate(plan_nivells):
                        col_n1, col_n2, col_n3, col_n4, col_n5 = st.columns([3.5, 2.5, 2.2, 0.9, 0.9])
                        p_tit = p.get("titol", "Control de nivells")
                        p_rec = p.get("recurrent", True)
                        p_avis = p.get("avis_dies_abans", 15)
                        if p_rec:
                            d_info = f"Cada any el {p.get('dia', 1):02d}/{p.get('mes', 1):02d}"
                        else:
                            d_info = f"Data puntual: {p.get('data_puntual', '-')}"

                        occ_p = next((o for o in occ_nivells if o.get("id") == p.get("id")), None)
                        rest_info = f"({occ_p['dies_left']} dies)" if occ_p else ""

                        col_n1.markdown(f"**{p_tit}**")
                        col_n2.write(f"📅 {d_info}")
                        col_n3.caption(f"🔔 Avís {p_avis}d abans {rest_info}")

                        is_editing_niv = (st.session_state.get("editing_niv_idx") == idx)
                        if col_n4.button("✏️" if not is_editing_niv else "🔼", key=f"edit_niv_{idx}", help=f"Modificar {p_tit}"):
                            if is_editing_niv:
                                del st.session_state["editing_niv_idx"]
                            else:
                                st.session_state["editing_niv_idx"] = idx
                            st.rerun()

                        if col_n5.button("🗑️", key=f"del_niv_{idx}", help=f"Eliminar {p_tit}"):
                            to_delete_niv = idx

                        # Editor en línia
                        if is_editing_niv:
                            with st.container(border=True):
                                st.markdown(f"###### ✏️ Modificar planificació: **{p_tit}**")
                                mn_c1, mn_c2 = st.columns([2, 1])
                                ed_niv_tit = mn_c1.text_input("Motiu o viatge", value=p.get("titol", ""), key=f"ed_niv_tit_{idx}")
                                ed_niv_tip = mn_c2.radio("Tipus", ["Recurrent cada any", "Data única puntual"],
                                                         index=0 if p_rec else 1, key=f"ed_niv_tip_{idx}", horizontal=True)

                                mn_c3, mn_c4, mn_c5 = st.columns(3)
                                if ed_niv_tip == "Recurrent cada any":
                                    cur_dia = int(p.get("dia", 20))
                                    cur_mes = int(p.get("mes", 7))
                                    ed_niv_dia = mn_c3.number_input("Dia del mes", min_value=1, max_value=31, value=cur_dia, step=1, key=f"ed_niv_dia_{idx}")
                                    ed_niv_mes = mn_c4.selectbox("Mes de l'any", range(1, 13), format_func=lambda m: f"{m:02d} - {mesos_noms[m-1]}", index=cur_mes-1, key=f"ed_niv_mes_{idx}")
                                    ed_niv_dt_val = ""
                                else:
                                    init_d = avui + timedelta(days=30)
                                    if p.get("data_puntual"):
                                        try:
                                            init_d = datetime.strptime(str(p.get("data_puntual")).strip(), "%d/%m/%Y").date()
                                        except Exception:
                                            pass
                                    edit_dt = mn_c3.date_input("Data del control", value=init_d, format="DD/MM/YYYY", key=f"ed_dt_{idx}")
                                    ed_niv_dt_val = edit_dt.strftime("%d/%m/%Y")
                                    ed_niv_dia = edit_dt.day
                                    ed_niv_mes = edit_dt.month

                                ed_niv_avis = mn_c5.number_input("Avisar amb antelació (dies)", min_value=1, max_value=60, value=int(p.get("avis_dies_abans", 15)), step=1, key=f"ed_niv_avis_{idx}")

                                b_edn1, b_edn2 = st.columns([1.5, 4])
                                if b_edn1.button("💾 Desar canvis", type="primary", key=f"btn_save_ed_niv_{idx}"):
                                    if not ed_niv_tit.strip():
                                        st.error("El motiu o viatge no pot estar buit.")
                                    else:
                                        p["titol"] = ed_niv_tit.strip()
                                        p["recurrent"] = (ed_niv_tip == "Recurrent cada any")
                                        p["dia"] = int(ed_niv_dia)
                                        p["mes"] = int(ed_niv_mes)
                                        p["data_puntual"] = ed_niv_dt_val
                                        p["avis_dies_abans"] = int(ed_niv_avis)
                                        mant["control_nivells"]["planificacions"] = plan_nivells
                                        _save_mant(mant)
                                        del st.session_state["editing_niv_idx"]
                                        st.success(f"S'han desat els canvis per a '{ed_niv_tit.strip()}'!")
                                        st.rerun()

                                if b_edn2.button("❌ Cancel·lar", key=f"btn_cancel_ed_niv_{idx}"):
                                    del st.session_state["editing_niv_idx"]
                                    st.rerun()

                    if to_delete_niv is not None:
                        if st.session_state.get("editing_niv_idx") == to_delete_niv:
                            del st.session_state["editing_niv_idx"]
                        plan_nivells.pop(to_delete_niv)
                        mant["control_nivells"]["planificacions"] = plan_nivells
                        _save_mant(mant)
                        st.rerun()

                st.write("---")
                st.markdown("##### ➕ Afegir nova data de control de nivells")
                niv_form_ver = st.session_state.get("niv_form_ver", 0)
                nn_c1, nn_c2 = st.columns([2, 1])
                nou_titol_niv = nn_c1.text_input("Motiu o viatge", placeholder="Ex: Viatge d'estiu, Viatge de Nadal, Control abans d'ITV...", key=f"nou_niv_titol_{niv_form_ver}")
                nou_tipus_niv = nn_c2.radio("Tipus", ["Recurrent cada any", "Data única puntual"], key=f"nou_niv_tipus_{niv_form_ver}", horizontal=True)

                nn_c3, nn_c4, nn_c5 = st.columns(3)
                if nou_tipus_niv == "Recurrent cada any":
                    nou_dia_niv = nn_c3.number_input("Dia del mes", min_value=1, max_value=31, value=20, step=1, key=f"nou_niv_dia_{niv_form_ver}")
                    nou_mes_niv = nn_c4.selectbox("Mes de l'any", range(1, 13), format_func=lambda m: f"{m:02d} - {mesos_noms[m-1]}", index=6, key=f"nou_niv_mes_{niv_form_ver}")
                    data_punt_val_niv = ""
                else:
                    data_punt_dt_niv = nn_c3.date_input("Data del control", value=avui + timedelta(days=30), format="DD/MM/YYYY", key=f"nou_niv_dt_{niv_form_ver}")
                    data_punt_val_niv = data_punt_dt_niv.strftime("%d/%m/%Y")
                    nou_dia_niv = data_punt_dt_niv.day
                    nou_mes_niv = data_punt_dt_niv.month

                nou_avis_niv = nn_c5.number_input("Avisar amb antelació (dies)", min_value=1, max_value=60, value=15, step=1, key=f"nou_niv_avis_{niv_form_ver}")

                if st.button("➕ Afegir a la planificació", type="primary", key="btn_afegir_plan_niv"):
                    if not nou_titol_niv.strip():
                        st.error("Si us plau, introdueix un motiu o nom per al viatge / control.")
                    else:
                        nou_item_niv = {
                            "id": str(int(datetime.now().timestamp())),
                            "titol": nou_titol_niv.strip(),
                            "dia": int(nou_dia_niv),
                            "mes": int(nou_mes_niv),
                            "recurrent": (nou_tipus_niv == "Recurrent cada any"),
                            "data_puntual": data_punt_val_niv,
                            "avis_dies_abans": int(nou_avis_niv),
                            "actiu": True
                        }
                        plan_nivells.append(nou_item_niv)
                        mant["control_nivells"]["planificacions"] = plan_nivells
                        _save_mant(mant)
                        st.session_state["niv_form_ver"] = niv_form_ver + 1
                        st.success(f"S'ha afegit '{nou_titol_niv.strip()}' a la planificació de nivells!")
                        st.rerun()

            # 2. Expandible de registre de control de nivells fet
            niv_fet_ver = st.session_state.get("niv_fet_ver", 0)
            with st.expander("✏️ Registrar control de nivells fet"):
                kn1, kn2, kn3 = st.columns(3)
                rn_data = kn1.date_input("Data del control", value=avui, format="DD/MM/YYYY", key=f"niv_fet_data_{niv_fet_ver}")
                rn_km = kn2.number_input("Km del cotxe (opcional)", min_value=0, value=int(car_kms_actuals), step=100, key=f"niv_fet_km_{niv_fet_ver}")
                
                opcions_estat = [
                    "Tots correctes (Oli, refrigerant, parabrises, frens)",
                    "Rellenat líquid parabrises",
                    "Rellenat refrigerant",
                    "Rellenat oli",
                    "Revisat / altres (veure notes)"
                ]
                idx_estat = 0
                if niv_estat in opcions_estat:
                    idx_estat = opcions_estat.index(niv_estat)
                rn_estat = kn3.selectbox("Estat dels nivells", opcions_estat, index=idx_estat, key=f"niv_fet_estat_{niv_fet_ver}")

                rn_nota = st.text_input("Observacions", value="Revisió de nivells d'oli, refrigerant, eixugaparabrises i líquid de frens", key=f"niv_fet_nota_{niv_fet_ver}")

                opcions_plans_niv = ["Control / revisió puntual entre mig (manté intactes els viatges planificats)"]
                for p in plan_nivells:
                    opcions_plans_niv.append(f"Compleix planificació: {p.get('titol', 'Control de nivells')}")

                correspon_niv = st.selectbox("Aquest control correspon a:", opcions_plans_niv, key=f"niv_fet_correspon_{niv_fet_ver}",
                                             help="Si fas una revisió puntual entre viatges, selecciona l'opció puntual per no cancel·lar els viatges anuals programats.")

                afegir_hist_niv = st.checkbox("Afegir a l'històric de manteniment", value=True, key=f"niv_fet_hist_{niv_fet_ver}")

                if st.button("💾 Desar control fet", type="primary", key="btn_desar_niv"):
                    dn_fet_str = rn_data.strftime("%d/%m/%Y")
                    mant["control_nivells"]["data_ultim_control"] = dn_fet_str
                    mant["control_nivells"]["km_ultim_control"] = int(rn_km) if rn_km > 0 else None
                    mant["control_nivells"]["estat_nivells"] = rn_estat

                    # Marcar compliment de viatge si escau
                    if correspon_niv != opcions_plans_niv[0]:
                        nom_sel_n = correspon_niv.replace("Compleix planificació: ", "").strip()
                        for p in plan_nivells:
                            if p.get("titol", "").strip() == nom_sel_n:
                                if p.get("recurrent", True):
                                    p["ultim_fet_any"] = rn_data.year
                                else:
                                    p["fet"] = True
                        mant["control_nivells"]["planificacions"] = plan_nivells

                    if afegir_hist_niv:
                        mant["historic"].append({
                            "data": dn_fet_str,
                            "tipus": "Control Nivells",
                            "km": int(rn_km),
                            "rodes": "",
                            "detall": f"{rn_nota.strip()} [{rn_estat}]"
                        })

                    _save_mant(mant)
                    st.session_state["niv_fet_ver"] = niv_fet_ver + 1
                    st.success(f"Control de nivells desat correctament! Estat: {rn_estat}.")
                    st.rerun()

        # ---------- TALLER / AVARIES ----------
        pendents = [h for h in mant["historic"] if h.get("estat") in ("Pendent", "En taller")]
        taller_tag = f" · ⚠️ {len(pendents)} pendents" if pendents else ""

        with st.expander(f"🛠️ Taller i Avaries{taller_tag}", expanded=expand_all or bool(pendents)):
            with st.expander("➕ Registrar entrada a taller / avaria / altre manteniment"):
                with st.form("form_taller"):
                    t1, t2, t3 = st.columns(3)
                    t_data = t1.date_input("Data", value=datetime.today(), format="DD/MM/YYYY", key="t_data")
                    t_km = t2.number_input("Km del cotxe", min_value=0, value=int(car_kms_actuals), step=100, key="t_km")
                    t_tipus = t3.selectbox("Tipus", ["Avaria", "Revisió", "ITV", "Frens", "Bateria", "Filtres", "Carrosseria", "Altres"], key="t_tipus")
                    t4, t5, t6 = st.columns(3)
                    t_taller = t4.text_input("Taller", key="t_taller")
                    t_cost_txt = t5.text_input("Cost (€)", value="", placeholder="Ex: 226,51", key="t_cost")
                    t_estat = t6.selectbox("Estat", ["Resolt", "Pendent", "En taller"], key="t_estat")
                    t_desc = st.text_area("Descripció (què ha passat / què s'ha fet)", key="t_desc")
                    if st.form_submit_button("💾 Desar registre", type="primary"):
                        try:
                            t_cost = float(t_cost_txt.replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")) if "," in t_cost_txt else float(t_cost_txt.replace("€", "").strip() or 0)
                        except ValueError:
                            t_cost = None
                        if t_cost is None:
                            st.error("El cost no és un número vàlid.")
                        elif not t_desc.strip():
                            st.error("Escriu una descripció.")
                        else:
                            mant["historic"].append({
                                "data": t_data.strftime("%d/%m/%Y"), "tipus": t_tipus, "km": int(t_km), "rodes": "",
                                "detall": t_desc.strip(), "taller": t_taller.strip(), "cost": float(t_cost), "estat": t_estat
                            })
                            _save_mant(mant)
                            for k in ["t_cost", "t_desc", "t_taller"]:
                                st.session_state.pop(k, None)
                            st.rerun()

            for p in pendents:
                st.warning(f"🔧 **{p.get('tipus')}** ({p.get('estat')}) · {p.get('data')} · {p.get('detall')}")

        # ---------- HISTÒRIC ----------
        hist_count = len(mant.get("historic", []))
        hist_tag = f" · {hist_count} registres" if hist_count > 0 else ""

        with st.expander(f"📋 Històric de Manteniment i Taller{hist_tag}", expanded=expand_all):
            if mant["historic"]:
                df_h = pd.DataFrame(mant["historic"])
                for col in ["data", "tipus", "km", "rodes", "detall", "taller", "cost", "estat"]:
                    if col not in df_h.columns:
                        df_h[col] = None
                df_h["_ord"] = pd.to_datetime(df_h["data"], format="%d/%m/%Y", errors="coerce")
                df_h["_idx"] = range(len(df_h))
                df_h = df_h.sort_values(["_ord", "km"], ascending=False)

                tipus_disp = sorted(df_h["tipus"].dropna().unique().tolist())
                filtre = st.multiselect("Filtrar per tipus", tipus_disp, default=[], placeholder="Tots")
                if filtre:
                    df_h = df_h[df_h["tipus"].isin(filtre)]

                cost_total = pd.to_numeric(df_h["cost"], errors="coerce").fillna(0).sum()
                m1, m2 = st.columns(2)
                m1.metric("Registres", len(df_h))
                m2.metric("Cost total", f"{cost_total:,.2f} €")

                vista = df_h[["_idx", "data", "tipus", "km", "rodes", "detall", "taller", "cost", "estat"]].copy()
                vista.insert(0, "Eliminar", False)
                edited = st.data_editor(
                    vista, hide_index=True, use_container_width=True, key="hist_mant",
                    column_config={
                        "_idx": None, "data": "Data", "tipus": "Tipus", "km": st.column_config.NumberColumn("Km", format="%d"),
                        "rodes": "Rodes", "detall": "Detall", "taller": "Taller",
                        "cost": st.column_config.NumberColumn("Cost (€)", format="%.2f"),
                        "estat": st.column_config.SelectboxColumn("Estat", options=["", "Resolt", "Pendent", "En taller"]),
                        "tipus": st.column_config.SelectboxColumn("Tipus", options=sorted(set(["Oli", "Rodes", "Avaria", "Revisió", "ITV", "Frens", "Bateria", "Filtres", "Carrosseria", "Altres"] + tipus_disp))),
                    },
                    disabled=["rodes"],
                )
                c_save, c_del = st.columns(2)
                if c_save.button("💾 Desar canvis de l'històric"):
                    for _, r in edited.iterrows():
                        h = mant["historic"][int(r["_idx"])]
                        for col in ["data", "tipus", "detall", "taller", "estat"]:
                            h[col] = "" if pd.isna(r[col]) else r[col]
                        h["km"] = 0 if pd.isna(r["km"]) else int(r["km"])
                        h["cost"] = 0.0 if pd.isna(r["cost"]) else float(r["cost"])
                    _save_mant(mant)
                    st.rerun()
                if edited["Eliminar"].any() and c_del.button("🗑️ Eliminar seleccionats"):
                    borrar = set(edited.loc[edited["Eliminar"], "_idx"].astype(int))
                    mant["historic"] = [h for i, h in enumerate(mant["historic"]) if i not in borrar]
                    _save_mant(mant)
                    st.rerun()
            else:
                st.info("Encara no hi ha cap manteniment registrat.")

    # ----------------------------------------------------
    # TAB 4: CONSUM ANUAL
    # ----------------------------------------------------
    with tab_consum:
        st.markdown("<h4 style='color:#f39c12;'>📊 Consum Mitjà Anual (L/100km)</h4>", unsafe_allow_html=True)

        if not df_gas.empty and not df_km.empty:
            df_gas_work = df_gas.copy()
            df_km_work = df_km.copy()
            df_gas_work['parsed_date'] = df_gas_work['data'].apply(parse_excel_date)
            df_gas_work['litres_val'] = clean_numeric(df_gas_work.get('litres', 0))
            df_km_work['parsed_date'] = df_km_work['data'].apply(parse_excel_date)

            df_gas_tivoli = df_gas_work[df_gas_work['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_gas_work.columns else df_gas_work
            df_km_tivoli = df_km_work[df_km_work['cotxe'].str.contains('tivoli|tívoli', case=False, na=False)] if 'cotxe' in df_km_work.columns else df_km_work

            df_km_tivoli_valid = df_km_tivoli.dropna(subset=['contador', 'parsed_date']).copy()
            df_km_tivoli_valid['contador_val'] = pd.to_numeric(df_km_tivoli_valid['contador'], errors='coerce')
            df_km_tivoli_valid = df_km_tivoli_valid.dropna(subset=['contador_val'])

            if not df_gas_tivoli.empty and not df_km_tivoli_valid.empty:
                gas_yr = df_gas_tivoli.groupby(df_gas_tivoli['parsed_date'].dt.year)['litres_val'].sum()
                km_yr = df_km_tivoli_valid.groupby(df_km_tivoli_valid['parsed_date'].dt.year)['contador_val'].agg(lambda x: x.max() - x.min())
                km_yr = km_yr.replace(0, pd.NA)

                consumption = ((gas_yr / km_yr) * 100).dropna().reset_index()
                consumption.columns = ['Any', 'L/100km']
                consumption['Any'] = consumption['Any'].astype(str)

                if not consumption.empty:
                    fig_line = px.bar(consumption, x='Any', y='L/100km', text_auto='.2f', color_discrete_sequence=['#f39c12'])
                    fig_line.update_traces(textfont_size=20, textposition='outside', cliponaxis=False)
                    fig_line.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f8fafc'),
                        xaxis=dict(gridcolor='#334155', type='category'),
                        yaxis=dict(gridcolor='#334155'),
                        margin=dict(t=40, b=20, l=10, r=10)
                    )
                    st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("No hi ha prou dades per calcular el consum anual.")
            else:
                st.info("No s'han trobat suficients dades de quilometratge per calcular el consum.")
        else:
            st.info("No hi ha dades de gasolina o quilometratge registrades.")
