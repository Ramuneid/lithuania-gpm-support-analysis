import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from growth_analysis import build_growth_analysis, growth_table


class GrowthTests(unittest.TestCase):
    def test_fixed_endpoints_gaps_and_short_histories(self):
        data = pd.DataFrame([
            (1, "Old name", 2020, 1000), (1, "New name", 2021, 1200),
            (1, "New name", 2023, 1800), (1, "New name", 2025, 2000),
            (2, "New recipient", 2024, 1000), (2, "New recipient", 2025, 2000),
            (3, "Single year", 2025, 1000),
            (4, "Zero baseline", 2020, 0), (4, "Zero baseline", 2025, 1000),
            (5, "Zero ending", 2020, 1000), (5, "Zero ending", 2025, 0),
            (6, "Missing amount", 2020, np.nan), (6, "Missing amount", 2025, 1000),
            (7, "Zero baseline", 2020, 1000), (7, "Zero baseline", 2025, 2000),
        ], columns=["recipient_code", "recipient_name", "tax_year", "calculated_pmd_eur"])
        annual, summary = build_growth_analysis(data)
        s = summary.set_index("recipient_code")
        a = annual.set_index(["recipient_code", "tax_year"])
        self.assertEqual(len(s), 7)
        self.assertEqual(s.loc[1, "recipient_name"], "New name")
        self.assertAlmostEqual(a.loc[(1, 2021), "yearly_growth_pct"], .2)
        self.assertTrue(pd.isna(a.loc[(1, 2023), "yearly_growth_pct"]))
        self.assertTrue(pd.isna(a.loc[(1, 2023), "yearly_log_growth"]))
        self.assertEqual(s.loc[1, "fixed_period_growth_pct"], 1)
        self.assertAlmostEqual(s.loc[1, "fixed_annualized_growth_pct"], 2 ** .2 - 1)
        self.assertTrue(pd.isna(s.loc[2, "fixed_period_growth_pct"]))
        self.assertEqual(s.loc[2, "observed_annualized_growth_pct"], 1)
        self.assertTrue(pd.isna(s.loc[3, "observed_period_growth_pct"]))
        self.assertEqual(s.loc[3, "history_status"], "Insufficient history")
        self.assertTrue(pd.isna(s.loc[4, "fixed_period_growth_pct"]))
        self.assertEqual(s.loc[5, "fixed_period_growth_pct"], -1)
        self.assertEqual(s.loc[5, "fixed_annualized_growth_pct"], -1)
        self.assertTrue(pd.isna(s.loc[5, "fixed_period_log_growth"]))
        self.assertTrue(pd.isna(s.loc[6, "baseline_amount"]))
        table, names = growth_table(annual, summary)
        self.assertEqual(list(table.columns), [2021, 2022, 2023, 2024, 2025,
                                              "Growth 2020-2025", "Annualized 2020-2025"])
        self.assertEqual(len(table), 7)
        self.assertTrue(table.index.is_unique)
        self.assertFalse(names.is_unique)


if __name__ == "__main__":
    unittest.main()
