# M2 验证入口与原始证据
实测设备：gpu-01/gpu-02，各8×H800，沿用M1 PyTorch2.8.0+cu128/NCCL2.27.3；gpu-01目录/home/campus/zhangweihao/myflash为权威源，gpu-02为执行镜像。实际hostname、UUID/进程/网卡/地址、完整底层命令仅服务器runs/；公开evidence.json只保留白名单数字/断言。
## 实际命令
下列是实际使用的完整高层入口，已在项目根执行；m2_run_node从本项目M1最终PASS的runs/m1d-20261010-allreduce-04/node-R/manifest.json读取已授权UUID/peer，启动前重新核验余量，不从其他项目读取配置。完整展开的torchrun参数、env、source SHA/diff/hash、所有退出值在各run control-node-R.json与node-R/manifest.json。
```sh
python3 scripts/m2_build.py
python3 tests/m2_ring.py
python3 tests/m2_hook_smoke.py
# B：gpu-01原生M1负载与显式Probe；各25次4096 int64元素
python3 scripts/m2_run_node.py --run-id m2b-20261010-native-01 --gpu-count 2 --mode allreduce --master-port 29751
python3 scripts/m2_run_node.py --run-id m2b-20261010-probe-04 --gpu-count 2 --mode allreduce --master-port 29751 --probe
# F：gpu-01直接NCCL Group/InitRank/Config/Split/lifecycle
python3 scripts/m2_run_node.py --run-id m2f-20261010-lifecycle-03 --gpu-count 2 --mode lifecycle --master-port 29761 --probe
# C：在两节点分别执行，node-rank为0与1；同时启动
python3 scripts/m2_run_node.py --run-id m2c-20261010-probe-02 --node-rank 0 --nnodes 2 --gpu-count 1 --mode allreduce --master-port 29771 --probe
python3 scripts/m2_run_node.py --run-id m2c-20261010-probe-02 --node-rank 1 --nnodes 2 --gpu-count 1 --mode allreduce --master-port 29771 --probe
# D：两节点同时分别执行
python3 scripts/m2_run_node.py --run-id m2d-20261010-allreduce-02 --node-rank 0 --nnodes 2 --gpu-count 8 --mode allreduce --master-port 29781 --probe
python3 scripts/m2_run_node.py --run-id m2d-20261010-allreduce-02 --node-rank 1 --nnodes 2 --gpu-count 8 --mode allreduce --master-port 29781 --probe
# E：D退出后，两节点同时分别执行
python3 scripts/m2_run_node.py --run-id m2e-20261010-ddp-04 --node-rank 0 --nnodes 2 --gpu-count 8 --mode ddp --master-port 29791 --probe
python3 scripts/m2_run_node.py --run-id m2e-20261010-ddp-04 --node-rank 1 --nnodes 2 --gpu-count 8 --mode ddp --master-port 29791 --probe
```
这些run_id已使用，复测必须换新run_id；每个普通GPU测试预算300s、PG超时120s，启动器保留60s供收尾，外部不按模糊进程名清理。独立Reader命令由manifest保存，启动于训练前、训练退出后排空并退出。没有GPU降频/OOM/拥塞/故障注入。
每run：runs/<run_id>/control-node-R.json、launch-node-R.log、exit-node-R.json、verify-node-R.log/json、cleanup-node-R.log/json；node-R内manifest.json、source.diff、GPU preflight/私有占用、torchrun.log、nccl.*.log、rank-*.json、probe/events-*.ndjson、reader-result.json、verification.json、cleanup.json。训练及Probe记录持久化后才清理共享内存，不删除原始证据。
## 通过断言
A：11项CPU测试包含count边界、环形回绕、满/锁截止丢失计数、四线程写入及并发读取、reader排他/正常重启/未ACK重启、持久化后未ACK重启CLI去重、run隔离/陈旧run拒绝、checksum/ABI坏数据、正常关闭排空精确unlink、持锁进程死亡poison。另有4线程CPU mock：1205事件、连续调用进入序号、递归内部初始化不重复采集、原错误rc4/5/7透传、非阻塞初始化UNSUPPORTED且空hash；不是GPU实验。
B/C/D：原M1源码/25循环/4096元素/SUM断言不变；B原生与Probe期望数值完全一致。每rank28次AllReduce（初始/两次barrier/25循环），其中count4096/dtypeInt64的25次必须完整出现。
E：原M1 676参数小DDP、rank差异数据、20step、finite loss/梯度/参数、delta>0、同步误差≤1e-6、显式destroy全部保留；实际当前入口要求ncclBcast26/AllGather1/AllReduce23每rank，保持真实API名称。原M1 files未改，原生无LD_PRELOAD保护仍在。
F：实际InitConfig、Group内InitRank及成功GroupEnd后COMM_MAPPING、两层嵌套Group/内外AllReduce、AllGather/Broadcast/Reduce/ReduceScatter、Send/Recv、Split、Finalize/Destroy的调用记录与数值断言。Split输出操作必须UNRESOLVED_SPLIT且hash空，不参加可靠跨进程组断言；这个限制不影响已批准训练的主要InitConfig路径。
所有Probe PASS同时要求：训练PID=buffer PID、rank集合精确、local GPU UUID正确、实际运行库22703/12080、源文件哈希一致（实际执行路径）、publish_seq连续、读取计数=写入计数=attempts、full/lock/errors/bad/poison均0、closed=1、非合成调用rc0。跨机同hash的成员精确为world全部rank；未知数据不补零、不参加组判断。COMM_MAPPING是元数据辅助记录，不计为独立NCCL API调用。
## 收尾与失败保留
CLI持久化NDJSON再ACK，正常结束后当前run对象在同一SSH测试会话内按Reader实际快照排空/closed/创建时间验证再unlink；unlink数量必须与rank数一致。早期会话结束后对象已消失的观察保留，原因未实证；不能声称对象一定跨登录会话保留，Reader重启验收在存活的run/IPC生命周期内进行。CPU owner-death模拟只针对本fixture子进程，不杀训练或其他任务。
首两次headers编译exit1、首轮Group验证器错误exit1、DDP首轮API名称错误验证exit1、早期清理脚本模块路径错误/对象不存在exit1均保留原日志；不追改这些run为PASS。新增最终run验证正确代码。首版暂存diff有空白格式错误，已在后续提交修正；该早期检查没有独立退出码文件，不补造PASS或退出码。
最终验证脚本/完整命令/实际exit在runs/m2-final-validation2-20261010；构建readelf/nm/ldd/既有OpenSSL版本与无CUDA/控制符号审计在runs/m2-native-audit-*；最终PID/显存/目标run共享内存/源码检查在runs/m2-postflight-*。具体最终路径、每测试0值与统计见RESULTS/evidence.json。M2完成后停止，M3 NOT_RUN。
