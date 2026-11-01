#!/usr/bin/env python3
"""Reproduce this synthetic order-snapshot case using Python standard library only."""
from __future__ import annotations
import argparse, copy, csv, hashlib, json, re, sys, zipfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

REPORT_DATE = "2026-10-31"
SCHEMAS = [
    ("01_门店A.xlsx", ["订单编号", "下单日期", "实收金额", "支付状态", "退款状态"], "%Y/%m/%d"),
    ("02_门店B.xlsx", ["order_id", "order_date", "amount", "payment", "refund"], "%d-%m-%Y"),
    ("03_门店C.xlsx", ["单号", "日期", "金额(元)", "状态", "是否退款"], "%Y年%m月%d日"),
]

def make_inputs():
    a = [("OD-001", "100.00", "paid", "no"), ("OD-002", "240.00", "paid", "no"), ("OD-003", "88.50", "paid", "no"), ("OD-004", "150.00", "paid", "yes"), ("OD-005", "199.00", "pending", "no"), ("OD-006", "", "paid", "no"), ("", "75.00", "paid", "no"), ("OD-008", "360.00", "paid", "no"), ("OD-009", "500.00", "paid", "no"), ("OD-010", "128.00", "paid", "no")]
    b = [(" od-001 ", "100.00", "paid", "no"), ("OD-002", "240.00", "paid", "no"), ("OD-009", "550.00", "paid", "no"), ("OD-011", "320.00", "paid", "no"), ("OD-012", "49.90", "paid", "no"), ("OD-013", "80.00", "paid", "yes"), ("OD-014", "660.00", "paid", "no"), ("OD-015", "99.00", "pending", "no"), ("OD-016", "180.00", "paid", "no"), ("OD-017", "50.00", "paid", "no")]
    c = [("OD-003", "88.50", "paid", "no"), ("OD-011", "320.00", "paid", "no"), ("OD-014", "660.00", "paid", "no"), ("OD-018", "99.90", "paid", "no"), ("OD-019", "210.00", "paid", "no"), ("OD-020", "388.00", "paid", "no"), ("OD-021", "120.00", "paid", "yes"), ("OD-022", "168.00", "paid", "no"), ("OD-023", "299.00", "paid", "no"), ("OD-024", "59.90", "paid", "no")]
    files = []
    for i, records in enumerate((a, b, c)):
        filename, headers, fmt = SCHEMAS[i]
        rows = []
        for j, (oid, amt, pay, refund) in enumerate(records):
            date = datetime(2026, 10, 30 if i == 0 and j == 7 else 31).strftime(fmt)
            text = ("¥" + amt if i == 0 else "CNY " + amt if i == 1 else amt + "元") if amt else ""
            pays = {"paid": ["已支付", "paid", "付款成功"][i], "pending": ["待支付", "pending", "未付款"][i]}
            refs = {"no": ["未退款", "no", "否"][i], "yes": ["已退款", "yes", "是"][i]}
            rows.append([oid, date, text, pays[pay], refs[refund]])
        files.append({"filename": filename, "sheet": "原始订单", "headers": headers, "rows": rows})
    return {"synthetic": True, "notice": "全部为合成演示数据，不含真人资料。订单快照非财务凭证。", "files": files}

def money(text):
    s = re.sub(r"[¥￥,\s]|CNY|元", "", str(text)).strip()
    if not s:
        return None
    try:
        v = Decimal(s)
    except InvalidOperation as e:
        raise ValueError(f"invalid amount {text!r}") from e
    if not v.is_finite() or v < 0 or v != v.quantize(Decimal("0.01")):
        raise ValueError(f"invalid CNY cents {text!r}")
    return int(v * 100)

def normalize(raw):
    out = []
    pay_map = {"已支付": "已支付", "paid": "已支付", "付款成功": "已支付", "待支付": "待支付", "pending": "待支付", "未付款": "待支付"}
    refund_map = {"未退款": "未退款", "no": "未退款", "否": "未退款", "已退款": "已退款", "yes": "已退款", "是": "已退款"}
    for i, f in enumerate(raw["files"]):
        for n, values in enumerate(f["rows"], 2):
            oid, date, amt, pay, refund = values
            issues = []
            oid = str(oid).strip().upper()
            if not oid:
                issues.append("缺订单ID")
            try:
                cents = money(amt)
                if cents is None:
                    issues.append("缺金额")
            except ValueError:
                cents = None
                issues.append("金额格式无效")
            try:
                date_norm = datetime.strptime(str(date), SCHEMAS[i][2]).date().isoformat()
            except ValueError:
                date_norm = None
                issues.append("日期无效")
            pay_norm = pay_map.get(str(pay).strip())
            refund_norm = refund_map.get(str(refund).strip())
            if pay_norm is None or refund_norm is None:
                issues.append("状态无效")
            out.append({"source_id": f"F{i+1}-R{n:02d}", "source_file": f["filename"], "source_sheet": f["sheet"], "source_row": n, "order_id": oid, "order_date": date_norm, "amount_cents": cents, "currency": "CNY", "payment_status": pay_norm, "refund_status": refund_norm, "issues": issues, "original": dict(zip(f["headers"], values))})
    return out

def analyze(raw):
    rows = normalize(raw)
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["order_id"] or "__MISSING__" + r["source_id"]].append(r)
    clean, exceptions, mappings = [], [], []
    conflict_ids = []
    for key, group in grouped.items():
        signatures = {(r["order_date"], r["amount_cents"], r["payment_status"], r["refund_status"], r["currency"]) for r in group}
        conflicting = len(group) > 1 and len(signatures) > 1
        if conflicting:
            conflict_ids.append(key)
        source_ids = [r["source_id"] for r in group]
        mapping = {"order_id": group[0]["order_id"], "source_ids": source_ids, "source_records": [{"file": r["source_file"], "sheet": r["source_sheet"], "row": r["source_row"], "source_id": r["source_id"]} for r in group], "conflict": conflicting}
        mappings.append(mapping)
        if conflicting or any(r["issues"] for r in group):
            for r in group:
                r["disposition"] = "待确认"
                r["reason"] = "同ID规范内容冲突，整单待确认" if conflicting else "、".join(r["issues"])
                r["canonical_source_id"] = ""
                exceptions.append(r)
            continue
        keeper = group[0]
        if keeper["order_date"] != REPORT_DATE:
            status, why = "非报表日", "订单日期不等于报表日"
        elif keeper["refund_status"] == "已退款":
            status, why = "退款单列", "已退款，不计入日报订单金额"
        elif keeper["payment_status"] != "已支付":
            status, why = "待支付", "未支付，不计入日报订单金额"
        else:
            status, why = "纳入日报", "报表日、已支付、未退款且无关键缺失/冲突的唯一订单"
        for j, r in enumerate(group):
            r["disposition"] = status if j == 0 else "完全重复"
            r["reason"] = why if j == 0 else "规范内容完全相同，仅保留一份；来源全部保留"
            r["canonical_source_id"] = keeper["source_id"]
        clean.append({k: keeper[k] for k in ("order_id", "order_date", "amount_cents", "currency", "payment_status", "refund_status")} | {"disposition": status, "source_ids": source_ids, "canonical_source_id": keeper["source_id"]})
    totals = Counter(r["disposition"] for r in rows)
    included = [r for r in clean if r["disposition"] == "纳入日报"]
    refunded = [r for r in clean if r["disposition"] == "退款单列"]
    naive = sum(r["amount_cents"] for r in rows if r["amount_cents"] is not None)
    truth = {
        "synthetic": True, "report_date": REPORT_DATE, "currency": "CNY", "amount_unit": "分（整数）",
        "metric_label": "纳入日报订单金额（演示口径）",
        "scope": "按订单日期，只合计2026-10-31已支付且未退款、关键字段完整且无同ID冲突的唯一订单；这不是财务收入或税务结论。",
        "deduplication": "同ID且日期/金额/支付/退款/币种规范内容完全相同，仅保留1份，保留全部来源；同ID任一内容不同整单待确认，不选最新。",
        "raw_file_count": len(raw["files"]), "raw_row_count": len(rows),
        "clean_unique_order_count": len(clean), "included_unique_order_count": len(included),
        "included_amount_cents": sum(r["amount_cents"] for r in included),
        "included_amount_yuan": f"{Decimal(sum(r['amount_cents'] for r in included))/100:.2f}",
        "included_order_ids": [r["order_id"] for r in included],
        "duplicate_excess_row_count": totals["完全重复"], "duplicate_excess_amount_cents": sum(r["amount_cents"] for r in rows if r["disposition"] == "完全重复"),
        "conflict_order_count": len(conflict_ids), "conflict_order_ids": conflict_ids,
        "conflict_raw_row_count": sum(1 for r in exceptions if "冲突" in r["reason"]),
        "conflict_observed_amount_cents": sum(r["amount_cents"] or 0 for r in exceptions if "冲突" in r["reason"]),
        "missing_key_row_count": sum(bool(r["issues"]) for r in rows),
        "missing_key_known_amount_cents": sum(r["amount_cents"] or 0 for r in rows if r["issues"]),
        "missing_amount_row_count": sum("缺金额" in r["issues"] for r in rows),
        "missing_id_row_count": sum("缺订单ID" in r["issues"] for r in rows),
        "exception_raw_row_count": len(exceptions),
        "refund_unique_order_count": len(refunded), "refund_amount_cents": sum(r["amount_cents"] for r in refunded),
        "pending_unique_order_count": totals["待支付"], "pending_amount_cents": sum(r["amount_cents"] for r in clean if r["disposition"] == "待支付"),
        "outside_report_date_count": totals["非报表日"], "outside_report_date_amount_cents": sum(r["amount_cents"] for r in clean if r["disposition"] == "非报表日"),
        "row_disposition_counts": dict(totals),
        "naive_sum_contrast": {"label": "故意设置的错误对照：直接相加所有可解析原始金额，忽略重复/状态/日期/缺ID/冲突", "amount_cents": naive, "amount_yuan": f"{Decimal(naive)/100:.2f}", "overstatement_vs_demo_cents": naive - sum(r["amount_cents"] for r in included), "not_an_agent_failure": True},
    }
    combos = defaultdict(list)
    for r in included:
        combination = tuple(sorted({int(s.split("-")[0][1:]) for s in r["source_ids"]}))
        combos[combination].append(r)
    trace_orders = {}
    for oid in ("OD-001", "OD-003"):
        order = next(r for r in included if r["order_id"] == oid)
        mapping = next(m for m in mappings if m["order_id"] == oid)
        trace_orders[oid] = {"order_id": oid, "amount_cents": order["amount_cents"], "source_records": mapping["source_records"], "counted_once": True}
    truth["report_fields"] = {
        "source_combinations_definition": "按一笔纳入订单出现过的完整文件组合互斥分组。每个ID只属一组，所有组金额合计等于日报金额；这是快照出现组合，不是门店或渠道业绩。",
        "source_combinations": [{"label": "+".join(chr(64+i) for i in key), "source_files": [raw["files"][i-1]["filename"] for i in key], "order_ids": [r["order_id"] for r in values], "count": len(values), "amount_cents": sum(r["amount_cents"] for r in values)} for key, values in sorted(combos.items())],
        "trace_example": trace_orders["OD-003"],
        "trace_examples": list(trace_orders.values()),
        "conflict_example": {"order_id": "OD-009", "resolution": "整单待确认，全部快照不纳入日报", "records": [{"source_id": r["source_id"], "file": r["source_file"], "sheet": r["source_sheet"], "row": r["source_row"], "amount_cents": r["amount_cents"]} for r in exceptions if r["order_id"] == "OD-009"]},
        "raw_file_rows": [{"file": f["filename"], "sheet": f["sheet"], "table_range": "A1:E11", "header_row": 1, "data_row_count": len(f["rows"])} for f in raw["files"]],
    }
    return rows, clean, exceptions, mappings, truth

def read_xlsx(path):
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            strings = ["".join(si.itertext()) for si in root]
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = []
        for rr in root.findall("m:sheetData/m:row", ns):
            if int(rr.get("r")) > 11:
                continue  # This case's documented source table is A1:E11; notice below it is not an order.
            vals = []
            for c in rr.findall("m:c", ns):
                v = c.find("m:v", ns)
                t = c.get("t")
                if t == "inlineStr":
                    val = "".join(c.find("m:is", ns).itertext())
                elif t == "s":
                    val = strings[int(v.text)] if v is not None else ""
                else:
                    val = v.text if v is not None else ""
                index = 0
                for char in re.sub(r"\d", "", c.get("r")):
                    index = index * 26 + ord(char) - 64
                while len(vals) < index:
                    vals.append("")
                vals[index - 1] = val
            rows.append(vals)
        return rows

def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--xlsx-dir", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    raw = make_inputs()
    source_mode = "deterministic synthetic source specification"
    if args.xlsx_dir:
        for f in raw["files"]:
            grid = read_xlsx(args.xlsx_dir / f["filename"])
            if grid[0] != f["headers"] or len(grid) != 11:
                raise ValueError("Unexpected source schema/row count")
            f["rows"] = [(r + [""] * 5)[:5] for r in grid[1:]]
        source_mode = "actual XLSX files parsed with zipfile and ElementTree"
    rows, clean, exceptions, mappings, truth = analyze(raw)
    assert len(rows) == 30
    assert sum(truth["row_disposition_counts"].values()) == 30
    # Meaningful changed-input plus boundary/exception case; does not mirror every implementation branch.
    changed = copy.deepcopy(raw)
    changed["files"][0]["rows"][9][2] = "¥129.00"
    changed["files"][2]["rows"][9][2] = ""
    changed_truth = analyze(changed)[4]
    expected_delta = 100 - 5990
    assert changed_truth["included_amount_cents"] == truth["included_amount_cents"] + expected_delta
    assert changed_truth["included_unique_order_count"] == truth["included_unique_order_count"] - 1
    assert changed_truth["exception_raw_row_count"] == truth["exception_raw_row_count"] + 1
    validation = {"passed": True, "change": "OD-010由128改129元，同时OD-024金额改空", "expected_delta_cents": expected_delta, "actual_changed_total_cents": changed_truth["included_amount_cents"], "baseline_total_cents": truth["included_amount_cents"], "new_missing_amount_order": "OD-024", "assertions": ["金额变化反映在日报", "缺金额不按零金额纳入", "异常数增加1且纳入订单数减1"]}
    def dump(name, obj):
        (args.out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dump("raw_inputs.json", raw)
    dump("truth.json", truth)
    dump("source_mappings.json", mappings)
    dump("workbook_payload.json", {"raw": raw, "rows": rows, "clean": clean, "exceptions": exceptions, "truth": truth})
    dump("validation.json", validation)
    (args.out / "raw_csv").mkdir(exist_ok=True)
    for i, source in enumerate(raw["files"], 1):
        with (args.out / "raw_csv" / f"input_{i}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(source["headers"])
            w.writerows(source["rows"])
    write_csv(args.out / "clean.csv", clean, ["order_id", "order_date", "amount_cents", "currency", "payment_status", "refund_status", "disposition", "canonical_source_id", "source_ids"])
    fields = ["source_id", "source_file", "source_sheet", "source_row", "order_id", "order_date", "amount_cents", "currency", "payment_status", "refund_status", "disposition", "reason", "canonical_source_id", "original"]
    write_csv(args.out / "row_disposition.csv", rows, fields)
    write_csv(args.out / "exceptions.csv", exceptions, fields)
    log = {"executed_at": datetime.now().astimezone().isoformat(), "python": sys.version.split()[0], "source_mode": source_mode, "raw_files": 3, "raw_rows": 30, "truth_sha256": hashlib.sha256((args.out / "truth.json").read_bytes()).hexdigest(), "validation_passed": True, "included_amount_cents": truth["included_amount_cents"]}
    with (args.out / "run_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")
    print(json.dumps(log, ensure_ascii=False))

if __name__ == "__main__":
    main()
