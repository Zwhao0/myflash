# G01 完整审批合同

状态 OPEN / REQUIRES_OWNER_DECISION；所有取值待批，当前 final_alert=false。推荐 a：论文点名库的有界 BEAST 窗口候选功能复现。b 为 cpOccPr 敏感性 EXTENSION；c 坚持经典 run-length BOCD 等价时当前路径不满足，需另批新设计。

PAPER p26 给出 BOCD run-length、Rbeast、窗口30、0.8和20%；未定义 BEAST 模型。UPSTREAM 固定0.1.25 sdist 的 BEAST 为分段 trend 模型平均 MCMC；cpPr 是配对候选的局部后验出现率汇总，cpOccPr 是逐位置出现率。二者不能声明等于经典 P(r_t=0|x_1:t)，也不是校准的故障概率。源码与输出证明当前调用没有前次 run-length 后验递推状态。

## 24 个显式参数（逐项 ADAPTATION）

| 参数 | 原值 |
|---|---|
| start | `1` |
| deltat | `1` |
| season | `"none"` |
| method | `"bayes"` |
| tcp_minmax | `[0, 10]` |
| torder_minmax | `[0, 1]` |
| tseg_minlength | `1` |
| tseg_leftmargin | `0` |
| tseg_rightmargin | `0` |
| mcmc_seed | `20261010` |
| mcmc_burbin | `200` |
| mcmc_chains | `3` |
| mcmc_thin | `5` |
| mcmc_samples | `8000` |
| precValue | `1.5` |
| precPriorType | `"componentwise"` |
| hasOutlier | `false` |
| print_param | `true` |
| print_progress | `false` |
| print_warning | `true` |
| quiet | `false` |
| gui | `false` |
| dump_ci | `false` |
| dump_mcmc | `false` |

mcmc_burbin 为接口真实拼写。模型支持、precision prior、链数/采样/种子、关闭 outlier 均未由论文规定；print/gui/dump 也是有界工程选择。未批准不得写入正式默认。

## Wrapper 隐式默认与 native 限制（UPSTREAM）

精确签名未传默认及全部可静态识别硬编码常量见 WRAPPER_DEFAULTS.json；按固定 wrapper AST读取，不加载 Rbeast。season none/outlier false 的字段存在不表示启用；detrend/deseasonalize false、trendComplexityFactor0、modelPriorType1、K_MAX0、maxMoveStepSize6、trendResamplingOrderProb0.1、seasonResamplingOrderProb0.17、CI alpha0.95、线程2/0、输入副本/输出配置均不可隐去。没有额外 kwargs，不强制 ISA，实际 ISA 是运行观测；不能由 defaults 保证计算量或跨机器重复性。

native 把 minSepDist 至少提升到 trendMaxOrder+1，当前至少2，并按N约束最大knot和margin；每前缀有效配置需从原native配置核对。tseg_rightmargin0 不等于 p44右侧保护k。完整固定上游 path/function/行号/文件和选段 SHA 见 SOURCE_LEDGER.json。

## 完整次序与判定优先级

1. validate_sequence: one run, rank0, positive finite time_ms, contiguous unique ordered iterations; invalid input -> INVALID_INPUT [ADAPTATION]

2. take last 30 original records before removals [PAPER window30 / ADAPTATION truncation order]

3. drop global iteration<=3, not first3 of each rolling window [PAPER warmup3 / ADAPTATION global interpretation]

4. population mean/std over eligible current window; abs z>3 removes points, z=3 retained; zero std uses z0; sample z audit only [PAPER z>3 / ADAPTATION population absolute statistic]

5. compress retained samples into start1/deltat1; preserve bidirectional mapping; <8 retained or constant series -> INSUFFICIENT_EVIDENCE [ADAPTATION]

6. fresh subprocess BEAST bayes refit current retained prefix window only, timeout30s; version/selected binary identity checked; failures never become zero probability [UPSTREAM BEAST / ADAPTATION per-prefix worker, timeout, identity]

7. raw tree kept; cp time->cp-1->current original iteration; cpPr paired slots, cpOccPr length N; null/null padding skipped; invalid/duplicate coordinate, invalid probability/shape -> INSUFFICIENT_EVIDENCE; no ncp_mode truncation [UPSTREAM output / ADAPTATION validation]

8. sort valid candidates chronologically by filtered index0 then slot; probability cpPr>=0.8 [PAPER0.8 / ADAPTATION inclusive comparison and sorting]

9. spacing original_iteration-previous>=2; previous only updated if probability AND spacing pass, BEFORE recovery/strength; later recovery-rejected point can suppress neighbour [PAPER distance<2 / ADAPTATION reference and order]

10. whole filtered window left[:i], right[i:], recent[i+1:]; means b,d,r; A=(d-b)/b,B=(d-b)/d calculated for audit before status selection, both strict>0.2; no approved formula [PAPER slices20% / ADAPTATION both formulas]

11. status precedence: probability fail -> spacing fail -> insufficient left/recent or d-b=0 -> recovery>=0.75 transient -> d-b<=0 no increase -> AMBIGUOUS_SPEC; recovery=(d-r)/(d-b), no clipping [PAPER recovery / ADAPTATION exception and priority]

12. after choosing formula, proposed final conjunction additionally requires selected G02 gate in this current prefix. Current persistence decision None, final_alert always false; no winner conflict/dedupe/final alarm invented [ADAPTATION approval boundary]

PAPER p27按“持续性、间距、预热、离群”介绍四重过滤，但明确离群发生拟合前；本文记录真实可执行的前处理和候选次序，并把论文未唯一规定部分标为ADAPTATION。间距合格点先更新previous，后恢复失败仍可抑制邻点，此细节须明确批准。preprocess guards不是所有上游模型的普适要求。

压缩轴删除一个原迭代间隙后仍步长1；保留映射只解决追踪，不能消除模型先验/时序改变。滚动窗口重拟合会修改旧cp、概率、成员、均值；当前前缀无未来泄漏并不意味着经典在线递推。无左右样本、零恢复分母、非法输出、worker异常/超时均不能变成无故障。G01批准只允许声明有限功能复现，不证明收敛、概率校准、科学等价或GPU效能。

当前支持N=8..30时，有效trendMinSepDist=2，显式左右margin0保留，trendMaxKnotNum=min(10,ceil((N-1)/3))；模型prior的显式值和native约束同时纳入审批，不把传入10解释成固定返回10槽。
