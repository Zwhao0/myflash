# M3来源与分类
PAPER：references/chapter3.pdf第三章§3.2.3 pp27–31、§3.3.1 pp32–33；SPEC S4/S5；0/1、stream Event、stop等待、Group共享时长、迟到rank短通信时延均来源于论文，后者仍是需实测的假设。没有采用图3-4数值断言。
UPSTREAM：已阅读 [NCCL2.27.3 Group API](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/api/group.html) 与 [Group用法](https://docs.nvidia.com/deeplearning/nccl/archives/nccl_2273/user-guide/docs/usage/groups.html)：返回成功意味着stream提交；内层End不提交全部工作；不能在外层End前同步；非阻塞InProgress不能推断已提交。
UPSTREAM：已阅读 [CUDA12.8 Event](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-runtime-api/group__CUDART__EVENT.html)：Event记录当前stream已排队内容，EventElapsedTime单位ms；同步等待捕获工作完成，default Event等待可能占用CPU；Event在完成前可销毁，由runtime异步释放。其它stream竞争可影响Event区间，不能把其称纯内核本体时间。
实际API签名/编译来自M1项目runtime12.8.90/NCCL2.27.3 headers；现有Triton/项目CCCL开发headers/g++与OpenSSL沿用M2，不安装任何新组件。CUDA创建函数因官方C++ header含重载，使用与公共C声明一致的函数指针，首轮编译失败留证。actual ncclGetVersion22703、cudaRuntimeGetVersion12080和实际映射路径由每rank验证。
ADAPTATION：native/ring.hpp/ring.cpp的ABI2、control word与事件结果、native/probe.cpp的非Group边界及单操作计时、TLS固定Group状态/epoch、复杂范围拒绝、逐API结果/主机同步耗时；flash/reader.py的NDJSON摘要与尾部恢复；tests/m3_*机制/错误/缺rank测试与scripts/m3_*验证/导出/资源边界。具体字段/测试证据见DESIGN/VALIDATION。Group成员复用同一对Event，跨scope新建并销毁；没有跨scope Event缓存，额外创建/销毁开销没有藏入低开销宣传。
本项目M2源提交64badbf tree79a1254与PR1最新f8316cf完整文件树相同；PR1已经merged。服务器M3分支以64badbf为起点，保留所有原提交。复用本项目M2 scripts/m2_launch.py、m2_run_node.py、m2_build.py、m2_verify.py的main流程创建独立M3入口；tests/m3_regression.py经runpy执行未修改的tests/m1_baseline.py，只在wrapper手动请求状态，全部原数字/训练断言保留。
全部Probe/Event逻辑独立编写，只调用公开API，没有复制NCCL/CUDA/PyTorch实现；没有读取或复用GreyHound源码，许可证仍未作为复用依据。没有访问旧失败项目。
EXTENSION：本轮没有Redis、BOCD/Rbeast、检测、自动定位或训练恢复。脚本计算分布/时延差只是独立评估；注入参数由负载和独立评估器持有，Probe不读取真实目标rank/类别。GPU降频/OOM/网络拥塞与其他作业进程终止不在授权范围，均未执行。
