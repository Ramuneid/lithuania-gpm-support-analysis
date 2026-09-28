# Project Guide

This document explains the folder structure and the purpose of the main files in this project.

The [Methodology](METHODOLOGY.md) provides a compact description of the implemented analysis rules.

The project rebuilds the 1.2% GPM support analysis with Python. The current workflow downloads or copies source files, inspects them, cleans each source, and saves smaller analysis-ready tables.

## Main Folder Structure

```text
1,2% GPM Analysis with Python/
  config/
  data/
    raw/
      latest/
      snapshots/
    interim/
    processed/
  notebooks/
  outputs/
  src/
  .gitignore
  README.md
  PROJECT_GUIDE.md
  requirements.txt
```

## Root Files

### `README.md`

Short project overview. It explains the purpose of the project, basic setup, and the main workflow.

It provides the entry point for readers unfamiliar with the project.

### `PROJECT_GUIDE.md`

This file. It gives a clearer explanation of the folder structure and what each important file does.

### `requirements.txt`

List of Python packages needed by the project.

Package installation command:

```powershell
pip install -r requirements.txt
```

### `.gitignore`

Tells Git which files should not be tracked.

It excludes generated data files, outputs, virtual environment files, and cache folders. This is useful because raw data and generated outputs can be large and can be recreated by running the scripts.

## `config`

Configuration files live here. These files control the pipeline without requiring changes to Python code.

### `config/sources.yaml`

Defines where each source comes from.

It contains:

- public source URLs
- local source paths
- raw filenames to save in `data/raw/latest`

Used by:

```text
src/01_download_sources.py
```

### `config/column_mapping.yaml`

Controls which columns are kept and how columns are renamed in cleaned outputs.

For each source, this file can define:

- source column names
- final cleaned column names
- descriptions
- `keep: true` or `keep: false`
- filters for sources that need row filtering

Example:

```yaml
names:
  columns:
    name:
      source_column: "pilnas_vardas"
      description: "Full name"
      keep: true
```

The YAML key, such as `name`, becomes the cleaned output column name.

Used by:

```text
src/03_clean_vmi.py
src/05_clean_names.py
src/06_clean_rekvizitai.py
src/07_prepare_analysis_tables.py
```

## `data`

Data files live here.

### `data/raw`

Original source files live here.

Raw files preserve the acquired source content. Source updates are handled by the acquisition script rather than manual edits to these files.

### `data/raw/latest`

Current raw source files used by the cleaning scripts.

Examples:

```text
paramos_apskaiciavimo_statistika_2026-07-07.xlsx
vardai.csv
rekvizitai.csv
source_manifest.json
```

### `data/raw/latest/source_manifest.json`

Tracks source update information.

It stores:

- source URL or local path
- download/check time
- file size
- SHA-256 file hash
- whether the file changed
- snapshot path

The hash is used to detect whether source content changed.

### `data/raw/snapshots`

Stores dated copies of raw source files when a source changes.

These snapshots support comparisons between source versions.

### `data/interim`

Cleaned source-specific tables live here.

These files are smaller than the raw files and follow the configuration in `config/column_mapping.yaml`.

Current files:

```text
vmi_support_by_recipient.csv
vmi_support_by_recipient.parquet
names.csv
names.parquet
rekvizitai.csv
rekvizitai.parquet
```

They provide source-specific inputs for exploratory analysis.

### `data/processed`

This folder contains the joined recipient analysis table and municipality summaries produced by `src/07_prepare_analysis_tables.py`. The recipient table combines VMI funding records with available Rekvizitai organization metadata.

## `src`

Python scripts live here. The documented commands assume the project root as their working directory.

### `src/01_download_sources.py`

Downloads or copies raw source files.

It reads:

```text
config/sources.yaml
```

It writes:

```text
data/raw/latest
data/raw/snapshots
data/raw/latest/source_manifest.json
```

Execution command:

```powershell
python src/01_download_sources.py
```

Useful checks:

```powershell
python src/01_download_sources.py --check-config
python src/01_download_sources.py --source vmi_support
```

### `src/02_inspect_sources.py`

Inspects raw source files and writes a text report.

It reads:

```text
data/raw/latest
```

It writes:

```text
outputs/source_inspection.txt
```

The report describes original columns, row counts, data types, missing values, Excel sheet names and example records.

Execution command:

```powershell
python src/02_inspect_sources.py
```

### `src/03_clean_vmi.py`

Cleans the VMI Excel workbook.

It reads:

```text
data/raw/latest/paramos_apskaiciavimo_statistika_2026-07-07.xlsx
config/column_mapping.yaml
```

It writes:

```text
data/interim/vmi_support_by_recipient.csv
data/interim/vmi_support_by_recipient.parquet
outputs/vmi_cleaning_summary.txt
```

Changes to the `vmi_support` mapping take effect when this cleaner is rerun.

### `src/05_clean_names.py`

Cleans the VLKK names source.

It reads:

```text
data/raw/latest/vardai.csv
config/column_mapping.yaml
```

It writes:

```text
data/interim/names.csv
data/interim/names.parquet
outputs/names_cleaning_summary.txt
```

Changes to the `names` mapping take effect when this cleaner is rerun.

### `src/06_clean_rekvizitai.py`

Cleans the Rekvizitai source.

It reads:

```text
data/raw/latest/rekvizitai.csv
config/column_mapping.yaml
config/rekvizitai_manual_corrections.csv
```

It writes:

```text
data/interim/rekvizitai.csv
data/interim/rekvizitai.parquet
outputs/rekvizitai_cleaning_summary.txt
```

Changes to the `rekvizitai` mapping take effect when this cleaner is rerun.

### `src/07_prepare_analysis_tables.py`

Creates final analysis-ready tables for exploratory data analysis.

It reads:

```text
data/interim/vmi_support_by_recipient.csv
data/interim/rekvizitai.csv
```

It writes:

```text
data/processed/recipient_analysis.csv
data/processed/recipient_analysis.parquet
data/processed/municipality_analysis.csv
data/processed/municipality_analysis.parquet
outputs/processed_data_quality_report.txt
```

This stage depends on the cleaned source tables. Its outputs provide the shared inputs for enriched recipient and municipality analysis.

## `outputs`

Human-readable reports and summaries live here.

Current files:

```text
source_inspection.txt
vmi_cleaning_summary.txt
names_cleaning_summary.txt
rekvizitai_cleaning_summary.txt
```

These files document the results of the corresponding processing stages.

## `notebooks`

The eight notebooks form an ordered analysis, from source inspection (00) through funding growth patterns (07). The [reading order](README.md#reading-order) lists each notebook's question and links.

Notebook 00 introduces data quality; notebook 01 begins the funding overview. The [methodology](METHODOLOGY.md) establishes the definitions of populations, top-1% membership and growth. Notebook introductions explain scope changes, while closing links connect adjacent parts of the analysis.

Notebooks load cleaned files from `data/interim` or joined tables from `data/processed`; they do not depend on variables from another notebook. Each is designed for sequential execution in a fresh kernel. The growth notebook includes whole-period and consecutive-year requests/per-request comparisons. These describe changes accompanying growth, not causal drivers.

## Typical Workflow

The source-processing sequence, executed from the project root, is:

```powershell
python src/01_download_sources.py
python src/02_inspect_sources.py
python src/03_clean_vmi.py
python src/05_clean_names.py
python src/06_clean_rekvizitai.py
python src/07_prepare_analysis_tables.py
```

Corresponding review outputs:

```text
outputs/source_inspection.txt
outputs/*_cleaning_summary.txt
data/interim/*.csv
```

## Column-Mapping Changes

Changes to retained columns or their names require the related cleaner to regenerate its output.

Examples:

```powershell
python src/03_clean_vmi.py
python src/05_clean_names.py
python src/06_clean_rekvizitai.py
```

Source acquisition is unnecessary when only transformation settings change and the original source files remain the same.

## Current Stage

The project includes a cleaning and validation pipeline, shared analytical definitions, eight analysis notebooks and external HTML heatmaps. It is no longer only a starting point for exploratory analysis.

The full verification workflow described in [REPRODUCIBILITY.md](REPRODUCIBILITY.md) assumes saved edits and closed notebook editors:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 src\08_verify_reproducibility.py
```

This rebuilds from existing raw inputs, runs tests, executes notebooks with fresh kernels and fingerprints generated outputs. `outputs/reproducibility_report.json` identifies the verified state; an earlier PASS does not verify subsequent edits. Notebook previews provide orientation, while `outputs/heatmaps/` contains complete recipient-level reports.
