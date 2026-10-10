# FLASH clean-room reproduction: Codex instructions

## 当前目标与来源
- 此仓库从零开发**中文论文第三章 FLASH**。不要打开、搜索、比较、引用或复制任何此前失败实现的源码、日志、目录、脚本、构建产物。
- `references/chapter3.pdf` 是目标规格；`SPEC.md` 是带位置标注的提要；`GAPS.md` 记录论文没有说明或者相互冲突的事项。
- GreyHound 作者的公开仓库（固定 SHA 见 `GREYHOUND_MAP.md`）是**可选工程参考**，不是 FLASH 原实现。复用时说明精确 `commit/path/function`、来源许可证和必要调整，避免将 GreyHound 算法当成 FLASH 的事实。
- 官方 NCCL/CUDA/PyTorch API 文档和目标机器实际加载的版本是接口语义/兼容性核验依据；不以经验代替实测。
- 每个实质性选择必须标记 `PAPER`、`UPSTREAM`、`ADAPTATION` 或 `EXTENSION`，并记录出处。
- 每轮先阅读 `SPEC.md`、`GAPS.md`、`PLAN.md`、`STATUS.md` 与当前 `tasks/` 文件，只做明确批准的任务。

## 不可静默更改的科学机制
- 不把 Rbeast 静默换成另一种 BOCD，不把 CUDA Event 时长换成 CPU API 返回耗时。
- 不把 GreyHound 的 ACF 迭代估计、暂停训练性能验证和缓解流程混入 FLASH 默认路径。
- 不把 rank 最小时延定位规则换成最大时延规则，不为了对齐论文图表调标签和样本。
- 故障注入目标 rank、时间和真实类别只给独立评估器，不得被在线检测器/定位器读取。
- 人工构造测试只证明算法单元逻辑，不能称 GPU 实验；原论文结论只作为需检验的目标。

## 增量任务与验收
- 一次只做一个最小任务，先列出允许修改的文件、接口、测试和退出方式，再实施。
- M0 只做新仓库初始化与文档，**不写 NCCL Hook 和 FLASH 核心逻辑**；M1 先无 FLASH 运行基础通信和训练，失败即停，不跳到 M2。
- 不因测试失败而扩大重构、删除失败记录、缩小断言或暗改阈值。
- `PASS` 必须提供实际执行机器、完整命令、退出码、原始日志路径；无法运行写 `BLOCKED`/`NOT_RUN`。
- 不可把缺失/坏数据补零参加最小 rank 筛选；明确 s/ms/us、数据元素 count/字节数/样本数。
- 区分 rank、进程内 communicator 指针、跨进程 id_hash、Group 批次 ID 和训练并行组。Group 公共耗时不得冒充每条 collective 独立耗时。
- 每次真实实验记录版本、参数、机器与互联、训练日志、原始采集、控制事件、预测以及评估器独立真值。

## 资源使用和安全
- 只读探测可在获准机器范围执行；驱动/CUDA/NCCL/系统软件的安装或升级需事先确认。
- GPU 降频、OOM、进程终止、通信/网络干扰均须先明确目标 GPU/PID/作业、最大时长、超时保护与恢复动作。
- 不干扰同机其他作业，不用 `pkill python`、清空整个 `/dev/shm`、Redis `FLUSHALL` 等泛化清理。
- 仅操作当前项目和本次 `run_id` 的资源；Redis 不得开放至不可信网络。
- 不输出凭证、token、数据集敏感内容；提供日志前注意脱敏。

## 每轮结束
更新 `STATUS.md`：任务号/提交与 diff、来源、实测设备、运行命令/退出码/日志、通过/失败/未测项、下一唯一任务。完成本轮后停止；只有明确审核通过才推进下一关。
