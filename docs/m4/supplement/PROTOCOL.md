# 固定协议、来源与证据入口

EXTENSION：人工DP/TP标签的direct NCCL小负载，CPU20ms迟到只用于条件化定位；非真实Megatron并行组/训练。核心A–E各两次独立启动，每启动epoch1/2；五组跟进A–E各一次。所有run使用不含真值的w序号。3次Monitor warmup（目标仍sleep20ms）→10次Profile全部计入→1次Monitor无迟到恢复，每epoch固定相同策略。控制状态0→1→0→1→0；不使用结果筛样本。

ADAPTATION：复用M4主线01c96abe:tests/m4_multigroup.py:main的阻塞InitRankConfig、unique-ID SHA256、数值检查与Profile请求；新tests/m4_late.py添加固定布局/CPU迟到/host审计。复制01c96abe:scripts/m4_launch.py:main/group_members到独立m4_late_launch入口，仅改负载与参数，安全检查原样保留；原文件不改。脚本标准库/本项目代码，无GreyHound源码/算法复用。

每collective先在所属stream生成输入并同步；全部4rank在CPU TCPStore ready屏障集结，只有target group/rank在该屏障返回后、NCCL调用前sleep20ms；NCCL完成后同步stream、校验SUM、再4rank done屏障。固定A→B（五组继续TP02→TP13→A2）。下一组不得在前组全部完成前进入；同机器monotonic_ns的入调用/完成时间验证无交叉。rank的ready返回并非同一时刻，entry_skew_ms全部公开；未将CPU耗时冒充Event时延。独立evaluator持有注入时间/目标；定位CLI只接收schema1测量、身份/成员/标签与完整性声明。

PAPER：SPEC S4–S6，第三章§3.2.3 pp27–31 / §3.3.2 p34 / 式3-1/3-2 pp41–42。原M4 flash/localization.py:analyze/rank_analysis/CV_THRESHOLD 与profile_input.py:read_records/validate_bundle全部未改；max-group/min-rank/CV0.1、双std/双权重、20%未启用的状态原样保留。

UPSTREAM：[NCCL communicator APIs](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/api/comms.html)、[collective APIs](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/api/colls.html)、[PyTorch2.8 TCPStore](https://docs.pytorch.org/docs/2.8/distributed.html#torch.distributed.TCPStore)。动态NCCL文档本次显示2.32.3，不能据此声称目标库升级；目标实测加载2.27.3与既有安装header/ABI、CUDA12.8，ncclGetUniqueId/阻塞Config/AllReduce正确性实测通过。既有M3 Event Probe二进制SHA不变，见validation.json。

安全：仅M1获准前4张GPU，启动前3072MiB余量；NCCL_BUFFSIZE1MiB、MIN_CTAS=MAX_CTAS=1、NVLS_ENABLE=0、OMP1、cuBLAS:16:8；1536MiB记录目标、2048MiB运行末检查，并非瞬时总显存硬上限。每测试300秒外部上限、训练主进程预算240秒内、无重启；超时只结束本次新session的PGID。即使验证失败也尝试原m2_cleanup精确run/node的closed/drained对象清理，并检查本次PID/GPU PID/shm；不存在广泛清理或其它作业终止。

## 实际命令/退出码（node-0项目根）

```sh
python3 tests/m4_offline.py --output runs/m4-supplement-fixtures-01
python3 scripts/m4_late_run.py --suite-id m4-late-core-01 --layout core
python3 scripts/m4_late_run.py --suite-id m4-late-five-01 --layout five --core-suite m4-late-core-01
python3 scripts/m4_late_export.py --core m4-late-core-01 --five m4-late-five-01
```

65fixtures命令exit0，原日志runs/m4-supplement-access/fixtures.log/precheck.json。核心suite外层异步启动未单独捕获OS退出码，不以其终态推测退出码；10个run内launch/verify/cleanup各实际exit0。五组suite外层实际exit0，five-suite-exit.json；5个run内三个命令均exit0。导出01/02/03实际exit0，export-command-*.json/export-*.log；02补充各未选组rank CV/score，03接入实验期间已合并P1的main，原测量未重跑、未筛选或修改。

展开UUID/路径/端口的完整命令与每个子命令退出码只在服务器runs/m4-late-{core,five}-01-wNN/control.json及command-{0,1,2}.log；node-0/manifest.json保存训练完整命令/source SHA/diff/hashes/环境/binary hash/timeout，torchrun.log、NCCL日志、reader.log、probe/*.ndjson、rank-*.json、evaluator-truth-rank-*.json、预检/占用日志与cleanup.json保留。各analysis-epoch{1,2}/input.json/prediction.json/analysis.log/evaluator.json保存独立CLI与evaluator结果；postflight.json/postflight-{0,1}.log保存只读清理复核。

服务器原始证据目录：runs/m4-late-core-01-w01..w10，runs/m4-late-five-01-w01..w05，runs/m4-supplement-access，runs/m4-supplement-fixtures-01。实际机器/拓扑/版本命令和输出仅在access/inventory*.json/log。公开validation.json保留原raw文件SHA与计数，可与服务器核验；results.json含逐窗全部max/CV/score/候选/独立评价；samples.json保留全部1800条测量的精确us分布与可重放schema1输入。

初始bundle传输因参数长度exit1，改binary scp exit0；保留transport-failures.json。未发生真实GPU运行或定位失败，正常误报与五组冲突全部保留；历史失败不删。GitHub仅新增文件与STATUS追加，不携带原始日志、真实地址/UUID/PID/服务器路径。最新main的P1隐私保护保留；旧历史隐私清理不属于本补充任务。
