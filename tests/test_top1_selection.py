import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis_helpers import prepare_top_1_dataset, build_top_1_presence, build_top_1_streaks


def recipient_rows(yearly_amounts):
    return pd.DataFrame([
        (f"{i:05d}", f"Recipient {i}", year, "Association", amount, 1)
        for year, amounts in yearly_amounts.items()
        for i, amount in enumerate(amounts)
    ], columns=["recipient_code", "recipient_name", "tax_year", "legal_form",
                "calculated_pmd_eur", "requests"])


class Top1SelectionTests(unittest.TestCase):
    def test_thresholds_are_year_specific_not_pooled(self):
        data = recipient_rows({2020: list(range(1, 101)),
                               2025: [n * 1000 for n in range(1, 101)]})
        original = data.copy(deep=True)
        filtered, top, thresholds = prepare_top_1_dataset(data)
        # Linear interpolation: 99 + 0.01 * (100 - 99).
        self.assertAlmostEqual(thresholds.loc[2020], 99.01)
        self.assertAlmostEqual(thresholds.loc[2025], 99010.)
        self.assertEqual(thresholds.name, "top_1_threshold")
        self.assertEqual(top.groupby("tax_year").size().to_dict(), {2020: 1, 2025: 1})
        self.assertEqual(top.set_index("tax_year").calculated_pmd_eur.to_dict(),
                         {2020: 100, 2025: 100000})
        for year, threshold in thresholds.items():
            self.assertTrue(filtered.loc[filtered.tax_year.eq(year), "top_1_threshold"].eq(threshold).all())
        pd.testing.assert_frame_equal(data, original)

    def test_every_recipient_tied_at_threshold_is_included(self):
        data = recipient_rows({2025: list(range(1, 99)) + [100, 100]})
        _, top, thresholds = prepare_top_1_dataset(data)
        self.assertEqual(thresholds.loc[2025], 100)
        self.assertEqual(set(top.recipient_code), {"00098", "00099"})
        self.assertEqual(len(top), 2)  # Ties intentionally permit more than 1%.

    def test_zeros_do_not_lower_threshold_or_enter_top_group(self):
        data = recipient_rows({2025: [0] * 100 + [100, 200]})
        filtered, top, thresholds = prepare_top_1_dataset(data)
        self.assertEqual(len(filtered), 102)  # Zero rows remain in the cohort.
        self.assertAlmostEqual(thresholds.loc[2025], 199.)
        self.assertEqual(top.calculated_pmd_eur.tolist(), [200])

    def test_all_zero_year_has_no_threshold_and_no_selected_recipients(self):
        data = recipient_rows({2020: [0, 0], 2025: [10, 20]})
        filtered, top, thresholds = prepare_top_1_dataset(data)
        self.assertNotIn(2020, thresholds.index)
        self.assertTrue(filtered.loc[filtered.tax_year.eq(2020), "top_1_threshold"].isna().all())
        self.assertEqual(top.tax_year.tolist(), [2025])
        zero_data = recipient_rows({2020: [0], 2025: [0]})
        filtered, top, thresholds = prepare_top_1_dataset(zero_data)
        self.assertEqual(len(filtered), 2)
        self.assertTrue(top.empty)
        self.assertTrue(thresholds.empty)

    def test_missing_calendar_years_are_not_filled_or_joined_into_streaks(self):
        data = recipient_rows({2020: [1, 10], 2022: [2, 20], 2025: [3, 30]})
        filtered, top, thresholds = prepare_top_1_dataset(data)
        self.assertEqual(set(thresholds.index), {2020, 2022, 2025})
        self.assertEqual(len(filtered), 6)
        self.assertEqual(top.tax_year.tolist(), [2020, 2022, 2025])
        streaks = build_top_1_streaks(build_top_1_presence(top))
        self.assertEqual(streaks.years_in_top_1.tolist(), [3])
        self.assertEqual(streaks.longest_consecutive_years.tolist(), [1])

    def test_missing_reference_year_raises_instead_of_using_another_cohort(self):
        data = recipient_rows({2020: [1, 10], 2024: [2, 20]})
        with self.assertRaisesRegex(ValueError, "No known legal forms found in reference year 2025"):
            prepare_top_1_dataset(data)

    def test_single_positive_recipient_is_selected(self):
        _, top, thresholds = prepare_top_1_dataset(recipient_rows({2025: [0, 42]}))
        self.assertEqual(thresholds.loc[2025], 42)
        self.assertEqual(top.recipient_code.tolist(), ["00001"])

    def test_custom_percentile_is_used(self):
        _, top, thresholds = prepare_top_1_dataset(
            recipient_rows({2025: list(range(1, 11))}), percentile=90)
        self.assertAlmostEqual(thresholds.loc[2025], 9.1)
        self.assertEqual(top.calculated_pmd_eur.tolist(), [10])

    def test_excluded_legal_forms_do_not_influence_threshold(self):
        data = recipient_rows({2020: [10, 20], 2025: [10, 20]})
        excluded = pd.DataFrame([("OUT", "Excluded", 2020, "Old form", 1000000, 1)],
                                columns=data.columns)
        filtered, top, thresholds = prepare_top_1_dataset(pd.concat([data, excluded], ignore_index=True))
        self.assertAlmostEqual(thresholds.loc[2020], 19.9)
        self.assertNotIn("OUT", set(filtered.recipient_code))
        self.assertEqual(set(top.recipient_code), {"00001"})


if __name__ == "__main__":
    unittest.main()
