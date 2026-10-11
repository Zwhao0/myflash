# Task02 / M6B-READY-G1-S2-C-EXECUTE

**整体隔离验收 BLOCKED**：正式环境完整安装前清单没有采集，915 个缓存文件缺少前测 SHA。CPU 门禁通过不能替代这项硬条件；候选 C 未采纳，正式调用路径未切换。见 FULL_MANIFEST_GAP.md。

| 实际检查 | 结果 |
|---|---|
| 固定 wheel / NumPy / sdist / lock / RECORD 与运行时解释器、模块、映射 .so 身份 | PASS |
| ABI / RNG reference、旧缓冲区独立性、复用 / 实际 normal auto AVX512 | PASS |
| 原 API 与 full/short prefix 严格断言；原 77 CPU tests、6 privacy tests及相关原断言 | PASS，各实际 exit0 |
| 两批完整后验/决策原比较器四项 | PASS；每批 5540 fits / 132960 arrays / 6300 prefixes |
| 55 份已保存前置 native 输出的原 parser/合法 cpOccPr 检查 | PASS；该审计新增 fits 0 |
| 原 1424 非缓存正式文件与原 .so、原 1517 来源文件 | 前后字节相等 |
| 安装后正式完整 2339 文件再核对 | 相等；不是安装前证明 |
| 历史 131811 个证据文件 | 两次 SHA 清单相同；首次快照在 C 第一批运行期间、安装后 |
| 完整正式环境安装前清单 | NOT_CAPTURED，整体验收 BLOCKED |
| 正式检测采纳、科学/GPU/NCCL/node-1/M6-B | NOT_APPROVED / OPEN / NOT_RUN |

实测 node-0 Intel Xeon Platinum8463B，Python3.12.3、NumPy2.2.6、glibc2.39。C wheel SHA a4925769e85d015682712fd18f924d3ad02e4a02e4f8bca9e4280028353c29ce，实际加载 .so SHA 1f08fbc9f24d0c00eb21f91f357519f15289ffd1ef18b9e7e0aca47c2596faeb；正式原 .so 仍 a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157。版本字符串相同不是身份依据；实际 module/native maps/RECORD 另有证据。

首轮执行代码 684d5c7a435fc36877b38e5397e2a1960eb4a354，固定基线 3ba7dad2070ad13466b4f14562ee54fa4a3e818b / tree a3bbf9d885e0f2f563f54086fb007f646c826f8d。两批 worker 各 476 个全部 exit0。新增 runner 漏传 cursor 测试 --output：原 argparse exit2/parent exit1 保留。4a4721c1426ba19f66b837220db82990987f6750 仅修新增调用参数；补跑9 cursor/8 extra/6 privacy和原比较器，finisher实际exit0，无新增拟合。原始采样目录在补测前后逐文件SHA完全相同。见 INVOCATION_REPAIR.md。

完整命令、环境、deadline、真实 exit、stdout/stderr SHA 在 commands/、validation.json及批次 native-command-index.json。私有原件在当前项目 runs/m6b-ready-g1-s2-c-20261011/{execution01,finish02}（node-0）以及本地同 run 的 remote-evidence/。原始 stdout/stderr、PID/路径、原生库和 wheel 留私有；公开命令用路径/进程别名，raw-public-correspondence.json 绑定原件 SHA。data/ 是原比较器完整 JSON 的原字节副本；包含两个完整矩阵，原数组 dtype/shape/base64/字节 SHA，并非摘要、首次样本或挑选样本。

标准库回读验证 265920 个数组，共 12948480 字节；transport-array-audit.json 留证。数值、标签、输入、模型、比较器、全部断言不改。P1正常场景的实际候选也全部保留，严格重复不等于科学规则获批或没有假候选。原 M5-R/A/B FAIL、三份 NOT_CAPTURED 与原 red9 全部保留。所有本轮失败/工具缺口见 failure-index.json；整体 BLOCKED 没有改写为 PASS。

先前未上传的七个只读预检报告完整收录于相邻 g1-s2-c-preflight/，历史 NOT_RUN/待授权原文不改；本轮专项授权单列 APPROVAL.md。来源和许可边界见 SOURCES.md，24参数在 model-identity.json。原 科学 G01/G02/G04/G09/G13/G20 继续 OPEN，final_alert=false，无正式路径切换/系统服务修改/编译/依赖下载/GPU/NCCL/故障注入或 node-1 部署。

退出：独立 Draft PR 精确提交审核，含完整清单缺口处理；本轮停止，不执行任务03。发布最终 head/tree 与真实 CI checkout 见 PR 描述/私有 publication-receipt.json；隐私 CI 不能证明 native、科学或 GPU 验收。
