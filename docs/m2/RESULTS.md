# M2 结果
**M2在明确支持范围内PASS，完成后停止；M3 NOT_RUN。** 实测node-0/node-1 H800；所有当前训练主要communicator由阻塞InitRankConfig可靠映射，跨机hash/rank集合验证通过。Split全局身份UNRESOLVED、异步/其他初始化及未包装API不声称完整支持。
最终GPU源码快照：e45f90e455b5abb17914005f92824add519c8f64；两机最终libflash_probe.so SHA256相同：5e9d3cd786864c7fe4785504c2004a2c9fd18c563dd32ade4d6da95924b79cad。文档收尾提交的HEAD由git rev-parse查询，不能在其自身内容中自引用。
| 项目/机器 | 最终run与原始日志 | 训练/Reader/验证/清理退出码 | 依据 |
|---|---|---|---|
| M2a node-0/node-1 | runs/m2-build-20261010T045005041270Z / m2-build-20261010T045012613277Z，manifest及逐命令log | 全部g++命令0 | 现有host compiler构建Probe/Reader/测试库；header/runtime版本匹配，实际hook命中见GPU事件 |
| A node-0 | runs/m2-cpu-final2-20261010/0.log、1.log、manifest.json | 0/0 | 11项ring/Reader测试；4线程mock1205事件、rc4/5/7原样返回；不称GPU实验 |
| B node-0 native | runs/m2b-20261010-native-01/node-0与control/exit/verify | 0/不适用/0/不适用 | 2rank，原M1数值断言 |
| B node-0 Probe | runs/m2b-20261010-probe-04/node-0 | 0/0/0/0 | 2rank、238事件；25次×4096元素/rank，数值与native一致；真实InitConfig/AllReduce与生命周期命中，unlink2 |
| C 两节点各1rank | runs/m2c-20261010-probe-02/node-0/1 | 各0/0/0/0 | 118/117事件、rank0/1、同unique-id SHA256，完整映射；各unlink1 |
| D 两节点16rank | runs/m2d-20261010-allreduce-02/node-0/1 | 各0/0/0/0 | 955/951事件、全部16rank SUM136及25次数值断言；完整映射；各unlink8 |
| E 两节点16rank DDP | runs/m2e-20261010-ddp-04/node-0/1 | 各0/0/0/0 | 1659/1665事件、16rank各20step、676参数、finite训练/梯度/参数、delta>0、同步误差0；各unlink8 |
| F node-0 | runs/m2f-20261010-lifecycle-03/node-0 | 0/0/0/0 | 72事件；阻塞InitConfig、Group内InitRank及延后mapping、嵌套Group内外、AllGather/Broadcast/Reduce/ReduceScatter/Send/Recv、Split、Finalize/Destroy；unlink2 |
| 跨节点/语义复核 node-0 | runs/m2-final-validation2-20261010/validate.py、validation.log、manifest.json | 0 | 实际PID=训练PID、22703/12080版本/项目库路径、执行路径hash一致、同hash全rank集合、原M1源码未修改、native/Probe数值一致、真实unlink数一致 |
| 结束资源/二进制检查 两节点 | runs/m2-postflight-final-20261010，manifest及00..日志 | 每命令0 | 本轮58/42个rank PID检查均已退出、本次GPU PID和shm对象剩余0；nm无CUDAEvent/同步/控制符号，两机Probe哈希一致 |
全部正常Probe run：publish_seq连续、读=写=attempts，full/lock/error/bad/poison计数均0；没有补零。消息count始终保留，未压缩记录或过滤小消息。公开白名单详见evidence.json；完整命令见VALIDATION和服务器control/manifest，完整日志仅服务器。
## 实际API覆盖与范围
真实GPU命中：InitRankConfig、InitRank、GroupStart/End、AllReduce、AllGather、ncclBcast（DDP每rank26）、ncclBroadcast（直接API测试）、Reduce、ReduceScatter、Send、Recv、Split、Finalize、Destroy、Count、UserRank、GetAsyncError、GetUniqueId（创建端）、GetVersion。与静态libtorch_cuda符号引用分开统计，不能由AllReduce结果推断所有API。
已有包装但未做真实GPU验收：InitAll/Scalable、Abort、Register/Deregister、MemAlloc/Free。InitAll/Scalable身份UNSUPPORTED；非阻塞配置/返回InProgress只在CPU mock验证透传与UNSUPPORTED/空hash，真实异步初始化NOT_RUN。
未包装：GroupSimulateEnd、CommShrink、WindowRegister/Deregister、RedOpCreate/Destroy等；ErrorString/LastError直接透传。Graph、多设备同进程、多stream Profile均NOT_RUN。Split只支持本地对象生命周期与原通信数值，跨进程新组身份不支持；没有从父comm或随机数据制造子组hash。
## 历史失败与观察
- runs/m2a-compile-20261010：仅runtime headers编译exit1缺crt；加入现有Triton后exit1缺nv/target；仅项目CCCL headers补齐后exit0，无nvcc/系统升级。
- m2b-20261010-probe-01：训练/Reader0，验证1（验证器错误要求PyTorch AllReduce路径必须Group）；Group要求在F独立实测保留，后续新run通过。原FAIL未改写。
- m2e-20261010-ddp-01：两机训练/Reader0，验证1/1（验证器把实际Bcast写成Broadcast）；修正为真实API名并加强为26/1/23精确通信覆盖，新run通过。原FAIL未改写。
- runs/m2-cleanup-20261010：早期对象已不存在与node-1模块路径错误，外层SSH检查exit1；日志保留，未伪造当时unlink成功。原因未确认；后续同会话真实unlink通过。
- runs/m2e-20261010-ddp-03-access：SSH transport255/255，在两节点创建run/control之前退出；训练NOT_RUN，确认无该run资源，原因未断言。新run04完成。
- 首版暂存diff有尾空白错误，后续修正；没有独立退出码记录，不补造历史PASS。
## 资源与开销口径
最终跨机每PID运行末GPU用量：各1rank984MiB、16rank AllReduce1040MiB、DDP1058MiB；1536MiB只是记录目标，2048MiB是运行末保护检查，非瞬时硬隔离。每次仍有启动前≥3072MiB余量检查，保留M1低资源NCCL参数，不扰动其他作业。
首对单机高层启动器elapsed约6.97s native / 7.57s Probe，包含启动/训练/Reader收尾，且共享负载未隔离；仅功能记录，不是图3-5/3-6开销结果。没有新增Probe GPU时长测量，没有性能结论。
源码、DESIGN/RESULTS/VALIDATION/SOURCES、STATUS/GAPS将发布审核分支；原始runs、wheel/headers、二进制与完整机器信息不上传。M2结束，下一唯一任务是用户审核M2；未批准/未执行M3。
