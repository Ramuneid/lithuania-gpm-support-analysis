import unittest
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from chart_style import _label_line_points, _zero_reference


class PointLabelsTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_labels_preserve_manual_and_skip_missing(self):
        fig, ax = plt.subplots()
        ax.plot([2020, 2021, 2022], [.1, np.nan, -.2], marker='o')
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:.1%}'))
        manual = ax.annotate('10%', (2020, .1), xytext=(12, 10), textcoords='offset points')
        _label_line_points(ax)
        _label_line_points(ax)
        self.assertEqual(len(ax.texts), 2)
        self.assertEqual(manual.get_position(), (12, 10))
        self.assertEqual(ax.texts[-1].get_text(), '-20%')

    def test_zero_does_not_change_limits_or_duplicate(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [-1, 1], marker='o')
        limits = ax.get_ylim()
        _zero_reference(ax)
        _zero_reference(ax)
        self.assertEqual(len(ax.lines), 2)
        self.assertEqual(ax.get_ylim(), limits)
        self.assertEqual(ax.lines[-1].get_alpha(), .25)

    def test_positive_zoom_and_log_excluded(self):
        for scale in ['linear', 'log']:
            fig, ax = plt.subplots()
            ax.plot([1, 2], [10, 20], marker='o')
            ax.set_yscale(scale)
            _zero_reference(ax)
            self.assertEqual(len(ax.lines), 1)

    def test_horizontal_and_existing_reference(self):
        fig, ax = plt.subplots()
        ax.barh(['a', 'b'], [-1, 2])
        reference = ax.axvline(0)
        _zero_reference(ax)
        self.assertEqual(len(ax.lines), 1)
        self.assertEqual(reference.get_alpha(), .25)

    def test_scatter_and_boxplot_not_labeled(self):
        fig, ax = plt.subplots()
        ax.scatter([1, 2], [3, 4])
        ax.boxplot([[1, 2, 3, 100]])
        _label_line_points(ax)
        self.assertEqual(len(ax.texts), 0)


if __name__ == '__main__':
    unittest.main()
