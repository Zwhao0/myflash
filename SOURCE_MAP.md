# M0 来源与 GreyHound 参考映射

## 来源层级与核验范围

PAPER：`references/chapter3.pdf` 为本项目规格。M0 实际读取 30 页文本，并核对图3-1/2/3/4、recovery_ratio、式3-1/2 所在完整页面。PDF SHA256 `49694130e79e0f08e17aec8ad2f7955f2551cf0942f076389d8b11cf2aebadaa` 与提供的 source_manifest 一致；不声称已重新验证未提供的完整原 PDF。

UPSTREAM：唯一可选工程参考为 [wutianyuan1/Greyhound 固定快照](https://github.com/wutianyuan1/Greyhound/tree/d641b3997c17de700e1ef7d37e353418df7e336d)，SHA `d641b3997c17de700e1ef7d37e353418df7e336d`。`GREYHOUND_MAP.md` 是工作包提供的既有核对摘要。本轮未联网读取该仓库正文、未 checkout/clone、未编译、未复制代码，不能把摘要提升为本轮独立完成审计。

许可证状态：NOT_VERIFIED；没有亲自读取该 SHA 的 LICENSE/NOTICE 或各源文件头，不猜测 MIT/Apache/GPL。任何复用须先核验精确许可及范围、保留要求的声明，再记录 commit/path/function/line 与修改 diff；许可证未核验或不允许复用时保持独立实现（G18）。本轮只有文档映射，无上游代码复用。

ADAPTATION：全新 Git、目录布局、run/epoch 隔离、单位约定和证据包均为本项目工程草案。EXTENSION：带宽定位、非 NCCL 栈、异步回收等须独立审核。不访问任何过去失败实现。

## 固定快照入口与首次验收

下表所有上游路径都固定在上述完整 SHA。符号未亲读时统一标待查看；不提供未经验证的行号或凭空命名函数。

| 分类 | 原始路径 / 需查看符号或结构 | 工作包已提供的摘要 | 本轮状态、适配边界与首次验收 |
|---|---|---|---|
| 可参考 | `README.md`：启动链、依赖、artifact 配置 | A10 四卡、ACF、profiling/validation、precheck、mitigation 与路径耦合 | 正文待查看；依赖/许可证 M1a 文档核对，A10 频率/拓扑不沿用；不为 M0 安装 |
| 需要改造 | `detector/ncclprobe.cpp`：NCCL 同名包装、`ncclCommInitRank`、`ncclCommInitRankConfig`、`ncclCommSplit`、`ncclGroupStart/End`、comm/id_hash 与事件结构 | 拦截、unique ID hash、Group 记录、调用压缩、状态检查 | 函数定义及布局待查看；M2 验 hook/共享内存/身份；M3 验 Event stream 与 Group 公共 duration；保留独立的 FLASH 控制路径 |
| 不能直接沿用 | `detector/ncclprobe.cpp`：`CHECK_PAUSE_MAGIC=503`、`should_check` 与 GroupEnd 后 event_handler 入口 | 特定 ncclInt8 调用可触发暂停控制 | 正文待查看；M2 在源级排除，再 M3 验无暂停/NCCL 广播依赖，不仅删 Python validation |
| 不能直接沿用 | `detector/event_handler.cpp`：world communicator 广播、`STATE_VALIDATE` 暂停循环、GEMM/P2P 任务（函数名待查看） | Redis→NCCL 广播并可能暂停训练 | 文件正文待查看；FLASH 使用 Redis→本地→共享内存的 0/1 流程；M2/M3 审计排除，M6 核验控制路径 |
| 不能直接沿用 | `detector/ncclprobe.cpp`：`ncclCommSplit` 内 `char buf[128]` 和 hash 路径 | 未初始化 buf 且警告无法获得 unique ID | 正文待查看；G06 OPEN；M2 先审计实际 API，Split 身份未验证则显式 unsupported；清零 buf 不构成全局身份方案 |
| 需要改造 | `detector/control_plane/slow_detection.py`：ACF 周期估计、`rb.beast`、`validate_performance_drop`、变点输出/过滤数据结构 | 实际使用 Rbeast；season='none'、hasOutlier=True 等上游调用；默认参数不等于 FLASH | 正文待查看；M5 用框架 rank0 迭代输入，剥离 ACF，不抄参数；先解决 G01/G02/G13 |
| 可参考 / 需要改造 | `detector/control_plane/global_analyzer.py`：id_hash→clique、标签映射、最大平均时延与 median 阈值路径（精确函数名待查看） | TP/DP/PP 标签和组筛选，不能证明已含 FLASH rank 最小延迟及 expert 交叉证据 | 正文待查看；M4 核映射与 group→rank 算术，保留论文 max 组/min rank；G04 OPEN |
| 可参考（部分来源） | `local_controller.py`：Rbeast 独立子进程调用 | 工作包仅说检索片段显示作者为段错误使用子进程 | 完整路径/函数/上下文均待查看，不猜测目录；M5 兼容性验证，不直接选定进程隔离方案 |
| 论文缺失 | Rbeast 版本/API 输出字段、20% 参照、保护区间、持续性时长、权重/合并规则 | 论文参数与实验时延不能唯一确定实现 | 无可证明的原 FLASH 源码；G01–G04/G13，M4/M5 前必须审核 |
| 论文缺失 | ABI/并发发布、epoch/ACK/完整性、Group/Graph/Split 支持范围 | 论文仅给高层路径 | G05–G07/G16；M2/M3/M6 前分别明确，不能把 GreyHound 现状当 FLASH 事实 |

## PAPER 模块追溯

| 模块 / 行为 | 论文出处 | 本项目首次计划验收 |
|---|---|---|
| 两机通信/训练底座 | 原环境与模型 §3.4.1 pp.36–37；工程顺序来自 PLAN | M1a 仅盘点，M1b 起另行通信/训练 |
| NCCL 拦截与共享内存 Monitor | §3.2.1 pp.23–24、§3.3.1 pp.32–33 | M2 |
| CUDA Event / 0→1→0 / Group duration | §3.2.3 pp.27–29、§3.3.1 p.33 | M3 |
| 标签→group→rank | §3.2.3 pp.30–31、§3.3.2 p.34 | M4 |
| 迭代上报 / Rbeast / recovery_ratio | §3.2.2 pp.25–27、§3.3.3 p.35 | M5 |
| 自动闭环 | 图3-1 p.24、图3-3 p.28、§3.3.2 pp.33–34 | M6 |
| MoE 混合并行、fail-stop | §3.1.3 p.23、§3.2.4 p.31、§3.4.6 pp.44–45 | M7 |
| 正式实验与口径 | §3.4 pp.36–45、§3.5 pp.46–47 | M8 |

官方 NCCL/CUDA/PyTorch 文档在 M1a 取得目标版本后用于接口兼容核验；当前尚未据其在线内容作本机兼容性判断。提供的参考链接不等于版本已匹配。
