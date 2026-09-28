import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis_helpers import build_top_1_presence, build_top_1_streaks, latest_recipient_names


class IdentityTests(unittest.TestCase):
    def test_rename_duplicates_and_shared_names(self):
        rows = pd.DataFrame([
            (1, "Newest", 2025), (1, "Old", 2020), (1, "Old", 2021),
            (1, "Renamed", 2021), (1, "Renamed", 2022),
            (1, "Renamed", 2023), (1, "Renamed", 2024),
            (2, "Newest", 2025), (3, None, 2025),
        ], columns=["recipient_code", "recipient_name", "tax_year"])
        presence = build_top_1_presence(rows)
        self.assertFalse(presence.duplicated(["recipient_code", "tax_year"]).any())
        summary = build_top_1_streaks(rows).set_index("recipient_code")
        self.assertEqual(len(summary), 3)
        self.assertEqual(summary.loc[1, "longest_consecutive_years"], 6)
        self.assertEqual(summary.loc[1, "years_in_top_1"], 6)
        self.assertEqual(summary.loc[1, "recipient_name"], "Newest")
        self.assertEqual(summary.loc[2, "recipient_name"], "Newest")
        self.assertTrue(pd.isna(summary.loc[3, "recipient_name"]))
        rows.loc[len(rows)] = [1, " ", 2026]
        self.assertEqual(latest_recipient_names(rows).loc[1], "Newest")


if __name__ == "__main__":
    unittest.main()
