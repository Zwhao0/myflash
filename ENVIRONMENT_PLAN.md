# M1a 两台 H800 只读环境盘点计划（已执行，结果见docs/m1）

ADAPTATION：以下原计划形成于M0；当时是下一任务命令草案，实际M1a结果现见docs/m1/ENVIRONMENT.md与VALIDATION.md。原计划不是执行报告，不创建训练进程/GPU 上下文、collective、CUDA Event、Redis 服务或基线代码。M0 仅通过 SSH 在 gpu-01 建档与运行 Git/文件核验；未做下列 GPU/网络/软件盘点。

## 已知目标与待补信息

| 对象 | 已知 | M1a 前需确认 |
|---|---|---|
| 开发服务器 H800-A | 本地私有 `服务器.md` 指向 `test@<server-address>`；实际主机名 gpu-01 | 是否也是第一台部署 H800、作业资源归属、指定 Python/容器和允许读取的范围 |
| 第二台 H800-B | 用户计划两台 H800 | 连接目标、账号/端口、目标项目目录；不从其他项目/凭证或扫描网段寻找 |
| 开发目录 | `/home/campus/zhangweihao/myflash`；M0 从不存在的目录创建 | 后续运行的 scratch/run_id 目录与容器挂载 |
| 互联 | 未知 | 双方可达接口/地址、RDMA/RoCE/IB 设备、GPU↔NIC 对应关系 |
| Redis | 论文图3-2/3-3 为远端服务，本项目位置未选定 | 已有实例/管理者、允许访问的地址、资源占用与 run 前缀；M1a 不部署、不写键 |

连接凭证仅留本地私有说明，未复制服务器、未纳入 Git、未写日志。私网地址/UUID/拓扑日志默认保存在项目本次盘点目录，不发往第三方。第二台连接信息须由用户提供；不复述或收集密码到设计文档。

## 运行与权限条件

获准 M1a 后在两台已明确目标机器、指定现有环境中分别执行；普通账号，无 sudo；每条记录完整命令、主机、时间、退出码、stdout/stderr。命令不存在或权限不足记 NOT_RUN/BLOCKED，不安装系统/Python 依赖，不使用整个 `env`、SSH 私钥、shell history、全机进程命令行或凭证配置。输出分享前隐藏凭证、其他作业标识与不必要地址。

M1a 中可产生文档/日志文件，目标采集命令只读。任何 ImportError/工具缺失/版本不明先登记，不能为继续推进而升级。不会因 nvidia-smi 显示 CUDA 上限就判断已安装 CUDA toolkit/runtime。

## 每机最小命令清单（尚未执行）

| 信息 | 拟执行命令 | 含义 / 限制 |
|---|---|---|
| 主机/系统/账号 | `hostname; uname -srmo; cat /etc/os-release; id -un` | 不导出账号数据库或环境变量全集 |
| GPU UUID/数目/显存/驱动 | `nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,memory.total,memory.used,driver_version --format=csv`；`nvidia-smi -L` | 实际型号与数量，不默认 8 张；显存单位保存 |
| GPU↔GPU/NIC 拓扑 | `nvidia-smi topo -m`；`lspci -nn`；`numactl --hardware` | NIC/PCIe/NUMA 对应需实际核验；缺工具记缺失 |
| GPU 当前资源 | `nvidia-smi --query-compute-apps=gpu_uuid,pid,used_gpu_memory --format=csv` | 不读取别人的 /proc/cmdline 或训练日志；只作占用判断，不终止任何 PID |
| CUDA toolkit | `command -v nvcc`；`nvcc --version`；`readlink -f /usr/local/cuda` | 仅查工具及路径；不安装；未指定容器时不推断训练环境 |
| Python/包版本 | 指定现有 `<python>` 的 `--version`；下面 host-only Python 查询 | compiled CUDA、PyTorch/NCCL 的实际加载须分别记录 |
| NIC/地址/路由 | `ip -br link`；`ip -br addr`；`ip route show` | 不扫描网段、不改网络；分享时过滤无关地址 |
| RDMA/IB/RoCE | `rdma link show`；`ibv_devinfo`；`ibdev2netdev`；`ibstat` | 设备存在不证明 NCCL 实际用它；缺命令或权限原样登记 |
| 磁盘/共享内存容量 | `df -h /home/campus/zhangweihao/myflash /dev/shm` | 只看容量，不清理、不枚举别的项目 |

以下 Python 命令仅在用户指定的现有解释器/容器运行；`<python>` 必须替换为实测路径，不建立 venv、不安装 torch。host-only 查询不调用 `torch.cuda.init/is_available/get_device_properties`，不创建 tensor 或 ProcessGroup：

```python
import sys, os, re, json, ctypes, importlib.metadata as md
print('python', sys.executable, sys.version)
for name in ['torch', 'nvidia-nccl-cu12', 'nvidia-cuda-runtime-cu12',
             'megatron-core', 'transformer-engine', 'flash-attn', 'Rbeast', 'redis']:
    try:
        print('package', name, md.version(name))
    except md.PackageNotFoundError:
        print('package', name, 'NOT_INSTALLED')
import torch
print('torch', torch.__version__, torch.__file__)
print('torch_build_cuda', torch.version.cuda)
print('torch_git', torch.version.git_version)
loaded = set()
with open('/proc/self/maps') as f:
    for line in f:
        fields = line.rstrip().split(None, 5)
        if len(fields) == 6 and re.search(r'lib(nccl|cudart|cuda)\.so', fields[5]):
            loaded.add(fields[5])
print('actually_mapped_libraries', json.dumps(sorted(loaded)))
for family in ['nccl', 'cudart']:
    paths = [p for p in loaded if re.search(r'lib' + family + r'\.so', p)]
    if not paths:
        print('version', family, 'NOT_LOADED; defer to approved M1 baseline')
    for path in sorted(paths):
        if path.endswith(' (deleted)'):
            print('version', family, 'MAPPED_FILE_DELETED', path)
            continue
        try:
            lib = ctypes.CDLL(path, mode=os.RTLD_NOLOAD | os.RTLD_LOCAL)
            fn = getattr(lib, 'ncclGetVersion' if family == 'nccl' else 'cudaRuntimeGetVersion')
            fn.argtypes = [ctypes.POINTER(ctypes.c_int)]
            fn.restype = ctypes.c_int
            value = ctypes.c_int()
            rc = fn(ctypes.byref(value))
            print('loaded_version', family, path, 'status', rc, 'encoded', value.value)
        except (OSError, AttributeError) as err:
            print('version', family, 'UNAVAILABLE', type(err).__name__)
```

ADAPTATION：上述是拟议只读版本核验；实际可用 API/返回值以目标安装版本官方文档为准。包 metadata/build tag 不等于运行时链接版本；若库未加载，记 NOT_LOADED，不强行初始化 GPU 来补答案。torch 的导入可能使用其已有动态依赖，但本脚本不显式载入未映射的库。容器 digest/框架 commit 仅查本项目已指定环境，不列举整个容器系统或其他作业。

## 两机可达性与 Redis（条件明确后才执行）

两端地址由用户确认后分别运行 `ip route get <peer_address>`；若允许轻量网络探测，再执行 `ping -c 2 -W 2 <peer_address>`，TCP 仅查获准单个地址/端口，例如 `nc -z -w 3 <peer_address> <approved_port>`。路由/ICMP 成功不证明跨机 NCCL 或 RDMA 可用；此证明留给后续单独获准的 M1 基线。

Redis 位置未知时只登记，M1a 不新建服务。对用户指定且获准的现有实例，可用其现有安全认证渠道执行 `redis-cli -h <approved_host> -p <approved_port> PING` 和 `INFO server` / `INFO memory`；不把密码放 `-a`、shell history 或日志，不查 KEYS/SCAN/客户端命令。跨机服务仅在信任边界内，资源计划要写明 owner/端口/现有内存与许可范围。

## M1a 输出与退出条件

ADAPTATION：每次 `run_id` 输出 manifest、两机原始命令日志、GPU/NIC 对应表、软件实际加载版本、环境差异与未运行项；确定后续 M1 最小 rank 和 Python 环境。当前第二台、环境、Redis、资源权限未知，不把它们补成默认值。

M1a 完成即停并审核。M1 的单机 2rank、两机各 1rank、全卡 AllReduce/DDP/原生 MoE 启动均是后续任务，本轮及 M1a 不执行。故障注入、降频、网络背景流量、系统升级均不在此计划授权范围。

## 2026-10-10 M1 授权更新

ADAPTATION：用户已一次授权完整 M1a–M1e，无需 M1a 后单独审批。追加允许已有作业 GPU 上低显存小测试（不要求完全空闲），并明确批准仅项目隔离环境 torch==2.8.0 CUDA12.8 wheel 及固定依赖；不改变系统驱动/系统库，保留原安全与独立 run_id 限制。两机外网不可达已由实测及用户确认，允许经本地中转离线依赖；原始拓扑/UUID/作业/地址日志只留服务器。当前状态由 docs/m1 与 STATUS 给出。

M1a实际盘点已完成，后续依赖/GPU基线在用户完整M1授权下执行；原“M1a完成单关审核”已由本轮授权覆盖。完整机器/地址/UUID/拓扑日志保留本机runs，公开计划中的原机器地址已脱敏，原文备份在runs/m1-public-redaction-20261010T035835Z。
