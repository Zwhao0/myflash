# M3验证
实测gpu-01/gpu-02 H800；权威源gpu-01:/home/campus/zhangweihao/myflash。命令均在项目根执行；GPU UUID/私网地址/项目路径在下面脱敏，完整展开命令保留服务器每run control-node-R.json。下列均实际执行且训练/Reader/验证/清理0（native无Reader/清理）。每次run_id不可复用。

```sh
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3abc-local-01 --gpus <approved_GPU_UUID_list> --mode mechanism --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29811 --timeout 300 --allow-shared --probe
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-roce-01 --gpus <approved_GPU_UUID_list> --mode mechanism --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29821 --timeout 300 --allow-shared --probe
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-roce-01 --gpus <approved_GPU_UUID_list> --mode mechanism --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29821 --timeout 300 --allow-shared --probe
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3e-group-01 --gpus <approved_GPU_UUID_list> --mode group --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29831 --timeout 300 --allow-shared --probe
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3e-group-02 --gpus <approved_GPU_UUID_list> --mode group --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29832 --timeout 300 --allow-shared --probe
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-allreduce-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29841 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-allreduce-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29841 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-ddp-01 --gpus <approved_GPU_UUID_list> --mode ddp --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29851 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-ddp-01 --gpus <approved_GPU_UUID_list> --mode ddp --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29851 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-allreduce-02 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29842 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-allreduce-02 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29842 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-ddp-02 --gpus <approved_GPU_UUID_list> --mode ddp --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29852 --timeout 300 --allow-shared --probe --profile
python3 scripts/m3_launch.py --python <project>/.venv-m1/bin/python --run-id m3f-ddp-02 --gpus <approved_GPU_UUID_list> --mode ddp --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29852 --timeout 300 --allow-shared --probe --profile
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-local-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29861 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-cross-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29871 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-cross-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29871 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-allreduce-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29881 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-allreduce-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29881 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-ddp-01 --gpus <approved_GPU_UUID_list> --mode ddp --nnodes 2 --node-rank 0 --master-addr <gpu01_master_address> --master-port 29891 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-ddp-01 --gpus <approved_GPU_UUID_list> --mode ddp --nnodes 2 --node-rank 1 --master-addr <gpu01_master_address> --master-port 29891 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-monitor-lifecycle-01 --gpus <approved_GPU_UUID_list> --mode lifecycle --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29862 --timeout 300 --allow-shared --probe
python3 scripts/m2_launch.py --python <project>/.venv-m1/bin/python --run-id m3d-native-01 --gpus <approved_GPU_UUID_list> --mode allreduce --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29863 --timeout 300 --allow-shared
# CPU最终suite（gpu-01；完整子命令在manifest）
python3 scripts/m3_cpu_suite.py
# 更严格的最终只读校验：两机分别node-rank 0/1
python3 scripts/m3_validate_all.py --node-rank 0
python3 scripts/m3_validate_all.py --node-rank 1
# 白名单导出与资源检查：各节点运行对应的node-rank
python3 scripts/m3_export.py --node-rank 0
python3 scripts/m3_export.py --node-rank 1
python3 scripts/m3_postflight.py --node-rank 0
python3 scripts/m3_postflight.py --node-rank 1
```
命令中的<project>代替服务器绝对根；实际完整命令/环境保留各control-node-R.json和node-R/manifest.json，包含torchrun/reader/低资源NCCL参数、代码SHA/diff/源文件hash/Probe hash、GPU预检、预算、退出、原始rank输出、nccl.*.log、events-*.ndjson。机制真值独立存evaluator-truth-rank-*.json，不被Probe读取，没有预测文件或自动定位。

普通GPU预算300s，训练PG/TCPStore120s，启动器留60s收尾；超时只结束本run独立进程组，Reader排空后按closed/created_ns/PID/read_pos对精确对象unlink。没有发生GPU测试timeout或其它作业终止。Reader错误/缺rank/丢失/部分生效不得完整PASS。

## 断言
- 本地请求只接受0/1、Profile epoch>0且不倒退/重开结束epoch；非Group入口和外层GroupStart生效，嵌套/同Group冻结；两轮Profile均有每rank有效数据，两个epoch之后各有Monitor数据，最终requested_control=applied_control且state=0。
- CUDA create/start/stop/sync/elapsed/destroy返回0，Event device=local_rank；valid duration有限且>0，ElapsedTime转换us正确，scope与Group ID一致。错误/捕获/多stream/非阻塞/提交失败没有有效duration=0。普通完整Profile要求unsupported=0；Group专门测试允许预期的UNSUPPORTED，complete_profile=false。
- A–D每rank134 AllReduce：130 Profile+4 Monitor，float32/count4096（元素，16384bytes）；每Profile对应外部Event参考区间，内部区间<=外区间+2us；实际stream_ptr=记录communication stream，comm/hash/rank/size关联正确。GPU前置Event耗时>0，host sleep仅CPU场景。两机NCCL NET/IB/RoCE日志有实际记录，非ping推断。
- E每rank60 collective；40有效Profile成员/24有效scope、16 unsupported成员；同Group两个成员共用epoch/status/duration，内层/提交前sync计数不增加，外层成功后只增加一次，数值3/5正确。共享duration不作为两个独立内核样本。
- F原M1 AllReduce25次4096 int64/32768bytes，SUM136；DDP676参数/20步、finite loss/grad/parameters、delta>0、每次同步误差<=1e-6；真实API每rankBcast26/AllGather1/AllReduce23保留。Profile AR12、DDP20样本/rank。wrapper在Monitor断言Probe CUDA调用计数不增加，包括DDP backward。最终全16rank、两个epoch、192/320样本、额外同步次数等于有效scope。
- M2原CPU11项/4线程mock、真实Monitor单机/跨机/16rank/DDP/lifecycle全部回归；原M1和M2基线入口blob SHA256不变，native入口仍可运行。ABI2明确拒绝ABI1、不支持运行中滚动升级；M2旧run已结束并清理，不将ABI1对象或无digest旧日志静默作为新数据。
- NDJSON保存完整newline记录并fsync后ACK；仅尾部未确认片段可截断、完整已持久化行保留、未ACK可重放；中部坏JSON/摘要/序号、已ACK但文件缺失/截断硬失败。CLI恢复与ACK测试CPU证据见suite3.log。
- attempts/write/read/持久化行数精确一致，publication连续，bad/poison/loss/errors均0；按固定rank集合检查，不补零。最终只读跨节点验证检查同id_hash完整rank集合、binary/core源hash相同。

## 证据路径与退出
CPU最终suite runs/m3-cpu-20261010T053356468174Z/manifest.json和0..5.log：六命令全0；上一suite runs/m3-cpu-20261010T052834548266Z也全0。真实run计数/退出见RESULTS/evidence-node-R.json，每run控制/训练/Reader/验证/清理完整日志在runs/<run_id>。最终validation与fixture日志在runs/m3-final-node-R/，退出0；postflight2.log退出0、公开postflight-node-R.json指向完整manifest，每命令exit0。导出export.log两节点exit0。失败首轮postflight.log保留exit1，底层git128，不覆盖为成功。
最终白名单联合校验gpu-01执行 `python3 scripts/m3_validate_public.py` exit0；核对源/binary、跨机hash成员、520样本/400非warmup/20分布以及4652条collective成员，输出及退出码保存runs/m3-final-public/validation.log、validation.exit，公开public-validation.json，该项PASS。首次调用误用不存在的Python路径exit127，原日志runs/m3-final-node-0/public-validation.log与.exit保留，未发生GPU操作；改用本阶段其它CPU检查一致的python3后新日志exit0。敏感原始数据不离开服务器，GitHub只同步源/文档/白名单样本。
公开命令的地址/UUID脱敏补强后，同一只读联合核验再执行一次exit0，日志runs/m3-final-public/validation2.log与validation2.exit；未改变实验行、rank、duration或分布。
CSV导出默认CRLF令git diff --check报告尾部空白exit2，原输出保存runs/m3-final-public/csv-preformat-diff.log/.exit。只把公开CSV换行改为LF，并逐字段比较确认完全相同（csv-format.json）；导出器固定LF。联合核验validation3.log通过，暂存diff-check.log为空且exit0。一次提交因服务器没有Git作者配置exit128，不影响测试；使用本阶段已有提交身份的单命令Git配置重试，无全局配置改动。
收尾规范化之后的实际完整命令/退出码/日志统一保存在gpu-01 runs/m3-final-public/final-manifest.json：python3 scripts/m3_validate_public.py、git add、git diff --cached --check、git -c user.name=Codex -c user.email=codex@localhost commit、python3 runs/m3-package-publish.py均exit0，逐项final-0.log至final-4.log。GitHub首份41个变化blob和完整tree匹配、Draft PR分支回读见SYNC.json。GitHub操作不作为GPU实验PASS依据。

## 未覆盖
真实default stream Profile、混合communicator Group、多设备/捕获/非阻塞InProgress、异步初始化、并发多线程Profile、未包装NCCL API与真实CUDA错误注入均NOT_RUN/UNSUPPORTED；CPU mock不替代GPU验收。未做GPU降频/OOM/网络拥塞/MoE/BOCD/Redis/M4自动定位，也未做论文20s自动窗口/正式吞吐开销比较。
