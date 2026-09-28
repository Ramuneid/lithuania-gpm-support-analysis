import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_validation import reconcile, validate_recipient_years


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.outputs = Path(self.temp.name)
        self.data = pd.DataFrame({"tax_year": [2024, 2025], "recipient_code": ["001", "001"],
                                  "requests": [2., 3.], "calculated_pmd_eur": [10., 20.],
                                  "recipient_municipality": [None, "City"]})

    def test_missing_metadata_is_retained(self):
        report = validate_recipient_years(self.data, self.outputs, "test")
        self.assertEqual(report.input_rows.sum(), 2)
        self.assertEqual(report.missing_metadata_rows.sum(), 1)

    def test_both_duplicate_types_stop(self):
        for amount, kind in [(10., "Identical copy"), (11., "Conflicting records")]:
            duplicate = self.data.iloc[[0]].copy()
            duplicate["calculated_pmd_eur"] = amount
            with self.assertRaises(ValueError):
                validate_recipient_years(pd.concat([self.data, duplicate], ignore_index=True), self.outputs, "test")
            review = pd.read_csv(self.outputs / "test_duplicate_rows.csv")
            self.assertEqual(set(review.duplicate_type), {kind})

    def test_invalid_measures_stop(self):
        for column, value in [("requests", 1.5), ("calculated_pmd_eur", -1),
                              ("calculated_pmd_eur", float("inf")), ("recipient_code", None)]:
            frame = self.data.copy()
            frame.loc[0, column] = value
            with self.assertRaises(ValueError):
                validate_recipient_years(frame, self.outputs, "test")

    def test_reconciliation_checks_each_year(self):
        reconcile(self.data, self.data.copy(), self.outputs, "test")
        changed = self.data.copy()
        changed["calculated_pmd_eur"] = [11., 19.]
        with self.assertRaises(ValueError):
            reconcile(self.data, changed, self.outputs, "test")


if __name__ == "__main__":
    unittest.main()
