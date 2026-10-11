# TASK09 — M3 ABI2 / M6 CPU 桥接结果

基点唯一为 PR #19 `b082d16939aab0d4ba4b9208475886c4b9ec808c`，
tree `10188bb80a4b9a10dff46c6eac5bb425fe3828ad`。实际 HTTPS fetch exit0，
独立分支 `codex/task09-m3-abi2-m6-cpu` 从该提交创建，未推送。
GitHub 只读确认 PR19 Open/Draft/unmerged；未将此次授权写成独立审核 PASS。

CPU 工程验收 PASS：35 项新测试、127 项原 CPU 回归 exit0、无 timeout。
机器为本地 macOS26.6.2 arm64，已有 bundled CPython3.12.14。
现有 source、native、测试、fixture 和科学参数均不改；STATUS/GAPS 仅追加。
完整命令、退出码、源码及原始日志 SHA 在 validation.json 和私有 receipt 中。
本轮不运行 M2b/M3、完整 G04/M5 native 矩阵、真实 Redis/server/GPU。
M6-B NOT_STARTED/NOT_RUN；本轮完成后停止，下一唯一任务为独立 TASK09 精确本地 HEAD 审核。

新增模块为显式 opt-in，不接自动 detector。调用方先建
`Abi2GlobalController`，给每节点的 `Abi2ProbeAdapter` 传入已拥有的
`Reader` 对象、确切 rank，以及必填 `scope_threads={rank: thread_id}`；
再建 `Abi2LocalController` 并绑定 `adapter.fence = local.fence`。
训练上报使用 `strict_reporter` 显式包裹现有 publisher 或 opt-in outbox。
已有 M6-A/Reporter 默认入口和历史预测保持原样。

## 关键验收

| 项目 | 契约与结果 |
|---|---|
| 严格 ACK 选择 | 显式 StrictAckPublisher 检查 confirmed is True、server_memory_ack is True、确切 record digest，以及 WRITE_CONFIRMED/DUPLICATE_CONFIRMED。None、未知/冲突/错 SHA 拒绝；pending/active 保留。精确重试不重新计时/同步；legacy None 行为保留在旧入口。|
| epoch/scope 对齐 | `control=(epoch<<1)|state`，仅按 epoch 比较顺序；同 epoch 3→2 为合法 reset。请求后的新 publication seq 加匹配原始 state/epoch、合法 standalone collective/outer GroupStart 及 header applied，才生成 per-rank proof。命令 ACK/header alone/旧记录均不够。|
| Profile 完整性 | 连续 read(false)→内存留证→ACK、原始 digest、run/node/rank/PID/created_ns/thread、control word/counters、hash、窗口和当前 generation 检查。ready 必须有完整 per-rank drained snapshot。继承 validate_bundle 精确 communicator/record/scope 数量、CUDA 11 字段、NCCL result、us/elements、Group 一致性；批准 G04 的 Q-TWO 继续生效。|
| Group 相关性 | outer GroupStart/End 必须属于当前命令，group_id/thread 对齐；未完成 Group 不 ready。8 条人工 Group collective 记录只计 4 个独立进程 scope/4 个 communicator scope observations，不当作 8 个独立时长。|
| 状态重置 | 两个完整 epoch 0→1→0 均有新 Monitor scope 记录。部分 reset、仅改变 header、不见边界不能闭合；超时 BLOCKED 且禁止新 epoch。全局/本地/adapter 重启及 reset 中重启需新 generation 证据。|
| 错误拒判 | 缺 rank/data/instance/scope、损坏/重复/gap、损失计数、writer closed/poison/replaced、请求/读取/ACK错误、未确认 ACK、CUDA/NCCL 错误、非法单位/Group 时长均拒判。数值边界仍为 AMBIGUOUS_SPEC。全部 final_alert=false、final_fault_ranks=[]。|

PAPER：SPEC S1/S4/S5，论文 pp23–24/27–35；Probe 的既有 CUDA Event timing
口径不变，Group 公共耗时不改成每 collective 独立时长。
ADAPTATION：上述 ACK、fencing、epoch、scope、完整性及 reset 工程契约；
重用本项目 exact base 的 Reader、M6 状态机、验证器与批准 G04 函数，
精确 commit/path/function/SHA 在 SOURCE_LEDGER.json。
UPSTREAM：无新增 NCCL/CUDA/PyTorch API 或外部代码复用；不引入新依赖。
EXTENSION：测试是人工构造的 CPU Reader API 字典及虚拟同机时间。
字段名 m3_cuda_event_v2 仅测试既有 schema 映射，不能称实际 CUDA Event 测量。
无 GreyHound 算法/代码复用，无阈值或标签调整，无注入真值输入。

## 明确边界

- Native `control` 是 thread_local。本轮只支持调用方显式声明的每 rank 单一
  scope 线程，并保全 process instance；不声称多线程 Probe/所有 timer 资源已重置。
- CPU mock 不调用 Reader 的 ctypes/C++/共享内存实现，没有新 native build。
  实际 ABI 二进制、robust mutex、CUDA/NCCL、硬件与多进程兼容性 NOT_RUN。
  不把这次工程 PASS 当作 M3 新 GPU 实验或生产桥接已验收。
- collected/applied 时间是同一主机的接收时间，窗口是既有 CPU 单机时间域。
  原始 timestamp_ns 保留但不拿它计算 CUDA duration；跨机时钟对齐及在途记录的
  物理采样窗口仍 OPEN。GPU duration 仅来自输入原字段，不从 CPU API 返回耗时构造。
- 原始记录先暂存本轮内存再 ACK；这不是 durable raw journal。重启中断的 epoch
  作废/显式 reset，不继续分析中断窗口；已有 outbox 仅负责训练 iteration 上报。
- 控制面 ACK 证明接收；raw proof 证明所声明线程的 scope 状态；两者均不证明磁盘
  durability、根故障、概率或真实故障识别率。最新错误无法恢复时保留 BLOCKED。
- 消息大小/统计口径、max-group/min-rank、批准 G04 和 detector 参数未改。
  原历史失败、NOT_CAPTURED、915 cache 缺口与隐私/权利 OPEN/DEFERRED 均保持。

## 本轮失败保留

`bridge01` 实际 exit1：3 个 FAIL/1 个 ERROR。新桥接错误地按完整 control word
排序，reset 3→2 被拒，覆盖了已得的 provisional analysis。原断言不改；
改为 epoch 顺序后 bridge02 28 项 exit0。随后为真实 source 边界补 Group lineage、
drain snapshots、reset 重启与线程声明；最终 bridge05 35 项 exit0。
失败原始 stdout/stderr、精确 SHA 和两份完整失败源码快照均保留。
bridge02/03/04 的中间源码全文未保存，只有真实运行 SHA：NOT_CAPTURED，
不将其冒充最终源码验收。最终 bridge05 字节与交付源对应。

`regression-m6b_ready_cursor_contract` 首次 exit2：本轮 caller 漏传既有必填
`--output`，原脚本/断言不改；补齐唯一参数后 regression-cursor02 九项 exit0。
原始 argparse 错误保留。没有依赖安装、native fits、测试阈值/断言缩减。

本地 Git 最終 head/tree/diff/clean receipt 在私有 git-final 目录；没有远端发布授权
推断、PR 修改、合并、服务清理或下一关执行。

证据核验 verify01 exit0：base2024files，2022protected byte-identical，
STATUS/GAPS append-only。changed-check01 使用既有 scan_text/sensitive_path
规则，只检查本轮48个变化文件并解析新增 Python；actual exit0/findings0。
没有完整历史隐私扫描 PASS，也没有用此检查关闭权利/隐私问题。
