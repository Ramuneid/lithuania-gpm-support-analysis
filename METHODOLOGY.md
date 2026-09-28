# Analysis Methodology

This page summarizes the implemented rules for the 2020-2025 analysis. It describes calculations, not causal conclusions or legal eligibility. Values are calculated PMD in nominal euros, not necessarily amounts ultimately transferred.

## Records and Population

- The unit of source data is one recipient-year. Organizations are identified by text `recipient_code`, not name; names are display labels. Unique-recipient counts must not be confused with recipient-year counts.
- Whole-dataset exploratory tables may include all cleaned records. Top-1% analyses and the growth sections use the shared cohort: 2020-2025 recipient-year records whose legal form is observed in 2025. Missing or excluded forms are reported.
- This rule applies to each record's legal form. It does not require the individual recipient to survive until 2025, and absence of a form does not prove legal ineligibility.
- Municipality means the recipient organization's recorded location, not supporters' residence. No municipality demographic denominators are used.

Implementation: [cohort.py](src/cohort.py), [analysis_helpers.py](src/analysis_helpers.py).

## Annual Top 1%

Each year's threshold is the 99th percentile of **positive adjusted PMD amounts within the cohort**, calculated using pandas' default linear interpolation. Selection includes all positive amounts greater than or equal to that year's threshold. Zeros do not enter the percentile calculation.

Ties at the threshold are all included; rounding and ties mean the selected share need not be exactly 1%. A year with no positive amounts has no threshold or selected recipients. Missing calendar years are not invented.

Persistent recipients in notebook 05 qualify in all six years, 2020-2025. Streaks require consecutive calendar years. Notebook 06's "other" group includes all nonpersistent 2025 top-1% recipients, not only newcomers. A newcomer is first observed in the top 1% in 2025 within this dataset, not necessarily for the first time ever.

Qualifying-year totals count only years in the top 1%. Full-period totals count all available cohort records for the same recipients. These totals overlap and must not be added together.

## Zero-Request Correction

After reconciling original amounts to the source workbook, step 03 sets positive PMD to zero wherever requests equal zero. Requests remain zero and the recipient-year record is retained. This is the project's explicit analysis policy, not an amendment to the published source.

Original and corrected values are retained in [vmi_zero_request_corrections.csv](outputs/vmi_zero_request_corrections.csv). The [yearly adjustment report](outputs/vmi_zero_request_adjustments_by_year.csv) reconciles source amounts minus corrections to analysis amounts. Raw files are unchanged.

## Growth and Missing Years

Let `A0` be starting funding and `A1` ending funding. Rates are stored as fractions and formatted as percentages where appropriate.

| Measure | Calculation | Valid comparison |
|---|---|---|
| Annual percentage growth | `A1 / A0 - 1` | Consecutive years; `A0 > 0`, `A1 >= 0` |
| Fixed-period growth | `A2025 / A2020 - 1` | Both endpoints observed; positive baseline, nonnegative ending |
| Annualized fixed-period growth | `(A2025 / A2020) ** (1/5) - 1` | Same endpoint requirements; a compound equivalent, not actual annual history |
| Log growth | `ln(A1 / A0)` | Both amounts strictly positive; annual comparisons also require consecutive years |

Missing records are never automatically zero. Comparisons across gaps are interval growth, not annual growth. Fixed-period growth can be calculated despite missing intermediate years, but those missing annual comparisons remain unavailable. A fall from positive funding to zero is -100% percentage growth and undefined log growth, not zero log growth.

Shorter histories are shown separately with their actual first/last years and duration. One-year histories have no growth estimate. Annualizing shorter histories does not make their calendar periods identical to 2020-2025.

Implementation: [growth_analysis.py](src/growth_analysis.py).

## Funding per Request and Growth Patterns

Annual funding per request is annual PMD divided by annual requests, requiring positive requests. The overall average is summed PMD divided by summed requests for the stated period. The median annual amount per request is the median of valid annual averages, with equal weight per year; it is not the median of individual request amounts. Requests are not assumed to represent unique supporters.

The growth-pattern comparison requires observed endpoints, positive starting PMD, nonnegative ending PMD, and positive requests at both endpoints. Among recipients whose funding increased, classify **more requests only**, **higher funding per request only**, or **both increased**. "Only" means the other measure stayed unchanged or decreased. Shares use comparable growing recipients as the denominator; unavailable comparisons and recipients without funding increases are reported separately.

The same rule applies to any consecutive-year comparison, but its eligible population can change by year. Funding equals requests multiplied by funding per request: growth factors multiply, percentages do not simply add. These are accompanying changes, not causal drivers or baseline predictors.

Implementation: [growth_components.py](src/growth_components.py).

## Organization Age

Age is tax year minus registration year, not exact birthday-based age. If a recipient has funding records before its recorded registration year, its registration date is treated as unreliable for age analysis. Age is unavailable in all years for that recipient, and its age group is Unknown. Funding records and the original registration date are retained. Missing and inconsistent registration dates are distinguished in `organization_age_status`; dates are not automatically corrected.

| Analysis | Age reference |
|---|---|
| Notebook 05 age chart and matching recipient table | First observed top-1% year; 2020 for the six-year persistent group |
| Notebook 06 comparison of 2025 recipients | Age in 2025 |
| Notebook 07 growth-by-age comparison | Latest recorded age, 2025 for the fixed-endpoint sample; recorded in `age_reference_year` |

First observed appearance is not necessarily first-ever appearance. End-of-period age must not be described as age at the start of growth.

## Valid Samples and Reporting

Notebook 07's descriptive analysis table requires valid fixed-period percentage growth. `total_recipients` refers to this endpoint sample, not all source recipients. `valid_log_growth_recipients` counts finite log-growth observations; log means, medians and boxplots use that smaller sample.

Municipality log-growth rankings require **at least 10 valid log-growth recipients**, not merely 10 total recipients. Funding/request totals retain the broader endpoint sample; excluded log observations and municipalities below the minimum remain visible in coverage tables. This minimum is a reporting rule, not a guarantee of statistical significance.

Heatmap previews show the first 30 rows in table order, not a representative sample. Full HTML tables are in `outputs/heatmaps/`; preview colors use the full-table scale. Clipped color intensity does not alter cell values.

The [Validation guide](VALIDATION_GUIDE.md) documents validation and audit outputs. [Reproducibility](REPRODUCIBILITY.md) describes fresh-kernel execution, backups and hashes identifying saved notebooks, data and HTML reports. Successful execution does not establish causal validity.
