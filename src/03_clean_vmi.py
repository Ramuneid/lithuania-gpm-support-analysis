from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import yaml
from data_validation import fingerprint, reconcile, validate_recipient_years, write_status


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Read raw files from the latest downloaded/copy snapshot.
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "latest"

# Write source-specific cleaned files here.
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Write a short human-readable cleaning summary here.
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

VMI_FILE = RAW_DIR / "paramos_apskaiciavimo_statistika_2026-07-07.xlsx"
COLUMN_MAPPING_FILE = PROJECT_ROOT / "config" / "column_mapping.yaml"


# These are the normalized columns we want from every yearly recipient sheet.
# Some older years have extra transfer/difference columns. The 2025 sheet does not.
BASE_COLUMNS = [
    "recipient_municipality",
    "recipient_code",
    "recipient_name",
    "legal_form",
    "requests_total",
    "requests_with_calculated_pmd",
    "electronic_requests_with_calculated_pmd",
    "electronic_requests_with_calculated_pmd_pct",
    "calculated_pmd_eur",
]

OPTIONAL_COLUMNS = [
    "transferred_pmd_eur",
    "pmd_difference_eur",
]


# The cleaner first creates stable internal names by column position.
# This dictionary connects the review/control file's source_label values to
# those internal names, so you can freely choose final output column names.
VMI_SOURCE_LABEL_TO_INTERNAL = {
    "Source sheet year": "tax_year",
    "Source worksheet name": "source_sheet",
    "Atnaujinta": "source_updated_at",
    "Gavėjo savivaldybės pavadinimas": "recipient_municipality",
    "Gavėjo kodas": "recipient_code",
    "Gavėjo pavadinimas": "recipient_name",
    "Teisinė forma": "legal_form",
    "Bendras pateiktų prašymų skaičius": "requests_total",
    "Prašymų, pagal kuriuos apskaičiuota PMD, skaičius": "requests_with_calculated_pmd",
    "Elektroniniu būdu pateiktų Prašymų, pagal kuriuos apskaičiuota PMD, skaičius": "electronic_requests_with_calculated_pmd",
    "Elektroniniu būdu pateiktų Prašymų, pagal kuriuos apskaičiuota PMD, proc.": "electronic_requests_with_calculated_pmd_pct",
    "Apskaičiuota PMD, Eur": "calculated_pmd_eur",
    "Pervesta PMD, įvertinus perskaičiavimus už ankstesnius metus": "transferred_pmd_eur",
    "Skirtumas tarp pervestos ir apskaičiuotos PMD": "pmd_difference_eur",
}


def extract_tax_year(sheet_name: str) -> int | None:
    """Extract the year from sheet names such as 'Apskaičiuota už 2025 metus'."""

    match = re.search(r"(20\d{2})", sheet_name)
    if match:
        return int(match.group(1))
    return None


def extract_source_updated_at(workbook: pd.ExcelFile, sheet_name: str) -> str | None:
    """Read the update date text from row 5, column A of a yearly VMI sheet."""

    preview = pd.read_excel(workbook, sheet_name=sheet_name, header=None, nrows=5)
    value = preview.iloc[4, 0]

    if pd.isna(value):
        return None

    text = str(value).strip()
    return text.replace("Atnaujinta:", "").strip()


def clean_code(value: object) -> str | None:
    """Convert recipient codes to stable text identifiers."""

    if pd.isna(value):
        return None

    # Excel may read numeric-looking codes as floats. Convert 123.0 to "123".
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()


def clean_text(value: object) -> str | None:
    """Trim text values and keep missing values as None."""

    if pd.isna(value):
        return None

    text = str(value).strip()
    if text == "":
        return None
    return text


def load_vmi_column_choices() -> list[tuple[str, str]]:
    """Read selected VMI output columns from config/column_mapping.yaml."""

    if not COLUMN_MAPPING_FILE.exists():
        raise FileNotFoundError(f"Missing column mapping file: {COLUMN_MAPPING_FILE}")

    with COLUMN_MAPPING_FILE.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    columns = config.get("vmi_support", {}).get("columns", {})
    if not columns:
        raise ValueError("column_mapping.yaml must contain vmi_support.columns.")

    selected_columns = []
    all_internal_columns = ["tax_year", "source_sheet", "source_updated_at"] + BASE_COLUMNS + OPTIONAL_COLUMNS

    for output_column, settings in columns.items():
        if not isinstance(settings, dict):
            raise ValueError(f"Column mapping for '{output_column}' must be a mapping.")

        if not settings.get("keep", False):
            continue

        source_label = settings.get("source_label")
        internal_column = settings.get("internal_column")

        if internal_column is None and source_label in VMI_SOURCE_LABEL_TO_INTERNAL:
            internal_column = VMI_SOURCE_LABEL_TO_INTERNAL[source_label]

        if internal_column is None and output_column in all_internal_columns:
            internal_column = output_column

        if internal_column not in all_internal_columns:
            raise ValueError(
                "Could not map output column "
                f"'{output_column}' to a VMI source column. "
                "Check source_label or add internal_column in column_mapping.yaml."
            )

        selected_columns.append((internal_column, output_column))

    if not selected_columns:
        raise ValueError("No VMI columns are marked keep: true in column_mapping.yaml.")

    return selected_columns


def apply_column_choices(df: pd.DataFrame, column_choices: list[tuple[str, str]]) -> pd.DataFrame:
    """Keep and rename columns according to the mapping file."""

    missing_columns = [internal for internal, _ in column_choices if internal not in df.columns]
    if missing_columns:
        raise ValueError(f"Cleaned VMI data is missing expected columns: {missing_columns}")

    internal_columns = [internal for internal, _ in column_choices]
    output_columns = [output for _, output in column_choices]

    selected = df.loc[:, internal_columns].copy()
    selected.columns = output_columns
    return selected


def clean_year_sheet(workbook: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    """Clean one yearly VMI recipient sheet into a normalized table."""

    tax_year = extract_tax_year(sheet_name)
    source_updated_at = extract_source_updated_at(workbook, sheet_name)

    # Rows 1-5 contain title, notes, update date, and source totals.
    # Rows 6-7 contain split headers.
    # Row 8 is the first data row, so skip the first 7 Excel rows.
    df = pd.read_excel(workbook, sheet_name=sheet_name, header=None, skiprows=7,
                       dtype={1: object})

    # Preserve column positions even when an entire source column is empty.
    df = df.dropna(axis=0, how="all")

    # Keep only the expected data columns. This protects us from trailing blank columns.
    expected_columns = BASE_COLUMNS + OPTIONAL_COLUMNS
    df = df.iloc[:, : len(expected_columns)]
    df.columns = expected_columns[: len(df.columns)]

    df["source_excel_row"] = df.index + 8

    # Clean text-like fields.
    df["recipient_municipality"] = df["recipient_municipality"].map(clean_text)
    df["recipient_code"] = df["recipient_code"].map(clean_code)
    df["recipient_name"] = df["recipient_name"].map(clean_text)
    df["legal_form"] = df["legal_form"].map(clean_text)

    # Convert numeric columns to numbers. Invalid values become missing values.
    numeric_columns = [
        "requests_total",
        "requests_with_calculated_pmd",
        "electronic_requests_with_calculated_pmd",
        "electronic_requests_with_calculated_pmd_pct",
        "calculated_pmd_eur",
        "transferred_pmd_eur",
        "pmd_difference_eur",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    # Add provenance columns so every cleaned row can be traced back.
    df.insert(0, "tax_year", tax_year)
    df.insert(1, "source_sheet", sheet_name)
    df.insert(2, "source_updated_at", source_updated_at)
    header = pd.read_excel(workbook, sheet_name=sheet_name, header=None, nrows=5)
    df.attrs["stated_pmd_eur"] = pd.to_numeric(header.iloc[4, 8], errors="coerce")

    return df


def apply_zero_request_policy(data: pd.DataFrame, outputs: Path) -> pd.DataFrame:
    """Retain zero-request rows but remove their positive PMD from analysis."""
    outputs.mkdir(parents=True, exist_ok=True)
    corrected = data.copy()
    mask = data["requests"].eq(0) & data["calculated_pmd_eur"].gt(0)
    audit = data.loc[mask].copy()
    audit["corrected_requests"] = 0
    audit["corrected_calculated_pmd_eur"] = 0.0
    audit["correction_reason"] = "Analysis policy: positive PMD with zero requests is treated as zero."
    audit.to_csv(outputs / "vmi_zero_request_corrections.csv", index=False, encoding="utf-8-sig")
    corrected.loc[mask, ["requests", "calculated_pmd_eur"]] = 0

    report = data.groupby("tax_year").agg(
        source_rows=("recipient_code", "size"),
        source_pmd_eur=("calculated_pmd_eur", "sum"),
    )
    adjustments = audit.groupby("tax_year").agg(
        corrected_rows=("recipient_code", "size"),
        removed_pmd_eur=("calculated_pmd_eur", "sum"),
    )
    report = report.join(adjustments).fillna(0)
    report["analysis_pmd_eur"] = corrected.groupby("tax_year")["calculated_pmd_eur"].sum()
    report["difference_eur"] = report.source_pmd_eur - report.removed_pmd_eur - report.analysis_pmd_eur
    report["passed"] = report.difference_eur.abs().le(.01)
    report.to_csv(outputs / "vmi_zero_request_adjustments_by_year.csv", encoding="utf-8-sig")
    if not report.passed.all():
        raise ValueError("Zero-request adjustments did not reconcile; review the yearly adjustment report.")
    print(f"Zero-request policy: {len(audit):,} rows; EUR {audit['calculated_pmd_eur'].sum():,.2f} removed.")
    return corrected


def main() -> None:
    """Clean all yearly VMI recipient sheets and save one combined table."""

    if not VMI_FILE.exists():
        raise FileNotFoundError(f"Missing VMI source file: {VMI_FILE}")

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    write_status(OUTPUTS_DIR, "vmi", "RUNNING", "Do not use previous outputs until this run passes.")

    workbook = pd.ExcelFile(VMI_FILE)
    column_choices = load_vmi_column_choices()

    # Only sheets with a tax year in the name are recipient-level yearly sheets.
    yearly_sheets = [
        sheet_name
        for sheet_name in workbook.sheet_names
        if extract_tax_year(sheet_name) is not None
    ]

    cleaned_tables = []
    summary_rows = []

    for sheet_name in yearly_sheets:
        cleaned = clean_year_sheet(workbook, sheet_name)
        cleaned_tables.append(cleaned)
        summary_rows.append(
            {
                "sheet_name": sheet_name,
                "tax_year": extract_tax_year(sheet_name),
                "rows_cleaned": len(cleaned),
                "calculated_pmd_eur": cleaned["calculated_pmd_eur"].sum(),
                "stated_pmd_eur": cleaned.attrs["stated_pmd_eur"],
            }
        )

    combined = pd.concat(cleaned_tables, ignore_index=True)
    validate_recipient_years(combined, OUTPUTS_DIR, "vmi", requests="requests_with_calculated_pmd")
    source_totals = pd.DataFrame(summary_rows)
    source_totals["difference_eur"] = source_totals["calculated_pmd_eur"] - source_totals["stated_pmd_eur"]
    source_totals.to_csv(OUTPUTS_DIR / "vmi_source_totals_review.csv", index=False, encoding="utf-8-sig")
    if not source_totals["difference_eur"].abs().le(.01).all():
        raise ValueError("Workbook totals did not reconcile. Review outputs/vmi_source_totals_review.csv.")
    selected = apply_column_choices(combined, column_choices)
    validate_recipient_years(selected, OUTPUTS_DIR, "vmi_selected")
    reconcile(combined.rename(columns={"requests_with_calculated_pmd": "requests"}), selected,
              OUTPUTS_DIR, "vmi_selection")

    selected = apply_zero_request_policy(selected, OUTPUTS_DIR)
    validate_recipient_years(selected, OUTPUTS_DIR, "vmi_adjusted")

    csv_path = INTERIM_DIR / "vmi_support_by_recipient.csv"
    parquet_path = INTERIM_DIR / "vmi_support_by_recipient.parquet"
    summary_path = OUTPUTS_DIR / "vmi_cleaning_summary.txt"

    selected.to_csv(csv_path, index=False, encoding="utf-8-sig")
    selected.to_parquet(parquet_path, index=False)

    summary = pd.DataFrame(summary_rows).sort_values("tax_year", ascending=False)
    with summary_path.open("w", encoding="utf-8") as file:
        file.write("VMI support recipient cleaning summary\n\n")
        file.write(f"Source file: {VMI_FILE}\n")
        file.write(f"Output CSV: {csv_path}\n")
        file.write(f"Output Parquet: {parquet_path}\n\n")
        file.write(summary.to_string(index=False))
        file.write("\n\n")
        file.write(f"Total rows cleaned: {len(combined):,}\n")
        file.write(f"Source calculated PMD, Eur (before policy): {combined['calculated_pmd_eur'].sum():,.2f}\n")
        file.write(f"Analysis calculated PMD, Eur (after policy): {selected['calculated_pmd_eur'].sum():,.2f}\n")
        file.write("Positive PMD with zero requests is set to zero; records are retained.\n")
        file.write("Review vmi_zero_request_corrections.csv and vmi_zero_request_adjustments_by_year.csv.\n")
        file.write("\nColumns saved:\n")
        for internal_column, output_column in column_choices:
            file.write(f"- {output_column} (from {internal_column})\n")

    print(f"Cleaned VMI data saved to: {csv_path}")
    print(f"Cleaned VMI data saved to: {parquet_path}")
    print(f"Cleaning summary saved to: {summary_path}")
    write_status(OUTPUTS_DIR, "vmi", "PASS", "Review missing-metadata warnings, then run step 07.",
                 source_sha256=fingerprint(VMI_FILE), interim_sha256=fingerprint(csv_path))
    print(f"VALIDATION PASS: review {OUTPUTS_DIR / 'vmi_validation_status.json'} and vmi_missing_metadata.csv")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_status(OUTPUTS_DIR, "vmi", "FAIL", str(exc))
        raise
