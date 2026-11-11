"""
tests/smoke/test_modules_smoke.py
Bateria de proves de regressió i contractes funcionals per a '🛡️ Control'.
- Mode ràpid (per defecte / pre-commit): sintaxi + contractes crítics (< 1s).
- Mode complet (CONTROL_FULL_APPTEST=1): proves reals amb streamlit.testing.v1.AppTest.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.control_manager import (
    load_registry,
    run_fast_contracts,
    run_syntax_check,
)


def _target_modules():
    env_mod = os.environ.get("CONTROL_TEST_MODULE", "").strip()
    if env_mod:
        return [m.strip() for m in env_mod.split(",") if m.strip()]
    return None


class TestFastContractsAndSyntax(unittest.TestCase):
    def test_syntax_and_contracts(self):
        targets = _target_modules()
        reg = load_registry()
        mods = targets or list(reg.get("modules", {}).keys())
        for mid in mods:
            entry = reg["modules"].get(mid)
            if not entry:
                continue
            with self.subTest(module=mid):
                ok_syn, syn_errs = run_syntax_check(entry.get("files", []))
                self.assertTrue(ok_syn, f"Errors de sintaxi a {mid}: {syn_errs}")
                ok_c, issues = run_fast_contracts([mid])
                self.assertTrue(ok_c, f"Contractes incomplerts a {mid}: {issues}")


@unittest.skipUnless(
    os.environ.get("CONTROL_FULL_APPTEST") == "1",
    "Executant només mode ràpid. Defineix CONTROL_FULL_APPTEST=1 per passar AppTest complet.",
)
class TestAppTestEndToEnd(unittest.TestCase):
    def _boot_module(self, mod_import_name: str):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(os.path.join(PROJECT_ROOT, "app.py"), default_timeout=90)
        at.session_state["authenticated"] = True
        at.session_state["role"] = "admin"
        at.session_state["user"] = "Admin"
        at.session_state["current_module"] = mod_import_name
        at.run(timeout=90)
        self.assertEqual(len(at.exception), 0, f"Excepció obrint {mod_import_name}: {at.exception}")
        return at

    def test_compres_manual_line_flow(self):
        targets = _target_modules()
        if targets and "compres" not in targets:
            self.skipTest("Filtrat per un altre mòdul")
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(os.path.join(PROJECT_ROOT, "app.py"), default_timeout=90)
        at.session_state["authenticated"] = True
        at.session_state["role"] = "admin"
        at.session_state["user"] = "Admin"
        at.session_state["current_module"] = "modules.compres"
        at.session_state["ticket_items"] = []
        at.run(timeout=90)
        self.assertEqual(len(at.exception), 0, f"Excepció inicial Compres: {at.exception}")

        at.session_state["manual_fam_selectbox"] = "verdura"
        at.session_state["manual_art_selectbox"] = "Tot junt"
        qty_w = next(w for w in at.number_input if w.key == "manual_qty_num")
        preu_w = next(w for w in at.number_input if w.key == "manual_preu_num")
        qty_w.set_value(1)
        preu_w.set_value(2.84)
        at.run(timeout=90)
        self.assertEqual(len(at.exception), 0, f"Excepció en entrar preu: {at.exception}")

        tot_w = next(w for w in at.text_input if w.key == "manual_tot_linea_disp")
        self.assertEqual(tot_w.value, "2.84 €")

        add_btn = next(w for w in at.button if w.key == "btn_add_line")
        add_btn.click()
        at.run(timeout=90)
        self.assertEqual(len(at.exception), 0, f"Excepció en clicar Entrar línia: {at.exception}")

        items = at.session_state["ticket_items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["totLinea"], 2.84)
        tot_after = next(w for w in at.text_input if w.key == "manual_tot_linea_disp")
        self.assertEqual(tot_after.value, "0.00 €")

    def test_blindat_and_vigilat_modules_boot(self):
        module_map = {
            "economic": "modules.economic",
            "cotxe": "modules.cotxe",
            "dashboard": "modules.dashboard",
            "llum_aigua": "modules.llum_aigua",
            "manteniment": "modules.manteniment",
            "menjar": "modules.menjar",
            "admin": "modules.admin",
            "control": "modules.control",
        }
        targets = _target_modules()
        for mid, import_name in module_map.items():
            if targets and mid not in targets:
                continue
            with self.subTest(module=mid):
                self._boot_module(import_name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
