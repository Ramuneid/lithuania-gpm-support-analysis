from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
LATEST_DIR = RAW_DIR / "latest"
SNAPSHOTS_DIR = RAW_DIR / "snapshots"
MANIFEST_PATH = LATEST_DIR / "source_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def load_sources(config_path: Path) -> dict[str, dict[str, Any]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    sources = parse_simple_sources_yaml(config_path)
    local_config = config_path.with_name('sources.local.yaml')
    if local_config.exists():
        for name, details in parse_simple_sources_yaml(local_config).items():
            if name not in sources:
                raise ValueError(f'Unknown local source override: {name}')
            sources[name].update(details)

    if not isinstance(sources, dict):
        raise ValueError("sources.yaml must contain a mapping of source names.")

    for name, details in sources.items():
        if not isinstance(details, dict):
            raise ValueError(f"Source '{name}' must be a mapping.")
        if "raw_file" not in details:
            raise ValueError(f"Source '{name}' is missing raw_file.")
        if "url" not in details and "local_path" not in details:
            raise ValueError(f"Source '{name}' must define url or local_path.")

    return sources


def parse_simple_sources_yaml(config_path: Path) -> dict[str, dict[str, str]]:
    """Parse the simple source registry format without external packages."""
    sources: dict[str, dict[str, str]] = {}
    current_source: str | None = None

    for line_number, raw_line in enumerate(config_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if not line.startswith(" ") and stripped.endswith(":"):
            current_source = stripped[:-1]
            if current_source in sources:
                raise ValueError(f"Duplicate source '{current_source}' on line {line_number}.")
            sources[current_source] = {}
            continue

        if current_source is None:
            raise ValueError(f"Expected a source name before line {line_number}.")

        if ":" not in stripped:
            raise ValueError(f"Expected key: value on line {line_number}.")

        key, value = stripped.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        sources[current_source][key.strip()] = value

    return sources


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"generated_at": None, "sources": {}}

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_manifest(manifest: dict[str, Any]) -> None:
    LATEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest["generated_at"] = utc_now()
    with MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
        file.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_url(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "paramos-statistika-python/0.1"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        with destination.open("wb") as file:
            shutil.copyfileobj(response, file)


def copy_local_file(local_path: str, destination: Path) -> None:
    source_path = Path(local_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Local source file not found: {source_path}")
    shutil.copy2(source_path, destination)


def fetch_source(name: str, details: dict[str, Any], temp_dir: Path) -> Path:
    raw_file = details["raw_file"]
    destination = temp_dir / raw_file

    if "url" in details:
        download_url(details["url"], destination)
    else:
        copy_local_file(details["local_path"], destination)

    return destination


def update_source(
    name: str,
    details: dict[str, Any],
    manifest: dict[str, Any],
    temp_dir: Path,
    snapshot_dir: Path,
) -> dict[str, Any]:
    fetched_path = fetch_source(name, details, temp_dir)
    file_hash = sha256_file(fetched_path)
    file_size = fetched_path.stat().st_size

    previous = manifest.get("sources", {}).get(name, {})
    previous_hash = previous.get("file_sha256")
    changed = file_hash != previous_hash

    latest_path = LATEST_DIR / details["raw_file"]
    LATEST_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "description": details.get("description"),
        "url": details.get("url"),
        "local_path": details.get("local_path"),
        "raw_file": details["raw_file"],
        "checked_at": utc_now(),
        "changed": changed,
        "file_sha256": file_hash,
        "file_size": file_size,
        "latest_path": str(latest_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "last_changed_at": previous.get("last_changed_at"),
        "snapshot_path": previous.get("snapshot_path"),
    }

    if changed:
        snapshot_path = snapshot_dir / details["raw_file"]
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fetched_path, snapshot_path)
        shutil.copy2(fetched_path, latest_path)
        entry["last_changed_at"] = entry["checked_at"]
        entry["snapshot_path"] = str(snapshot_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    elif not latest_path.exists():
        shutil.copy2(fetched_path, latest_path)

    return entry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download or copy project source files and track changes with hashes."
    )
    parser.add_argument(
        "--source",
        action="append",
        help="Run only one source name. Can be used more than once.",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate config/sources.yaml without downloading or copying files.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately if any source fails.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = load_sources(CONFIG_PATH)

    if args.source:
        selected = set(args.source)
        missing = selected.difference(sources)
        if missing:
            print(f"Unknown source name(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2
        sources = {name: details for name, details in sources.items() if name in selected}

    if args.check_config:
        print(f"Config OK: {CONFIG_PATH}")
        print(f"Sources: {', '.join(sources)}")
        return 0

    manifest = load_manifest()
    manifest.setdefault("sources", {})

    current_run_id = run_id()
    temp_dir = RAW_DIR / ".tmp" / current_run_id
    snapshot_dir = SNAPSHOTS_DIR / current_run_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    failures: dict[str, str] = {}

    try:
        for name, details in sources.items():
            try:
                entry = update_source(name, details, manifest, temp_dir, snapshot_dir)
                manifest["sources"][name] = entry
                status = "changed" if entry["changed"] else "unchanged"
                print(f"{name}: {status} ({entry['file_size']} bytes)")
            except Exception as exc:
                failures[name] = str(exc)
                print(f"{name}: failed - {exc}", file=sys.stderr)
                if args.fail_fast:
                    raise

        if failures:
            manifest["last_failures"] = {
                name: {"failed_at": utc_now(), "error": message}
                for name, message in failures.items()
            }
        else:
            manifest.pop("last_failures", None)

        save_manifest(manifest)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    if failures:
        print("Completed with failures. See data/raw/latest/source_manifest.json.")
        return 1

    print(f"Manifest saved: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
