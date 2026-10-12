"""Execute A's notebook in a fresh project-local kernel; save only after success."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]


def execute_notebook() -> dict:
    local = ROOT / ".local"
    for folder in ["kernels/ca6003-validation", "runtime", "ipython", "jupyter"]:
        (local / folder).mkdir(parents=True, exist_ok=True)
    os.environ["JUPYTER_RUNTIME_DIR"] = str(local / "runtime")
    os.environ["IPYTHONDIR"] = str(local / "ipython")
    os.environ["JUPYTER_CONFIG_DIR"] = str(local / "jupyter")
    specification = {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                     "display_name": "CA6003 validation (project local)", "language": "python"}
    (local / "kernels/ca6003-validation/kernel.json").write_text(json.dumps(specification), encoding="utf-8")
    manager = KernelManager(kernel_name="ca6003-validation", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(local / "kernels")]))
    path = ROOT / "notebooks/A_data_foundation.ipynb"
    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    nbformat.validate(notebook)
    started = datetime.now(timezone.utc).isoformat()
    client = NotebookClient(notebook, km=manager, timeout=180, allow_errors=False)
    try:
        client.execute(cwd=str(ROOT))
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if not all(cell.execution_count is not None for cell in code_cells):
        raise RuntimeError("Notebook code cells were skipped")
    if any(output.output_type == "error" for cell in code_cells for output in cell.outputs):
        raise RuntimeError("Notebook contains error output")
    path.write_text(nbformat.writes(notebook) + "\n", encoding="utf-8", newline="\n")
    report = {"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
              "fresh_kernel": True, "code_cells_executed": len(code_cells), "errors": 0,
              "status": "passed", "kernel_environment": "current project interpreter; no global kernelspec installation"}
    (ROOT / "outputs/notebook_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    execute_notebook()
