# 任务07：已批准G04显式入口与CPU验收

2026-10-11，限定CPU功能验收 **PASS**。新分支 `codex/m6b-ready-g3-g04-implementation` 从负责人批准的 PR17 HEAD `8fa096c9af00449a1ce940f99d153406cfe323e1` / tree `5f05021646305fffd23663fe42bfa92b7bac7d43` 开始。独立审核PASS及八项规则批准由负责人在本聊天明确报告；独立新增 `APPROVAL.json`，原任务06 null审批账本保持字节不变。未声称整体M6B-READY科学验收通过。

新增 `flash.localization.analyze_approved_g04(bundle)`，输入仍为原schema1 Profile bundle；原 `analyze(bundle)`、原CLI及控制器调用保持旧语义。原定位模块函数体完整字节保留，仅增加stdlib `Fraction` 导入和新函数。未修改 `profile_input.py`、G01/G02/G13、fixtures、原断言或原始历史证据。

## 来源与行为

PAPER：同标签排除单rank组；单组直达；多组以本地communicator均值的最大值计算组间CV、选择最大组；Stage2最小rank；式3-1组均值绘图诊断与Stage1分开。来源：PR17 `G04_DECISION_PACKET.md` 原审计p30/31/34、式3-1 p41、式3-2 p42。本轮继承精确源码/论文摘要与审计，没有重新声称PDF视觉审核或读取任何旧失败项目。无GreyHound/外部算法源码复用。

ADAPTATION：负责人批准 S1-MAX/W-EQUAL/R-GROUP/T-GE/C-GUARD/N-GUARD/Q-TWO/F-PROVISIONAL，详见独立审批账本。W-EQUAL仅选定hash组内每rank本地实例均值等权；W-SCOPE均值/CV/最小rank仅诊断，绝不参与候选合并或投票。每参与实例至少2个去重scope，否则INCOMPLETE；原均值、scope计数和身份留在groups/stage2。最大组并列保留两组轨迹、最小rank并列保留全部；数值或CV分歧返回AMBIGUOUS_SPEC，不按编号挑选或用epsilon。

N-GUARD对已经保存的binary64输入均值用 `Fraction` 计算精确平均、方差及CV²>=1/100、R-GROUP>=1/5门禁；不声称修复原始测量或之前平均误差。rank阈值采用授权的字面 `(mu-a_min)/mu`，不改原 `mean()`。任务06审计辅助表达式采用 `ref/den-x/den`，二者数学等价但浮点边界可能不同；新入口明确实现授权表达式，旧审计文件不改。在全部97个可复用schema1回放上，状态及候选与任务06推荐一致。独立人工边界[8,12]us得到float0.2/exact1/5，两门禁一致，T-GE等号通过；原[80,120]us的mean99.99999999999999保留、float与exact门禁不一致，AMBIGUOUS_SPEC。没有舍入、改数据、加epsilon或暗改阈值。

Profile校验仍由原 `validate_bundle` 执行。缺失/坏数据新入口返回INCOMPLETE，不补零。单rank组不进入Stage2；单组跳过组间sample CV，未定义值为null。正常等时延为NO_CANDIDATE，零均值CV为AMBIGUOUS_SPEC。显式parallel_states只能证明已声明标签，不能证明框架报告全部标签。

Group共享scope标识、去重、communicator hash、本地process/generation与跨comm相关风险全部沿用。Group成员重复记录不会增加实例sample_count，Group总耗时仍为共享观察。sample_count是实例内去重计时scope数，不是独立随机样本；payload count为元素，duration为us；CV/20%无量纲。不同hash即使成员相同仍是不同组。

F-PROVISIONAL：缺数据/支持不足优先INCOMPLETE；规格、并列或不同rank冲突AMBIGUOUS_SPEC；无候选NO_CANDIDATE；唯一候选PROVISIONAL_CANDIDATE。其它标签的已知候选与来源证据在拒判时仍保留。所有路径 `final_fault_ranks=[]`、`final_alert=false`，无生产告警或自动升级。不同标签支持不能证明独立，双标签一致仍可能误报。

EXTENSION：20项确定性CPU单元测试是算法/身份算术证据，不能称GPU实验。批准入口不读取expected/evaluator/注入信息；新测试明确验证附加真值字段不改变输出。历史评估真值仅在两个预测完成后加入报告。

## 实测验收

机器：本地MacBook Air，macOS26.6.2 arm64；已有bundled CPython3.12.14，未安装任何依赖。以下路径均为本次实际argv，完整cwd/主机/时间/stdout/stderr/退出码见 `commands.json` 和私有run回执。

```sh
/Users/henry/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B tests/m6b_ready_approved_localization.py -v
/Users/henry/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B tests/m4_offline.py --output /Users/henry/Desktop/FLASH_Codex/runs/m6b-ready-g3-g04-implementation-20261011/m4-original
/Users/henry/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B docs/m6b-ready/g3-g04-implementation/verify_history.py --output /Users/henry/Desktop/FLASH_Codex/runs/m6b-ready-g3-g04-implementation-20261011/history01
```

- 新20测试最终cpu02 exit0：单组、多组、通过CV的并列最大组、CV=0先跳过、最小rank并列、W-EQUAL/W-SCOPE翻转且Q-TWO完整的新增案例、19/20/21%、数值边界、两种CV、零均值/样本不足、缺数据、Group共享/嵌套/跨hash/成员去重、标签一致/冲突、INCOMPLETE优先保留其它标签证据、无候选/极大/次正规时延。
- 原65fixtures原手写断言及退出码全部保持并通过；24有效exit0、41预期拒绝exit2，父验收exit0。`m4-fixture-manifest.json` 保留每个真实子命令，`m4-fixture-results.json` 保存全部actual/exit/日志及SHA；逐例原始文件仍在私有run。
- 32原M4完整默认预测逐字段相等（30补充+2原正常五组），history01 exit0。新入口97schema1历史回放：32provisional、55INCOMPLETE、5NO_CANDIDATE、5AMBIGUOUS_SPEC；与任务06已有推荐状态/候选全部相等。
- Q-TWO使14原有效单scope合成案例INCOMPLETE；清单、原观察与scope证据在 `history.json`，原fixtures/expected不改。W翻转原案例也保留两个最小rank观察。
- 原正常五组两epoch仍可能双标签一致指向rank3；正常候选、迟到五组标签冲突原样保留。没有为减少误报调标签、改样本、移除冲突、投票或发布final。任务06完整敏感性矩阵原SHA继承，不重新生成或扩增M5矩阵。

`source-ledger.json`、`validation.json`、`history.json`绑定执行源码/输入SHA；`preservation.json`核对基线所有受保护文件字节不变及STATUS/GAPS仅追加。新包hash索引另列，不自引用其自身SHA。

## 失败、未测与停止点

cpu01 exit1：新Group测试在新增第二scope后遗漏声明expected_samples更新，原验证器正确返回INCOMPLETE。只修正新测试声明为2，原断言不变，失败原始日志/当时定位与测试源码快照保留。证据封装prepare-evidence两次exit1（新增Fraction导入使字面前缀假设不成立；随后多加换行），仅修复封装校验，原函数体最终严格字节相等；日志/私有脚本快照保留。根目录Git探测exit128为tool-transcript-only，raw NOT_CAPTURED。见 `failure-index.json`。不删除失败或回填历史缺失。

新GPU/NCCL、native编译/拟合、M5原生矩阵、Redis服务、故障注入、服务器探测、隐私专项、M6-B、任务08、合并均NOT_RUN。历史M5失败、三NOT_CAPTURED、915cache preinstall SHA缺口、权利/隐私DEFERRED/OPEN原样保留。此CPU功能通过不证明真实故障识别、物理持续性、置信度或论文实验结论；G09/G20仍需后续批准。

完成后发布新的独立Draft PR，提供精确HEAD/tree；下一唯一动作是ChatGPT独立审核该精确提交。STOP，不执行任务08或合并任何PR。发布命令/远端回读私有回执保存在上述run，精确最终head/tree在PR描述与发布回执，避免文档自引用commit SHA。
