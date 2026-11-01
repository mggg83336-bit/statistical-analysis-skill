#!/usr/bin/env python3
"""Reproduce the labelled descriptive-only fixture, not a general statistics engine."""
import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path
import statistics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with args.data.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 2 or set(rows[0]) != {"id", "x", "y"}:
        parser.error("fixture needs id,x,y columns and at least two complete rows")
    if len({row["id"] for row in rows}) != len(rows):
        parser.error("fixture ids must be unique")
    result = {"status": "SYNTHETIC_DEMO", "native_validation": False,
              "python_version": platform.python_version(),
              "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
              "statistics": {}}
    for column in ("x", "y"):
        values = [float(row[column]) for row in rows]
        result["statistics"][column] = {
            "n": len(values), "mean": statistics.mean(values),
            "sample_sd": statistics.stdev(values), "min": min(values), "max": max(values)}
    output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        if args.output.resolve() == args.data.resolve():
            parser.error("output must differ from input")
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
