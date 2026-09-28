# Cleaning And Transformation Notes

This document records source-cleaning decisions and the exploratory work that informed them. It distinguishes the scripted pipeline from notebook-stage proposals. The [Methodology](METHODOLOGY.md) and [Validation guide](VALIDATION_GUIDE.md) describe the current analysis rules and validation requirements; historical experiments below are not additional production policies.

## General Workflow

The project keeps three levels of data:

```text
data/raw       Original downloaded or copied source files
data/interim   Cleaned source-specific tables
data/processed Final joined tables for analysis
```

Raw source snapshots are retained unchanged. Cleaning and transformation outputs are stored separately in `data/interim` or `data/processed`.

Column selection and naming are controlled mainly by:

```text
config/column_mapping.yaml
```

Source locations are controlled by:

```text
config/sources.yaml
```

## VMI Support Data

Current cleaned output:

```text
data/interim/vmi_support_by_recipient.csv
data/interim/vmi_support_by_recipient.parquet
```

Script:

```text
src/03_clean_vmi.py
```

Transformations applied:

- Each VMI worksheet is read and combined into one table.
- Worksheet year is saved as `tax_year`.
- Lithuanian source columns are renamed using `config/column_mapping.yaml`.
- Only columns marked `keep: true` are saved.
- Current kept columns are:

```text
tax_year
recipient_municipality
recipient_code
recipient_name
legal_form
requests
calculated_pmd_eur
```

Recommended data types for analysis:

```text
tax_year            integer
recipient_code      text
requests            number
calculated_pmd_eur  number
other columns        text
```

## Names Data

Current cleaned output:

```text
data/interim/names.csv
data/interim/names.parquet
```

Script:

```text
src/05_clean_names.py
```

Transformations applied:

- Lithuanian source columns are renamed using `config/column_mapping.yaml`.
- Only columns marked `keep: true` are saved.
- Current kept columns are:

```text
name
sex
```

Exploratory use of the names reference:

- `name` provides reference values for matching first names extracted from director records.
- `sex` was considered as a fallback for missing `leader_gender` during exploratory review. A name-based inference is not independently verified information about a person.

## Rekvizitai Data

Current source path:

```text
User-specific Rekvizitai CSV path, configured in config/sources.local.yaml (not published)
```

Project raw copy:

```text
data/raw/latest/rekvizitai.csv
```

Current cleaned output:

```text
data/interim/rekvizitai.csv
data/interim/rekvizitai.parquet
```

Script:

```text
src/06_clean_rekvizitai.py
```

Transformations applied in the script:

- The source file is copied into `data/raw/latest` by `src/01_download_sources.py`.
- Lithuanian source columns are renamed using `config/column_mapping.yaml`.
- Only columns marked `keep: true` are saved.
- `recipient_age` is no longer kept.
- `leader_gender` is kept from the source column `leaders_gender`.
- Manual corrections are applied from:

```text
config/rekvizitai_manual_corrections.csv
```

Current kept columns:

```text
code
start_date
director
leader_gender
address
mobile_phone
website
```

Important date parsing note:

The raw source column `starto_data` contains many valid dates.
During notebook review, it was found that the current interim `start_date` had only 3 unique non-missing dates because date parsing was too strict after manual corrections introduced mixed date formats.

The mixed-format parsing expression for the cleaned table is:

```python
pd.to_datetime(rekvizitai_clean["start_date"], errors="coerce", format="mixed")
```

or, when starting from raw:

```python
pd.to_datetime(rekvizitai_raw["starto_data"], errors="coerce", format="mixed")
```

This preserves thousands of unique start dates from the raw source.

Recommended data types for analysis:

```text
code           text
start_date     date
director       text
leader_gender  text/category
address        text
mobile_phone   text
website        text
```

Phone numbers and organization codes are represented as text.
They are identifiers/contact values, not quantities.

## Processed Recipient Analysis Table

Current processed output:

```text
data/processed/recipient_analysis.csv
data/processed/recipient_analysis.parquet
```

Script:

```text
src/07_prepare_analysis_tables.py
```

This table joins VMI recipient-year support records to Rekvizitai organization details.

Organization age fields are created here so they can be reused consistently across notebooks:

```text
organization_start_date
organization_start_year
organization_age
organization_age_group
```

Age rule:

```text
organization_age = tax_year - organization_start_year
```

Age refers to the VMI tax year rather than the current date. The same organization can therefore appear in different age groups across tax years.

Under the current policy, a funding record before the recorded registration year makes that recipient's age unavailable in all years. A missing registration date also produces unavailable age. The original date and funding records remain intact, and the age group is Unknown; `organization_age_status` distinguishes the reasons.

Age groups:

```text
0-5
6-10
11-15
16-20
21-25
26-30
31-35
36-40
41+
missing
```

## Rekvizitai Director Cleaning In Notebook

The following decisions document exploratory notebook work rather than a guarantee that every transformation is part of the scripted pipeline.

Director cleaning decisions:

- The original `director` column provides traceability.
- The proposed `director_clean` field contains the name portion only.
- Commas and subsequent role descriptions are excluded from that proposed field.
- The proposed name split produces:

```text
director_first_name
director_last_name
```

Example:

```text
Eimantas Jazokas, prezidentas -> Eimantas Jazokas
director_first_name -> Eimantas
director_last_name  -> Jazokas
```

Known review issue:

Some director values contain only one word, such as a first name only or a role word.
Those rows need manual review because a last name cannot be extracted reliably.

## Rekvizitai First Name Matching

Notebook matching goal:

```text
director_first_name -> names table -> match found or missing
```

Normalization used before matching:

- trim spaces
- lowercase text
- normalize Unicode
- remove hidden zero-width characters
- replace repeated spaces with one normal space

The matching rule was refined:

- The exploratory match compares the Rekvizitai first name with any word in the names table's `name` field, rather than only the full field value.

This helps when the names table contains multi-word names.

Unmatched first names are saved for review as:

```text
outputs/director_first_names_not_in_names_table.csv
```

## Leader Gender Assignment

Notebook gender assignment goal:

```text
Fill missing leader_gender values using director first name.
```

Preferred final values:

```text
Female
Male
missing
```

In this proposed field convention, unknown values remain missing rather than becoming a separate `Unknown` string.

Gender assignment order:

1. Existing Rekvizitai `leader_gender` values take precedence in the exploratory sequence.
2. Missing values are candidates for a first-name match to the reference table's `sex` field.
3. The historical experiment also proposed the following name-ending fallback, which is a heuristic rather than verified personal information:

```text
first name ends with a, ė, or e -> Female
other ending                  -> Male
```

Recommended final analysis column:

```text
leader_gender_final
```

Supporting columns used during review:

```text
leader_gender_clean
leader_gender_from_name
leader_gender_from_name_clean
leader_gender_from_name_ending
```

## Rekvizitai Duplicate And Empty Row Review

Notebook review steps:

- Fully empty rows.
- Exact duplicate rows.
- Repeated organization codes.

Historical notebook approach:

- The experiment excluded all rows belonging to duplicated `code` values.
- This exploratory approach is distinct from the funding pipeline's current policy, which reports duplicate recipient-year keys and stops for review.

This is stricter than keeping the first or last duplicate.
It is useful when duplicate codes need manual investigation instead of automatic selection.

## Missing Values

The project currently allows pandas to display missing values using different markers:

```text
<NA>
NaN
NaT
None
```

Decision:

- Internal missing-value markers need not have identical printed forms.
- Pandas missing-value checks recognize these markers consistently:

```python
df.isna().sum()
```

This works across pandas missing-value markers.

## Historical Pipeline-Integration Proposal

The exploratory notes proposed moving confirmed Rekvizitai transformations into a script for reproducibility. This list records that proposal, not a claim that every item has been implemented or approved as a current analytical rule.

Likely script update:

```text
src/06_clean_rekvizitai.py
```

Transformations to add permanently:

- parse `start_date` with `format="mixed"`
- create `director_clean`
- create `director_first_name`
- create `director_last_name`
- create `leader_gender_final`
- optionally remove duplicate organization codes
- save review outputs for unmatched first names and removed duplicate codes
