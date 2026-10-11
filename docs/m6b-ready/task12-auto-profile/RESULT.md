# TASK12 结果：CPU 工程验收 PASS；独立审核待完成

从 PR22 精确 HEAD `0dd0e1c5cac043aef1449d5cfe9e74ed38447cf3`，独立分支
`codex/task12-detector-profile` 实现 B01 的最小接线。运行代码只改既有 Controller
并新增 automatic_profile；Detector/adapter/consumer/Localization/native 字节保持。
新增合同、任务、定向测试及证据，STATUS/GAPS 仅追加。精确最终本地 commit/tree/
diff 绑定私有 `runs/task12-auto-profile-20261011/final-git.receipt.json` 与交付回复，
避免在提交内自引用未来 SHA。没有远端发布或 M6-B 准入结论。

ADAPTATION：决定和冻结请求意图先同一 SQLite 事务提交，之后 ACK consumer；
本地游标已 ACK 时至少存在对应持久意图。确定性身份不随 generation 或 native 诊断
变化，完整内容 hash 用于冲突拒绝。正式 detection_trigger 才调用独立自动 v1 入口。
待处理意图优先重放；忙/失联/复位时保存意图并背压，绝不静默丢弃。详见 CONTRACT.md。
已批准的 G01/G02/G13/G04 不重审、不调参；没有最终告警。

实测设备：本地 macOS26.6.2 arm64，Mac17,3 / Apple M5；现有 bundled
CPython3.12.14、SQLite3.53.1。硬件与版本由 environment01 实际 exit0 取得，
真实 hostname、完整绝对 argv/cwd 和原始 stdout/stderr 在私有 receipts。
测试用受控 CPUAdapter + MemoryStore，无 native/Rbeast 拟合、Redis或GPU。

| 实际执行 | 数量 | 退出码 | 原始日志 |
|---|---:|---:|---|
| auto03：TASK12 定向测试 | 24 | 0 | runs/task12-auto-profile-20261011/auto03.stdout.txt / stderr.txt |
| regression01：原 m6_control | 32 | 0 | 同目录 regression01.stdout.txt / stderr.txt |
| regression02：原 detector/reporter/C门禁/cursor/outbox/ABI2 CPU | 108 | 0 | 同目录 regression02.stdout.txt / stderr.txt |
| cursor01：原 cursor contract | 9 | 0 | 同目录 cursor01.stdout.txt / stderr.txt |

完整实际命令保存在每项 `.receipt.json`；审阅版本的 argv、源码 SHA、原始与脱敏
stdout/stderr SHA、执行机器与时长保存在 validation.json，日志在 logs/。
实际命令形式为现有 bundled Python `-B runs/task12-auto-profile-20261011/run.py`
加 run 名、同一 Python、`-B` 及 validation.json 中完整参数。auto03 使用
`TASK12_EVIDENCE_DIR=runs/task12-auto-profile-20261011/auto03-states`，保存24份原始状态。
四份状态副本在 states/，均记录游标、journal 决策/意图/receipt 和 run 文档；其它
原始状态仍在私有 run。初始 auto01 的18项、扩展 auto02 的24项均 exit0，保留日志。
最终运行 auto03 固定了稳定逻辑身份与完整内容冲突校验，未改科学参数或原断言。

覆盖重复/冲突、候选非触发、规则/C门禁、事务失败、intent后ACK前中断、ACK后
请求前失联、远端成功后本地回执前中断、丢ACK、失联重连、重启、旧 generation、
active/partial reset、已完成请求去重、源记录改变/过期、journal坏意图、容量及绑定
拒绝。子进程 `os._exit(73)` 是预期受控 CPU 崩溃；父测试实际 exit0，不能把73写为
native/训练失败。首轮到最终本轮 CPU 测试无失败；未缩小断言。

发现阶段根目录 Git128、未匹配 shell glob1 保留于会话；原始独立日志 NOT_CAPTURED。
它们是目录/文件发现错误，非验收测试失败。历史 FAIL/NOT_CAPTURED/915 cache 缺口/
privacy/rights 状态保留，没有删除或重写。仅对本轮变化文本执行既有轻量检查，不
声称完整历史审计通过。

CPU 硬退出不证明物理掉电；远端回执仅服务器内存接收，不是跨存储原子事务、Redis
磁盘持久性或 exactly-once 效果。每次前缀正式触发是独立意图，没有新 episode规则。
默认最多500个决策，容量/源证据丢失明确 BLOCKED，需要人工核对，不自动修复。
单一 dispatcher 所有者；真实 ABI2 自动入口、编排、框架完成边界、物理窗口/跨机
时钟、原始 journal 和安全恢复仍分别 OPEN/NOT_RUN。真实 Redis/GPU/native/server/
M6-B、默认生产切换、阈值调整、最终告警、远端发布均未执行。

下一唯一任务：独立审核本轮精确本地 HEAD；完成本轮即停，不自行推进下一关。

静态 verify01 实际 exit0：基点2084文件中2081保护文件字节一致，STATUS/GAPS 两项
仅追加；11份来源绑定、四组执行源码/日志哈希通过；本轮改变文本 findings0。
完整结果见 preservation.json（证据封装前实际输出），最终封装后再次核验和 staged
`git diff --check` 的实际回执保留私有。轻量文本检查不代替历史 privacy/rights 审核。

最终静态 verify02 超时90s，wrapper 实际 exit1；原 wrapper 未保存 timeout 异常的
子进程退出码/原始 stdout/stderr，明确 NOT_CAPTURED。原始异常在会话工具输出，
完整 argv/cwd、原 verifier/runner 源码快照及 SHA 在私有 verify02.failure.json。
verify01 逐文件 Git 读取实际85.694s；最小修正仅批量读取完全相同的固定 Git blobs，
原有保护断言和90s超时不变。该静态失败不删除，不影响24+149 CPU退出0事实；
最终另编号静态复核绑定私有回执。

批量版静态 verify03 实际 exit0/no timeout；原2081文件保护/2追加/11来源/四组执行
源码绑定和改变文本 findings0 全部再次通过。最终结果见 preservation-final.json 和
validation.json；verify02 原超时与 NOT_CAPTURED 不回填为成功。最后只封装证据后
再检查，不改运行代码或重跑 CPU 科学测试。
