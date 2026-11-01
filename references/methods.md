# 分析方法导航与原生语法路由

用途：根据研究问题定位方法、查找目标软件的命令与算法、列出影响结果的设置。这里是方法导航，不是“全部方法已经实现或通过原生验证”的清单。只有本次实际运行、导出结果并留下核验记录的方法才能标为已验证。

## 如何使用本表

先确定研究设计、变量尺度、目标 estimand（所估计的量）、独立单位及重复测量结构，再选方法。表中命令名只是检索入口，不是完整可执行语法；先核对安装版本、许可模块、命令帮助和 Methods and formulas，再写本次脚本。不要为了让结果显著而选择分析、删样本或更换标准误。

| 研究任务 | SPSS Statistics 检索入口 | Stata 检索入口 | 必须明确或核验 |
|---|---|---|---|
| 数据定义、重编码、合并、长宽转换 | GET DATA、GET FILE、COMPUTE、RECODE、MATCH FILES、ADD FILES、VARSTOCASES、CASESTOVARS | import、use、generate、recode、merge、append、reshape | 主键与匹配基数；日期单位；字符串编码；缺失代码；原始记录数及重复行 |
| 频数、百分比、描述统计、分位数 | FREQUENCIES、DESCRIPTIVES、EXAMINE、MEANS | summarize、tabulate、tabstat、centile | 分母含不含缺失；SD 分母；百分位插值；加权与非加权 N |
| 正态性、异常值与分布诊断 | EXAMINE | swilk、sktest、qnorm、histogram | 检验适用样本量；残差还是原始变量；异常值处理规则预先确定 |
| 单样本、独立或配对均值检验 | T-TEST | ttest | 配对 ID；差值方向；等方差与不等方差结果；df 公式；单侧或双侧 |
| 方差齐性及组间比例 | EXAMINE、ONEWAY、CROSSTABS 及相应比例检验命令 | robvar、sdtest、prtest、bitest | Levene 基于均值或中位数；正态性条件；二项区间与检验定义 |
| 列联表、卡方、精确检验、关联效应量 | CROSSTABS | tabulate、mcc、symmetry | 期望频数；Yates 校正；Fisher 双侧定义；配对结构；精确模块许可 |
| 单因素 ANOVA、Welch ANOVA、事后比较 | ONEWAY | oneway、pwmean 及对应版本支持的命令 | 经典还是异方差模型；多重比较法；各比较使用的误差项及 df |
| 析因 ANOVA、ANCOVA、一般线性模型 | UNIANOVA、GLM | anova、regress、contrast、margins | SS 类型、对比编码、交互项、空单元、边际均值的参考分布 |
| 重复测量、多元重复测量 | GLM | anova、manova，或另建 mixed 模型 | 被试单位、时间顺序、球形性、GG/HF 修正、多元检验；mixed 不自动等同重复测量 ANOVA |
| 非参数独立样本检验 | NPTESTS、NPAR TESTS | ranksum、kwallis、median | 秩和或 U 统计量方向、并列秩、精确或渐近 p、连续性校正、事后比较 |
| 非参数配对或多时点检验 | NPTESTS、NPAR TESTS | signrank、signtest；Friedman 等查目标版本官方目录或已审查扩展 | 零差值、并列秩、完整配对、精确分布；不能把独立样本算法用于配对数据 |
| Pearson、Spearman、Kendall 与偏相关 | CORRELATIONS、NONPAR CORR、PARTIAL CORR | correlate、pwcorr、spearman、ktau、pcorr | 成对或整行删除；tau-a/tau-b；偏相关控制集；推断算法与 CI |
| 线性、多元、分层、交互和多项式回归 | REGRESSION、UNIANOVA | regress、test、lincom、margins | 实际设计矩阵、截距、参照组、中心化、协方差估计、嵌套比较样本一致 |
| 二元、序数、多项 Logistic 与 Probit | LOGISTIC REGRESSION、PLUM、NOMREG、PROBIT、GENLIN | logit、logistic、ologit、mlogit、probit | 事件编码与阈值符号、基准结局、平行线假设、完全分离、OR 与概率边际效应区别 |
| 计数、发生率、零膨胀、其他 GLM | GENLIN；零膨胀等先查原生或已安装扩展 | poisson、nbreg、zip、zinb、glm | 分布、link、exposure/offset、NB1/NB2 参数化、尺度、零膨胀方程 |
| 非线性、稳健、分位数、删失与受限因变量 | NLR、CNLR、QUANTILE REGRESSION；其余按版本检索 | nl、rreg、qreg、tobit、intreg、truncreg | 损失或似然、起值、分位数定义、删失与截断区别、非光滑目标的 SE 算法 |
| 多层线性与广义线性混合模型 | MIXED、GENLINMIXED | mixed、melogit、mepoisson、menbreg、meglm | ML/REML、随机效应与残差结构、积分法及点数、df、收敛与奇异拟合 |
| 广义估计方程 | GENLIN 的重复测量设置 | xtgee | population-averaged estimand、工作相关、scale、稳健或模型式 VCE、聚类单位 |
| 量表信度、项目分析、ICC 与一致性 | RELIABILITY | alpha、icc、kappa | 反向题规则、raw/standardized alpha、缺失处理、自动反向、ICC 模型及单次或平均测量 |
| PCA、EFA、旋转与因子得分 | FACTOR | pca、factor、rotate、predict | PCA 不等于共同因子；提取方法、因子数、矩阵、旋转标准化、载荷符号与排列、计分算法 |
| CFA、SEM、路径及广义 SEM | SPSS Amos 为独立产品；不得把 Statistics 的 FACTOR 当 CFA；也可经明确指定的外部引擎 | sem、gsem | 识别约束、测量模型、估计量、缺失数据机制、稳健校正、标准化方案、拟合指标定义 |
| 项目反应理论、潜类别、有限混合 | 按 Statistics 扩展或相关独立产品检索 | irt、fmm、gsem | 题目类型、潜变量尺度、类别标签切换、多起点、局部最优、积分误差 |
| 中介、调节、调节中介 | 回归/宏方案；PROCESS 是第三方宏，须记录版本及授权来源 | sem、gsem、mediate、bootstrap、nlcom 及已审查扩展 | 线性或非线性 estimand、交互方程、间接效应定义、重抽样单位、CI 类型；宏型号不能代替公式 |
| 生存、风险、竞争风险与复发事件 | KM、COXREG；其他模型按模块/扩展检索 | stset、sts、stcox、streg、stcrreg | 时间零点、删失、延迟进入、时变协变量、ties 方法、比例风险、亚分布与原因别风险区别 |
| 面板固定/随机效应与动态面板 | MIXED 或明确的外部/扩展方案；不要假称同名原生命令齐全 | xtset、xtreg、xtlogit、xtpoisson、xtabond、xtdpdsys | 个体与时间 ID、FE/RE estimand、吸收参数计数、VCE、工具变量与滞后、不同 R² |
| 工具变量、联立方程、选择与内生性 | 按目标版本相关回归/扩展检索 | ivregress、ivprobit、reg3、heckman、eregress | 排除约束、第一阶段、识别与弱工具诊断、GMM 权矩阵、方差修正、选择方程 |
| 双重差分、匹配、加权、处理效应 | 通用建模可编码，但须明确 estimand 与实现来源 | didregress、xtdidregress、hdidregress、xthdidregress、teffects | 平行趋势、时间与队列、ATT/ATE、共同支持、权重、标准误单位、异质处理效应 |
| 断点、合成控制、事件研究等专门因果方法 | 目标版本官方/已安装扩展或外部引擎 | 官方目录或已审查社区命令 | 阈值规则、带宽、核、趋势、donor pool；不能用普通 OLS 冒充已验证的专门估计器 |
| 时间序列、预测、单位根、协整、VAR 与波动 | ARIMA、TSMODEL 等 Forecasting 命令 | tsset、arima、dfuller、pperron、var、vec、arch、sspace、ucm | 时间频率与缺口、差分、趋势、滞后选择、初始状态、似然方法、预测区间及样本外评价 |
| 复杂抽样、分层整群及重复权重 | CSPLAN、CSDESCRIPTIVES、CSTABULATE、CSGLM 等 | svyset、svy | pweight、PSU、strata、FPC、单 PSU、Taylor/BRR/jackknife、子总体估计 |
| 缺失机制、EM、多重插补及合并 | MVA、MULTIPLE IMPUTATION | mi set、mi impute、mi estimate | 插补模型与类型、被动变量、约束、m、burn-in、种子、Rubin 合并及有限样本 df |
| 功效、精度与样本量 | 官方 Power Analysis 对应命令，核对版本 | power、ciwidth | 检验假设、效应量定义、侧数、alpha、分配比、脱落率及聚类设计效应 |
| Meta 分析、Meta 回归、发表偏倚 | 目标版本 Meta Analysis 命令与许可 | meta set、meta esize、meta summarize、meta regress、meta funnel | 效应量尺度、抽样方差、连续性校正、固定或随机效应、tau²、Hartung–Knapp 等推断 |
| MANOVA、判别、聚类、对应分析、多维尺度 | GLM、DISCRIMINANT、CLUSTER、QUICK CLUSTER、TWOSTEP CLUSTER、CORRESPONDENCE、PROXSCAL、ALSCAL | manova、discrim、cluster、ca、mca、mds | 距离、标准化、链接规则、初始中心、先验概率、维数、特征值和解的旋转不确定性 |
| 空间回归与空间面板 | 按官方地理空间命令目录或明确的外部/扩展实现检索；时空预测不等于空间回归 | spset、spmatrix、spregress、spxtregress | 空间 ID、W 矩阵与标准化、孤岛、空间滞后/误差、直接及间接效应 |
| Bayesian 分析与 MCMC | 官方 Bayesian Statistics 对应命令，逐命令核验 | bayes、bayesmh、bayesstats | 先验、参数化、链数、burn-in、ESS、收敛、后验区间及 Monte Carlo 误差 |
| 树、神经网络、正则化、机器学习与分类预测 | TREE、MLP、RBF 及具体模块/扩展 | lasso、elasticnet、H2O 集成等按版本检索 | 数据分割、防泄漏、预处理拟合范围、超参数、折分、类别权重、预测校准；预测不自动给出因果解释 |
| 控制图、质量、联合分析与抽样设计 | SPCHART、ORTHOPLAN、CONJOINT 及模块 | 按官方目录、函数或已审查扩展检索 | 子组与限值定义、阶段、异常规则、设计编码与效用识别、适用模型 |

## 没有列到的命令及扩展

1. 用用户要求的软件、版本和问题检索官方命令目录；不要把“本表未列出”误判为软件不支持。原生语法能完成的方法均沿同一协议接入，不要求先扩充本表。
2. 阅读该命令的完整 Syntax、Options、缺失与权重说明、Stored results/OMS 输出、算法或 Methods and formulas，记录准确 URL、版本和日期。仅凭搜索摘要、菜单截图或相似命令名不能确定算法。
3. 编制一张本次方法卡：研究问题、estimand、假设、样本与编码、公式或似然、优化器、初值/容差、df/VCE/CI、软件和包版本、原生结果提取字段、对照数据、状态。方法卡随复现材料保存。
4. 原生可用时先运行小型确定性样本，检查命令确实支持指定选项，再运行正式数据；失败时保留日志并修正，不静默换方法。
5. 第三方 `.ado`、SPSS 扩展、宏、R/Python 包均不是软件核心保证的一部分。记录作者、版本、来源及依赖，查其原始文档；依赖处理遵守本次任务范围及环境执行权限，不自动购买许可或修改无关全局环境。
6. 原生许可或专门实现不可用时，可以产出未运行的 `.sps`/`.do` 与公式核验的替代结果，但明确标注未通过原生对照。不能用占位值补足结果。

## 易混淆的模型与报告口径

- 在 SPSS 与 Stata 之间对齐的是特定模型、算法和设置，不是两套软件各自任意默认值。两个都正确的默认分析可能输出不同数值。
- `GENLINMIXED`、GEE、固定效应、随机效应和重复测量 ANOVA 的模型假设与目标参数不同，不能按数据“都是重复测量”互相替换。
- FACTOR 中的 PCA、EFA 与 CFA 分开处理。SPSS 的未完整指定 FACTOR 语法可能因子命令顺序而改变有效设置，必须看实际运行日志。参见 [IBM FACTOR 说明](https://www.ibm.com/docs/en/spss-statistics/31.0.0?topic=factor-overview-command)。
- SPSS Amos、Modeler、PROCESS、Stata 社区命令与 Statistics/Stata 核心命令分别标明来源。不可把跨产品或第三方功能宣称为 SPSS Statistics 原生功能。
- 分类不平衡、缺失、聚类和复杂抽样先影响分析单位和方差，不能只把最终 N 对齐就认定模型相同。

## 官方入口及核对日期

本导航于 2026-11-01 核对公开入口，公开 Stata 文档页显示 Release 19；IBM 页面采用 Statistics 31 的版本入口。它们是检索基线，不代表用户机器安装此版本；实际运行始终锁定本机版本。完整 SPSS Algorithms PDF 本次未成功读取，不可声称已逐式核验全部 SPSS 算法；需要时从匹配版本的本机帮助或 IBM 文档页获取。

- [IBM Statistics 31 文档与模块手册](https://www.ibm.com/support/pages/ibm-spss-statistics-31-documentation)
- [IBM 命令语法分类导航](https://www.ibm.com/docs/en/spss-statistics/31.0.0?topic=reference-introduction-guide-command-syntax)
- [IBM Statistics 31 Command Syntax Reference](https://www.ibm.com/docs/en/SSLVMB_31.0.0/pdf/IBM_SPSS_Statistics_Command_Syntax_Reference.pdf)
- [Stata 官方文档和专业手册目录](https://www.stata.com/features/documentation/index.html)
- 按任务读取：[多元统计 MV](https://www.stata.com/manuals/mv.pdf)、[结构方程 SEM](https://www.stata.com/manuals/sem.pdf)、[混合模型 ME](https://www.stata.com/manuals/me.pdf)、[多重插补 MI](https://www.stata.com/manuals/mi.pdf)、[调查抽样 SVY](https://www.stata.com/manuals/svy.pdf)。
- 按任务读取：[生存 ST](https://www.stata.com/manuals/st.pdf)、[面板 xtreg](https://www.stata.com/manuals/xtxtreg.pdf)、[时间序列 TS](https://www.stata.com/manuals/ts.pdf)、[因果推断 CAUSAL](https://www.stata.com/manuals/causal.pdf)、[Meta](https://www.stata.com/manuals/meta.pdf)、[空间 SP](https://www.stata.com/manuals/sp.pdf)。
