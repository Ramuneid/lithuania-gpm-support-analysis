# Data Validation and Review Reports

Validation forms the boundary between updated sources and analysis. It is required after workbook updates, changes to cleaning rules or column mappings, or changes to an interim file. The core validation stages are invoked from the project folder with:

```powershell
.\.venv\Scripts\python.exe src/03_clean_vmi.py
.\.venv\Scripts\python.exe src/07_prepare_analysis_tables.py
```

Step 07 depends on successful completion of step 03.

## After Step 03

`outputs/vmi_validation_status.json` records step 03's status and run time. A current `PASS` indicates successful completion of its checks.

- `vmi_yearly_validation.csv`: input row counts, unique recipients, known PMD totals, invalid/duplicate counts, and missing-metadata counts by year.
- `vmi_source_totals_review.csv`: cleaned PMD versus the workbook's stated PMD in cell I5 of each yearly recipient sheet; differences must be within EUR 0.01. A missing or changed source layout stops validation for review.
- `vmi_selection_reconciliation.csv`: rows, requests, and yearly PMD must remain unchanged when selecting output columns.
- `vmi_invalid_rows.csv`: blocking errors with original sheet and Excel row references. Missing codes or years, nonfinite/negative amounts, and noninteger/negative request counts stop the run.
- `vmi_duplicate_rows.csv`: repeated recipient-year keys, classified as identical copies or conflicting records. Both stop the run; neither is silently removed or summed. Resolution requires evidence identifying the correct source record.
- `vmi_missing_metadata.csv`: missing names, municipalities, or legal forms. These records remain in the data and identify coverage limitations for geographic or legal-form analysis.

No interim data is saved until the data checks pass. Completely empty Excel rows are ignored; every remaining row below the seven-row header is checked. Invalid rows are reported rather than silently rejected. Consequently, a successful run preserves all input business records, including their yearly totals.

## After Step 07

`outputs/processed_validation_status.json` records step 07's status. Analysis depends on a current `PASS` rather than the mere presence of processed files.

- `prepared_vmi_yearly_validation.csv`: defensive validation of the interim recipient-year keys and values.
- `recipient_join_reconciliation.csv`: joining organization details must preserve row counts, PMD, and request totals by year.
- `municipality_aggregation_reconciliation.csv`: aggregation changes row counts but must preserve yearly PMD and requests. Missing municipalities remain an unassigned group.
- `processed_data_quality_report.txt`: enrichment coverage, including missing organization ages and director information.

Step 07 checks source and interim file hashes against the successful step 03 run. Changed files require renewed step 03 validation.

## If Validation Stops

When validation stops, the status detail and referenced review CSV identify the issue requiring clarification or correction before the failed stage can be rerun. Existing CSV/Parquet files may belong to an earlier successful run and are not evidence that the latest data passed. `RUNNING` is also not a success status. Automated validation does not determine which conflicting source record is authoritative.

Fresh-kernel notebook execution follows successful validation of both stages and review of the reported warnings.

## Recipient Identifiers

Recipient and organization codes are text identifiers in CSV reads and joins,
not numeric measures. This preserves leading zeros (for example, `00123`) and
alphanumeric codes. Notebook 05 validates its recipient-year age join as one-to-one.
Excel import preserves codes stored as text; it cannot infer leading zeros that
exist only in Excel display formatting rather than the stored value.

## Zero-Request Amount Policy

Step 03 first reconciles the unadjusted source amounts against the workbook.
It then sets positive calculated PMD to zero wherever requests equal zero,
retaining the recipient-year record and its zero requests. This is an explicit
analysis policy, not a revision of the published source. The raw workbook is unchanged.

- `outputs/vmi_zero_request_corrections.csv` preserves original values and corrected values.
- `outputs/vmi_zero_request_adjustments_by_year.csv` reconciles source amounts minus corrections to analysis amounts for every year.
- `outputs/vmi_adjusted_yearly_validation.csv` validates the adjusted data before saving.

Funding totals, growth and amount-per-request calculations use the adjusted data.
A retained zero amount can produce a -100% decline; growth from a zero baseline
and amount per request for zero requests remain undefined, not zero.
Updated results require rebuilt step 03 and step 07 outputs followed by fresh-kernel notebook execution.
