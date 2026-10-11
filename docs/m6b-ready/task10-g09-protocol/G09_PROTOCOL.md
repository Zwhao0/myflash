# TASK10 — 两台 8×H800 的 G09 实验准入协议 v1

状态：**PROTOCOL_FOR_REVIEW**；GPU 注入 **NOT_RUN**，M6-B **NOT_STARTED**。
本轮授权仅制定协议。下列“可准入”表示未来满足条件后可申请的范围；
不授权运行、降频、终止进程、背景通信、安装软件或迁移 runtime。
基点 `f44e3fb44e48979298a13efbd9dccad5000c3eef` /
tree `1a4f6cec6597f907f9ebe647c62de921fbcb70e4`。

## 1. 科学口径与现有边界

**PAPER**（SPEC S4/S6/S7/S9；§3.2.3 pp27–31、§3.3.2 p34、§3.4 pp36–45）：
Profile 用 CUDA Event，窗口 `W=max(2.2*T_ms/1000,20)s`；同标签选最大
communicator 平均时延组，组内选最小平均时延 rank。Group 公共 duration
只是一项共享 scope 观测；不能把组内 collective 条数作为独立样本数。
fail-stop 使用 NCCL 调用新鲜度；原论文 H200，当前 H800 属功能/机制检验。

**ADAPTATION**（GAPS M3/任务05/07/09 与对应 RESULT/APPROVAL）：
既有 M3 仅支持小负载、单机及两机各一 rank 的 CPU/GPU 通信前迟到现象；
没有降频/真实拥塞/真实 MoE/多故障证据。保持 G09 OPEN。
Detector 显式批准路径仍为固定 BEAST/Rbeast 参数、30 迭代窗口、
`cpPr>=0.8`、当前原始 iteration 跨度 `t-j+1>20`、过滤均值
`A=(d-b)/b>0.2`；不得调参数追求 1–2 迭代。
G04 保持 W-EQUAL/R-GROUP/T-GE/C-GUARD/N-GUARD/Q-TWO/F-PROVISIONAL，
数值歧义、标签冲突、缺数据均保留；`final_alert=false/final_fault_ranks=[]`。
在线系统没有获准的硬件/软件/计算/网络根因分类器。

**UPSTREAM**：Event 返回 ms，记录保存 us 时显式乘 1000；事件区间可含
排队/其他 stream 干扰，不宣称纯 NCCL 内核时间。[CUDA12.8 Event API](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-runtime-api/group__CUDART__EVENT.html)。
Group 可批量提交且操作次序须一致。[NCCL2.27.3 Group API](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/usage/groups.html)。
这些接口语义不能代替目标机实际版本、加载库和依赖链实测。

## 2. 故障分类、目标与可准入范围

以下选择为 **ADAPTATION**（G09/G08/G12/G13、PLAN M3/M6/M7）；
辅助 sleep/kernel/背景流量负载的故障模型为 **EXTENSION**。
每次只注入一种机制。候选根因由独立注入证据定义，不从定位结果倒推。

| ID | 未来场景与确切目标 | 独立真值 / 区分依据 | 范围与结论限制 |
|---|---|---|---|
| N0 | 相同负载无注入，含 sham 控制动作 | 私有 evaluator 记 root_ranks=[]；保存正常长计算段 | 必须有；正常产生候选也计误报，不删组/样本 |
| C1 | 一个训练 rank 在 NCCL 提交前 CPU 有限等待 | rank/PID/进程启动标识、预定迭代、实际等待开始结束、实际等待 ms | CPU 迟到机制；不是 GPU 算力或 NCCL/网络故障 |
| C2 | 一个节点所有已注册训练 rank 均按 C1 延迟 | root_ranks=该节点训练 rank 完整集合；逐 rank 证据 | 慢节点多目标边界，首轮单 rank 阶梯后另列；不能算单 rank 命中 |
| G1 | 一个 rank 做额外 GPU 前置计算，再沿 compute→event→comm wait→Probe start 依赖链通信 | 前置工作 Event 时长、stream/依赖、工作量、GPU UUID、实际完成证据 | GPU 计算迟到辅助模型；不是物理降频；前置工作须在通信计时区间外 |
| G2 | 一个独占 GPU UUID 有限 SM 时钟限制 | 设定前状态、允许 MHz、命令回读、期间实际 SM 频率/计算时长、恢复回读；映射所有受影响 rank | 设备级退化，可能同时拖慢计算和 NCCL；不能默认标“纯计算慢” |
| N1 | 本项目独立背景 NCCL 作业在已批准 GPU/网卡端口之间通信 | 背景作业 PID/PG/字节量/时间、链路计数变化、前置计算及通信 Event 对照 | 通信压力/资源竞争边界；背景 GPU kernel 也可能占算力，证据不足时标混合影响 |
| F1 | 指定一个训练 worker 自行退出，或对确切 worker PID 发已批准信号 | evaluator 记录退出码/信号、PID启动标识、最后进展、launcher 对同作业的后续终止 | 受控进程 fail-stop；不代表 GPU 挂死、机器断电或网络断路 |

C1/G1 第一轮分别覆盖两节点的目标，含 rank0 与非 rank0；16 rank 时建议
目标 global rank0、global rank8，但必须以实际 rank→node→local rank→GPU UUID
登记为准，不能假设 CUDA_VISIBLE_DEVICES 索引等于物理设备索引。
C2（整节点CPU迟到）、G2的节点多GPU版本、并发多故障、GPU OOM/硬件 hang、强制 NCCL timeout、
节点断电/重启、网卡 down/tc/丢包、GPU reset、功耗/内存时钟改变不在首批准入。
G2 的单 GPU 行不授权整节点降频；N1 背景作业不能混入被观测训练 communicator。
没有真实 rank 根集合的共享链路压力只报告 affected_ranks/链路目标和边界，
rank precision/recall 写 NOT_APPLICABLE，不能人为指定一个“故障 rank”。

**ADAPTATION**：保存注入控制量与实际效果两列。sleep ms、前置 kernel 工作量、
SM MHz/相对变化、背景 bytes/s 均不是论文“5%–85%退化”的同义值。
evaluator 用同负载未注入基线 30 个有效迭代的均值 B 和预登记故障段均值 D
报告 `duration_growth=(D-B)/B`；固定工作量时另报 `1-B/D` 与实测吞吐损失。
不能用此独立真值基线替换 detector 当前窗口均值或向它提供效果标签。
所有预登记故障都保留：实测 <20%、没有触发、负效果、失败均不删。

## 3. 真值隔离与运行清单

**ADAPTATION**（AGENTS 真值隔离、PLAN 统一实验包、TASK09）：
RUN_MANIFEST_TEMPLATE.json 仅列字段；未来 launch 前必须填实值并封存 SHA，
空字段直接 BLOCKED。分三份权限边界，不把私有部分加载到 controller：

| 文档/进程 | 所含内容 | 可读取者 |
|---|---|---|
| public_runtime_manifest | run_id、代码/tree/diff/二进制 SHA、环境、rank/comm/组成员、每rank单scope线程、计时单位、控制参数、预算 | 训练、Probe、Local/Global、detector、localizer |
| private_injection_plan 与 truth_events | scenario、target GPU/PID/rank、注入迭代/时刻/强度、根集合、成功/失败/恢复证据 | 隔离 injector、safety supervisor、独立 evaluator；训练目标只能接受自己的注入动作 |
| sealed_predictions 与 evaluation | 在线原输出及输入 SHA、scope/epoch、首次检测/候选/最终字段；事后匹配/指标 | 预测先封存，evaluator 后关联真值；在线系统无反向访问 |

run_id 使用不含场景/目标/强度的随机 ID；线上 CLI/env/Redis命名/key/value、
共享内存和日志不携带注入目标、真实类别、计划或真假故障时刻。
注册所需全量 rank/GPU 映射不包含“选中故障”标记。
仅文件权限不足以隔离同用户进程：未来需独立 OS 身份/隔离容器挂载或等效
已验证访问边界；在线身份直接读取/列目录私有真值及读取 injector 环境的
负向检查必须失败。当前该检查 NOT_RUN；不可称无泄漏已验收。
不得把注入分支内知道真值的训练代码传给 detector；force-profile 必须标
FORCED_PROFILE，其预定采样由控制计划触发且不给 localizer 真值标签。

独立 evaluator 记录：event_id、根集合 root_ranks、实际影响集合 affected_ranks、
secondary_stalled_ranks、申请时间、实际生效区间、结束/恢复、每事件时钟域与
不确定度、原始证据 SHA、注入是否成功。非注入因子的连带影响标混合/未知。
注入失败不能计成功故障 TP/FN；但进入计划完成率的分母，原日志不可删除。

## 4. 注入预算、超时与恢复

以下数值是 **ADAPTATION 提议上限**（AGENTS 安全、既有 M3 预算），不是论文参数，
未来执行须明确审核并按机器条件缩小；本轮全部 NOT_RUN。

| 项目 | 首批上限 / 准入动作 |
|---|---|
| 单次 trial | 600s 墙钟，启动→恢复/精确清理都在内；启动前封存各阶段预算 |
| 持续注入 | 每 episode ≤180s；最多2 episode/trial，累计≤360s；超时独立停止注入 |
| C1/C2 | 每个指定迭代一次有限 sleep ≤100ms；不忙等、不降低整机CPU资源 |
| G1 | 每次前置GPU工作校准≤100ms；有限循环，无持久kernel；allocated/reserved高水位及采样显存有日志 |
| 小负载显存 | 每训练rank/单GPU≤2048MiB记录上限，启动前可用≥3072MiB；运行采样超限则结束本次作业。不是硬件瞬时隔离保证 |
| G2 | 一次一个独占UUID；锁定值须来自实际支持范围，不预写H200 MHz；不改memory/power/persistence设置 |
| N1 | 两机相关GPU/链路资源独占；一对背景rank，buffers≤512MiB/rank，背景含runtime总显存≤2048MiB/GPU，且同GPU合计预算预登记；目标流量上限为已测空闲链路吞吐的25%，不能限速/核验则BLOCKED |
| 控制超时 | accept/apply、drain/aggregate、Monitor reset 各≤10s；Redis/socket 每次≤2s、总retry≤10s；使用单机/已验证映射时间域 |
| NCCL PG | 小负载显式操作 timeout=60s；启动/全局600s watchdog独立。正常操作无法适用该预算则BLOCKED，不能让超时冒充注入故障 |
| 恢复 | 注入停止后≤30s：G2恢复精确原设置，N1停止并wait本次背景PID，F1所有本作业worker精确退出，原训练不自动续跑 |
| 首批总量 | 每场景/目标/模式3个独立trial；2次episode不当2个独立trial。单批准批次最多12trial/2h，剩余矩阵标NOT_RUN并另批审核 |

**ADAPTATION**：自动持续慢场景预登记至少30预热、30正常、60退化、30恢复迭代；
sham 用相同长度。用于机制的 forced 小阶梯可另固定少量迭代，但不能称自动
检测效果。真实2epoch试验需两段恢复/正常和重新触发，不能直接复用上一轮。
launch 前以该负载校准 T 和预算，保证全部迭代、完整 W、control/drain/reset/
恢复余量能放进总预算；放不下 BLOCKED。不得缩短 W/持久性规则或追加未登记
重复来“拿到一次成功”。瞬时/恢复和长计算负对照独立预登记，保留滤除与误报。

**ADAPTATION**：safety supervisor 在训练/控制进程之外持有具体资源清单和有限期限；
注入前启动有恢复权限的监督进程并验证它不依赖训练/NCCL/Redis继续运行。
只操作本次run登记PID及启动标识，退出前防PID复用；TERM后10s仍未退出才对
同一已核验本作业PID升级KILL并wait。不得 pkill python、清空 /dev/shm 或 FLUSHALL。
按run精确释放共享内存/Redis namespace；训练停止后才unlink。控制面失联、
显存/温度越界、CUDA/NCCL错误、未知其他作业/权限变化时停止本次trial并恢复。
温度保护值用目标设备实际限制与操作者批准值中的较低者，必须填入清单。
恢复失败留 BLOCKED/RECOVERY_FAILED 并停止整个批次，不允许自动GPU reset/系统重启。

**UPSTREAM**：[nvidia-smi 官方文档](https://docs.nvidia.com/deploy/nvidia-smi/index.html)
说明 GPU clock lock/reset 涉及管理权限，reset回默认不等于恢复既有自定义设置。
若无法读回/恢复原clock policy，G2直接BLOCKED，不盲目reset；本轮未验证H800支持。
[PyTorch2.8 distributed](https://docs.pytorch.org/docs/2.8/distributed.html)
说明 NCCL操作超时后的异步状态不可安全继续使用；F1/通信错误后结束当前PG，
下一试验新run/新进程，不声称自动训练恢复。watchdog是实验保护，不是FLASH检测器。

## 5. M6-B 必须补的真实证据及停止门

以下是 **ADAPTATION 准入阶梯**（PLAN M1/M3/M6，任务08/09范围限制），
只能在未来明确执行授权后按序开展，任一功能/数值/恢复失败即停。

| 门 | M6-B 必须执行/验证 | 不能沿用的 CPU 结论 |
|---|---|---|
| B0 | 两机只读重新盘点实际UUID/可用资源/拓扑/RoCE、驱动/runtime/实际lib路径SHA、框架/容器、固定C runtime身份与许可/使用授权 | 历史H800或C CPU证据不能证明本次加载身份；不安装/默认迁移 |
| B1 | 无注入实际通信/小DDP正确性：单机2rank→跨机各1rank→16rank；相同版本下Monitor与手动Profile数值对照 | 历史M1/M3无需整套重跑，但本次最小数值/ABI2冒烟必需 |
| B2 | 真实Reader ctypes/共享内存→本地控制→真实Redis→全局；完成scope proof、epoch/fence、两轮0→1→0、全rank干净drain与新Monitor记录 | task09字典mock/header不能证明实际应用、计时资源清理；仅每rank已验证单scope线程 |
| B3 | 实际框架 begin/end计时含预登记CUDA完成、严格ACK/outbox→有序消费、真实跨进程transport；原始journal先durable写后ACK或明确“崩溃epoch作废” | SQLite mock/内存暂存不是GPU完成、Redis durability、断电/续训证据 |
| B4 | 验证时钟/窗口与真值隔离；单机减法或跨机映射及误差界；实际物理scope所属窗口由原始证据确认 | collected_at receive时间不能代替物理采样时刻；未解决则只给接收窗口工程结果，真实Profile定位BLOCKED |
| B5 | N0/sham→C1/G1小阶梯→16rank自动2epoch；G2/N1/F1各自先获批目标/恢复再独立试验；C2另列多目标边界 | CPU测试不证明降频/通信压力/fail-stop适用性；同标签多组第一阶段需真实组成员，不能人造标签冒充MoE |

B2/B4存在实现空缺时，提交单独最小工程任务审核；不得边实验边悄改桥接/计时。
先封存未来代码/构建SHA，涉及改代码须重新审批且重新做受影响冒烟。
目前没有获准的 detector→live Profile 自动接线或完整 fail-stop运行验收；
B5前必须有该接线独立实现/审核和时钟证据，TASK10不实现它们。
F1在worker退出后不能要求缺失rank补Profile/reset：采集存活控制证据、
标 INCOMPLETE/BLOCKED，终止本作业/封存结果；下一轮新run，不能硬造闭环成功。
全局控制器/Redis不作为F1目标，不验证单点控制面HA。
真正MoE/论文四并行配置、全强度曲线/250迭代与大次数基准仍属M7/M8；
当前DDP不能替代它们。超出支持的stream/Graph/init/Split hash显式UNSUPPORTED。

## 6. 评价与时延（预登记的 ADAPTATION；候选层是 EXTENSION）

每场景、目标集合、强度控制量/实测效果、模式、拓扑分别报告分子/分母，
不把两episode或相关Group成员当独立重复。计划数、启动数、注入成功数、
数据完整数、超时/拒判/恢复失败数均公开；条件指标不替代全部成功注入分母。

**Detector**：以运行前固定的episode生效区间 `[onset,off)` 匹配首次合格
`detection_trigger`（不是低概率cp或qualified候选），同episode后续触发计重复。
TP_D=区间内成功注入且至少触发一次的episode数，FN_D=成功注入数−TP_D；
FP_D=无注入/恢复区间未匹配的触发数。precision=TP_D/(TP_D+FP_D)，
recall=TP_D/(TP_D+FN_D)，分母0写UNDEFINED；单列重复次数/正常暴露小时误报率。
边界时钟不确定触发标MATCH_AMBIGUOUS并给上下界，不偷偷分配TP。
<20%和瞬时场景也留在all-injection报告，另列预登记持久/强度分层。
未触发/未观察完成的时延记right_censored或NOT_MEASURED，不能填0。
性能Detector分母只含已预登记的性能场景；F1走独立fail-stop指标，
不能把进程退出后不再有完成迭代的事件混入性能检测召回或补造迭代。

**Profile**：请求数、accepted数、逐rank实际applied比例、完整窗口数/请求数、
独立scope样本数、Group成员条数、drop/lock/checksum/error计数、
drain/reset成功率、拒判/不支持原因。原始CUDA duration分布与host stop等待
分开；必要的手动仪器开销作为机制负载记录，不混进Monitor无额外Event口径。
缺rank、坏duration、loss、旧epoch、未完成Group、窗口不明直接INCOMPLETE；不补零。
NO_CANDIDATE和INCOMPLETE/AMBIGUOUS_SPEC分别统计。

**Localization**：online输出原有 provisional候选集合 C，对独立root集合 R
计算TP_L=|C∩R|、FP_L=|C−R|、FN_L=|R−C|、集合完全匹配 `C=R`；ties全保留。
报告micro分子/分母、逐trial指标、拒判率；拒判有R时为无命中/FN，不删出all-injection。
forced完整窗口的conditional指标明确独立列；无自动触发时自动链路计未命中。
normal R=[]时空集合匹配可报告，但precision分母0仍UNDEFINED。
机制证据另报目标Event mean/其他rank mean、最小rank与真值吻合比例、
max-group/min-rank/CV/20%每道筛选与全部分布，不选“好看”的组。
因现有F-PROVISIONAL，最终diagnosis precision/recall及最终E2E为NOT_IMPLEMENTED；
只可报告automatic detection→valid Profile→正确provisional candidate的链路召回，
不得改名为论文最终故障识别率。共享链路root无法定义时依第2节NOT_APPLICABLE。

**Fail-stop**：单独记录FLASH原 `failstop_ranks` 集合 H，以及根集合 R、
独立 observed_stalled集合 S、launcher连带终止集合。根TP/FP/FN按H与R计算，
S覆盖率单列；被连带阻塞的健康rank不是根TP。正常长计算/CPU迟到误报单列。
新鲜度窗口例如2T的T来源/更新/最小界与运行实现SHA必须预登记；
论文未定参数不得现场猜值。OS退出/supervisor日志只供真值/保护，不能替换规则。

**时延**：每条时间保存clock_id/unit/host及原始值；跨主机单调时钟禁止直接相减。
同一全局控制器单调域记录以下接收/决策边界，真实物理域另以经验证映射报告：

| 边界 | 定义 |
|---|---|
| t_truth | 私有evaluator的实际注入生效时间/区间，映射后仅事后评估；不是下发请求时间 |
| t_detect | 首次合格detection_trigger完成；iteration编号同步记录 |
| t_request / t_applied | Profile命令封存 / 全部rank新scope应用证据收到 |
| t_window_start / t_window_end | 全rank生效后固定W采样窗口，物理scope归属独立验证 |
| t_drained / t_result / t_reset | 完整数据及drain证据收到 / 分析结果封存 / 全rank新Monitor证据收到 |

报告检测=t_detect−t_truth；dispatch=t_request−t_detect；应用=t_applied−t_request；
窗口准备=t_window_start−t_applied；采集=t_window_end−t_window_start（不得短于W）；
汇总=t_drained−t_window_end；定位计算=t_result−t_drained；reset=t_reset−t_result；
provisional端到端=t_result−t_truth，完整cycle=t_reset−t_truth。
forced从t_request计Profile/定位耗时，检测及automatic E2E写NOT_APPLICABLE。
时钟误差映射给区间；无可靠映射时检测/端到端秒数NOT_MEASURED，仍报告本机阶段
和可证明的iteration距离。rank0完成上报/ACK/outbox传输滞后单列，不能扣除后
称用户可见时延。每trial原值，3重复仅描述性median/range；样本够时给p95并标n。
不能强称论文1–2检测/2–3总迭代达成，不能把20s改成1迭代。

## 7. 已有 CPU 证据复用与本轮验收

**ADAPTATION**：基点的tasks05/07/08/09结果、来源ledger和保存命令已提供：
固定C工程身份/历史后验对照、批准detector 13测试/历史回放、G04 20测试/
65原fixture、outbox33测试与94回归、ABI2 bridge35新与127原回归。
TASK10不重跑这些CPU单元/完整M5native矩阵/G04敏感性矩阵，
不访问此前失败系统。本项目已保存的FAIL/NOT_CAPTURED/915缓存清单缺口/
隐私与权利OPEN保持原记录，文档引用不补成新PASS。
M6-B仅在新增接线/接口修改后跑受影响的定向CPU回归；上述B门真实路径不能豁免。

未来每run最少归档：manifest/封存SHA、真实argv/cwd/版本/设备/互联、训练日志、
原Probe采集及durable/ACK顺序、各控制事件与fence/epoch、全部predictions、
独立私有truth、独立evaluation、退出码/timeout与恢复/本次资源清理。
公开文件脱敏，不发布凭证/私有设备标识/真值目录；原日志保留私有SHA关联。
本轮只验文档及2070个基点文件保护，实测本地机器与完整命令/exit/log见RESULT.md。
下一唯一任务：独立审核TASK10精确HEAD及本协议；即便通过，也须另行明确
批准M6-B最小实现/执行、场景/目标资源/预算和恢复动作。完成本轮即停。
