# TASK11 — M6B-READY 最终准入审计

授权：2026-10-11 用户明确要求以精确 HEAD
`b517c5a922d52895e274c3758b5b7c2c409d91ca` 为唯一基点，审核现有
Detector、Localization、Reporter/Redis、ABI2 桥接和 G09 协议的端到端缺口。
本地基点干净；独立工作树 `m6b-task11-work`，分支 `codex/task11-m6b-ready-audit`。
指定基点是本轮来源授权，不补写前序独立审核 PASS。

性质：ADAPTATION 审计/准入判断；PAPER 事实沿用 SPEC；UPSTREAM 官方接口核对；
EXTENSION 辅助故障与候选指标沿用 TASK10，均不新增科学算法。

允许修改：本任务、新增 `docs/m6b-ready/task11-final-audit/**`，
`STATUS.md` / `GAPS.md` 仅追加。私有命令/脚本/原始日志只存
`runs/task11-m6b-ready-audit-20261011/`。允许静态审计核验脚本，禁止导入/执行 FLASH。
所有已有 runtime/native/tests/fixtures/原始证据/协议/审批账本字节不变。

接口：文档和不可执行准入清单；没有新 Detector/Profile/Redis/ABI API，
清单的 execution_authorized=false 不能作为未来执行授权开关。

核验：精确 HEAD/tree/父提交；基点全部 tracked 文件保护及两文件追加；
源码声明/调用与文档行号/SHA；既有最终验收源码 SHA 和已保存审阅日志 SHA；
新 JSON/文件引用/清单一致性，`git diff --cached --check`。
不重跑已经完成的 CPU 算法/后验/敏感性矩阵，不读取其它旧失败系统。
不加载 native/Rbeast、不安装/升级、不连接服务器、不启动 Redis/GPU/训练/故障注入。

退出：形成本地可审阅提交、精确 HEAD/tree/diff/原始核验回执；完成即停。
失败保留、另编号复核，不扩大重构或修改原断言/阈值。
下一唯一动作：独立审核 TASK11 精确本地 HEAD；仅审核通过后再明确授权最小接线任务。
本轮不推送、不合并、不执行 TASK12 或 M6-B。
