"""Rebuild local data and execute every notebook in a separate fresh kernel."""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HTML_REPORTS = (
    "02_percentage_growth.html",
    "02_log_growth.html",
    "02_short_histories.html",
    "07_percentage_growth.html",
    "07_short_histories.html",
)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def collect_output_hashes(root):
    """Fingerprint analysis CSVs and current HTML reports, excluding run archives."""
    html_dir = root / "outputs" / "heatmaps"
    for name in EXPECTED_HTML_REPORTS:
        path = html_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty expected HTML report: {path}")
    paths = [p for folder in ["interim", "processed"]
             for p in (root / "data" / folder).glob("*.csv")]
    paths.extend(html_dir.rglob("*.html"))
    return {str(p.relative_to(root)): sha256(p) for p in sorted(paths) if p.is_file()}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "outputs" / "reproducibility" / stamp
    backup = run_dir / "notebook_backups"
    backup.mkdir(parents=True)
    report = {"status": "RUNNING", "started_at_utc": stamp, "python": platform.python_version(),
              "executable": sys.executable, "platform": platform.platform(), "steps": [], "notebooks": []}
    report_path = ROOT / "outputs/reproducibility_report.json"

    def save():
        text = json.dumps(report, indent=2) + "\n"
        report_path.write_text(text, encoding="utf-8")
        (run_dir / "report.json").write_text(text, encoding="utf-8")

    def run_step(name, args):
        print(f"RUN {name}", flush=True)
        log_path = run_dir / f"{name}.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run([sys.executable, "-X", "utf8", *args], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
        report["steps"].append({"name": name, "exit_code": result.returncode,
                                 "log": str(log_path.relative_to(ROOT))})
        save()
        if result.returncode:
            raise RuntimeError(f"{name} failed. Read {log_path}")
        print(f"PASS {name}", flush=True)

    save()
    try:
        for line in (ROOT / "requirements.txt").read_text().splitlines():
            if "==" in line and not line.startswith("#"):
                package, expected = line.split("==")
                if version(package) != expected:
                    raise RuntimeError(f"{package} does not match requirements.txt; install the pinned requirements first.")
        run_step("dependency_check", ["-m", "pip", "check"])
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"], text=True)
        (run_dir / "environment.txt").write_text(freeze, encoding="utf-8")
        inputs = [*list((ROOT / "data/raw/latest").glob("*")), *list((ROOT / "config").glob("*")),
                  *list((ROOT / "src").glob("*.py")), ROOT / "requirements.txt"]
        report["input_sha256"] = {str(p.relative_to(ROOT)): sha256(p) for p in inputs if p.is_file()}
        notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
        for path in notebooks:
            shutil.copy2(path, backup / path.name)
        report["notebook_backups"] = str(backup.relative_to(ROOT))
        for script in ["03_clean_vmi.py", "05_clean_names.py", "06_clean_rekvizitai.py", "07_prepare_analysis_tables.py"]:
            run_step(script.removesuffix(".py"), [str(ROOT / "src" / script)])
        for stage in ["vmi", "processed"]:
            status = json.loads((ROOT / "outputs" / f"{stage}_validation_status.json").read_text())
            if status["status"] != "PASS":
                raise RuntimeError(f"{stage} validation did not pass.")
        run_step("tests", ["-m", "unittest", "discover", "-s", "tests", "-v"])

        for path in notebooks:
            print(f"RUN fresh kernel: {path.name}", flush=True)
            started = time.monotonic()
            original_hash = sha256(path)
            notebook = nbformat.read(path, as_version=4)
            for cell in notebook.cells:
                if cell.cell_type == "code":
                    cell.outputs = []
                    cell.execution_count = None
            manager = KernelManager(kernel_name="python3")
            # Force the verified environment rather than an unrelated registered kernel.
            manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
            client = NotebookClient(notebook, km=manager, timeout=600, allow_errors=False,
                                    resources={"metadata": {"path": str(ROOT / "notebooks")}})
            try:
                client.execute()
                cells = [c for c in notebook.cells if c.cell_type == "code" and c.source.strip()]
                if any(c.execution_count is None for c in cells):
                    raise RuntimeError("Some nonempty code cells were not executed.")
                if any(o.output_type == "error" for c in cells for o in c.outputs):
                    raise RuntimeError("Notebook contains an error output.")
                if sha256(path) != original_hash:
                    raise RuntimeError("Notebook changed during execution; refusing to overwrite concurrent edits.")
                temporary = run_dir / path.name
                nbformat.write(notebook, temporary)
                os.replace(temporary, path)
                report["notebooks"].append({"name": path.name, "status": "PASS", "code_cells": len(cells),
                                             "seconds": round(time.monotonic() - started, 1), "sha256": sha256(path)})
                save()
                print(f"PASS {path.name}: {len(cells)} executed cells saved", flush=True)
            except Exception as exc:
                nbformat.write(notebook, run_dir / ("failed_" + path.name))
                report["notebooks"].append({"name": path.name, "status": "FAIL", "error": str(exc)})
                raise
            finally:
                if manager.has_kernel:
                    manager.shutdown_kernel(now=True)
        report["output_sha256"] = collect_output_hashes(ROOT)
        report["status"] = "PASS"
        (ROOT / "requirements-lock.txt").write_text(
            "# Verified environment: Python " + platform.python_version() + "; " + platform.system() + "\n" + freeze,
            encoding="utf-8",
        )
    except Exception as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        raise
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        save()
    print(f"ALL PASSED. Report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
