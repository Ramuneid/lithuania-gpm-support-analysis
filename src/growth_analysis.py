"""Comparable annual, fixed-period, and observed-period recipient growth."""

import numpy as np
import pandas as pd
from IPython.display import HTML
from cohort import COHORT_LABEL
from chart_style import contrast_text, format_number
from matplotlib.colors import to_hex


def build_growth_analysis(data, amount_column="calculated_pmd_eur", start=2020, end=2025):
    if end <= start:
        raise ValueError("The end year must follow the start year.")
    data = data.copy()
    for column in ["tax_year", amount_column, "requests"]:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.loc[data["tax_year"].between(start, end)].dropna(
        subset=["recipient_code", "tax_year"]
    )
    data["tax_year"] = data["tax_year"].astype(int)
    names = data.sort_values("tax_year").groupby("recipient_code")["recipient_name"].last()
    measures = {"amount": (amount_column, lambda s: s.sum(min_count=1))}
    if "requests" in data:
        measures["requests"] = ("requests", lambda s: s.sum(min_count=1))
    annual = data.groupby(["recipient_code", "tax_year"], as_index=False).agg(**measures)
    annual = annual.sort_values(["recipient_code", "tax_year"])
    annual["recipient_name"] = annual["recipient_code"].map(names)
    grouped = annual.groupby("recipient_code")
    annual["previous_observed_year"] = grouped["tax_year"].shift()
    annual["previous_year_amount"] = grouped["amount"].shift()
    annual["year_gap"] = annual["tax_year"] - annual["previous_observed_year"]
    current = annual["amount"].where(annual["amount"] >= 0)
    previous = annual["previous_year_amount"].where(annual["previous_year_amount"] > 0)
    ratio = current / previous
    annual["interval_growth_pct"] = ratio - 1
    annual["yearly_growth_pct"] = (ratio - 1).where(annual["year_gap"].eq(1))
    # Log ratios are only defined for strictly positive endpoints.
    annual["yearly_log_growth"] = np.log(ratio.where(ratio > 0)).where(
        annual["year_gap"].eq(1)
    )

    summary = names.to_frame()
    valid = annual.loc[annual["amount"].notna()]
    history = valid.groupby("recipient_code")
    summary["observed_years"] = history["tax_year"].nunique().reindex(summary.index, fill_value=0)
    summary["first_observed_year"] = history["tax_year"].min()
    summary["last_observed_year"] = history["tax_year"].max()
    summary["elapsed_years"] = summary["last_observed_year"] - summary["first_observed_year"]
    summary["first_observed_amount"] = history["amount"].first()
    summary["last_observed_amount"] = history["amount"].last()
    observed_ratio = (
        summary["last_observed_amount"].where(summary["last_observed_amount"] >= 0)
        / summary["first_observed_amount"].where(summary["first_observed_amount"] > 0)
    ).where(summary["elapsed_years"] > 0)
    summary["observed_period_growth_pct"] = observed_ratio - 1
    summary["observed_annualized_growth_pct"] = observed_ratio.pow(
        1 / summary["elapsed_years"].where(summary["elapsed_years"] > 0)
    ) - 1
    summary["history_status"] = "Available"
    summary.loc[observed_ratio.isna(), "history_status"] = "Invalid or zero baseline"
    summary.loc[summary["observed_years"] < 2, "history_status"] = "Insufficient history"
    for year, column in [(start, "baseline_amount"), (end, "endpoint_amount")]:
        summary[column] = annual.loc[annual["tax_year"].eq(year)].set_index("recipient_code")["amount"]
    fixed_ratio = (
        summary["endpoint_amount"].where(summary["endpoint_amount"] >= 0)
        / summary["baseline_amount"].where(summary["baseline_amount"] > 0)
    )
    summary["fixed_period_growth_pct"] = fixed_ratio - 1
    summary["fixed_annualized_growth_pct"] = fixed_ratio.pow(1 / (end - start)) - 1
    summary["fixed_period_log_growth"] = np.log(fixed_ratio.where(fixed_ratio > 0))
    summary["fixed_annualized_log_growth"] = summary["fixed_period_log_growth"] / (end - start)
    summary["fixed_period_status"] = "Available"
    summary.loc[fixed_ratio.isna(), "fixed_period_status"] = "Invalid or zero baseline"
    summary.loc[summary[["baseline_amount", "endpoint_amount"]].isna().any(axis=1),
                "fixed_period_status"] = "Missing endpoint"
    return annual, summary.reset_index()


def growth_table(annual, summary, start=2020, end=2025, logarithmic=False):
    metric = "yearly_log_growth" if logarithmic else "yearly_growth_pct"
    period = "fixed_period_log_growth" if logarithmic else "fixed_period_growth_pct"
    rate = "fixed_annualized_log_growth" if logarithmic else "fixed_annualized_growth_pct"
    ordered = summary.sort_values(period, ascending=False, na_position="last").set_index("recipient_code")
    table = annual.pivot(index="recipient_code", columns="tax_year", values=metric)
    table = table.reindex(index=ordered.index, columns=range(start + 1, end + 1))
    table[f"Growth {start}-{end}"] = ordered[period]
    table[f"Annualized {start}-{end}"] = ordered[rate]
    # Keep codes as internal keys; names are only display labels.
    table.index.name = "Recipient"
    return table, ordered["recipient_name"].fillna("Unnamed recipient")


def _export_preview(full_html, preview_html, output_path, total, shown):
    from html import escape
    from pathlib import Path
    from urllib.parse import quote
    import os

    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                    "<title>Recipient growth analysis</title>"
                    "<style>body{font:14px/1.5 'Segoe UI',sans-serif;color:#000;background:#fff}"
                    "td,th{padding:6px 10px}summary{cursor:pointer}</style></head><body>"
                    + full_html + "</body></html>", encoding="utf-8")
    notebook_dir = Path(__file__).resolve().parents[1] / "notebooks"
    link = quote(os.path.relpath(path, notebook_dir).replace(os.sep, "/"), safe="/.")
    return HTML(f"<p>Preview: first {shown:,} of {total:,} rows in table order. "
                f"<a href='{escape(link, quote=True)}' target='_blank'>Open full HTML table</a> "
                f"({escape(path.name)}).</p>" + preview_html)


def render_growth_heatmap(table, names, cmap, colors, logarithmic=False,
                          output_path=None, preview_rows=30, _period_limit=None):
    from html import escape

    annual_columns, summary_columns = list(table.columns[:-2]), list(table.columns[-2:])
    number_format = (lambda value: format_number(value, 2, signed=True)) if logarithmic else (
        lambda value: format_number(value * 100, 1, suffix="%", signed=True))
    styled = table.style.format(number_format, na_rep="Unavailable")
    values = table[summary_columns[0]].abs().dropna()
    limit = max(1.0, float(values.quantile(0.95))) if not values.empty else 1.0
    if _period_limit is not None:
        limit = _period_limit
    def cell_style(value, bound):
        background = colors["missing"] if pd.isna(value) else to_hex(cmap(np.clip((value / bound + 1) / 2, 0, 1)))
        return f"background-color: {background}; color: {contrast_text(background)}"
    styled = styled.map(lambda value: cell_style(value, 1), subset=annual_columns + [summary_columns[1]])
    styled = styled.map(lambda value: cell_style(value, limit), subset=[summary_columns[0]])
    styled = styled.format_index(lambda code: escape(str(names.loc[code])), axis=0)
    styled = styled.set_properties(**{"text-align": "center", "min-width": "105px", "padding": "6px 10px"})
    styled = styled.set_properties(subset=[summary_columns[0]], **{"border-left": "3px solid #777"})
    styled = styled.set_table_styles([
        {"selector": "", "props": [("border-collapse", "separate"), ("border-spacing", "0")]},
        {"selector": "th", "props": [("color", "black"), ("background-color", colors["background"])]},
        {"selector": "thead", "props": [("position", "sticky"), ("top", "0"), ("z-index", "3")]},
        {"selector": "thead th:first-child", "props": [("position", "sticky"), ("left", "0"), ("z-index", "4")]},
        {"selector": "th.row_heading", "props": [("position", "sticky"), ("left", "0"),
          ("text-align", "left"), ("min-width", "300px"), ("z-index", "2")]},
    ])
    note = COHORT_LABEL + ". "
    note += "Annual columns compare consecutive years only; unavailable comparisons are not zero growth. "
    note += "Theme colors: purple = decline; pale pink = neutral; green = growth. "
    note += ("Annual and annualized color scale: -1 to +1 log units. " if logarithmic else
            "Annual and annualized color scale: -100% to +100%. ")
    note += (f"Total-period color scale: +/-{limit:.2f} log units. " if logarithmic else
             f"Total-period color scale: +/-{limit:.0%}. ")
    note += "Colors saturate at the limits; cell labels retain actual values. Grey = unavailable."
    with pd.option_context("styler.render.max_elements", max(262144, table.size + len(table))):
        html = styled.to_html(max_rows=len(table), max_columns=len(table.columns))
    numeric = table.copy()
    numeric.index = [str(names.loc[code]) for code in table.index]
    numeric_html = numeric.to_html(escape=True, na_rep="Unavailable", float_format=number_format,
                                   classes="growth-numeric")
    result = HTML(f"<p>{note}</p><div tabindex='0' aria-label='Scrollable growth heatmap' "
                  f"style='max-height:650px;max-width:100%;overflow:auto;border:1px solid #ddd'>{html}</div>"
                  "<details><summary>Exact values without color</summary>"
                  "<style>.growth-numeric td{text-align:right}.growth-numeric th{text-align:left}</style>"
                  "<div tabindex='0' style='max-height:650px;overflow:auto;text-align:right'>"
                  + numeric_html + "</div></details>")
    if output_path is not None:
        if preview_rows < 1:
            raise ValueError("preview_rows must be positive.")
        preview = render_growth_heatmap(table.head(preview_rows), names, cmap, colors,
                                        logarithmic, _period_limit=limit)
        return _export_preview(result.data, preview.data, output_path, len(table), min(preview_rows, len(table)))
    return result


def render_short_histories(summary, start=2020, end=2025, output_path=None, preview_rows=30):
    shorter = summary.loc[
        summary["first_observed_year"].ne(start) | summary["last_observed_year"].ne(end),
        ["recipient_name", "first_observed_year", "last_observed_year", "observed_years",
         "elapsed_years", "observed_period_growth_pct", "observed_annualized_growth_pct", "history_status"],
    ].copy()
    shorter.columns = ["Recipient", "First year", "Last year", "Observed years", "Elapsed years",
                       "Observed-period growth", "Annualized observed growth", "History status"]
    styled = shorter.style.hide(axis="index").format({
        "First year": "{:.0f}", "Last year": "{:.0f}", "Observed years": "{:.0f}",
        "Elapsed years": "{:.0f}", "Observed-period growth": "{:.1%}",
        "Annualized observed growth": "{:.1%}",
    }, na_rep="Unavailable", escape="html")
    with pd.option_context("styler.render.max_elements", max(262144, shorter.size + len(shorter))):
        html = styled.to_html(max_rows=len(shorter))
    result = HTML("<div style='max-height:500px;overflow:auto'>" + html + "</div>")
    if output_path is not None:
        if preview_rows < 1:
            raise ValueError("preview_rows must be positive.")
        subset = summary.loc[
            summary["first_observed_year"].ne(start) | summary["last_observed_year"].ne(end)
        ].head(preview_rows)
        preview = render_short_histories(subset, start, end)
        return _export_preview(result.data, preview.data, output_path, len(shorter), len(subset))
    return result
