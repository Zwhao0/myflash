# 离线输入 schema_version=1
接口由flash/profile_input.py验证；输入示例tests/m4_cases/single_group_min_rank/input.json，真实白名单示例multigroup-input-epoch1.json。

| 字段 | 类型/单位/语义 |
|---|---|
| context.run_id/profile_epoch | 非空字符串/正整数；一次分析只允许一个run和一个epoch；window_id可额外记录预先选择窗口，不接收故障真值 |
| records[].node_id/global_rank | 显式节点字符串/非负全局rank；不等同comm_rank |
| id_hash | 64位小写SHA256十六进制；可靠UNIQUE_ID_SHA256；跨进程键，不看comm_ptr |
| process_instance/comm_generation | 进程生命周期字符串/正整数，本地实例与全局hash分离；跨rank的generation无需相等 |
| comm_rank/comm_size | 本地communicator rank/成员数；验证全局rank映射双射和实际成员集合 |
| timing_scope/status | collective或group_shared；仅VALID参与；unsupported/invalid/null拒绝整个声明窗口 |
| duration_us/duration_unit | finite非负数/us；m3_cuda_event_v2额外要求>0，synthetic_nonnegative_v1仅CPU构造允许零；不从CPU提交时间替代 |
| state/result/cuda_results | state1、NCCL成功0、11槽CUDA API结果：前10必须0，第11必须-1；来源M3 ABI2定义 |
| api/count/count_unit/datatype | NCCL公开操作名、非负元素数/elements、NCCL2.27.3 datatype枚举0..11（实测安装header含两种Float8）；duration比较保留异构风险 |
| group_id/group_depth/thread_id | Group外ID/depth0；共享Group正ID/depth，线程用于区分本地outer scope；嵌套共用外层ID |
| sample_seq | 进程内唯一正publication序号；重复拒绝；raw全文件还检查连续性与digest |
| communicators[] | 所有预期hash/members/local_instances；局部实例包含node/globalrank/process/generation/comm_rank/expected_samples/expected_records。samples是去重scope数，records是成员记录数；这份期望应来自工作负载/采集manifest，不从残缺记录猜成员 |
| parallel_states[] | label/members/evidence；可用id_hashes显式消歧；没有id_hashes时只匹配真实成员集合；不按流量推DP/TP/EP；每声明hash必须匹配至少一个显式标签 |

CLI：`python3 scripts/m4_analyze.py --input <bundle.json> --output <prediction.json>`。
M3 raw：`--format m3_ndjson --records <完整每进程.ndjson列表>`；先全文件digest/context/连续性校验再按显式run/epoch选Profile collective。原raw各文件只能属于同一run。
M3公开profile CSV：`--format m3_csv --records docs/m3/profile-samples-node-0.csv docs/m3/profile-samples-node-1.csv --supplements <sidecar.json>`；context.source_run_policy=explicit_selection允许同一公开表内显式选择run，未选择行不混合。sidecar键run:rank:publish_seq，包含缺失node/pid或process_instance/thread_id/generation/comm_rank/size/identity_source/result和完整CSV的source_csv_sha256。必须有证据，禁止覆盖duration/API/count/dtype等原测量字段。没有补充拒绝，不能靠文件名猜身份。
M3机制samples CSV含case/warmup/独立参考时间，供外部回放器与evaluator选择既定窗口；先与Profile CSV/raw关联，移除case/真值后构建schema1。定位器没有case/target/故障类别接口。
输出有效分析exit0：NO_CANDIDATE、PROVISIONAL_CANDIDATE或AMBIGUOUS_SPEC；坏输入exit2 REJECTED_INPUT。final_fault_ranks始终空，G04未解决；exit0仅离线运算完成。输出含成员/局部均值/样本数/完整性、双权重/双CV、max组/min rank依据、独立score、异构签名/Group风险与标签冲突。
