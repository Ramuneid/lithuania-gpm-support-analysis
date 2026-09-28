import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cohort import filter_recipient_cohort
from analysis_helpers import prepare_top_1_dataset


class CohortTests(unittest.TestCase):
    def test_reference_year_exclusions_and_form_changes(self):
        data = pd.DataFrame([
            (1, "A", 2020, "Association", 10),
            (1, "A", 2025, "Association", 20),
            (2, "B", 2024, "Old form", 30),
            (3, "C", 2020, "Association", 40),
            (4, "D", 2024, "Old form", 50),
            (4, "D", 2025, "Association", 60),
            (5, "E", 2025, None, 70),
            (6, "F", 2026, "Future form", 80),
        ], columns=["recipient_code", "recipient_name", "tax_year", "legal_form", "calculated_pmd_eur"])
        data["requests"] = 1
        kept, yearly, excluded, changes = filter_recipient_cohort(data)
        self.assertEqual(set(kept.recipient_code), {1, 3, 4})
        self.assertEqual(len(kept), 4)
        self.assertEqual(set(changes.recipient_code), {4})
        self.assertEqual(changes.included_in_cohort.tolist(), [False, True])
        self.assertEqual(set(excluded.exclusion_reason), {"Missing legal form", "Not observed in reference year"})
        self.assertTrue((yearly.all_rows == yearly.included_rows + yearly.excluded_rows).all())
        self.assertTrue((yearly.all_pmd_eur == yearly.included_pmd_eur + yearly.excluded_pmd_eur).all())
        filtered, _, _ = prepare_top_1_dataset(data)
        self.assertEqual(set(filtered.index), set(kept.index))
        with self.assertRaises(ValueError):
            filter_recipient_cohort(data.loc[data.tax_year < 2025])


if __name__ == "__main__":
    unittest.main()
