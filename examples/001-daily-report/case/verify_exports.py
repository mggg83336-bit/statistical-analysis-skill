#!/usr/bin/env python3
"""Independently inspect exported XLSX cached values with standard-library XML/ZIP."""
import argparse, hashlib, json, zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as E

ap = argparse.ArgumentParser()
ap.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent)
args = ap.parse_args()
folder = args.dir
truth = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
expected = {
    "B5": str(Decimal(truth["included_amount_cents"]) / 100),
    "B6": str(truth["included_unique_order_count"]),
    "B8": str(Decimal(truth["refund_amount_cents"]) / 100),
    "B9": str(truth["refund_unique_order_count"]),
    "B11": str(truth["raw_row_count"]), "B12": str(truth["duplicate_excess_row_count"]),
    "B13": str(truth["conflict_order_count"]), "B14": str(truth["exception_raw_row_count"]),
    "B15": str(truth["pending_unique_order_count"]), "B16": str(truth["outside_report_date_count"]),
    "B18": str(Decimal(truth["naive_sum_contrast"]["amount_cents"]) / 100),
}
errors, actual = [], {}
files = []
for p in sorted(folder.glob("*.xlsx")):
    with zipfile.ZipFile(p) as z:
        for name in z.namelist():
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                root = E.fromstring(z.read(name))
                for c in root.findall("m:sheetData/m:row/m:c", ns):
                    if c.get("t") == "e":
                        errors.append([p.name, name, c.get("r")])
                if p.name == "04_订单日报.xlsx" and name == "xl/worksheets/sheet1.xml":
                    cells = {c.get("r"): c for c in root.findall("m:sheetData/m:row/m:c", ns)}
                    actual = {key: cells[key].find("m:v", ns).text for key in expected}
    files.append({"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(files) == 4, "Expected exactly the requested 4 XLSX outputs"
assert actual and all(Decimal(actual[k]) == Decimal(v) for k, v in expected.items()), actual
assert not errors, errors
result = {"executed_at": datetime.now().astimezone().isoformat(), "saved_workbook": "04_订单日报.xlsx", "cached_values": actual, "expected_values_from_truth": expected, "unexpected_error_cells": errors, "xlsx_files": files, "passed": True}
(folder / "xlsx-cache-validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
