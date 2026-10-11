# TASK12 B01 工程合同（ADAPTATION v1）

唯一来源起点 PR22 `0dd0e1c5cac043aef1449d5cfe9e74ed38447cf3`。
PAPER：SPEC S2/S3/S4、§3.2.2–3.2.3 pp25–29；rank0 有序迭代触发按需剖析，
Profile 窗口依既有 `max(T_ms/1000*2.2,20s)`。本文没有重读/重新判定科学机制。
ADAPTATION：沿用 task05 APPROVAL.json 的 G01-a/G02-inclusive_span/G13-A；
G04 仍为 task07 已批准选择。指定 C SHA 从既有 adapter 常量读取，不更新二进制。
EXTENSION：测试用 CPUAdapter + MemoryStore 及受控故障点，仅证明接线合同。
无 GreyHound 源码复用或新的 UPSTREAM 实现。

`DurableAutomaticProfiler` 接收同一 run/store 的 rank0 DurableIterationConsumer，
一次 step 最多处理一条新增记录。只将该记录之前最多29条已持久化记录送入既有
`detect(..., approved_rules=True)`；不得读未来迭代或 evaluator 真值。所有过滤、
窗口、参数和阈值由原 Detector 完成。每条正式 detection_trigger 都产生独立意图；
不引入 episode 合并、冷却期、阈值修改或“已在 Profile 所以忽略”的规则。

独立 SQLite 复用既有 `_Ledger` 的事务/schema及 EXTRA synchronous/fullfsync/目录
fsync，独立 kind 绑定 consumer 路径、manifest、模式、C身份/解释器、容量和规则。
它的 position 是“决策已持久化的位置”，不是 consumer 的 ACK 游标。records 中
每条保存输入记录、完整决策、冻结请求（或 null）、processable 和远端回执。
决策及意图同一事务提交，之后才调用原 consumer.commit([record])。两数据库之间
没有原子事务；正确性靠严格先后顺序、最多一条尚未 ACK 的记录与一致性拒绝。

| 中断点 | 重启行为 | consumer cursor |
|---|---|---|
| 决策事务前/事务中 | 事务回滚；从确认记录重新检测 | 不推进 |
| 决策+意图提交后，consumer ACK 前 | 重新 poll 证明同一原始记录；复用冻结决策/意图 | 证明成功才 ACK |
| consumer ACK 后，请求 CAS 前 | 重放持久意图 | 已 ACK 但意图必然存在 |
| 请求 CAS 成功，ACK 丢失/本地回执提交前 | 相同 ID、相同内容重放；远端返回原 epoch | 不生成重复 epoch |
| 接受回执已本地保存后 | 校验远端仍有该 ID/hash/epoch；缺失则 BLOCKED | 不继续吞新数据 |

request_id 由 run、完整 record 哈希、自动接口版本、Detector 版本、批准包和 C 身份
确定，不包含 controller generation、随机输出或诊断文本。完整请求（含决策/manifest/
simulation 标识）另算 request_sha256。相同 ID、不同 payload 必须拒绝，不能创建
第二个 epoch。GlobalController 的独立 `start_automatic_v1` 验证完整版本、批准规则/
参数、严格 bool trigger、候选、输入序列、rank0 和 C 身份证据；CAS 内重新检查 source
还在确认保留区、ownership 和去重，自动来源与 epoch 一并写入同一 run 文档。
原 start 继续只接收 MANUAL_TEST_TRIGGER。Abi2GlobalController 继承新入口，尚无真实
编排或自动入口接 ABI2 native 的实测；本任务不声称它已完成。

状态 active/reset/容量耗尽/失联/旧 generation/源记录不再可证明时，保存意图并
BLOCKED，后续新增迭代不 ACK。重放待处理意图优先于新消费；容量默认最多500个
决策，达到上限明确停止，不删数据或自行开新 run。已确认远端请求后来失败/ABORTED
仍算“请求已被接收”；继续遵从原 controller 的复位/失败行为，不无限补发已接收
请求或把它当诊断成功。控制器已完成 epoch 的 ID 仍可重放去重。

Detector engine/身份/原始数组失败也持久保存决策，不 ACK，返回 BLOCKED，后续 step
不重拟合该冻结失败。短/常量输入等正常证据不足允许 ACK；正式 trigger 才有请求。
本任务不自动清除失败，不实现 operator reconciliation 或坏文件重建。

运行合同是单一 dispatcher 所有者，独占该 consumer/ledger；不支持双主。
外部擅自 ACK、缺失 journal、变更 binding、坏 hash/schema/intent 被拒绝。SQLite IO、
格式或编程错误会显式抛错并终止当前调用；不把它包装成成功或跳过迭代。
物理掉电、文件系统/磁盘丢失及双库独立回滚不在 CPU 硬退出测试证明范围。
RedisStore 的现有 CAS 可作为未来传输接口；本轮只运行 MemoryStore。
远端成功回执仅证明服务器内存接收，不证明 Redis 磁盘持久性或 exactly-once Profile
效果。丢失 run/已接受请求证据需要人工核对，禁止默默重新创建 run 或漏触发。

调用必须显式 approved_rules=True。实际模式仅接受明确 candidate_c_python 的既有
RbeastAdapter（原 native 身份门禁不变）；CPU 模式需显式 cpu_simulation=True，不能
使用 native adapter。本轮不执行实际模式，不加载 Rbeast/native，不连接 Redis。
没有默认生产入口/CLI/后台循环、故障注入、最终告警或 M6-B。

回退方式：停止调用新 dispatcher；保留本 run 的两份 ledger 和远端证据供核对。
原手动接口保持可用；有 active epoch 时仍按原复位合同处理，不能删除意图“回退”。
下一唯一任务：独立审核本轮精确本地 HEAD；真实编排、框架边界、物理窗口及恢复
分别另行授权。G01/G02/G13/G04 已批准规则不重开审议。
