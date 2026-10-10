# M4 结果（2026-10-10）
**确定性算法与已收到授权范围 PASS；完整科学最终判决未复现。** G04 OPEN，final_fault_ranks始终空；M4d消息在“进行”处截断，其未收到的额外条件 NOT_RUN/待补充，不能宣称额外验收完成。M4结束后停止，M5未启动。

## 输入与算法
schema1读取完整M3 NDJSON/带证据sidecar的公开Profile CSV/固定合成JSON。校验run/epoch、可靠id_hash、局部comm generation与进程实例、实际成员/local rank双射、声明全comm与各实例样本数/成员数、publication/digest、VALID/成功CUDA计时、单位及finite duration。缺失/坏值不补零；CSV补充不能覆盖测量字段。Group按外层进程/线程scope去重，nested保留depth；跨comm共享duration明确相关。
Stage1按同标签多组max communicator mean→CV0.1→最大组；仅单组直达Stage2、单rank排除。Stage2 rank均值CV0.1→最小rank。双权重和双std敏感性分歧、并列和多标签冲突都可见，不强行唯一判决。式3-1/3-2独立，clique mean score不替代max统计；API/count/dtype异构签名可见，不归一化。

## 固定 CPU fixtures
65项全部PASS，实际gpu-01 Python3.12.3；不是GPU实验。每项输入/手算期望：tests/m4_cases/<name>/input.json、expected.json；实际输出/退出：docs/m4/fixtures/<name>/actual.json、exit_code.txt；完整命令/日志路径见fixture-validation.json。坏输入exit2是预期拒绝；有效空预测/临时候选/规格分歧exit0仅表示离线分析完成。期望为固定手写常量/算式，测试不调用定位函数生成期望。
覆盖三同标签组、单组、CV两侧/边界/标准差口径分歧、max组与min rank、score独立、单rank/空输入/缺rank/缺sample/整个comm缺失/重复、零均值/NaN/Infinity/负值/boolean/单位、same-member不同hash、共享/嵌套Group/重复成员/相关跨comm、多标签一致/冲突、权重候选翻转、异构API/count/dtype及安装header Float8 metadata、raw digest/sequence/tail/context、CSV缺证据/坏证据/禁止覆盖时延。

## M3 真实回放
完整520机制样本全部保留；外部评估器按预先给定sequence窗口选择，两epoch不混合，case/目标rank不传给定位器。每窗口分别用全部13次和原M3每轮前3warmup固定排除的10次，共40个独立分析输出。两个口径均：16/16迟到窗口的排序候选匹配目标；4个normal窗口中3个输出临时候选（假阳性），1个空预测。不能称最终诊断precision/recall、自动端到端性能或论文实验结果。
已有已验证16rank AR192条、DDP320条Profile回放通过。DDP每rankepoch1=12、epoch2=8，混合API/count保留异构风险。Group02每epoch56条成员含16条UNSUPPORTED，两完整窗口明确拒绝，不偷偷丢掉后宣称完整成功。raw/公开CSV逐字段相等；CSV补充身份/节点/generation来自原raw而非地址相等或流量猜测。完整结果见m3-replay.json；原始raw留服务器，gpu-02证据直接项目内传到gpu-01 runs/m4-replay-source，不下载/上传原始敏感数据。

## 有限真实多组
run_id=m4-multigroup-normal-01，gpu-01原获准M1 UUID集合前4张H800；PyTorch2.8.0+cu128/CUDA runtime12080/NCCL22703，沿用低资源CTA/NVLS设置。单机4rank，DP三组[0,1]、[2,3]、独立[0,1]；TP两组[0,2]、[1,3]。DP/TP为负载显式测试标签，不称真实MoE框架并行。
两轮Profile各60条，五个可靠hash、十个本地comm实例、每instance每epoch6条。两标签均真正执行Stage1并选最大组，Stage2按min rank，两轮都得到rank3、两个标签一致；独立真值为正常/空故障集合，故候选属于临时误报。保存统计/原测量/成员与预测，未改标签/时延/阈值或按結果删点。公开120条multigroup-profile.csv及两个epoch的输入/预测；process_instance仅隐私别名，发布前验证统计/预测完全相同。
训练/Reader/完整校验/精确清理退出均0，首轮launcher耗时约10.37s。原始退出/命令在runs/m4-multigroup-normal-01/control.json与command-0..2.log/node-0/manifest.json。末检查每PID显存980/980/978/978MiB，启动>=3072MiB余量；postflight只查本run四PID/GPU PID/精确shm前缀，残留均0。无故障注入、系统变更、其它作业干扰；300s独立进程组timeout保护未触发。新跨机多组/延迟注入多组/混合comm真实Group/Float8真实GPU工作负载 NOT_RUN。

## 回归与保留失败
原M3 Reader、缺rank/损坏验证与公开证据验证exit0；M1–M3/native原源及docs/m3对a1ed7e2字节不变，baseline-preservation.json。
回放尝试01 FAIL：公开CSV duration字符串未转数值；02 FAIL：错误假设DDP每epoch相同数量，实际已审核12/8；改适配后03和final均PASS，未改旧数据、断言或阈值。SSH首次私有连接说明解析错误exit255、初始化后一个只读hash命令Tcl引用错误exit1保留本地中转日志，均非GPU实验失败。本轮GPU测试无FAIL。
最终命令/退出/日志见VALIDATION与final-checks.json。源码初始提交d8f4867，后续边界补强/证据提交及完整GitHub tree同步见SYNC（历史SHA与内容树分开）。
