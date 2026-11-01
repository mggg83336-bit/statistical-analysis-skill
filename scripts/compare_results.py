#!/usr/bin/env python3
"""Compare structured statistical output against a declared native baseline.

See references/comparison.md. This validates numerical agreement for the supplied
cells and metadata; it does not authenticate provenance or prove general parity.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from decimal import Decimal
from pathlib import Path

HASH = re.compile(r"^[0-9a-f]{64}$")
LIMITATION = ("Agreement applies only to the supplied analysis and cells. Native "
              "provenance is declared by the producer and is not authenticated by this checker.")


class InputError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def exact_keys(obj, keys, path):
    require(type(obj) is dict, f"{path}: expected an object")
    require(set(obj) == set(keys), f"{path}: expected keys {sorted(keys)}; got {sorted(obj)}")


def nonempty_string(value, path):
    require(type(value) is str and bool(value.strip()), f"{path}: expected a nonempty string")


def number(value, path):
    require(type(value) in (int, float), f"{path}: expected a number, not boolean or null")
    require(not isinstance(value, float) or math.isfinite(value), f"{path}: nonfinite number")
    return Decimal(str(value))


def validate_tree(value, path):
    """Reject non-JSON values and nonfinite floats anywhere, including metadata."""
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, f"{path}: object keys must be strings")
            validate_tree(item, f"{path}.{key}")
    elif type(value) is list:
        for index, item in enumerate(value):
            validate_tree(item, f"{path}[{index}]")
    elif type(value) is float:
        require(math.isfinite(value), f"{path}: nonfinite number")
    else:
        require(value is None or type(value) in (str, int, bool), f"{path}: unsupported value type")


def validate_document(doc, label, reference=False):
    validate_tree(doc, label)
    exact_keys(doc, {"schema_version", "provenance", "analysis", "metrics"}, label)
    require(type(doc["schema_version"]) is int and doc["schema_version"] == 1,
            f"{label}.schema_version: expected integer 1")
    p = doc["provenance"]
    exact_keys(p, {"engine", "version", "kind", "command", "artifact_sha256"}, f"{label}.provenance")
    for key in ("engine", "version", "command"):
        nonempty_string(p[key], f"{label}.provenance.{key}")
    require(p["kind"] in ("native", "reimplementation"), f"{label}.provenance.kind: unsupported kind")
    require(type(p["artifact_sha256"]) is str and HASH.fullmatch(p["artifact_sha256"]),
            f"{label}.provenance.artifact_sha256: expected lowercase SHA-256")
    if reference:
        require(p["engine"] in ("SPSS", "Stata") and p["kind"] == "native",
                f"{label}.provenance: reference must declare native SPSS or Stata")
    a = doc["analysis"]
    exact_keys(a, {"target_engine", "target_version", "method", "specification", "data_sha256",
                   "sample", "weights", "settings"}, f"{label}.analysis")
    require(a["target_engine"] in ("SPSS", "Stata"), f"{label}.analysis.target_engine: expected SPSS or Stata")
    for key in ("target_version", "method", "specification"):
        nonempty_string(a[key], f"{label}.analysis.{key}")
    require(type(a["data_sha256"]) is str and HASH.fullmatch(a["data_sha256"]),
            f"{label}.analysis.data_sha256: expected lowercase SHA-256")
    if reference:
        require(p["engine"] == a["target_engine"] and p["version"] == a["target_version"],
                f"{label}: native engine/version must match the analysis target")
    s = a["sample"]
    exact_keys(s, {"n", "ordered_id_sha256"}, f"{label}.analysis.sample")
    require(type(s["n"]) is int and s["n"] >= 0, f"{label}.analysis.sample.n: expected nonnegative integer")
    require(type(s["ordered_id_sha256"]) is str and HASH.fullmatch(s["ordered_id_sha256"]),
            f"{label}.analysis.sample.ordered_id_sha256: expected lowercase SHA-256")
    w = a["weights"]
    exact_keys(w, {"type", "variable", "handling"}, f"{label}.analysis.weights")
    require(w["type"] in ("none", "frequency", "analytic", "probability", "importance", "other"),
            f"{label}.analysis.weights.type: unsupported type")
    require(type(w["variable"]) is str, f"{label}.analysis.weights.variable: expected string")
    require(type(w["handling"]) is dict, f"{label}.analysis.weights.handling: expected object")
    if w["type"] == "none":
        require(w["variable"] == "", f"{label}.analysis.weights.variable: must be empty for unweighted analysis")
    else:
        nonempty_string(w["variable"], f"{label}.analysis.weights.variable")
        require(bool(w["handling"]), f"{label}.analysis.weights.handling: weighted analysis needs explicit handling")
    settings = a["settings"]
    required_settings = {"confidence_level", "missing_policy", "test_sidedness", "estimator",
                         "covariance", "df_method", "ci_method", "has_intercept"}
    require(type(settings) is dict and required_settings <= set(settings),
            f"{label}.analysis.settings: requires {sorted(required_settings)}")
    ci = number(settings["confidence_level"], f"{label}.analysis.settings.confidence_level")
    require(0 < ci < 1, f"{label}.analysis.settings.confidence_level: must be between 0 and 1")
    for key in ("missing_policy", "test_sidedness", "estimator", "covariance", "df_method", "ci_method"):
        nonempty_string(settings[key], f"{label}.analysis.settings.{key}")
        require(settings[key].strip().lower() not in ("default", "unknown", "unspecified"),
                f"{label}.analysis.settings.{key}: effective setting must be explicit")
    require(type(settings["has_intercept"]) is bool or settings["has_intercept"] == "not_applicable",
            f"{label}.analysis.settings.has_intercept: expected boolean or not_applicable")
    if a["method"].upper() == "OLS":
        require(type(settings["has_intercept"]) is bool,
                f"{label}.analysis.settings.has_intercept: OLS requires boolean")
    metrics = doc["metrics"]
    require(type(metrics) is dict and bool(metrics), f"{label}.metrics: expected nonempty object")
    for key, metric in metrics.items():
        nonempty_string(key, f"{label}.metrics key")
        path = f"{label}.metrics.{key}"
        exact_keys(metric, {"kind", "value"}, path)
        kind, value = metric["kind"], metric["value"]
        require(kind in ("number", "count", "category"), f"{path}.kind: unsupported kind")
        if kind == "number":
            number(value, f"{path}.value")
        elif kind == "count":
            require(type(value) is int and value >= 0, f"{path}.value: expected nonnegative integer count")
        else:
            require(type(value) is str, f"{path}.value: expected string category")
    for sample_key in ("n", "model.n"):
        if sample_key in metrics:
            metric = metrics[sample_key]
            require(metric["kind"] == "count" and metric["value"] == s["n"],
                    f"{label}.metrics.{sample_key}: reserved raw sample count must match analysis.sample.n")


def metadata_differences(left, right, path="analysis"):
    if type(left) is not type(right):
        return [{"path": path, "reason": "metadata_type_mismatch", "reference": left, "candidate": right}]
    if type(left) is dict:
        differences = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}.{key}"
            if key not in left or key not in right:
                differences.append({"path": child, "reason": "metadata_key_missing"})
            else:
                differences.extend(metadata_differences(left[key], right[key], child))
        return differences
    if type(left) is list:
        if len(left) != len(right):
            return [{"path": path, "reason": "metadata_list_length_mismatch"}]
        differences = []
        for i, (a, b) in enumerate(zip(left, right)):
            differences.extend(metadata_differences(a, b, f"{path}[{i}]"))
        return differences
    if left != right:
        return [{"path": path, "reason": "metadata_value_mismatch", "reference": left, "candidate": right}]
    return []


def validate_policy(policy, metrics):
    validate_tree(policy, "tolerances")
    exact_keys(policy, {"schema_version", "metrics"}, "tolerances")
    require(type(policy["schema_version"]) is int and policy["schema_version"] == 1,
            "tolerances.schema_version: expected integer 1")
    exact_keys(policy["metrics"], set(metrics), "tolerances.metrics")
    for key, metric in metrics.items():
        rule = policy["metrics"][key]
        path = f"tolerances.metrics.{key}"
        if metric["kind"] == "number":
            exact_keys(rule, {"abs_tol", "rel_tol"}, path)
            for field in ("abs_tol", "rel_tol"):
                require(number(rule[field], f"{path}.{field}") >= 0, f"{path}.{field}: must be nonnegative")
        else:
            exact_keys(rule, {"exact"}, path)
            require(rule["exact"] is True, f"{path}.exact: must be true")


def compare_documents(reference, candidate, policy):
    """Return a JSON-serializable result; invalid inputs cannot produce a pass."""
    result = {"schema_version": 1, "status": "invalid_input", "equivalent": False,
              "limitation": LIMITATION}
    try:
        validate_document(reference, "reference", reference=True)
        validate_document(candidate, "candidate")
        validate_policy(policy, reference["metrics"])
        differences = metadata_differences(reference["analysis"], candidate["analysis"])
        ref_metrics, cand_metrics = reference["metrics"], candidate["metrics"]
        missing = sorted(set(ref_metrics) - set(cand_metrics))
        extra = sorted(set(cand_metrics) - set(ref_metrics))
        for key in missing:
            differences.append({"path": f"metrics.{key}", "reason": "candidate_metric_missing"})
        for key in extra:
            differences.append({"path": f"metrics.{key}", "reason": "unexpected_candidate_metric"})
        cells = []
        for key in sorted(set(ref_metrics) & set(cand_metrics)):
            a, b = ref_metrics[key], cand_metrics[key]
            cell = {"metric": key, "reference": a["value"], "candidate": b["value"]}
            if a["kind"] != b["kind"]:
                cell.update(passed=False, reason="metric_kind_mismatch")
            elif a["kind"] == "number":
                left, right = Decimal(str(a["value"])), Decimal(str(b["value"]))
                rule = policy["metrics"][key]
                diff = abs(left - right)
                threshold = max(Decimal(str(rule["abs_tol"])), Decimal(str(rule["rel_tol"])) * max(abs(left), abs(right)))
                cell.update(passed=diff <= threshold, absolute_difference=str(diff), allowed_difference=str(threshold))
            else:
                cell.update(passed=a["value"] == b["value"])
            cells.append(cell)
            if not cell["passed"]:
                differences.append({"path": f"metrics.{key}", "reason": cell.get("reason", "value_outside_tolerance")})
        passed = not differences
        result.update(status="pass" if passed else "mismatch", equivalent=passed,
                      compared_metric_count=len(cells), differences=differences, cells=cells,
                      reference_provenance=reference["provenance"], candidate_provenance=candidate["provenance"])
    except (InputError, TypeError, ValueError, OverflowError, ArithmeticError) as exc:
        result["errors"] = [str(exc)]
    return result


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise InputError(f"duplicate JSON object key: {key}")
        obj[key] = value
    return obj


def read_json(path):
    def reject_constant(value):
        raise InputError(f"nonstandard JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=no_duplicates,
                      parse_constant=reject_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", help="structured native reference JSON")
    parser.add_argument("candidate", help="structured candidate JSON")
    parser.add_argument("--tolerances", required=True, help="explicit per-metric tolerance JSON")
    parser.add_argument("--output", help="also save the machine-readable report")
    parser.add_argument("--reference-artifact", help="verify the reference artifact file's SHA-256 against declared provenance")
    args = parser.parse_args(argv)
    protected = [args.reference, args.candidate, args.tolerances]
    if args.reference_artifact:
        protected.append(args.reference_artifact)
    if args.output and Path(args.output).resolve() in {Path(p).resolve() for p in protected}:
        print(json.dumps({"schema_version": 1, "status": "invalid_input", "equivalent": False,
                          "errors": ["Output must not overwrite any input or native artifact."],
                          "limitation": LIMITATION}, ensure_ascii=False))
        return 2
    try:
        reference, candidate, policy = (read_json(p) for p in (args.reference, args.candidate, args.tolerances))
        result = compare_documents(reference, candidate, policy)
        if args.reference_artifact and result["status"] != "invalid_input":
            hasher = hashlib.sha256()
            with Path(args.reference_artifact).open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(block)
            verified = hasher.hexdigest() == reference["provenance"]["artifact_sha256"]
            result["reference_artifact_hash_verified"] = verified
            if not verified:
                result["equivalent"] = False
                result["status"] = "mismatch"
                result["differences"].append({"path": "reference.provenance.artifact_sha256", "reason": "artifact_hash_mismatch"})
        else:
            result["reference_artifact_hash_verified"] = None
    except (OSError, ValueError, TypeError) as exc:
        result = {"schema_version": 1, "status": "invalid_input", "equivalent": False,
                  "errors": [str(exc)], "limitation": LIMITATION}
    output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        try:
            Path(args.output).write_text(output, encoding="utf-8")
        except OSError as exc:
            print(json.dumps({"schema_version": 1, "status": "invalid_input", "equivalent": False,
                              "errors": [f"Cannot save report: {exc}"]}, ensure_ascii=False))
            return 2
    print(output, end="")
    return 0 if result["status"] == "pass" else 1 if result["status"] == "mismatch" else 2


if __name__ == "__main__":
    sys.exit(main())
