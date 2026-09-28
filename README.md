# 1,2% GPM Analysis with Python

This project rebuilds the 1.2% GPM support analysis using Python.

The workflow is designed to:

- download source data into `data/raw`
- inspect and document source schemas
- clean each source into `data/interim`
- join cleaned sources into analysis-ready tables in `data/processed`
- export summary tables and reports into `outputs`

## Project status: Work in progress

This project explores Lithuania's 1.2% GPM support funding during
2020–2025, including funding distribution, recipient persistence
and growth patterns.

The analysis and documentation are being refined. Findings are
exploratory and may change as validation and further analysis continue.

Source data and generated exports are not included in this repository.
Some analyses require separately obtained organization metadata.

## Project Structure

```text
data/
  raw/        Original downloaded or copied source files
  interim/    Cleaned source-specific files
  processed/  Final joined tables used for analysis
src/           Python scripts for each workflow step
config/        Source URLs and project settings
notebooks/     Ordered analysis notebooks with saved results
outputs/       Final reports, exports, and charts
```

The [Project guide](PROJECT_GUIDE.md) explains the folders and scripts. The [Methodology](METHODOLOGY.md) defines the population, top 1%, corrections, growth measures and age references. [Chart design guidelines](CHART_DESIGN_GUIDELINES.md) describe the visual conventions and accessibility criteria.

The [Validation guide](VALIDATION_GUIDE.md) documents checks performed after data updates. [Reproducibility](REPRODUCIBILITY.md) describes the complete rebuild and fresh-kernel execution process.

## Data Sources

### Public repository and local data

The repository shares analysis code, methodology and selected saved notebook
results, not the underlying datasets. Public VMI and VLKK sources are listed
below. The organization metadata is obtained separately; a complete rebuild
requires a compatible Rekvizitai CSV and permission to use it.

Machine-specific paths belong in the ignored `config/sources.local.yaml`.
`config/sources.local.example.yaml` illustrates the format. The downloader
merges this optional local file over `config/sources.yaml`. The public
configuration contains a placeholder, not a working metadata download.

The optional `config/rekvizitai_manual_corrections.csv` remains local because
it includes personal/contact details. Without the same reviewed corrections,
a rebuild can differ from the saved analysis even with the same raw data.

Raw, intermediate and processed data, local configurations, backups and files
under `outputs/` are excluded from Git. Full HTML heatmaps are therefore not
included: they are generated locally by the relevant analysis notebooks.
The inspection notebook's saved outputs are cleared for public sharing.
Running notebooks can restore personal records and local paths in their outputs;
these must be reviewed again before each publication. See
[Public sharing review](PUBLIC_SHARING.md) for the scope and limitations.

Source URLs and raw output filenames are listed in `config/sources.yaml`.

The initial sources are:

- VMI support calculation statistics workbook
- VLKK Lithuanian names dataset
- local Rekvizitai organization data

## Reading Order

The [methodology](METHODOLOGY.md) establishes the definitions used throughout the notebooks. The sequence below progresses from source inspection to funding comparisons. Each notebook loads its own inputs and does not depend on another notebook's kernel state.

| Notebook | Main question |
| --- | --- |
| [00: Data inspection](notebooks/00_data_inspection.ipynb) | What is in the cleaned sources, and what needs checking? |
| [01: Funding overview](notebooks/01_exploratory_analysis.ipynb) | How do funding, requests and registered locations vary? |
| [02: Distribution and heatmaps](notebooks/02_pmd_distribution.ipynb) | How are amounts distributed, and how does each recipient's funding change? |
| [03: Legal-form coverage](notebooks/03_legal_forms_analysis.ipynb) | Which legal forms appear in each year? |
| [04: Annual top 1%](notebooks/04_top_1_percent_overview.ipynb) | Who qualifies, and how concentrated is their funding? |
| [05: Persistent top 1%](notebooks/05_top_1_persistent_recipients.ipynb) | Who qualifies repeatedly, and how old were they at first observed qualification? |
| [06: Persistent and other recipients](notebooks/06_top_1_newcomers_vs_returning.ipynb) | How do these groups differ within the 2025 top 1%? |
| [07: Growth patterns](notebooks/07_growth_drivers_analysis.ipynb) | What changes accompany annual and whole-period funding growth? |
| [08: All-recipient growth](notebooks/08_all_recipients_growth_analysis.ipynb) | How do funding and requests change without the legal-form filter? |

Early exploration covers all cleaned records. Top-1% sections and notebook 07 use the shared legal-form cohort and report exclusions. Notebook 08 covers all recorded recipients in 2020-2025 without a legal-form or top-1% filter; each growth measure still requires comparable data. Notebook 02's pooled thresholds are not the annual selection thresholds in 04-06. Notebook 06's "other" group is broader than newcomers; notebooks 07 and 08 describe associations, not causal drivers.

Full heatmaps are exported to `outputs/heatmaps/`. The ordered previews in notebooks 02 and 07 are not representative samples; the exported HTML contains all rows.

## Rebuild Workflow

1. Source acquisition downloads public files or copies local sources.
2. Source inspection profiles sheets, columns, row counts and missing values.
3. VMI cleaning standardizes and validates funding records.
4. Names cleaning prepares the names reference table.
5. Rekvizitai cleaning prepares organization metadata.
6. Data preparation joins the cleaned sources into analytical tables.
7. Exports provide summaries for review and visualization.
8. Verification runs tests and executes every notebook in a fresh kernel, saving outputs and fingerprints.

The complete local rebuild after source or analysis changes is invoked with:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 src\08_verify_reproducibility.py
```

The verification workflow assumes notebook edits are saved and editors are closed, preventing stale editor copies from overwriting refreshed files. It rebuilds from existing raw files; downloading new sources is a separate operation. `outputs/reproducibility_report.json` and the [validation reports](VALIDATION_GUIDE.md) document the outcome beyond successful cell execution.

## Setup

The project uses a virtual environment, created and activated with:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Its dependencies are installed with:

```powershell
pip install -r requirements.txt
```

## Updating Source Data

Source updates are handled by:

```powershell
python src/01_download_sources.py
```

The script reads `config/sources.yaml`, downloads public sources, copies local sources, and writes the current files to `data/raw/latest`.

It also calculates a SHA-256 hash for each source. When a source changes, the script saves a timestamped copy in `data/raw/snapshots` and updates `data/raw/latest/source_manifest.json`.

Configuration checks and individual-source update commands:

```powershell
python src/01_download_sources.py --check-config
python src/01_download_sources.py --source vmi_support
python src/01_download_sources.py --source names
```

## Notes

Raw snapshots remain unchanged during analysis. Cleaning and transformation steps write separate files to `data/interim` or `data/processed`.

Municipality summaries describe support received by organizations registered in each municipality, not where their supporters live.
