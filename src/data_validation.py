"""Blocking checks and review files for recipient-year data."""

from datetime import datetime, timezone
import hashlib
import json

import numpy as np
import pandas as pd


def fingerprint(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_status(outputs, stage, status, detail, **extra):
    outputs.mkdir(parents=True, exist_ok=True)
    record = {"status": status, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "detail": detail, **extra}
    (outputs / f"{stage}_validation_status.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )


def validate_recipient_years(data, outputs, stage, requests="requests"):
    outputs.mkdir(parents=True, exist_ok=True)
    required = ["tax_year", "recipient_code", requests, "calculated_pmd_eur"]
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    reasons = pd.Series("", index=data.index)
    codes = data["recipient_code"].astype("string").str.strip()
    reasons.loc[codes.isna() | codes.eq("").fillna(False)] += "Missing recipient code; "
    for column in ["tax_year", requests, "calculated_pmd_eur"]:
        values = pd.to_numeric(data[column], errors="coerce")
        bad = ~np.isfinite(values.astype(float))
        if column == "tax_year":
            bad |= values.mod(1).ne(0) | values.lt(2000) | values.gt(2100)
        else:
            bad |= values.lt(0)
            if column == requests:
                bad |= values.mod(1).ne(0)
        reasons.loc[bad] += f"Invalid {column}; "
            # Retain these records, but export them for source review.
    request_values = pd.to_numeric(data[requests], errors="coerce")
    amount_values = pd.to_numeric(data["calculated_pmd_eur"], errors="coerce")
    zero_requests_positive_amount = data.loc[
        request_values.eq(0) & amount_values.gt(0)
    ].copy()

    review_path = outputs / f"{stage}_zero_requests_positive_amount.csv"
    zero_requests_positive_amount.to_csv(
        review_path, index=False, encoding="utf-8-sig"
    )

    if not zero_requests_positive_amount.empty:
        print(
            f"WARNING: {len(zero_requests_positive_amount):,} records "
            f"have positive funding but zero requests. Review {review_path}"
        )
    invalid = data.loc[reasons.ne("")].copy()
    invalid["validation_issue"] = reasons.loc[invalid.index]
    invalid.to_csv(outputs / f"{stage}_invalid_rows.csv", index=False, encoding="utf-8-sig")
    repeated = data.duplicated(["tax_year", "recipient_code"], keep=False)
    duplicates = data.loc[repeated].copy()
    # Provenance differs even when the business record is an exact copy.
    business = [c for c in data.columns if not c.startswith("source_")]
    variants = data[business].drop_duplicates().groupby(["tax_year", "recipient_code"], dropna=False).size()
    if not duplicates.empty:
        duplicates["duplicate_type"] = [
            "Identical copy" if variants.loc[(row.tax_year, row.recipient_code)] == 1 else "Conflicting records"
            for row in duplicates.itertuples()
        ]
    else:
        duplicates["duplicate_type"] = pd.Series(dtype="string")
    duplicates.to_csv(outputs / f"{stage}_duplicate_rows.csv", index=False, encoding="utf-8-sig")
    metadata = [c for c in ["recipient_name", "recipient_municipality", "legal_form"] if c in data]
    warnings = data.loc[data[metadata].isna().any(axis=1)].copy()
    warnings.to_csv(outputs / f"{stage}_missing_metadata.csv", index=False, encoding="utf-8-sig")
    summary = data.groupby("tax_year", dropna=False).agg(
        input_rows=("recipient_code", "size"),
        unique_recipients=("recipient_code", "nunique"),
        known_pmd_eur=("calculated_pmd_eur", lambda s: s.sum(min_count=1)),
    )
    summary["invalid_rows"] = invalid.groupby("tax_year", dropna=False).size().reindex(summary.index, fill_value=0)
    summary["duplicate_rows"] = duplicates.groupby("tax_year", dropna=False).size().reindex(summary.index, fill_value=0)
    summary["missing_metadata_rows"] = warnings.groupby("tax_year", dropna=False).size().reindex(summary.index, fill_value=0)
    summary["zero_requests_positive_amount_rows"] = (
        zero_requests_positive_amount.groupby("tax_year", dropna=False)
        .size()
        .reindex(summary.index, fill_value=0)
    )
    summary.to_csv(outputs / f"{stage}_yearly_validation.csv", encoding="utf-8-sig")
    if data.empty or not invalid.empty or not duplicates.empty:
        raise ValueError(f"Validation stopped: {len(invalid)} invalid rows, {len(duplicates)} duplicate rows. "
                         f"Review {outputs / (stage + '_invalid_rows.csv')} and "
                         f"{outputs / (stage + '_duplicate_rows.csv')}. Existing data files are previous results.")
    return summary


def reconcile(before, after, outputs, stage, equal_rows=True):
    def totals(frame):
        return frame.groupby("tax_year", dropna=False).agg(
            rows=("calculated_pmd_eur", "size"),
            pmd_eur=("calculated_pmd_eur", "sum"), requests=("requests", "sum")
        )
    report = totals(before).join(totals(after), lsuffix="_before", rsuffix="_after", how="outer")
    report["pmd_difference"] = report.pmd_eur_after - report.pmd_eur_before
    report["requests_difference"] = report.requests_after - report.requests_before
    good = report.notna().all(axis=1) & report.pmd_difference.abs().le(.01) & report.requests_difference.eq(0)
    if equal_rows:
        good &= report.rows_before.eq(report.rows_after)
    report["passed"] = good
    report.to_csv(outputs / f"{stage}_reconciliation.csv", encoding="utf-8-sig")
    if not good.all():
        raise ValueError(f"Unexplained changes: review {outputs / (stage + '_reconciliation.csv')}")
