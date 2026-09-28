import sys
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from growth_analysis import render_growth_heatmap, render_short_histories


class HeatmapExportTests(unittest.TestCase):
    def test_full_export_and_bounded_preview(self):
        table = pd.DataFrame({2021: [.1, -.2, .3], "Growth 2020-2025": [1., 2., 9.],
                              "Annualized 2020-2025": [.2, .3, .4]}, index=[1, 2, 3])
        names = pd.Series({1: "First", 2: "Second", 3: "Last <recipient>"})
        cmap = LinearSegmentedColormap.from_list("test", ["red", "white", "green"])
        colors = {"missing": "#eeeeee", "background": "white"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "full.html"
            preview = render_growth_heatmap(table, names, cmap, colors, output_path=path, preview_rows=1).data
            full = path.read_text(encoding="utf-8")
            self.assertIn("Last &lt;recipient&gt;", full)
            self.assertNotIn("Last &lt;recipient&gt;", preview)
            self.assertIn("first 1 of 3", preview)
            self.assertIn("+/-830%", full)
            self.assertIn("+/-830%", preview)
            summary = pd.DataFrame({"recipient_name": ["First", "Second"],
                "first_observed_year": [2021, 2022], "last_observed_year": [2025, 2025],
                "observed_years": [5, 4], "elapsed_years": [4, 3],
                "observed_period_growth_pct": [.1, .2], "observed_annualized_growth_pct": [.02, .06],
                "history_status": ["Available", "Available"]})
            result = render_short_histories(summary, output_path=path, preview_rows=1).data
            self.assertNotIn("Second", result)
            self.assertIn("Second", path.read_text(encoding="utf-8"))
