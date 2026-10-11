# TASK11 — M6B-READY 最终准入审计

**结论：M6B-READY 对真实两台 H800 自动候选闭环仍为 BLOCKED。**
已有模块级工程证据可以复用；缺的是具体接线和真实路径验收。
不需要再次运行完整 CPU 实验矩阵来证明相同结论。
TASK11 是静态审计交付，不能记为 M6-B、G09 或最终故障识别 PASS。

唯一来源提交 `b517c5a922d52895e274c3758b5b7c2c409d91ca`。
本文所有源码行号均指该 HEAD；完整 tree、文件 SHA、函数定位在
[SOURCE_LEDGER.json](SOURCE_LEDGER.json)。没有采用移动分支、旧失败系统或 GreyHound 源码。
任务授权及本轮检查见 [任务书](../../../tasks/06b_ready_task11_final_admission_audit.md)
和 [RESULT.md](RESULT.md)。本轮只在本地 macOS 执行文档/静态检查。

## 1. 准入分层与已验证能力

下列分层为 **ADAPTATION**（PLAN M3/M6/M7/M8、TASK10 §5–6）。
它用于明确阻塞范围，不把尚无最终告警混同为所有手动机制测试都不能规划。

| 层级 | 当前准入结论 | 必须补齐 |
|---|---|---|
| L0：真实手动 Profile/机制小阶梯 | BLOCKED，待独立实施与资源授权 | B02–B08 的相应子项；不需要以自动触发作为手动测试前置，但只能报 forced 指标 |
| L1：自动 Detector→完整 Profile→正确 provisional candidate→安全 reset | BLOCKED | B01–B08；两真实节点、两个完整 epoch、N0 对照；按 C_valid 评价 |
| L2：受控进程 fail-stop | BLOCKED，独立于性能 Detector | B02/B05–B09 及 F1 目标/退出/恢复批准；不要求已退出 rank 伪造 Profile/reset |
| L3：最终故障告警、论文最终 E2E、MoE/正式图表 | NOT_IMPLEMENTED / NOT_RUN | B10；最终判决另需科学授权，真实训练与正式实验另需 M7/M8 授权 |

以下是**继承的已验证能力**，来源为本 HEAD 保存的最终结果、命令与源码哈希。
`INHERITED_EVIDENCE.json` 区分“来源字节相同”和“后来已批准改变”，
没有声称本轮重新运行原命令或读取全部服务器私有原始日志。

| ID | 已有能力 / 边界 | 历史验收与精确来源 |
|---|---|---|
| E01 | 批准 Detector 显式入口：固定 Rbeast 参数、原30迭代窗口、cpPr≥0.8、当前原始 `t-j+1>20`、严格 A>0.2；保留资格与触发分层 | task05 新13 CPU测试及保存 C 历史回放；`change_detection.detect(..., approved_rules=True)`；`g2-approved-detector/RESULT.md/validation.json/APPROVAL.json` |
| E02 | 固定 C 二进制身份须显式选择；错误身份拒绝；批准规则不自动采纳 C 或安装环境 | `RbeastAdapter(candidate_c_python=...)`；SHA常量 `1f08fbc9…6faeb`；task03 来源和 task05 只读历史核验。目标机当前加载身份 NOT_PROBED |
| E03 | G04 批准入口：最大组→最小rank，等权、20% inclusive、双CV/数值门禁、每实例≥2去重scope、只给候选 | task07 新20 CPU测试、原65fixtures、97历史回放；`analyze_approved_g04`；`g3-g04-implementation/APPROVAL.json/validation.json` |
| E04 | Reporter 冻结已完成记录，精确 ACK；SQLite outbox 先入库再发送，未知结果 read→exact retry；显式消费 cursor commit | task08 新33 CPU测试+94原回归；`iteration_reporter`、`iteration_outbox`、`m6_iteration`；`g20-reporter/RESULT.md/validation.json`。不是物理GPU完成/断电/真实跨机恢复证明 |
| E05 | 真实 Redis transport 已实现并在 node-0 验收过；GET/EVAL CAS、有限socket期限、丢响应/重启/失文档拒绝 | M6-A 6个真实 Redis用例、32控制CPU用例；Redis8.10.2/client8.1.0；`docs/m6/RESULTS.md/validation.json`。同机 Unix socket、模拟scope/时钟，不是当前桥接两机网络验收 |
| E06 | ABI2 Python接线已有明确 Reader 接口、fresh per-rank scope proof、epoch/generation fence、Group lineage、干净drain、新Monitor记录；桥接调用批准 G04 | task09 bridge05新35 CPU测试+127原回归；`m6_abi2_bridge`；`task09-abi2-cpu/RESULT.md/validation.json/review-logs.json`。字典 Reader mock，没有真实 ctypes/GPU/Redis组合执行 |
| E07 | 真实 CUDA Event/ABI2 原底座有 M3有限负载记录；含CPU及GPU前置迟到、Group共享观察和恢复范围 | `docs/m3/RESULTS.md/VALIDATION.md`；`native/probe.cpp:Timer`、`native/ring.*`、`Reader`。只能继承原范围；当前桥接二进制/负载/时钟不能因此自动 PASS |
| E08 | G09 已有场景、私有真值、安全预算、准入门、分层评价协议 | 精确基点的 `task10-g09-protocol/G09_PROTOCOL.md`（已含 C_raw/C_valid修正）及空白清单；协议非 launcher，未授权运行 |

E01/E03 的 G01/G02/G13/G04 为 **ACCEPTED_ASSUMPTION**：采用独立 APPROVAL.json
而非早期 null/OPEN 历史账本。G09/G20 的物理适用性仍 OPEN；没有重新请求已经批准的参数。
E05 的 `m6_iteration.py` 原 M6-A执行SHA已被后续cursor任务改变，审计明示该差异，
当前文件有 task09最终回归来源；不能把旧 Redis测试当作改变后整个组合的验证。

## 2. 当前端到端路径：已接与断点

**PAPER**：SPEC S1–S7，论文 §3.2.2/3.2.3/3.2.4、§3.3 pp25–35。
**ADAPTATION**：下表来自精确源码，而不是接口名相似就推定可运行。

| 环节 | 精确源码事实 | 判定 |
|---|---|---|
| 框架完成迭代→Reporter | `tests/m5_ddp.py:116–117` 建 LocalHistory；回调有CUDA等待；不是 Redis/outbox 发布 | 有框架示例，无live接线 |
| 完成记录→M6窗口 | `m6_protocol.py:35–42` 只接受 `after_optimizer_cuda_complete` 或CPU模拟边界；DDP的长描述字符串不匹配 | 不能原样串接；须核验真实边界后建立明确字段映射 |
| confirmed rank0→Detector | `detect:257` 的批准路径可调用；`DurableIterationConsumer.poll/commit` 有交付语义；无在线 dispatcher | 缺自动消费、提交、去重与触发持久记录 |
| Detector→Profile | `m6_controller.py:14,71–93` 的 start 只批准 MANUAL_TEST_TRIGGER；ABI2 Global继承start | detection_trigger 无自动消费者；不能把它改名manual就算自动闭环 |
| Redis→Local→Reader.request | RedisStore已存在；Abi2ProbeAdapter.request/poll调用已声明 Reader | Python桥接已有；真实实例发现/所有权/库加载/启动轮询/退出入口缺失 |
| requested→actual applied | native control/thread_local；adapter要求写请求后基线之后的新scope记录+header一致 | 不得以请求ACK/header代替每rank单线程应用/恢复证据 |
| 样本→窗口 | bridge.samples记 `collected_at_seconds=self.now`；Local按接收时间过滤；Global窗口仍标 single_host_cpu_simulation | 未证明物理scope属于全rank生效后的W；跨机绝对单调时间不能直接比较 |
| ABI2→Localization | bridge._analyze调用 analyze_approved_g04；默认 Global调用原 analyze | 选择正确入口是必要配置；默认CPU模拟入口不等于批准的live路径 |
| result→Monitor→下轮 | 每rank新state0 proof才关闭；失败要求显式reset，reset超时BLOCKED | 逻辑已有，真实资源回收/丢连接/worker退出后安全退出未验证 |

`timestamp_ns` 是 Probe 构造元数据事件时的host单调时间；它不是GPU Event完成时刻，
`duration_us` 也不能自动拼成对应的host物理区间。CUDA Event耗时必须保留原来源。
仅按header/接收时刻判断窗口，即使输出了数值也不能通过 B04。

## 3. 硬性阻塞与最小补线清单

所有 B 项的工程准入/建议为 **ADAPTATION**，涉及物理机制则保持对应 GAPS OPEN。
每项必须独立给出已审核的实现SHA、机器/命令/退出/原日志/恢复结果；
本轮只审计，不实施以下改动。清单机器可读版本为 [CHECKLIST.json](CHECKLIST.json)。

| ID / 阻塞层 | 当前缺口与出处 | 最小交付与关闭证据 |
|---|---|---|
| B01 / L1 | 缺 approved Detector→Profile dispatcher；manual-only start；默认 adapter不选C | confirmed rank0有序消费→显式C身份/approved_rules→保存完整输入/决策→版本化自动request；run/global generation/consumer cursor/decision digest/request_id对应；重启/丢ACK/重复触发/active或reset中触发不能产生额外epoch或跳过输入。固定去重/忙时pending规则须单列批准，不能偷换G02或吞掉触发；新接线只跑受影响定向测试，不重跑native矩阵 |
| B02 / L0–L2 | ABI2/Redis/Local/Global尚无真实组合入口；调用者负责Readers，mock source标记不能证明真实执行 | 本次run限定的发现/绑定，真实Reader库/Probe构建SHA和ABI280 bytes，rank→pid+created_ns→scope thread→GPU登记；显式选Abi2Global/Local+RedisStore，100–500ms有界poll；CPU模拟与真实source分开可验证，不能只改字符串称PASS。禁止另启一个抢同ring的reader CLI |
| B03 / L0–L1 | 当前框架Reporter仅LocalHistory；boundary不匹配；begin/end中含审计collectives；跨进程outbox/消费未接 | 经核验的训练边界→strict_reporter/DurableIterationOutbox→IterationPublisher/Reader；失败body abort、完成未知ACK保留；源rank0和全部组成员登记。记录哪些审计工作含在迭代，保持开/关工作量一致。当前steps上限100不足TASK10的150迭代单段计划，须独立小launcher/预算，不能暗改旧测试限制 |
| B04 / L0–L1 | 发布 confirmed_at是publisher clock；采集/applied是local receive；window是global clock；raw不是完整物理GPU区间 | 给每值clock_id/host/unit，建立本地有效边界及跨主机映射/误差界；scope是否全在W、跨边界/in-flight/迟到样本如何拒判须先定契约。验证offset、漂移、延迟、批量积压和边界scope；证明全rank应用后有效W≥max(2.2T_ms/1000,20)s。映射不可靠保留秒数NOT_MEASURED；物理窗口不成立则真实定位BLOCKED，不以接收窗口通过 |
| B05 / L0–L2 | bridge.poll先内存暂存后ACK；原Reader CLI fsync→ACK不由桥接调用；scope计时/记录丢失会失去原raw | 选择并批准一种最小方案：单Reader拥有durable raw journal后ACK并可重放/去重，或在ACK前具备可审计崩溃epoch作废/fencing/拒续分析路径。后者不宣称恢复丢失raw；有效完成trial仍需全部raw归档和SHA。outbox只保iteration，不可代替NCCL raw；禁同ring双reader |
| B06 / L0–L2 | 请求/应用/reset逻辑通过mock；native是thread_local且header无command generation；计时资源退出未验证 | 实际单scope线程受支持负载的两轮0→1→0、fresh Monitor、Group完全结束/Event清理、loss counters/drain；native写请求前后重新核验所有者fence。断联/旧owner/半reset/worker退出的有限保护及恢复；已退出rank不补零、不冒称all-rank reset。无法恢复终止本次作业、新run，禁止自动续训 |
| B07 / L0–L2 | public/private分份协议不等于真实访问隔离；manifest/标签仍由caller声明 | 独立身份/容器或等效隔离，在线读取/list真值目录及injector env负向检查失败；匿名run_id；封存prediction再由evaluator关联真值。框架导出真实rank/comm/parallel组，禁止标签携带注入目标；单DP组可小冒烟，但Stage1/MoE须真实多个同标签组 |
| B08 / L0–L2 | 本次两机资源/运行栈/预算未盘点；8MiB整doc、10000events/adapter列表、100epochs、4096单poll上限会作用于真实负载 | B0只读盘点、已加载库/固定C SHA/授权、可用GPU/互联/其它作业与supervisor；按实际collective数、W、rank数预估原raw/Redis文档容量和持续drain速率，含active→epochs复制/两轮累积；容量不足BLOCKED或另审归档接线，不提高上限掩盖问题。每trial600s及阶段预算/恢复余量可行后再申请GPU范围 |
| B09 / L2 | 未实现完整FLASH failstop_ranks新鲜度监视/上报；性能Detector无法从退出后的完成迭代判停机 | 独立最小runtime：Probe实际新NCCL调用→local freshness→global failstop_ranks；T来源、例如2T的更新时间/边界须预登记并批准。OS/watchdog只给evaluator/安全，不代替算法；保root/secondary/launcher集合及长计算负对照。F1停止当前PG/本作业，不能强行走性能闭环 |
| B10 / L3 | F-PROVISIONAL使所有final_fault_ranks=[]/final_alert=false；真实MoE/论文配置/最终分类未实现 | 保持当前值；最终诊断规则只有另获科学授权才实施。M7实际框架/MoE/API/标签，M8统计口径/重复/负对照另行批准；不以provisional结果或DDP代替论文最终识别率 |

B01–B08 关闭只能申请 L1 最小验收，不证明 G09 已适用于降频/网络竞争。
B09 不阻塞 L0/L1 的非fail-stop小阶梯；B10 不阻塞诚实报告 forced/自动provisional指标。
B08 的环境身份/可用性和容量须本次实测，不用历史缓存缺口推断当前数据完整。

## 4. 可接受偏差与仍待决定的边界

“可接受”仅表示已有批准或当前限定实验可明确声明的范围，不扩大发布/执行许可。
没有为推进L1新批准科学参数，也没有关闭原问题的完整适用范围。

| ID | 性质 / 依据 | 可接受条件与不允许的结论 |
|---|---|---|
| A01 | ADAPTATION，task05独立APPROVAL | G01-a固定BEAST窗口重拟合、G02当前candidate age、G13严格A；不是经典run-length BOCD、物理连续21轮或1–2迭代最终告警 |
| A02 | PAPER+ADAPTATION，task07独立APPROVAL | max-group/min-rank、等权/Q-TWO/20%inclusive/歧义拒判/F-PROVISIONAL；仅候选，不能校准成概率或以双标签一致证明故障 |
| A03 | ADAPTATION，M2/M3/G07 | robust mutex、ABI2/发布序号/ACK/严格loss拒判、非Group辅助支持；需要量化本次开销，不引用论文纳秒开销为项目结果 |
| A04 | PAPER+ADAPTATION，SPEC S4/M3 | Event stop sync，单设备单stream阻塞comm、每rank显式单scope线程；Graph、多stream、Split/非阻塞/init未知拒绝，不能让真实DDP超范围后悄悄过滤 |
| A05 | ADAPTATION，TASK10/PLAN | H800小负载功能/机制阶梯，与H200/原13.3B MoE差异明示；真实DDP并非原模型/混合并行复现 |
| A06 | PAPER，SPEC S8/G15 | count元素/dtype保raw、Group共享scope；按绝对时延基线，不把成员记录当独立样本。带宽/分桶/归一化只作后续EXTENSION |
| A07 | ADAPTATION，TASK09/M6-A | 单global、standalone Redis、无HA/磁盘ACK；丢store或worker退出可BLOCKED后精确结束作业/新run。崩溃epoch作废策略须B05实装后才可用 |
| A08 | ADAPTATION+EXTENSION，TASK10 §6 | forced/automatic、C_raw诊断/C_valid正式候选指标分列；拒判非空真值计FN，未触发保留，无最终指标；历史正常候选/冲突不删除 |

必须保留：既有M5/P1 A/B FAIL、三份NOT_CAPTURED、915-cache preinstall SHA缺口、
历史隐私/权利 OPEN/DEFERRED。TASK11不读取旧失败系统、不补采/重写这些证据。
这些历史限制不是自动扩大系统改造或重复矩阵的理由；当前目标机身份与新增真实路径
则必须有本次证据，不能用“历史已通过”绕过。

## 5. 待授权 GPU 任务（全部 NOT_RUN）

此表为 **ADAPTATION**（TASK10 B0–B5/§4）；C1/G1/N1辅助故障模型为 **EXTENSION**。
沿用原协议上限，不填虚构GPU UUID/PID、MHz、网卡或批准人；当前 execution_authorized=false。
每次批准仍需精确资源、当前代码SHA、时长、超时保护和恢复动作。

| ID | 最小下一真实任务 / 前置门 | 验收与停止方式 |
|---|---|---|
| U00 | B0 两机只读资源/版本/加载库/固定C身份/互联盘点 | 只读不使用GPU；本轮NOT_RUN。缺资源/依赖记BLOCKED，不安装或迁移 |
| U01 | B1 当前源码/构建的Monitor与手动Profile数值/ABI冒烟：单机2rank→两机各1rank→16rank | 每一扩展另给资源预算；先小负载/无注入，只测新增路径；失败立即停，不重跑全M1/M3矩阵 |
| U02 | B2–B4 真实Reader/Redis/框架/时钟/安全两轮闭环无注入 | 新集成入口已独立审查；20s下限、fresh作用域、全rankdrain/reset、真实raw与预测封存；断联后精确结束/恢复，不能由mock替代 |
| U03 | B5 N0/sham/长计算负对照，然后C1/G1分别在两节点/rank0与非rank0小阶梯，最后16rank自动两epoch | 自动仅在B01–B08关闭后；forced独立标记。不删正常候选/拒判；每episode≤180s、每trial≤600s，30/30/60/30单段迭代及两轮预算事先可行；注入目标真值私有 |
| U04 | G2 一个独占H800 UUID的SM时钟限制 | 另批目标UUID/原policy/可用MHz/≤180s/独立supervisor/≤30s原policy恢复与回读；不能读回原policy直接BLOCKED |
| U05 | N1 本项目一对背景NCCL rank的通信压力 | 另批GPU/NIC端口/PID/PG/流量与显存预算；可限速与核验才执行；≤180s后wait本作业；共享链路无root集合时rank指标NOT_APPLICABLE |
| U06 | F1 指定worker自退出/批准信号 | B09关闭且资源/信号/最大时长/精确PID启动标识/本PG结束预登记；root与secondary分开，已退出rank不伪造reset，下一trial新run |

单批准批次上限仍12trial/2h；每场景/目标/模式3个独立trial，两个episode非独立重复。
C2整节点迟到、多GPU降频、多故障、OOM、hang、强制NCCL timeout、网卡干扰/
机器重启/DeepEP/正式MoE和图表均不自动纳入首批。
恢复失败标 RECOVERY_FAILED/BLOCKED 并停止整批，不广泛清理、不GPU reset。

## 6. 唯一下一动作与最小工程任务建议

**下一唯一动作：独立审核 TASK11 精确提交和上述准入清单。**
用户本轮授权审计，未授权新增接线、GPU运行、安装、推送或最终科学判决。

审核通过后建议单独授权 **TASK12：confirmed rank0→approved Detector→版本化自动Profile请求**
（B01），保持手动路径和所有科学参数；先给允许文件/API、忙时触发处理、
消费/decision/request原子性、重启/幂等/拒判的定向验收与退出方式。
不使用假GPU样本宣称L1。后续B02/B03真实集成入口、B04物理窗口、B05/B06
raw/恢复、B07/B08隔离/资源依次拆成最小任务，由各自审核结果决定执行顺序。
这是建议队列，不是连续授权；任何接线改动只重验受影响定向CPU用例和本次真实冒烟。

## 7. 来源说明

**PAPER**：本文仅沿用本HEAD的SPEC S1–S9/页码和批准审计提要，
没有声称本轮重新渲染/视觉审核PDF。**ADAPTATION**：全部准入判断和最小接线要求
由本HEAD的代码/任务/结果追溯。**EXTENSION**：只沿用TASK10辅助故障和候选层评价。

**UPSTREAM**（2026-10-11在线核对，官方接口文档；无源码复用）：
CUDA Event耗时为ms、stop同步及跨stream干扰语义，见
[CUDA12.8 Event API](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-runtime-api/group__CUDART__EVENT.html)；
Group提交/外层结束语义见
[NCCL2.27.3 Group](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/usage/groups.html)。
Redis EVAL原子执行是服务器脚本性质，见
[Redis Lua](https://redis.io/docs/latest/develop/programmability/eval-intro/)；
单调时钟参考点未定义、只宜同有效域作差，见
[Python3.12 time](https://docs.python.org/3.12/library/time.html#time.monotonic)。
这些官方语义不能代替目标机加载版本或两机时间域核验；本轮目标机NOT_PROBED。
