"""List and hash the explicit release allowlist; never include local/reference files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = [".gitignore", ".gitattributes", "README.md", "THIRD_PARTY_NOTICES.md", "requirements.in", "requirements.lock.txt"]
DIRECTORIES = ["config", "data/raw", "data/source", "data/splits", "src", "scripts", "notes", "notebooks", "outputs"]
MANIFEST = "outputs/release_manifest.json"


def collect() -> dict:
    candidates = [ROOT / name for name in ROOT_FILES]
    for directory in DIRECTORIES:
        candidates.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    files = {}
    for path in sorted(set(candidates)):
        name = path.relative_to(ROOT).as_posix()
        if name == MANIFEST:
            continue
        if path.suffix.lower() in {".pdf", ".pem", ".key", ".pyc"} or path.name.startswith(".env"):
            raise ValueError(f"Unexpected restricted file in allowlist: {name}")
        data = path.read_bytes()
        if path.suffix.lower() not in {".zip"}:
            content = data.decode("utf-8", errors="replace")
            patterns = [r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}",
                        r"AKIA[A-Z0-9]{16}", r"sk-[A-Za-z0-9_-]{30,}", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                        r"https?://[^\s\"']+[?&](?:sig|token|access_token)="]
            if any(re.search(pattern, content) for pattern in patterns):
                raise ValueError(f"Possible secret/transfer URL in release file: {name}")
        files[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return {"manifest_version": 1, "files": files,
            "manifest_self_excluded": MANIFEST, "total_bytes_excluding_manifest": sum(x["bytes"] for x in files.values()),
            "excluded": [".venv/", ".local/", "references/", "all course or group-manual PDFs", "Library helpers and transfer metadata", "credentials"],
            "scope": "A data governance only; licensed UCI original archives/data plus authored scripts, docs and generated evidence",
            "secret_scan": "Known token/key and signed-transfer patterns checked; staged file review remains required"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    current = collect()
    destination = ROOT / MANIFEST
    if args.verify:
        saved = json.loads(destination.read_text(encoding="utf-8"))
        if current != saved:
            raise ValueError("Release manifest mismatch; snapshot changed")
        print(f"Verified frozen release: {len(current['files'])} files plus manifest")
    else:
        destination.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Release allowlist: {len(current['files'])} files plus manifest; {current['total_bytes_excluding_manifest']} bytes")
