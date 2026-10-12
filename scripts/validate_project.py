"""Read-only verification of bytes, assignments, policies, and exported evidence."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.audit import AUDIT_COLUMNS, audit_train, profile_train
from src.data_contract import FEATURES, LOCK, load_partition, load_split_indices, read_raw, validate_saved_splits, verify_bytes


class GovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = read_raw()
        cls.splits = validate_saved_splits(cls.raw)

    def test_all_original_artifacts_are_pinned(self):
        for path, expected in LOCK["artifacts"].items():
            verify_bytes((ROOT / path).read_bytes(), expected, path)

    def test_manifest_complete_disjoint_and_expected_sizes(self):
        expected = {"train": 27126, "val": 9042, "test": 9043}
        self.assertEqual({name: len(ids) for name, ids in self.splits.items()}, expected)
        self.assertEqual(len(set(np.concatenate(list(self.splits.values())))), len(self.raw))
        self.assertEqual(set(np.concatenate(list(self.splits.values()))), set(range(len(self.raw))))

    def test_policy_covers_every_raw_field_and_tracking_only_row_id(self):
        policy = pd.read_csv(ROOT / "notes/feature_policy.csv", keep_default_na=False)
        dictionary = pd.read_csv(ROOT / "notes/data_dictionary.csv", keep_default_na=False)
        self.assertEqual(dictionary.field.tolist(), LOCK["columns"])
        self.assertEqual(policy.field.tolist(), LOCK["columns"] + ["row_id"])
        self.assertEqual(policy.loc[policy.role.eq("input"), "field"].tolist(), FEATURES)
        self.assertTrue(policy.reviewer.eq("pending").all())

    def test_loader_preserves_original_values_labels_and_split_order(self):
        for name in ["train", "val"]:
            X, y = load_partition(name)
            expected = self.raw.loc[self.splits[name]]
            pd.testing.assert_frame_equal(X, expected[FEATURES])
            pd.testing.assert_series_equal(y, expected.y.map({"no": 0, "yes": 1}).astype("int64"))
            self.assertFalse(set(X.columns) & {"row_id", "y", "duration", "campaign", "contact", "day", "month"})

    def test_test_partition_requires_explicit_unsealing(self):
        with self.assertRaisesRegex(ValueError, "sealed"):
            load_partition("test")

    def test_train_audits_recompute_and_no_blockers(self):
        train = self.raw.loc[np.sort(self.splits["train"])]
        expected = audit_train(train)
        actual = pd.read_csv(ROOT / "outputs/quality_audit.csv", keep_default_na=False)
        self.assertEqual(actual.columns.tolist(), AUDIT_COLUMNS)
        pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(set(actual.severity), {"STOP", "INVESTIGATE", "VALID_STATE"})
        self.assertEqual(actual.loc[actual.severity.eq("STOP"), "n_affected"].sum(), 0)
        train_ids = set(self.splits["train"])
        for examples in actual.example_row_ids:
            self.assertTrue(set(json.loads(examples)).issubset(train_ids))
        actual_profile = pd.read_csv(ROOT / "outputs/train_profile.csv")
        pd.testing.assert_frame_equal(actual_profile, profile_train(train), check_dtype=False)

    def test_predeclared_format_and_coverage_reports(self):
        from src.audit import format_checks
        expected = pd.DataFrame([row for name, ids in self.splits.items() for row in format_checks(self.raw.loc[ids], name)])
        actual = pd.read_csv(ROOT / "outputs/format_checks.csv")
        pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(actual.n_violations.sum(), 0)
        self.assertEqual(self.raw.y.value_counts().to_dict(), LOCK["integrity_reference"]["target_counts"])

    def test_split_report_withholds_holdout_label_statistics(self):
        actual = pd.read_csv(ROOT / "outputs/split_summary.csv").set_index("partition")
        for name, ids in self.splits.items():
            self.assertEqual(actual.loc[name, "n_rows"], len(ids))
            if name == "train":
                labels = self.raw.loc[ids, "y"]
                self.assertEqual(actual.loc[name, "n_yes"], int(labels.eq("yes").sum()))
                self.assertEqual(actual.loc[name, "n_no"], int(labels.eq("no").sum()))
            else:
                self.assertTrue(actual.loc[name, ["n_yes", "n_no", "positive_rate"]].isna().all())

    def test_modified_bytes_are_rejected(self):
        path = ROOT / "data/raw/bank-full.csv"
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_bytes(path.read_bytes() + b"\n", LOCK["artifacts"]["data/raw/bank-full.csv"], "synthetic tampering")

    def test_split_json_rejects_silent_type_coercion_and_invalid_ranges(self):
        original = json.loads((ROOT / "data/splits/split_indices.json").read_text(encoding="utf-8"))
        for value in [float(original["train"][0]) + .5, str(original["train"][0]), True, -1, 45211]:
            with self.subTest(value=value):
                changed = {name: ids.copy() for name, ids in original.items()}
                changed["train"][0] = value
                with patch("pathlib.Path.read_text", return_value=json.dumps(changed)):
                    with self.assertRaises(ValueError):
                        load_split_indices()


if __name__ == "__main__":
    unittest.main(verbosity=2)
