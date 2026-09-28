import importlib
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
apply_policy = importlib.import_module("03_clean_vmi").apply_zero_request_policy


class ZeroRequestPolicyTests(unittest.TestCase):
    def test_correction_preserves_rows_originals_and_audit(self):
        data = pd.DataFrame({
            "tax_year": [2020, 2020, 2025, 2025],
            "recipient_code": ["001", "002", "001", "002"],
            "requests": [0, 2, 0, 1],
            "calculated_pmd_eur": [12.5, 30., 0., 5.],
        })
        original = data.copy()
        with tempfile.TemporaryDirectory() as folder:
            outputs = Path(folder)
            result = apply_policy(data, outputs)
            pd.testing.assert_frame_equal(data, original)
            self.assertEqual(result.calculated_pmd_eur.tolist(), [0., 30., 0., 5.])
            pd.testing.assert_frame_equal(result.drop(columns="calculated_pmd_eur"), data.drop(columns="calculated_pmd_eur"))
            audit = pd.read_csv(outputs / "vmi_zero_request_corrections.csv")
            self.assertEqual(audit.calculated_pmd_eur.tolist(), [12.5])
            report = pd.read_csv(outputs / "vmi_zero_request_adjustments_by_year.csv")
            self.assertTrue(report.passed.all())
            pd.testing.assert_frame_equal(apply_policy(result, outputs), result)
            self.assertTrue(pd.read_csv(outputs / "vmi_zero_request_corrections.csv").empty)
