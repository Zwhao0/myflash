# FLASH 全新开发状态

当前阶段：M4 离线两阶段定位
当前状态：M4 PASS（已收到授权范围/确定性算法）；G04最终科学判决OPEN；完成后停止
当前任务：tasks/04_localization.md已完成明确范围；等待M4审核与截断消息补充，不进入M5。

## 权威路径、来源与改动

- 开发机：node-0，Linux 6.8.0-142-generic x86_64/glibc2.39；工作目录 `<project>`，当前 Git 分支 `codex/m4-localization`（M0初建为main）。
- 用户明确在服务器开发；该目录 SSH 只读检查时不存在，创建时再次确认不存在。不访问旧失败实现。
- 原始输入是本地工作包的文档/第三章 PDF；未将本地连接凭证、其他项目、实现或构建产物传入。输入哈希见 `docs/m0/input_hashes.json`。
- 新增 `.gitignore`、`ARCHITECTURE.md`、`SOURCE_MAP.md`、`ENVIRONMENT_PLAN.md`、四个目录 `.gitkeep` 与 `docs/m0` 证据；更新本文件与 `GAPS.md`。
- PAPER 来源仅第三章与 SPEC；UPSTREAM 来源为 GREYHOUND_MAP 提供的固定 SHA 摘要，上游正文/许可证未独立读取。ADAPTATION 为架构接口/目录/单位/隔离/计划草案；EXTENSION 不纳入基线。
- G01–G16 未关闭；追加 G17 图3-4 数值差异、G18 许可/正文待核对、G19 参数/显存口径、G20 迭代发布语义，全部 OPEN，不自行决定科学假设。

## 实际运行与证据

| 检查 | 实际机器、完整命令与原始日志 | 退出码 / 结论 |
|---|---|---|
| PDF 全30页文本与 SHA | 本地只读参考核验；完整 bundled Python 命令见 `docs/m0/00_local_reference.log`；关键完整页图像已核对，详见 VALIDATION | 0 / PASS；PDF hash 与提供 manifest 一致，未重验完整原 PDF |
| 服务器新目录与传输 | node-0；创建前路径不存在；24 个文件初始哈希见 `transfer_manifest.json`，Git 命令见 `commands.json` / `01_bootstrap.log` | PASS；`git rev-parse` 初始化前128是预期，`git init -b main` 与初始化后核验0 |
| 规格/来源/目录/ignore 边界 | node-0；完整 `python3 -c ...`、git root/branch/remote/ignore 命令见 `commands.json` / `02_verify.log` | 0 / PASS；24哈希一致，原输入未改，四目录仅 .gitkeep；未忽略源/规格检查返回1为预期 |
| Git 最终快照 | node-0；`git add`、`git diff --cached --check`、`git commit`、`git status`、最终 SHA 与 stat 的实际原始记录见 `.git/m0-final.log` / `.git/m0-final-commands.json` | 实际结果以日志为准；服务器没有配置作者，单次提交使用 Codex <codex@localhost>，不修改全局配置 |

首次 M0 快照 SHA：`2d608b73fe2ed7ff6af88b4be92dcf4083931557`，其提交/文件列表/退出码见 `docs/m0/03_snapshot.log`。最终证据提交内不硬写它自身的 SHA；最终 SHA 从 `git rev-parse HEAD` / `.git/m0-final.log` 查询。完整命令/退出码保存，不将文档核验称 GPU PASS。

本地最初的 Git/占位尝试已撤销，仅保留原工作包；清理最后尝试删除空 docs 目录时因系统 .DS_Store 返回1，此系统文件保留。无本地实现仓库。本地源阅读不等于服务器环境验证。

## GitHub 同步追加请求

PASS：用户创建并指定 [Zwhao0/myflash](https://github.com/Zwhao0/myflash)，分支 main；GitHub 已授予读写权限，保留用户创建时的仓库可见性。服务器开发、本地仅作 bundle/文件中转；服务器未连接 GitHub。

已同步源提交 `1296efbd4feca26cb40157e8fd392ee2d9f0cec5` 到 GitHub 提交 `19ff3e183ee4cf21b7cb2d001c2b2dcfa6709ff8`。31 文件 blob SHA 逐一一致，双方 tree SHA 为 `957c46dff4979591eafe09f3e35fbf7116f77ec0`；GitHub main 已回读确认。使用 connector 生成 GitHub 提交，因此提交 SHA/历史不同；不将文件内容一致说成提交历史相同。实际操作与核验证据见 `docs/m0/04_github_sync.json`。

真实仓库 URL 已写入用户本地 `服务器.md`，原凭证保留且未输出/上传；该私有文件在 ignore 中且不在 GitHub。上传前已逐文件检查未含私有说明中的真实凭证。当前同步记录/状态补充也从服务器提交后经中转同步，最终 head/tree 与工作树证据写入 `.git/m0-sync-final.log`，无需服务器联网。

本项目开发源始终为 node-0；本地工作包保持原任务输入，临时 transport mirror 不进行 FLASH 开发。最小流程和当前状态见 `docs/m0/SYNC.md`。M0 完成后停止。

## 阶段记录

| 阶段 | 状态 | 证据 / 审核 |
|---|---|---|
| M0 | PASS | 本轮文档/独立仓库实际核验；后续阶段待审核 |
| M1 | PASS（核心） | M1a–M1d实测通过；M1e准备BLOCKED、MoE NOT_RUN，详见docs/m1 |
| M2 | PASS（已支持范围） | Probe/Reader构建、CPU11项、单机/跨机/16rank/DDP/Group实测，docs/m2 |
| M3 | PASS（已验证范围） | 手动两轮、Event、A–F机制/16rank/Monitor回归，docs/m3 |
| M4 | PASS（确定性/明确范围） | docs/m4；G04完整判决OPEN，未收到附加标准NOT_RUN |
| M5 | NOT_RUN | 无 Rbeast 安装/检测器实现 |
| M6 | NOT_RUN | 无 Redis 服务/自动闭环 |
| M7 | NOT_RUN | 无训练/降频/停机/网络注入 |
| M8 | NOT_RUN | 无论文实验/性能结论 |

## 当前未知与下一唯一任务

两机已确认各8张H800、运行时CUDA12.8/NCCL2.27.3及实际RoCE通信。Megatron/TE/native训练入口、可用授权容器、Redis实例位置仍缺失/未核验；G01–G20科学未知保持OPEN。M1小模型DDP不能填补论文训练配置。

下一唯一任务：用户审核M4的docs/m4及源码，并补充截断M4d要求；M3已审核，M5未开始。MoE仍不在当前批准范围。

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
实测node-0/node-1各8×H800，所有PASS的完整命令、退出码、原始日志见docs/m2/VALIDATION.md与RESULTS.md及各run control/manifest。CPU11项和4线程mock1205事件exit0/0；单机native/Probe、单机Group/lifecycle、两机各1rank、16rank AR、16rank20步DDP均训练/Reader/验证/清理0；最终事件238、72、118/117、955/951、1659/1665，全部支持范围内记录完整、丢失0；跨机hash与全rank集合/实际PID、22703/12080库版本匹配。DDP同步误差0、参数更新>0；M1测试/launcher源文件未改、原无Probe保护仍有效。
最终运行末显存984/1040/1058MiB，保留1536目标/2048运行末检查及启动前3072余量；不是瞬时硬限制。各run在同一测试会话真实unlink2/1/8个当前run对象；postflight两节点58/42个本轮rank PID均已退出、本次GPU PID/shm剩余0。未降频、OOM、拥塞、杀其他作业或广泛清理。
支持范围：阻塞InitRank/Config（含Group后延迟mapping）、常用collectives、Group/lifecycle；Split新组跨进程身份UNRESOLVED，异步/其他init身份UNSUPPORTED，未测/未包装API见RESULTS。G06/G07只在已验证范围采用明确ADAPTATION，复杂路径仍OPEN。不把comm_ptr/Group/训练组混用。没有Probe CUDAEvent/额外GPU同步、Redis、BOCD、异常检测/定位或恢复。
保留编译两次exit1、Group/Bcast验证器历史exit1、早期清理失败与DDP03 SSH255/NOT_RUN；未追改失败、缩减M1数值/训练断言或改阈值。两处验证器错误按真实API路径更正，并由更严格/独立测试验收；全部新run证据保留服务器runs，GitHub仅脱敏源码/文档。报告为功能验收，不是论文正式性能结果。
M2完成即停。下一唯一任务：用户审核M2；M3及以后未开始。GitHub审核分支与最终tree回执在.git/m2-final-sync.json记录，完成发布后追加链接。

GitHub审核分支已发布：codex/m2-monitor；Draft PR https://github.com/Zwhao0/myflash/pull/1 。首份脱敏交付source 4f6ed9610b78e0b1aa627536f80bcb6fae7d2ec9 → GitHub 4eb3cd71957298877dcdd0109c90ab129745caaf，25个变化blob及完整tree 3ea4153194c63cd1248f0ebd279e8eba95185890 完全匹配、分支回读成功，main未改动。公开首轮回执docs/m2/SYNC.json；本次状态/回执追加的最终双方SHA/tree在.git/m2-final-sync.json记录。M2结束，不进入M3。


## M3最终结果与停止（2026-10-10）
用户审核M2后一次授权完整M3a–M3d，内部连续推进；没有进入M4。PR1已经merged，服务器64badbf的tree79a1254与PR最新f8316cf对齐；从已审核M2创建codex/m3-profile，main与M2提交未覆盖。权威源node-0:<project>；node-1只执行同步镜像，Git提交历史不同，不冒称两机SHA一样。
实现/提交：ccded07手动控制/ABI2/Event/恢复/负载；14a5c70补强失败内层GroupEnd无效化和部分rank校验；最终辅助验证/文档/白名单提交用git log和同步回执查询。diff为native/ring.*、native/probe.cpp、flash/reader.py，新增tests/m3_*、scripts/m3_*、tasks/03_profile与docs/m3，更新GAPS/本文件；M1及M2基线入口不改。PAPER/UPSTREAM/ADAPTATION/EXTENSION出处见SOURCES，没有GreyHound源码复用或旧失败实现访问，无系统软件变更。
实际设备两台各8×H800，PyTorch2.8+cu128/CUDA12080/NCCL22703；完整命令/退出/原始日志/断言在docs/m3/VALIDATION与每run服务器manifest。手动两轮0→1→0、非Group真实路径、CUDA Event时间和无效null、Reader尾中断/中部损坏/已ACK丢失拒绝通过；CPU六命令全0（suite053356468174Z）。单机/跨RoCE分别260有效时延，CPU20ms与同依赖链GPU前置计算两个目标rank均观察到短Event通信区间；G09只在该边界受支持，仍OPEN。
最新Group02：80有效成员/48有效scope；32多stream成员UNSUPPORTED/null，验证PASS不称该全窗口完整Profile。最新16rank AR02：1904事件、192有效Profile，原25次数值/SUM136；DDP02：3299事件、320有效Profile、各20step/676参数/更新>0/同步误差0。全部正常采集loss0，排空/清理0；Monitor单机/跨机/16rank/DDP/lifecycle、native2rank及原M2 CPU回归全部通过。真实不支持/未测API、stream、Graph、异步行为见RESULTS/VALIDATION。
最终两节点Probe SHA256 c9f6987d35d2bff32aed205c2bac0741a41fe6804861b2e82450f4369c541e77与核心源hash完全相同；两节点检查62/50个本轮rank PID、剩余进程/GPU PID/shm均0；单run<=300s、预检3072MiB余量、1536目标/2048运行末界限，最高约1058MiB。Profile的stop等待独立统计，AR02全rank之和35.651ms/DDP02 122.267ms，不当墙钟开销或无开销结论。
首轮header重载build exit1、node-1 postflight因源Git对象未导入exit1/底层128、一次GitHub连接器查询传输失败均保留。postflight改为审批源blob hash比较，范围不变、两节点新run/日志exit0。原敏感实验日志只在服务器，公开520机制原始样本/完整分布与其它Profile成员数据均白名单导出、不改原时延/标签。
下一唯一任务：用户审核M3交付及G09适用边界；未经明确通过不进入M4。未授权/未执行降频、OOM、网络拥塞、其它作业终止、Redis、BOCD、自动检测/两阶段定位或训练恢复。GitHub审核分支/PR及完整tree回读结果以docs/m3/SYNC.json或后续回执为准。

M3审核发布已完成：Draft PR https://github.com/Zwhao0/myflash/pull/2 ，分支codex/m3-profile。从权威node-0源831c53e7e023302e30ea1267f44db7c357f6e608同步到GitHub eebe891d46f107bc3e978f7b7c14443774680c0e；41个变化blob及完整tree c4ce7dd1b5740e10e7c30d2966279662064570a8逐SHA完全相同，PR分支回读PASS，main保持672e82aa且M3未合并。公开回执docs/m3/SYNC.json；本回执/状态后续仅文档提交的最终双方SHA/tree在.git/m3-final-sync.json保存。收尾联合验证与diff/commit命令、退出码、日志见服务器runs/m3-final-public/final-manifest.json，均0。M3结束，停止等待审核；M4 NOT_RUN。

## M4执行中
从PR2最新已验证30ca740的等树服务器a1ed7e2建立codex/m4-localization；main不缺M3地推进，也未合并PR2。node-0为开发源。
M4a输入、M4b确定两阶段/双权重/CV敏感性、M4c首50手算fixture PASS；M4d 520机制样本与公开CSV/raw逐字段一致回放PASS（runs/m4-replay-03，exit0）。错误适配尝试runs/m4-replay-01/02保留：CSV字符串转换、DDP每epoch计数假设错误，不改原M3数据/科学阈值。
真实M3 normal样本也输出候选，不掩饰误报；详见最终docs/m4。有限正常4rank五通信组准备中，300s、M1获准UUID前4、每进程<=2GiB末检查/启动>=3GiB余量、仅当前run结束和精确shm清理。

## M4最终结果与停止（2026-10-10）
任务04，用户审核M3后完整授权；从未合并PR2最新30ca740的等树服务器a1ed7e2建立codex/m4-localization，不从缺M3的main开发。初始M4源码提交d8f4867，后续交付SHA/tree见SYNC/最终回执；diff仅新flash/profile_input.py/localization.py、scripts/tests/m4_*、固定fixtures/docs/m4、tasks04与STATUS/GAPS/ARCHITECTURE/PLAN。native/Reader与M1–M3原源/证据字节不变。
PAPER最大组/最小rank/CV0.1与独立式3-1/3-2；UPSTREAM官方API与安装NCCL2.27.3 header（dtype0..11）；ADAPTATION数据验证/共享scope/双权重与std/CLI/评估隔离；EXTENSION合成零timing定义与有限人工并行组。精确出处见docs/m4/SOURCES。
实际node-0，65固定CPU fixtures全部PASS；每项input/手算expect/actual/exit和日志明确保存（tests/m4_cases、docs/m4/fixtures、fixture-validation.json，runs/m4-offline-final-03）。完整命令python3 tests/m4_offline.py --output runs/m4-offline-final-03 exit0，原log runs/m4-final-check-03/0.log。不是GPU实验。
python3 scripts/m4_replay.py --output runs/m4-replay-final-03 exit0，log同目录1.log；520机制数据全保留，192AR/320DDP与两个含unsupported的Group窗口（拒绝）回放；raw/公开CSV一致。两采样口径16/16迟到窗口排序匹配，但normal3/4产生临时候选；不能宣称最终精确率/召回率或自动诊断成功。
真实node-0四H800，python3 scripts/m4_run_real.py --run-id m4-multigroup-normal-01 --master-port 29911，各launch/verify/cleanup exit0，完整展开命令/日志runs/m4-multigroup-normal-01/control.json和command-0..2.log；NCCL22703/CUDA12080/Torch2.8+cu128、300s/3GiB预余量/2GiB末检查，实际978–980MiB。五同标签/跨标签通信组、十local实例、两epoch各60有效记录；两轮正常负载的max组/min rank均rank3，真值空，保留临时误报。没有新故障注入或真实MoE。
最终只读python3 scripts/m4_verify_real.py --run-id m4-multigroup-normal-01 exit0，runs/m4-final-check-03/2.log；Reader/source preservation和三个原M3 CPU/公开证据回归均0，runs/m4-final-check-01/3..5.log。postflight本run四PID/对应GPU PID/shm残留全0，公开postflight.json。原失败回放01/02与中转错误保留，不暗改数据/阈值。
G04权重/20%/std与部分score参照OPEN；候选PROVISIONAL_CANDIDATE/分歧AMBIGUOUS_SPEC，final_fault_ranks为空。M4d消息后半截断未收到，额外验收条件NOT_RUN；新跨机多组/延迟注入多组/混合comm真实Group/Float8真实GPU/完整最终判决NOT_RUN。BOCD/Redis/自动闭环/恢复/MoE/M5未开发未启动。
下一唯一任务：审核本M4明确交付及G04选项，并补充截断M4d后半；本轮到此停止，不自动推进下一关。审核PR/服务器与GitHub内容树匹配回执待本轮同步完成追加。

M4审核发布完成：Draft PR https://github.com/Zwhao0/myflash/pull/4 ，base=codex/m3-profile（PR2仍未合并），head=codex/m4-localization。服务器源124405ce4d3e3b72dfe96b93d2c532145eb096c4 → GitHub f2b1c54dcbd32db65f06cf10365611f7f9b7cdfc，327变化文件blob及完整tree d9348a2d80c98dca08efa0851150fbbfbe026de5一致，main未改。整包/分批inline tree两次连接器传输错误保留；逐blob上传204个独立对象全部SHA核验后组装完整tree成功，不影响CPU/GPU结果。首次公开中转取数因Expect缓冲区默认太小失败，改显式缓冲后完整payload/每blob hash校验成功；未下载原始敏感数据。docs/m4/SYNC.json记录此次审核快照，文档回执追加的最后双方head/tree写.git/m4-final-sync.json。M4明确范围完成且停止；G04完整判决OPEN，截断附加标准未验收，M5不启动。

M4最终回读补充：执行期间用户的PR2已经合并，main=2fcc45724e8bbfde800539beeae45febddd7e572、tree177745dd与M4起点完全相同；本轮没有更新main。PR4由创建时的codex/m3-profile retarget为main，只调整审核基线，源/实验不变。文档追加提交同步后最终服务器/GitHub head/tree记录.git/m4-final-sync.json。


## P1 隐私审查与可审核修复（2026-10-10）
任务：tasks/04_privacy.md。用户要求处理公开仓库隐私；基线 GitHub main 2fcc45724e8bbfde800539beeae45febddd7e572，11个不同提交/4分支已扫描；既有安全分支与main同SHA。可审核 diff 将身份文档/M0公开日志脱敏，盘点脚本从自身路径确定根目录，补充ignore/隐私检查/5项合成测试/CI与docs/privacy。出处ADAPTATION用户请求与AGENTS日志约束；UPSTREAM GitHub清理文档和MIT checkout固定SHA，详见AUDIT。没有科学机制、训练配置、数值或样本标签变更。
实际设备：本地macOS Darwin25.6.0 arm64，Python3.9.6；没有访问实验服务器/执行GPU测试/安装软件。完整命令、退出码、原始本地日志路径在docs/privacy/validation.json，cwd为审查clone；日志相对该clone保存在../logs/。文本检查0、5项合成测试0、数据/核心保留检查0、既有M3公开证据验证0、git diff --cached --check 0。preservation.json保存逐文件SHA256；这是本地文件验证，不是新增H800 PASS。
历史扫描exit1/FAIL：旧路径/机器名与M0真实私网地址仍可访问；只是检查器正确检出，不能称历史清理PASS。当前文本的已测隐私规则PASS；PDF及全文摘录公开再分发授权PENDING、项目LICENSE未选定；专用分支保护API403/BLOCKED；随后通用branch API确认main protected=false/无必需checks，Secret scanning配置UNKNOWN。没有强推/历史改写/可见性变更，没有合并main。GitHub上传SHA/tree与Draft PR结果以本轮回执为准，不覆盖旧同步哈希；旧日志/hash均标为历史快照或脱敏副本。
下一唯一任务：审核P1改动及材料授权，决定是否明确批准独立的全refs历史清理；不进入M4。


## P1-C1 PR3冲突解决（2026-10-10）
用户反馈有冲突；仅把已合并M4的main 01c96abeab2be25ff38176357a19fb53f18356f8合入P1安全分支，保留双父历史，不强推。冲突为STATUS两块，保留M4当前状态/完整阶段记录及P1历史。ARCHITECTURE/GAPS/PLAN自动合并并保留M4内容。ADAPTATION来源是用户冲突修复请求；新增文档身份字段按既定别名脱敏，M4 replay只改机器名注释，AST与main一致。
10份人工NDJSON按精确路径/哈希登记，仍接受所有秘密/身份文本规则；317份M4代码/fixtures/输入期望/实验数据与main逐字相同，完整范围/哈希见docs/privacy/conflict-preservation.json。其余M4改动只含身份元数据/一行注释，原断言/失败/样本/时延/标签保持。原P1快照JSON保留历史口径。
本地macOS Darwin25.6.0 arm64/Python3.9.6：6隐私测试、当前树检查、原60文件保留、M3公开证据、65M4 fixtures、main M4保留/AST/PLAN一致与diff两检查均exit0；完整命令/退出码/原始日志路径见docs/privacy/conflict-validation.json（../logs/conflict-01/00..07.log）。第一次65fixtures日志runs/p1-conflict-m4-fixtures保留。一次状态追加的Python编码错误未写入成功，保留本地错误日志并用显式UTF8重试，未更改测试断言。没有新GPU实验/服务器回放/科学选择。最终commit/tree/远端CI以收尾回执为准。
下一唯一任务：用户审核已解冲突的PR3；不代合并main，不推进M5；旧历史与材料授权仍待另行处理。
