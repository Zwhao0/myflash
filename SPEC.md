# FLASH 复现规格：论文事实与待确认项

本文档以原论文第三章为依据。页码指论文印刷页；原 PDF 页码 = 印刷页 + 16。术语保留论文写法；对其正确性/普适性的判断应单列，不改写为已证明事实。

## S1 范围与三层结构

[论文 §3.2.1，pp.23–24]
NCCL Probe 运行在训练进程内，以 LD_PRELOAD 截获 NCCL 调用；本地控制器每节点一个，通过共享内存读取信息；全局控制器一个，通过 Redis 协调节点和执行诊断。

监控状态为 0，剖析状态为 1。FLASH 输出异常/慢 rank，当前复现不负责恢复。论文提及 Pre-check，但未在本章充分说明实施与验收步骤，见 GAPS。

## S2 常态监控：两条独立路径

[论文 §3.2.2，pp.25–27]
性能退化路径：框架在迭代结束后提供迭代时间 → Redis → 全局控制器。以 rank 0 的迭代时间为基准，不从 NCCL 调用推断迭代边界。

停机路径：Probe 记录 NCCL 调用元数据 → 共享内存 → 本地控制器统计调用新鲜度 → 超时报告。监控模式不启用 CUDA Event。

框架上报的列表示例为 iter_time_{rank}，值为 iteration:time_ms；最多保留 500 条。运行隔离前缀是建议的工程适配，不是论文原字段。

## S3 检测与过滤

[论文 §3.2.2、§3.3.2，pp.26–27、33]
论文称检测为 BOCD，并写明使用 Rbeast；滑动窗口 30 个迭代；thresh_prob=0.8；degradation_thresh=0.2；前 3 个迭代过滤；z-score>3.0 的异常点移除；相邻变点距离小于 2 时过滤后续变点。

持久性判断：
- baseline_mean = 变点左侧均值。
- degraded_mean = 变点右侧（包含变点）均值。
- recent_mean = 右侧去掉变点后的均值。
- recovery_ratio = (degraded_mean - recent_mean) / (degraded_mean - baseline_mean)。
- recovery_ratio >= 0.75 时过滤为瞬时波动；否则保留为持续退化候选。

不能从这些参数推断所有实现：退化比例的分母/方向、空切片、右侧最少点数、零方差/零分母、异常点过滤后的索引映射、Rbeast 的参数和随机性均需明确。§3.4.3 的“持续超过20个迭代”与 §3.4.5 的“1–2个迭代”存在待核对分歧。

## S4 按需剖析

[论文 §3.2.3，pp.27–29]
全局控制器写状态 1；本地控制器以 100–500ms 轮询并写共享内存；Probe 在 Group 结束处读取状态并切换。采集窗口公式是 max(latest_iter_time × 2.2, 20.0)，20.0 为秒尺度下限。上报迭代时间是 ms，具体实现必须显式转换到秒后使用公式。

CUDA Event 放在 NCCL 执行区间的相应 stream 上；论文写有 cudaEventSynchronize(stop_event)，不能声称剖析路径完全不阻塞主机线程。基线不得未经许可换成异步回收计时方案。

[论文 §3.3.1，pp.32–33]
Group 级优化为一个 Group 一对起止事件，将测得总耗时写回 Group 各条记录；非 Group、嵌套 Group、多 stream、不同 communicator、CUDA Graph 和异步 communicator 初始化的具体处理未充分给出，需按实际工作负载逐项确认。

本地按 communicator 聚合 min/max/avg/std，上报全局；分析完成回到状态 0。profile_epoch、节点 ACK、数据完整性和超时是拟议工程适配，不是论文已定义协议。

## S5 communicator 与并行语义

[论文 §3.2.3、§3.3.1–3.3.3，pp.30、32–35]
简化模式记录 communicator 地址、id_hash、global_rank，避免依赖 NCCL 内部 ring/tree。按 id_hash 建通信组，结合框架上报的 parallel states 标记 TP/DP/PP/expert_dp/expert_tp 等标签。无法判定者为特殊组。

“应用/框架进程组”“NCCL communicator”“一次 ncclGroupStart/End 批量提交”是不同对象，实现中不能混为同一 ID。

框架需上报迭代时间和并行组成员信息，因此应表述为“Probe 透明接入 + 框架少量集成”，不承诺完全零修改。

## S6 两阶段定位

[论文 §3.2.3、§3.3.2，pp.30–31、34]
同标签内先过滤单 rank 组。每组计算 max_avg_latency，即组内各 communicator 平均延迟的最大值。若仅一个可用通信组，跳过组间筛选直接进入组内分析；多个组时检查组间 CV，CV<0.1 时跳过，否则筛选最大者作为候选。

候选组内按 rank 聚合时延并计算 avg_latency；rank 间 CV<0.1 时跳过，否则最小 avg_latency 的 rank 成为候选。论文另写默认 20% 离群筛选阈值，但分母/参照量未完整定义，实施前须确认。

多个标签指向同一 rank 时汇总证据。论文没有完整定义冲突消解、最小证据数、置信度标定和多故障候选规则，不可自行补成“论文算法”。

图3-7 / 式3-1 使用通信组平均时延构造 score_clique；正文运行算法的 max_avg_latency 不等于该平均量。图3-8 / 式3-2 使用 (组内rank时延均值 - 该rank均值) / 组内rank时延均值。分数不是经过校准的故障概率。

## S7 Fail-stop

[论文 §3.2.4，p.31]
窗口随迭代时间变化，例如 2 倍迭代时间；窗口内无新 NCCL 调用时上报 failstop_ranks。本章没有证明该规则能区分根故障 rank、通信中被连带阻塞的健康 rank 和正常长计算阶段。验收必须同时看检测事件与实际报告集合。

## S8 MoE 和已声明限制

[论文 §3.1.3、§3.5，pp.23、46–47]
利用稳定的注意力层传统并行通信及专家数据并行提供定位信息，不等于直接分析所有 EP/AllToAll 通信。当前不覆盖 DeepEP/Gloo/MPI，不直接完成硬件/软件/计算/网络根因分类。

当前统计上报省略 count（这里指通信数据量），不同消息大小/阶段的绝对时延比较可能有偏差。原始记录保留通信 count/dtype/操作类型可作审计；基线分析仍应保留论文口径。改用带宽、分桶或时延归一化属于后续扩展，不能静默代替基线。

## S9 原实验条件与数值

[论文 §3.4.1，pp.36–37]
原实验：2 节点，每节点 8 张 H200；软件表列 Ubuntu 24.04.2、CUDA12.9、NCCL2.26.5、Python3.12.3、PyTorch2.8.0a0、megatron-core0.12.1、Transformer Engine2.4.0、FlashAttention2.8.0。版本标签不能代替容器 digest、框架 commit 和实际加载库路径。

模型表：总参数约13.3B、激活参数1.4B、36层、hidden1024、16 attention heads/8 KV heads、128路由专家、top8、1共享专家、专家中间维896；训练表：GBS4096、MBS8、Seq4096、muon、lr1e-3。具体模型构造、优化器来源、数据处理和启动脚本仍需补齐。

默认并行 EP8/TP1/PP1/CP1/Expert_DP2；图3-10列出 EP8/TP1/PP1、EP4/TP2/PP1、EP4/TP1/PP2、EP4/TP2/PP2，均在16GPU环境。不能只凭标签数量推断实际rank成员。

[论文 §3.4.3–3.4.6，pp.38–45]
监控吞吐实验250迭代；AllReduce 4/8/16/32/64/128MB，预热500次，每档10000次、每100次一批。原文报告开销、精确率/召回率和耗时只是待复现实验结果，不是本项目已取得的结果。
