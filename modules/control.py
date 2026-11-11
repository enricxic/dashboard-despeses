"""
modules/control.py
Mòdul '🛡️ Control':
Panell de vigilància per nivells (Blindat / Vigilat / Obert), còpies de seguretat i rollback,
bateria de proves de regressió i auditoria d'impacte entre mòduls.
"""

from __future__ import annotations

import os
import streamlit as st

from core.control_manager import (
    LEVEL_BLINDAT,
    LEVEL_META,
    LEVEL_OBERT,
    LEVEL_VIGILAT,
    VALID_LEVELS,
    create_backup_snapshot,
    evaluate_all_modules,
    get_dependents,
    get_git_diff_summary,
    get_recent_git_log,
    is_git_available,
    list_backup_snapshots,
    load_registry,
    restore_backup_snapshot,
    run_fast_contracts,
    run_smoke_tests_subprocess,
    seal_module,
    set_module_level,
    unlock_module,
)


def _render_module_card(mod_id: str, entry: dict, status_info: dict, registry: dict, role: str) -> None:
    level = status_info["level"]
    meta = LEVEL_META.get(level, LEVEL_META[LEVEL_OBERT])
    state = status_info["state"]

    if state == "OK":
        badge_bg, badge_fg, badge_txt = "#064e3b", "#6ee7b7", "✅ Verificat"
    elif state == "DESBLOQUEJAT":
        badge_bg, badge_fg, badge_txt = "#78350f", "#fde68a", f"🔓 Desbloquejat fins {status_info['unlocked_until']}"
    elif state == "MODIFICAT_AUTORITZAT":
        badge_bg, badge_fg, badge_txt = "#1e3a8a", "#93c5fd", "🛠️ Editant amb permís"
    elif state == "MISSING":
        badge_bg, badge_fg, badge_txt = "#7f1d1d", "#fca5a5", "❌ Fitxer absent"
    else:
        badge_bg, badge_fg, badge_txt = "#7f1d1d", "#fca5a5", f"⚠️ Modificat ({len(status_info['changed_files'])})"

    with st.container(border=True):
        c_title, c_badge = st.columns([3, 2])
        with c_title:
            st.markdown(f"### {entry.get('icon', '📦')} {entry.get('name', mod_id)} `{mod_id}`")
            st.caption(
                f"Últim segell: **{status_info.get('verified_at') or '-'}** "
                f"(commit `{status_info.get('verified_commit') or '-'}`) · "
                f"Fitxers: {', '.join(f'`{f}`' for f in entry.get('files', []))}"
            )
        with c_badge:
            st.markdown(
                f"<div style='text-align:right; margin-top:6px;'>"
                f"<span style='background:{badge_bg}; color:{badge_fg}; padding:4px 10px; "
                f"border-radius:999px; font-weight:600; font-size:0.85rem;'>{badge_txt}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        if status_info["changed_files"]:
            st.warning("Fitxers modificats respecte a la versió segellada: " + ", ".join(status_info["changed_files"]))

        if status_info["unlocked"] and status_info["unlock_reason"]:
            st.info(f"Motiu autorització activa: {status_info['unlock_reason']}")

        dependents = get_dependents(registry, mod_id)
        if dependents:
            dep_names = [f"{registry['modules'][d]['icon']} {registry['modules'][d]['name']}" for d in dependents]
            st.caption("🔗 Afecta indirectament: " + ", ".join(dep_names))

        contracts = entry.get("contracts", [])
        if contracts:
            with st.expander("📋 Funcionalitats crítiques protegides", expanded=False):
                for c in contracts:
                    st.markdown(f"- {c}")

        if role != "admin":
            st.caption("🔒 Només el perfil Administrador pot modificar cadenats o nivells.")
            return

        col_b1, col_b2, col_b3, col_b4 = st.columns([1.4, 1.4, 1.3, 1.6])

        with col_b1:
            if level == LEVEL_BLINDAT and not status_info["unlocked"]:
                with st.popover("🔓 Desbloquejar", use_container_width=True):
                    motiu = st.text_input("Motiu obligatori del canvi", key=f"motiu_{mod_id}")
                    hores = st.number_input("Hores d'autorització", min_value=1, max_value=72, value=12, key=f"hores_{mod_id}")
                    if st.button("Confirmar desbloqueig + còpia", key=f"do_unlock_{mod_id}", type="primary", use_container_width=True):
                        ok, msg = unlock_module(mod_id, motiu, hours=int(hores), user=st.session_state.get("user", "admin"))
                        if ok:
                            st.toast(msg, icon="🔓")
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                if st.button("🔒 Verificar i Segellar", key=f"do_seal_{mod_id}", use_container_width=True):
                    ok, msg = seal_module(mod_id, user=st.session_state.get("user", "admin"))
                    if ok:
                        st.toast(msg, icon="🔒")
                        st.rerun()
                    else:
                        st.error(msg)

        with col_b2:
            if st.button("💾 Còpia de seguretat", key=f"do_bak_{mod_id}", use_container_width=True):
                snap = create_backup_snapshot(mod_id, reason="manual_ui", source="disk", registry=registry)
                if snap:
                    st.toast(f"Còpia desada: {os.path.basename(snap)}", icon="💾")
                else:
                    st.error("No s'ha pogut crear la còpia.")

        with col_b3:
            if st.button("🧪 Test ràpid", key=f"do_test_{mod_id}", use_container_width=True):
                ok, issues = run_fast_contracts([mod_id])
                if ok:
                    st.toast(f"{entry['name']}: contractes i sintaxi OK!", icon="✅")
                else:
                    st.error("\n".join(issues))

        with col_b4:
            cur_idx = VALID_LEVELS.index(level) if level in VALID_LEVELS else 2
            new_lvl = st.selectbox(
                "Nivell",
                VALID_LEVELS,
                index=cur_idx,
                format_func=lambda x: f"{LEVEL_META[x]['icon']} {LEVEL_META[x]['short']}",
                key=f"sel_lvl_{mod_id}",
                label_visibility="collapsed",
            )
            if new_lvl != level:
                ok, msg = set_module_level(mod_id, new_lvl, user=st.session_state.get("user", "admin"))
                if ok:
                    st.toast(msg, icon="🎚️")
                    st.rerun()


def render() -> None:
    if st.button("⬅️ Tornar a l'Inici"):
        st.session_state.current_module = None
        st.query_params.clear()
        st.rerun()

    st.title("🛡️ Control i Protecció de Mòduls")
    st.caption(
        "Sistema de protecció en 3 nivells (**Blindat**, **Vigilat**, **Obert**), "
        "còpies de seguretat amb rollback i proves automàtiques de regressió."
    )

    role = st.session_state.get("role", "guest")
    registry = load_registry()
    statuses = evaluate_all_modules(registry)

    counts = {LEVEL_BLINDAT: 0, LEVEL_VIGILAT: 0, LEVEL_OBERT: 0}
    modified_list = []
    for mid, st_info in statuses.items():
        lvl = st_info["level"]
        counts[lvl] = counts.get(lvl, 0) + 1
        if st_info["changed_files"] or st_info["state"] == "MISSING":
            modified_list.append(mid)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🔒 Blindats (Bloquejats)", counts[LEVEL_BLINDAT])
    k2.metric("🛡️ Vigilats (En ús)", counts[LEVEL_VIGILAT])
    k3.metric("🔓 Oberts (Construcció)", counts[LEVEL_OBERT])
    k4.metric("⚠️ Canvis respecte al segell", len(modified_list))

    tab_levels, tab_backups, tab_tests, tab_audit = st.tabs([
        "🚦 Nivells i Cadenats",
        "💾 Còpies de Seguretat i Rollback",
        "🧪 Proves de Regressió",
        "🔍 Auditoria i Historial",
    ])

    with tab_levels:
        for lvl in VALID_LEVELS:
            meta = LEVEL_META[lvl]
            st.markdown(f"## {meta['icon']} {meta['label']}")
            st.caption(meta["desc"])
            mods_in_lvl = [mid for mid, info in statuses.items() if info["level"] == lvl]
            if not mods_in_lvl:
                st.info("Cap mòdul assignat en aquest nivell.")
            for mid in mods_in_lvl:
                _render_module_card(mid, registry["modules"][mid], statuses[mid], registry, role)
            st.divider()

    with tab_backups:
        st.subheader("💾 Punts de Control, Còpies de Seguretat i Rollback")
        st.caption(
            "Els mòduls **Vigilats** i **Oberts** generen còpies automàtiques abans de cada commit; "
            "també pots crear punts de control manuals i restaurar qualsevol estat anterior."
        )

        mod_choices = list(registry["modules"].keys())
        c_sel, c_mot, c_btn = st.columns([2, 2, 1.3])
        with c_sel:
            bak_mod = st.selectbox(
                "Mòdul",
                mod_choices,
                format_func=lambda m: f"{registry['modules'][m]['icon']} {registry['modules'][m]['name']}",
                key="bak_create_mod",
            )
        with c_mot:
            bak_reason = st.text_input("Etiqueta / Motiu", value="punt_control", key="bak_create_reason")
        with c_btn:
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            if st.button("📸 Crear Snapshot ara", type="primary", use_container_width=True, disabled=(role != "admin")):
                snap = create_backup_snapshot(bak_mod, reason=bak_reason, source="disk", registry=registry)
                if snap:
                    st.success(f"Snapshot creat: `{os.path.basename(snap)}`")
                    st.rerun()
                else:
                    st.error("No s'han trobat fitxers per copiar.")

        st.divider()
        filter_mod = st.selectbox(
            "Filtrar snapshots per mòdul",
            ["Tots"] + mod_choices,
            format_func=lambda m: "Tots els mòduls" if m == "Tots" else f"{registry['modules'][m]['icon']} {registry['modules'][m]['name']}",
            key="bak_filter_mod",
        )
        snaps = list_backup_snapshots(None if filter_mod == "Tots" else filter_mod)
        if not snaps:
            st.info("Encara no hi ha còpies de seguretat locals desades a `data/control_backups/`.")
        else:
            for idx, snap in enumerate(snaps[:25]):
                with st.container(border=True):
                    sc1, sc2 = st.columns([3.5, 1.5])
                    with sc1:
                        st.markdown(
                            f"**{snap.get('module_name', snap.get('module_id'))}** · "
                            f"`{snap.get('created_at', '')}` · Motiu: `{snap.get('reason', '')}` · "
                            f"Commit: `{snap.get('git_head', '-')}`"
                        )
                        f_desc = ", ".join(f"`{fn}` ({meta.get('source', 'disk')})" for fn, meta in snap.get("files", {}).items())
                        st.caption(f"Fitxers: {f_desc}")
                    with sc2:
                        if role == "admin":
                            if st.button("⏪ Restaurar aquest punt", key=f"restore_{idx}_{snap['folder_name']}", use_container_width=True):
                                ok, msg, _ = restore_backup_snapshot(snap["snapshot_dir"], user=st.session_state.get("user", "admin"))
                                if ok:
                                    st.success(msg + " (S'ha creat abans una còpia de seguretat de seguretat per si cal desfer-ho.)")
                                    st.rerun()
                                else:
                                    st.error(msg)

    with tab_tests:
        st.subheader("🧪 Executor de Proves de Regressió i Contractes")
        c_t1, c_t2, c_t3 = st.columns([2, 1.4, 1.6])
        with c_t1:
            test_target = st.selectbox(
                "Abast de la prova",
                ["Tots"] + list(registry["modules"].keys()),
                format_func=lambda m: "🌐 Tots els mòduls" if m == "Tots" else f"{registry['modules'][m]['icon']} {registry['modules'][m]['name']}",
                key="test_target_sel",
            )
        with c_t2:
            test_mode = st.radio(
                "Tipus",
                ["Ràpid (<1s: Sintaxi + Contractes)", "Complet (AppTest E2E)"],
                key="test_mode_rad",
            )
        with c_t3:
            st.markdown("<div style='margin-top:26px;'></div>", unsafe_allow_html=True)
            run_now = st.button("▶️ Executar Proves", type="primary", use_container_width=True)

        if run_now:
            full = test_mode.startswith("Complet")
            target_arg = None if test_target == "Tots" else test_target
            with st.spinner("Executant comprovacions..."):
                ok, out = run_smoke_tests_subprocess(mod_id=target_arg, full_apptest=full)
            st.session_state["last_control_test_ok"] = ok
            st.session_state["last_control_test_out"] = out

        if "last_control_test_out" in st.session_state:
            if st.session_state.get("last_control_test_ok"):
                st.success("✅ Totes les proves han passat correctament.")
            else:
                st.error("❌ S'han detectat errors en les proves.")
            st.code(st.session_state["last_control_test_out"], language="text")

    with tab_audit:
        st.subheader("🔍 Auditoria de Canvis, Impacte Compartit i Historial")
        if is_git_available():
            st.markdown("#### Canvis pendents respecte `HEAD`")
            sel_diff_mod = st.selectbox(
                "Veure `git diff` del mòdul",
                list(registry["modules"].keys()),
                format_func=lambda m: f"{registry['modules'][m]['icon']} {registry['modules'][m]['name']}",
                key="audit_diff_mod",
            )
            diff_txt = get_git_diff_summary(registry["modules"][sel_diff_mod]["files"])
            if diff_txt:
                st.code(diff_txt, language="diff")
            else:
                st.success("Cap canvi pendent respecte al darrer commit Git per a aquest mòdul.")

            st.markdown("#### Darrers commits certificats al repositori")
            commits = get_recent_git_log(limit=12)
            if commits:
                st.dataframe(commits, use_container_width=True, hide_index=True)
        else:
            st.info("Entorn sense repositori `.git` local (ex. Streamlit Cloud). Es mostra el registre d'auditoria intern.")

        st.markdown("#### Registre d'Auditoria de Control (`control_registry.json`)")
        audit_rows = registry.get("audit_log", [])
        if audit_rows:
            st.dataframe(audit_rows[:30], use_container_width=True, hide_index=True)
        else:
            st.info("Sense esdeveniments d'auditoria registrats.")
