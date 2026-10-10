# FLASH 全新开发状态

当前阶段：M0 新仓库建档与规格/接口梳理
当前状态：PASS（实际创建与核验完成；阶段推进待用户审核）
当前任务：tasks/00_bootstrap.md；完成 M0 后停止，不推进 M1。

## 权威路径、来源与改动

- 开发机：gpu-01，Linux 6.8.0-142-generic x86_64/glibc2.39；工作目录 `/home/campus/zhangweihao/myflash`，独立 Git 分支 `main`。
- 用户明确在服务器开发；该目录 SSH 只读检查时不存在，创建时再次确认不存在。不访问旧失败实现。
- 原始输入是本地工作包的文档/第三章 PDF；未将本地连接凭证、其他项目、实现或构建产物传入。输入哈希见 `docs/m0/input_hashes.json`。
- 新增 `.gitignore`、`ARCHITECTURE.md`、`SOURCE_MAP.md`、`ENVIRONMENT_PLAN.md`、四个目录 `.gitkeep` 与 `docs/m0` 证据；更新本文件与 `GAPS.md`。
- PAPER 来源仅第三章与 SPEC；UPSTREAM 来源为 GREYHOUND_MAP 提供的固定 SHA 摘要，上游正文/许可证未独立读取。ADAPTATION 为架构接口/目录/单位/隔离/计划草案；EXTENSION 不纳入基线。
- G01–G16 未关闭；追加 G17 图3-4 数值差异、G18 许可/正文待核对、G19 参数/显存口径、G20 迭代发布语义，全部 OPEN，不自行决定科学假设。

## 实际运行与证据

| 检查 | 实际机器、完整命令与原始日志 | 退出码 / 结论 |
|---|---|---|
| PDF 全30页文本与 SHA | 本地只读参考核验；完整 bundled Python 命令见 `docs/m0/00_local_reference.log`；关键完整页图像已核对，详见 VALIDATION | 0 / PASS；PDF hash 与提供 manifest 一致，未重验完整原 PDF |
| 服务器新目录与传输 | gpu-01；创建前路径不存在；24 个文件初始哈希见 `transfer_manifest.json`，Git 命令见 `commands.json` / `01_bootstrap.log` | PASS；`git rev-parse` 初始化前128是预期，`git init -b main` 与初始化后核验0 |
| 规格/来源/目录/ignore 边界 | gpu-01；完整 `python3 -c ...`、git root/branch/remote/ignore 命令见 `commands.json` / `02_verify.log` | 0 / PASS；24哈希一致，原输入未改，四目录仅 .gitkeep；未忽略源/规格检查返回1为预期 |
| Git 最终快照 | gpu-01；`git add`、`git diff --cached --check`、`git commit`、`git status`、最终 SHA 与 stat 的实际原始记录见 `.git/m0-final.log` / `.git/m0-final-commands.json` | 实际结果以日志为准；服务器没有配置作者，单次提交使用 Codex <codex@localhost>，不修改全局配置 |

首次 M0 快照 SHA：`2d608b73fe2ed7ff6af88b4be92dcf4083931557`，其提交/文件列表/退出码见 `docs/m0/03_snapshot.log`。最终证据提交内不硬写它自身的 SHA；最终 SHA 从 `git rev-parse HEAD` / `.git/m0-final.log` 查询。完整命令/退出码保存，不将文档核验称 GPU PASS。

本地最初的 Git/占位尝试已撤销，仅保留原工作包；清理最后尝试删除空 docs 目录时因系统 .DS_Store 返回1，此系统文件保留。无本地实现仓库。本地源阅读不等于服务器环境验证。

## GitHub 同步追加请求

PASS：用户创建并指定 [Zwhao0/myflash](https://github.com/Zwhao0/myflash)，分支 main；GitHub 已授予读写权限，保留用户创建时的仓库可见性。服务器开发、本地仅作 bundle/文件中转；服务器未连接 GitHub。

已同步源提交 `1296efbd4feca26cb40157e8fd392ee2d9f0cec5` 到 GitHub 提交 `19ff3e183ee4cf21b7cb2d001c2b2dcfa6709ff8`。31 文件 blob SHA 逐一一致，双方 tree SHA 为 `957c46dff4979591eafe09f3e35fbf7116f77ec0`；GitHub main 已回读确认。使用 connector 生成 GitHub 提交，因此提交 SHA/历史不同；不将文件内容一致说成提交历史相同。实际操作与核验证据见 `docs/m0/04_github_sync.json`。

真实仓库 URL 已写入用户本地 `服务器.md`，原凭证保留且未输出/上传；该私有文件在 ignore 中且不在 GitHub。上传前已逐文件检查未含私有说明中的真实凭证。当前同步记录/状态补充也从服务器提交后经中转同步，最终 head/tree 与工作树证据写入 `.git/m0-sync-final.log`，无需服务器联网。

本项目开发源始终为 gpu-01；本地工作包保持原任务输入，临时 transport mirror 不进行 FLASH 开发。最小流程和当前状态见 `docs/m0/SYNC.md`。M0 完成后停止。

## 阶段记录

| 阶段 | 状态 | 证据 / 审核 |
|---|---|---|
| M0 | PASS | 本轮文档/独立仓库实际核验；后续阶段待审核 |
| M1 | NOT_RUN | 两台 H800 只读盘点与 NCCL/DDP/MoE 基线均未运行 |
| M2 | NOT_RUN | 无 Probe/共享内存实现 |
| M3 | NOT_RUN | 无 Event 剖析/GPU 机制实验 |
| M4 | NOT_RUN | 无定位算法/fixture |
| M5 | NOT_RUN | 无 Rbeast 安装/检测器实现 |
| M6 | NOT_RUN | 无 Redis 服务/自动闭环 |
| M7 | NOT_RUN | 无训练/降频/停机/网络注入 |
| M8 | NOT_RUN | 无论文实验/性能结论 |

## 未知与下一唯一开发任务

未知：第二台部署主机、两机实际卡数/UUID/显存、指定 Python/容器、实际 CUDA/NCCL/框架版本、RDMA/NIC/GPU 拓扑、双方可达地址、资源占用与 Redis 位置。原模型配置和算法未决项按 GAPS 保留。

下一唯一开发任务：用户审核通过后 M1a，只读盘点明确目标的两台 H800，输出原始命令日志、实际版本与差异；执行范围/命令见 ENVIRONMENT_PLAN。本轮在 M0 停止。
