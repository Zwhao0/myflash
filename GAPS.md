# 复现分歧登记簿

状态默认为 OPEN。每项确认后追加“证据、决定、批准者、配置/代码位置、测试”，不要覆盖原始问题。未阻塞的模块可继续；禁止为了推进整套系统而猜测会改变结论的实现。

| ID | 来源与问题 | 实施前需要确认 / 最小验证 |
|---|---|---|
| G01 | §3.2.2称BOCD并使用Rbeast；上游slow_detection.py实际调用rb.beast | 根据论文与 GreyHound 参考调用确定本仓库 Rbeast API、包版本、模型参数、变点输出字段/索引；论文不明处先记假设并征求审核，不能凭 BOCD 名称改写为另一种后验递推 |
| G02 | §3.4.3写持续超过20迭代；§3.4.5写检测1–2迭代 | 论文未给出统一解释；原作者的 FLASH 代码/日志如将来获得可作旁证，但不作为本项目依赖。先登记两种解释，由用户批准复现假设并将测试阶段延迟分开测量 |
| G03 | §3.2.3剖析max(2.2T,20s)；§3.4.5以约1迭代剖析核算总时延 | 明确ms到s转换；分别记录检测、下发、有效采样、汇总、分析、总时延；不能调整公式去拟合2–3迭代 |
| G04 | §3.2.3/3.3.2使用组内最大平均时延；式3-1使用通信组平均时延 | 运行时筛选与绘图统计分别保留；确认rank跨communicator聚合是否按样本数加权；默认20%离群阈值的参照量待定 |
| G05 | §3.2.3以Group为边界；§3.3.1共用Group duration | 非Group、嵌套、多stream、跨comm及异步初始化逐项测试；混合Group的公共耗时必须标注粒度，不能假装是每条collective的独立时间 |
| G06 | §3.3.1简化id_hash；Greyhound的ncclCommSplit使用未初始化buf并警告不支持获取unique ID | 审计工作负载实际走的初始化API。InitRank/Config可利用输入unique ID；Split等需独立设计并验证全局一致性；没支持就显式报unsupported，不制造随机hash |
| G07 | §3.3.1允许无锁读取和少量丢失；但无完整ABI/发布协议 | 核对布局、对齐、生命周期、多线程写入、读写发布和清空竞态；测试撕裂记录、溢出、重复、reader重启。必要的安全修正单列ADAPTATION |
| G08 | §3.2.4无NCCL调用即fail-stop | 记录原始规则输出；分辨无新调用、进程退出、GPU/通信挂起和连带阻塞。不能用测试看门狗或独立心跳替代后声称原算法通过 |
| G09 | §3.2.3慢rank短时延是关键依据；§3.4.4同时评估通信拥塞 | 首先分别测试CPU迟到、GPU前置计算迟到、GPU降频和真实背景通信。现象不成立时先核对测量，再记录适用边界，不能自动反转min/max规则 |
| G10 | §3.3.3框架上报两类信息；§3.4.2又强调无需专用适配 | 以实际接口清单统计改动；复现不追求强行“少于10行”或零hook。纯API元数据不能凭空还原训练迭代 |
| G11 | §3.4.1环境与模型表不足以唯一确定训练配置 | 记录原论文表中给出的配置与缺失信息；无法获得精确原始启动脚本时设计独立、明确标记的功能复现配置。原作者额外材料可选，不阻塞 M0–M3 |
| G12 | §3.4.4称限制一个节点GPU频率；图3-10称一个GPU降频 | 区分单rank、单GPU、整机多GPU退化。记录实际注入集合，不把节点故障计为单rank故障 |
| G13 | §3.4.4退化强度5%–85%；检测默认阈值20% | 明确强度是GPU降频比例、计算变慢、迭代时长增长还是吞吐损失；分别报告自动触发召回与强制剖析条件下定位效果 |
| G14 | §3.2.1提Pre-check；主状态机只有Monitor/Profile | 论文提及启动验证但状态机只有0/1；先将Pre-check列为缺失细节，不照搬Greyhound整套precheck/validation，也不把未做的precheck算已复现 |
| G15 | §3.5承认未上报通信数据量并建议带宽判断 | 初版按时延基线；额外保留count/dtype仅作审计。带宽/分桶属于EXTENSION；它们也需要独立论证，不能当成必然正确的修复 |
| G16 | 论文0/1状态未详细说明分布式采集轮次和完整性 | run_id/profile_epoch/节点ACK/超时是拟议适配；禁止混用旧数据、漏rank补零；不支持的窗口返回证据不足 |

## 已选定与未选定

已选定的工作范围：只做 FLASH；**全新仓库从零开发，不访问旧失败实现**；先进行新项目建档与原生底座验证，再做微基准、离线算法、自动闭环，最后做论文实验。
尚未选定：检测器最终参数、20%计算公式、持久性时长、聚合加权规则、复杂Group/初始化支持范围、具体H800训练配置。

## 追加决定模板

```text
ID:
状态: OPEN / RESOLVED / ACCEPTED_ASSUMPTION / BLOCKED
原始证据: 论文节/页，或仓库commit:path:line，或实验run_id
决定:
性质: PAPER / UPSTREAM / ADAPTATION / EXTENSION
为何不改变/是否改变论文机制:
批准:
实现位置:
验证命令与证据:
```

## M0 新增核对（2026-10-10，均保持 OPEN）

原 G01–G16 未关闭、未改阈值、未批准任何科学假设。以下只补充实际发现的证据与后续验证条件。

| ID | 本轮证据与差异 | 后续需要确认 / 首次阶段 |
|---|---|---|
| G17 | PAPER §3.2.3 p.30 正文称快 rank 266ms、慢 rank 3ms；同页图3-4 的时间线慢 rank 标 120ms，快 rank 266ms；完整页面已视觉核对 | 仅作为图文数值不一致登记。不得选某个数值拟合实验或 fixture；保留 min-rank 机制，M3 独立实测，不擅自解决 |
| G18 | UPSTREAM 工作包只给 GreyHound 搜索快照 SHA/入口摘要，没有提供 LICENSE/NOTICE 与完整源码；本轮未联网读取正文 | 精确 SHA 的许可证/文件头、函数与数据结构/行号待查看；任何源码复用前核验许可。没有代码复用，不称完成上游审计；M1a 文档/M2 前 |
| G19 | PAPER 表3-1 p.36 标 H200 140GB，p.37 正文 141GB 且称“单个专家参数量1.4B”，表3-3 为总13.3B/激活1.4B/128专家 | 不把激活参数直接等同单专家参数或显存预算；结合 G11 保留表与正文各自口径。实际 H800 显存 M1a，模型参数构造 M7 前确认 |
| G20 | PAPER §3.2.2 p.25 为每迭代结束回调写 iteration:time_ms；§3.3.3 p.35 描述 rank0 启动后台进程定期推送 | 需明确真实迭代计时边界、发布/同步/重复乱序语义，不将定期推送当迭代结束或 CUDA 完成；M5 前审核，关联 G10 |

开发路径事实（ADAPTATION，不是科学机制决定）：用户本轮明确在服务器开发；本地服务器说明给定 `test@<server-address>` 与 `<project>`。M0 只读 SSH 证实该路径不存在，随后新建独立仓库；第二台部署目标和软件/GPU 环境仍未知。连接凭证留本地且不版本化。

## M1 环境与实现边界补充（ADAPTATION）

G01–G20不关闭。M1实测为H800小合成负载、native NCCL2.27.3/PyTorch2.8，而非论文H200/Qwen MoE训练；Megatron/TE/native入口未就绪，G11/G19模型口径仍需核验。低资源CTA/NVLS配置仅功能基线，不用作论文性能比较。原地址现脱敏，备份仅服务器runs；无算法/阈值/科学机制变更。

## M2 工程决定（2026-10-10，ADAPTATION）
G06：阻塞InitRank/Config输入ncclUniqueId采用SHA256；Group中输出在成功外层GroupEnd后建本地映射；Split跨进程身份明确UNRESOLVED、hash为空，InitAll/Scalable/非阻塞初始化身份UNSUPPORTED。未实现复杂路径不制造一致ID；G06复杂范围仍OPEN。来源installed NCCL2.27.3 nccl.h与官方comms/group文档；位置native/probe.cpp，单机实际证据runs/m2f-20261010-lifecycle-01。
G07：选择ABI1、每进程ring、进程共享ROBUST mutex、10ms有限锁等待、可观测full/lock丢失、checksum、Reader排他、peek→持久化→ACK、重启去重；替代论文Python无锁读/重置。保持Monitor元数据机制，增加同步/持久化开销；不能引用论文纳秒开销作为实现结果。位置native/ring.*、flash/reader.py，CPU9项runs/m2-unit-20261010-ack。G07本支持范围由M2最终证据验收，跨ABI/任意破坏恢复仍不支持。
G21：项目runtime wheel缺完整开发头文件；M2不写kernel无需nvcc，现有g++13.3+M1 Triton3.4的CUDA12.8 crt+项目隔离CCCL12.8.90头文件可编译。用户续令解决本问题；没有系统安装或运行库替换。原失败与成功命令/退出码在runs/m2a-compile-20261010，CCCL发布SHA256和许可见docs/m2/SOURCES.md（收尾补齐）。本决定只涉及构建，不改变科学机制。

M2最终证据：G06支持范围验收PASS（InitRank/Config，Group中输出仅成功外层GroupEnd后映射）；Split仍UNRESOLVED、异步/InitAll/Scalable仍UNSUPPORTED，不关闭复杂初始化问题。G07采用已记载ROBUST锁/单调截止/完整发布/ACK，CPU11项、4线程mock及真实1/2/16rank/DDP均通过；不把差异协议称论文原实现，跨ABI/任意毒化恢复仍不支持。G21编译问题已由获准项目headers解决，无系统升级；对应SOURCE/RESULTS日志。追加生命周期观察：早期SSH结束后命名对象消失，原因未确认；当前入口在同一会话真实精确unlink并保存NDJSON，不保证跨最后登录会话的IPC存续。参见docs/m2与runs/m2-final-validation2-20261010。


## M3决定与证据（2026-10-10）
G05 / ADAPTATION / 已验证范围接受：非Group入口补充是M2实际PyTorch路径所需，外层GroupStart固定state/epoch，成功外层End后stop/sync。单stream单设备阻塞comm和嵌套共享范围通过；多stream成员显式UNSUPPORTED/null。科学Group公平聚合、复杂API/stream范围仍OPEN。依据官方NCCL2.27.3 Group与CUDA12.8 Event文档，位置native/probe.cpp，m3abc-local-01/m3d-roce-01/m3e-group-02与CPU错误mock。
G07 / ADAPTATION / ABI2与已验证恢复范围：Event280bytes、请求/应用word与逐scope状态；拒读ABI1，旧run结束后升级，不支持滚动升级。NDJSON摘要、连续序号、仅未ACK尾片截断、完整记录保留/重放；中部损坏或已ACK数据缺失拒绝。并发/锁/损失M2测试重跑，任意破坏/持锁死亡仍不猜测恢复。位置native/ring.*、flash/reader.py；suite20261010T053356468174Z。
G09 / PAPER机制假设 / 仅观察到适用边界，仍OPEN：单机及RoCE的CPU0/1、GPU0/1迟到，两轮各13次（每轮预先固定3warmup），有效分布每case/rank20点；目标rank的通信Event区间较短。GPU计算经compute→Event→comm wait→Probe start，目标自身前置工作在区间外；Event也可包含主机提交间隙、GPU排队/peer等待，不是纯内核本体。尚未分解组成，未检验降频/拥塞/其它消息/算法/真实MoE/并发故障，禁止推广或翻转min/max。原始值/标签未改，见docs/m3 samples/distributions与RESULTS。
G16 / ADAPTATION / 手动协议已验证：控制本地请求和逐事件实际epoch；Header应用值只是最近调用线程边界，不代表全rank ACK；验证器要求所有rank/epoch/计数/状态完整，缺rank/部分生效/timeout/异常不能完整Profile。Group预期Unsupported的测试PASS与complete_profile=false分开。自动分布式控制/20s公式/Redis/控制失联闭环仍未实现，留M6审核。
G04/G01/G02/G03/G06/G10–G15/G17–G20等科学/复杂范围不因M3功能通过自动关闭。Group共享字段聚合必须按scope解释，不将成员重复当独立测量；M4权重尚待批准。

## M4 G04 核对与待决定选项（2026-10-10，OPEN）
证据：第三章 §3.2.3 pp30–31、§3.3.2 p34、式3-1/3-2 pp41–42全文/公式页已复核。已有SPEC/ARCHITECTURE/M3设计也未提供唯一20%参照或跨comm权重。没有GreyHound算法作为FLASH规则旁证。
PAPER：确定部分仅max communicator mean选组、min rank mean排序、CV0.1、独立绘图scores。正式20%过滤未实现，候选标PROVISIONAL_CANDIDATE；分歧标AMBIGUOUS_SPEC，不输出最终故障rank。
待用户决定（本轮不请求猜测性批准）：
1. rank聚合：每本地communicator均值等权 / 每独立scope样本数加权 / 新证据定义。影响：不等样本量时可改变rank排序；fixture aggregation_weights_disagree明确给出rank1 vs rank0。
2. 20%分母/参照：相对组内rank均值 / 相对其它rank均值 / 相对次小时延 / 原作者规则。各自改变近阈值候选与正常误报；均未启用默认过滤。
3. std总体 / 样本：小组可跨越CV0.1；本轮population标ADAPTATION、sample并列敏感性，跨门槛不强判。
4. 式3-1 clique平均与全组参照的权重：本轮展示本地comm均值等权，明确统计口径，不替代max_avg_latency；未校准概率。
ADAPTATION G05/G16：同进程/线程/outer group_id scope内每本地comm最多一观测，保留成员数量和独立scope数量。跨comm共享scope相关性风险可见，不假装独立；缺失/无效/重复/身份不可靠直接拒绝，零均值不定义CV。
批准：用户M4明确允许确定性部分PASS、保留G04。实现flash/profile_input.py/localization.py；测试tests/m4_cases与docs/m4验证记录。科学问题未关闭。

## M5 evidence update (2026-10-10)

All four items remain OPEN. M5 implementation emits AMBIGUOUS_SPEC and no final
alert; implementation/CPU library compatibility PASS is separate from scientific
FLASH detection validity. User approved isolated dependency installation, not a
resolution of these scientific choices.

| ID | Evidence and implementation | Unresolved decision |
|---|---|---|
| G01 | PAPER pp26–27 calls Rbeast BOCD/run-length posterior. UPSTREAM approved wheel Rbeast0.1.25 rb.beast fits a full window via BEAST; trend.cp is a time coordinate with start/deltat, cpPr is localized occurrence probability, cpOccPr is pointwise. ADAPTATION uses cp-1 with start1/deltat1 and complete raw output. | Model priors/MCMC/segment margins, interpreting cpPr>=0.8, using all cp slots versus ncp_mode, compressed time after outlier deletion, population z-score and whole-window versus neighboring segments are explicit experimental assumptions. These have not been scientifically approved. No classical incremental BOCD equivalence. |
| G02 | PAPER §3.4.3 >20 iterations versus §3.4.5 1–2 iterations. Code reports observed original iterations and >20 fact, with required duration/decision=null. | No duration gate selected; replay delay measures candidate evidence only. Native segment minimum/margins are model support, not FLASH persistence. Cannot tune a gate to reproduce paper latency. |
| G13 | PAPER20% lacks denominator/direction, and injected degradation5–85% lacks equivalent iteration interpretation. Code reports (degraded-baseline)/baseline and (degraded-baseline)/degraded with separate threshold facts. | Neither duration-growth nor throughput-loss rule approved. Strict >0.2 experimental boundary recorded; >= sensitivity at exact equality unresolved. No automatic alert or injected GPU frequency inference. |
| G20 | PAPER p25 completed-iteration callback versus p35 periodic rank0 sender. ADAPTATION actual begin/end callback, UTC completion timestamp, monotonic duration; optional explicit CUDA completion wait. Local persistence is after timing and must only consume completed records. | General framework boundary/data loading/asynchronous CUDA completion and future transport exactly-once/ACK/restart remain to be agreed for M6. The DDP test boundary is declared and verified, not universal framework support. |

G01 compatibility/reproducibility evidence: approved Rbeast0.1.25+NumPy2.2.6
imports and fits on Python3.12.3. Same nonzero seed20261010 changes native posterior
arrays across repeated calls and isolated subprocesses; strict exact-output test
FAIL is retained. Field compatibility does not close stochastic reproducibility.
UPSTREAM same-version sdist SHA8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec:
abc_rand_pcg_local_avx512.c:avx512_pcg_set_seed references increment (different union
member from increment512); possible uninitialized-state cause, not confirmed as the
wheel execution cause. No binary patch/rebuild, library upgrade or alternate detector.


## M5-R evidence update (2026-10-10; G01/G02/G13/G20 remain OPEN)

UPSTREAM/ADAPTATION: fixed Rbeast0.1.25 wheel seeder now has causal local evidence:
AVX512 reads old word at byte32 instead of initialized increment512 at byte64.
Independent initialized-buffer intervention changes seeded states/random outputs;
all six predicted state vectors match; actual installed disassembly and ordinary
auto dispatch corroborate this. This confirms the initializer defect, not a
successful M5 repair or proof that every posterior discrepancy has this sole cause.
ROOT_CAUSE includes exact source/version/license, limits, proposed one-line fix,
isolated-build risks and independent strict/decision retest plan. No patch/build/
dependency install/runtime replacement occurred; proposal NOT_APPROVED/NOT_RUN.

G01 strict acceptance remains FAIL: unchanged m5_real_api and m5_replay each exit1
again in m5-r-strict-20261010-01.32×20 diagnostic cells in each independent batch
show auto/AVX512 failure under fresh/same processes, one/three chains and fixed
affinity/threads; SSE/AVX2 controls are exact within their cells, not adopted defaults.
Native model/probability/index assumptions remain unresolved. Full posterior bytes
differ at all35 fitted prefixes of every fixture in complete batch02.

EXTENSION: seven unchanged fixed fixtures×20 replays/batch, two batches. Batch02
captures all4900 decision fits and has stable qualified cp sets/presence/first
observations; low-probability raw cp drift occurs. Batch01 retains three invalid
cpOccPr validation exceptions causing candidate absence flips at sustained28/35
and growth19 prefix29. A diagnostic capture-order mistake lost their three raw
trees; inputs/parameters/exit1/decisions and NOT_CAPTURED status remain, and the whole
matrix was independently rerun without changed seed/model/input selection. The
specific invalid values/causal explanation are not guessed. No clipping, probability
tolerance, missing-data zero, discarded repeat or softened strict assertion.

G13 remains OPEN: nominal20% duration candidate first23/throughput none;21% first22/
none, consistently across20 complete repeats. Different prefixes of20% switch
duration membership as fixed slice means vary; no denominator selected. G02
persistence interpretation and G20 production callback/transport semantics unchanged.
No universal statistical bound or GPU fault accuracy inference from these fixtures;
recommend reviewed upstream remedy before accepting statistical-repeatability limits.
See docs/m5/repeatability/{ROOT_CAUSE,EXPERIMENTS,RESULTS}.md and complete data.
final_alert=false; no Redis/control/automatic Profile/M6.


## M5-P1 engineering evidence (2026-10-10; scientific gaps remain OPEN)
ADAPTATION/UPSTREAM: matched fixed-release B/C builds differ only in
ext_src/abc_rand_pcg_local_avx512.c:avx512_pcg_set_seed increment→increment512.
C passes independent integer recurrence/prior-memory/reuse/actual-auto gates,
unchanged API and independent full/short prefix assertions, and both complete
predeclared exact numerical/decision matrices. B retains prior-memory dependence,
prefix FAIL and cross-context actual-AVX512 posterior differences; its API PASS
is also retained. This supports the bounded one-line engineering remedy, not
universal causation, thread safety or an approved production runtime replacement.
See docs/m5/patch-p1/RESULTS.md, validation.json and complete indexed byte evidence.
All historical FAIL/NOT_CAPTURED remain. No probability relaxation/clipping,
zero-filling, seed/input selection, parser/ISA/default-model change or GPU experiment.
G01 as a whole, G02/G04/G09/G13/G20 stay OPEN. Both20% denominators remain
unapproved; cpPr≈0.8 behavior, production false positives, real GPU fault metrics
and paper1–2 iteration claim are untested. Wheel redistribution/license and PDF
rights questions remain unresolved. final_alert=false; scientific validity,
formal adoption and M6 NOT_APPROVED/OPEN. Only next task: independent Draft PR review.


## M5-S1 scientific audit (2026-10-10; no decisions approved)

G01/G02/G13: OPEN / REQUIRES_OWNER_DECISION. PAPER full pp26/27/40/43/44,
fixed UPSTREAM Rbeast0.1.25 sdist and ADAPTATION code at PR8 d2973f5 are
separated in docs/m5/science-s1. BEAST MCMC/window refit is not proven online
run-length BOCD; cpPr is local summed/capped occurrence output, distinct from
pointwise cpOccPr and unproven as P(run_length=0). All24 adapter parameters are
explicit engineering/model choices without exact paper authority. No replacement.
G02: inclusive span>20, exclusive elapsed>20, retained count>20, consecutive
qualified prefixes>20 and k1/k2 guards independently saved/tested, none enabled.
Sustained candidate22 versus span41/elapsed42 demonstrates differing semantics;
final alert iteration null. G13: A time growth/B reciprocal-mean throughput proxy
remain separate strict>0.2; growth20 A first23/B none, growth21 A22/B none;
recovery diverges30..32. No fixture-driven choice or GPU accuracy claim.
EXTENSION sensitivity audits all12600 saved C prefixes/280 replays,630 unique
rows; original832 files and formal1424 runtime files byte-preserved. Current
node-0 CPU validation02 all11 commands0; validation01 source-path/citation FAIL
retained, no relaxed arithmetic. Scientific validity/runtime adoption/M6 remain
NOT_APPROVED. G04/G09/G20 dependencies only; no localization/controller changes.
See G01_SEMANTICS/G02_TIMELINE/G13_THRESHOLD/DECISION_PROPOSAL/validation.json.
Only next task: independent owner/ChatGPT review of M5-S1 Draft PR.

## M6-A CPU control engineering (2026-10-10)
G16 / ADAPTATION: explicit schema1 run/epoch, atomic revision CAS, command/hash ACK,
global/local fencing, per-rank legal-scope proof, window/drain/data hashes and
bounded verified Monitor reset implemented separately in flash/m6_*.py. CPU-only
logical nodes and virtual clocks (EXTENSION) pass final32 tests and two epochs;
actual Redis integration BLOCKED (existing server/client absent, no installation).
This is bounded engineering evidence, not a final distributed/GPU protocol or HA
claim. Source PAPER SPEC S1/S2/S4; UPSTREAM official Redis EVAL/LTRIM docs;
prior request/application authority PR9 native/probe.cpp and docs/m3/DESIGN.md.
See docs/m6/{CONTROL_PROTOCOL,STATE_MACHINE,REDIS_SCHEMA,RESULTS,VALIDATION}.md.

G20 stays OPEN: original IterationRecord fields/boundaries retained, independent
500-item ordered transport, exact retained dedup/conflict/unknown-write receipts,
freshness/cursor/restart visibility added. Transport response is server-memory
confirmation only, not disk/training/GPU completion. CPU mock end is explicitly
simulated. Production callback/outbox ACK, real ABI fencing, persistence after
Redis loss and true process/Probe recovery remain unapproved. Control loss/partial
reset returns BLOCKED/TIMEOUT/ABORTED with operator conditions; no fake rank ACK,
zero-fill, previous-epoch replenishment or final scientific alert.

G01/G02/G04/G09/G13 remain OPEN and unchanged; M6-A imports no automatic Rbeast
trigger. Complete synthetic M4 inputs alone yield existing provisional/no-candidate/
ambiguous evidence; defaults/weights/min-rank/CV/20% filters untouched. Formal
runtime1424 non-cache files and all851 old source/fixtures/evidence preserved
(STATUS/GAPS append only). final_alert=false, final_fault_ranks=[]; M6 overall,
GPU/cross-machine loop, science validity and paper precision/recall NOT_RUN or
NOT_APPROVED. Next unique task is independent M6-A Draft PR technical review.

### M6-A actual Redis authorization supplement (2026-10-10)
The human user superseded the earlier dependency prohibition specifically for
real Redis installation. Private fixed Redis8.10.2/client8.1.0 installed without
formal .venv-m5/system service changes; CPU mock32 and actual Redis6 tests pass.
M6-A ENGINEERING PASS supersedes initial overall BLOCKED; all initial failure/
missing-dependency receipts remain. UPSTREAM versions/source/license/SHA in
docs/m6/dependency-lock.json, ADAPTATION isolated build/venv/socket/deadlines.
Actual server stop/restart changes server run_id and loses the old run document;
stale client operations/resume stay BLOCKED, a new run succeeds. This confirms
only exercised socket/standalone-memory behavior, not persistence, HA, physical
Probe recovery or cross-host training. G20 remains OPEN. No lost-reply or delay
network impairment was injected; those cases remain deterministic mock coverage.
G01/G02/G04/G09/G13 also remain OPEN. Original scientific algorithms/evidence
unchanged, final_alert=false/final_fault_ranks=[]; no M6 overall/science/GPU PASS.
Next unique task is independent M6-A Draft PR technical review.


## M6B-READY-G0-E (2026-10-11; no scientific choices)
ADAPTATION: unchanged IterationReader.read accepts after_iteration>last as
READ_CONFIRMED (last1/cursor2 or1000000, last501/500retained/cursor502). Strict
integer contract also fails for bool, floats, NaN/+Inf. Independent CPU test
exit1/9failures, pre-assert raw receipts retained; first one-node setup ERROR
retained separately, not defect evidence. No core fix; Gate4 OPEN/NOT_RUN.
PAPER500retention does not define this engineering cursor type rule.

M6B-READY goal remains BLOCKED: G1 candidate C finite historical engineering
PASS does not install S2 or point sys.executable at C; G2 full scientific
parameters/preprocessing/G01/G02/G13 and G3 weights/20%/CV/conflicts still require
owner choices. G20 Reporter completion/outbox/ACK, caller-clock confirmed_at,
physical restart and native ABI2 generation bridge remain OPEN. CPU simulated
applied/sample/drain evidence cannot close GPU/cross-node gates. G5/G09 scope,
truth isolation, metrics and safety plan require review; real M6-B NOT_RUN.
Historical installation original human message located (scope M6-A only, message
time/version/path not supplied); future reuse requires owner decision. Prior
FAIL/NOT_CAPTURED/normal provisional candidates/cross-label conflicts retained.
See docs/m6b-ready/g0-evidence. Only next task: independent ChatGPT review.


## M6B-READY-G0F cursor engineering scope (2026-10-11)
ADAPTATION / task01 human-authorized future cursor contract implemented in
flash/m6_iteration.py:IterationReader.read. Existing integer helper enforces
type(value) is int and >=0 before store read; valid future cursor rejected only
after existing integrity checks. None and legal boundaries preserve full window.
77 CPU tests exit0; unchanged original9 red tests now green, old9failures/exit1
raw and sanitized history byte preserved. Sources/argv/logs/environment and
formal1424/.so preservation: docs/m6b-ready/g0f-cursor. Cursor engineering PASS
only; original G01/G02/G04/G13/G09/G20 and other gate decisions remain OPEN/
NOT_APPROVED, M6B-READY overall BLOCKED. No Redis/service/install/GPU/native fit.
Historical privacy/PID/binary rights DEFERRED/OPEN by current task package, no
history rewriting or scientific acceptance implied. Stop for exact-head review.


## M6B-READY G1-S2-C / task02 (2026-10-11)
ADAPTATION: explicit human isolated-C CPU execution authorization satisfied;
Gate0F exact3ba7dad independently PASS per human report. Existing scientific
parameters/fixtures/comparator/assertions unchanged, no new upstream build.
C runtime/native/API/full-short and two full posterior matrices plus original
CPU regressions actual PASS within bounded CPU scope; 11080matrix fits,
265920arrays,12600prefixes. CLI caller missing-output defect retained2/parent1;
new caller argument repaired, missed tests/comparator0, no native retry/data
mutation. Historical M5-R/A/B failures and three NOT_CAPTURED remain.

Overall S2 engineering acceptance BLOCKED: full formal preinstall inventory
NOT_CAPTURED;1424noncache bytes/original.so a7432000... pre/post preserved,
actual2339 files includes915cache files without preinstall SHA. Postinstall
full2339 match cannot substitute. Source/history/probability/output audits and
failure index: docs/m6b-ready/g1-s2-c; earlier unpublished preflight7 docs now
included unchanged. Formal adoption NOT_APPROVED, M6-B NOT_RUN; original
G01/G02/G04/G09/G13/G20 remain OPEN, historic rights/privacy DEFERRED/OPEN.
Next unique task independent precise-head Draft PR review and gap decision;
stop, do not execute task03 or reinstall/rerun to backfill missing baseline.

Own formal-inventory instrumentation corrected to include cache; readonly function actual2339/915 omitted-cache, fits0/installations0. Corrected full installer/native runner NOT_RUN; current preinstall full snapshot still NOT_CAPTURED and overallBLOCKED. PR13 independent Draft, precise final publication/CI bound in PR/private receipt; STOP.
