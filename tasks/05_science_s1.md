# M5-S1 科学语义审计（2026-10-10）

授权：用户完整 M5-S1 任务书，连续完成 A–D 与离线验收后独立 Draft PR 并停止。
精确基线：PR8 d2973f5fa66ae99ec7ea09ea7040a11d1b95b845，
tree c81e05380685e86acccde6ff97638d49d02457c8。
新分支 codex/m5-s1-science-audit；base codex/m5-p1-avx512-seed。

允许修改：本文件、scripts/m5_s1_*.py、tests/m5_s1_*.py、
docs/m5/science-s1/**；STATUS.md/GAPS.md 只追加。
接口：纯标准库离线 CLI，读取固定候选 C 两批原记录；不调用 native。
PAPER：第三章原文和完整页；UPSTREAM：固定 0.1.25 sdist/wrapper/native；
ADAPTATION：独立重算、哈希/映射核验；EXTENSION：分母/持续性敏感性候选。

实施顺序：A 源码/论文引用与参数账本；B 逐前缀时间线及独立持续性规则；
C 两分母的严格 >0.2 边界与全部前缀分析；D 待批准决定和 S2 部署方案。
测试：新增确定性测试、全部12600前缀完整性/重复一致性/无未来数据、原算术
结果精确对照、既有 Reporter/detection/API字段/contract/隐私与 P1 数据回读。
真实命令、环境、exit、输入输出 SHA 与日志保存在本 run 的私有记录及脱敏
validation.json。CPU 超时每检查600s，仅终止本次子进程，不占用 GPU。
退出：原数据/算术不一致记 FAIL 保留证据；来源/运行环境不足记 BLOCKED 或
NOT_RUN。不得放宽断言或重跑 native 填补缺口。

禁止：修改 flash/、原测试/fixture/参数/seed/阈值、原 M5-R/P1 证据；
安装、编译、runtime 替换、GPU/NCCL/Redis/M6、最终告警、合并/force push。
G01/G02/G13 均 OPEN / REQUIRES_OWNER_DECISION；final_alert=false。
