# TASK12 B01 — Detector 自动触发 Profile 最小接线

ADAPTATION 授权：2026-10-11 当前用户明确批准 TASK12，唯一基点
PR22 HEAD `0dd0e1c5cac043aef1449d5cfe9e74ed38447cf3`。独立本地
分支 `codex/task12-detector-profile`。先读取该基点 AGENTS/SPEC/GAPS/PLAN/
STATUS/tasks；沿用 task05 的 G01-a/G02-inclusive_span/G13-A 和指定 C 身份，
以及 task07 G04 既有批准；不重新决定规则。

允许修改：`flash/m6_controller.py`；新增 `flash/automatic_profile.py`、
`tests/task12_auto_profile.py`、本任务、`docs/m6b-ready/task12-auto-profile/**`；
STATUS/GAPS 仅追加。私有完整命令回执/CPU日志 `runs/task12-auto-profile-20261011`。
不修改 Detector/Rbeast/Localization/Reporter/consumer/native/原断言/fixture。

接口：`GlobalController.start_automatic_v1(request, now)`（ABI2 子类继承）；
`DurableAutomaticProfiler(path, consumer, controller, manifest, adapter=...,
approved_rules=True, cpu_simulation=False).step(now)`。显式 simulation=True
才准测试适配器；实际模式仅既有指定 C opt-in 适配器，身份检查保留。
独立自动 trigger/version；不得用 MANUAL_TEST_TRIGGER 代称自动请求。

一致性：独立 SQLite 的一笔事务保存有序决策及冻结请求意图，然后才
ACK DurableIterationConsumer。确定性 request_id = run/record/规则版本/批准包/C身份哈希；
完整请求另有内容哈希用于冲突拒绝，不因 generation 或 native 诊断差异重建身份。
请求 CAS 内同时创建 epoch、保存 request_id/hash 和完整自动来源。失去 ACK
重读/精确重放，不重新 fit 冻结决策。忙/重置/失联保留意图并暂停后续 ACK。
有界容量耗尽明确 BLOCKED，不删意图；服务器内存 ACK 不证明 Redis 磁盘或
exactly-once 效果。单一 ledger/consumer 所有者，任何未覆盖游标都拒绝。

验收：受控 CPU 适配器 + MemoryStore，重复/冲突、候选非触发、局部事务失败、
intent 后 ACK 前/ACK 后请求前/远端成功后本地回执前中断、实际子进程硬退出、
失联/丢 ACK/重启/旧 generation、active 和 partial reset、缺失或坏源记录、
容量/绑定/身份门禁、原 CPU 相关回归。完整 argv/设备/退出码/原始日志必须保存；
故障用例仅证明工程合同。不新跑历史后验矩阵。

退出：本地可审阅提交，报告精确 HEAD/tree/diff/证据/未测边界，然后停止。
本轮未授权远程发布；不默认生产切换、安装、阈值调整、最终告警、真实 Redis/
GPU/native/server/框架/物理窗口/恢复实验或 M6-B。不推进后续任务。
