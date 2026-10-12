"""Re-download in an isolated temporary copy and compare deterministic artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DETERMINISTIC = [
    "data/source/bank-marketing.zip", "data/source/bank.zip", "data/raw/bank-full.csv", "data/raw/bank-names.txt",
    "data/splits/split_manifest.csv", "data/splits/split_indices.json", "outputs/train_profile.csv",
    "outputs/quality_audit.csv", "outputs/format_checks.csv", "outputs/split_summary.csv",
    "outputs/train_history_consistency.csv", "outputs/audit_summary.json",
    "notes/data_dictionary.csv", "notes/feature_policy.csv",
]


def hashes(root: Path) -> dict:
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in DETERMINISTIC}


def verify() -> dict:
    started = datetime.now(timezone.utc).isoformat()
    temporary = Path(tempfile.mkdtemp(prefix="ca6003-repro-"))
    # Only project-authored source/config is copied, not archives, CSVs, splits, or outputs.
    for directory in ["config", "src", "scripts"]:
        shutil.copytree(ROOT / directory, temporary / directory, ignore=shutil.ignore_patterns("__pycache__"))
    expected = hashes(ROOT)
    commands = [
        [sys.executable, str(temporary / "scripts/prepare_data.py")],
        [sys.executable, str(temporary / "scripts/build_documents.py")],
        [sys.executable, str(temporary / "scripts/validate_project.py")],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=temporary, text=True, capture_output=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise RuntimeError(f"Fresh-copy command failed: {Path(command[1]).name}\n{result.stdout}\n{result.stderr}")
    actual = hashes(temporary)
    mismatches = [name for name in expected if expected[name] != actual[name]]
    if mismatches:
        raise ValueError(f"Fresh-download artifacts differ: {mismatches}")
    result = subprocess.run([sys.executable, str(temporary / "scripts/prepare_data.py"), "--offline"],
                            cwd=temporary, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode or hashes(temporary) != actual:
        raise RuntimeError("Second offline run changed deterministic artifacts or failed")
    if hashes(ROOT) != expected:
        raise RuntimeError("Source project's frozen evidence changed during verification")
    report = {"status": "passed", "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "fresh_official_download": True, "preloaded_data": False, "offline_second_run_unchanged": True,
              "compared_artifacts": actual, "source_project_unchanged": True,
              "temporary_copy": "Kept under the OS temporary directory for diagnostics; no private path recorded"}
    (ROOT / "outputs/reproducibility.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in report.items() if key != "compared_artifacts"}, indent=2))
    return report


if __name__ == "__main__":
    verify()
