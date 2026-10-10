# P1 公开仓库隐私审查（2026-10-10）

审查基线：Zwhao0/myflash main `2fcc45724e8bbfde800539beeae45febddd7e572`。当前可见性为 public；未修改可见性、未合并修复、未改写历史。审查设备为本地 macOS / Darwin 25.6.0 arm64，Python 3.9.6、系统 Git；未连接实验服务器、未运行新的 GPU 实验。

## 范围与实际发现

- 四个可见远端分支：main、codex/m2-monitor、codex/m3-profile、security/public-repo-guard；最后一个与 main 同 SHA，没有已有修复。
- 全部 11 个可达不同提交的文件树，122 个不同 blob：121 个 UTF-8 文本 blob 和一个 PDF。没有 tag/release；审查时 Actions run 为 0。
- PR #1/#2 均已合并；PR head 与对应分支相同，正文已检查，评论/评审时间线返回空。PR正文的机器名称也需后续编辑；本轮不替用户发送评论或改写既有 PR 正文。
- 文本中未发现本检查器覆盖的凭证签名或明文凭证赋值；这不是“没有任何秘密”的保证。GPU UUID/MAC 实值未命中。提交作者使用 GitHub noreply 邮箱，作者公开姓名属于身份元数据，未改写。
- 当前文档和 M0 公开日志保留不必要的服务器/本地路径及机器名称；盘点脚本硬编码了私有项目路径。23 个原文件完成身份脱敏/路径修复，详见 redactions.json。
- M0 的 `19ff3e1` 历史版本中 ENVIRONMENT_PLAN.md 和 GAPS.md 保留了真实私网地址。地址不在当前树，但旧版本仍可访问。所有分支祖先仍有这类历史残留。
- requirements.lock 的四段点分数字是固定软件版本，已人工核验；不把它们当 IP 删除或修改。
- references/chapter3.pdf 与 chapter3_extracted.txt 含完整章摘录；仓库没有可核验的公开再分发授权。保留现有参考，授权状态 PENDING，不擅自删掉目标规格或认定获准。
- 仓库根没有项目 LICENSE；公开可见不等于已经选定开源许可证。项目许可由权利人另行选择，本轮不代为赋予许可。

GitHub rulesets 读取结果为空；专用 main 分支保护读取为 403 Resource not accessible by integration，该接口 BLOCKED。随后通用 branches/main API 返回 protected=false / protection.enabled=false / required checks=[]，据此确认当前 main 没有该接口报告的保护或必需检查。仓库元数据返回 public / private=false / forks_count=0；security_and_analysis 未返回，Secret scanning/Push protection 状态 UNKNOWN。没有修改远端设置。未覆盖不可见 refs、他人 clone、缓存、外部附件、PDF 内嵌对象、二进制/编码秘密或未返回的服务端配置。

## 可审核修复与证据解释

ADAPTATION 来源：用户本轮隐私请求、AGENTS.md 的凭证/日志约束。文档使用稳定 node-0/node-1 别名和 <project>/<local-project>/<local-python> 占位符；公开 M0 日志明确为脱敏副本。脚本 scripts/m1_inventory.py 从自身文件位置推导项目根，命令参数和盘点项保持原范围；本轮未执行盘点。原样保留失败、退出码、运行配置、rank/通信组/样本标签和所有性能数值。

原有 transfer/input/source/tree 哈希与 SYNC 回执指向当时的原始快照，作为历史记录保留；新公开副本与旧 tree 不相同。没有用新哈希覆盖历史证据或制造“修复后服务器已经验证”的结论。所有原实验 CSV、原 M1–M3 evidence JSON、核心 native/flash 和除盘点脚本外的既有 scripts/tests 保持逐字不变。详细命令、退出码、日志和哈希检查见 validation.json。

ADAPTATION：scripts/privacy_check.py 只依赖标准库，检查 Git tracked 当前文件并只输出位置/类别，禁止输出匹配值。阻止常见凭证、用户目录、机器 UUID/MAC、真实 IPv4、带凭证 URL 及私有文件路径；精确锁文件版本行例外，回环/未指定/文档示例地址允许。仅允许既有 M0 公开日志和已登记 PDF；PDF 会明确显示 NOT_SCANNED_BINARY。它不能替代完整 secrets/人工材料授权审查。当前树 CI 不能清除历史或在推送前阻止泄露；推送前本地运行命令才会在上传前检查。

UPSTREAM：CI 使用 [actions/checkout](https://github.com/actions/checkout/commit/11bd71901bbe5b1630ceea73d27597364c9af683) v4.2.2、固定 SHA；来源 [MIT LICENSE](https://github.com/actions/checkout/blob/11bd71901bbe5b1630ceea73d27597364c9af683/LICENSE)，无源码复制；调整为 contents:read / persist-credentials:false / 5分钟预算。只运行文本检查和合成测试，不涉及服务器/GPU。Actions 实际执行结果需在 PR 中另查，不能以本地通过代替。

推送前在项目根运行：

```sh
python3 tests/privacy_check_test.py
python3 scripts/privacy_check.py
git diff --check
```

新增文件需先按实际路径 git add，再运行 tracked 检查；ignore 不能保护已经 tracked 的文件，也不能阻止 git add -f。建议后续将 CI 设置为 main 必需检查；当前 main 没有报告保护，本轮未修改远端保护设置。

## 历史清理决定待审核

UPSTREAM 来源：[GitHub 删除敏感数据官方说明](https://docs.github.com/zh/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)。仅合并这份普通修复不能删除旧 blob、旧分支或 PR 引用。历史改写会改变原始提交及其后代 SHA，影响论文实验/source 同步引用、已有 clone、PR diff 与签名；原始 SHA 必须通过私有映射追溯。公开复制品无法保证追回；GitHub 缓存/PR refs 的服务端清理与支持政策需单独评估。

下一唯一任务：审核 P1 diff、确认论文 PDF/全文摘录的公开再分发授权，并决定是否另开一个明确批准的全 refs 历史清理任务。执行前需冻结写入、限定 refs、保留私有备份与旧新 SHA 映射、在独立 clone 演练并验证全部字段及实验数据不变，再审核具体 ref 更新方案。不能删除旧分支后就宣称清除历史；不能仅用新空仓库替换而隐去实验可追溯性。若未来发现真实凭证，先撤销/轮换，再评估历史清理。

P1 的本地检查通过仅证明本次已测隐私规则及数据保留；历史/授权/远端安全设置尚未关闭。M4 及新 GPU 实验均 NOT_RUN。
