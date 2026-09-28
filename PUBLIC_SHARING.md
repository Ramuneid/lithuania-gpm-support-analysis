# Public sharing review

The public project is a work in progress, not a distribution of source metadata.
Source field names and code describing their processing remain visible; actual
director/contact records and machine-specific configuration stay local.

## Publication choices

- Inspection notebook outputs are cleared; the code and explanations remain.
- Other analytical figures and tables remain, including organization names and
  recipient identifiers used in the funding analysis. These are not anonymized.
- Local-path diagnostic outputs are cleared without removing analytical code.
- `config/sources.local.yaml` holds the author's original metadata path and is
  ignored by Git. Its example contains no real machine path.
- The manual-corrections CSV stays locally available but is ignored because it
  includes personal names and contact/address fields.
- Source datasets, exported HTML heatmaps, CSV reports and backups stay outside
  the public repository. Full heatmaps are generated locally, not hosted here.

## Rebuild limitations

The downloader reads public source locations from `config/sources.yaml` and
overlays optional values from `config/sources.local.yaml`. Another reader needs
their own authorized metadata CSV. The raw CSV schema is described in
`config/column_mapping.yaml` and the cleaning code. Exact reproduction also
requires the same source snapshots and reviewed manual corrections; those
corrections are optional to the pipeline but affect its results.

## Review before each publication

Check notebook outputs, Markdown, attachments, configuration and staged changes
for credentials, local paths and personal records. Review rendered figures as
well as text: automated credential scans cannot verify image contents or source
redistribution rights. Re-executing notebooks can restore cleared output.

Ignore rules do not remove previously committed content. Before a first push,
inspect the staged file list; if this project has been committed elsewhere,
review that history separately. No Git history or remote repository was audited
as part of this local preparation. Automated pattern checks reduce risk but are
not a guarantee that every secret or sensitive detail has been found.
