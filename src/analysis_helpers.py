"""Reusable analysis helpers for notebooks.

These helpers keep repeated notebook setup logic in one place while leaving
the notebooks readable and easy to run independently.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from cohort import END_YEAR, LEGAL_FORM_REFERENCE_YEAR, START_YEAR, filter_recipient_cohort


def load_vmi_support_by_recipient(project_root: Path) -> pd.DataFrame:
    """Load and standardize the interim VMI recipient-year table."""
    interim_dir = project_root / "data" / "interim"
    vmi = pd.read_csv(interim_dir / "vmi_support_by_recipient.csv", low_memory=False,
                      dtype={"recipient_code": "string"})

    vmi["tax_year"] = pd.to_numeric(vmi["tax_year"], errors="coerce")
    vmi["recipient_code"] = vmi["recipient_code"].str.strip()
    vmi["requests"] = pd.to_numeric(vmi["requests"], errors="coerce")
    vmi["calculated_pmd_eur"] = pd.to_numeric(vmi["calculated_pmd_eur"], errors="coerce")
    vmi["legal_form_clean"] = vmi["legal_form"].fillna("Unknown").str.strip()

    return vmi


def latest_recipient_names(data: pd.DataFrame) -> pd.Series:
    """Latest nonblank name per code; same-year ties use source row order."""
    names = data[["recipient_code", "recipient_name", "tax_year"]].copy()
    names["tax_year"] = pd.to_numeric(names["tax_year"], errors="coerce")
    names["recipient_name"] = names["recipient_name"].astype("string").str.strip().replace("", pd.NA)
    names = names.dropna(subset=["recipient_code", "tax_year", "recipient_name"])
    return (names.sort_values("tax_year", kind="stable")
            .drop_duplicates("recipient_code", keep="last")
            .set_index("recipient_code")["recipient_name"])


def prepare_top_1_dataset(
    vmi: pd.DataFrame,
    filter_year: int = LEGAL_FORM_REFERENCE_YEAR,
    percentile: float = 99,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Return recipients above each year's percentile threshold."""
    filtered, _, _, _ = filter_recipient_cohort(
        vmi, start=START_YEAR, end=END_YEAR, reference_year=filter_year
    )

    # Calculate a separate threshold for each year.
    positive_rows = filtered.loc[
        filtered["calculated_pmd_eur"] > 0
    ]

    yearly_thresholds = (
        positive_rows.groupby("tax_year")["calculated_pmd_eur"]
        .quantile(percentile / 100)
        .rename("top_1_threshold")
    )

    filtered = filtered.merge(
        yearly_thresholds,
        left_on="tax_year",
        right_index=True,
        how="left",
        validate="many_to_one",
    )

    # Include everyone tied at the threshold.
    top_df = filtered.loc[
        (filtered["calculated_pmd_eur"] > 0)
        & (
            filtered["calculated_pmd_eur"]
            >= filtered["top_1_threshold"]
        )
    ].copy()

    top_df["recipient_name"] = top_df["recipient_code"].map(latest_recipient_names(filtered))
    top_df["pmd_per_request"] = (
        top_df["calculated_pmd_eur"]
        / top_df["requests"].where(top_df["requests"] > 0)
    )

    return filtered, top_df, yearly_thresholds


def build_top_1_presence(top_1_df: pd.DataFrame) -> pd.DataFrame:
    """Return one recipient-year row for top 1% presence calculations."""
    presence = top_1_df[["recipient_code", "recipient_name", "tax_year"]].copy()
    presence["tax_year"] = pd.to_numeric(presence["tax_year"], errors="coerce")
    presence = presence.dropna(subset=["recipient_code", "tax_year"])
    presence["tax_year"] = presence["tax_year"].astype(int)
    names = latest_recipient_names(presence)
    presence = presence.drop_duplicates(["recipient_code", "tax_year"])
    presence["recipient_name"] = presence["recipient_code"].map(names)
    return presence


def longest_consecutive_streak(years: pd.Series) -> int:
    """Calculate the longest consecutive-year streak in a year series."""
    years = sorted(set(years))
    longest = 0
    current = 0
    previous_year = None

    for year in years:
        if previous_year is None or year == previous_year + 1:
            current += 1
        else:
            current = 1

        longest = max(longest, current)
        previous_year = year

    return longest


def build_top_1_streaks(top_1_presence: pd.DataFrame) -> pd.DataFrame:
    """Summarize top 1% presence into recipient-level streak measures."""
    top_1_presence = build_top_1_presence(top_1_presence)
    result = (
        top_1_presence.groupby("recipient_code")
        .agg(
            years_in_top_1=("tax_year", "nunique"),
            longest_consecutive_years=("tax_year", longest_consecutive_streak),
            first_year_in_top_1=("tax_year", "min"),
            last_year_in_top_1=("tax_year", "max"),
            years_list=("tax_year", lambda x: ", ".join(map(str, sorted(x.unique())))),
        )
        .reset_index()
    )
    result.insert(1, "recipient_name", result["recipient_code"].map(latest_recipient_names(top_1_presence)))
    return result
