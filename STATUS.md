# FLASH 全新开发状态

当前阶段：M2 透明 NCCL Probe / Monitor 共享内存
当前状态：M2 PASS（已支持范围），本轮完成并停止；M3 NOT_RUN
当前任务：tasks/02_monitor.md 已完成；等待M2审核，不自动推进M3。

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
| M1 | PASS（核心） | M1a–M1d实测通过；M1e准备BLOCKED、MoE NOT_RUN，详见docs/m1 |
| M2 | PASS（已支持范围） | Probe/Reader构建、CPU11项、单机/跨机/16rank/DDP/Group实测，docs/m2 |
| M3 | NOT_RUN | 无 Event 剖析/GPU 机制实验 |
| M4 | NOT_RUN | 无定位算法/fixture |
| M5 | NOT_RUN | 无 Rbeast 安装/检测器实现 |
| M6 | NOT_RUN | 无 Redis 服务/自动闭环 |
| M7 | NOT_RUN | 无训练/降频/停机/网络注入 |
| M8 | NOT_RUN | 无论文实验/性能结论 |

## 当前未知与下一唯一任务

两机已确认各8张H800、运行时CUDA12.8/NCCL2.27.3及实际RoCE通信。Megatron/TE/native训练入口、可用授权容器、Redis实例位置仍缺失/未核验；G01–G20科学未知保持OPEN。M1小模型DDP不能填补论文训练配置。

下一唯一任务：用户审核已完成M2的docs/m2及源码。M3手动剖析/机制验证未授权、未执行；MoE准备仍需独立授权。

## M1 2026-10-10 早期执行记录（历史）

M0 已由用户审核；完整 M1a–M1e 已授权，无需逐子任务审批。追加允许共享 GPU 低显存小测试，以及仅项目隔离环境 torch==2.8.0 CUDA12.8 wheel/固定依赖。两机均已连接并只读盘点，8×H800/81559MiB、驱动580.178.04、Python3.12.3；宿主 Python 无 torch，Docker权限不足，两机无外网（用户确认）。项目 venv 创建成功，直接在线安装失败；现经本地配置代理与公开 PyPI 镜像下载 Linux wheel，SHA256锁定后离线传输，不升级系统组件。

M1a硬件/网络盘点完成，实际 CUDA/NCCL 加载版本待基线；M1b–M1d NOT_RUN，MoE 尚未验证。脚本来源/资源/断言说明见 docs/m1/SOURCES.md；原始证据仅服务器 runs/。本地工作包不作为开发源，未访问旧失败实现。

## M1 最终结果与停止

完整M1a–M1e一次授权；共享GPU小测试与项目隔离依赖获准。用户最后明确允许略超1536MiB、不因少量显存超出阻碍开发；当前1536MiB为记录目标，2048MiB运行末保护上限、启动前≥3072MiB余量。最终配置NCCL_BUFFSIZE1MiB、MIN_CTAS=MAX_CTAS=1、NVLS_ENABLE=0、cuBLAS :16:8；没有系统升级、FLASH逻辑、故障注入、全局清理或访问旧实现。

M1a PASS：两机8×H800/81559MiB、Ubuntu24.04.4、驱动580.178.04、Python3.12.3；kernel差异与host库差异见ENVIRONMENT。离线25包安装及pip check两机均0，实测映射项目libcudart12.8/libnccl2.27.3，与系统driver区别记录；实际跨机NET/IB/RoCE有通道日志，不靠ping推断。

M1b PASS：baseline-02退出0，2rank全部数值正确。M1c PASS：baseline-01/02两次两机退出0。M1d PASS：AllReduce-01..04均16rank数值正确SUM136、每rank25次；最终配置03/04独立启动均0。DDP-03/04两次16rank各20step退出0，loss有限、参数变化0.02080027759、同步误差0；最终每进程1040/1058MiB，PG与本次进程正常释放，postflight两机检查0。

历史FAIL保留：M1b-01旧1024MiB预算超出；DDP-01旧1536MiB预算超出；DDP-02记录两份20步rank结果1542MiB超预算，其他rank被本次torchrun结束、结果不完整，不能称16rank PASS。直接在线下载/安装失败及一个早期包装器未写完整stdout的缺失也保留。用户新授权不追改历史状态；新run重新验证。

M1e环境准备BLOCKED、原生MoE NOT_RUN：已核验宿主/项目入口缺Megatron/TE/native pretrain，无nvcc、Docker权限不足；未安装复杂框架。只有DDP DP=[0..15]，无真实Megatron TP/PP/EP组；Redis连接NOT_RUN。

交付：docs/m1/ENVIRONMENT.md、RESULTS.md、VALIDATION.md、SOURCES.md、requirements.lock、evidence.json；scripts/m1_inventory.py、m1_install_offline.py、m1_launch.py、m1_summarize.py与tests/m1_baseline.py。PAPER/UPSTREAM/ADAPTATION/EXTENSION追溯见SOURCES，未复用GreyHound代码。完整命令/退出/UUID/原始NCCL日志只留两机runs/<run_id>，目录清单与验证依据见VALIDATION；公开evidence仅白名单数字/源码哈希。

GPU最终实测源快照ed36c024a31f6343277f5330e114f0d6439d86f8；双机launcher/test哈希一致。文档/证据最终提交由git rev-parse HEAD查询；本轮GitHub同步通过本地中转，从服务器提交树导出，非force/expected_sha保护main；同步回执将在.git/m1-sync-final.json记录双方提交、完整tree/blob一致性，不把不同提交历史称相同。同步状态在下方收尾回执追加，不向公开仓库上传完整机器信息。

本轮M1完成即停，M2–M8均NOT_RUN。

收尾校验PASS：runs/m1-final-validation-20261010T040704Z，5项退出0及证据断言通过；040640Z检查器路径错误的exit128已保留并更正聚合状态，未追改GPU结果。M0两份旧文档的服务器地址已从当前文件移除，备份只留服务器；既有公开Git历史未重写，历史隐私边界需另行处理。

GitHub同步PASS：服务器源c50e53a8e8e70ae83c54b14841b69b397b18e001 → GitHub 5899c098345a4b96c75970db8a18a6ff7ce86930，全部文件tree 734ba0c4244064c4fad632c0d21eb06d5784fde1完全匹配，17个变化blob逐一核验、main回读成功。公开回执docs/m1/SYNC.json；回执与STATUS这次追加亦从服务器提交后同步，最终双方commit/tree及工作树检查保存在.git/m1-sync-final.json。没有force/历史重写，无原始日志/完整机器数据/凭证上传。M1停止，M2未运行。


## M2 执行开始（2026-10-10）
用户完整批准M2a–M2d；后续明确继续解决编译问题，不因缺headers停工。首两次host编译失败分别缺crt/host_config.h与nv/target，原日志runs/m2a-compile-20261010保留。已有M1 Triton提供CUDA12.8 crt headers；用户续令下仅解包官方CCCL12.8.90 wheel到本项目.build-deps-m2，SHA256核对PyPI；无系统升级、未改变M1运行库。
当前修改范围native/flash/新增m2脚本测试、docs/m2、tasks/02_monitor/.gitignore/GAPS/STATUS。PAPER/UPSTREAM/ADAPTATION边界与ABI、锁/ACK协议见docs/m2/DESIGN.md；没有GreyHound源码复用、CUDAEvent/额外GPU同步/Redis/检测/定位。
CPU9项PASS（包括未ACK重启与持锁进程死亡poison），单机native与Probe数值断言退出0；m2b-probe-01验证器误要求PyTorch AllReduce必须调用Group而退出1，保留FAIL及原日志，不追改。该错误由专门生命周期/Group测试覆盖相同要求，并新run m2b-probe-02 PASS；m2f-lifecycle-01 InitRank/Config、嵌套Group及Split明示UNRESOLVED数值测试PASS。后续仍在获准M2范围完成跨机/16rank/DDP与完整证据；不进入M3。


## M2 最终结果与停止（2026-10-10）
用户完整授权M2并要求解决编译问题；仅项目隔离CCCL12.8.90 headers补齐，现有g++13.3/ld2.42成功，M1运行库与系统栈未改。PAPER/UPSTREAM/ADAPTATION/EXTENSION来源见docs/m2/SOURCES.md；从零独立实现，没有GreyHound代码复用或访问旧失败系统。
最终GPU代码快照e45f90e455b5abb17914005f92824add519c8f64，双节点Probe哈希5e9d3cd786864c7fe4785504c2004a2c9fd18c563dd32ade4d6da95924b79cad完全一致。修改：native/ring.hpp/ring.cpp/probe.cpp；flash/reader.py；新增m2 build/launch/run/verify/cleanup脚本与ring/mock/lifecycle测试；tasks/02_monitor、docs/m2四文档/evidence、.gitignore、GAPS/ARCHITECTURE/本文件。最终提交/diff从git log与本轮收尾回执查，不自引用未来SHA。
实测gpu-01/gpu-02各8×H800，所有PASS的完整命令、退出码、原始日志见docs/m2/VALIDATION.md与RESULTS.md及各run control/manifest。CPU11项和4线程mock1205事件exit0/0；单机native/Probe、单机Group/lifecycle、两机各1rank、16rank AR、16rank20步DDP均训练/Reader/验证/清理0；最终事件238、72、118/117、955/951、1659/1665，全部支持范围内记录完整、丢失0；跨机hash与全rank集合/实际PID、22703/12080库版本匹配。DDP同步误差0、参数更新>0；M1测试/launcher源文件未改、原无Probe保护仍有效。
最终运行末显存984/1040/1058MiB，保留1536目标/2048运行末检查及启动前3072余量；不是瞬时硬限制。各run在同一测试会话真实unlink2/1/8个当前run对象；postflight两节点58/42个本轮rank PID均已退出、本次GPU PID/shm剩余0。未降频、OOM、拥塞、杀其他作业或广泛清理。
支持范围：阻塞InitRank/Config（含Group后延迟mapping）、常用collectives、Group/lifecycle；Split新组跨进程身份UNRESOLVED，异步/其他init身份UNSUPPORTED，未测/未包装API见RESULTS。G06/G07只在已验证范围采用明确ADAPTATION，复杂路径仍OPEN。不把comm_ptr/Group/训练组混用。没有Probe CUDAEvent/额外GPU同步、Redis、BOCD、异常检测/定位或恢复。
保留编译两次exit1、Group/Bcast验证器历史exit1、早期清理失败与DDP03 SSH255/NOT_RUN；未追改失败、缩减M1数值/训练断言或改阈值。两处验证器错误按真实API路径更正，并由更严格/独立测试验收；全部新run证据保留服务器runs，GitHub仅脱敏源码/文档。报告为功能验收，不是论文正式性能结果。
M2完成即停。下一唯一任务：用户审核M2；M3及以后未开始。GitHub审核分支与最终tree回执在.git/m2-final-sync.json记录，完成发布后追加链接。

GitHub审核分支已发布：codex/m2-monitor；Draft PR https://github.com/Zwhao0/myflash/pull/1 。首份脱敏交付source 4f6ed9610b78e0b1aa627536f80bcb6fae7d2ec9 → GitHub 4eb3cd71957298877dcdd0109c90ab129745caaf，25个变化blob及完整tree 3ea4153194c63cd1248f0ebd279e8eba95185890 完全匹配、分支回读成功，main未改动。公开首轮回执docs/m2/SYNC.json；本次状态/回执追加的最终双方SHA/tree在.git/m2-final-sync.json记录。M2结束，不进入M3。
