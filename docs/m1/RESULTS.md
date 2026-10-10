# M1 结果

**M1核心通信/训练底座PASS；Megatron/MoE环境准备BLOCKED，原生MoE训练NOT_RUN。** M1a–M1e已按批准范围处理；停止于M1，不开发M2，不称论文模型复现。

| 项目 | 结论 | 实际依据 |
|---|---|---|
| M1a | PASS（盘点完成，缺失如实登记） | 两机各8张H800；系统/编译/运行库口径区分；GPU/PCIe/NIC/NUMA、RDMA、路由和占用原始采集 |
| M1b | PASS（保留首轮FAIL） | node-0两个rank正确初始化，UUID对应，SUM3与25次collective断言通过，退出0、无本次遗留进程 |
| M1c | PASS | 两机各1GPU；两个独立run_id均退出0；rank0/1映射及25次数值验证；实际NET/IB/RoCE数据通道日志 |
| M1d AllReduce | PASS | 两机各8rank；所有16rank初始SUM136；每rank4096个int64元素全部检查；4次独立启动正常退出，最终低资源配置2次 |
| M1d DDP | PASS（保留2次历史FAIL） | 676参数小模型、rank差异合成数据、前向/反向/同步/SGD更新；最终两次各16rank×20step通过 |
| M1e 环境准备 | BLOCKED | 已核验Python入口缺Megatron/TE/native训练入口；host无nvcc，Docker无权限；未部署复杂框架 |
| M1e native MoE训练 | NOT_RUN | 无真实TP/PP/EP训练进程组或MoE结果；DDP不能代替native MoE |

## 每次实际启动（单位明确）

退出码/耗时按node0/node1顺序；耗时为节点启动器全过程秒，显存为运行末本进程GPU用量最大MiB。全部测试预算300s；没有执行故障注入。原始逐rank结果与全部step保存在服务器；公开逐rank摘要/逐step聚合见 [evidence.json](evidence.json)。

| run_id | 状态 | 退出码 | 启动器耗时s | 显存最大MiB | 数值/训练情况 |
|---|---|---|---|---|---|
| m1b-20261010-baseline-01 | FAIL | 1 | 6.190 | 1234 | SUM3；25次数值断言 |
| m1b-20261010-baseline-02 | PASS | 0 | 6.088 | 1234 | SUM3；25次数值断言 |
| m1c-20261010-baseline-01 | PASS | 0/0 | 6.948/5.547 | 1002 | SUM3；25次数值断言 |
| m1c-20261010-baseline-02 | PASS | 0/0 | 6.737/20.640 | 1002 | SUM3；25次数值断言 |
| m1d-20261010-allreduce-01 | PASS | 0/0 | 12.747/12.037 | 1476 | SUM136；每rank25次数值断言 |
| m1d-20261010-allreduce-02 | PASS | 0/0 | 13.300/12.033 | 1476 | SUM136；每rank25次数值断言 |
| m1d-20261010-allreduce-03 | PASS | 0/0 | 15.149/14.032 | 1040 | SUM136；每rank25次数值断言 |
| m1d-20261010-allreduce-04 | PASS | 0/0 | 15.199/34.148 | 1040 | SUM136；每rank25次数值断言 |
| m1d-20261010-ddp-01 | FAIL | 1/1 | 35.429/33.918 | 1670 | 20步数值完成；旧1536MiB预算FAIL |
| m1d-20261010-ddp-02 | FAIL | 1/1 | 200.896/199.800 | 1542 | 仅2份rank结果；1542MiB预算FAIL后其余rank结束 |
| m1d-20261010-ddp-03 | PASS | 0/0 | 16.312/34.986 | 1058 | 16rank各20步；参数同步/更新通过 |
| m1d-20261010-ddp-04 | PASS | 0/0 | 16.246/15.013 | 1058 | 16rank各20步；参数同步/更新通过 |

AllReduce每rank初始rank+1的标量检查之后，运行5次预热+20次测量，每次输入rank+1+step，期望SUM=W(W+1)/2+step×W，所有4096个int64元素（32768字节）逐次断言。rank结果中每次expected_sum只有断言成功后才记录。所有成功run全局rank集合精确为0..W-1，local_rank与显式UUID/实际CUDA UUID相符，双机测试源码SHA256一致。

最终16rank AllReduce两次的CUDA completion-dependency interval均值为0.161081 / 0.168107 ms；host completion均值0.179208 / 0.187320 ms。它们是小张量、共享/动态负载条件下的功能记录，不是NCCL独立内核时间、FLASH Probe时间、带宽基准或论文图表结果。最终参数为BUFFSIZE1MiB、MIN_CTAS=MAX_CTAS=1、NVLS_ENABLE=0；这验证普通native NCCL路径，不能称默认NVLS路径或自动最优算法验收。

## DDP确定性与资源释放

固定种子20261010，模型16→32→4、Tanh、batch8、SGD0.01，rank数据种子20261010+rank；每步loss/梯度/参数有限，参数与rank0的独立副本比较而不修改原模型。两个成功run的所有rank最大参数变化均0.02080027759，最终及每步最大同步误差0（断言≤1e-6）；最终rank loss范围0.6516727209–1.5677684546，rank数据不同所以不要求loss彼此相同。

两次DDP全部step/rank迭代耗时均值14.164480 / 14.461435 ms；保存了每rank每步的loss、iteration_ms与参数同步误差。迭代计时含有限性检查与完成同步，参数审计broadcast位于计时后；第一步/共享作业影响不剔除，不用于吞吐结论。真实DDP组为DP=[0..15]；没有Megatron TP/PP/EP组，也不标记为MoE。

最终AllReduce每进程GPU用量1040MiB，DDP1058MiB；运行末均低于1536MiB目标。成功run全部显式destroy ProcessGroup、退出0，新进程组成员为空，结束后本测试GPU PID均不存在；两机postflight检查退出0。仅启动器对本次新进程组有超时/失败清理能力；未使用全局清理。

## 历史失败与未完成项

首轮M1b数值全部正确，但1234MiB超过当时1024MiB，因此FAIL保留；用户明确批准1536/3072MiB后新run通过。DDP01全部20步数值已完成，但1582–1670MiB超过当时严格1536MiB预算，FAIL保留。DDP02仅留rank2/10两份完整结果，均20步完成、1542MiB；预算断言失败导致torchrun结束本次其他rank，退出1，不冒充16rank正常退出或300s超时。中途看不到输出不等于已证实通信挂起。NCCL非致命RAS bind警告在成功/失败日志中均存在，不把它直接当根因。

用户随后明确允许略超1536MiB、不因此阻碍开发；当前它是记录目标，2GiB是保护检查，仍≥3GiB启动余量。之后使用当前CTA约束、关闭可选NVLink SHARP资源分配及:16:8确定性工作区；新run实际通过并降低用量，没有删失败、缩数值断言或调整科学阈值。详见SOURCES授权轨迹。

无外网直接安装/探测失败已保留；由已批准的项目离线wheel方案解决。第三个早期下载探测包装器曾TimeoutExpired而未写完整stdout，缺失原始输出明确记在recovery-note，不补造；后来独立限时探测保留exit124原始日志。Megatron/TE/native MoE入口、CUDA编译工具以及未指定Redis服务仍不可用/未核验；没有大型模型/数据下载或复杂框架安装。

## M2建议（尚未获准/未执行）

ADAPTATION：先在本轮小负载上建立最小透明Monitor：核对实际NCCL2.27.3初始化API（含InitRankConfig是否使用）及AllReduce调用覆盖，建立rank/communicator/跨进程ID与run_id映射，再实现共享内存完整性/溢出可见性。以preload前后数值一致和重复启动作为首个验收；Monitor正常路径不加CUDA Event/额外同步，不接Rbeast、Redis或故障注入。先只读确认C++编译器及项目headers/build依赖，需要新增依赖另行批准。native Megatron/MoE环境作为单独离线准备事项，使用固定框架SHA/兼容TE入口，待现有容器授权或批准离线组件后再运行真实并行组冒烟；DDP基础测试不关闭G11等论文未知项。
