# M2：完整 Monitor / Probe / 共享内存
用户于 2026-10-10 审核 M1 后一次批准 M2a–M2d；内部子任务无需再审核，完成后停止，不进入 M3。用户随后要求继续解决缺失编译头文件，不因该问题停在 M2a。仅将 CUDA12.8 CCCL12.8.90 wheel 解包到本项目 .build-deps-m2，既有运行环境和系统组件不变。
允许文件：native/、flash/、新增 tests/m2_*、scripts/m2_*、docs/m2/、本任务、STATUS/GAPS/.gitignore；必要时更新 ARCHITECTURE。M1 源码、失败记录和无 LD_PRELOAD 入口保持可用。
接口：Monitor=0；公开 NCCL 同名包装/原函数返回码；每进程 ABI1 环形共享内存；C++ bridge 读取/确认；Python 只校验和保存。
测试：CPU并发/异常/重启/清理；单机2rank原生与Probe；两机各1rank；两机16rank AllReduce与20步DDP；直接NCCL Group/初始化/生命周期测试。
退出：每普通GPU测试预算≤300s，M1 UUID来源、启动前≥3072MiB余量、1536MiB记录目标/2048MiB运行末检查；仅结束本次独立进程组，清理已验证的本run闭合排空对象。
PAPER 来源§3.2.1/3.2.2/3.3.1；UPSTREAM 官方2.27.3 headers/docs与PyTorch2.8 APIs；并发、SHA256身份、run隔离和可靠确认属ADAPTATION；无GreyHound源码复用、无CUDAEvent/额外GPU同步/Redis/检测/定位。
