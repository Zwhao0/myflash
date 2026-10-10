# GreyHound 上游审计入口

本文件仅用于新项目参考 GreyHound 作者公开仓库，不代表借用任何过去失败的实现。本轮查阅的是作者仓库 wutianyuan1/Greyhound。代码搜索返回固定版本 d641b3997c17de700e1ef7d37e353418df7e336d；开展复现时仍须记录实际 checkout 的完整SHA。这里只列已经查看的入口，不声称完成上游全部审计或编译验证。

```text
https://github.com/wutianyuan1/Greyhound
https://github.com/wutianyuan1/Greyhound/tree/d641b3997c17de700e1ef7d37e353418df7e336d
```

| 已查看入口 | 真实内容 | 对 FLASH 的处理 |
|---|---|---|
| README.md | A10四卡artifact说明；ACF检测、profiling/validation、precheck、mitigation；定制集群需修改路径/拓扑/数据配置 | 参考启动链与依赖，不把A10注入频率或所有训练脚本原封不动移植到H800 |
| detector/ncclprobe.cpp | NCCL包装、InitRank/InitRankConfig/Split、unique ID hash、Group记录、调用压缩、状态检查 | 复用前验证hook覆盖和测量语义；剥离验证与训练控制依赖，保留上游快照 |
| detector/event_handler.cpp | 读取Redis并通过world communicator广播控制；STATE_VALIDATE暂停循环；执行GEMM/P2P任务 | 这不是FLASH的本地控制器→共享内存0/1路径，不得直接作为默认流程 |
| detector/control_plane/slow_detection.py | ACF找周期；rb.beast(ts, season='none', ..., hasOutlier=True)；趋势变点与概率；离群过滤 | 参考Rbeast调用；用框架迭代输入替代ACF需显式改造；参数不能照抄当成FLASH参数 |
| detector/control_plane/global_analyzer.py | id_hash构建clique；TP/DP/PP标签；同标签内最大平均时延与median阈值筛选可疑组 | 可复用映射思路，不等于已包含FLASH的rank最小延迟定位和expert标签交叉证据 |

## 三个必须点名审计的地方

**控制路径耦合。** ncclprobe.cpp 中 CHECK_PAUSE_MAGIC=503，特定ncclInt8调用设置should_check；GroupEnd之后可进入event_handler。event_handler使用NCCL广播并可暂停训练。FLASH默认路径须确认这些依赖是否彻底解除，而不只是删掉Python里的validation函数。

**Split标识。** 上游ncclCommSplit声明char buf[128]后将其用于hash，并发出“不支持通过split获取unique ID”的警告。此路径不能作为稳定全局组标识的已验证实现。不能仅通过清零buf“修复”，因为那仍无法区分不同split组。

**统计库与默认值。** 上游确实调用Rbeast的rb.beast；validate_performance_drop的默认值和比例定义不等于中文论文所给参数。local_controller.py检索片段还显示作者曾为Rbeast段错误使用独立进程。这里只能说明新项目需要单独验证 Rbeast 在目标环境中的兼容性。

## 本轮外部核对（与论文内容分开）

NVIDIA官方NCCL文档说明collective在GPU stream上异步执行；group内调用可能尚未提交到stream，必须关注GroupEnd语义。现代接口与本机版本未必一致，最后以固定部署版本头文件/源码及微基准为准。

Rbeast作者将库称为BEAST（贝叶斯模型平均与时序分解）；不能仅凭论文的BOCD简称推断其等同于Adams–MacKay的run-length在线递推。

OpenAI文档说明Codex会读取AGENTS.md，且支持按复现步骤、约束、最小修复和测试结果组织任务。本工作包其他.md文件需在任务中明确要求读取，不假设它们自动加载。

```text
https://github.com/zhaokg/Rbeast
https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/groups.html
https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/streams.html
https://developers.openai.com/codex/guides/agents-md
https://developers.openai.com/codex/prompting
```
