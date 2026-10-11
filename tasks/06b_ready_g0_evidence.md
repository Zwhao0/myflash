# Codex 任务书：M6B-READY-G0-E

## 任务目标与停止边界

完成 M6B-READY Gate 0 的剩余证据补全，并对 future iteration cursor 缺口执行独立、确定性的 CPU 契约复现。交付可供 ChatGPT 独立审核的实际源码、原始日志对应的脱敏证据、每个子进程退出码、失败记录和精确 head CI。

本任务不是 M5-S2 安装、G20 修复或 M6-B。不得安装/升级依赖、创建新的依赖环境、编译/修补/加载新的 native 库、切换正式调用方、启动 Redis 实例/系统服务、使用 GPU、访问第二节点、修改科学规则或启用最终告警。完成本任务即停止，等待独立审核。

## 1. 唯一项目与固定起点

唯一项目：Zwhao0/myflash。不得打开、搜索、比较或复制任何此前失败的 FLASH 实现及其代码、日志、目录、脚本、构建产物。

只读核对以下预期快照；若远端发生变化，记录实际 SHA/差异并停止在只读核对，不自动合并、rebase、重置分支或沿用旧审核。

- PR #10：Draft / Open / unmerged。
- head：5b91977b07b4f357e0c2e37490739e4a5803fea0
- tree：5eeeef0101538597b08a1482c3b17d2b9b6be0f6
- base：codex/m5-s1-science-audit，7746fccb88718a5567da0d042d2679672d4226fc
- main：ce984ea21a604092312442c7c788f2f4b244fad4
- main tree / M5-S1 tree：2fc769bd39f96d58e7fb1ea261f984bf24380590
- PR #10 相对 main：diverged，ahead 10 / behind 4，merge-base 7746fccb88718a5567da0d042d2679672d4226fc。
- M6-A 最后执行代码：e3f6b4225db83ec97e0b59161fa4f46a14ab9f68；到发布 head 的后续两次提交没有修改 flash/scripts/tests 执行源码。

从精确 head 新建独立分支 codex/m6b-ready-g0-evidence，Draft PR base 为 codex/m6a-control-plane。既有分支名若已存在，不覆盖；报告状态。保持 Public，不改 main/PR #10，不自动合并，不 force-push，不改写历史或修改可见性。

历史实验只按精确快照取证，不依赖已移动的分支名：

- M5-R：ed954f5a289e2a9f3c585f7f5af3792d0fde0c8d
- M5-P1：d2973f5fa66ae99ec7ea09ea7040a11d1b95b845
- M5-S1：7746fccb88718a5567da0d042d2679672d4226fc

## 2. 允许修改的范围

只能新增：

- tasks/06b_ready_g0_evidence.md
- docs/m6b-ready/g0-evidence/ 下的审核、审批索引、门禁矩阵、脱敏证据、验证回执
- tests/m6b_ready_cursor_contract.py
- scripts/m6b_ready_g0_validate.py（如确实需要独立的有界采集器）

STATUS.md / GAPS.md 只追加，不修改已有段落。其余既有源码、测试、fixtures、依赖锁、隐私规则、历史数据与报告逐字保留。不得修改 flash/m6_iteration.py；缺陷修复留给后续 Gate 4。

先阅读 AGENTS.md、SPEC.md、GAPS.md、PLAN.md、STATUS.md、ARCHITECTURE.md，以及交接列出的 M5-R/P1/S1 和 M6-A 材料。以本次明确范围为准，不沿旧任务文档自动开展下一阶段。

## 3. 执行前证据清单

使用现有项目工具和兼容 Python，优先 node-0 已有 Python 3.12.3；不安装缺失依赖。只读核对当前项目和已批准资源范围，不扫描其他项目或其他作业。

记录 Git commit/tree/parents、工作区差异、全部既有 tracked 文件哈希及正式 .venv-m5 非缓存文件清单。后续只允许新增本任务文件和 STATUS/GAPS 追加。正式原 Rbeast .so 应为：

a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157

不修改 .venv-m5，不导入 Rbeast 开始拟合，不调用 GPU 或 native 构建入口。所有子进程清除 LD_PRELOAD，设置 CUDA_VISIBLE_DEVICES 为空和 PYTHONDONTWRITEBYTECODE=1；不修改系统环境或服务。

## 4. 现有原始证据的只读回验

只沿本项目 docs/m6/{validation.json,data-index.json,postflight.json,installation.json,preservation.json} 指向的私有路径核对，不扫描旧失败项目。解析 JSON，不只读报告中的 PASS 字符串。

至少回验：

1. server-relevant-05 的实际执行 manifest，三个测试子命令、源码 SHA、退出码、超时标志、完整 stdout/stderr 与文件 SHA。
2. 32 项 CPU 模拟测试、六项真实 Redis 测试的完整测试名、各自结果和结束统计；不以 driver 启动成功代替子进程完成。
3. 两轮 epoch 的状态转换、每节点 ACK 与每 rank applied 证据分离、采样/manifest/drain 哈希、M4 分析结果、Monitor 复位证明。
4. 至少一项 ACK-only TIMEOUT、一项 partial-reset BLOCKED、一项缺失/坏样本 INCOMPLETE、一项重启/旧 epoch 拒绝的实际证据。
5. server-validation-04 Redis setup 失败、初期 BLOCKED、超时和 NOT_CAPTURED，以及 postflight/发布包装器失败，均保留原记录。
6. postflight 的自有进程/socket 清理回执与正式环境保护回执。历史清理结果与当前只读观察分别标注，不能将旧“0 残留”当作新的实测。

公开脱敏后的完整测试 stdout/stderr，以及上述正常/异常案例的必要状态证据；精确地址、路径、PID、凭据等仅留私有 runs/。脱敏不得改变科学数值、阈值、样本、标签、状态、退出码和失败原因。公开文件给出原件和脱敏件各自 SHA 及映射说明，不能把脱敏文件 SHA 伪称原件 SHA。

若某原件缺失、不可访问或 SHA 不符，标记 MISSING/BLOCKED/MISMATCH；不得通过重新运行制造“原件”，不得补写原始退出码。保存缺口后可继续其他独立取证，但不能给该门禁 PASS。

M5-R/P1/S1 本轮做相关索引、精确快照及保全检查，不重新编译或重跑历史 22,160 次拟合。原 M5-R FAIL 和三份 NOT_CAPTURED 保持不变。

## 5. Redis 授权账本

只能引用可追溯的负责人原始授权消息，或由负责人明确提供的原始凭据。记录批准者、时间、消息/凭据定位、批准的版本/路径/操作范围，以及私有原件 SHA（确有原件时）。

Codex 自己在 PR、installation.json 或说明文档中写的“用户已授权”，不是原始授权凭据。本次交接也不能被回填成过去安装的授权。

未取得原件时：

- historical_install_authorization = UNVERIFIED
- future_dependency_use = REQUIRES_OWNER_DECISION
- 批准者/批准时间不得猜测或补写。

若负责人后来给予未来复用许可，单独新增 future approval，不改变历史 UNVERIFIED。不要为寻找凭据扫描其他项目或无关会话/邮箱。

## 6. Future cursor 契约复现：只加独立测试，不修现有实现

目标：原 flash/m6_iteration.py 的 IterationReader.read(after_iteration=...) 目前只检查消费者游标早于保留历史，没有拒绝 after_iteration > stream.last。现有 tests/m6_control.py 的游标测试和未来 scope 测试不是这一条件的覆盖。

用现有 MemoryStore、registration/GlobalController 或现有 CPU Simulation 构建记录；不启动 Redis，不使用 CUDA，不调用 Rbeast。

测试至少覆盖：

- last=1 时，after_iteration=2 和一个明显更大的整数：必须明确拒绝或返回 INSUFFICIENT_EVIDENCE/BLOCKED，不得 READ_CONFIRMED。
- 500 条保留后，after_iteration=last+1：同样拒绝。
- after_iteration=last、retained_from-1 的合法边界；不得为了本任务将原来返回完整保留窗口的行为擅自改成增量切片。
- after_iteration=retained_from-2：现有证据不足路径保持。
- 缺失 run、空历史、过期记录：保留现有拒绝/证据不足/TIMEOUT 语义。
- bool、负数、浮点、字符串、NaN/Inf 游标的实际行为分别记录；严格整数契约标为 ADAPTATION 工程契约，不能冒称论文要求。

在断言之前先持久化输入、服务端 last/retained_from、原始返回状态或异常，保证失败也有原始输出。保留该独立测试，以便 Gate 4 修复后对同一测试作 green 回归。

对当前源码，合法未来游标被 READ_CONFIRMED 接受应使契约测试退出非零并显示 FAIL。不得反转断言以证明“缺陷存在”后把功能门禁写 PASS；不得使用 expectedFailure、跳过、修改旧测试或捕获异常后静默吞掉失败。

采集器可以在完整记录此失败后继续其他独立检查，但必须分别保存子进程退出码，顶层不得把存在未通过必需契约测试的验证包写成工程全 PASS。

## 7. 本轮允许执行的回归与证据收集

只执行现有纯 Python/CPU 单元与上述独立契约测试，例如：

- tests/m6_control.py
- scripts/m6_demo.py --output <新的私有 runs 目录>
- tests/m6b_ready_cursor_contract.py
- tests/privacy_check_test.py
- scripts/privacy_check.py

不调用整个 m6_validate 注册表，不运行 tests/m6_redis.py，不启动 native 回归、不运行任何新 Rbeast fit。原六项真实 Redis 的本轮工作仅为第 4 节的原始证据回验；新的真实 Redis 回归要等复用权限明确。

使用有界 subprocess 执行并 wait 每个子进程；CPU 单元可沿既有 120s 保护，文本隐私扫描可沿既有 600s 保护。保护预算是工程测试上限，不是科学采样时长。超时只终止本任务自有子进程组，不能泛化清理。不要用 shell 管道或“|| true”吞掉真实退出码。

记录每条完整私有命令、执行目录、解释器/环境、输入/源码 SHA、stdout/stderr、退出码、超时和 child_finished。输出目录必须新建；原始失败不可覆盖。

## 8. 门禁矩阵与依赖

每项分开记录：功能、严格数值重复、科学有效性、隐私发布；同时区分执行者结论和待 ChatGPT 独立审核结论。

矩阵必须保留：

- G0：远端/历史绑定、M6-A 证据、Redis 原始授权、future cursor 复现。
- G1：既有 C/P1 有限范围工程 PASS；M5-S2 隔离安装/验收 NOT_RUN；正式调用方采纳 REQUIRES_OWNER_DECISION。
- G2：G01/G02/G13 及参数/预处理完整审批 REQUIRES_OWNER_DECISION；批准后回归 NOT_RUN。
- G3：G04 权重、20% 定义、CV 和冲突处理 REQUIRES_OWNER_DECISION。
- G4：future cursor 修复、Reporter 完成/出站记录/ACK、时钟域、重启、ABI2 桥接与 CPU 契约 OPEN/NOT_RUN。
- G5：最终组合回归/审计 BLOCKED；G09 范围、真值隔离、指标及安全方案待批准。
- M6-B 的真实 GPU/跨机端到端结果 NOT_RUN，既不是本任务应完成的结果，也不是可提前宣布的 PASS。

需要明确的源码依赖：

- RbeastAdapter.analyze 用 sys.executable 启动 worker；worker 目前只检查版本，不能区分原 wheel 与 C。候选环境验收不等于正式调用已指向 C。
- IterationReporter.end 不处理 publisher 的返回回执；不能直接把 Redis publisher 作为可靠落盘/重试 sink。
- IterationPublisher 的 confirmed_at 来自调用方时钟，不能当作跨机 Redis 服务端接收时刻。
- M6-A 的 Probe、applied/sample/drain 来源和时钟域均限定 CPU 模拟。
- Reader.request(state, epoch) 的 ABI2 接口未携带 M6-A 全局/本地 generation；需要真正约束原生写入的桥接方案。
- M4 当前禁用未定的 20% 过滤，双权重与 population/sample 分歧保留歧义；正常临时候选和跨标签冲突不能删除。

这些是后续任务的输入，不授权本轮修复、换库、改科学规则或启用 native。

## 9. 必需交付物

在 docs/m6b-ready/g0-evidence/ 交付：

- BASELINE_AUDIT.md：实际 DAG、精确快照、执行源码与发布源码关系、证据边界。
- GATE_MATRIX.md：每项状态、证据、依赖、关闭条件和审批需求。
- APPROVALS.json：原始凭据或 UNVERIFIED；不自批科学/安装权限。
- EVIDENCE_INDEX.json：原始/脱敏文件定位、各自 SHA、读取/核验结果。
- FUTURE_CURSOR.md：最小反例、旧源码行为、测试断言、实际退出码和未修复说明。
- validation.json：所有本轮命令/机器别名/解释器/源码与日志 SHA/退出码/超时。
- preservation.json、postflight.json：已有文件及正式环境前后保全、本轮自身资源收尾。
- 必要的完整脱敏测试日志及正常/异常状态证据。

STATUS/GAPS 追加 M6B-READY 总目标、本轮发现和下一唯一任务。不得把已交付报告、red-test 复现成功、历史 CI 或 Codex 自评写成准入全 PASS。预计本轮可标“证据工作已交付；future cursor FAIL；M6B-READY BLOCKED”，以实际结果为准。

## 10. 发布与独立审核

先做完整文本隐私检查和变更路径检查，再普通 push 独立 Draft PR；只发布本项目代码和脱敏证据，不新增公开论文全文、第三方源码或 wheel。

回读发布 head/tree、base、实际 diff。保存当前 head 的 push 隐私 CI；PR CI 若使用临时 merge commit，记录真实 checkout SHA 并核对 tree 与目标 head 的关系，不能只看 run 的 head_sha。CI 只证明实际检查的范围，不证明 GPU/科学/运行时采纳。

最终回执明确：新 PR、head/tree/base、执行代码 SHA、文件级对应关系；已运行/未运行项目；全部失败；原始授权是否找到；正式环境是否不变；本轮没有执行的安装/native/Redis/GPU项目。

本任务到此停止，等待 ChatGPT 独立审核。不得开始 M5-S2、科学规则修改、G20 修复或 M6-B。
