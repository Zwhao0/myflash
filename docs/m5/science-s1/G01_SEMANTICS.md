# G01：BOCD、BEAST 与当前工程语义

结论：当前工程实现了“每个新前缀的过滤后窗口，重新执行 BEAST Bayesian
model averaging，再筛选历史 trend 变点”。它使用论文点名的 Rbeast，但没有实现
或证明经典在线 run-length posterior 的递推。候选 C 解决有限范围重复性工程
问题，不证明 `trend.cpPr >= 0.8` 与论文 BOCD 判决等价。
状态：**OPEN / REQUIRES_OWNER_DECISION**；科学有效性 NOT_APPROVED。

## 证据身份与引用方法

PAPER：`references/chapter3.pdf` 的完整印刷页 26、27、40、43、44 已视觉核对。
该摘录 PDF 从印刷页19开始，摘录页号=印刷页−18；原全文 PDF 页号=印刷页+16。
例如印刷26对应摘录第8页、原全文第42页，避免把摘录文件当成全文分页。
文本行号与 SHA 见 [source-receipts](data/source-receipts.json)。

UPSTREAM：仅固定 PyPI Rbeast0.1.25 release sdist，SHA256
`8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec`。
[版本发布页](https://pypi.org/project/rbeast/0.1.25/)说明 BEAST 是 Bayesian
model averaging；以下推断以该 sdist 实際 wrapper/native 字节为权威，不依赖
变化的 master 或当前 CRAN 文档。文件 SHA、函数、行号、选段 SHA 均见 source-receipts。
原生文件含非 UTF-8 字节，引用脚本采用 Latin-1 无损字节映射；不改源文件。
包 LICENSE 为 MIT，P1 第三方 notice/再分发缺口未解决；本轮不公开完整源码或 wheel。

ADAPTATION：myflash 固定 commit
`d2973f5fa66ae99ec7ea09ea7040a11d1b95b845`。
`flash/rbeast_adapter.py:PARAMETERS` L12–19、`candidates_from_raw` L22–55、
`RbeastAdapter/worker` L75–125；`flash/change_detection.py:preprocess` L28–54、
`filter_candidates` L57–104、`detect/prefix_replay` L107–130。
全部原文件 SHA 在 input-hashes.json 中。
没有读取/复用 GreyHound 或此前失败 FLASH 源码。

## PAPER 的明确内容及缺口

§3.2.2 印刷 p26 写 run length 后验 `P(r_t | x_1:t)`，以
`P(r_t=0 | x_1:t)` 超过阈值判当前时刻为变点，同时写“FLASH 使用Rbeast”实现
BOCD。同页明确 window30、thresh_prob0.8、degradation_thresh0.2，但没有版本、
BEAST 模型参数或具体结果字段。80%文字为“达到”，公式描述为“超过”；当前
`>=0.8` 是既有实验选择，本轮保留，不宣称论文唯一比较符已确定。

§3.2.2 pp26–27 明确左/右/右去首点三均值与 recovery_ratio，`>=0.75` 过滤；
相邻变点距离<2过滤后续点，前3次跳过，z-score>3移除。
§3.3.2 p33说明监控执行 BOCD 和多重过滤后进入剖析，不能补足模型概率语义。
§3.4.5 p44另有右侧保护 k=1或2；与当前 rightmargin0 和恢复过滤不是同一约束。

## UPSTREAM 实际推断

`py_src/Rbeast/beast.py:beast` L1–45 定义接口；L168–194说明 bayes/MCMC；
L420–450 构造 prior/mcmc，L496–503调用 `cbeast.Rbeast('beast_'+method,...)`。
`ext_src/glue_code.c` L150–174派发单序列核心。
`beastv2_COREV4.c:beast2_main_corev4` L285–390重置并运行各链、提出 basis/knot
模型修改；L513–625接受/拒绝并按 burn-in/thinning 保存样本；L836–852累计每个
样本模型的 knot 出现次数；L1124–1132按保存样本数归一化。整个输入窗口的
likelihood/prior 参与拟合，模型包含分段多项式 trend（这里 order0/1）、误差方差
与 precision 推断；季节/outlier 组件在当前配置关闭。变点位置、数量与阶次在
MCMC 模型空间探索并汇总，不是单一最佳分割，也不是在线 run-length 分布。

不存在从前一次 posterior 状态到新 `x_t` 的 adapter 接口：每次传入独立数组、
启动独立 native worker；既有实现不保存 `P(r_{t-1}|x_1:t-1)` 或 hazard 状态。
因此从源码和调用接口可以证明当前路径非 Adams–MacKay 式递推；无法由此证明
论文实际实现用了哪一种算法，也不能自行将它替换成别的 BOCD。

## cp、cpPr、cpOccPr

| 字段 | UPSTREAM 定义/生成 | ADAPTATION 映射与限制 |
|---|---|---|
| trend.cp | wrapper L266–269；核心 L1523–1540：零基候选位置×deltat+start；按重要性排序，未用槽为 NaN | start1/deltat1时 index0=cp−1，再查本前缀 index0_to_iteration；null padding 单列，非法/重复不补零 |
| trend.cpOccPr | 核心 knot 频率归一化后的逐时刻后验出现率，长度 N | 有限值须在[0,1]；这是以整个窗口为条件的历史位置概率，非告警真实性概率或 run-length posterior |
| trend.cpPr | 核心 L1526–1529将 FindChangepoint 输出 mem 配对 cp；abc_common.c L995–1052概率曲线局部 sum-filter/peak；L1248–1264将汇总值上限置1 | 对 cp 对应局部位置集的后验出现率汇总诊断，不必等于 cpOccPr[cp−1]，更未证明等于 P(r_t=0)；adapter 不额外裁剪 |

UPSTREAM 的 `cpPr` 汇总还依赖实际 minSepDist。wrapper 把 tseg_minlength1 传给
trendMinSepDist；`beastv2_io_in_args.c` L852–889强制至少 trendMaxOrder+1，当前
order上限1使有效 minSepDist 至少2，受短窗口长度约束；sum-filter 的
minSegLen=minSepDist+1，常为3。native 同时限制最大 knot 数，故传入 tcp_max10
不意味着每次都返回10槽。内部选点阈值0.01（核心 L1465）也不是 FLASH 的0.8。
不能把 wrapper 参数名的“最小段长”与论文20次持续性或右侧保护混为一谈。

## 全部 PARAMETERS 账本

下列每个值均为 **ADAPTATION**，接口/默认实现来源为 **UPSTREAM**；论文没有
明确规定其中任一精确取值。source-receipts.parameters 包含完整24项和值，测试
逐项与基线 AST 对照；不把“恰好等于上游默认”转成 PAPER 参数。

| PARAMETERS（原值） | 用途/影响 | 论文依据状态 |
|---|---|---|
| start=1，deltat=1 | 压缩 retained 样本的人工时间轴，便于 cp−1 映射 | 工程坐标，删除异常点后不等距于原 iteration |
| season='none'，method='bayes' | 关闭周期项、选完整 Bayes 分析 | trend-only 假设；论文未指定模型 |
| tcp_minmax=[0,10]，torder_minmax=[0,1] | knot数量与分段常量/线性 trend 支持 | prior/模型能力未经论文批准；native还会约束 |
| tseg_minlength=1，tseg_leftmargin=0，tseg_rightmargin=0 | 段间距/端点支持 | 不能表示 p44 k=1/2 的已批准规则 |
| mcmc_seed=20261010，mcmc_burbin=200 | 可重复种子与预热采样；burbin为真实接口拼写 | 非论文值，C重复性仅有限工程证据 |
| mcmc_chains=3，mcmc_thin=5，mcmc_samples=8000 | MCMC预算和Monte Carlo估计 | 计算耗时/精度未经论文标定 |
| precValue=1.5，precPriorType='componentwise' | 系数 precision 初值和各组件 precision 推断 | prior敏感性仍未验证 |
| hasOutlier=False | 不引入 BEAST outlier 模型，已有 z-score 移除独立发生 | 不能视为论文要求或与z-score等价 |
| print_param=True，print_progress=False，print_warning=True，quiet=False | 保留配置与警告、控制显示 | 工程观测，非科学定义 |
| gui=False，dump_ci=False，dump_mcmc=False | 普通调用路径、不输出CI/完整MCMC样本 | 工程输出选择；raw仍完整保存实际返回树 |

未显式传入的 wrapper prior/extra 默认也影响实际模型（如 complexity0、重采样
order概率、线程选项），不能认为 PARAMETERS 是整个 native 配置的全部。
wrapper L420–479和 P1 保存的实际配置是后续批准/复核入口。
论文七个检测常数在 DetectionConfig 中，不在 Rbeast PARAMETERS 中。

## 重拟合、延迟与历史漂移

ADAPTATION：每个新前缀先截最近30原 iteration、剔除全程前3和当时窗口
population z-score>3点，重建压缩数组，再独立拟合；样本<8的 guard 也是工程
选择，名称含 NATIVE_MINIMUM 不证明所有上游条件均要求8。左右均值取整个
filtered窗口，间距按原 iteration、以先前概率合格且距离合格点为参照；与论文
“首点”在过滤顺序/多变点情形下是否一致尚未唯一规定。

EXTENSION 后果：随着窗口新增/移除点，过去同一位置的概率、局部cp代表点、
z-score成员、baseline/degraded均值都可改变。相同cp坐标在滚动窗口中也可映射
到不同原iteration，须每个前缀独立映射。重拟合只使用当时可见前缀，因此没有
使用真实未来数据；但它会用该前缀右侧数据修订历史变点，这与“当前时刻的
run length在线后验递推”不同。首次概率越线、首次临时候选、cp发生位置和
最终告警必须分别报告；CPU拟合时长本轮未测，不能声称1–2迭代端到端实时性。

当前证据证明 API/映射、重复性和离线算术；不能证明误报率、真实GPU故障
灵敏度、Monte Carlo收敛、概率校准或论文科学等价。推荐先由负责人明确
“论文点名库的窗口候选功能复现”可接受范围；若要求经典BOCD严格复现，现有
证据不能通过，须另行授权科学设计，不能以本轮擅换检测器解决。
