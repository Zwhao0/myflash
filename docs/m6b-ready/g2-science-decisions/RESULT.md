# TASK04 科学规则决策包

状态 REQUIRES_OWNER_DECISION。推荐待批组合：G01-a（有界BEAST窗口候选功能复现，完整24参数+隐式默认+压缩轴+过滤次序）；G02-inclusive_span（含cp原iteration跨度t-j+1>20为主要p40字面对照，其他为敏感性）；G13-A（迭代时长增长严格>0.2，B和实测吞吐单列）。这不是批准或正式默认，SCIENTIFIC_DECISIONS.json中所有approved=null，final_alert=false。

基线PR14 head 7c898ecbf8636eed6d07ec0070d2c3c0c99688e0 / tree 10533c34d6b3aab4f50e61f898be78249580afba，人类确认已独立审核通过；新分支codex/m6b-ready-g2-science-decisions。论文完整印刷p26/27/40/43/44本轮视觉核对；固定sdist/wrapper与既有S1引文SHA本轮核验。仅当前clean-room项目S1/P1指定历史。

## 七场景全部口径（首次iteration，A/B）

| 场景 | 首次概率 | 无新门槛 | 含首>20 | 排首>20 | retained>20 | 连续>20 | k1 | k2 |
|---|---|---|---|---|---|---|---|---|
| stable | — | —/— | —/— | —/— | —/— | —/— | —/— | —/— |
| sustained | 22 | 22/22 | 41/41 | 42/42 | 41/41 | 42/42 | 22/22 | 23/23 |
| growth_19 | 22 | —/— | —/— | —/— | —/— | —/— | —/— | —/— |
| growth_20 | 22 | 23/— | 43/— | 43/— | 43/— | —/— | 23/— | 23/— |
| growth_21 | 22 | 22/— | 41/— | 42/— | 41/— | 42/— | 22/— | 23/— |
| spike | — | —/— | —/— | —/— | —/— | —/— | —/— | —/— |
| recovery | 22 | 22/22 | —/— | —/— | —/— | —/— | 22/22 | 23/23 |

两批完全相同；—表示45步观察范围内未出现，非永远不会出现。所有最终告警均null/false。全概率/cp/均值/前缀证据沿固定S1/P1路径及SHA读取，不用本轮新拟合覆盖旧失败。

## 本轮验证与退出

本机macOS/System Python3.9.6标准库静态AST、JSON、精确边界算术与历史前缀独立核验，命令/退出/原日志SHA见validation.json和私有runs/m6b-ready-g2-science-20261011。不把历史node0/native工程PASS说成本轮native/GPU实验。允许变更仅new docs/task、STATUS/GAPS追加；已有1858文件（后二者仅追加）保留。没有安装/重编译/native拟合/Redis/GPU/故障注入/正式默认切换/M6-B。

M5-R、P1 A/B失败、三个NOT_CAPTURED、task02丢失915-cache预安装hash及task03差异全部保持；历史权利/隐私DEFERRED/OPEN。候选C工程证据不证明概率校准或论文算法等价。仅文档/算术校验可PASS，科学有效性NOT_APPROVED。

下一唯一动作：独立审核本Draft精确head与完整决策包，由负责人逐项明确批准（可用NEXT_STEP.md表单）；本轮停止，不执行task05或产生最终报警。
