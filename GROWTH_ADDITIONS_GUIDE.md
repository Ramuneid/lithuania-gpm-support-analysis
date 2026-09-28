# Three Complementary Views of Funding Growth

This reference explains the three additional growth views implemented in notebook 07: euro changes within growth patterns, contributions to population-level recorded funding, and annual comparisons in a stable sample. The code examples document their construction; the notebook contains the current executable analysis and shared chart styling. These views complement rather than replace the earlier tables and charts.

## 1. Position in the Analysis

The sections appear in `notebooks/07_growth_drivers_analysis.ipynb` before the shorter-history appendix. They depend on the earlier preparation steps and the project's Python environment. Markdown passages explain the comparisons; Python cells construct the tables and figures. Fresh-kernel execution verifies independence from unrecorded interactive state.

The additions use `recipient_year_amounts`, not `growth_driver_table`: the latter excludes recipients without valid fixed endpoints. That restricted table would omit the endpoint-absence groups needed for the population comparison. Monetary values are nominal calculated PMD under the project's correction policy, not necessarily transferred funding.

## 2. Scope and Setup

Section description:

```markdown
## Additional perspectives on funding growth

How much funding changed, which recipients contributed to recorded totals, and whether annual patterns persist in a stable sample are separate questions. These additional views retain the shared legal-form cohort and the existing annual and whole-period analyses.

Recipients are identified by code. Missing observations remain missing. Pattern counts describe frequency, while euro changes describe financial scale; neither establishes causes.
```

Reference implementation:

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from IPython.display import display
from cohort import START_YEAR, END_YEAR
from growth_components import compare_growth_components, GROWTH_PATTERNS

if "recipient_year_amounts" not in globals():
    raise RuntimeError("Run this notebook from the beginning first.")

extra_annual = recipient_year_amounts.loc[
    recipient_year_amounts["tax_year"].between(START_YEAR, END_YEAR)
].copy()
required_years = set(range(START_YEAR, END_YEAR + 1))
if required_years - set(extra_annual["tax_year"]):
    raise ValueError("A required analysis year is missing from the cohort.")
if extra_annual.duplicated(["recipient_code", "tax_year"]).any():
    raise ValueError("Expected one record per recipient code and year.")
values = extra_annual[["amount", "requests"]]
if not np.isfinite(values).all().all() or values.lt(0).any().any():
    raise ValueError("Review missing, nonfinite or negative recorded measures first.")

money_format = "{:,.2f} EUR"
count_format = "{:,.0f}"
```

The validation rejects missing values inside recorded rows. This is different from a recipient having no row in a particular year. Zero amounts remain allowed.

## 3. Euro Changes Within Growth Patterns

Section description:

```markdown
### How much funding changed within each pattern?

For comparable endpoints, the table shows unique recipients, starting funding, ending funding and the net euro change within each group. Growing recipients retain the existing three patterns. Declining and unchanged recipients appear separately.

These are changes within groups, not amounts caused by requests or funding per request. Recipients without a valid requests/per-request comparison are reported separately. In particular, a zero-request endpoint can prevent this comparison even when funding change itself is measurable.
```

Reference implementation:

```python
extra_components = compare_growth_components(
    extra_annual, START_YEAR, END_YEAR
)
extra_available = extra_components["comparison_status"].eq("Available")
extra_comparable = extra_components.loc[extra_available].copy()
extra_comparable["euro_group"] = extra_comparable["growth_pattern"]
extra_comparable.loc[
    extra_comparable["end_amount"].lt(extra_comparable["start_amount"]),
    "euro_group",
] = "Funding decreased"
extra_comparable.loc[
    extra_comparable["end_amount"].eq(extra_comparable["start_amount"]),
    "euro_group",
] = "Funding unchanged"
extra_comparable["change_eur"] = (
    extra_comparable["end_amount"] - extra_comparable["start_amount"]
)
extra_group_order = GROWTH_PATTERNS + ["Funding decreased", "Funding unchanged"]
pattern_euros = (
    extra_comparable.groupby("euro_group")
    .agg(
        unique_recipients=("recipient_code", "nunique"),
        starting_funding_eur=("start_amount", "sum"),
        ending_funding_eur=("end_amount", "sum"),
        change_eur=("change_eur", "sum"),
    )
    .reindex(extra_group_order, fill_value=0)
)
assert pattern_euros["unique_recipients"].sum() == len(extra_comparable)
assert np.isclose(
    pattern_euros["change_eur"].sum(),
    extra_comparable["end_amount"].sum() - extra_comparable["start_amount"].sum(),
    rtol=0, atol=0.01,
)
print(f"Comparable recipients: {len(extra_comparable):,}; {START_YEAR}-{END_YEAR}")
display(pattern_euros.style.format({
    "unique_recipients": count_format,
    **{c: money_format for c in pattern_euros if c != "unique_recipients"},
}))
print("Excluded from the requests/per-request comparison:")
pattern_unavailable = (
    extra_components.loc[~extra_available]
    .groupby("comparison_status")
    .agg(unique_recipients=("recipient_code", "nunique"))
)
display(pattern_unavailable)
assert len(extra_comparable) + pattern_unavailable["unique_recipients"].sum() == len(extra_components)
```

The euro-change chart complements the original count chart. This reference example illustrates the plotted measures; the notebook uses the current shared presentation helpers:

```python
plot_euros = pattern_euros.iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(
    plot_euros.index, plot_euros["change_eur"],
    color=[CHART_COLORS["negative"] if v < 0 else CHART_COLORS["primary"]
           for v in plot_euros["change_eur"]],
)
ax.bar_label(bars, labels=[f"{v:+,.0f} EUR" for v in plot_euros["change_eur"]], padding=4)
ax.axvline(0, color="black", linewidth=0.8)
ax.margins(x=0.30)
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1_000_000:.1f}M"))
ax.set_title(f"Recorded funding change within each pattern, {START_YEAR}-{END_YEAR}")
ax.set_xlabel("Net change in calculated PMD, million EUR")
ax.set_ylabel("")
plt.tight_layout()
plt.show()
```

Read the count and euro charts together. A more frequent pattern need not have the largest euro increase. Net changes can also be dominated by a few large recipients; this table does not quantify their causal contributions.

## 4. Population-Level Recorded Funding

Section description:

```markdown
### What explains the difference between the recorded endpoint totals?

The full cohort is grouped by recorded presence at both endpoints, only the start, only the end, or neither endpoint. Recipients with recorded zero funding remain included.

The contribution column reconciles the difference between recorded totals. For start-only recipients it subtracts their recorded starting funding; for end-only recipients it adds their recorded ending funding. This is accounting for observed records, not an assumption that an absent recipient received zero, and not an individual growth rate.

End-only presence does not prove a new organization was established. Start-only presence does not prove closure. Recipients present only in intermediate years remain visible in the neither-endpoint group.
```

Reference implementation:

```python
endpoint_presence = pd.DataFrame({
    "recipient_code": extra_annual["recipient_code"].unique()
})
for year, label in [(START_YEAR, "start"), (END_YEAR, "end")]:
    endpoint = extra_annual.loc[
        extra_annual["tax_year"].eq(year), ["recipient_code", "amount"]
    ].rename(columns={"amount": f"{label}_funding_eur"})
    endpoint[f"{label}_present"] = True
    endpoint_presence = endpoint_presence.merge(
        endpoint, on="recipient_code", how="left", validate="one_to_one"
    )
    endpoint_presence[f"{label}_present"] = endpoint_presence[f"{label}_present"].eq(True)

start_present = endpoint_presence["start_present"]
end_present = endpoint_presence["end_present"]
presence_order = ["Both endpoints", "Start only", "End only", "Neither endpoint"]
endpoint_presence["recorded_presence"] = np.select(
    [start_present & end_present, start_present & ~end_present, ~start_present & end_present],
    presence_order[:3], default=presence_order[3],
)
population_funding = (
    endpoint_presence.groupby("recorded_presence")
    .agg(
        unique_recipients=("recipient_code", "nunique"),
        start_funding_eur=("start_funding_eur", lambda s: s.sum(min_count=1)),
        end_funding_eur=("end_funding_eur", lambda s: s.sum(min_count=1)),
    )
    .reindex(presence_order)
)
population_funding["unique_recipients"] = population_funding["unique_recipients"].fillna(0).astype(int)
# Zeros here represent no recorded contribution to an aggregate, not imputed funding.
# The recipient-level endpoint amounts and displayed funding columns stay missing.
population_funding["contribution_to_recorded_change_eur"] = (
    population_funding["end_funding_eur"].fillna(0)
    - population_funding["start_funding_eur"].fillna(0)
)
start_total = extra_annual.loc[extra_annual["tax_year"].eq(START_YEAR), "amount"].sum()
end_total = extra_annual.loc[extra_annual["tax_year"].eq(END_YEAR), "amount"].sum()
assert population_funding["unique_recipients"].sum() == extra_annual["recipient_code"].nunique()
assert np.isclose(population_funding["start_funding_eur"].sum(), start_total, rtol=0, atol=0.01)
assert np.isclose(population_funding["end_funding_eur"].sum(), end_total, rtol=0, atol=0.01)
assert np.isclose(
    population_funding["contribution_to_recorded_change_eur"].sum(),
    end_total - start_total, rtol=0, atol=0.01,
)
print(f"Start = {START_YEAR}; end = {END_YEAR}")
display(population_funding.style.format({
    "unique_recipients": count_format,
    **{c: money_format for c in population_funding if c != "unique_recipients"},
}, na_rep="Not recorded"))
print(f"Recorded total: {start_total:,.2f} EUR -> {end_total:,.2f} EUR")
print(f"Difference between recorded totals: {end_total - start_total:+,.2f} EUR")
```

The assertions check that all recipient codes are counted once and that the table reconciles to the two actual annual funding totals. The count in Both endpoints need not equal the fixed-percentage-growth sample: a recorded zero baseline is included here but cannot have a percentage growth rate.

## 5. Available-Pair and Stable-Sample Comparisons

Section description:

```markdown
### Do annual patterns persist when the eligible recipients stay fixed?

The available-pair view uses all recipients with valid data for each consecutive-year comparison. The stable sample is the intersection of recipients with valid requests/per-request comparisons in every annual pair across the analysis period. It is not a top-1% or persistent-top-1% sample.

Stable-sample membership is fixed, but the recipients whose funding grows can still change by year. The comparison therefore includes growing, declining and unchanged counts as well as pattern shares among growing recipients. Eligibility requires positive requests at both endpoints and a positive starting amount for each pair; a recorded zero ending amount is allowed by the shared helper.

The stable sample favors longer observed histories. Differences from the available-pair results indicate sensitivity to sample composition, not proof of a causal explanation.
```

Reference implementation:

```python
extra_pair_results = {}
eligible_sets = []
for year in range(START_YEAR, END_YEAR):
    pair = compare_growth_components(extra_annual, year, year + 1)
    extra_pair_results[f"{year}-{year + 1}"] = pair
    eligible_sets.append(set(pair.loc[
        pair["comparison_status"].eq("Available"), "recipient_code"
    ]))
stable_codes = set.intersection(*eligible_sets)
print(f"Recipients valid for every consecutive-year comparison: {len(stable_codes):,}")

coverage_rows, share_rows, exclusion_rows = [], [], []
for period, pair in extra_pair_results.items():
    excluded = pair.loc[~pair["comparison_status"].eq("Available")]
    for reason, group in excluded.groupby("comparison_status"):
        exclusion_rows.append({"period": period, "reason": reason,
                               "unique_recipients": group["recipient_code"].nunique()})
    available = pair.loc[pair["comparison_status"].eq("Available")]
    stable = pair.loc[pair["recipient_code"].isin(stable_codes)]
    assert stable["comparison_status"].eq("Available").all()
    for sample, frame in [("Available pair", available), ("Stable sample", stable)]:
        delta = frame["end_amount"] - frame["start_amount"]
        growing = frame.loc[delta.gt(0)]
        coverage_rows.append({
            "period": period, "sample": sample,
            "comparable_recipients": len(frame), "growing": int(delta.gt(0).sum()),
            "declining": int(delta.lt(0).sum()), "unchanged": int(delta.eq(0).sum()),
        })
        counts = growing["growth_pattern"].value_counts().reindex(GROWTH_PATTERNS, fill_value=0)
        assert counts.sum() == len(growing)
        for pattern, count in counts.items():
            share_rows.append({
                "period": period, "sample": sample, "pattern": pattern,
                "share": count / len(growing) if len(growing) else np.nan,
            })

annual_sample_coverage = pd.DataFrame(coverage_rows).set_index(["period", "sample"])
assert annual_sample_coverage[["growing", "declining", "unchanged"]].sum(axis=1).eq(
    annual_sample_coverage["comparable_recipients"]
).all()
assert annual_sample_coverage.xs("Stable sample", level="sample")[
    "comparable_recipients"
].eq(len(stable_codes)).all()
annual_sample_shares = pd.DataFrame(share_rows).pivot(
    index=["period", "pattern"], columns="sample", values="share"
).reindex(columns=["Available pair", "Stable sample"])
annual_sample_shares["stable_minus_available_pp"] = 100 * (
    annual_sample_shares["Stable sample"] - annual_sample_shares["Available pair"]
)
display(annual_sample_coverage)
print("Unavailability in the full cohort for each pair (including recipients absent at both endpoints):")
display(pd.DataFrame(exclusion_rows, columns=["period", "reason", "unique_recipients"]))
display(annual_sample_shares.style.format({
    "Available pair": "{:.1%}", "Stable sample": "{:.1%}",
    "stable_minus_available_pp": "{:+.1f} pp",
}, na_rep="No growing recipients"))
```

The additional comparison chart uses the annual shares calculated above:

```python
fig, axes = plt.subplots(1, len(GROWTH_PATTERNS), figsize=(15, 4), sharey=True)
for ax, pattern in zip(axes, GROWTH_PATTERNS):
    chart = annual_sample_shares.xs(pattern, level="pattern")
    for sample, color in [("Available pair", CHART_COLORS["primary"]),
                          ("Stable sample", CHART_COLORS["secondary"])]:
        ax.plot(chart.index, chart[sample], marker="o", color=color, label=sample)
    ax.set_title(pattern, fontsize=10)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.tick_params(axis="x", rotation=45)
    ax.set_xlabel("Consecutive-year comparison")
axes[0].set_ylabel("Share of comparable growing recipients")
axes[-1].legend()
fig.suptitle("Annual growth-pattern shares: available and stable samples")
plt.tight_layout()
plt.show()
```

If there are no stable recipients, their shares remain unavailable, rather than displaying misleading zeros. Percentage-point differences compare shares: 53% minus 40% is +13 percentage points, not +13% relative growth.

## 6. Interpretation Across Views

```markdown
### Reading these views together

The population table accounts for the change in recorded funding totals. Pattern tables distinguish frequency from euro scale within comparable recipients. The stable-sample view checks whether annual pattern shares depend on which recipients can be compared.

Amounts, recipient counts and availability tables provide complementary evidence. A frequent pattern need not contribute the most euros, and a stable overall mix does not mean each recipient followed the same pattern each year. Missing observations do not establish zero funding, organizational entry or closure.
```

These statements explain interpretation limits rather than asserting numerical findings. Numerical conclusions depend on the executed outputs.

## 7. Verification

Verification checks fresh-kernel execution, reconciliation assertions and stable-sample eligibility across annual pairs. Population totals reconcile to the same filtered cohort, not the all-source totals in notebook 01. The stable sample's comparable-recipient count remains fixed while its growing-recipient count may vary. Earlier count and annual charts remain complementary outputs.

The full verification command assumes saved notebook edits and closed notebook editors:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 src\08_verify_reproducibility.py
```

`outputs/reproducibility_report.json` records the verification outcome. A successful run saves refreshed notebooks to disk; an older editor copy is not the verified version.
