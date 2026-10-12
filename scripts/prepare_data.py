"""One command: fetch pinned official archives, verify raw bytes, split, audit."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import platform
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_contract import LOCK, make_manifest, make_splits, read_raw, sha256_bytes, verify_bytes


def put_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"Refusing to overwrite changed immutable artifact: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def acquire(*, offline: bool = False) -> dict:
    outer_path = ROOT / "data/source/bank-marketing.zip"
    source_manifest_path = ROOT / "data/source/provenance.json"
    downloaded = False
    if outer_path.exists():
        outer = outer_path.read_bytes()
    elif offline:
        raise FileNotFoundError("Pinned outer archive missing; run without --offline to download it")
    else:
        request = urllib.request.Request(LOCK["download_url"], headers={"User-Agent": "CA6003-data-governance/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            outer = response.read()
        downloaded = True
    verify_bytes(outer, LOCK["artifacts"]["data/source/bank-marketing.zip"], "outer archive")
    with zipfile.ZipFile(io.BytesIO(outer)) as archive:
        inner = archive.read("bank.zip")
    verify_bytes(inner, LOCK["artifacts"]["data/source/bank.zip"], "bank.zip")
    with zipfile.ZipFile(io.BytesIO(inner)) as archive:
        csv = archive.read("bank-full.csv")
        names = archive.read("bank-names.txt")
    artifacts = {"data/source/bank-marketing.zip": outer, "data/source/bank.zip": inner,
                 "data/raw/bank-full.csv": csv, "data/raw/bank-names.txt": names}
    for relative, content in artifacts.items():
        verify_bytes(content, LOCK["artifacts"][relative], relative)
    for relative, content in artifacts.items():
        put_immutable(ROOT / relative, content)
    if source_manifest_path.exists():
        provenance = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        for relative, content in artifacts.items():
            if provenance["artifacts"][relative]["sha256"] != sha256_bytes(content):
                raise ValueError("Existing provenance disagrees with locked source")
    else:
        provenance = {
            "dataset_page": LOCK["dataset_page"], "download_url": LOCK["download_url"],
            "acquired_utc": datetime.now(timezone.utc).isoformat() if downloaded else None,
            "acquisition": "official HTTPS download" if downloaded else "verified pre-existing archive; download time unknown",
            "extraction_chain": "bank-marketing.zip > bank.zip > bank-full.csv + bank-names.txt",
            "original_bytes_modified": False,
            "license": "CC BY 4.0", "license_url": LOCK["license_url"],
            "artifacts": {relative: {"bytes": len(content), "sha256": sha256_bytes(content)}
                          for relative, content in artifacts.items()},
        }
        put_immutable(source_manifest_path, (json.dumps(provenance, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return provenance


def prepare(*, offline: bool = False) -> dict:
    acquire(offline=offline)
    raw = read_raw()
    reference = LOCK["integrity_reference"]
    if raw["y"].value_counts().to_dict() != reference["target_counts"]:
        raise ValueError("Predeclared source target-count check failed")
    if int(raw.pdays.eq(-1).sum()) != reference["pdays_minus_one"] or int(raw.pdays.eq(999).sum()) != reference["pdays_999"]:
        raise ValueError("Wrong pdays sentinel/version")
    splits = make_splits(raw)
    manifest = make_manifest(raw, splits)
    put_immutable(ROOT / "data/splits/split_manifest.csv", manifest.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    indices = {name: ids.tolist() for name, ids in splits.items()}
    put_immutable(ROOT / "data/splits/split_indices.json", (json.dumps(indices, separators=(",", ":")) + "\n").encode("utf-8"))
    from src.audit import write_reports
    summary = write_reports(raw, splits)
    summary["source_sha256"] = LOCK["artifacts"]["data/raw/bank-full.csv"]["sha256"]
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use verified local archives; never access network")
    args = parser.parse_args()
    prepare(offline=args.offline)
