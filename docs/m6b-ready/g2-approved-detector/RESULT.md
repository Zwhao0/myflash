# 任务05：已批准检测规则 CPU 验收

G01-a、G02-inclusive_span、G13-A 已由本聊天负责人在 2026-10-11 的“FLASH M6B-READY｜任务 04 科学规则批准与任务 05 执行授权”明确批准，前置独立审核精确 PR15 head `5f9cccf2c8582837ba1050fafdf7f56106964465` / tree `017b7f2eb65328c5b52788957ea0bd2e96e99f8c`。本轮从该 head 新建 `codex/m6b-ready-g2-approved-detector`；工程确定性验收 PASS，真实故障识别率/概率校准/GPU效能/端到端生产告警没有据此取得验证。G20 仍 OPEN。

`flash/change_detection.py` 增加显式 `approved_rules=True` 路径。合法的当前模型候选在满足 cpPr>=0.8、原迭代间距>=2、完整左右/recent均值、恢复<0.75、正向时长增长以及严格 A=(d-b)/b>0.2 后成为 `qualified_candidate`；再满足当前原迭代 `t-j+1>20` 成为 `detection_trigger`。模型、资格、检测触发逐层输出；`final_alert` 始终 false，没有接入控制器或发起 Profile。

原 `preprocess` 和旧候选算术保持：原30条窗口再全程warmup<=3过滤、population abs-z>3、压缩轴/双向原迭代映射，chronological cpPr>=0.8，spacing先更新previous再恢复/强度。新路径复用旧均值和次序，拒绝非法 raw/参数身份不符/非正或非有限值/零分母/缺少左右样本；均值溢出返回 insufficient，非有限派生比例为 null。B=(d-b)/d仅诊断；实测吞吐为 null/NOT_MEASURED_WORK_AND_WALLTIME，无工作量或墙钟时不制造实测值。其余五计数口径只保存在历史敏感性输出，不参与主判定。

默认 `approved_rules=False` 保留原 schema 和全部原输出；Rbeast adapter/worker/全部24 PARAMETERS/固定隐式wrapper/native行为/旧fixtures/所有旧断言/M4/Redis/control原字节不变。既有 C 仍必须通过 `RbeastAdapter(candidate_c_python=...)` 独立显式选择，版本/固定.so SHA/映射身份拒绝逻辑未改。省略新参数与C adapter即恢复原调用方式。新接口细节见 INTERFACE.md，批准和来源见 APPROVAL.json / SOURCES.md。

实际设备为本地 MacBook Air / macOS26.6.2 arm64。新13项CPU测试最终使用既有 bundled Python3.12.14，exit0/无timeout；原检测8、Reporter4、C opt-in7、cursor额外8与cursor合同9共36项，系统Python3.9.6实际exit0。原cursor入口首次误漏 `--output` 的 argparse exit2保留，补齐调用参数后9项exit0；没有修改原测试。机器名、精确解释器、完整argv/cwd、时间、真实退出码和stdio/SHA在 commands/ 与私有原件关联中。

严格历史 verifier 使用现有 bundled Python3.12.14，最终 actual exit0 / 约16秒 / 无timeout / 新native fits0：读取P1两批及S2两批各七场景、20重放、45前缀，共560重放/25,200前缀。默认 detect 与保存输出逐字段严格相等，原 full[:24]==short（两个45/24 capture）完整保留，额外138 strict前缀也由新旧路径核验。1260代表前缀/7432候选槽完整保留模型cp、概率、均值、恢复、A/B、六口径和被拒原因。每次重放都用原fixture[:t]，raw与preprocessing不改；检测器不读取独立evaluator真值。输入文件SHA、派生source SHA和完整结果在 history.json。

另仅重新读取S2两批固定 `pinned-c3-auto-fresh` reference cell共40已存fit的960数组：dtype/shape/size/base64/SHA、raw对应浮点值和原全posterior字节哈希逐项验证；没有执行矩阵或加载.so。task03已有真实C加载/错二进制exit78证据被只读校验，历史 C binary SHA固定 `1f08fbc9f24d0c00eb21f91f357519f15289ffd1ef18b9e7e0aca47c2596faeb`。本轮远端环境/二进制 NOT_PROBED，不主张新native或完整环境保全。

| 固定场景 | 四批相同的首次 A+inclusive 检测触发 | B+inclusive 诊断首次 |
|---|---:|---:|
| stable | null | null |
| sustained | 41 | 41 |
| growth_19 | null | null |
| growth_20 | 43 | null |
| growth_21 | 41 | null |
| spike | null | null |
| recovery | null | null |

growth_20 的43/45前缀A通过源于实际binary64均值，不按场景标签舍入回20%；growth_21的41–45也是A/B分歧。所有未触发、早期候选、漂移/恢复/不足/被拒槽均保留；这些是历史合成CPU数据，没有用于宣称误报率/召回率、连续21次真实退化或1–2迭代最终检测延迟。

本轮失败见 failure-index.json。首轮新测试exit1保留：测试恢复比手算错、构造的少数baseline被旧z过滤移成常量、nextafter样本均值假定错，以及新路径未捕获fmean溢出。修正新测试构造而保持原断言目标/阈值/旧fixtures，并补充溢出拒判。历史verifier首次fixture包装结构处理错误exit1保留，使用原`records`字段修正；其次Python3.9.6严格输出比较在sample std/z-score末位与历史3.12不同exit1保留。同一逐字段严格断言在现有3.12.14通过，未加容差或删字段，也未用3.9失败声称跨版本全输出相等。无安装/升级/重拟合。初始非Git目录exit128与任务包路径错误只有tool transcript，raw文件NOT_CAPTURED；不补造原始回执。

所有1882基线tracked文件中，仅检测器修改，STATUS/GAPS追加且原字节前缀不变；其他1879文件及前置PR15 checkout完整保全。历史M5-R/P1 A/B失败、三个NOT_CAPTURED、915-cache preinstall SHA缺口均保留。原科学申请 `approved=null` 文件是历史记录，新批准另存APPROVAL.json。历史隐私/许可DEFERRED/OPEN；本轮无隐私专项、历史补采、依赖安装、native编译、GPU/NCCL、Redis服务、故障注入或M6-B。CI沿用原自动流程，不能代替CPU/科学验收。

唯一下一动作：对新独立 Draft PR 的精确head做独立审核。交付后停止；不执行任务06/G04或G20、M6-B。

发布前完整staged diff --check实际exit2：首轮新CPU失败stderr中的unittest子测试行尾空白原样保留，未裁剪raw。先前只含tracked源码的检查exit0没有覆盖新增日志，不能当作完整diff PASS。源码/任务/说明的独立检查另记，最终完整diff exit2保留。
