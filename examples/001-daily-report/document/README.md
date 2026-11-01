# 第001期日报生成与独立验收

本目录的 Word 构建器只负责把已验证的结构化结果排成日报。新原始数据需先按明确业务规则重新分析并生成 truth.json，不可仅修改 Word 或沿用旧结果。

## 依赖与运行

使用 Python 3；报告脚本需要 `python-docx`。从包含 `case/` 和 `document/` 的复用包根目录运行：

```bash
python document/generate_report.py --truth case/truth.json --out 第001期_可核对日报.docx --facts-out document/report_facts.json
python document/validate_independently.py --case case --out document/validation.json
```

`generate_report.py` 的日期、金额、订单数、原始行去向、异常数字与源行定位，均动态读取所给 truth。它不含本机绝对路径。`report_facts.json` 保存实际业务文案和 truth 校验和，便于追溯。Word 使用 Letter 纵向；正文与表格11pt。

`validate_independently.py` 直接读取 `case/raw_csv/input_*.csv` 的原始文本，另用 SQLite 分组、内容签名及窗口排序核算，不调用案例生产分析脚本。它核对本次三份固定字段结构的合成案例；新案例需重新明确字段映射与验收口径。

## 本次口径

全局订单ID去重后，只纳入报表日已支付且未退款、关键字段完整、同ID规范内容无冲突的唯一订单。完全相同内容只计一次并保留全部来源；冲突和缺字段待确认。来源文件只是快照来源，不能当经营渠道业绩。金额以整数分累计，展示时格式化为元。

全部输入为合成演示数据，快照非财务凭证，日报金额不是财务收入或税务结论。故意直接相加所有可解析原始金额，仅作为错误对照。
