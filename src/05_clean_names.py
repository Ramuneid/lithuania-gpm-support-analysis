from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Read raw files from the latest downloaded/copy snapshot.
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "latest"

# Write source-specific cleaned files here.
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Write a short human-readable cleaning summary here.
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

NAMES_FILE = RAW_DIR / "vardai.csv"
COLUMN_MAPPING_FILE = PROJECT_ROOT / "config" / "column_mapping.yaml"


def load_source_config(source_name: str) -> dict:
    """Read one source section from config/column_mapping.yaml."""

    if not COLUMN_MAPPING_FILE.exists():
        raise FileNotFoundError(f"Missing column mapping file: {COLUMN_MAPPING_FILE}")

    with COLUMN_MAPPING_FILE.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    source_config = config.get(source_name)
    if not source_config:
        raise ValueError(f"Missing '{source_name}' section in column_mapping.yaml.")

    return source_config


def clean_text(value: object) -> str | None:
    """Trim text values and keep missing values as None."""

    if pd.isna(value):
        return None

    text = str(value).strip()
    if text == "":
        return None
    return text


def apply_column_mapping(df: pd.DataFrame, source_config: dict) -> pd.DataFrame:
    """Keep and rename columns marked keep: true in the mapping file."""

    column_config = source_config.get("columns", {})
    if not column_config:
        raise ValueError("names.columns is missing in column_mapping.yaml.")

    source_columns = []
    output_columns = []

    for output_column, settings in column_config.items():
        if not isinstance(settings, dict):
            raise ValueError(f"Column mapping for '{output_column}' must be a mapping.")

        if not settings.get("keep", False):
            continue

        source_column = settings.get("source_column")
        if source_column not in df.columns:
            raise ValueError(
                f"Source column '{source_column}' for output column '{output_column}' "
                "does not exist in names source."
            )

        source_columns.append(source_column)
        output_columns.append(output_column)

    if not source_columns:
        raise ValueError("No names columns are marked keep: true in column_mapping.yaml.")

    selected = df.loc[:, source_columns].copy()
    selected.columns = output_columns
    return selected


def clean_names(df: pd.DataFrame, source_config: dict) -> pd.DataFrame:
    """Create a compact names table controlled by config/column_mapping.yaml."""

    selected = apply_column_mapping(df, source_config)

    # Clean common selected text fields when they are present.
    for column in ["first_name", "sex", "normativity", "origin_group_1"]:
        if column in selected.columns:
            selected[column] = selected[column].map(clean_text)

    # Convert the name count to a number when it is selected.
    if "name_count" in selected.columns:
        selected["name_count"] = pd.to_numeric(selected["name_count"], errors="coerce")

    # Remove rows with no selected data, then remove exact duplicates.
    selected = selected.dropna(how="all")
    selected = selected.drop_duplicates().reset_index(drop=True)

    return selected


def main() -> None:
    """Clean the VLKK names source and save selected columns."""

    if not NAMES_FILE.exists():
        raise FileNotFoundError(f"Missing names source file: {NAMES_FILE}")

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    source_config = load_source_config("names")

    # Read the source CSV. low_memory=False gives more consistent type detection.
    raw = pd.read_csv(NAMES_FILE, low_memory=False)
    cleaned = clean_names(raw, source_config)

    csv_path = INTERIM_DIR / "names.csv"
    parquet_path = INTERIM_DIR / "names.parquet"
    summary_path = OUTPUTS_DIR / "names_cleaning_summary.txt"

    cleaned.to_csv(csv_path, index=False, encoding="utf-8-sig")
    cleaned.to_parquet(parquet_path, index=False)

    with summary_path.open("w", encoding="utf-8") as file:
        file.write("Names cleaning summary\n\n")
        file.write(f"Source file: {NAMES_FILE}\n")
        file.write(f"Output CSV: {csv_path}\n")
        file.write(f"Output Parquet: {parquet_path}\n\n")
        file.write(f"Raw rows: {len(raw):,}\n")
        file.write(f"Rows saved: {len(cleaned):,}\n")
        file.write(f"Columns saved: {', '.join(cleaned.columns)}\n")
        if "sex" in cleaned.columns:
            file.write("\nRows by sex:\n")
            file.write(cleaned["sex"].value_counts(dropna=False).to_string())
            file.write("\n")

    print(f"Cleaned names data saved to: {csv_path}")
    print(f"Cleaned names data saved to: {parquet_path}")
    print(f"Cleaning summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
