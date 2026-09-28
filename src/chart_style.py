"""Shared chart styling helpers for project notebooks."""

from __future__ import annotations

import json
import re
import textwrap
from cycler import cycler
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, QuadMesh
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.ticker import Formatter, FuncFormatter, LogLocator, NullFormatter, FixedFormatter, ScalarFormatter
from matplotlib.text import Text
from matplotlib.transforms import IdentityTransform
import numpy as np


def contrast_ratio(first, second):
    """WCAG relative-luminance contrast for opaque sRGB colors."""
    def luminance(color):
        rgb = np.asarray(to_rgb(color))
        linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
        return float(linear @ [.2126, .7152, .0722])
    a, b = sorted([luminance(first), luminance(second)])
    return (b + .05) / (a + .05)


def contrast_text(background):
    return max(("black", "white"), key=lambda color: contrast_ratio(color, background))


def secondary_text_color(color, background="white"):
    """Lighten the same base color only as far as readable contrast permits."""
    rgb = np.asarray(to_rgb(color))
    for strength in np.linspace(.35, 0, 71):
        tint = rgb + (1 - rgb) * strength
        if contrast_ratio(tint, background) >= 4.5:
            return tuple(tint)
    return tuple(rgb)


def trim_decimal_zeros(label):
    """Strip redundant fractional zeros from formatted display numbers."""
    def trim(match):
        value = match.group().rstrip("0").rstrip(".")
        return "0" if value in ("-0", "\u22120") else value
    return re.sub(r"(?<![\w.])[+\-\u2212]?\d[\d,]*\.\d+(?![\d.])", trim, str(label))


def format_number(value, decimals=1, *, suffix="", signed=False):
    """Readable presentation numbers; retain tiny nonzero values."""
    if not np.isfinite(value):
        return "Unavailable"
    precision = decimals
    if value and round(value, precision) == 0:
        precision = max(precision, int(-np.floor(np.log10(abs(value)))) + 1)
    number = format(value, f"{'+' if signed else ''},.{precision}f")
    return trim_decimal_zeros(number) + suffix


class _ReadableFormatter(Formatter):
    """Keep locator/scientific-offset behavior of the original formatter."""
    def __init__(self, original):
        self.original = original

    def set_axis(self, axis):
        super().set_axis(axis)
        self.original.set_axis(axis)

    def set_locs(self, locs):
        super().set_locs(locs)
        self.original.set_locs(locs)

    def get_offset(self):
        return self.original.get_offset()

    def __call__(self, value, pos=None):
        return trim_decimal_zeros(self.original(value, pos))


class _ParentheticalText(Text):
    """Use the original Text layout, tinting only explanatory parentheses.

    Matplotlib's pinned Text layout supplies baseline positions for wrapped and
    rotated labels. Keeping this artist retains its normal layout/export bounds.
    """
    def draw(self, renderer):
        value = self.get_text()
        if not self.get_visible() or "(" not in value or "$" in value or re.search(r"\b(?:ln|log|exp)\(", value):
            return super().draw(renderer)
        alpha = self.get_alpha()
        self.set_alpha(0)
        super().draw(renderer)
        self.set_alpha(alpha)
        _, lines, _ = self._get_layout(renderer)
        anchor = self.get_transform().transform(self.get_unitless_position())
        angle = np.deg2rad(self.get_rotation())
        direction = np.array([np.cos(angle), np.sin(angle)])
        background = self.axes.get_facecolor() if self.axes else self.figure.get_facecolor()
        muted = secondary_text_color(self.get_color(), background)
        depth = 0
        for line, _, (x, y) in lines:
            runs = []
            for char in line:
                inside = depth > 0 or char == "("
                if runs and runs[-1][1] == inside:
                    runs[-1] = (runs[-1][0] + char, inside)
                else:
                    runs.append((char, inside))
                depth += (char == "(") - (char == ")" and depth > 0)
            advance = 0
            for run, inside in runs:
                point = anchor + [x, y] + advance * direction
                segment = Text(*point, run, fontproperties=self.get_fontproperties(),
                               color=muted if inside else self.get_color(), alpha=alpha,
                               rotation=self.get_rotation(), rotation_mode="anchor",
                               ha="left", va="baseline", transform=IdentityTransform())
                segment.set_figure(self.figure)
                segment.draw(renderer)
                advance += renderer.get_text_width_height_descent(run, self.get_fontproperties(), False)[0]


def _style_parentheses(fig):
    for artist in fig.findobj(match=Text):
        value = artist.get_text()
        if "(" not in value:
            continue
        if type(artist) is Text:
            artist.__class__ = _ParentheticalText
        elif value.strip().startswith("(") and value.strip().endswith(")"):
            # Standalone Annotation counts keep their existing coordinates.
            artist.set_color(secondary_text_color(artist.get_color(), fig.get_facecolor()))


def _label_line_points(ax):
    """Label marked data series, retaining caller-supplied point annotations."""
    from matplotlib.text import Annotation
    series = []
    for line in ax.lines:
        if (not line.get_visible() or line.get_transform() != ax.transData
                or line.get_marker() in (None, '', ' ', 'None', 'none')
                or line.get_linestyle() in (None, '', ' ', 'None', 'none')):
            continue
        x, y = line.get_data(orig=False)
        points = [(float(a), float(b)) for a, b in zip(x, y)
                  if np.isfinite(a) and np.isfinite(b)]
        if points:
            series.append(points)
    existing = []
    for text in ax.texts:
        if isinstance(text, Annotation) and text.xycoords == 'data':
            try:
                existing.append((float(ax.convert_xunits(text.xy[0])), float(ax.convert_yunits(text.xy[1]))))
            except (TypeError, ValueError):
                pass
    formatter = ax.yaxis.get_major_formatter()
    original = formatter.original if isinstance(formatter, _ReadableFormatter) else formatter
    for index, points in enumerate(series):
        for i, (x, y) in enumerate(points):
            if any(a == x and b == y for a, b in existing):
                continue
            if not (min(ax.get_xlim()) <= x <= max(ax.get_xlim())
                    and min(ax.get_ylim()) <= y <= max(ax.get_ylim())):
                continue
            label = format_number(y, 2) if isinstance(original, ScalarFormatter) else formatter(y)
            if '%' in label:
                label = format_number(y * 100, 1, suffix='%', signed=label.startswith('+'))
            peers = [b for group in series for a, b in group if a == x]
            above = y >= float(np.median(peers))
            offset = 10 if above else -12
            first, last = i == 0, i == len(points) - 1
            annotation = ax.annotate(
                trim_decimal_zeros(label), (x, y),
                xytext=(10 if first else -10 if last else 0, offset),
                textcoords='offset points',
                ha='left' if first else 'right' if last else 'center',
                va='bottom' if above else 'top', fontsize=9,
                color=plt.rcParams['text.color'],
            )
            annotation.set_gid('auto-point-label')
            existing.append((x, y))


def _zero_reference(ax):
    """A faint zero reference on the value axis, without expanding its limits."""
    from matplotlib.container import BarContainer
    bars = [c for c in ax.containers if isinstance(c, BarContainer)]
    horizontal = bool(bars and bars[0].orientation == 'horizontal')
    # Horizontal boxplots already supply an explicit vertical reference.
    for line in ax.lines:
        for transform, values in [(ax.get_yaxis_transform(), line.get_ydata()),
                                  (ax.get_xaxis_transform(), line.get_xdata())]:
            if line.get_transform() == transform:
                try:
                    is_zero = np.asarray(values, dtype=float).size > 0 and np.all(np.asarray(values, dtype=float) == 0)
                except (TypeError, ValueError):
                    is_zero = False
                if is_zero:
                    line.set_color(plt.rcParams['text.color'])
                    line.set_alpha(.25)
                    line.set_linewidth(.8)
                    line.set_zorder(0)
                    return
    scale = ax.get_xscale() if horizontal else ax.get_yscale()
    limits = ax.get_xlim() if horizontal else ax.get_ylim()
    if scale != 'linear' or not min(limits) <= 0 <= max(limits):
        return
    if not (ax.lines or ax.collections or bars):
        return
    draw = ax.axvline if horizontal else ax.axhline
    line = draw(0, color=plt.rcParams['text.color'], alpha=.25, linewidth=.8,
                zorder=0, label='_nolegend_')
    line.set_gid('zero-reference')


def _separate_auto_labels(fig):
    """Move only generated labels when their rendered boxes overlap."""
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        automatic = [t for t in ax.texts if t.get_gid() == 'auto-point-label']
        occupied = [t.get_window_extent(renderer).expanded(1.06, 1.12)
                    for t in ax.texts if t not in automatic and t.get_visible()]
        bounds = ax.get_window_extent(renderer)
        for line in ax.lines:
            if line.get_transform() != ax.transData:
                continue
            x, y = line.get_data(orig=False)
            for a, b in zip(x, y):
                if np.isfinite(a) and np.isfinite(b):
                    px, py = ax.transData.transform((a, b))
                    occupied.append(Bbox.from_extents(px - 5, py - 5, px + 5, py + 5))
        for text in automatic:
            original = text.get_position()
            for shift in [0, 14, -14, 28, -28, 42, -42, 56, -56]:
                text.set_position((original[0], original[1] + shift))
                box = text.get_window_extent(renderer).expanded(1.06, 1.12)
                if (bounds.contains(box.x0, box.y0) and bounds.contains(box.x1, box.y1)
                        and not any(Bbox.overlaps(box, other) for other in occupied)):
                    break
            else:
                text.set_position(original)
                box = text.get_window_extent(renderer).expanded(1.06, 1.12)
            occupied.append(box)


def finish_chart(fig=None, note="", *, point_labels=True, zero_reference=True):
    """Apply common finishing rules without changing plotted observations."""
    from matplotlib.container import BarContainer
    fig = fig or plt.gcf()
    for ax in fig.axes:
        # Keep explicitly requested major reference grids, never add a grid.
        ax.grid(False, which="minor")
        for axis, scale in [(ax.xaxis, ax.get_xscale()), (ax.yaxis, ax.get_yscale())]:
            if scale == "log":
                original = axis.get_major_formatter()
                sample = original(1)
                currency = "EUR" in sample or "\u20ac" in sample or "EUR" in axis.get_label_text()
                axis.set_major_locator(LogLocator(base=10, numticks=8))
                axis.set_minor_formatter(NullFormatter())
                if currency:
                    axis.set_major_formatter(FuncFormatter(
                        lambda value, _: (f"{value:,.0f}" if value >= 1 else f"{value:.2g}") + " EUR"
                    ))
            formatter = axis.get_major_formatter()
            if not isinstance(formatter, (FixedFormatter, _ReadableFormatter)):
                axis.set_major_formatter(_ReadableFormatter(formatter))
        title = ax.get_title(loc="left") or ax.get_title()
        ax.set_title("")
        ax.set_title(textwrap.fill(title, 64 if len(fig.axes) == 1 else 30), loc="left")
        bars = [c for c in ax.containers if isinstance(c, BarContainer)]
        horizontal = bool(bars and bars[0].orientation == "horizontal")
        if bars:
            for i, container in enumerate(bars):
                for bar in container:
                    bar.set_edgecolor("none")
                    bar.set_linewidth(0)
                    bar.set_hatch(None)
                    bar.set_alpha(1)
            legend = ax.get_legend()
            if legend is not None and len(legend.legend_handles) == len(bars):
                for handle, container in zip(legend.legend_handles, bars):
                    if hasattr(handle, "set_hatch") and len(container):
                        handle.set_hatch(container[0].get_hatch())
                        handle.set_edgecolor(container[0].get_edgecolor())
                        handle.set_linewidth(container[0].get_linewidth())
            values = np.concatenate([np.asarray(c.datavalues) for c in bars])
            if np.isfinite(values).any() and np.nanmin(values) >= 0:
                if horizontal:
                    ax.set_xlim(left=0)
                else:
                    ax.set_ylim(bottom=0)
            if horizontal:
                labels = ["\n".join(textwrap.fill(line, 38) for line in t.get_text().splitlines()) for t in ax.get_yticklabels()]
                ax.set_yticks(ax.get_yticks(), labels)
        # Remove decorative outlines, preserving axes and statistical line artists.
        for shape in ax.patches:
            if shape.get_fill() and shape.get_facecolor()[3] > 0:
                shape.set_edgecolor("none")
                shape.set_linewidth(0)
        for collection in ax.collections:
            if isinstance(collection, (PolyCollection, QuadMesh)):
                collection.set_edgecolor("none")
                collection.set_linewidth(0)
        legend = ax.get_legend()
        if legend is not None:
            for handle in legend.legend_handles:
                if isinstance(handle, Patch) and handle.get_fill():
                    handle.set_edgecolor("none")
                    handle.set_linewidth(0)
        if point_labels:
            _label_line_points(ax)
        if zero_reference:
            _zero_reference(ax)
        for text in ax.texts:
            if re.match(r"^[+\-\u2212]?\d", text.get_text()):
                text.set_text(trim_decimal_zeros(text.get_text()))
            if text.get_fontsize() < 9:
                text.set_fontsize(9)
    bottom = .04
    if note:
        wrapped = textwrap.fill(note, max(45, int(fig.get_figwidth() * 12)))
        bottom = (.20 + .15 * len(wrapped.splitlines())) / fig.get_figheight()
        fig.text(.02, .015, wrapped, ha="left", va="bottom", fontsize=9)
    fig.tight_layout(rect=(0, bottom, 1, .93 if fig._suptitle else 1))
    # Fit outside value labels using their actual rendered extent.
    for _ in range(3):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for ax in fig.axes:
            bars = [c for c in ax.containers if isinstance(c, BarContainer)]
            if not bars or not ax.texts:
                continue
            horizontal = bars[0].orientation == "horizontal"
            bounds = ax.get_window_extent(renderer)
            limits = ax.get_xlim() if horizontal else ax.get_ylim()
            low, high = limits
            for label in ax.texts:
                if label.get_transform() != ax.transData and not hasattr(label, "xy"):
                    continue
                box = label.get_window_extent(renderer)
                if horizontal:
                    if box.x1 > bounds.x1:
                        high = max(high, ax.transData.inverted().transform((box.x1 + 8, bounds.y0))[0])
                    if box.x0 < bounds.x0 and limits[0] < 0:
                        low = min(low, ax.transData.inverted().transform((box.x0 - 8, bounds.y0))[0])
                elif box.y1 > bounds.y1:
                    high = max(high, ax.transData.inverted().transform((bounds.x0, box.y1 + 8))[1])
            (ax.set_xlim if horizontal else ax.set_ylim)(low, high)
    _separate_auto_labels(fig)
    _style_parentheses(fig)
    plt.show()


def growth_boxplot(data, group, order, title, note=""):
    """Horizontal distributions with explicit finite-log sample sizes."""
    metric = "whole_period_log_growth"
    arrays = [data.loc[data[group].eq(value), metric].dropna().to_numpy() for value in order]
    arrays = [values[np.isfinite(values)] for values in arrays]
    labels = [textwrap.fill(str(value), 38) + f" (n={len(values):,})"
              for value, values in zip(order, arrays)]
    fig, ax = plt.subplots(figsize=(10, max(5, .42 * len(labels) + 2)))
    ax.boxplot(arrays, vert=False, tick_labels=labels, showfliers=True)
    ax.invert_yaxis()
    ax.axvline(0, color=plt.rcParams["text.color"], linewidth=.8)
    ax.set(title=title, xlabel="Log growth 2020-2025: ln(ending / starting PMD)", ylabel="")
    excluded = len(data) - sum(map(len, arrays))
    finish_chart(fig, f"{note} n = recipients with finite log growth; {excluded:,} unavailable in these groups. "
                 "Boxes: median and middle 50%; whiskers: 1.5 IQR; points: outliers, not confidence intervals.")


def load_chart_style(project_root: Path) -> dict[str, Any]:
    """Load the project chart theme JSON."""
    style_path = project_root / "config" / "chart_style.json"
    with style_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def colors_from_style(style: dict[str, Any]) -> dict[str, str]:
    """Return named color shortcuts from the theme palette."""
    data_colors = style.get("dataColors", [])
    fallback = [
        "#074650",
        "#009292",
        "#fe6db6",
        "#feb5da",
        "#480091",
        "#b66dff",
        "#b5dafe",
        "#6db6ff",
        "#914800",
        "#23fd23",
    ]
    palette = data_colors or fallback

    return {
        "primary": palette[0],
        "secondary": palette[1] if len(palette) > 1 else palette[0],
        "accent": style.get("tableAccent", palette[2] if len(palette) > 2 else palette[0]),
        "highlight": palette[2] if len(palette) > 2 else palette[0],
        "muted": palette[3] if len(palette) > 3 else palette[0],
        "positive": palette[9] if len(palette) > 9 else palette[-1],
        "negative": palette[4] if len(palette) > 4 else palette[0],
        "neutral": palette[3] if len(palette) > 3 else "#F2F2F2",
        "missing": "#F2F2F2",
        "background": style.get("background", "#FFFFFF"),
        "foreground": style.get("foreground", palette[0]),
    }


def growth_cmap_from_style(style: dict[str, Any]) -> LinearSegmentedColormap:
    """Map decline/neutral/growth to theme colors (purple/pink/green)."""
    colors = colors_from_style(style)
    return LinearSegmentedColormap.from_list(
        "project_growth_cmap",
        [colors["negative"], colors["neutral"], colors["positive"]],
    )


def apply_chart_style(style: dict[str, Any]) -> None:
    """Apply the chart theme to Matplotlib defaults."""
    colors = colors_from_style(style)
    palette = style.get("dataColors", [])

    plt.rcParams.update(
        {
            "axes.prop_cycle": cycler(color=palette),
            "figure.facecolor": colors["background"],
            "axes.facecolor": colors["background"],
            "axes.edgecolor": colors["foreground"],
            "axes.labelcolor": colors["foreground"],
            "axes.titlecolor": colors["foreground"],
            "xtick.color": colors["foreground"],
            "ytick.color": colors["foreground"],
            "text.color": colors["foreground"],
            "grid.color": colors["foreground"],
            "grid.alpha": 0.25,
            "axes.grid": False,
            "legend.frameon": False,
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.titlelocation": "left",
            "axes.titlepad": 14,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.axisbelow": True,
            "lines.linewidth": 1.8,
            "lines.markersize": 5,
            "savefig.dpi": 250,
            "savefig.facecolor": colors["background"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "boxplot.boxprops.color": colors["primary"],
            "boxplot.whiskerprops.color": colors["primary"],
            "boxplot.capprops.color": colors["primary"],
            "boxplot.medianprops.color": colors["secondary"],
            "boxplot.flierprops.markeredgecolor": colors["primary"],
        }
    )
