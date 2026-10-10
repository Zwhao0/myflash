# M1 执行与验收证据

2026-10-10，实际设备gpu-01/gpu-02。项目根均为 `/home/campus/zhangweihao/myflash`；gpu-01为权威开发源，gpu-02为当前项目执行镜像。下述公开命令以占位符替代真实UUID、地址；**实际完整命令、环境、时间、代码SHA/diff/源码哈希、退出码、GPU映射在每run的control/manifest中**，原始记录只在服务器，本机CPU检查不能替代GPU PASS。

## 已实际执行的入口及日志

| 检查 | gpu-01原始目录 | gpu-02原始目录 | 退出/依据 |
|---|---|---|---|
| 初始只读inventory | runs/m1a-20261010T031757Z | runs/m1a-20261010T031855Z | manifest各命令/00..23.log；nvcc缺失127，其余正常；host torch缺失独立记录 |
| 项目环境后inventory | runs/m1a-20261010T034421Z | runs/m1a-20261010T034423Z | Python stack查询0；库maps/version与硬件/网络原始输出 |
| Docker账号访问 | runs/m1-env-20261010T031840Z | runs/m1-env-20261010T031842Z | exit1权限拒绝，不能称容器内框架检查通过 |
| 宿主包/库补查 | runs/m1-host-libs-20261010T033211Z | runs/m1-host-libs-20261010T033214Z | dpkg-query1，无所列包；/usr/local/cuda实际不存在；gpu02 ldconfig库项版本未知 |
| 直接在线安装 | runs/m1-env-prepare-20261010T032059Z | runs/m1-env-prepare-20261010T032102Z | venv0、在线pip1；未改变系统 |
| 限时下载复查 | runs/m1-download-recheck-20261010T032615Z | runs/m1-download-recheck-20261010T032617Z | timeout包装exit124；保留失败与早期包装器recovery-note |
| 离线安装 | runs/m1-offline-install-20261010T034129Z | runs/m1-offline-install-20261010T034210Z | 校验/安装/pip check三项均0；manifest、pip-report、逐命令日志 |
| M1e项目入口检查 | runs/m1e-project-20261010T034451Z | runs/m1e-project-20261010T034453Z | result.json：包缺失，BLOCKED；native_moe_run NOT_RUN，parallel_states=null |
| 结束资源/源码核验 | runs/m1-postflight-20261010T040046Z | runs/m1-postflight-20261010T040048Z | 4项exit0；本次GPU PID不存在，py_compile与git diff --check成功 |

环境采集实际入口：`python3 scripts/m1_inventory.py --peer <verified-peer>`，安装后使用 `.venv-m1/bin/python scripts/m1_inventory.py --peer <verified-peer>`；完整stack命令与每个探测命令均在manifest。离线安装入口：`python3 scripts/m1_install_offline.py --approved`，依赖锁/manifest来自已批准25包wheel depot。M1e host检查另在m1e-host-20261010T033340Z / 033342Z；原生框架不存在的scope仅为本账号已核验入口。

## 可重复执行的GPU命令模板

首先确定获准GPU UUID与实际peer地址，检查剩余显存；不能复制旧run_id。跨机时两节点同一新run_id、同一master地址/端口同时启动。以下变量由操作者从本项目私有盘点填写，不从其他项目凭证读取；`--allow-shared`仅用于本用户已批准的小测试。

```sh
# gpu-01单机两GPU；GPU_UUIDS为2个已确认且唯一的UUID
python3 scripts/m1_launch.py --python "$PWD/.venv-m1/bin/python"   --run-id "$NEW_RUN_ID" --gpus "$GPU_UUIDS" --mode allreduce   --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29651   --timeout 300 --allow-shared

# 两机：每机GPU_UUIDS为1个UUID（M1c）或8个UUID（M1d）；NODE_RANK分别0/1
python3 scripts/m1_launch.py --python "$PWD/.venv-m1/bin/python"   --run-id "$NEW_RUN_ID" --gpus "$GPU_UUIDS" --mode allreduce   --nnodes 2 --node-rank "$NODE_RANK" --master-addr "$MASTER_ADDR"   --master-port 29654 --timeout 300 --allow-shared

# 同一16GPU映射，小模型20步DDP；使用另一run_id/端口，前一测试退出后再启动
python3 scripts/m1_launch.py --python "$PWD/.venv-m1/bin/python"   --run-id "$NEW_DDP_RUN_ID" --gpus "$GPU_UUIDS" --mode ddp   --nnodes 2 --node-rank "$NODE_RANK" --master-addr "$MASTER_ADDR"   --master-port 29655 --timeout 300 --allow-shared
```

M1c实际端口29652；M1d AllReduce29654、DDP29655。底层torchrun命令由manifest保存：project Python `-m torch.distributed.run --nnodes N --nproc-per-node G --node-rank R --master-addr ... --master-port ... --max-restarts 0 tests/m1_baseline.py --mode ... --output runs/<run_id>/node-R`。单机world2；跨机world2或16。当前默认BUFFSIZE1048576、MIN_CTAS=MAX_CTAS=1、NVLS_ENABLE=0、CUBLAS_WORKSPACE_CONFIG=:16:8、NCCL_DEBUG=INFO、SUBSYS=INIT,NET,GRAPH、OMP1，无LD_PRELOAD。早期run的不同参数、旧预算以各自source snapshot/manifest和SOURCES为准，不能用当前参数追写历史。

## 每run证据布局与验收方式

所有RESULTS列出的run_id对应两机 `runs/<run_id>/node-0|node-1/`（单机只有node0）。根目录有control-node-R.json、launch-node-R.log、exit-node-R.json；node目录有manifest.json、source.diff、gpu-preflight.log、occupancy-private.log、python-preflight.log、torchrun.log、nccl.<host>.<pid>.log、rank-<global_rank>.json。日志含真实UUID、地址、占用信息，禁止上传。RESULTS逐run表列出了实际退出码和耗时；[evidence.json](evidence.json)按白名单导出数值摘要，源码哈希可逐节点比对。

PASS同时要求：数值断言未禁用；PG初始化正确；CUDA UUID与所选UUID一致且本机唯一；预期全部rank有PASS JSON；AllReduce所有元素/所有循环一致；DDP各rank20步finite loss/gradient/parameters、参数delta>0、每步同步误差≤1e-6；显式destroy；每节点torchrun/launcher退出0；本次进程组为空。不是只有exit0或只有ping。结束后另核查本测试GPU PID不存在。失败记录不缺省补0；DDP02缺失14份结果，不视为全部rank通过。

实际传输验收从跨机NCCL原日志逐channel的via NET/IB与Using network IB/RoCE判断。M1c两次均有16条双节点合计NET/IB通道记录；最终16rank AR每次4条、DDP每次8条（含方向及初始化记录，不是独立collective数量），NET/Socket数据通道记录为0。实际HCA/接口、PXN/GDR路由细节留私有日志；不把bootstrap TCP socket误称数据走TCP，也不单凭出现IB字样或设备存在认定RDMA。

公开计时单位均ms，启动器elapsed单位s，显存MiB，allocator峰值bytes，张量count为元素。CUDA事件字段名为cuda_dependency_interval_ms，明确包含PyTorch当前stream等待NCCL完成的依赖区间；不能冒充每条NCCL API独立GPU耗时。没有FLASH采集、检测、预测或故障真值；control标注FLASH=false、fault_injection=false、truth=not applicable。

`scripts/m1_summarize.py --output runs/<new-evidence-id>/node-summary.json` 在每节点只导出白名单：排除host/address/UUID/PID/完整库路径/原始trace；保留源码SHA、状态、数字和清理计数。公开evidence把AllReduce逐元素/逐次记录压缩成断言完成数及期望/耗时摘要，DDP保存逐step聚合；服务器rank JSON仍保留全部原始逐step值。缺失原始文件必须报错或记录缺失，不制造PASS。

## Git与后续阶段边界

GPU测试实际权威快照包含7291034（首轮）、b728e79（初次成功通信/16rank）、32db9a3（DDP02）、5ffe2be（DDP03）及ed36c02（最终AR/DDP）；节点执行镜像SHA可能不同，但每次双机launcher/test SHA256一致。最终源码/报告提交与同步记录由服务器Git及.git/m1-sync-final.json查询，发布前本地中转按私有说明扫描凭证/IP/UUID，GH使用非force与expected_sha保护main，逐文件blob与tree核验，不覆盖无关提交。历史GitHub提交SHA不同于服务器，树一致不等于历史相同。

M1完成后停止。M2需单独审核，建议范围见RESULTS；MoE运行仍需兼容框架/训练入口及明确许可。

最终文档/证据检查：runs/m1-final-validation-20261010T040704Z，py_compile、launcher --help、git diff --check、git check-ignore及status五项均0，22份node run摘要的rank/退出/清理/源码一致性断言通过。先前040640Z检查脚本误把/.venv-m1/作为Git外部路径，check-ignore退出128；原错误日志保留，原聚合PASS已更正为FAIL并注明原因。该检查错误不改变GPU测试结果。

公开历史边界：M0旧版ENVIRONMENT_PLAN/GAPS曾含服务器地址；本轮当前文件已脱敏、原文只在私有redaction run备份。既有GitHub历史未重写，因此不能保证历史版本/旧diff无地址；本轮公开源码/摘要经私有说明逐值扫描后上传，无凭证、真实UUID或原始NCCL日志。
