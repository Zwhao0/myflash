# M1 来源与选择

PAPER：SPEC S9 保存论文训练环境与 H200 配置；本轮 H800 小负载只验证通信/训练底座，不称论文 MoE 复现。

UPSTREAM：官方 PyTorch [distributed 2.8](https://docs.pytorch.org/docs/2.8/distributed.html)、[DDP 2.8](https://docs.pytorch.org/docs/2.8/generated/torch.nn.parallel.DistributedDataParallel.html)、[torchrun 2.8](https://docs.pytorch.org/docs/2.8/elastic/run.html)、[CUDA Event 2.8](https://docs.pytorch.org/docs/2.8/generated/torch.cuda.Event.html) 和 [NCCL 环境变量](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html) 为接口依据；采用公开 API，从零编写，不复制实现源码。UUID 属性另核对 PyTorch tag v2.8.0 `torch/csrc/cuda/Module.cpp:registerCudaDeviceProperties`；没有复用其代码或 GreyHound 代码。目标 API 兼容性仍须实际运行，文档核验不等于 GPU PASS。

ADAPTATION：CPU/GPU 固定种子、小型 rank 差异合成数据；AllReduce int64 每 rank 输入 rank+1+step，SUM 期待 W(W+1)/2+step×W；4096 元素=32768 字节，5 预热+20 次验证；DDP 16→32→4、batch8、SGD0.01、20 step，每步验证有限 loss/梯度/参数及 rank0 参数广播比对（误差≤1e-6），更新量必须>0；所有 rank 独立记录。

ADAPTATION：按明确 UUID 设置 CUDA_VISIBLE_DEVICES，并与实际 CUDA UUID 比对；每次启动独立 run_id；总预算≤300s，ProcessGroup timeout120s；只清理新进程组。用户追加批准共享 GPU 小测试，启动前每卡必须有≥2048MiB余量，PyTorch allocator 限总显存1%，运行末审计本 PID 设备用量≤1024MiB。该限额不限制 CUDA/NCCL 外部分配瞬时峰值，因此不能据此声称硬资源隔离；未达到检查条件即失败/阻塞。

ADAPTATION：NCCL_BUFFSIZE=1048576 限制内部通信 buffer 配置；此为小测试资源选择，不是性能基准。CUDA Event 记录 PyTorch 当前 stream 中覆盖 collective completion dependency 的区间；独立记录 host completion 时间，不充当 FLASH Probe/Group 计时。DDP iteration_ms 包含数值检查和完成同步，参数审计通信在该迭代计时后，不用于论文性能结论。

ADAPTATION：用户明确批准项目隔离环境 torch==2.8.0 CUDA12.8 wheel 及固定依赖；不变更系统驱动/系统库。安装成功后必须锁定完整依赖/哈希，并在两机实测映射库。缺依赖或下载失败保持 BLOCKED。

EXTENSION：没有纳入检测、定位、故障注入、缓解或自动闭环。

## 离线依赖传输

ADAPTATION：两机离线，使用用户本机既有系统代理访问清华 PyPI 镜像；下载 PyPI 发布的 torch2.8.0 Linux CPython3.12 wheel，编译 CUDA12.8，NCCL2.27.3。不是更换系统 NCCL 或安装 CUDA toolkit。Linux/Python3.12 markers 由 wheel metadata 显式求依赖闭包，25包准确版本与SHA256见 requirements.lock。macOS下载器额外取到 importlib-metadata/zipp 两个 marker<3.10 依赖，仅保留本地下载记录，不装到目标环境。

UPSTREAM：主 wheel 哈希另核对官方 [torch2.8.0 PyPI文件](https://pypi.org/project/torch/2.8.0/)（cp312 manylinux2_28 x86_64：b2aca0939fb7e4d842561febbd4ffda67a8e958ff725c1c27e244e85e982173c）与 [NCCL2.27.3 PyPI文件](https://pypi.org/project/nvidia-nccl-cu12/2.27.3/)（x86_64：adf27ccf4238253e0b826bce3ff5fa532d65fc42322c8bfdfaf28024c0fbe039）。其余包按 TLS 镜像索引下载并做锁文件哈希/两机传输后核验，不声称逐包另行核对了官方元数据。接口文档固定 [NCCL2.27.3 archive](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/env.html)。

ADAPTATION：gpu-02 使用当前新项目路径的轻量源码镜像执行，SOURCE_COMMIT标注 gpu-01 权威源快照；各节点 run manifest保留自己的GitSHA、diff、测试源码SHA256，双机测试前核对源码哈希。训练无大型模型/数据下载，Megatron/TE未安装。

## 显存预算明确调整（用户批准）

首轮 m1b-20261010-baseline-01 两个 rank 的25次数值检查均完成，实际本PID GPU显存1234MiB，超过最初1024MiB检查预算，因此保留 FAIL/退出1及完整原始日志。用户已明确批准资源预算改为1536MiB、启动前余量至少3072MiB；原数值断言、样本数、超时不变，重跑使用新run_id。上述资源数值替代初始2048/1024MiB，不是 FLASH 科学阈值，且运行末样本不能保证外部 CUDA/NCCL 分配的瞬时峰值。

## DDP 显存减小，不改变预算或断言

ADAPTATION：m1d-20261010-ddp-01 完成20步数值/参数同步检查，但本PID GPU用量1582–1670MiB超过已批准1536MiB，因此保留FAIL/退出1。按用户避免占满显存的要求，后续启动改为NCCL_BUFFSIZE=262144、NCCL_MAX_NCHANNELS=1、CUBLAS_WORKSPACE_CONFIG=:16:8；缩小通信buffer/channel与确定性cuBLAS工作区，不改变模型、数据、20步、数值阈值、1536/3072MiB预算或300s上限。见官方NCCL2.27.3环境变量与[cuBLAS12.8重现性](https://docs.nvidia.com/cuda/archive/12.8.0/cublas/index.html#results-reproducibility)。此配置仅功能验收，不用于吞吐基准；新run_id独立重跑。

## 第二次 DDP 配置的进展阻塞

ADAPTATION：m1d-20261010-ddp-02 曾在初始化后长时间无结果；最终rank2记录20步完成，但GPU用量1542MiB超过1536MiB，随后torchrun结束其余本次rank，退出1（不是启动器300s超时）。保留FAIL与不完整rank结果；不能把中间观察误称确定的通信挂起。日志仍显示16 coll/NVLS channels，不能把MAX_NCHANNELS=1当成实际1channel。后续恢复此前通过的1MiB buffer，采用NCCL2.27.3当前MIN_CTAS=MAX_CTAS=1并显式NVLS_ENABLE=0避免分配NVLink SHARP资源（普通NVLink/P2P和跨机RoCE仍可用）；保留:16:8工作区。是低资源功能基线配置，不表示默认NVLS/自动算法或性能基准通过；预算、模型、次数及数值断言均不变。官方[NCCL2.27.3变量](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/env.html#nccl-nvls-enable)为UPSTREAM依据；配置效果仍以新run日志和数值验收为准。

## 用户进一步放宽资源验收

ADAPTATION：用户明确要求“超过一点显存没事，不要占满，不要因为这个原因阻碍开发”，覆盖此前严格1536MiB检查。后续1536MiB为记录目标，略超只记memory_target_exceeded；2GiB为本轮保护上限，启动前仍≥3GiB余量，1% PyTorch allocator、低资源NCCL配置不变。保留先前按旧政策产生的FAIL，不追改它们为PASS；新run_id验证当前源码。GPU总显存81559MiB，保护检查仍只是运行末样本，不能声称瞬时硬隔离。所有数值断言/次数/超时未改。
