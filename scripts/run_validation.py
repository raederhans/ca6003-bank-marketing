"""Record actual project checks and link the most recent notebook/reproduction evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    tests = subprocess.run([sys.executable, str(ROOT / "scripts/validate_project.py")], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(tests.stdout + tests.stderr)
    if tests.returncode:
        raise SystemExit(tests.returncode)
    pip_check = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    if pip_check.returncode:
        raise RuntimeError(pip_check.stdout + pip_check.stderr)
    frozen = subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, capture_output=True, text=True).stdout
    actual = sorted(line.lower() for line in frozen.splitlines() if line and not line.startswith("#"))
    locked = sorted(line.lower() for line in (ROOT / "requirements.lock.txt").read_text().splitlines() if line and not line.startswith("#"))
    if actual != locked:
        raise RuntimeError("Active environment differs from requirements.lock.txt")
    notebook = json.loads((ROOT / "outputs/notebook_validation.json").read_text(encoding="utf-8"))
    reproduction = json.loads((ROOT / "outputs/reproducibility.json").read_text(encoding="utf-8"))
    if notebook["status"] != "passed" or reproduction["status"] != "passed":
        raise RuntimeError("Notebook/reproduction evidence is not passing")
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(), "status": "passed",
              "governance_tests": {"command": "python scripts/validate_project.py", "exit_code": tests.returncode,
                                   "output": tests.stdout + tests.stderr},
              "dependencies": {"pip_check": pip_check.stdout.strip(), "exact_lock_match": True},
              "notebook": notebook, "fresh_download_reproduction": reproduction,
              "independent_QA": "pending", "student_human_review": "pending", "C_semantic_review": "pending"}
    (ROOT / "outputs/validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Recorded successful validation; independent QA and student review remain pending")
