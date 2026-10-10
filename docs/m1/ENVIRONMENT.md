# M1 环境核验（公开脱敏版）

2026-10-10 在 node-0 / node-1 实测。权威源为 node-0 当前新项目；node-1 仅为执行镜像。完整地址、GPU UUID、PCIe/NIC/NUMA 对应矩阵、其他作业标识和原始日志仅在两机项目 `runs/` 中。以下为聚合环境事实，不是带宽或论文性能结论。

| 项目 | node-0 | node-1 |
|---|---|---|
| GPU | 8×NVIDIA H800；每卡81559 MiB | 相同 |
| OS / kernel | Ubuntu24.04.4；6.8.0-142-generic | Ubuntu24.04.4；6.8.0-139-generic |
| 驱动 / Python | 580.178.04 / 3.12.3 | 相同 |
| 拓扑概况 | NVLink连接可见；2个NUMA节点；GPU/PCIe/NIC映射已采集 | 相同；完整差异留私有日志 |
| 网络设备 | Ethernet链路RDMA端口：4×400Gb/s、1×25Gb/s报告速率；无InfiniBand链路层端口 | 相同；报告速率不等于实测吞吐 |
| 两机可达性 | 双向peer路由与2次ping退出0；torchrun rendezvous与跨机NCCL实际通过 | 相同 |
| 宿主库 | libcuda、ibverbs可见；无ldconfig NCCL项 | libcuda、ibverbs及NCCL项可见，但宿主NCCL版本未确认/未作为训练库使用 |
| 宿主CUDA toolkit | nvcc不存在；/usr/local/cuda不存在 | 相同 |
| 原有环境入口 | /usr/bin/python3无torch；当前账号Docker socket拒绝访问；已核验账号标准入口未找到可用conda/训练环境 | 相同 |
| 外部网络 | 无可用外网；用户确认，HTTP下载探测失败 | 相同 |

ADAPTATION：用户批准在已占用GPU上运行低资源测试。启动器每次检查选定GPU UUID、显存余量及MIG状态，MIG Disabled；后续启动前至少3072MiB余量。用户先批准严格1536MiB预算，后明确允许略超；最终1536MiB为记录目标、2048MiB为本轮运行末保护检查，PyTorch allocator限制总显存1%。这些检查不构成CUDA/NCCL瞬时峰值的硬隔离。没有降频、OOM、网络干扰、故障注入或终止其他作业；共享环境无法据此证明性能无干扰。

## 已批准的项目离线环境

两机 `.venv-m1/bin/python` 均安装同一Linux/Python3.12依赖闭包，25包版本与SHA256见 [requirements.lock](requirements.lock)。安装器离线 `--no-index --require-hashes`，两机哈希检查、安装、pip check均退出0；没有升级驱动、系统CUDA/NCCL或安装CUDA toolkit。wheel depot在 `.wheels-m1/`，与venv及runs均gitignored。

| 版本口径 | 两机实测结果 |
|---|---|
| 安装包 | torch2.8.0、nvidia-nccl-cu12 2.27.3；其余固定依赖见lock |
| PyTorch编译标签 | torch2.8.0+cu128；torch.version.cuda=12.8；torch git/build记录在每rank原始JSON |
| 运行时实际CUDA | libcuda来自原系统580.178.04；libcudart.so.12来自项目venv；cudaRuntimeGetVersion返回12080（12.8） |
| 运行时实际NCCL | libnccl.so.2来自项目venv；ncclGetVersion返回22703（2.27.3），实际/proc/self/maps与API均记录 |
| native transport | 跨机成功运行日志有Using network IB、RoCE及实际via NET/IB通道；未观察到via NET/Socket数据通道；初始化控制socket与数据传输分别记录 |

实际socket接口、RDMA HCA/端口、GID与每channel传输记录见私有 `nccl.*.log`，M1c另有 `network-evidence-private.txt`。上述证据支持本次IB verbs/RoCE传输成功；不声称原生InfiniBand fabric、所有HCA逐一验证、GPUDirect RDMA专项验收或400Gb/s性能达标。

UPSTREAM来源及ADAPTATION参数理由见 [SOURCES.md](SOURCES.md)。本地仅通过既有代理获取公开wheel并中转；主torch/NCCL wheel哈希另核对官方PyPI，其余通过TLS镜像与锁文件/两机传输后哈希核验。不能声称逐包另行核对了官方发布哈希。

## 后续组件与范围

Megatron-Core/Megatron-LM、Transformer Engine、FlashAttention在本账号宿主及项目Python入口中未安装，项目无native pretrain入口，Docker权限不足。没有跨其他项目搜索训练代码或凭证。只说明已核验入口的可用性，不断言服务器所有账号/容器都不存在框架。

宿主/项目Python Redis、Rbeast未安装；无用户指定且获准访问的Redis实例，Redis服务连接测试NOT_RUN，未部署服务、未写键。可用现有实例位置仍待明确。NumPy为torch可选功能，在本基线未安装也未使用；其警告保留，不影响本次torch tensor测试。
