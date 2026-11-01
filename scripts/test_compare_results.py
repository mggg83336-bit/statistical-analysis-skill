#!/usr/bin/env python3
"""Behavioral tests for parity validation, including fail-closed inputs."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compare_results import compare_documents, read_json


def fixture():
    reference = {
        "schema_version": 1,
        "provenance": {"engine": "Stata", "version": "19", "kind": "native",
                       "command": "regress y x", "artifact_sha256": "a" * 64},
        "analysis": {
            "target_engine": "Stata", "target_version": "19", "method": "OLS",
            "specification": "y = intercept + x", "data_sha256": "b" * 64,
            "sample": {"n": 40, "ordered_id_sha256": "c" * 64},
            "weights": {"type": "none", "variable": "", "handling": {}},
            "settings": {"confidence_level": 0.95, "missing_policy": "listwise",
                         "test_sidedness": "two-sided", "has_intercept": True,
                         "estimator": "OLS", "covariance": "classical",
                         "df_method": "n-rank(X)", "ci_method": "Student-t Wald",
                         "nested": {"seed": None, "contrasts": ["reference", False]}}},
        "metrics": {"x.estimate": {"kind": "number", "value": 2.0},
                    "x.p": {"kind": "number", "value": 0.001},
                    "n": {"kind": "count", "value": 40},
                    "converged": {"kind": "category", "value": "yes"}}}
    candidate = copy.deepcopy(reference)
    candidate["provenance"].update(engine="Python", version="3.11", kind="reimplementation",
                                   command="verified_ols.py", artifact_sha256="d" * 64)
    policy = {"schema_version": 1,
              "metrics": {"x.estimate": {"abs_tol": 1e-10, "rel_tol": 1e-8},
                          "x.p": {"abs_tol": 1e-12, "rel_tol": 1e-8},
                          "n": {"exact": True}, "converged": {"exact": True}}}
    return reference, candidate, policy


class ComparisonBehavior(unittest.TestCase):
    def setUp(self):
        self.r, self.c, self.p = fixture()

    def compare(self):
        return compare_documents(self.r, self.c, self.p)

    def test_same_values_different_implementations_pass(self):
        result = self.compare()
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["equivalent"])
        self.assertEqual(result["compared_metric_count"], 4)
        self.assertIn("not authenticated", result["limitation"])

    def test_explicit_numeric_tolerance(self):
        self.c["metrics"]["x.estimate"]["value"] = 2.000000001
        self.assertEqual(self.compare()["status"], "pass")
        self.c["metrics"]["x.estimate"]["value"] = 2.000001
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_zero_tolerance_is_exact_numeric_comparison(self):
        self.p["metrics"]["x.estimate"] = {"abs_tol": 0, "rel_tol": 0}
        self.c["metrics"]["x.estimate"]["value"] = 2.000000000000001
        self.assertFalse(self.compare()["equivalent"])

    def test_small_p_values_not_rounded_to_zero(self):
        self.r["metrics"]["x.p"]["value"] = 1e-20
        self.c["metrics"]["x.p"]["value"] = 1e-15
        self.p["metrics"]["x.p"] = {"abs_tol": 0, "rel_tol": 1e-8}
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_different_sample_ids_cannot_pass_identical_coefficients(self):
        self.c["analysis"]["sample"]["ordered_id_sha256"] = "e" * 64
        result = self.compare()
        self.assertFalse(result["equivalent"])
        self.assertTrue(any(d["path"].endswith("ordered_id_sha256") for d in result["differences"]))

    def test_different_data_cannot_pass(self):
        self.c["analysis"]["data_sha256"] = "e" * 64
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_count_is_exact(self):
        self.c["metrics"]["n"]["value"] = 41
        self.assertEqual(self.compare()["status"], "invalid_input")

    def test_shared_omission_of_inference_settings_is_invalid(self):
        for key in ("covariance", "estimator", "df_method", "ci_method", "has_intercept"):
            with self.subTest(key=key):
                self.r, self.c, self.p = fixture()
                del self.r["analysis"]["settings"][key]
                del self.c["analysis"]["settings"][key]
                self.assertEqual(self.compare()["status"], "invalid_input")

    def test_shared_internal_sample_count_contradiction_is_invalid(self):
        for key in ("n", "model.n"):
            with self.subTest(key=key):
                self.r, self.c, self.p = fixture()
                for doc in (self.r, self.c):
                    doc["metrics"][key] = {"kind": "count", "value": 41}
                self.assertEqual(self.compare()["status"], "invalid_input")

    def test_unknown_inference_settings_and_ols_intercept_are_invalid(self):
        for key, value in (("covariance", "default"), ("df_method", "unknown"),
                           ("has_intercept", "not_applicable"), ("has_intercept", 1)):
            with self.subTest(key=key, value=value):
                self.r, self.c, self.p = fixture()
                for doc in (self.r, self.c):
                    doc["analysis"]["settings"][key] = value
                self.assertEqual(self.compare()["status"], "invalid_input")

    def test_count_cannot_be_float_or_bool(self):
        for value in (40.0, True, None, -1):
            with self.subTest(value=value):
                self.c["metrics"]["n"]["value"] = value
                self.assertEqual(self.compare()["status"], "invalid_input")

    def test_number_cannot_be_bool_null_or_string(self):
        for value in (True, False, None, "2.0"):
            with self.subTest(value=value):
                self.c["metrics"]["x.estimate"]["value"] = value
                self.assertEqual(self.compare()["status"], "invalid_input")

    def test_null_metadata_matches_but_not_numeric_zero(self):
        self.assertEqual(self.compare()["status"], "pass")
        self.c["analysis"]["settings"]["nested"]["seed"] = 0
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_nested_bool_is_not_integer(self):
        self.c["analysis"]["settings"]["nested"]["contrasts"][1] = 0
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_metadata_float_and_int_are_distinct(self):
        self.c["analysis"]["settings"]["extra"] = 1.0
        self.r["analysis"]["settings"]["extra"] = 1
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_nonfinite_rejected_everywhere(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for location in ("metric", "metadata", "tolerance"):
                with self.subTest(value=value, location=location):
                    self.r, self.c, self.p = fixture()
                    if location == "metric":
                        self.c["metrics"]["x.estimate"]["value"] = value
                    elif location == "metadata":
                        self.c["analysis"]["settings"]["other"] = value
                    else:
                        self.p["metrics"]["x.estimate"]["abs_tol"] = value
                    self.assertEqual(self.compare()["status"], "invalid_input")

    def test_missing_or_extra_metric_fails(self):
        del self.c["metrics"]["x.p"]
        self.assertEqual(self.compare()["status"], "mismatch")
        self.r, self.c, self.p = fixture()
        self.c["metrics"]["unrequested"] = {"kind": "number", "value": 99}
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_missing_or_extra_metadata_key_fails(self):
        del self.c["analysis"]["settings"]["nested"]
        self.assertEqual(self.compare()["status"], "mismatch")
        self.c["analysis"]["settings"]["unrequested"] = True
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_missing_top_level_key_invalid(self):
        del self.c["analysis"]
        self.assertEqual(self.compare()["status"], "invalid_input")

    def test_no_silent_default_tolerances(self):
        del self.p["metrics"]["x.p"]
        self.assertEqual(self.compare()["status"], "invalid_input")

    def test_negative_or_boolean_tolerance_invalid(self):
        for value in (-1, True, None):
            self.p["metrics"]["x.p"]["abs_tol"] = value
            self.assertEqual(self.compare()["status"], "invalid_input")

    def test_nonexact_count_policy_invalid(self):
        self.p["metrics"]["n"] = {"exact": 1}
        self.assertEqual(self.compare()["status"], "invalid_input")

    def test_reference_requires_native_and_matching_target_version(self):
        self.r["provenance"]["kind"] = "reimplementation"
        self.assertEqual(self.compare()["status"], "invalid_input")
        self.r, self.c, self.p = fixture()
        self.r["provenance"]["version"] = "18"
        self.assertEqual(self.compare()["status"], "invalid_input")

    def test_different_weight_settings_fail(self):
        self.c["analysis"]["weights"] = {"type": "frequency", "variable": "w", "handling": {"zero": "exclude"}}
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_kind_change_fails(self):
        self.c["metrics"]["x.estimate"] = {"kind": "category", "value": "2.0"}
        self.assertEqual(self.compare()["status"], "mismatch")

    def test_duplicate_json_key_and_nonstandard_constants_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
                path.write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_json(path)

    def test_cli_cannot_overwrite_evidence(self):
        script = Path(__file__).with_name("compare_results.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for name, doc in (("reference.json", self.r), ("candidate.json", self.c), ("policy.json", self.p)):
                path = root / name
                path.write_text(json.dumps(doc), encoding="utf-8")
                paths.append(path)
            artifact = root / "native.log"
            artifact.write_text("fixture only", encoding="utf-8")
            for output in [*paths, artifact]:
                before = output.read_bytes()
                run = subprocess.run([sys.executable, str(script), str(paths[0]), str(paths[1]),
                                      "--tolerances", str(paths[2]), "--reference-artifact", str(artifact),
                                      "--output", str(output)], capture_output=True, text=True, check=False)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(json.loads(run.stdout)["status"], "invalid_input")
                self.assertEqual(output.read_bytes(), before)

    def test_cli_exit_codes_and_artifact_hash_check(self):
        script = Path(__file__).with_name("compare_results.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "native-output.log"
            artifact.write_text("test fixture only", encoding="utf-8")
            self.r["provenance"]["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            paths = []
            for name, doc in (("reference.json", self.r), ("candidate.json", self.c), ("policy.json", self.p)):
                path = root / name
                path.write_text(json.dumps(doc), encoding="utf-8")
                paths.append(path)
            command = [sys.executable, str(script), str(paths[0]), str(paths[1]), "--tolerances", str(paths[2]),
                       "--reference-artifact", str(artifact), "--output", str(root / "comparison.json")]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue(json.loads(completed.stdout)["reference_artifact_hash_verified"])
            artifact.write_text("changed", encoding="utf-8")
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 1)
            self.assertFalse(json.loads(completed.stdout)["equivalent"])
            paths[1].write_text("not json", encoding="utf-8")
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(completed.stdout)["status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
