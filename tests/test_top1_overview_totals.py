import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analysis_helpers import latest_recipient_names


class Top1OverviewTotalsTests(unittest.TestCase):
    def test_qualifying_and_full_period_totals_share_recipient_population(self):
        data = pd.DataFrame([
            ("001", 2020, 1000., 10), ("001", 2025, 50., 2),
            ("A-2", 2020, 100., 3), ("A-2", 2025, 2000., 20),
            ("other", 2025, 500., 5),
        ], columns=["recipient_code", "tax_year", "calculated_pmd_eur", "requests"])
        data["recipient_name"] = data["recipient_code"]
        data["recipient_municipality"] = "City"
        data["legal_form_clean"] = "Association"
        top = data.loc[data.calculated_pmd_eur.ge(1000)].copy()
        nb = json.loads((ROOT / "notebooks/04_top_1_percent_overview.ipynb").read_text(encoding="utf-8"))
        source = next("".join(c["source"]) for c in nb["cells"]
                      if c["cell_type"] == "code" and "".join(c["source"]).startswith("top_1_unique ="))
        scope = {"df_filtered": data, "top_1_df": top, "pd": pd, "np": np,
                 "latest_recipient_names": latest_recipient_names, "display": lambda *args: None}
        exec(source, scope)
        table = scope["top_1_unique"].set_index("recipient_code")
        self.assertEqual(set(table.index), {"001", "A-2"})
        self.assertEqual(table.pmd_top1_years.sum(), 3000.)
        self.assertEqual(table.pmd_all_years.sum(), 3150.)
        self.assertEqual(table.requests_top1_years.sum(), 30)
        self.assertEqual(table.requests_all_years.sum(), 35)
        self.assertEqual(table.loc["001", "years_in_top1"], "2020")
        self.assertEqual(table.loc["001", "years_observed_all_years"], "2020, 2025")
