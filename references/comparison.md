# 原生结果对照与可追溯验证

## 何时读取

采用 Python、R 或其他库复现 SPSS／Stata 程序，或声称某次分析与原生结果一致之前，读取本文件。检查器只验证输入所列的分析和结果单元格；它不实现统计方法，不认证原生来源，也不证明未测试的方法、版本或数据具有相同结果。

## 三个不同结论

- **原生执行**：实际运行已授权的目标软件和指定程序，保留语法、日志、版本、模块与原始输出；没有跨引擎复现结论。
- **本次对照通过**：原生输出与候选实现使用相同数据、实际估计样本、权重及设置，所有预先指定结果均通过对照。注明目标版本与容差。
- **尚未验证**：没有真实原生基准，或样本、程序设置、单元格、不可估计结果不能完整核对。公式推导、库间一致和本检查器的单元测试都不能升级为原生一致。

不得把自己生成的候选结果同时作为原生基准。基准来自真实 `.spv`、OMS 导出、Stata 日志及机器可读存储结果等；保存原件并记录 SHA-256。参考引擎必须与 `analysis.target_engine` 和 `target_version` 相同，不能用“Stata 和 SPSS 差不多”替代指定目标。

## 执行顺序

1. 先定义请求需要的全部结果，例如每一项系数、标准误、检验统计量、自由度、p 值、置信区间、样本数、拟合指标、边际效应和诊断。依据原生完整结果建立单元格清单，不能看到差异后删掉不一致项。
2. 对齐观测的筛选、缺失剔除、分组、排序、变量编码、对比编码、因子参照组、常数项、权重与模型参数化。多模型报告逐模型建立基准。
3. 明确原生程序实际使用的缺省设置，写入 `analysis.settings`，再配置候选实现。不能只记录“default”。
4. 从未四舍五入的机器可读输出提取数值，确保 p 值不是打印的 `0.000`，置信区间不是用报告中的系数和标准误重算。`p < .001` 不能恢复精确 p 值，需重新导出或标记无法数值对照。
5. 在看结果之前确定逐单元格容差，并保存理由。高精度解析算法可以使用 `abs_tol=1e-10, rel_tol=1e-8` 作为调查起点，但这不是普遍合格线。特别小的 p 值宜选择足够小或零绝对容差；病态模型、迭代估计、数值积分与随机模拟需要按方法定义精度，不能为通过而放宽阈值。
6. 执行检查，处理失败原因并重新运行。保留最初差异及修正依据；若无法排除差异，报告尚未对齐。随机程序即使种子相同也可能使用不同随机数生成器或并行顺序，不能承诺逐位相同。
7. 保存结构化结果、容差、检查报告与原生证据。论文按需要舍入；对照始终使用未舍入值。

## 引擎探测

```bash
python scripts/probe_engines.py > engine_inventory.json
```

仅查询 PATH 和少量 macOS 常见安装位置，不执行引擎、不读取许可证、不递归扫描资料目录。`executable_found` 表示存在可执行路径，仍须确认产品身份、版本、许可、模块及批处理入口；PATH 中的 `stats` 可能属于其他产品。`not_found` 仅表示已检查的位置没有找到，用户可提供实际路径。Python 的 `spss` 同名模块或可读取 `.sav` 的库不等于 SPSS 统计引擎。

## 对照文件格式

`compare_results.py` 使用 UTF-8 JSON，根层只允许以下四个键。两份文件的 `analysis` 必须逐层、逐类型完全相同；`provenance` 允许不同，因为执行引擎和代码本来可以不同。数字与布尔值严格区分，元数据中的整数与浮点数也严格区分，例如 `1` 与 `1.0`。先规范序列化约定，不能临时掩盖实质差异。

以下仅为字段示意，哈希和数值均不是原生运行证据，不能拿来声称原生验证通过：

```json
{
  "schema_version": 1,
  "provenance": {
    "engine": "Stata",
    "version": "19",
    "kind": "native",
    "command": "regress y x",
    "artifact_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "analysis": {
    "target_engine": "Stata",
    "target_version": "19",
    "method": "OLS",
    "specification": "y = intercept + x",
    "data_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "sample": {
      "n": 40,
      "ordered_id_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    },
    "weights": {"type": "none", "variable": "", "handling": {}},
    "settings": {
      "confidence_level": 0.95,
      "missing_policy": "listwise",
      "test_sidedness": "two-sided",
      "has_intercept": true,
      "estimator": "OLS",
      "covariance": "classical",
      "df_method": "n-rank(X)",
      "ci_method": "Student-t Wald",
      "reference_levels": {},
      "other_method_specific_options": {}
    }
  },
  "metrics": {
    "coef.x.estimate": {"kind": "number", "value": 2.0},
    "coef.x.se": {"kind": "number", "value": 0.25},
    "model.n": {"kind": "count", "value": 40},
    "model.convergence": {"kind": "category", "value": "converged"}
  }
}
```

候选文件保留相同的 `analysis` 与 `metrics` 单元格集合；`provenance.engine` 可为 `Python`、`R` 或实际原生引擎，`kind` 为 `reimplementation` 或 `native`，并写实际版本、执行脚本／命令、候选原始结果文件哈希。`command` 可记录入口并在同一工作目录保存完整语法，不得只记录无法复现的口头方法名。

- `data_sha256`：对同一份冻结输入原件按字节计算 SHA-256；另保留清洗脚本和字典。不以候选转换文件的不同哈希替换共同输入身份。若原始数据不能直接共享，先约定双方相同的规范化数据快照。
- `sample.n`：该程序真正使用的观测行数，不等于加权人口数。权重和原生程序的特殊定义另列指标。
- `sample.ordered_id_sha256`：对实际估计样本、按实际顺序排列的唯一稳定行标识生成哈希。推荐将 ID 规范为字符串数组，使用 `json.dumps(ids, ensure_ascii=False, separators=(",", ":"))` 编码为 UTF-8 后哈希；双方使用同样规范。分组分析逐组核对样本，重复测量和面板分析保留每条原始记录的唯一标识。行号 ID 只对同一冻结快照有效，不能在各自排序或清洗之后重新编号。
- `weights.type`：`none`、`frequency`、`analytic`、`probability`、`importance` 或 `other`；`none` 时变量为空字符串。加权时 `handling` 不得为空，写入零值、负值、缺失、标准化、自由度及有效样本处理；复杂抽样另在 settings 记录 PSU、分层、FPC、子总体与方差方法。
- `settings`：必须包含 `confidence_level`、`missing_policy`、`test_sidedness`、`estimator`、`covariance`、`df_method`、`ci_method`、`has_intercept`。除置信水平和截距字段外均写明确字符串；不适用项写 `not_applicable`，不能写 default／unknown／unspecified。`has_intercept` 为布尔值或 `not_applicable`，OLS 必须为布尔值。补足该程序的一切有效设置，包括小样本修正、检验类型、平方和、链接函数、分布、迭代准则、积分、并列值处理、分位数算法、随机化、排序等；这些基础必填项仍不等同所有方法合同已完整。
- 指标名 `n` 与 `model.n` 保留为原始有效样本行数：如果使用，必须为 count 并与 `analysis.sample.n` 一致。加权 N、聚类数、个体数等使用 `weighted.n`、`cluster.n`、`subject.n` 等另名，不能冒用这两个保留字段。
- `metrics`：每个键对应单个结果单元格，矩阵按有名称的行列展开，例如 `vcov.x.z`；`number` 接受有限整数或浮点数，`count` 只接受非负整数并精确比较，`category` 只接受字符串并精确比较。整数值的自由度若可能为近似小数，应使用 `number` 并给出合理容差。
- 数值指标不接受 `null`、布尔值、字符串、NaN 或正负无穷。不可估计参数、边界失败或打印阈值不能用零填补，也不能删除后宣称所有参数一致；应把这次完整对照标记为尚未验证，并在差异说明中列出原因。

## 明确的逐单元格容差

单独保存 `tolerances.json`。其指标键必须与原生基准的指标集合完全相同，不存在隐式容差或忽略项：

```json
{
  "schema_version": 1,
  "metrics": {
    "coef.x.estimate": {"abs_tol": 1e-10, "rel_tol": 1e-8},
    "coef.x.se": {"abs_tol": 1e-10, "rel_tol": 1e-8},
    "model.n": {"exact": true},
    "model.convergence": {"exact": true}
  }
}
```

数值条件为：`|reference − candidate| ≤ max(abs_tol, rel_tol × max(|reference|, |candidate|))`。计数与类别只能设置 `exact: true`；容差不能是负数、布尔值、空值或非有限值。小数计算使用 Python 标准库 Decimal 对已解析 JSON 数值的十进制表示进行比较，不把打印舍入当作算法差异。

```bash
python scripts/compare_results.py native.json candidate.json \
  --tolerances tolerances.json \
  --reference-artifact native_output.log \
  --output comparison.json
```

`--reference-artifact` 可验证指定文件的字节哈希是否等于原生基准声明的 `artifact_sha256`。哈希相符只能证明文件身份，不能证明文件确由原生软件产生。实际工作必须保留运行日志、程序、环境信息和导出过程。

退出码 `0` 表示输入所列内容通过，`1` 表示元数据／结果／文件哈希不匹配，`2` 表示输入无效或无法读写。标准输出及 `--output` 为机器可读 JSON，包含逐单元格数值、允许误差和差异路径。丢失或多出的候选指标都失败；重复 JSON 键、非标准 JSON 数值和不完整元数据都不能产生通过结论。单元格全部在容差内而样本不同，仍然失败。

`--output` 不得指向输入 JSON、容差文件或 `--reference-artifact` 原件；检查器会拒绝覆盖证据。

## 开发检查与扩充

```bash
python scripts/test_compare_results.py
```

这些测试只验证检查器行为，包括样本差异、精确计数、容差、嵌套布尔值／空值、非有限数、缺失项、重复 JSON 键、CLI 退出码和文件哈希。它们不验证任何统计方法与 SPSS／Stata 的一致性。增加一个方法时，还需真实原生固定案例、边界案例、参数化与缺省值说明，并按相同流程新增方法级对照证据。
