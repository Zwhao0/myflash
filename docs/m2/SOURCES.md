# M2 来源与构建依赖
PAPER：目标规格是 references/chapter3.pdf 的第三章§3.2.1 pp.23–24、§3.2.2 pp.25–27、§3.3.1 pp.32–33；对应 SPEC S1/S2/S4/S5。采用 LD_PRELOAD、惰性初始化、Monitor元数据与环形共享内存。论文未给出完整并发协议，不能引用论文50–200ns数字为本实现实测。
UPSTREAM API：
- [NCCL 2.27.3 communicator](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/api/comms.html)：InitRank/Config的unique ID输入、Split/lifecycle、异步返回。
- [NCCL 2.27.3 Group](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/api/group.html)与[collective](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/api/colls.html)：公共签名和Group提交语义。
- [PyTorch v2.8.0 NCCLUtils.cpp](https://github.com/pytorch/pytorch/blob/v2.8.0/torch/csrc/distributed/c10d/NCCLUtils.cpp)：初始化选择核验；[ProcessGroupNCCL.cpp:ProcessGroupNCCL::broadcast](https://github.com/pytorch/pytorch/blob/v2.8.0/torch/csrc/distributed/c10d/ProcessGroupNCCL.cpp#L4163)确实调用ncclBcast，_broadcast_oop另调用ncclBroadcast。本项目保留两个真实API名字，不互相改标签。
- 运行接口以项目实际wheel nccl.h（NCCL_VERSION_CODE=22703）和每rank实际/proc/self/maps、ncclGetVersion=22703、cudaRuntimeGetVersion=12080为准；签名直接由官方header编译核验，无手写替代声明。
所有Probe/Reader代码独立编写；只是调用API，不复制PyTorch或NCCL实现源码。GreyHound固定SHA仍是GREYHOUND_MAP.md所列可选参考；本轮没有读取/复用其源码，LICENSE仍NOT_VERIFIED，不据其算法或许可推断FLASH实现。
## 编译条件与缺失headers的解决
ADAPTATION：现有g++13.3.0、GNU ld2.42构建共享库，无nvcc、无CUDA kernel。M1已安装的runtime12.8.90 wheel有公共headers但缺crt/host_config.h；已有Triton3.4.0内置CUDA12.8编译headers补充crt，仍缺nv/target。首两次实际编译exit1，日志保留runs/m2a-compile-20261010。
用户随后明确“先尝试解决这个问题，不堵塞”；仅补充本项目隔离开发headers：
- 包：[nvidia-cuda-cccl-cu12 12.8.90](https://pypi.org/project/nvidia-cuda-cccl-cu12/12.8.90/)
- wheel：nvidia_cuda_cccl_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl，2939012字节
- SHA256：575bc5cfb0fe4a1956c539215c0f1e6718821b95a68ef6b7abf226aa87e3a5ad，与官方PyPI文件元数据一致，两机传输后重新核验。
- 只用标准库zipfile解包至.build-deps-m2/，wheel留.wheels-m2/，两者gitignored；不向.venv-m1安装、不改变运行依赖、不修改系统驱动/CUDA/NCCL/配置。含nv/target的头文件明确SPDX Apache-2.0 WITH LLVM-exception；包其他文件按其自带声明使用，不统一推断许可证，不把vendor headers提交GitHub。
- SHA256使用两机已有OpenSSL libcrypto/开发headers；dpkg/ldd证据为原系统既有组件，没有新安装OpenSSL。ring使用既有Linux/glibc pthread/shm/flock/posix_fallocate。
可重复准备（有上述获准wheel时）：
```sh
python3 - <<'PY'
import pathlib,hashlib,zipfile
p=next(pathlib.Path('.wheels-m2').glob('nvidia_cuda_cccl_cu12-12.8.90-*.whl'))
assert hashlib.sha256(p.read_bytes()).hexdigest()=='575bc5cfb0fe4a1956c539215c0f1e6718821b95a68ef6b7abf226aa87e3a5ad'
with zipfile.ZipFile(p) as z:z.extractall('.build-deps-m2')
PY
python3 scripts/m2_build.py
```
完整g++ include/link命令、每命令退出、header/source/产物SHA256写入各节点runs/m2-build-*/manifest.json；Probe只依赖CPU系统库，通过dlsym调用原NCCL。构建时Wl,-z,defs检查未解析符号，readelf/nm/ldd再核验。
## 工程选择（ADAPTATION）
ABI1、每进程ring、0600/O_EXCL、容量预分配、ROBUST锁与单调时钟10ms锁截止、丢失/错误计数、校验和、Reader排他、peek/持久化/ACK/重启去重、独立运行命名和精确清理，均是G07必要安全补充。与论文Python无锁清空不同，额外锁和fsync开销未作正式性能结论。
SHA256只用于输入unique ID的稳定组候选标识；comm_ptr/本地generation/TLS Group ID与训练组严格分开。阻塞InitRank/Config覆盖；Split不猜测跨进程hash；异步/其他初始化标UNSUPPORTED。调用序号只在包装入口分配，映射记录关联原初始化call_seq，不制造额外NCCL调用。
复用本项目已审核M1 launcher资源边界与原始m1_baseline.py数值/训练断言，M1文件保持不变；M2独立--probe入口显式设置LD_PRELOAD，只对torchrun训练进程注入，Reader独立无GPU库。每次启动仍检查获准UUID≥3072MiB余量；1536MiB目标、2048MiB运行末检查；MIN/MAX_CTAS1、BUFFSIZE1MiB、NVLS0等仅功能基线参数。
EXTENSION：未加入Profile/CUDAEvent、Redis、Rbeast/BOCD、告警、定位、故障注入或恢复；M3及以后未开始。
