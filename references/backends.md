# 原生引擎与代码路径

## 选择原则

原生执行是获得目标软件结果的优先路径。相同原始数据不够：还要匹配版本、模块、命令选项及有效样本。SPSS 和 Stata 不是彼此的金标准；按用户指定目标核验。软件文件读取器（如 pyreadstat、pandas read_stata）只负责 IO，不是原生统计引擎。

`python scripts/probe_engines.py` 只检查常见路径和模块位置，不启动程序，不验证许可证。不在 PATH 不代表没安装；探测到文件也不代表可执行、模块齐全或许可证有效。随后对选定引擎做最小、隔离的实际运行，记录版本和模块。不要启动软件更新、购买许可或修改全局 Python 配置来“修复”运行环境。

## Stata

先查看实际安装和 `about`，记录版本、更新、版本控制及 ado 来源。Mac 的应用内可执行文件名及位置依产品版和安装目录确定，不能照搬 Linux 的 `stata-mp` 名称。Mac 官方后台模式：

```text
"/实际路径/StataSE.app/Contents/MacOS/StataSE" -e do "/任务目录/analysis.do"
```

`-e` 在完成后退出且不提示；Unix 的通常形式为 `stata -b do analysis.do`。Windows 按目标版本手册使用真实 exe 与 `/e` 等对应开关，不把 Mac 参数机械套用。用 subprocess 的参数数组调用，不拼接来自文件名或用户内容的 shell 命令。

在隔离工作目录运行，避免覆盖已有日志。记录启动时执行的 `profile.do` 的相关影响；`version` 设为已确认目标版本，不能靠写一个旧 version 数字假设重现全部旧软件环境。数据清洗、`set`、随机数生成器和 seed、`svyset`／`xtset`／`tsset`、对照基准、模型选项写入 do-file。按模型保存 `e(sample)` 对应样本。

结果优先提取真实 `e()`／`r()`、协方差矩阵及参数 stripe，计算 p／CI 时用命令文档规定的分布和 df；不一律用正态分布。标准化系数、边际效应、OR／HR 与原系数分开命名，区间按对应尺度变换。`collect`、`putdocx`、`etable` 等随版本变化，仅在存在时使用。第三方命令用 `which` 核验 ado 文件和依赖版本，不能把 `reghdfe`／`esttab` 等当内置或默默安装最新版本。

检查 batch 日志中的 `r(#)`、执行到哪一行、估计返回状态和预期结果文件，不能仅检查操作系统退出码。`assets/native-smoke.do` 是待在目标引擎验证的合成小例，不是已生成的基准。

## IBM SPSS Statistics

记录 Statistics 版本、补丁、许可模块、Python 集成版本与 Unicode／区域设定。Statistics、Amos、Modeler 以及第三方 PROCESS 宏须分别识别；安装 Statistics 不代表拥有后两者或宏。

可在已配置的 IBM Python 集成环境通过 `import spss` 与 `spss.Submit(...)` 执行完整语法。外部 Python 模式会启动 Statistics 后端，但需要产品支持的环境和许可；普通 pip 同名包不能替代。Mac 的 IBM Python3 for SPSS Statistics 应用是官方支持的入口之一。若外部环境不可用，交付 `.sps` 在原生 Syntax Editor／受支持生产模式执行，不能声称已经执行。

```python
# 在与目标 IBM 产品匹配、已配置的 Python 环境中执行；不是普通 Python 独立实现。
from pathlib import Path
import spss
syntax = Path("analysis.sps").read_text(encoding="utf-8")
spss.Submit(syntax)
```

语法必须包含完整命令和句点；Python 代码块、MATRIX 或 BEGIN DATA 块不能随意拆分。外部 Submit 模式有特定命令限制，例如 OUTPUT EXPORT／OPEN／SAVE 不受支持，不能通用调用。使用 OMS 导出可解析 OXML、SAV 等受支持结果，再生成论文 Word。

每次显式确认 `FILTER`、`SPLIT FILE`、`WEIGHT`、用户缺失值定义、SELECT IF、临时变换、活动 dataset 和命令执行顺序。SPSS WEIGHT 的语义因过程变化，不将其统一等同 Stata pweight 或 WLS。根据实际模型和文档生成状态设置，不为“统一默认”抹去用户设计。

OMS 先打开捕获，再运行过程，最后 `OMSEND`。提取器须识别 namespace、pivot 多维表、subtype、参数／分类标签与原始数值字段；跨语言不能只匹配显示标题。OXML 仍可能含格式化显示文字，须确认取得全精度字段。保存错误与警告，确认每个预期过程的表确实产生。`assets/native-smoke.sps` 是待执行的合成小例。

## Python 与 R 复现

按过程选择库，不规定一个包承包全部：例如 SciPy 的基本检验、statsmodels 的回归与时序、R 的 survival／survey／mice／lavaan 等，都须核实实际版本文档、参数、限制、默认值。此处包名是查找路径，不表示它们已经安装或与目标匹配。

从目标文档建立参数映射后才能复现。显式核对 Welch／pooled、Type I／II／III SS、ddof、ties、连续性修正、精确／渐近、HC 类型、cluster 小样本修正、ML／REML、link、类别参考、优化和 CI。不能仅因函数同名而替换。非线性模型随机初值、局部最优和随机抽样必须另行核验；同 seed 不保证序列相同。

原生软件不可用时，可以完成已明确定义的复现并交 Word；标记 `REIMPLEMENTED_UNVERIFIED`。确切原生输出确实为任务必要条件时，只阻塞依赖它的分析，交付可运行语法和所缺条件。

## 官方依据

核实日期 2026-11-01。以下是接入方式依据，实际过程须查目标版本：

- [Stata Mac 后台调用与真实可执行路径](https://www.stata.com/support/faqs/mac/advanced-topics/)
- [Stata Unix batch mode](https://www.stata.com/support/faqs/unix/batch-mode/)
- [Stata postfile 与精度类型声明](https://www.stata.com/manuals/ppostfile.pdf)
- [Stata export delimited 与 datafmt](https://www.stata.com/manuals/dimportdelimited.pdf)
- [SPSS 32 外部 Python 接入](https://www.ibm.com/docs/en/spss-statistics/32.0.0?topic=programs-running-spss-statistics-from-external-python-process)
- [SPSS 30 Submit 行为及外部模式命令限制](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=classes-spsssubmit-function-python)
- [SPSS 30 OMS 输出格式](https://www.ibm.com/docs/en/spss-statistics/30.0.0?topic=command-format-keyword-oms)
- [SPSS 31 完整语法参考入口](https://www.ibm.com/docs/en/spss-statistics/31.0.0?topic=reference-introduction-guide-command-syntax)

这些不同版本的链接仅说明相应版本的行为，不能据此声称任意目标版本都相同。
