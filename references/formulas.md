# 统计公式与数值对齐要点

本文件提供常用公式和错误检查点；不是 SPSS／Stata 所有算法的替代手册。复杂模型按目标版本的官方 Algorithms 或 Methods and formulas 落实公式、算法及参数化。下列公式通常假设独立、未加权、完整样本；权重、复杂抽样、重复测量或插补结果不能直接套用。

## 记号及输入约束

`n` 为当前分析实际纳入的观测数，`X` 为含预定截距与对比编码的设计矩阵，`k=rank(X)`，`e=y−Xβ̂`，`G` 为聚类数。总体参数与样本估计量区分。所有统计量先在全精度计算，显示时才四舍五入；不能用 Word 中四舍五入后的系数反算检验。

在计算前固定有效样本的行 ID、顺序和排除理由；核对系统缺失、用户缺失、SPSS 过滤/分组/权重、Stata 扩展缺失及条件表达式。Stata 中数值缺失的排序语义与 pandas 的 NaN 不同，`x>0` 等条件必须显式排除缺失，不能机械翻译。

## 描述统计与相关

- 均值 `x̄=Σxᵢ/n`；样本方差 `s²=Σ(xᵢ−x̄)²/(n−1)`；均值标准误 `s/√n`。不能把总体 SD（分母 n）或标准误当成样本 SD。
- 均值区间在正态独立样本下为 `x̄±t_(1−α/2,n−1)×s/√n`；比例区间须注明 Wilson、精确 Clopper–Pearson、Wald 或其他方法，不能只写“95% CI”。
- 分位数与偏度、峰度必须指定算法（插值、偏差修正、超额峰度或原始峰度）。同名的 median/quantile/skew/kurtosis 函数不保证同口径；用含重复值、偶数 n 的样本验证。
- Pearson `r=Σ[(xᵢ−x̄)(yᵢ−ȳ)]/√[Σ(xᵢ−x̄)²Σ(yᵢ−ȳ)²]`；检验 `t=r√[(n−2)/(1−r²)]`，df=n−2，在相应分布假设下使用。完美相关、常数列单独处理。
- Spearman 为秩的 Pearson 相关，重复值采用一致的平均秩；简式 `1−6Σdᵢ²/[n(n²−1)]` 仅适用于无并列秩。Kendall tau-b 的分母含 X 与 Y 的并列校正，不可用 tau-a 替代。成对删除的相关矩阵每格 n 不同，甚至可能非正定。
- 控制 q 个线性协变量的偏相关可用 X、Y 分别对控制集与截距回归后的残差相关；标准检验 df=n−q−2，要求控制集独立并核对实际秩。

## 均值检验与效应量

单样本 `t=(x̄−μ₀)/(s/√n)`，df=n−1。配对数据先按 ID 对齐，`dᵢ=xᵢ−yᵢ`，对 d 作单样本检验；df 是完整配对数减 1。

独立样本等方差检验：

```text
sp² = [(n1−1)s1²+(n2−1)s2²]/(n1+n2−2)
t = (x̄1−x̄2−Δ0)/sqrt[sp²(1/n1+1/n2)]
df = n1+n2−2
```

不等方差检验的统计量及 Satterthwaite 自由度：

```text
a = s1²/n1; b = s2²/n2
t = (x̄1−x̄2−Δ0)/sqrt(a+b)
dfS = (a+b)² / [a²/(n1−1)+b²/(n2−1)]
```

这里有重要的软件命名差异：通称 Welch–Satterthwaite 的实现通常采用上式。Stata `ttest ..., unequal` 使用 Satterthwaite；`ttest ..., welch` 使用另一近似 `dfW=−2+(a+b)²/[a²/(n1+1)+b²/(n2+1)]`。不能把“Welch”字面相同当成 df 相同。两侧 p 为 `2×Pr(T_df≥|t|)`；区间用相同 df。按实际 SPSS 输出的 df 与公式选择 Stata 选项。参见 [Stata ttest 方法与公式](https://www.stata.com/manuals/rttest.pdf) 及 [IBM T-TEST](https://www.ibm.com/docs/en/spss-statistics/31.0.0?topic=reference-t-test)。

效应量须写明标准化分母及符号：独立组 `d=(x̄1−x̄2)/sp`；Hedges `g=J(ν)d`，`J(ν)=Γ(ν/2)/[√(ν/2)Γ((ν−1)/2)]`，常用近似为 `1−3/(4ν−1)`，不得把近似冒充精确。配对 `dz=d̄/sd` 与使用原始测量 SD 的 dav 等不同。效应量 CI 应使用对应非中心分布或明确的重抽样方法，不能简单复用均值差区间。

## 列联表、秩检验与多重比较

- Pearson `χ²=Σ(Oij−Eij)²/Eij`，独立性模型 `Eij=行和×列和/n`，df=(r−1)(c−1)。结构零、权重或抽样设计会改变适用条件。2×2 的连续性校正与不校正结果分别保留，不能互换。
- Cramér `V=√[χ²/(n×min(r−1,c−1))]`；偏差校正版本是另一估计量。OR 的事件与参照组先固定；零格修正不得静默增加 0.5。
- Fisher 双侧精确 p 有不同尾部定义；对齐目标软件规则，不能以单侧 p 乘 2 自动替代。McNemar 仅用不一致配对格，精确二项与渐近校正分别标注。
- Mann–Whitney 若 `R1` 为第一组秩和，可定义 `U1=R1−n1(n1+1)/2`，`U2=n1n2−U1`；报告的 U、秩和或 z 符号必须与软件表格定义一致。检验通常针对分布；只有额外位置平移假设下才解释为中位数差。
- Wilcoxon signed-rank 要固定零差值策略、对绝对差并列的秩与方差修正、精确或正态近似、连续性校正。不要在有并列/零值时使用无并列的简式方差。
- “精确 p”是实际计算方式而非小样本标签。版本可能改变自动触发精确算法的阈值；例如当前 [Stata ranksum 文档](https://www.stata.com/manuals/rranksum.pdf) 描述了随 n 变化的默认行为，实际运行要核对本机版本。
- Bonferroni、Holm、BH/FDR、Tukey、Games–Howell 的比较族、统计量与适用条件分别记录。p 值校正、同时置信区间和原始单次区间不能混标。

## ANOVA 与线性回归

经典单因素 ANOVA `F=MS_between/MS_within`，df=(g−1,n−g)。`η²=SS_effect/SS_total`；`partial η²=SS_effect/(SS_effect+SS_error)`。多因素时 SS 类型、模型秩、缺失单元与对比决定分子，不能仅按组数套 df。

OLS 在满列秩时 `β̂=(X′X)⁻¹X′y`；计算使用 QR/SVD 或库的稳定算法，不显式求逆。`σ̂²=e′e/(n−k)`；经典协方差 `V=σ̂²(X′X)⁻¹`。`R²=1−SSE/SST` 需注明是否含截距和 centered/uncentered；有截距时调整 `R²adj=1−(1−R²)(n−1)/(n−k)`。

```text
A = (X′X)⁻¹
HC0 = A [Σ xᵢxᵢ′ eᵢ²] A
HC1 = n/(n−k) × HC0
HC2 = A [Σ xᵢxᵢ′ eᵢ²/(1−hᵢᵢ)] A
HC3 = A [Σ xᵢxᵢ′ eᵢ²/(1−hᵢᵢ)²] A
Cluster base = A [Σg (Xg′eg)(Xg′eg)′] A
```

聚类修正常见因子 `G/(G−1)×(n−1)/(n−k)`，但不要用于所有命令：FE 吸收、权重、多向聚类、小样本方法会改变系数与 df。必须核对目标命令。单个系数推断的 t/z、联合检验 F/χ²及分母 df，和协方差矩阵一样重要。参见 [Stata regress](https://www.stata.com/manuals/rregress.pdf)。

标准化线性系数在普通含截距 OLS 下为 `βj*=βj×sxj/sy`，使用同一分析样本的 SD。交互、多项式、哑变量、加权与潜变量标准化须另外定义，不能对所有模型自动套用。VIF 也必须说明基于哪些设计列。

SPSS 与 Stata 均须显式指定 SS/对比和样本，不以“默认 Type III/partial”推断复杂设计完全相同。重复测量需核对误差层次及 GG/HF 修正；混合模型还需指定 ML/REML、协方差结构及固定效应 df。参见 [Stata anova](https://www.stata.com/manuals/ranova.pdf)。

## GLM、离散结局及混合模型

- GLM 写明 `g(μ)=Xβ+offset`、响应分布和尺度。Logit `p=expit(Xβ)`，OR=`exp(β)`；Poisson log-link 的 IRR=`exp(β)`；这些不能混标为均值差。若使用 Wald 区间，先在 β 尺度得到区间，再指数变换。
- 二项数据的事件编码、trials、权重与聚合方式必须一致；序数模型阈值参数的符号和参照方向按软件参数化解释。
- NB2 为 `Var(Y|X)=μ+αμ²`，NB1 为另一参数化。对数似然是否包含常数、过度离散参数定义、AIC/BIC 的 n 和 k 都需对齐。
- 一般极大似然：指定似然、link、起值、约束、梯度/海森矩阵与优化收敛。完全分离、边界估计或非正定海森矩阵不得输出常规 Wald 显著性并假称拟合成功。
- 线性混合模型 `y=Xβ+Zu+ε`，`u∼N(0,G)`、`ε∼N(0,R)`，边际协方差 `V=ZGZ′+R`。ML 与 REML 的目标不同；随机效应 SD、variance、covariance 与 correlation 参数不能混比。广义混合模型还受积分/近似算法影响。
- GEE 的稳健协方差是独立聚类级 sandwich；与 GLMM 的条件参数不可直接比较。根据模型应报告估计值、SE、CI、检验、拟合诊断和有效聚类数。

## 测量模型、中介及调节

- 原始 Cronbach alpha `α=k/(k−1)×[1−Σsj²/s_total²]`；标准化 alpha `αstd=k r̄/[1+(k−1)r̄]`。k 为题数；总分必须按既定反向和缺失规则计算。alpha 不能证明单维性或结构效度。ICC 按单向/双向、固定/随机、绝对一致/一致性、单次/平均测量分别写公式和模型名称。
- PCA 对相关/协方差矩阵分解；EFA 模型 `Σ=ΛΦΛ′+Ψ`。载荷的符号、因子排列以及旋转解不唯一；数值比对前允许明确记录的符号/排列匹配，再比较共同度、重构矩阵与目标函数，不能用任意旋转掩盖估计差异。
- CFA/SEM 要固定潜变量尺度、残差相关、均值结构、估计量和缺失处理。标准化分为不同方案；CFI/TLI/RMSEA/SRMR 的基线模型、稳健校正、df 和区间计算按引擎版本查证。不要把 ML、稳健 ML、WLSMV、DWLS 互称等价。
- 简单线性无交互中介：`M=iM+aX+γC+eM`，`Y=iY+c′X+bM+δC+eY`；间接效应 `ab`。在同样本、同控制及相应线性设定下才有 `c=c′+ab`。非线性、交互或不同样本不强行分解。
- 调节模型含 `b3 XW`；X 的条件斜率 `b1+b3 W`，其方差由完整系数协方差求得：`Var(b1)+W²Var(b3)+2W Cov(b1,b3)`。简单斜率、Johnson–Neyman 与预测概率区间使用对应模型尺度。
- Bootstrap 写明重抽样单位、重复数、随机数生成器、失败拟合处理和区间（percentile、basic、BC、BCa 等）。相同 seed 在不同引擎不保证相同重抽样；严格重现需保存并复用实际抽样索引。不能用 Sobel p 值替代 bootstrap 区间。

## 插补、调查、生存及其他专门方法

- Rubin 合并：`Q̄=ΣQm/M`，`Ū=ΣUm/M`，`B=Σ(Qm−Q̄)(Qm−Q̄)′/(M−1)`，`T=Ū+(1+1/M)B`。有限样本 df 与联合检验需按具体合并规则；不是把 M 份 p 值平均。参见 [Stata MI](https://www.stata.com/manuals/mi.pdf)。
- 复杂抽样先固定权重、PSU、strata、FPC、子总体和方差法。普通 weighted OLS 的 SE 不等于设计式 SE。参见 [Stata SVY](https://www.stata.com/manuals/svy.pdf)。
- Kaplan–Meier `Ŝ(t)=Π_(tj≤t)(1−dj/nj)`，风险集必须包含准确的进入、退出、删失规则；Greenwood 区间还取决于变换。Cox 的 ties 近似、层化、稳健 VCE 和时间尺度一致才可比。SPSS 某些 COXREG 版本的 ties 能力有限，不能用不支持的选项补造对齐；查 [IBM COXREG 说明](https://www.ibm.com/support/pages/node/418819) 及当前版本手册。
- 面板、时间序列、因果、Meta、空间及 Bayesian 模型的公式不在此概括为“通用回归”。读取 [methods.md](methods.md) 对应专业手册并形成方法卡，尤其核对初始状态、W 矩阵、效应量、识别假设、先验和 Monte Carlo 误差。

## 逐结果对齐与合理容差

比较次序：有效样本和权重 → 编码和设计矩阵 → 点估计/目标函数 → VCE/df → CI/检验/p → 图表与正文。样本 ID、类别标签、参照组、方法类型应精确一致，不能靠数值容差通过。

本 skill 的比较脚本采用 `|a−b|≤max(atol, rtol×max(|a|,|b|))`；这与某些库的 `atol+rtol×|b|` 判据不同。按量纲与算法条件事先设定容差；接近零用绝对容差，极小 p 可比较可靠计算的 log-p（字段另行命名并注明尺度）。不能为通过验证临时放宽阈值；只比较已显示的小数位不能证明原生精度一致。迭代模型和模拟方法报告收敛误差或 MCSE，不能承诺逐位相同。

本文件公式是实施检查点，核对日期 2026-11-01；引用入口的版本不自动替代本机版本。任何“原生一致”的结论必须附本次原生输出、精确设置、对应字段、容差及实际比较记录。
