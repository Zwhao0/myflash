# M2 Monitor 设计
本文件描述当前实现与支持范围，验收结果另见 RESULTS/VALIDATION。所有实现独立编写，不复用许可未核验的 GreyHound。
PAPER：第三章§3.2.1 pp.23–24、§3.2.2 pp.25–27、§3.3.1 pp.32–33：LD_PRELOAD、首次调用惰性初始化、Monitor=0、调用元数据、环形共享内存。M2不实现调用新鲜度告警，不实现Profile。
UPSTREAM：签名来自项目NCCL2.27.3 nccl.h；GPU调用由原函数执行，包装返回同一个ncclResult_t。RTLD_NEXT解析，必要时从显式已加载库RTLD_NOLOAD解析；无法解析则显式exit127，不能伪造NCCL成功。TLS重入保护避免包装自身递归；没有持有元数据锁调用NCCL。
ADAPTATION：每进程一个0600 POSIX shm对象，名字包含run/node/PID/创建单调时间，Header中再次校验完整run/node。对象创建O_EXCL，posix_fallocate预先保留整个容量，失败显式禁用采集并保留原NCCL调用；正常退出关闭位并保留对象供Reader排空，在同一次测试会话内最后仅按当前run的已验证清理列表unlink。不清空/dev/shm。
## ABI与发布协议（ADAPTATION，G07）
ABI1仅当前Linux x86_64/glibc进程共享pthread ABI；Header记录magic、ready、ABI、header/event字节、容量、state、PID/global_rank、run/node、created_ns、write/read绝对指针、attempts、full/lock丢失、错误、bad_records、closed/poisoned。Event固定192字节。容量默认8192，允许1..1048576；指针模容量选槽，绝对publish_seq自1递增。容量/指针/ABI不合法拒读，不补零。
所有记录复制、发布与确认由C++持有PTHREAD_PROCESS_SHARED + ROBUST mutex；解锁/加锁建立发布顺序。pthread_mutex_clocklock使用CLOCK_MONOTONIC截止；锁获取最多等待10ms；写者锁失败记录dropped_lock，不改变原NCCL返回码。attempts/dropped/errors使用x86_64锁自由64bit GCC原子；满缓冲拒绝新记录并计dropped_full。正常发布attempts=write_pos，包含可观测丢失时另计数，错误路径单独记录，不承诺无损无限容量。
Reader单实例flock排他，仅C++ bridge触碰映射；Python不解析pthread布局、不直接竞态读写。读取先peek复制完整槽并校验publish_seq与FNV1a64结构校验和，之后确认才推进read_pos。CLI写入NDJSON、flush/fsync后ACK；重启从共享read_pos继续，已持久化未ACK事件按publish_seq去重。标准Reader.read默认立即ACK，调用方取得记录后的持久化由调用方负责。损坏槽计bad_records/errors且显式报EBADMSG；持锁进程退出则EOWNERDEAD→poisoned，停止读写，不猜测修复部分记录。被毒化对象只人工针对精确对象审计处理，不自动清理。
这些措施替代论文Python无锁读取/清空方式；不同并发协议和fsync开销均是工程适配，不声称论文纳秒开销。
## 事件字段与单位
| 字段 | 单位与范围 |
|---|---|
| run_id/node_id/PID/global_rank | run≤80、node≤32 ASCII字母数字下划线连字符；PID进程标识；global_rank来自torchrun RANK，绝不由comm_rank代替 |
| timestamp_ns/thread_id/call_seq | CLOCK_MONOTONIC纳秒、Linux TID、进程调用进入序号；跨线程调用返回可乱序，跨节点时间不可相减 |
| publish_seq | 在本进程buffer内发布顺序；与调用进入序号不同；COMM_MAPPING是额外元数据记录，沿用初始化call_seq |
| comm_ptr/comm_generation | 本进程指针uint64与本进程生命周期序号；跨进程没有地址可比性 |
| id_hash/identity | 128字节ncclUniqueId的SHA256十六进制，来源UNIQUE_ID_SHA256；Split为UNRESOLVED_SPLIT且空hash；未知空hash；Group内初始化先PENDING_GROUP，GroupEnd成功后发布COMM_MAPPING |
| comm_rank/comm_size | NCCL组内rank和size；仅可验证的初始化输入有效，未知=-1，不等同global_rank |
| api/result/count/datatype/op/peer | NCCL API枚举/原返回码；collective count为元素数；Register/MemAlloc count为字节数；其他不适用；dtype/op/peer不适用=-1 |
| group_id/group_depth/stream_ptr | TLS外层Group批次ID与嵌套深度，外层开始分配进程唯一ID；非Group=0；stream本进程标识。Group不是框架训练并行组 |
不存储duration，不从CPU返回耗时生成GPU时延，不插CUDA Event或额外cuda同步。M1基准工作负载自身已有的CUDA Event/完成同步仍归M1数值验收，不是Probe行为。
## 支持边界
当前包装：AllReduce/AllGather/Broadcast/Bcast/Reduce/ReduceScatter/Send/Recv；InitRank/InitRankConfig/Split/InitAll/InitRankScalable；GroupStart/End；Finalize/Destroy/Abort；GetAsyncError/Count/UserRank/GetUniqueId/GetVersion/Register/Deregister/MemAlloc/MemFree。
可靠跨进程身份范围：成功阻塞InitRank/Config，含Group中初始化延后到外层成功GroupEnd；Split只保存本地生命周期，跨进程身份明确UNRESOLVED。InitAll/Scalable、配置blocking=0或返回ncclInProgress的非阻塞初始化不提供可靠身份，UNSUPPORTED_INIT；它们不能参加要求可靠组映射的验收。
GroupSimulateEnd、WindowRegister/Deregister、RedOpCreate/Destroy、CommShrink等当前未包装；ErrorString/LastError直接透传。实际GPU命中列表以真实记录为准，不将链接符号引用表视为动态覆盖。CUDA Graph、非阻塞Group提交、复杂多设备同进程未验收，不承诺覆盖；多stream元数据可记录但未验收Profile区间。
EXTENSION：没有引入GPU计时、Redis、Rbeast/BOCD、异常检测、定位、控制广播、暂停验证、ACF或缓解。M2后停止。

生命周期范围：已观察到早期SSH退出后对象消失，清除原因未确认；不保证跨最后登录会话保留。当前控制入口在同一会话内完成创建/读取/持久化/清理。记录在原函数返回后发布，保存返回前采集的调用进入时间，不作为停机检测实现。训练进程采用torchrun exec模型；fork继承已初始化Probe、非Linux x86_64/glibc ABI未支持。
