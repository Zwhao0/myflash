# M3设计
PAPER: SPEC S4/论文§3.2.3 pp27–29与§3.3.1 pp32–33，0/1状态、stream起止Event、stop同步、Group共享耗时。
ADAPTATION G05/G07/G16: ABI2安全升级，旧ABI拒读，不原地转换。每进程请求控制word=(epoch<<1)|state，epoch不能倒退、已结束epoch不得重新Profile。本地C API flash_profile_request与Reader.request均只提交请求。非Group collective入口/最外层GroupStart读取控制，TLS冻结至scope结束，实际state/epoch逐事件记录。Header applied_control仅表示最近一个调用线程的边界，不代表所有rank已生效；完整性由独立验证器核对每rank/每轮记录。任何缺rank、损坏、丢失、失败或timeout均不能完整PASS。未调用线程不产生ACK，不伪造成功。
ADAPTATION: 非Group单操作路径覆盖M2真实PyTorch无显式Group行为；Group同stream/同设备/可靠阻塞communicator时从首条成员之前到成功外层End提交之后计时。成员延后发布，scope=group_shared，每个成员保留原result和group_id，只有一个共享时间样本，不解释为单操作内核耗时。
UPSTREAM: NCCL GroupEnd成功仅保证提交而非GPU完成；嵌套内层不得等待。inProgress/失败Group不记录stop、不等待、duration=null。多stream/多设备/capture/未知或非阻塞comm显式unsupported。nonGroup Send/Recv不支持同步剖析，以免序列发送等待制造死锁。未包装API不承诺计时。
Event在Profile scope内新建新销毁，无缓存/复用生命周期；因此Monitor没有残留Event、没有新增Event或GPU同步调用。CUDA每API rc记录，未调用=-1，失败duration=null；ms×1000->us。sync_block_ns另计主机等待，绝非替代GPU时间。不存在低开销承诺。
Reader: 完整newline记录必须逐条连续且context一致；仅最后未完成newline且未被ACK的片段可以truncate+fsync，完整记录保留、未ACK重放去重。中间坏JSON/sequence/context、ACK已确认但文件缺失/截断均硬失败。正常CLI写flush/fsync后ACK；直接Reader.read默认ACK语义仍由调用方负责持久化。
EXTENSION: 无BOCD/Redis/检测/定位/恢复；注入参数仅测试负载和独立评估器持有，Probe不读取真值。

## ABI2字段与资源约定（ADAPTATION）
ABI2 Event固定280字节，ABI1为192；Header ABI/layout必须全部匹配。安全升级需要结束旧run、Reader持久化/排空并仅unlink其对象，再使用新run_id；不在活动ABI1对象内升级。
CUDA结果数组0–9顺序：get_device、capture_query、create_start、create_stop、record_start、record_stop、sync_stop、elapsed_ms、destroy_start、destroy_stop；第10槽汇总后续device查询/切换/恢复错误，成功为未设置值-1，不能单独解释为完整调用轨迹。未调用值为-1；timing_status=0/1/2/3分别NOT_APPLICABLE/VALID/UNSUPPORTED/INVALID_DURATION；scope=0/1/2分别none/collective/group_shared。成员计数不能替代独立timing scope计数。
每个scope一对Event，Group各成员共用这一对，结束后销毁；不同scope重新创建，跨scope缓存复用未实现。任何内层End失败均锁存并使外层最终结果无效，不因后续成功掩盖失败。
CUDA Event时间不等于纯NCCL kernel runtime：开始与停止记录之间可能包含GPU队列等待、peer到达等待和主机后续提交间隔。GPU前置计算在另一compute stream完成，通过work_done Event让communication stream等待；Probe start在该依赖之后，故不会把目标rank已消耗的前置计算时间计入其通信区间。具体代码/证据见tests/m3_mechanism.py。
