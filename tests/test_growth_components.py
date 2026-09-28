import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from growth_components import compare_growth_components, GROWTH_PATTERNS


class ComponentTests(unittest.TestCase):
    def test_patterns_coverage_and_accounting_identity(self):
        rows = []
        for code, amount, requests in [("a", 200, 20), ("b", 200, 10),
                                        ("c", 400, 20), ("d", 0, 0),
                                        ("e", 50, 10), ("f", 0, 10)]:
            rows.extend([(code, code, 2020, 100, 10), (code, code, 2025, amount, requests)])
        rows.append(("g", "g", 2020, 100, 10))
        annual = pd.DataFrame(rows, columns=["recipient_code", "recipient_name", "tax_year", "amount", "requests"])
        result = compare_growth_components(annual).set_index("recipient_code")
        self.assertEqual(result.loc[["a", "b", "c"], "growth_pattern"].tolist(), GROWTH_PATTERNS)
        self.assertEqual(result.loc["d", "growth_pattern"], "Not comparable")
        self.assertEqual(result.loc["g", "comparison_status"], "Missing endpoint data")
        self.assertEqual(result.loc["f", "amount_growth_pct"], -1)
        valid = result.loc[result.comparison_status.eq("Available")]
        identity = (1 + valid.requests_growth_pct) * (1 + valid.amount_per_request_growth_pct) - 1
        pd.testing.assert_series_equal(identity, valid.amount_growth_pct, check_names=False)
        with self.assertRaises(ValueError):
            compare_growth_components(pd.concat([annual, annual.iloc[[0]]]))
