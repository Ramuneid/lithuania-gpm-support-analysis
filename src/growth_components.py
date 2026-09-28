"""Descriptive endpoint comparisons of funding, requests and funding per request."""

import numpy as np
import pandas as pd


GROWTH_PATTERNS = [
    "More requests only",
    "Higher funding per request only",
    "Both increased",
]


def compare_growth_components(annual, start=2020, end=2025):
    """Use one row per code/year; never substitute zero for missing endpoints."""
    if end <= start:
        raise ValueError("The ending year must follow the starting year.")
    if annual.duplicated(["recipient_code", "tax_year"]).any():
        raise ValueError("Expected unique recipient-year records.")
    names = annual.sort_values("tax_year").groupby("recipient_code")["recipient_name"].last()
    result = names.to_frame()
    for year, label in [(start, "start"), (end, "end")]:
        endpoint = annual.loc[annual.tax_year.eq(year)].set_index("recipient_code")
        for metric in ["amount", "requests"]:
            result[f"{label}_{metric}"] = endpoint[metric]
    columns = ["start_amount", "end_amount", "start_requests", "end_requests"]
    present = result[columns].notna().all(axis=1)
    finite = np.isfinite(result[columns]).all(axis=1)
    valid = (present & finite & result.start_amount.gt(0) & result.end_amount.ge(0)
             & result.start_requests.gt(0) & result.end_requests.gt(0))
    result["comparison_status"] = "Available"
    result.loc[~valid, "comparison_status"] = "Invalid or zero denominator"
    result.loc[~present, "comparison_status"] = "Missing endpoint data"
    for label in ["start", "end"]:
        result[f"{label}_amount_per_request"] = (
            result[f"{label}_amount"] / result[f"{label}_requests"].where(result[f"{label}_requests"].gt(0))
        )
    for metric in ["amount", "requests", "amount_per_request"]:
        result[f"{metric}_growth_pct"] = (
            result[f"end_{metric}"] / result[f"start_{metric}"].where(result[f"start_{metric}"].gt(0)) - 1
        ).where(valid)
    grew = valid & result.end_amount.gt(result.start_amount)
    more_requests = result.end_requests.gt(result.start_requests)
    # Cross-products avoid division rounding when comparing per-request amounts.
    higher_average = (result.end_amount * result.start_requests).gt(result.start_amount * result.end_requests)
    result["growth_pattern"] = "Not comparable"
    result.loc[valid, "growth_pattern"] = "No funding increase"
    result.loc[grew & more_requests & ~higher_average, "growth_pattern"] = GROWTH_PATTERNS[0]
    result.loc[grew & ~more_requests & higher_average, "growth_pattern"] = GROWTH_PATTERNS[1]
    result.loc[grew & more_requests & higher_average, "growth_pattern"] = GROWTH_PATTERNS[2]
    return result.reset_index()
