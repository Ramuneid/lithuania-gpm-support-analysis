import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis_helpers import load_vmi_support_by_recipient, prepare_top_1_dataset, build_top_1_presence, build_top_1_streaks
from growth_analysis import build_growth_analysis

prepare = importlib.import_module("07_prepare_analysis_tables")
clean_vmi = importlib.import_module("03_clean_vmi")


class IdentifierLoadingTests(unittest.TestCase):
    def test_csv_grouping_growth_and_age_join_preserve_distinct_codes(self):
        codes = ["00123", "123", "A-001"]
        rows = pd.DataFrame([
            (year, code, code, "City", "Association", 2, 100.)
            for year in range(2020, 2026) for code in codes
        ], columns=["tax_year", "recipient_code", "recipient_name", "recipient_municipality",
                    "legal_form", "requests", "calculated_pmd_eur"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data/interim").mkdir(parents=True)
            rows.to_csv(root / "data/interim/vmi_support_by_recipient.csv", index=False)
            loaded = load_vmi_support_by_recipient(root)
            self.assertEqual(str(loaded.recipient_code.dtype), "string")
            self.assertEqual(set(loaded.recipient_code), set(codes))
            _, top, _ = prepare_top_1_dataset(loaded, percentile=0)
            streaks = build_top_1_streaks(build_top_1_presence(top))
            self.assertEqual(len(streaks), 3)
            self.assertTrue(streaks.longest_consecutive_years.eq(6).all())
            _, summary = build_growth_analysis(loaded)
            self.assertEqual(set(summary.recipient_code), set(codes))
            metadata = pd.DataFrame({"code": pd.Series(codes, dtype="string"),
                "start_date": ["2000-01-01", "2010-01-01", "2020-01-01"],
                **{field: [None] * 3 for field in ["director", "leader_gender", "address", "mobile_phone", "website"]}})
            with patch.object(prepare, "OUTPUTS_DIR", root / "outputs"):
                processed = prepare.build_recipient_analysis(prepare.prepare_vmi(loaded), prepare.prepare_rekvizitai(metadata))
            processed.to_csv(root / "recipient_analysis.csv", index=False)
            ages = pd.read_csv(root / "recipient_analysis.csv", dtype={"recipient_code": "string"})
            merged = top.merge(ages[["recipient_code", "tax_year", "organization_age"]],
                               on=["recipient_code", "tax_year"], validate="one_to_one")
            self.assertEqual(len(merged), len(rows))
            self.assertEqual(merged.calculated_pmd_eur.sum(), rows.calculated_pmd_eur.sum())
            self.assertEqual(merged.loc[merged.tax_year.eq(2025)].set_index("recipient_code").organization_age.to_dict(),
                             {"00123": 25, "123": 15, "A-001": 5})

    def test_excel_text_codes_survive_numeric_looking_column(self):
        records = [[None] * 11 for _ in range(7)]
        records[4][0] = "Updated"
        records[4][8] = 200
        for code in ["00123", "123"]:
            records.append(["City", code, "Name", "Association", 2, 2, 2, 100, 100, None, None])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.xlsx"
            pd.DataFrame(records).to_excel(path, sheet_name="2025", header=False, index=False)
            with pd.ExcelFile(path) as workbook:
                result = clean_vmi.clean_year_sheet(workbook, "2025")
            self.assertEqual(result.recipient_code.tolist(), ["00123", "123"])
