import sys
import unittest
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from chart_style import (load_chart_style, colors_from_style, growth_cmap_from_style,
                         contrast_text, contrast_ratio, apply_chart_style, finish_chart)
from chart_style import format_number, trim_decimal_zeros, secondary_text_color, _ParentheticalText
from growth_analysis import render_growth_heatmap


class ChartStyleTests(unittest.TestCase):
    def setUp(self):
        self.style = load_chart_style(Path(__file__).resolve().parents[1])

    def tearDown(self):
        plt.close("all")

    def test_palette_and_gradient_label_contrast(self):
        cmap = growth_cmap_from_style(self.style)
        for fill in self.style["dataColors"] + [cmap(x) for x in np.linspace(0, 1, 256)]:
            self.assertGreaterEqual(contrast_ratio(fill, contrast_text(fill)), 4.5)

    def test_missing_heatmap_values_have_words_and_numeric_alternative(self):
        table = pd.DataFrame({2021: [-1., np.nan], "Growth 2020-2025": [-1., .5],
                              "Annualized 2020-2025": [-1., .1]}, index=["a", "b"])
        html = render_growth_heatmap(table, pd.Series({"a": "A", "b": "B"}),
                                     growth_cmap_from_style(self.style), colors_from_style(self.style)).data
        self.assertIn("Unavailable", html)
        self.assertIn("color: white", html)
        self.assertIn("Exact values without color", html)
        self.assertIn("tabindex='0'", html)
        self.assertIn("-100%", html)

    def test_finish_keeps_values_and_zero_baseline(self):
        apply_chart_style(self.style)
        fig, ax = plt.subplots()
        bars = ax.barh(["A", "B"], [1, 100])
        ax.bar_label(bars, labels=["1 EUR", "100 EUR"], padding=4)
        with patch("matplotlib.pyplot.show"):
            finish_chart(fig, "Test chart")
        self.assertEqual([bar.get_width() for bar in bars], [1, 100])
        self.assertEqual(ax.get_xlim()[0], 0)
        self.assertGreater(ax.get_xlim()[1], 100)

    def test_log_axis_does_not_round_positive_amounts_to_zero(self):
        apply_chart_style(self.style)
        fig, ax = plt.subplots()
        ax.plot([.01, 100], [1, 2])
        ax.set_xscale("log")
        ax.set_xlabel("Calculated PMD, EUR, log scale")
        with patch("matplotlib.pyplot.show"):
            finish_chart(fig)
        self.assertEqual(ax.xaxis.get_major_formatter()(.01), "0.01 EUR")

    def test_readable_numbers_keep_meaningful_decimals(self):
        self.assertEqual(trim_decimal_zeros("70.0M EUR"), "70M EUR")
        self.assertEqual(trim_decimal_zeros("70.80M EUR"), "70.8M EUR")
        self.assertEqual(trim_decimal_zeros("-0.0%"), "0%")
        self.assertEqual(format_number(1234, 2, suffix=" EUR"), "1,234 EUR")
        self.assertEqual(format_number(.001, 1), "0.001")
        self.assertEqual(format_number(35.5, 1, suffix="%"), "35.5%")

    def test_solid_bars_no_grid_and_tinted_parentheses(self):
        apply_chart_style(self.style)
        fig, ax = plt.subplots()
        bars = ax.bar([0, 1], [10, 20], hatch="//", color=self.style["dataColors"][0])
        ax.set_xticks([0, 1], ["1\n(n=123)", "2\n(n=32)"])
        ax.set_xlabel("Streak (n = recipients)")
        ax.grid(False, which="both")
        with patch("matplotlib.pyplot.show"):
            finish_chart(fig)
        fig.canvas.draw()
        self.assertTrue(all(not bar.get_hatch() for bar in bars))
        self.assertTrue(all(not line.get_visible() for line in ax.get_xgridlines() + ax.get_ygridlines()))
        self.assertIsInstance(ax.get_xticklabels()[0], _ParentheticalText)
        self.assertIsInstance(ax.xaxis.label, _ParentheticalText)
        base = self.style["foreground"]
        tint = secondary_text_color(base)
        self.assertGreaterEqual(contrast_ratio(tint, "white"), 4.5)
        self.assertLess(contrast_ratio(tint, "white"), contrast_ratio(base, "white"))

    def test_explicit_major_reference_grid_is_preserved(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])
        ax.grid(True, axis="y", which="major")
        with patch("matplotlib.pyplot.show"):
            finish_chart(fig)
        self.assertTrue(any(line.get_visible() for line in ax.get_ygridlines()))

    def test_light_stacked_bars_and_legend_have_no_outlines(self):
        apply_chart_style(self.style)
        fig, ax = plt.subplots()
        bars = ax.bar([0, 1], [2, 3], color='#b5dafe', edgecolor='black', linewidth=2, label='Small')
        upper = ax.bar([0, 1], [1, 2], bottom=[2, 3], color='#fe6db6', label='Large')
        ax.legend()
        with patch('matplotlib.pyplot.show'):
            finish_chart(fig)
        for shape in list(bars) + list(upper) + ax.get_legend().legend_handles:
            self.assertEqual(shape.get_linewidth(), 0)
            self.assertEqual(shape.get_edgecolor()[3], 0)
        self.assertTrue(ax.spines['left'].get_visible())
        self.assertEqual([bar.get_height() for bar in bars], [2, 3])

    def test_histogram_and_filled_area_outlines_removed(self):
        fig, axes = plt.subplots(1, 2)
        _, _, bins = axes[0].hist([1, 2, 2, 3], edgecolor='white', linewidth=2)
        area = axes[1].fill_between([1, 2], [2, 3], edgecolor='black', linewidth=2)
        reference = axes[1].axhline(1, color='black')
        with patch('matplotlib.pyplot.show'):
            finish_chart(fig)
        self.assertTrue(all(b.get_linewidth() == 0 for b in bins))
        self.assertTrue(np.all(area.get_linewidths() == 0))
        self.assertTrue(reference.get_visible())


if __name__ == "__main__":
    unittest.main()
