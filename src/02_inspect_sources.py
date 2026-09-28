from pathlib import Path

import pandas as pd


# Find the main project folder.
# __file__ is this script's path, and parents[1] goes one level above src/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# All source files downloaded by 01_download_sources.py are stored here.
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "latest"

# The inspection report will be saved here.
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "source_inspection.txt"


def write_line(report_file, text: object = "") -> None:
    """Write one line to the inspection report."""

    print(text, file=report_file)


def inspect_csv(file_name: str, report_file) -> None:
    """Print basic information about one CSV source file."""

    # Build the full path to the CSV file.
    file_path = RAW_DIR / file_name

    # Print a clear section header so the report is easy to scan.
    write_line(report_file, "=" * 80)
    write_line(report_file, f"CSV file: {file_name}")
    write_line(report_file, "=" * 80)

    # Stop early with a helpful message if the file has not been downloaded yet.
    if not file_path.exists():
        write_line(report_file, f"File not found: {file_path}")
        return

    # Read the CSV into a pandas DataFrame.
    # A DataFrame is like a table: rows and columns.
    df = pd.read_csv(file_path, low_memory=False)

    # df.shape returns a tuple: (number_of_rows, number_of_columns).
    write_line(report_file, "\nRows and columns:")
    write_line(report_file, df.shape)

    # Show every column name exactly as pandas read it from the file.
    write_line(report_file, "\nColumn names:")
    for column in df.columns:
        write_line(report_file, f"- {column}")

    # Show the detected data type for each column.
    # This helps us see which columns are text, numbers, dates, etc.
    write_line(report_file, "\nData types:")
    write_line(report_file, df.dtypes)

    # Count empty values in each column.
    # This helps identify columns that need cleaning or special handling.
    write_line(report_file, "\nMissing values:")
    write_line(report_file, df.isna().sum())

    # Print the first few records so we can understand what the rows look like.
    write_line(report_file, "\nFirst 5 rows:")
    write_line(report_file, df.head())
    write_line(report_file)


def inspect_excel(file_name: str, report_file) -> None:
    """Print basic information about one Excel workbook."""

    # Build the full path to the Excel workbook.
    file_path = RAW_DIR / file_name

    # Print a clear section header for the workbook.
    write_line(report_file, "=" * 80)
    write_line(report_file, f"Excel workbook: {file_name}")
    write_line(report_file, "=" * 80)

    # Stop early with a helpful message if the workbook is missing.
    if not file_path.exists():
        write_line(report_file, f"File not found: {file_path}")
        return

    # Open the Excel file once, then reuse that object for every sheet.
    workbook = pd.ExcelFile(file_path)

    # Sheet names help us decide which sheet contains the useful source table.
    write_line(report_file, "\nSheet names:")
    for sheet_name in workbook.sheet_names:
        write_line(report_file, f"- {sheet_name}")

    # Inspect each sheet separately because Excel files often contain multiple tables.
    for sheet_name in workbook.sheet_names:
        write_line(report_file)
        write_line(report_file, "-" * 80)
        write_line(report_file, f"Sheet: {sheet_name}")
        write_line(report_file, "-" * 80)

        # Read the sheet using pandas' default behavior.
        # This assumes the first non-skipped row is the header, which may or may not be true.
        df = pd.read_excel(workbook, sheet_name=sheet_name)

        write_line(report_file, "\nRows and columns:")
        write_line(report_file, df.shape)

        write_line(report_file, "\nColumn names detected by pandas:")
        for column in df.columns:
            write_line(report_file, f"- {column}")

        write_line(report_file, "\nData types:")
        write_line(report_file, df.dtypes)

        write_line(report_file, "\nMissing values:")
        write_line(report_file, df.isna().sum())

        write_line(report_file, "\nFirst 10 rows:")
        write_line(report_file, df.head(10))

        # Also read the first rows without treating any row as a header.
        # This helps spot title rows, notes, merged-looking headers, or skipped metadata.
        raw_preview = pd.read_excel(workbook, sheet_name=sheet_name, header=None, nrows=10)

        write_line(report_file, "\nRaw first 10 rows, no header assumed:")
        write_line(report_file, raw_preview)


def main() -> None:
    """Create the source inspection text report."""

    # Make sure the outputs folder exists before writing the text file.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Open the report file in write mode.
    # encoding="utf-8" keeps Lithuanian characters readable.
    with OUTPUT_PATH.open("w", encoding="utf-8") as report_file:
        # print(..., file=report_file) writes to the text file instead of the terminal.
        write_line(report_file, "Source inspection report")
        write_line(report_file, f"Project root: {PROJECT_ROOT}")
        write_line(report_file, f"Raw data folder: {RAW_DIR}")
        write_line(report_file)

        # Inspect each CSV source currently stored in data/raw/latest.
        inspect_csv("vardai.csv", report_file)
        inspect_csv("rekvizitai.csv", report_file)

        # Inspect the VMI Excel workbook currently stored in data/raw/latest.
        inspect_excel("paramos_apskaiciavimo_statistika_2026-07-07.xlsx", report_file)

    print(f"Inspection report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
