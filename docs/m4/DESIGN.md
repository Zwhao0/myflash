# M4 设计与来源边界
PAPER §3.2.3 pp30–31/§3.3.2 p34：id_hash通信组、显式parallel states标签、单rank排除、max communicator mean选择最大组、rank平均选择最小rank、CV门槛0.1。相同成员不同hash仍是独立通信组。
PAPER pp41–42 式3-1/3-2独立score函数，score不替代max_avg_latency、不称概率。
ADAPTATION G05/G07/G16：schema1；manifest列出全部预期hash、真实成员和每个进程内comm实例、预期独立计时数与成员记录数。缺失/坏数/不支持使窗口拒绝，不补零。raw校验摘要与完整publish连续性；公开CSV缺失的node/generation/identity/result等必须用逐publish样本sidecar或raw证据补充，缺补充拒绝。
ADAPTATION G05：group_shared按(run,epoch,node,process_instance,thread,group_id)验证同一scope字段一致；每个本地comm在scope内最多贡献一次。嵌套成员保留group_depth，共用外层ID。跨comm共用scope是相关观测，不声称独立、报告风险。
ADAPTATION G04：同时公开population与sample CV；零均值CV未定义。选population口径并标明；若两种口径跨越门槛，报告AMBIGUOUS_SPEC而不强判。并列最大组/最小rank保留所有并列项。
G04未解决：按独立scope样本数加权与每个本地comm均值等权两种rank统计都输出；候选不同则AMBIGUOUS_SPEC。20%参照未定义且不启用；确定排序仅PROVISIONAL_CANDIDATE。标签冲突展示各标签证据、不加权投票。
ADAPTATION G15：API/count/datatype异构风险可见，始终分析duration_us，不按消息大小归一化。
输入没有故障目标/类别，外部窗口选择只能显式记录选择来源；评估真值只给独立evaluator。M3 normal数据也按同一规则回放，保留可能误报。
