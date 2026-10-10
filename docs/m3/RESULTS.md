# M3结果
M3在下列支持范围内完成，停止等待审核；M4及后续未开始。实测gpu-01/gpu-02，各8×H800，PyTorch2.8.0+cu128、NCCL22703、CUDA runtime12080；沿用M1低资源配置。所有完整原始日志只在服务器runs；公开CSV是隐私白名单导出，数值没有调整。

## 六项验收结论
1. **手动状态机PASS**：ABI2；进程本地API/Reader.request；非Group collective入口和最外层GroupStart生效，Group内固定state/epoch；两轮0→1→0正确。epoch保存历史而不清零。每rank证据齐全才视为完整Profile；请求返回0只代表请求接受。Reader PASS只代表传输/排空通过。
2. **CUDA Event计时PASS（支持范围）**：start在真实NCCL前，stop在真实提交后；stop同步后ElapsedTime ms×1000得到us。逐API结果与额外主机同步等待单列；错误/不支持输出null。Group成员复用同一对Event，跨scope新建并销毁，正常记录创建/销毁rc均0。CPU mock错误释放后live Event=0。没有缓存，也没有无开销声明。
3. **单机/跨机现象支持受控到达偏斜机制**：CPU通信前20ms sleep，或compute stream的40次512×512 fp32 matmul→end Event→communication stream wait_event→Probe start。GPU计算不是host sleep。两种目标rank分别重复，全部原始样本保留。支持“迟到rank的这个通信Event区间较短”，不能推成所有计算/通信退化的普适规律。
4. **Group范围PASS（单stream、单设备、可靠阻塞comm）**：内层End没有等待，外层成功提交后才stop/sync；同组两个成员共享duration与group_id，scope=group_shared。Group测试每rank40有效成员记录、24有效计时scope；另16个多stream成员记录UNSUPPORTED/null。这个测试的验证PASS不表示整个含不支持场景的Profile窗口完整成功；final-validation的complete_profile=false。
5. **16rank PASS**：最新AllReduce保留每rank25次数值断言/SUM136，共192个有效Profile样本；DDP保留676参数、每rank20step、finite loss/grad/parameter、delta>0与同步误差0，共320个有效Profile样本。两个程序各两轮切换，最终Monitor、完整排空、精确unlink16。原M1文件与无Probe入口保留，native2rank复测exit0。
6. **科学假设仍未确认**：G09对GPU降频、通信拥塞、其它消息规模/算法/拓扑、真实MoE混合并行与并发故障的适用性；正常rank天然时延差异与误报边界；G04聚合权重/Group重复计数；论文20%阈值及G01/Rbeast等后续算法均未验证。原论文H200/原训练配置和性能数字没有复现。

## 命令、退出、日志与计数
完整入口与逐项断言见VALIDATION；这里四个0依次是训练/Reader/验证/清理。每run的日志根为runs/<run_id>/node-R，另有control/exit/verify/cleanup-node-R文件。每个节点attempts=write_pos=read_pos=NDJSON条数，publish_seq连续，full/lock/errors/bad/poison均0。没有用缺失值补零。

| run_id | 机器 | NDJSON事件（各节点） | 退出码 |
|---|---|---|---|
| m3abc-local-01 | gpu-01 | 275 | 0/0/0/0 |
| m3d-roce-01 | gpu-01/gpu-02 | 138/137 | 0/0/0/0 |
| m3e-group-01 | gpu-01 | 255 | 0/0/0/0 |
| m3e-group-02 | gpu-01 | 255 | 0/0/0/0 |
| m3f-allreduce-01 | gpu-01/gpu-02 | 955/954 | 0/0/0/0 |
| m3f-ddp-01 | gpu-01/gpu-02 | 1656/1659 | 0/0/0/0 |
| m3f-allreduce-02 | gpu-01/gpu-02 | 952/952 | 0/0/0/0 |
| m3f-ddp-02 | gpu-01/gpu-02 | 1647/1652 | 0/0/0/0 |
| m3d-monitor-local-01 | gpu-01 | 235 | 0/0/0/0 |
| m3d-monitor-cross-01 | gpu-01/gpu-02 | 121/117 | 0/0/0/0 |
| m3d-monitor-allreduce-01 | gpu-01/gpu-02 | 949/951 | 0/0/0/0 |
| m3d-monitor-ddp-01 | gpu-01/gpu-02 | 1647/1652 | 0/0/0/0 |
| m3d-monitor-lifecycle-01 | gpu-01 | 72 | 0/0/0/0 |

CPU最终suite：gpu-01 runs/m3-cpu-20261010T053356468174Z/manifest.json，六个完整命令退出均0；原11项ring、原4线程1205-event hook、Reader25次测试执行（包含原11项重复发现；新增3类恢复/协议测试）、Profile错误mock46事件（6有效、11无效、5不支持collective），缺rank/部分rank未进入第二epoch/timeout/丢失/损坏拒绝测试。不是GPU实验。最终更严格只读验证，两节点分别runs/m3-final-node-R/validation.log exit0、gpu-01 validation-tests.log exit0；公开final-validation-node-R.json包含完整Profile标志。

科学A–D及首轮F使用Probe SHA256 583371a93b85308c2f5db4d4c7980344d9dc9fea7714988545b5054e472a9b19；最终Group02/F02/16rank Monitor使用c9f6987d35d2bff32aed205c2bac0741a41fe6804861b2e82450f4369c541e77，两机一致。差异是补强失败内层End无效化；正常Event位置/单位/stream和原始实验标签没有变化。实际source_commit/diff/hash在每run manifest；核心实现提交ccded07、补强提交14a5c70，最终交付提交另由git log/SYNC查询，不自引用。

## 时延分布（us，中位数）
每环境/每rank/每case有26个原始Profile样本：两轮各13次；预先固定每轮前三次warmup，只以余下20次计算以下分布。完整26次均在samples-node-R.csv中，min/p10/mean/p90/max/std在distributions-node-R.csv中。没有依结果删异常点、调标签或改min/max。

| 环境 | 场景 | rank0 median_us | rank1 median_us |
|---|---|---:|---:|
| 单机 | normal | 45.760 | 20.688 |
| 单机 | cpu0 | 30.768 | 20166.368 |
| 单机 | cpu1 | 20171.600 | 31.008 |
| 单机 | gpu0 | 17.040 | 1835.616 |
| 单机 | gpu1 | 5177.456 | 26.736 |
| RoCE | normal | 99.440 | 45.184 |
| RoCE | cpu0 | 53.152 | 20189.408 |
| RoCE | cpu1 | 20216.289 | 58.960 |
| RoCE | gpu0 | 42.832 | 1832.160 |
| RoCE | gpu1 | 5418.208 | 58.224 |

cpu0/gpu0目标rank0，cpu1/gpu1目标rank1，由独立评估器给出。正常场景两个rank也不是完全等时；不将这个差异转成定位结论。GPU前置计算在独立stream上，comm wait依赖明确，目标rank start在该前置计算完成后执行，故其通信duration排除了自身前置工作。Event区间可以包含主机提交间隙、GPU排队/peer等待与其它stream竞争，不是纯内核本体耗时。尚无kernel级trace来分解这些组成，不宣称GPU计算退化或网络故障根因定位。

## 同步开销与资源
额外cudaEventSynchronize的主机等待时间之和：单机机制1247.265ms、跨机1254.398ms、Group02 1.240ms、16rank AR02 35.651ms、DDP02 122.267ms。按有效scope去重，Group成员共享字段不重复相加。各rank等待时间之和不等于作业墙钟开销；没有严格成对性能实验或“完全无开销”结论，创建/销毁/控制锁/Reader fsync等也有代价。
M3运行末每PID约982–1058MiB，均<=2048MiB，启动前每UUID>=3072MiB余量检查、1536MiB记录目标保留，非瞬时硬隔离。最终两节点分别检查62/50个本轮rank PID；本轮残留进程、GPU PID、共享对象均0，postflight-node-R.json对应完整服务器manifest/逐命令日志。无降频、OOM、网络拥塞、其它作业终止或泛化清理。

## 失败保留和边界
- 首轮build runs/m2-build-20261010T052107331199Z exit1：CUDA header重载函数地址歧义；修正公共C函数指针后新build通过，原日志保留。
- gpu-02首轮postflight exit1，底层git diff exit128：执行镜像没有gpu-01的64badbf Git对象；非GPU失败。保留runs/m3-final-node-1/postflight.log与原m3-postflight目录/2.log。改为比对审批源blob SHA256，gpu-01逐个git show64badbf核验后两机postflight2均0；未放宽文件范围或修改原M1/M2入口。
- 连接器search_branches一次传输失败；后续PR1读取和M3分支创建恢复。发布结果以SYNC回执为准，不能当GPU验收。
- 收尾白名单验证首次误用不存在的Python路径exit127，runs/m3-final-node-0/public-validation.log/.exit保留；改用python3后runs/m3-final-public/validation.log和validation2.log均exit0，没有GPU重跑或数据改动。
- 多stream/multidevice Group、capture与未知/非阻塞comm明确UNSUPPORTED/null；真实multidevice/capture/InProgress错误行为NOT_RUN，CPU mock仅验证拒绝/原返回码。Profile非Group Send/Recv不支持同步计时；其它Profile API、mixed-comm Group、default-stream、并发多线程Profile没有真实验收。CUDA Graph重放、GroupSimulateEnd等未包装API不承诺覆盖。没有真实CUDA错误注入。
