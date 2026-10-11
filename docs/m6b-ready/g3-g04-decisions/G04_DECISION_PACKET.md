# 任务 06：G04 两阶段定位规则决策包

2026-10-11。状态 **REQUIRES_OWNER_DECISION**。本文件及矩阵只用于审批；没有修改、启用或接入任何定位规则。`approved=null`，实际 `final_fault_ranks=[]`。任务 05 的 PR16 精确 head `7588873d705668497694ac1d12041db5005e4b49` / tree `5b345197cb70c95c66c65870c8608a9091c4621d` 已由负责人在本轮确认独立审核通过，并批准任务 06 发布。

## 可逐项批准的推荐组合

| 维度 | 推荐选项 ID | 内容 | 性质 / 依据 |
|---|---|---|---|
| Stage1 | S1-MAX | 同标签排除单 rank 组；单组直达；多组用 max_avg_latency、CV 门槛、选最大组；绘图 mean score 独立保存 | PAPER，p30/p34、式3-1 p41 |
| communicator 权重 | W-EQUAL | 每个 rank 的本地 communicator 实例均值等权；独立 scope 数加权结果完整保存作敏感性，不投票，不额外扩大到标签内其它 hash | ADAPTATION，论文 p30 聚合未定权；任务06建议 |
| 20% 参照 | R-GROUP | 对最小 rank 用 `(组内 rank 均值 - 该 rank 均值) / 组内 rank 均值`，只测低时延方向 | ADAPTATION，将 PAPER 式3-2 的统计量用作 p31 未定义的百分比过滤 |
| 20% 比较符号 | T-GE | 数学阈值 `>= 1/5`；严格 `> 1/5` 完整保留 | ADAPTATION，p31 只给默认20%，没有指定等号；不继承检测器 G13 的严格符号 |
| CV | C-GUARD | population 为主，sample 保留；两者跨越0.1时 `AMBIGUOUS_SPEC` | ADAPTATION，p31/p34 没有给 ddof；沿用 M4 保守分歧输出 |
| 数值边界 | N-GUARD | 不加 epsilon、不舍入调阈值。浮点计算与对输入 rank/group 均值的有理数参照运算跨阈值时拒判，保存两条证据 | ADAPTATION，本轮算术审计；有理数不能修复测量或上游均值误差 |
| 样本支持 | Q-TWO | 每个参与候选组 rank 聚合的本地实例至少2个去重计时 scope；1个只给观察诊断，不作候选判决 | ADAPTATION，p31 小样本措辞未定义样本数；2仅是最低可计算支持，不是稳定性证明 |
| 标签冲突 / final | F-PROVISIONAL | 同 rank 累积带来源证据；不同 rank、并列、规格分歧拒绝 final；唯一候选仍 provisional，本轮及后续未另批告警前 final 空 | ADAPTATION，p31 未定义冲突、证据最小数、置信度与多故障 |

推荐由文本来源和可审计性决定。正常候选、权重翻转、冲突均原样保留；没有依据 expected 标签或独立真值选择权重、阈值或标签。这些选项必须分别批准；同意发布本包不等于批准科学规则，也不自动授权任务07。

## 1. Stage1 与图表分数

PAPER p30/p34：通信组身份为跨进程 `id_hash`；本地 communicator 是 `(node, global_rank, process_instance, generation)` 的实例，不能用跨进程指针相等代替。相同成员的不同 hash 保持不同组。框架标签、通信组、ncclGroup 批次不是同一对象。

令本地实例平均延迟为 `m_c`，同 hash 组统计 `M_g=max_c(m_c)`；同标签只有一个多 rank 组时直接进入 Stage2，两个以上组时对 `[M_g]` 做 CV，`CV<0.1` 跳过，`CV>=0.1` 选所有并列最大组。单 rank 组事先排除，不参与 CV 和图表参照。

ADAPTATION：如果通过 CV 后出现并列最大组，保留各组 Stage2 观察，并以 `AMBIGUOUS_SPEC/MAX_GROUP_TIE` 阻止唯一/final 判决。所有最大值相等且为正时先命中 CV=0 的 `NO_CANDIDATE`，不绕过 CV 强行定位；全零时 CV 未定义，`AMBIGUOUS_SPEC`。缺组/坏计时/不可靠身份/漏 rank/漏声明 scope 仍按完整性门禁拒绝，不能补零选择最小 rank。

PAPER 式3-1 是绘图统计：`t_g=mean_c(m_c)`，`mu_tag=mean_g(t_g)`，`score_clique=(t_g-mu_tag)/mu_tag`。这是组均值相对同标签可用组均值的分数，不是最大值排序，也不是校准概率。本地实例等权构造 `t_g` 是现有 M4 的 ADAPTATION，不是论文给出的唯一跨实例权重。

原 fixture `max_is_not_clique_score`：A的本地均值2/40us，B为30/30us。Stage1最大值A=40、B=30，应选A；图表均值A=21、B=30，得分A≈-0.17647、B≈+0.17647。改用 score 排序会选B，直接改变论文正文规则，因此不列作可接受基线选项。原 `stage1_maximum_tie` 只有两个同为18us的组，其 CV=0，实际验证的是跳过；它没有验证“通过 CV 后仍并列最大”的分支，该分支是拟议适配，不能补称既有实测覆盖。

## 2. rank 跨 communicator 的权重

仅在选定 hash 的组内，令 `C_r` 为 rank r 的所有已声明本地 communicator 实例；每实例先按独立计时 scope 去重，`n_c` 是去重 scope 数，`m_c=mean(duration_scope_us)`。

| 选项 | 完整定义 | 后果 / 风险 |
|---|---|---|
| W-EQUAL 推荐 | `a_r=sum(m_c)/len(C_r)` | 每个 communicator 实例有同等贡献；低样本实例可能影响很大，Q-TWO与n_c诊断需一并明确 |
| W-SCOPE | `a_r=sum(n_c*m_c)/sum(n_c)`，等价于拼接每实例已去重scope观测 | 调用频率高的实例贡献更大，可能把“不同通信对象”问题变成“观测频次”问题；改变最小rank |

scope标识隐含已验证的 `(run_id, profile_epoch)`；collective用 `(node, process_instance, sample_seq)`，Group用 `(node, process_instance, thread_id, outer_group_id)`。Group多个成员记录只算一个实例内scope；嵌套depth不是新增样本；`count`是数据元素数，4096 float32元素=16384字节，不是样本权重。

跨实例/跨 hash 共用同一个 Group scope 仍是相关观测。W-SCOPE的n_c只表示该实例内去重观测数，不能把总和叫独立随机样本量；本轮矩阵保留现有 M4 的 per-instance scope 加权敏感性，不实施跨comm union、1/k分摊或协方差估计。若负责人要真正跨实例 union，应另批 EXTENSION，并规定同一scope如何分配，不可静默替换本包 W-SCOPE。跨标签共享scope/同一hash的别名也不能凭标签数量增加独立证据数。

原 `aggregation_weights_disagree`：rank0两个实例为1us×9、100us×1；rank1为20us×1、30us×9。等权均值约50.5/25us，最小rank1；scope加权约10.9/29us，最小rank0。原20条输入未改，两套数字都保存。Q-TWO推荐会因两个实例只有1个scope而返回INCOMPLETE；矩阵的 `observational` 支持选项仍完整展示翻转，不能用拒判把科学权重分歧隐藏。

真实M4各组每rank一个本地实例、相同样本数，两权重一致，**这些真实窗口不足以决定不等样本量下的权重**。选择 W-EQUAL 后，W-SCOPE候选不同是公开敏感性风险，不参与额外OR/AND/投票；如果希望一有权重差异就拒判，需要在审批中明确指定额外守卫，不能视为推荐主口径已经包含。

## 3. 20% 的四种参照、方向与边界

令 `a_r` 为所选权重的 rank 均值，`mu=mean(all a_r)`，`peer_mu=mean(a_q,q!=r)`，`peer_min=min(a_q,q!=r)`。只对通过 Stage2 CV 后的最小rank集合计算；不改为选最大rank，不扫描所有低于均值的rank以扩大候选。

| ID | 过滤量 | 来源 / 后果 |
|---|---|---|
| R-GROUP 推荐 | `(mu-a_r)/mu` | PAPER式3-2的score；把它当20%过滤量仍是ADAPTATION。参照包含候选自身，依赖组规模 |
| R-PEER | `(peer_mu-a_r)/peer_mu` | ADAPTATION；与“比其它rank低20%”的措辞相近，论文没有指定该式 |
| R-MIN-DEN | `(peer_mu-a_r)/a_r` | ADAPTATION；换小分母会放大比率；a_r=0时未定义，不能用∞强制通过 |
| R-NEAREST | `(peer_min-a_r)/peer_min` | EXTENSION；要求相对最近比较rank也离群，常更保守；并列最小时可能零分数 |

两rank时 R-GROUP>=20% 意味着 `a_min/a_other<=2/3`；R-PEER>=20%为比率<=0.8；R-MIN-DEN>=20%为比率<=5/6。它们不是同一规则。两个rank的 population CV数学上等于低rank的R-GROUP分数，所以该20%过滤在这个特例比CV0.1更严格；这不是任意rank数量的结论。

T-GE `>=`与T-GT `>`分别审批、并列保存。数学上的[79,121]us对应21%均通过；[80,120]恰20%时T-GE通过/T-GT拒绝；[81,119]为19%均拒绝。**实际现有M4缩放求均值在[80,120]上给99.99999999999999，浮点分数0.19999999999999984**，两种浮点比较都会拒绝；本包N-GUARD对原rank均值有理数重算参照时发现T-GE分歧，输出AMBIGUOUS_SPEC。保留原计算，不把浮点值舍入成0.2、不暗改现有mean函数。

N-GUARD也比较CV的浮点门禁与对输入均值计算的有理数方差/均值平方门禁：数学CV>=1/10等价于CV²>=1/100。它不引入容差带，不保证浮点rank均值等于真实时间或精确原样本平均。二元输入[90,110]的数学population CV恰0.1，现有浮点约0.09999999999999998；[9,11]约0.10000000000000003，缩放本身即可影响边界。N-GUARD是拟议ADAPTATION，不是原算法已经修复边界。

ties用保存均值的精确相等判断；保留所有并列，不按rank编号任选。近似相等值不增加人为tie容差；保存float.hex/原值可在任务07追加审计接口，但本轮没有新增生产字段。并列最小即使所有阈值通过也AMBIGUOUS_SPEC，不视为多故障已证明。分母零时null/拒判；全部零是未定义CV；真实M3 Event duration必须>0，合成零值只作算术逻辑证据。缺数据与零不是同一种状态。

## 4. CV口径与小样本

Stage1统计轴是同标签可用组的M_g，每组一票；Stage2统计轴是选定组内rank的a_r，每rank一票。二者都不按通信样本数再加权CV。时间单位us，CV和过滤比率无量纲。

`population = sqrt(sum((x-mu)^2)/N)/mu`，`sample = sqrt(sum((x-mu)^2)/(N-1))/mu`。N=1时sample未定义：Stage1单组明确跳过组间CV直达，单rank组事先排除，不能把未定义sample置0；Stage2少于两个rank属于完整性/范围不足。N=2时sample=population×sqrt(2)，不能忽略差异。零均值CV未定义；N>=2且同值正数的CV=0可正常跳过。

| ID | 主门禁 | 分歧处理 |
|---|---|---|
| C-GUARD 推荐 | population为主，保留sample | 任一适用阶段两者跨0.1，AMBIGUOUS_SPEC，不声称健康或故障 |
| C-POP | population>=0.1才继续 | sample只诊断，即使sample跨阈值也不据此拒判；仍保存N-GUARD数值分歧 |
| C-SAMPLE | sample>=0.1才继续 | population只诊断；更易通过离群分析门禁，不等同科学更可靠 |

原 `std_convention_disagreement` 的rank均值9.2/10.8us：population≈0.08，sample≈0.113137，guard拒判；其它两口径会分别跳过/进入20%计算，仍不保证有候选。M3一个正常all13窗口也存在此类CV分歧：本包推荐guard保留AMBIGUOUS_SPEC；两个单口径配合R-GROUP20%最终都无候选，状态改为NO_CANDIDATE。真实M4被选组没有跨CV阈值分歧；部分**未选组**有分歧（如补充core首窗另一组population≈0.0733、sample≈0.1037），全组统计仍保留，不能说所有真实组两口径一致。

Q-TWO按每个参与rank聚合的本地实例去重scope数检查。某实例只有一个scope，保留m_c和其它标签观察，但合并结果优先INCOMPLETE，不能用CV“跨多个rank”替代“时间样本支持”；1个rank、1个本地实例、1个scope是三个不同概念。坏记录/不完整声明仍全窗拒绝，不因剔除一个坏scope使它达到2个好scope后冒称完整。2个高度相关scope不证明稳定，需要后续科学验证。

## 5. 多标签、并列、多故障与final

| 情形 | F-PROVISIONAL推荐状态与输出 |
|---|---|
| 完整、各门禁可定且无候选 | NO_CANDIDATE；表示本轮规则没有候选，不证明没有故障 |
| 唯一最小rank通过、至少一个有效标签 | PROVISIONAL_CANDIDATE；证据逐(label,hash,rank,scope来源)保存，final空 |
| 多标签一致同rank | 去重累积label/hash/scope证据；不把两个权重方法当两个标签，不打虚构置信度分数；仍provisional |
| 不同标签指向不同rank | AMBIGUOUS_SPEC；保留并集与每标签轨迹；不挑最高score、最多票、最先出现者，不按真值择标签 |
| 通过门禁的最大组并列、最小rank并列 | AMBIGUOUS_SPEC；保留所有并列与阈值结果，不判已发生多故障 |
| 缺声明必需标签/rank/实例/采集数据，或任何坏证据 | INCOMPLETE；不能把缺失标签当投票弃权后输出final |
| 全零CV/数值门禁或口径跨界无法定 | AMBIGUOUS_SPEC；不是NO_CANDIDATE |

“必需标签”须来自独立于真值的工作负载声明。现有parallel_states可校验显式映射、所有comm是否被匹配，不能凭空知道框架是否漏报整个预期标签；缺少该声明时不声称覆盖所有并行标签。本轮不添加生产expected_labels接口，任务07若采用需单列适配接口及批准范围。

另外两种供负责人比较：F-SINGLE可把完整无冲突的唯一候选视作final资格；F-TWO要求至少两个不同标签一致才有资格。矩阵的`hypothetical_final_eligible`仅模拟这两种最简准入条件，**没有通过G09/G20/自动闭环等前置，不能实际告警**。不同hash/label仍可能受同一同步与测量依赖影响，不能默认独立。

原M4正常五组的两个epoch都有两个标签指向rank3，F-TWO也会赋予两个正常窗口final资格。故“两个标签一致”本身无法解决已见误报，不推荐据此直接放行final。已有迟到五组5/10冲突没有证据区分单故障的连带统计与真实多故障；允许多个final故障rank是另一个EXTENSION，需独立真值与多故障实验。所有候选来自时延；真值仅在计算完成后由评估器对照。

## 6. 只读敏感性结果

137行：65原fixtures（24有效/41预期拒绝）、30补充真实窗口、2原M4正常五组窗口、40个M3公开统计窗口。固定Stage1与N-GUARD，权重2×CV3×参照4×符号2×支持2×final政策3=288组合（N-BINARY只列方案风险，没有另做矩阵），39,456单元；41无效输入的11,808单元只记录拒绝，27,648单元为有效统计分析。矩阵保留baseline、全组双权重/CV/四分数/Stage1与图表参照、推荐输出、所有组合与独立评估对照。

本机existing Python3.12.14、macOS26.6.2/arm64运行审计；65固定手写断言和原退出码全部核对通过，32个M4真实窗口的整个预测JSON逐字段等于原保存结果。M3的40窗按原固定序号/预热选择复用公开CSV，候选与历史M4记录一致；只做充分统计重算，原私有raw digest/身份验证继承历史，**本轮未重验原私有raw**。40窗包含all13和fixed_warmup3的重叠观测，不能当40次独立实验。

以下均用W-EQUAL、C-GUARD、N-GUARD、T-GE、Q-TWO，只改变参照：

| 证据 | 原禁用20% | R-GROUP推荐 | R-PEER / R-MIN-DEN / R-NEAREST |
|---|---|---|---|
| core迟到16窗 | 16/16目标排序匹配 | 16/16候选匹配 | 同样16/16 |
| core正常4窗 | 4/4临时候选 | 3/4仍有候选；首窗R-GROUP≈0.181878被过滤 | 4/4仍有候选；首窗R-PEER≈0.308通过 |
| five全部10窗 | 5/10冲突 | 5/10仍冲突，另5窗provisional | 相同5/10冲突 |
| five迟到8窗 | DP排序8/8匹配，5窗冲突 | DP证据仍匹配；合并仅3/8唯一匹配，5/8多rank冲突 | 相同 |
| five正常2窗 | 2/2候选rank3 | 2/2仍有候选 | 相同 |
| 原M4正常五组2窗 | 2/2双标签rank3 | 2/2仍有候选；F-TWO亦具假想final资格 | 相同 |
| M3公开统计40窗 | 两个口径各迟到16/16；正常各3/4候选 | 32迟到观察匹配、8正常观察中6候选；其中另1个all13为规格分歧、1个fixed_warmup3无候选 | 候选集合相同 |

这些是固定历史数据上的规则敏感性，不是新GPU实验、最终故障precision/recall、自动检测率、20秒剖析闭环或降频/网络拥塞结论。所有正常与冲突场景保持原标签/值/数量；原expected.json只校验既有算法，没有被拿来生成新方案期望。

推荐政策全137行有70provisional、55INCOMPLETE、6NO_CANDIDATE、6AMBIGUOUS_SPEC；55中41是原坏输入、14是原有效合成用例在拟议Q-TWO下只有单scope支持。这不修改旧测试预期，不能将14写成原M4失败。`observational`整套矩阵保留原单scope排序/权重翻转/并列/标签冲突。

## 7. 审批账本、退出与下一关

机器可读选项、公式、性质、来源、风险与独立approval空位见`APPROVAL_LEDGER.json`；`matrix.json`、`validation.json`、`preservation.json`、`source-ledger.json`、`failure-index.json`和`postflight.json`绑定命令、源码/输入/输出SHA与实际退出。原始本轮日志在项目私有 `runs/m6b-ready-g3-g04-20261011`。审计01/02/03/04均exit0；01/02是数值参照逐步补齐前的中间报告，保留且不覆盖，03为最终数值方案，04在独立任务06工作树复验并逐行相等，最终命令以04为准。

本轮新增文档/审计脚本/任务，STATUS/GAPS只追加。原1954文件在来源checkout全部保持；任务06分支除STATUS/GAPS追加外1952文件保持原字节，flash/、全部fixtures、M4原证据及失败历史均不改。新原生拟合、M5矩阵、GPU/Redis/控制器、安装、native编译、服务器环境盘点与任务07均NOT_RUN；历史915-cache保全缺口与历史隐私/权利DEFERRED/OPEN不修补。

下一唯一动作：独立审查任务06 Draft PR精确head/tree和上述每个选项，明确S1/W/R/T/C/N/Q/F选择及批准范围。只有完整科学选项批准、并明确授权任务07后才能改定位算法；本轮交付后停止。
