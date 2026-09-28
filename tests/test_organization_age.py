import importlib
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
prepare = importlib.import_module("07_prepare_analysis_tables")


class OrganizationAgeTests(unittest.TestCase):
    def test_inconsistent_date_invalidates_all_years_without_changing_funding(self):
        rows = pd.DataFrame([
            (code, year, 100.0, 2)
            for code in ["00123", "123", "missing", "unmatched"]
            for year in [2020, 2022, 2025]
        ], columns=["recipient_code", "tax_year", "calculated_pmd_eur", "requests"])
        metadata = pd.DataFrame({
            "code": ["00123", "123", "missing"],
            "start_date": pd.to_datetime(["2022-04-15", "2020-01-01", None]),
            "organization_start_year": pd.Series([2022, 2020, pd.NA], dtype="Int64"),
        })
        result = prepare.build_recipient_analysis(rows, metadata)
        pd.testing.assert_frame_equal(result[rows.columns], rows)
        bad = result.loc[result.recipient_code.eq("00123")]
        self.assertTrue(bad.organization_age.isna().all())
        self.assertTrue(bad.organization_age_group.eq("Unknown").all())
        self.assertTrue(bad.organization_age_status.eq("Registration date inconsistent").all())
        self.assertTrue(bad.organization_start_date.eq(pd.Timestamp("2022-04-15")).all())
        self.assertTrue(bad.organization_start_year.eq(2022).all())
        good = result.loc[result.recipient_code.eq("123")]
        self.assertEqual(good.organization_age.tolist(), [0, 2, 5])
        self.assertTrue(good.organization_age_status.eq("Available").all())
        missing = result.loc[result.recipient_code.isin(["missing", "unmatched"])]
        self.assertTrue(missing.organization_age.isna().all())
        self.assertTrue(missing.organization_age_group.eq("Unknown").all())
        self.assertTrue(missing.organization_age_status.eq("Registration date missing").all())
        self.assertEqual(str(result.organization_age.dtype), "Int64")
