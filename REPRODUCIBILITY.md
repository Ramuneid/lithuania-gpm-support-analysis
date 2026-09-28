# Analysis Reproducibility

Verification runs in the project folder using its `.venv` environment. It assumes saved notebook edits and closed notebook editors. Concurrent edits are not part of a reproducible run and can conflict with regenerated outputs.

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe src/08_verify_reproducibility.py
```

This command checks dependency versions, rebuilds data from the existing local raw files, validates the results, runs tests, and executes every notebook in a separate fresh kernel. It saves outputs and execution counts in the notebooks after each successful execution. It does not download newer source data or change conclusions.

`outputs/reproducibility_report.json` records the outcome. A complete successful run has a final `PASS` status and lists all eight notebooks as `PASS`. Failed steps include a log path for diagnosis. An older report or partially executed notebook does not verify the current project state.

Each run stores the Python version, package snapshot, input hashes, logs, and original notebook backups under `outputs/reproducibility/<run timestamp>/`. A successful run writes `requirements-lock.txt`, including transitive dependencies. `requirements.txt` pins the direct dependencies used by the analysis and execution tooling.

## Output Hashes

The report's `output_sha256` section records project-relative paths and SHA-256
hashes for interim/processed CSVs and all HTML reports in `outputs/heatmaps/`.
It excludes historical run backups. A missing or empty expected HTML export
prevents a PASS. The expected-export list is maintained in
`src/08_verify_reproducibility.py` when notebook exports are added or renamed.
Notebook hashes remain in the `notebooks` section. These hashes identify the
exact saved file bytes; HTML styling IDs can change between runs even when the
underlying analytical values are unchanged.

An editorial-only Markdown revision also changes a notebook's file hash, even when its code and saved results remain identical. The documentation review in `outputs/documentation_review.json` records those narrower preservation checks separately. It is not a replacement for a fresh execution report and does not extend an earlier execution PASS to new file bytes.

## Another Computer

The tested runtime is Python 3.12.7 on Windows. The equivalent environment setup and verification commands are:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe src/08_verify_reproducibility.py
```

Reproduction depends on the raw files and configuration identified by the successful run. The notebooks contain absolute `PROJECT_ROOT` paths, which require adjustment when the project moves. The Rekvizitai download configuration also references a local path, while verification uses the existing raw copy. A package snapshot and successful local execution do not prove portability to a different operating system.

After successful verification, the notebooks on disk already contain refreshed results. Further interactive execution uses the project's `.venv` interpreter; an additional manual Run All is unnecessary for the verified state.
