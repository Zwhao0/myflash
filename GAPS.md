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
