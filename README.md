# FLASH：两台 H800 的全新开发与论文复现工作包（v2）

这是一个**从零开发**的任务与规格工作包，不包含可运行 FLASH 系统，也没有在两台 H800 上完成任何功能/性能验证。

## 起步方式（不接触过去失败的项目）

1. 新建一个独立、空白的工作目录，例如 `~/projects/flash-fresh`，将本 ZIP **直接解压到该目录**，使 `AGENTS.md` 位于工作目录顶层。
2. 在该目录启动 Codex。首轮只让它执行 `tasks/00_bootstrap.md`（M0），不要一句话要求“实现完整 FLASH”。
3. M0 通过后进入 `tasks/01_baseline.md`（M1），先证明两台 H800 的原生 NCCL 和训练底座可运行，再逐关实现 Probe、手动剖析、离线算法、检测器和自动闭环。
4. 不进入旧失败项目、不读取或比较其中源码与日志、不按它的目录结构开发、不借用它的构建产物。`GreyHound` 原始开源仓库是允许参考的上游，不属于旧失败项目。

推荐的首轮提示词（可以直接复制）：

```text
请在全新 FLASH 工作目录开展 M0，从零启动项目，绝不参考或访问此前失败的实现。
先阅读 AGENTS.md、SPEC.md、GAPS.md、PLAN.md、STATUS.md、GREYHOUND_MAP.md、tasks/00_bootstrap.md，以及 references/chapter3.pdf。
本轮只执行 tasks/00_bootstrap.md：建立干净的仓库结构，写出架构/来源映射/拟议环境探测清单，并更新状态。不要开始 M1，不编写 NCCL hook 或定位算法，不运行 GPU 故障注入，不安装或升级系统软件。
结尾提交你实际修改的文件、运行命令、退出码、未知项和 M1a 唯一建议任务，然后停止。
```

## 包内文件

| 文件 | 用途 |
|---|---|
| `AGENTS.md` | Codex 长期约束、来源分级、运行安全和验收标准 |
| `SPEC.md` | 中文论文第三章机制和参数，不补造缺失细节 |
| `GAPS.md` | 原论文内部歧义、GreyHound 接口差异和待实测条件 |
| `PLAN.md` | M0–M8 阶段划分和停止条件 |
| `GREYHOUND_MAP.md` | GreyHound 固定版本与已经核对的参考代码入口 |
| `STATUS.md` | 当前阶段及运行证据记录 |
| `tasks/00_bootstrap.md` | 首轮项目启动任务，完全不依赖任何旧实现 |
| `tasks/01_baseline.md` | 原生 NCCL/训练底座验证（M1），按子任务审批 |
| `tasks/TEMPLATE.md` | 后续逐轮实现、修复和验证任务模板 |
| `references/chapter3.pdf` | 原论文第三章的完整页面摘录（原 PDF 第 35–64 页，对应印刷页 19–48） |
| `references/chapter3_extracted.txt` | 仅供文本检索；公式、图表以 PDF 为准 |

## 复现目标与来源原则

只做第三章 FLASH：常态检测、按需 CUDA Event 剖析、通信组到 rank 级定位及论文内的 fail-stop 检测。不开发第四章 SHIFT、恢复、自动迁移或工业化平台。

主要依据是用户上传的**中文论文第三章**；GreyHound 作者开源代码用作可复用的工程参考；CUDA/NCCL/PyTorch 官方文档用于核对接口语义和兼容性。**不使用上次失败系统作任何来源或诊断资料**。可复用 GreyHound 中合适的代码，但须固定 commit、检查许可并标记与论文的差异；不能把 GreyHound 的 ACF、stop-the-world、mitigation 默认混进 FLASH。

论文的实验环境是两台各 8 张 H200，用户计划两台 H800。卡数、显存、RDMA/NIC 和软件版本尚待两台目标机器实测，不推断可直接运行 16 ranks。对结果分别声明“功能复现”“机制/趋势复现”“论文条件数值复现”，不拿原论文图中数字倒逼代码。

每轮一个最小任务，改动/测试/日志/退出码可复核，遇到未定义参数或运行阻塞及时停止并登记。所有故障注入需目标、许可、最大持续时间和回滚方式；GPU 结果必须来自目标机器实际运行。
