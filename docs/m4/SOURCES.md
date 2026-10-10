# M4 来源
PAPER：references/chapter3.pdf §3.2.3 pp30–31/§3.3.2 p34/式3-1 p41/式3-2 p42；全文+完整页图核对。SPEC S5/S6/S8；运行排序与绘图score严格分离。
UPSTREAM：官方[NCCL2.27.3 communicator](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/api/comms.html)、[CUDA12.8 Event](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-runtime-api/group__CUDART__EVENT.html)、[PyTorch2.8 TCPStore](https://docs.pytorch.org/docs/2.8/distributed.html)。本轮阅读官方文档，实测运行库仍由每rank的loaded_versions核验。未复制官方库源码。
本项目已审核来源：服务器a1ed7e2/tree177745dd等PR2 head30ca740；flash/reader.py NDJSON字段/digest、scripts/m3_export.py公开CSV、tests/m3_mechanism.py ctypes+TCPStore小负载，tests/m1_baseline.py版本/内存检查。scripts/m4_launch.py从该提交scripts/m3_launch.py/main保留UUID/300s/Reader/独立PG检查，仅替换M4入口与源hash覆盖。M1–M3源代码与原始数据不改。
ADAPTATION：schema1/完整性manifest/严格拒绝；scope去重/共享相关性；双权重与双std敏感性；tie与标签冲突输出；CLI/离线回放/evaluator隔离；有限多组正常负载与资源验证。
EXTENSION：synthetic_nonnegative_v1仅固定CPU fixture可精确零，不等同真实M3 CUDA Event有效计时（要求>0）。实验性统计敏感性不是最终FLASH判决。多组DP/TP为显式测试标签，仅验证通信结构，不称真实MoE并行部署。
没有GreyHound源码复用，没有旧失败实现访问；无BOCD/Rbeast/Redis/自动控制/恢复/降频/OOM/网络干扰。

UPSTREAM补核：实测项目NCCL2.27.3 nccl.h的ncclDataType_t包含0..11，Float8e4m3/e5m2为10/11；离线metadata校验据此接受，不宣称真实Float8 GPU workload已测。
