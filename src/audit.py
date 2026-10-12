"""Descriptive data-quality evidence. Open profiling is restricted to train."""
from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from src.data_contract import CATEGORIES, EXPECTED_COLUMNS, FEATURES, NUMERIC, ROOT

AUDIT_COLUMNS = ["check_id", "field", "rule", "partition", "n_affected", "example_row_ids",
                 "severity", "decision", "rationale", "owner"]


def format_checks(frame: pd.DataFrame, partition: str) -> list[dict]:
    """Rules specified before inspection; holdout checks contain no open profiling."""
    checks = []
    def add(rule, n):
        checks.append({"partition": partition, "rule": rule, "n_violations": int(n), "passed": int(n) == 0})
    add("exact_17_columns_in_source_order", int(list(frame.columns) != EXPECTED_COLUMNS))
    add("no_actual_null_cells", frame.isna().sum().sum())
    add("no_empty_or_whitespace_cells", frame.astype(str).apply(lambda s: s.str.strip().eq("")).sum().sum())
    for column in NUMERIC:
        add(f"{column}:integer_dtype", int(not pd.api.types.is_integer_dtype(frame[column])))
    for column, values in CATEGORIES.items():
        add(f"{column}:documented_category", (~frame[column].isin(values)).sum())
    for name, mask in {
        "age:positive": frame.age.le(0), "day:1_to_31": ~frame.day.between(1, 31),
        "duration:nonnegative": frame.duration.lt(0), "campaign:at_least_one": frame.campaign.lt(1),
        "pdays:minus_one_or_nonnegative": frame.pdays.lt(-1), "previous:nonnegative": frame.previous.lt(0),
    }.items():
        add(name, mask.sum())
    return checks


def profile_train(train: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in EXPECTED_COLUMNS:
        col = train[name]
        text = col.astype(str)
        item = {"partition": "train", "field": name, "dtype": str(col.dtype), "n_rows": len(col),
                "n_null": int(col.isna().sum()), "n_empty": int(text.eq("").sum()),
                "n_whitespace_only": int((text.str.strip().eq("") & text.ne("")).sum()),
                "n_unknown": int(text.eq("unknown").sum()), "n_minus_one": int(text.eq("-1").sum()),
                "n_unique": int(col.nunique(dropna=False))}
        if name in NUMERIC:
            for label, q in [("min", 0), ("q01", .01), ("q25", .25), ("median", .5), ("q75", .75), ("q99", .99), ("max", 1)]:
                item[label] = float(col.quantile(q))
        rows.append(item)
    return pd.DataFrame(rows)


def audit_train(train: pd.DataFrame) -> pd.DataFrame:
    rows = []
    def add(check_id, field, rule, mask, severity, decision, rationale, owner="A"):
        selected = train.index[np.asarray(mask, dtype=bool)]
        rows.append(dict(zip(AUDIT_COLUMNS, [check_id, field, rule, "train", len(selected),
                    json.dumps([int(x) for x in selected[:5]]), severity, decision, rationale, owner])))
    for name in EXPECTED_COLUMNS:
        values = train[name]
        missing = values.isna() | values.astype(str).str.strip().eq("")
        add("missing_" + name, name, "actual null or empty/whitespace cell", missing, "STOP",
            "Stop if affected; otherwise pass", "Unexpected actual missingness requires source/parse review; no automatic imputation")
        if name in CATEGORIES:
            add("category_" + name, name, "value outside documented bank-names categories", ~values.isin(CATEGORIES[name]), "STOP",
                "Stop if affected; otherwise pass", "Version/format mismatch must be resolved without recoding records")
        unknown = values.astype(str).eq("unknown")
        if "unknown" in CATEGORIES.get(name, []):
            add("unknown_" + name, name, "literal category unknown", unknown, "VALID_STATE", "Retain raw category",
                "Literal unknown is not NaN; C may compare job/education strategies only; poutcome stays unchanged", "A; C implementation pending")
    for name, mask in {
        "age": train.age.le(0), "day": ~train.day.between(1, 31), "duration": train.duration.lt(0),
        "campaign": train.campaign.lt(1), "pdays": train.pdays.lt(-1), "previous": train.previous.lt(0),
    }.items():
        add("domain_" + name, name, "violates predeclared integer domain", mask, "STOP",
            "Stop if affected; otherwise pass", "Verify raw provenance and documentation before any repair")
    add("pdays_never", "pdays", "pdays == -1", train.pdays.eq(-1), "VALID_STATE", "Retain sentinel in raw",
        "Never contacted in a previous campaign; not missing days; S is implemented by C")
    add("pdays_zero", "pdays", "pdays == 0", train.pdays.eq(0), "VALID_STATE", "Retain distinct from -1",
        "Zero elapsed days is a nonnegative interval; it must not mean never contacted")
    add("negative_balance", "balance", "balance < 0", train.balance.lt(0), "VALID_STATE", "Retain negative balance",
        "Average annual balance in EUR can be negative; no evidence of parsing error")
    for name in ["balance", "previous"]:
        cut = float(train[name].quantile(.99))
        add("upper_tail_" + name, name, f"value > training 99th percentile ({cut:g})", train[name].gt(cut), "INVESTIGATE",
            "Retain; B reviews tail evidence", "A descriptive training-only flag, not an invalidity boundary or deletion rule", "A; B review pending")
    never = train.pdays.eq(-1)
    zero_prev = train.previous.eq(0)
    add("history_never_positive_previous", "pdays,previous", "pdays == -1 and previous > 0", never & ~zero_prev, "INVESTIGATE",
        "Retain; review any affected rows", "Different campaign-history definitions may explain a mismatch; do not fabricate contact history", "A; B/C review pending")
    add("history_contacted_zero_previous", "pdays,previous", "pdays >= 0 and previous == 0", ~never & zero_prev, "INVESTIGATE",
        "Retain; review any affected rows", "A semantic consistency check; not grounds for automatic deletion", "A; B/C review pending")
    add("history_contacted_unknown_outcome", "pdays,poutcome", "pdays >= 0 and poutcome == unknown", ~never & train.poutcome.eq("unknown"), "INVESTIGATE",
        "Retain unknown outcome", "Unknown outcome cannot automatically be interpreted as no previous contact", "A; B/C review pending")
    add("history_never_known_outcome", "pdays,poutcome", "pdays == -1 and poutcome != unknown", never & train.poutcome.ne("unknown"), "INVESTIGATE",
        "Retain; verify meaning", "A known outcome alongside never-contacted requires review rather than invented replacement", "A; B/C review pending")
    add("duplicate_full_rows", "all 17 raw fields", "all members of exact duplicate groups (keep=False)", train.duplicated(keep=False), "INVESTIGATE",
        "Retain all rows", "Matching public records do not establish duplicate people; row_id is not customer ID")
    for scope, features in [("raw16", EXPECTED_COLUMNS[:-1]), ("allowed11", FEATURES)]:
        n_labels = train.groupby(features, dropna=False, sort=False)["y"].transform("nunique")
        add("conflicting_labels_" + scope, ",".join(features), "same feature values with more than one target label; affected group members", n_labels.gt(1), "INVESTIGATE",
            "Retain; document identifiability limitation", "Feature equality is not identity; do not merge clients or choose a preferred label")
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def write_reports(raw: pd.DataFrame, splits: dict[str, np.ndarray], root: Path = ROOT) -> dict:
    out = root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    train = raw.loc[np.sort(splits["train"])]
    profile = profile_train(train)
    audit = audit_train(train)
    profile.to_csv(out / "train_profile.csv", index=False, lineterminator="\n")
    audit.to_csv(out / "quality_audit.csv", index=False, lineterminator="\n")
    formats = pd.DataFrame([check for name, ids in splits.items() for check in format_checks(raw.loc[ids], name)])
    formats.to_csv(out / "format_checks.csv", index=False, lineterminator="\n")
    split_summary = []
    for name, ids in splits.items():
        targets = raw.loc[ids, "y"] if name == "train" else None
        split_summary.append({"partition": name, "n_rows": len(ids),
                              "n_no": int(targets.eq("no").sum()) if targets is not None else None,
                              "n_yes": int(targets.eq("yes").sum()) if targets is not None else None,
                              "positive_rate": float(targets.eq("yes").mean()) if targets is not None else None,
                              "purpose": "training profile" if name == "train" else "structure/coverage only; label statistics withheld"})
    pd.DataFrame(split_summary).to_csv(out / "split_summary.csv", index=False, lineterminator="\n")
    history = train.assign(pdays_state=np.where(train.pdays.eq(-1), "never_-1", "contacted_ge0"),
                           previous_state=np.where(train.previous.eq(0), "zero", "positive"))
    counts = history.groupby(["pdays_state", "previous_state", "poutcome"], dropna=False).size().rename("n").reset_index()
    counts.insert(0, "partition", "train")
    counts["denominator"] = len(train)
    counts.to_csv(out / "train_history_consistency.csv", index=False, lineterminator="\n")
    summary = {
        "raw_shape": list(raw.shape), "split_sizes": {name: len(ids) for name, ids in splits.items()},
        "open_profile_partition": "train", "training_rows": len(train),
        "holdout_policy": "predeclared schema, category membership, numeric domain and row coverage checks only; no holdout label statistics",
        "format_violations": int(formats.n_violations.sum()),
        "audit_stop_affected": int(audit.loc[audit.severity.eq("STOP"), "n_affected"].sum()),
        "training_exact_duplicate_group_members": int(train.duplicated(keep=False).sum()),
        "training_duplicate_excess_rows": int(train.duplicated(keep="first").sum()),
        "training_pdays_minus_one": int(train.pdays.eq(-1).sum()),
        "training_pdays_zero": int(train.pdays.eq(0).sum()),
        "training_unknown_job": int(train.job.eq("unknown").sum()),
        "training_unknown_education": int(train.education.eq("unknown").sum()),
        "training_negative_balance": int(train.balance.lt(0).sum()),
        "rows_deleted": 0, "imputation_fitted": False, "scaler_fitted": False, "models_fitted": 0,
        "student_review": "pending", "C_semantic_review": "pending",
    }
    (out / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    environment = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                   "scikit-learn": sklearn.__version__, "platform": platform.system(), "machine": platform.machine()}
    (out / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8", newline="\n")
    if summary["format_violations"] or summary["audit_stop_affected"]:
        raise ValueError("Blocking data-quality failure; inspect saved audit, do not clean silently")
    return summary
