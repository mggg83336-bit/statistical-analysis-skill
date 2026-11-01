#!/usr/bin/env python3
"""Render an explicit statistical report JSON to DOCX; never compute statistics.

Requires python-docx in the chosen runtime. --validate-only writes nothing.
The status is supplied by the analysis workflow, not certified by this renderer.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile


STATUSES = {
    "NATIVE_EXECUTED": "原生软件执行",
    "VERIFIED_MATCH": "原生基准数值对照已通过",
    "REIMPLEMENTED_UNVERIFIED": "复现结果 尚未通过原生基准验证",
    "BLOCKED": "分析待补条件",
    "SYNTHETIC_DEMO": "模拟数据示例 不用于研究结论",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_keys(value, required, optional, where):
    require(isinstance(value, dict), f"{where}: expected object")
    require(set(required) <= set(value), f"{where}: missing keys {sorted(set(required)-set(value))}")
    require(set(value) <= set(required) | set(optional),
            f"{where}: unknown keys {sorted(set(value)-set(required)-set(optional))}")


def text(value, where, empty=False):
    require(isinstance(value, str) and (empty or value.strip()), f"{where}: expected nonempty string")
    require(not any(ord(ch) < 32 and ch not in "\n\t\r" for ch in value),
            f"{where}: invalid XML control character")


def number(value, where):
    require(type(value) in (int, float), f"{where}: expected finite number, not boolean")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    require(finite, f"{where}: expected finite number")


def finite_tree(value, where="report"):
    if isinstance(value, dict):
        for key, child in value.items():
            finite_tree(child, f"{where}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            finite_tree(child, f"{where}[{index}]")
    elif isinstance(value, float):
        require(math.isfinite(value), f"{where}: NaN/Infinity is prohibited")


def decimal_display(value, digits):
    quant = Decimal("1").scaleb(-digits)
    dec = Decimal(str(value))
    with localcontext() as context:
        context.prec = max(28, dec.adjusted() + digits + 4)
        result = dec.quantize(quant, rounding=ROUND_HALF_UP)
    if result == 0:
        result = abs(result)
    return format(result, f".{digits}f")


def cell_text(value):
    """Typed numbers keep unrounded JSON values; plain strings remain author's text."""
    if isinstance(value, dict):
        object_keys(value, ("value", "format"), ("digits",), "cell")
        fmt = value["format"]
        require(isinstance(fmt, str) and fmt in ("number", "p", "percent", "integer"), "cell.format: unsupported format")
        v = value["value"]
        number(v, "cell.value")
        digits = value.get("digits", 3 if fmt == "p" else (0 if fmt == "integer" else 2))
        require(type(digits) is int and 0 <= digits <= 10, "cell.digits: integer 0..10 required")
        if fmt == "p":
            require(0 <= v <= 1 and 1 <= digits <= 10, "p cell: value 0..1 and digits 1..10 required")
            threshold = 10 ** (-digits)
            return f"< {decimal_display(threshold, digits)}" if v < threshold else decimal_display(v, digits)
        if fmt == "integer":
            require(float(v).is_integer(), "integer cell: fractional value prohibited")
            require(digits == 0, "integer cell: digits must be 0")
            return str(int(v))
        return decimal_display(v * (100 if fmt == "percent" else 1), digits) + ("%" if fmt == "percent" else "")
    if value is None:
        return "—"
    if isinstance(value, str):
        text(value, "cell", empty=True)
        return value
    number(value, "cell")
    return str(value)


def local_asset(value, base, where):
    text(value, where)
    candidate = Path(value)
    require(not candidate.is_absolute(), f"{where}: use a path relative to the JSON")
    path = (base / candidate).resolve()
    require(path.is_relative_to(base.resolve()), f"{where}: path must stay within the JSON directory")
    require(path.is_file(), f"{where}: file not found: {value}")
    return path


def validate_report(report, base):
    finite_tree(report)
    object_keys(report, ("schema_version", "title", "status", "provenance", "sections"),
                ("subtitle", "keywords", "references", "style"), "report")
    require(report["schema_version"] == "1.0", "schema_version: expected 1.0")
    text(report["title"], "title")
    require(isinstance(report["status"], str) and report["status"] in STATUSES, "status: unsupported value")
    if "subtitle" in report:
        text(report["subtitle"], "subtitle")
    for field in ("keywords", "references"):
        if field in report:
            require(isinstance(report[field], list), f"{field}: expected array")
            for item in report[field]:
                text(item, field)
    provenance = report["provenance"]
    object_keys(provenance, ("data_description", "engine", "engine_version", "analysis_code", "verification"),
                ("data_sha256", "comparison_report", "analysis_plan", "random_seed", "notes"), "provenance")
    for key, value in provenance.items():
        if key == "random_seed":
            require(type(value) is int and value >= 0, "random_seed: nonnegative integer required")
        else:
            text(value, f"provenance.{key}")
    if "data_sha256" in provenance:
        v = provenance["data_sha256"]
        require(len(v) == 64 and all(ch in "0123456789abcdef" for ch in v), "data_sha256: lowercase SHA256 required")
    if report["status"] in ("NATIVE_EXECUTED", "VERIFIED_MATCH"):
        require("data_sha256" in provenance, "verified statuses require data_sha256")
    if report["status"] == "VERIFIED_MATCH":
        require("comparison_report" in provenance, "VERIFIED_MATCH requires comparison_report")
    style = report.get("style", {})
    object_keys(style, (), ("body_font_zh", "body_font_en", "body_size_pt", "line_spacing", "margin_cm"), "style")
    for key in ("body_font_zh", "body_font_en"):
        if key in style:
            text(style[key], f"style.{key}")
    for key, lo, hi in (("body_size_pt", 9, 16), ("line_spacing", 1, 2), ("margin_cm", 1.5, 3.5)):
        if key in style:
            number(style[key], f"style.{key}")
            require(lo <= style[key] <= hi, f"style.{key}: range {lo}..{hi}")
    content_width_cm = 21 - 2 * style.get("margin_cm", 2.5)
    sections = report["sections"]
    require(isinstance(sections, list) and sections, "sections: nonempty array required")
    for si, section in enumerate(sections):
        where = f"sections[{si}]"
        object_keys(section, ("heading", "blocks"), ("level",), where)
        text(section["heading"], f"{where}.heading")
        require(type(section.get("level", 1)) is int and section.get("level", 1) in (1, 2, 3), f"{where}.level: 1..3 required")
        require(isinstance(section["blocks"], list) and section["blocks"], f"{where}.blocks: nonempty array required")
        for bi, block in enumerate(section["blocks"]):
            loc = f"{where}.blocks[{bi}]"
            require(isinstance(block, dict), f"{loc}: object required")
            kind = block.get("type")
            if kind == "paragraph":
                object_keys(block, ("type", "text"), (), loc)
                text(block["text"], f"{loc}.text")
            elif kind == "table":
                object_keys(block, ("type", "caption", "columns", "rows"), ("notes",), loc)
                text(block["caption"], f"{loc}.caption")
                columns = block["columns"]
                require(isinstance(columns, list) and 1 <= len(columns) <= 12, f"{loc}.columns: 1..12 columns required")
                supplied_widths = []
                for col in columns:
                    object_keys(col, ("label",), ("align", "width_cm"), f"{loc}.column")
                    text(col["label"], f"{loc}.column.label")
                    require(col.get("align", "center") in ("left", "center", "right"), f"{loc}: invalid column align")
                    if "width_cm" in col:
                        number(col["width_cm"], f"{loc}.width_cm")
                        require(col["width_cm"] > 0, f"{loc}: width must be positive")
                        supplied_widths.append(col["width_cm"])
                require(not supplied_widths or len(supplied_widths) == len(columns), f"{loc}: supply all column widths or none")
                require(sum(supplied_widths) <= content_width_cm + 0.001, f"{loc}: column widths exceed printable area")
                require(isinstance(block["rows"], list) and block["rows"], f"{loc}.rows: nonempty array required")
                for row in block["rows"]:
                    require(isinstance(row, list) and len(row) == len(columns), f"{loc}: wrong row width")
                    for cell in row:
                        cell_text(cell)
                if "notes" in block:
                    require(isinstance(block["notes"], list), f"{loc}.notes: array required")
                    for note in block["notes"]:
                        text(note, f"{loc}.note")
            elif kind == "figure":
                object_keys(block, ("type", "caption", "path", "alt"), ("width_cm", "notes"), loc)
                text(block["caption"], f"{loc}.caption")
                text(block["alt"], f"{loc}.alt")
                image_path = local_asset(block["path"], base, f"{loc}.path")
                require(image_path.suffix.lower() in (".png", ".jpg", ".jpeg"), f"{loc}: PNG/JPEG figures only")
                width = block.get("width_cm", min(14, content_width_cm))
                number(width, f"{loc}.width_cm")
                require(1 <= width <= content_width_cm, f"{loc}: figure too wide")
                if "notes" in block:
                    text(block["notes"], f"{loc}.notes")
            else:
                raise ValueError(f"{loc}: unsupported block type {kind!r}")


def set_font(font_object, east_asia, latin, size_pt):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor
    font_object.name = latin
    font_object.size = Pt(size_pt)
    font_object.color.rgb = RGBColor(0, 0, 0)
    rpr = font_object._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr, value in (("eastAsia", east_asia), ("ascii", latin), ("hAnsi", latin)):
        fonts.set(qn(f"w:{attr}"), value)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fonts.attrib.pop(qn(f"w:{attr}"), None)


def add_table(doc, block, style):
    from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
    caption = doc.add_paragraph(block["caption"], style="Caption")
    caption.paragraph_format.keep_with_next = True
    table = doc.add_table(rows=1, cols=len(block["columns"]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [c.get("width_cm") for c in block["columns"]]
    if not all(widths):
        total = 21 - 2 * style.get("margin_cm", 2.5)
        weights = [max(2, min(12, len(c["label"]))) for c in block["columns"]]
        # Give the descriptive first column more room without squeezing statistics.
        weights[0] = max(weights[0], 6)
        widths = [total * w / sum(weights) for w in weights]
    for col, width in zip(table.columns, widths):
        col.width = Cm(width)
    table_properties = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:val"), "single" if side in ("top", "bottom") else "nil")
        if side in ("top", "bottom"):
            edge.set(qn("w:sz"), "10")
            edge.set(qn("w:color"), "000000")
        borders.append(edge)
    table_properties.append(borders)
    margins = OxmlElement("w:tblCellMar")
    for side, value in (("top", 80), ("bottom", 80), ("left", 90), ("right", 90)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(value))
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    table_properties.append(margins)
    for cell, column in zip(table.rows[0].cells, block["columns"]):
        cell.text = column["label"]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        bottom = OxmlElement("w:tcBorders")
        line = OxmlElement("w:bottom")
        line.set(qn("w:val"), "single")
        line.set(qn("w:sz"), "6")
        line.set(qn("w:color"), "000000")
        bottom.append(line)
        cell._tc.get_or_add_tcPr().append(bottom)
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    table.rows[0]._tr.get_or_add_trPr().append(repeat)
    for values in block["rows"]:
        row = table.add_row()
        for cell, value in zip(row.cells, values):
            cell.text = cell_text(value)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    aligns = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT}
    for row_index, row in enumerate(table.rows):
        cant_split = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant_split)
        for cell, column, width in zip(row.cells, block["columns"], widths):
            cell.width = Cm(width)
            for para in cell.paragraphs:
                para.alignment = aligns[column.get("align", "center")]
                para.paragraph_format.space_before = Pt(0)
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1.15
                for run in para.runs:
                    set_font(run.font, style.get("body_font_zh", "Songti SC"), style.get("body_font_en", "Times New Roman"), 10.5)
                    run.bold = row_index == 0
    for note in block.get("notes", []):
        doc.add_paragraph(note, style="Table Note")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def build_document(report, base):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
    doc = Document()
    opts = report.get("style", {})
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    margin = Cm(opts.get("margin_cm", 2.5))
    sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = margin
    zh, en = opts.get("body_font_zh", "Songti SC"), opts.get("body_font_en", "Times New Roman")
    body_size = opts.get("body_size_pt", 12)
    styles = doc.styles
    if "Table Note" not in styles:
        styles.add_style("Table Note", 1)
    for name, size, bold in (("Normal", body_size, False), ("Title", 18, True), ("Subtitle", 11, False),
                             ("Heading 1", 14, True), ("Heading 2", 12, True), ("Heading 3", 12, True),
                             ("Caption", 10.5, False), ("Table Note", 10, False)):
        style = styles[name]
        set_font(style.font, zh, en, size)
        style.font.bold = bold
        style.paragraph_format.line_spacing = opts.get("line_spacing", 1.5) if name == "Normal" else 1.2
        style.paragraph_format.space_after = Pt(6 if name == "Normal" else 8)
        if name.startswith("Heading"):
            style.paragraph_format.space_before = Pt(12)
            style.paragraph_format.keep_with_next = True
        # Avoid any inherited decoration on titles and headings.
        ppr = style.element.find(qn("w:pPr"))
        if ppr is not None:
            for child in list(ppr):
                if child.tag in (qn("w:pBdr"), qn("w:shd")):
                    ppr.remove(child)
    title = doc.add_paragraph(report["title"], style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if report.get("subtitle"):
        sub = doc.add_paragraph(report["subtitle"], style="Subtitle")
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if report["status"] in ("SYNTHETIC_DEMO", "REIMPLEMENTED_UNVERIFIED", "BLOCKED"):
        doc.add_paragraph(STATUSES[report["status"]], style="Subtitle")
    if report.get("keywords"):
        doc.add_paragraph("关键词：" + "；".join(report["keywords"]))
    for section in report["sections"]:
        doc.add_heading(section["heading"], level=section.get("level", 1))
        for block in section["blocks"]:
            if block["type"] == "paragraph":
                doc.add_paragraph(block["text"])
            elif block["type"] == "table":
                add_table(doc, block, opts)
            elif block["type"] == "figure":
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.keep_with_next = True
                run = p.add_run()
                picture = run.add_picture(str(local_asset(block["path"], base, "figure.path")),
                                          width=Cm(block.get("width_cm", min(14, 21 - 2 * opts.get("margin_cm", 2.5)))))
                picture._inline.docPr.set("descr", block["alt"])
                doc.add_paragraph(block["caption"], style="Caption")
                if block.get("notes"):
                    doc.add_paragraph(block["notes"], style="Table Note")
    if report.get("references"):
        doc.add_heading("参考文献", level=1)
        for entry in report["references"]:
            doc.add_paragraph(entry)
    doc.add_heading("计算与复现信息", level=1)
    doc.add_paragraph("结果状态：" + STATUSES[report["status"]])
    labels = {"data_description": "数据", "engine": "计算引擎", "engine_version": "版本", "analysis_code": "分析代码",
              "verification": "核验记录", "data_sha256": "数据 SHA256", "comparison_report": "数值对照报告",
              "analysis_plan": "分析方案", "random_seed": "随机种子", "notes": "说明"}
    for key, value in report["provenance"].items():
        doc.add_paragraph(labels[key] + "：" + str(value), style="Table Note")
    # ZIP metadata may vary with save time; body layout and numeric formatting are deterministic.
    doc.core_properties.title = report["title"]
    doc.core_properties.subject = "统计分析报告"
    doc.core_properties.author = ""
    return doc


def load_spec(path):
    def reject_constant(value):
        raise ValueError(f"Nonstandard JSON number: {value}")
    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            require(key not in obj, f"duplicate JSON key: {key}")
            obj[key] = value
        return obj
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant, object_pairs_hook=unique_pairs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--output", "--out", dest="out", type=Path)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="replace existing output and its traceability sidecar")
    args = ap.parse_args()
    try:
        spec = args.spec.resolve()
        report = load_spec(spec)
        validate_report(report, spec.parent)
        if args.validate_only:
            print(json.dumps({"valid": True, "status": report["status"], "certifies_statistics": False}, ensure_ascii=False))
            return 0
        require(args.out is not None, "--out is required unless --validate-only")
        out = args.out.resolve()
        require(out.suffix.lower() == ".docx", "output extension must be .docx")
        require(out != spec, "output must differ from input")
        sidecar = out.with_suffix(".traceability.json")
        require(sidecar != spec, "traceability sidecar must differ from input")
        require(args.force or not (out.exists() or sidecar.exists()), "output exists; use another name or --force")
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = build_document(report, spec.parent)
        with tempfile.NamedTemporaryFile(suffix=".docx", dir=out.parent, delete=False) as temporary:
            tmp = Path(temporary.name)
        try:
            doc.save(tmp)
            tmp.replace(out)
        finally:
            tmp.unlink(missing_ok=True)
        trace = {"schema_version": "1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                 "report_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                 "input_spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
                 "status_is_author_supplied": True, "certifies_statistics": False, "report_spec": report}
        sidecar.write_text(json.dumps(trace, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"docx": str(out), "traceability": str(sidecar), "status": report["status"],
                          "render_and_visual_review_required": True}, ensure_ascii=False))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
