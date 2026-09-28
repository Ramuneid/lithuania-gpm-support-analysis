from __future__ import annotations

from pathlib import Path

import pandas as pd
import json
from data_validation import fingerprint, reconcile, validate_recipient_years, write_status


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Read the cleaned, source-specific tables from here.
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Save analysis-ready tables here.
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Save a short human-readable cleaning report here.
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def clean_text(value: object) -> str | None:
    """Trim text values and keep empty text as missing."""

    if pd.isna(value):
        return None

    text = str(value).strip()
    if text == "":
        return None

    return text


def clean_code(value: object) -> str | None:
    """Keep organization codes as text so leading zeroes would not be lost."""

    text = clean_text(value)
    if text is None:
        return None

    # CSV readers sometimes turn numeric-looking IDs into values like 123.0.
    if text.endswith(".0"):
        text = text[:-2]

    return text


def standardize_leader_gender(value: object) -> str | None:
    """Standardize leader gender values used in the analysis tables."""

    text = clean_text(value)
    if text is None:
        return None

    replacements = {
        "Vyras": "Male",
        "Moteris": "Female",
        "Nėra duomenų apie lytį": "Unknown",
    }

    return replacements.get(text, text)


def assign_organization_age_group(age: object) -> str | None:
    """Assign an organization age in years to a reusable analysis group."""

    if pd.isna(age):
        return None

    age_value = float(age)

    if age_value <= 5:
        return "0-5"
    if age_value <= 10:
        return "6-10"
    if age_value <= 15:
        return "11-15"
    if age_value <= 20:
        return "16-20"
    if age_value <= 25:
        return "21-25"
    if age_value <= 30:
        return "26-30"
    if age_value <= 35:
        return "31-35"
    if age_value <= 40:
        return "36-40"

    return "41+"


def read_interim_csv(file_name: str) -> pd.DataFrame:
    """Read one CSV file from data/interim."""

    path = INTERIM_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(f"Missing interim file: {path}")

    return pd.read_csv(path, low_memory=False, dtype={"recipient_code": "string", "code": "string"})


def save_processed_table(df: pd.DataFrame, file_stem: str) -> list[Path]:
    """Save a processed table as CSV and, when supported, Parquet."""

    csv_path = PROCESSED_DIR / f"{file_stem}.csv"
    parquet_path = PROCESSED_DIR / f"{file_stem}.parquet"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    saved_paths = [csv_path]

    try:
        df.to_parquet(parquet_path, index=False)
    except ImportError:
        # Parquet is useful but optional. The bundled runtime used for notebooks
        # may not include pyarrow or fastparquet, while CSV remains sufficient
        # for the current analysis workflow.
        pass
    else:
        saved_paths.append(parquet_path)

    return saved_paths


def prepare_vmi(vmi: pd.DataFrame) -> pd.DataFrame:
    """Clean types in the VMI support table."""

    cleaned = vmi.copy()

    cleaned["tax_year"] = pd.to_numeric(cleaned["tax_year"], errors="coerce")
    cleaned["recipient_code"] = cleaned["recipient_code"].map(clean_code).astype("string")
    cleaned["recipient_municipality"] = cleaned["recipient_municipality"].map(clean_text)
    cleaned["recipient_name"] = cleaned["recipient_name"].map(clean_text)
    cleaned["legal_form"] = cleaned["legal_form"].map(clean_text)
    cleaned["requests"] = pd.to_numeric(cleaned["requests"], errors="coerce")
    cleaned["calculated_pmd_eur"] = pd.to_numeric(cleaned["calculated_pmd_eur"], errors="coerce")

    validate_recipient_years(cleaned, OUTPUTS_DIR, "prepared_vmi")
    cleaned["tax_year"] = cleaned["tax_year"].astype("Int64")
    cleaned = cleaned.reset_index(drop=True)

    return cleaned


def prepare_rekvizitai(rekvizitai: pd.DataFrame) -> pd.DataFrame:
    """Clean Rekvizitai table and standardize analysis helper columns."""

    cleaned = rekvizitai.copy()

    cleaned["code"] = cleaned["code"].map(clean_code).astype("string")
    cleaned["director"] = cleaned["director"].map(clean_text)
    cleaned["leader_gender"] = cleaned["leader_gender"].map(standardize_leader_gender)
    cleaned["address"] = cleaned["address"].map(clean_text)
    cleaned["mobile_phone"] = cleaned["mobile_phone"].map(clean_text)
    cleaned["website"] = cleaned["website"].map(clean_text)
    cleaned["start_date"] = pd.to_datetime(cleaned["start_date"], errors="coerce", format="mixed")

    cleaned["organization_start_year"] = cleaned["start_date"].dt.year.astype("Int64")
    cleaned["has_director"] = cleaned["director"].notna()
    cleaned["has_leader_gender"] = cleaned["leader_gender"].notna() & (cleaned["leader_gender"] != "Unknown")
    cleaned["has_mobile_phone"] = cleaned["mobile_phone"].notna()
    cleaned["has_website"] = cleaned["website"].notna()

    cleaned = cleaned.dropna(subset=["code"])
    cleaned = cleaned.drop_duplicates(["code"], keep="last").reset_index(drop=True)

    return cleaned


def build_recipient_analysis(vmi: pd.DataFrame, rekvizitai: pd.DataFrame) -> pd.DataFrame:
    """Join VMI support recipients to Rekvizitai organization details."""

    joined = vmi.merge(
        rekvizitai,
        how="left",
        left_on="recipient_code",
        right_on="code",
        validate="many_to_one",
        indicator="metadata_match",
    )

    joined = joined.drop(columns=["code"])
    joined = joined.rename(columns={"start_date": "organization_start_date"})

    calculated_age = joined["tax_year"] - joined["organization_start_year"]
    # A contradictory registration date is unreliable for every year of that recipient.
    inconsistent_codes = joined.loc[
        calculated_age.lt(0).fillna(False), "recipient_code"
    ].unique()
    inconsistent_date = joined["recipient_code"].isin(inconsistent_codes)
    missing_date = joined["organization_start_year"].isna()

    joined["organization_age_status"] = "Available"
    joined.loc[missing_date, "organization_age_status"] = "Registration date missing"
    joined.loc[inconsistent_date, "organization_age_status"] = "Registration date inconsistent"
    joined["organization_age"] = calculated_age.mask(
        inconsistent_date | missing_date
    ).astype("Int64")
    joined["organization_age_group"] = (
        joined["organization_age"].map(assign_organization_age_group).fillna("Unknown")
    )

    return joined


def build_municipality_analysis(vmi: pd.DataFrame) -> pd.DataFrame:
    """Aggregate support by recipient municipality and tax year."""

    support_by_municipality = (
        vmi.groupby(["tax_year", "recipient_municipality"], as_index=False, dropna=False)
        .agg(
            recipients=("recipient_code", "nunique"),
            requests=("requests", "sum"),
            calculated_pmd_eur=("calculated_pmd_eur", "sum"),
        )
        .rename(
            columns={
                "tax_year": "year",
                "recipient_municipality": "municipality",
            }
        )
    )

    return support_by_municipality


def write_quality_report(
    vmi: pd.DataFrame,
    rekvizitai: pd.DataFrame,
    recipient_analysis: pd.DataFrame,
    municipality_analysis: pd.DataFrame,
    saved_files: list[Path],
) -> Path:
    """Write a compact report describing the processed analysis tables."""

    report_path = OUTPUTS_DIR / "processed_data_quality_report.txt"

    matched = recipient_analysis["metadata_match"].eq("both")
    unmatched = recipient_analysis["metadata_match"].eq("left_only")

    review_groups = {
        "No matching metadata code": unmatched,
        "Matched, but director missing": (
            matched & recipient_analysis["director"].isna()
        ),
        "Matched, but registration date missing": (
            matched & recipient_analysis["organization_start_date"].isna()
        ),
        "Age unavailable: registration date missing": (
            recipient_analysis["organization_age_status"]
            .eq("Registration date missing")
        ),
        "Age unavailable: registration date inconsistent": (
            recipient_analysis["organization_age_status"]
            .eq("Registration date inconsistent")
        ),
    }

    with report_path.open("w", encoding="utf-8") as file:
        file.write("Processed data quality report\n\n")
        file.write("Input tables:\n")
        file.write(f"- VMI rows: {len(vmi):,}\n")
        file.write(f"- Rekvizitai rows: {len(rekvizitai):,}\n\n")

        file.write("Processed tables:\n")
        file.write(f"- Recipient analysis rows: {len(recipient_analysis):,}\n")
        file.write(f"- Municipality analysis rows: {len(municipality_analysis):,}\n\n")

        file.write("Metadata matching and age coverage:\n")
        for label, mask in review_groups.items():
            records = recipient_analysis.loc[mask]
            unique_recipients = records["recipient_code"].nunique()
            file.write(
                f"- {label}: {len(records):,} recipient-year records; "
                f"{unique_recipients:,} unique recipients\n"
            )
        file.write("Categories can overlap; do not add these counts.\n")
        file.write("\nMunicipality totals describe recipient locations, not donor locations.\n\n")

        file.write("Leader gender values in Rekvizitai:\n")
        file.write(rekvizitai["leader_gender"].fillna("Missing").value_counts().to_string())
        file.write("\n\n")

        file.write("Files saved:\n")
        for path in saved_files:
            file.write(f"- {path}\n")

    return report_path


def main() -> None:
    """Create analysis-ready processed tables for exploratory data analysis."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    write_status(OUTPUTS_DIR, "processed", "RUNNING", "Validation and preparation in progress.")
    status_path = OUTPUTS_DIR / "vmi_validation_status.json"
    if not status_path.exists():
        raise ValueError("Run src/03_clean_vmi.py and review its validation report first.")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status.get("status") != "PASS" or status.get("interim_sha256") != fingerprint(INTERIM_DIR / "vmi_support_by_recipient.csv"):
        raise ValueError("Interim data is not validated or has changed. Rerun src/03_clean_vmi.py.")
    source_path = PROJECT_ROOT / "data/raw/latest/paramos_apskaiciavimo_statistika_2026-07-07.xlsx"
    if status.get("source_sha256") != fingerprint(source_path):
        raise ValueError("Raw VMI source has changed. Rerun src/03_clean_vmi.py.")

    vmi = prepare_vmi(read_interim_csv("vmi_support_by_recipient.csv"))
    rekvizitai = prepare_rekvizitai(read_interim_csv("rekvizitai.csv"))

    recipient_analysis = build_recipient_analysis(vmi, rekvizitai)
    municipality_analysis = build_municipality_analysis(vmi)
    validate_recipient_years(recipient_analysis, OUTPUTS_DIR, "joined_recipients")
    reconcile(vmi, recipient_analysis, OUTPUTS_DIR, "recipient_join")
    reconcile(vmi, municipality_analysis.rename(columns={"year": "tax_year"}),
              OUTPUTS_DIR, "municipality_aggregation", equal_rows=False)

    saved_files = []
    saved_files.extend(save_processed_table(recipient_analysis, "recipient_analysis"))
    saved_files.extend(save_processed_table(municipality_analysis, "municipality_analysis"))

    report_path = write_quality_report(
        vmi,
        rekvizitai,
        recipient_analysis,
        municipality_analysis,
        saved_files,
    )

    print(f"Recipient analysis table saved to: {PROCESSED_DIR / 'recipient_analysis.csv'}")
    print(f"Municipality analysis table saved to: {PROCESSED_DIR / 'municipality_analysis.csv'}")
    print(f"Quality report saved to: {report_path}")
    write_status(OUTPUTS_DIR, "processed", "PASS", "Row counts and yearly PMD/request totals reconciled. Ready for notebooks.")
    print(f"VALIDATION PASS: review {OUTPUTS_DIR / 'processed_validation_status.json'} before running notebooks.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_status(OUTPUTS_DIR, "processed", "FAIL", str(exc))
        raise
