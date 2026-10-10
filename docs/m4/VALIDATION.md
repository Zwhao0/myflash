# M4 实测命令与证据
开发源/实际CPU与GPU执行机器：gpu-01:/home/campus/zhangweihao/myflash；Python3.12.3，GPU额外使用项目.venv-m1内PyTorch2.8.0+cu128。M3跨机样本原采集gpu-01/gpu-02；当前只读离线重放均gpu-01。
以下完整命令均项目根运行，退出0；GPU展开UUID命令只存私有control.json，公开用占位符且不冒称完整展开命令。

```sh
python3 tests/m4_offline.py --output runs/m4-offline-final-03
python3 scripts/m4_replay.py --output runs/m4-replay-final-03
python3 scripts/m4_verify_real.py --run-id m4-multigroup-normal-01
python3 tests/m3_reader.py
python3 tests/m3_validation.py
python3 scripts/m3_validate_public.py
python3 scripts/m4_export.py --offline runs/m4-offline-final-03 --replay runs/m4-replay-final-03 --checks runs/m4-final-check-03
python3 scripts/m4_run_real.py --run-id m4-multigroup-normal-01 --master-port 29911
```
前三命令原始日志runs/m4-final-check-03/{0,1,2}.log和manifest.json；三回归原始日志runs/m4-final-check-01/{3,4,5}.log，命令/退出完整manifest.json。export.log在final-check-03，白名单导出验证exit0。真实run的三个子命令及各退出0、10.37s/0.06s/0.04s在control.json；torchrun.log、Reader日志、per-rank检查/actual加载版本、NCCL日志、完整NDJSON、独立normal真值、source SHA/diff/各文件hash、预检、timeout/精确清理均node-0私有目录。
实际展开GPU命令形态（参数全量在服务器control.json）：
```sh
python3 scripts/m4_launch.py --python <project>/.venv-m1/bin/python --run-id m4-multigroup-normal-01 --gpus <M1_approved_first_4_UUIDs> --mode multigroup --nnodes 1 --node-rank 0 --master-addr 127.0.0.1 --master-port 29911 --timeout 300 --allow-shared --probe
python3 scripts/m2_cleanup.py --run-id m4-multigroup-normal-01 --node-rank 0
```
postflight只读命令ps -eo pid=、nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits均exit0；仅与本run四PID取交集，不发布其他进程。Python Path.glob只查flash_m2_m4-multigroup-normal-01_node-0_*，无删除广泛资源。postflight.json保存结果。

断言：65fixture固定手算匹配；raw完整digest/连续/context；CSV原字段和raw相等且metadata补充hash有效；expected整个comm/rank/instance/scope/record数量；run/epoch污染/坏值拒绝；Group scope去重；双权重/双CV/冲突输出；真实预定五组/十localcomm/各epoch60/每local6、各rank全部SUM数值、两轮Monitor零新增Probe CUDA、最后state0/请求应用一致；Reader attempts=write=read=持久化行数、loss/errors/bad/poison0，全部rank/PID对应正确。
真实验证entry在GPU完成后补强为所有counter必须存在且为0（不采用可缺字段检查），只读同一原始run重验通过，未重跑/改数据。M1–M3/native保存逐路径diff--exit-code0，既有回归通过；不是全部M1–M3 GPU重复实验，旧全GPU回归本轮NOT_RUN。
失败尝试保留runs/m4-replay-01/02，后续不同目录重试；不删除、不伪称PASS。最终结果仍有normal临时误报，G04保持OPEN。
