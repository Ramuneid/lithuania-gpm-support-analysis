from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import yaml
except ImportError:  # pragma: no cover - depends on local environment.
    yaml = None


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Read raw files from the latest downloaded/copy snapshot.
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "latest"

# Write source-specific cleaned files here.
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Write a short human-readable cleaning summary here.
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

REKVIZITAI_FILE = RAW_DIR / "rekvizitai.csv"
COLUMN_MAPPING_FILE = PROJECT_ROOT / "config" / "column_mapping.yaml"
MANUAL_CORRECTIONS_FILE = PROJECT_ROOT / "config" / "rekvizitai_manual_corrections.csv"


MANUAL_CORRECTION_TO_SOURCE_COLUMNS = {
    "input_code": "ivestas_kodas",
    "code": "kodas",
    "code_match_status": "kodo_atitikimas",
    "recipient_age": "amzius",
    "start_date": "starto_data",
    "director": "vadovas",
    "leader_gender": "leaders_gender",
    "address": "adresas",
    "mobile_phone": "mobilus_telefonas",
    "website": "tinklalapis",
}

REKVIZITAI_FALLBACK_CONFIG = {
    "columns": {
        "code": {"source_column": "kodas", "keep": True},
        "start_date": {"source_column": "starto_data", "keep": True},
        "director": {"source_column": "vadovas", "keep": True},
        "leader_gender": {"source_column": "leaders_gender", "keep": True},
        "address": {"source_column": "adresas", "keep": True},
        "mobile_phone": {"source_column": "mobilus_telefonas", "keep": True},
        "website": {"source_column": "tinklalapis", "keep": True},
    }
}


def load_source_config(source_name: str) -> dict:
    """Read one source section from config/column_mapping.yaml."""

    if yaml is None:
        if source_name == "rekvizitai":
            return REKVIZITAI_FALLBACK_CONFIG
        raise ImportError("PyYAML is required to read non-Rekvizitai source configuration.")

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


def clean_code(value: object) -> str | None:
    """Convert organization codes to stable text identifiers."""

    if pd.isna(value):
        return None

    text = str(value).strip()
    if text == "":
        return None

    # CSV readers sometimes convert numeric-looking IDs to values like 123.0.
    if text.endswith(".0"):
        text = text[:-2]

    return text


def apply_manual_corrections(raw: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Apply optional manual Rekvizitai corrections matched by input_code."""

    if not MANUAL_CORRECTIONS_FILE.exists():
        return raw, 0

    corrections = pd.read_csv(MANUAL_CORRECTIONS_FILE, dtype=str, low_memory=False)

    if "input_code" not in corrections.columns:
        raise ValueError("rekvizitai_manual_corrections.csv must contain input_code.")

    corrected = raw.copy()
    corrected["ivestas_kodas"] = corrected["ivestas_kodas"].map(clean_code)
    corrections["input_code"] = corrections["input_code"].map(clean_code)

    applied_count = 0

    for _, correction in corrections.iterrows():
        input_code = correction["input_code"]
        if input_code is None:
            continue

        matching_rows = corrected["ivestas_kodas"] == input_code
        if not matching_rows.any():
            continue

        for correction_column, source_column in MANUAL_CORRECTION_TO_SOURCE_COLUMNS.items():
            if correction_column not in corrections.columns:
                continue
            if source_column not in corrected.columns:
                continue

            value = clean_text(correction[correction_column])
            if value is None:
                continue

            if source_column in {"ivestas_kodas", "kodas"}:
                value = clean_code(value)

            corrected.loc[matching_rows, source_column] = value

        applied_count += int(matching_rows.sum())

    return corrected, applied_count


def apply_column_mapping(df: pd.DataFrame, source_config: dict) -> pd.DataFrame:
    """Keep and rename columns marked keep: true in the mapping file."""

    column_config = source_config.get("columns", {})
    if not column_config:
        raise ValueError("rekvizitai.columns is missing in column_mapping.yaml.")

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
                "does not exist in Rekvizitai source."
            )

        source_columns.append(source_column)
        output_columns.append(output_column)

    if not source_columns:
        raise ValueError("No Rekvizitai columns are marked keep: true in column_mapping.yaml.")

    selected = df.loc[:, source_columns].copy()
    selected.columns = output_columns
    return selected


def clean_rekvizitai(df: pd.DataFrame, source_config: dict) -> pd.DataFrame:
    """Create a compact Rekvizitai table controlled by config/column_mapping.yaml."""

    # Clean source columns before renaming so this still works if you rename
    # the output columns in column_mapping.yaml.
    for column in df.columns:
        if column in {"ivestas_kodas", "kodas"}:
            df[column] = df[column].map(clean_code)
        else:
            df[column] = df[column].map(clean_text)

    selected = apply_column_mapping(df, source_config)

    # Parse selected date columns when the default output name is used.
    if "start_date" in selected.columns:
        selected["start_date"] = pd.to_datetime(
            selected["start_date"],
            errors="coerce",
            format="mixed",
        ).dt.date

    # Remove rows with no selected data, then remove exact duplicates.
    selected = selected.dropna(how="all")
    selected = selected.drop_duplicates().reset_index(drop=True)

    return selected


def write_code_match_review(raw: pd.DataFrame) -> tuple[Path, Path]:
    """Save a small review of rows where the Rekvizitai code did not match."""

    if "kodo_atitikimas" not in raw.columns:
        raise ValueError("Rekvizitai source does not contain kodo_atitikimas.")

    review_path = OUTPUTS_DIR / "rekvizitai_code_match_review.txt"
    ne_rows_path = OUTPUTS_DIR / "rekvizitai_code_match_ne_rows.csv"

    status_counts = raw["kodo_atitikimas"].fillna("Missing").value_counts(dropna=False)
    ne_rows = raw[raw["kodo_atitikimas"] == "NE"].copy()

    ne_rows.to_csv(ne_rows_path, index=False, encoding="utf-8-sig")

    with review_path.open("w", encoding="utf-8") as file:
        file.write("Rekvizitai code match review\n\n")
        file.write("Rows by code match status:\n")
        file.write(status_counts.to_string())
        file.write("\n\n")
        file.write(f"Rows where kodo_atitikimas = NE: {len(ne_rows):,}\n")
        file.write(f"NE rows saved to: {ne_rows_path}\n")

    return review_path, ne_rows_path


def main() -> None:
    """Clean the Rekvizitai source and save selected columns."""

    if not REKVIZITAI_FILE.exists():
        raise FileNotFoundError(f"Missing Rekvizitai source file: {REKVIZITAI_FILE}")

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    source_config = load_source_config("rekvizitai")

    # Read all columns as text because IDs, phone numbers, and websites are not math.
    raw = pd.read_csv(REKVIZITAI_FILE, dtype=str, low_memory=False)
    corrected_raw, manual_corrections_applied = apply_manual_corrections(raw)
    cleaned = clean_rekvizitai(corrected_raw, source_config)
    code_match_review_path, ne_rows_path = write_code_match_review(corrected_raw)

    csv_path = INTERIM_DIR / "rekvizitai.csv"
    parquet_path = INTERIM_DIR / "rekvizitai.parquet"
    summary_path = OUTPUTS_DIR / "rekvizitai_cleaning_summary.txt"

    cleaned.to_csv(csv_path, index=False, encoding="utf-8-sig")
    parquet_saved = True
    try:
        cleaned.to_parquet(parquet_path, index=False)
    except ImportError:
        parquet_saved = False

    with summary_path.open("w", encoding="utf-8") as file:
        file.write("Rekvizitai cleaning summary\n\n")
        file.write(f"Source file: {REKVIZITAI_FILE}\n")
        file.write(f"Output CSV: {csv_path}\n")
        if parquet_saved:
            file.write(f"Output Parquet: {parquet_path}\n\n")
        else:
            file.write("Output Parquet: not saved because no Parquet engine is installed\n\n")
        file.write(f"Raw rows: {len(raw):,}\n")
        file.write(f"Manual corrections applied to rows: {manual_corrections_applied:,}\n")
        file.write(f"Rows saved: {len(cleaned):,}\n")
        file.write(f"Columns saved: {', '.join(cleaned.columns)}\n")
        file.write(f"Code match review: {code_match_review_path}\n")
        file.write(f"Code match NE rows: {ne_rows_path}\n")

        if "code_match_status" in cleaned.columns:
            file.write("\nRows by code match status:\n")
            file.write(cleaned["code_match_status"].value_counts(dropna=False).to_string())
            file.write("\n")

    print(f"Cleaned Rekvizitai data saved to: {csv_path}")
    if parquet_saved:
        print(f"Cleaned Rekvizitai data saved to: {parquet_path}")
    else:
        print("Cleaned Rekvizitai Parquet not saved because no Parquet engine is installed.")
    print(f"Cleaning summary saved to: {summary_path}")
    print(f"Code match review saved to: {code_match_review_path}")
    print(f"Code match NE rows saved to: {ne_rows_path}")
    print(f"Manual corrections applied to rows: {manual_corrections_applied}")


if __name__ == "__main__":
    main()
