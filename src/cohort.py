"""Shared population rule for comparable recipient analyses."""

import pandas as pd
from IPython.display import display

START_YEAR = 2020
END_YEAR = 2025
LEGAL_FORM_REFERENCE_YEAR = 2025
COHORT_LABEL = "Legal forms observed in 2025"


def filter_recipient_cohort(data, start=START_YEAR, end=END_YEAR,
                            reference_year=LEGAL_FORM_REFERENCE_YEAR):
    if not start <= reference_year <= end:
        raise ValueError("Reference year must fall within the analysis period.")
    rows = data.copy()
    rows["tax_year"] = pd.to_numeric(rows["tax_year"], errors="coerce")
    rows["calculated_pmd_eur"] = pd.to_numeric(rows["calculated_pmd_eur"], errors="coerce")
    rows["legal_form_clean"] = rows["legal_form"].astype("string").str.strip().replace("", pd.NA)
    rows = rows.loc[rows["tax_year"].between(start, end)].copy()
    reference = rows.loc[rows["tax_year"].eq(reference_year), "legal_form_clean"].dropna()
    if reference.empty:
        raise ValueError(f"No known legal forms found in reference year {reference_year}.")
    keep = rows["legal_form_clean"].isin(reference.unique())
    included, excluded = rows.loc[keep].copy(), rows.loc[~keep].copy()
    annual = pd.DataFrame(index=pd.Index(range(start, end + 1), name="tax_year"))
    for label, frame in [("all", rows), ("included", included), ("excluded", excluded)]:
        grouped = frame.groupby("tax_year")
        annual[f"{label}_recipients"] = grouped["recipient_code"].nunique().reindex(annual.index, fill_value=0)
        annual[f"{label}_rows"] = grouped.size().reindex(annual.index, fill_value=0)
        annual[f"{label}_pmd_eur"] = grouped["calculated_pmd_eur"].sum(min_count=1).reindex(annual.index, fill_value=0)
    annual["excluded_pmd_share"] = annual["excluded_pmd_eur"] / annual["all_pmd_eur"].where(annual["all_pmd_eur"] > 0)
    annual["missing_amount_rows"] = rows["calculated_pmd_eur"].isna().groupby(rows["tax_year"]).sum().reindex(annual.index, fill_value=0)
    excluded["exclusion_reason"] = "Not observed in reference year"
    excluded.loc[excluded["legal_form_clean"].isna(), "exclusion_reason"] = "Missing legal form"
    forms = excluded.groupby(["legal_form_clean", "exclusion_reason"], dropna=False).agg(
        recipients=("recipient_code", "nunique"),
        rows=("recipient_code", "size"),
        pmd_eur=("calculated_pmd_eur", lambda s: s.sum(min_count=1)),
    ).reset_index()
    changed_codes = rows.groupby("recipient_code")["legal_form_clean"].nunique()
    changes = rows.loc[rows["recipient_code"].isin(changed_codes[changed_codes > 1].index),
                       ["recipient_code", "recipient_name", "tax_year", "legal_form_clean"]].copy()
    changes["included_in_cohort"] = keep.loc[changes.index]
    changes = changes.sort_values(["recipient_code", "tax_year"])
    return included, annual.reset_index(), forms, changes


def show_cohort_report(annual, excluded_forms, changes):
    print(f"{COHORT_LABEL}; analysis years {START_YEAR}-{END_YEAR}.")
    print("Filtering applies to recipient-year legal forms, not survival of each recipient in 2025.")
    print("Yearly inclusion and exclusion totals (amounts sum known values):")
    formats = {c: "{:,.2f}" for c in annual.columns if c.endswith("_eur")}
    formats["excluded_pmd_share"] = "{:.2%}"
    display(annual.style.format(formats, na_rep="Unavailable"))
    print("Excluded legal forms; absence is not evidence of legal ineligibility:")
    display(excluded_forms.style.format({"pmd_eur": "{:,.2f}"}, na_rep="Missing legal form", escape="html"))
    print(f"Recipients with multiple recorded legal forms: {changes['recipient_code'].nunique():,}")
    print("The full legal_form_changes table retains every affected recipient-year; preview:")
    display(changes.head(30))
    print("A recipient can appear in both inclusion groups within a year if its source records have different forms.")
