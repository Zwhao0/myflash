# TASK10 协议交付与本轮检查

唯一基点 `f44e3fb44e48979298a13efbd9dccad5000c3eef`，
tree `1a4f6cec6597f907f9ebe647c62de921fbcb70e4`；干净基点核验后新建
`codex/task10-g09-protocol` / `m6b-task10-work`，原task09分支未修改。
本轮仅文档，协议状态 PROTOCOL_FOR_REVIEW；本地文档/字节保护检查 PASS。
无远端发布授权推断、push/PR/merge、服务器探测或GPU实验。

交付 G09_PROTOCOL.md 的分类/真值/预算/恢复/真实准入阶梯/分层指标与时延，
RUN_MANIFEST_TEMPLATE.json 的非执行空白清单，SOURCE_LEDGER.json 的精确基点
文件SHA及官方文档链接，本任务和STATUS/GAPS追加。接口与原代码全部保持。
不关闭G09，不扩大F-PROVISIONAL；最终diagnosis指标NOT_IMPLEMENTED。

PAPER仅现有SPEC页码事实；ADAPTATION为继承批准契约与本轮协议定义；
EXTENSION为受控辅助模型/候选层评价；UPSTREAM为官方API语义，未复用外部源码。
不重新渲染PDF、不复用GreyHound、不重跑CPU算法/后验矩阵；历史证据只是引用，
没有声称本轮重验其raw日志或补齐FAIL/NOT_CAPTURED/缓存缺口/权利问题。

原始命令/输出/真实退出保存于本项目私有
`runs/task10-g09-protocol-20261011/`，公开validation.json保留命令与SHA关联。
所有检查均在本地macOS，非H800实验；目标机实际版本/环境本轮NOT_PROBED。
准备阶段：用户给定根目录不是Git仓库，首次git探测exit128保留在工具转录，
独立raw文件NOT_CAPTURED；未读任何旧失败系统。桌面create_worktree工具因调用
根目录非Git返回Not a git repository（工具错误，无进程退出码），随后从已验证
task09 checkout用git worktree add成功exit0，stdout/stderr和完整argv留存。
来源ledger准备16个基点文件精确SHA匹配，git status真实exit0。

完整本轮验收命令：

```sh
/usr/bin/python3 <task10-private-run>/verify_protocol.py
git -C <task10-checkout> diff --cached --check
```

命令脚本只做文档/JSON/继承字节及允许路径检查，不import FLASH、不加载native/
Rbeast、不启动Redis/训练、不连接服务器。失败另编号留存，不弱化断言。
本地提交及final-head回执绑定精确HEAD/tree/diff；不在提交内自引用其未来SHA。
下一唯一任务：独立TASK10精确HEAD协议审核；完成即停，不执行M6-B。

## 实际本地核验记录

本机 macOS26.6.2 / arm64，现有系统 Python3.9.6。
`verify01` 实际 exit0、无timeout：2070基点文件中2068个字节完全相同，
STATUS/GAPS仅追加；来源16文件SHA一致；新增JSON/允许路径/准入关键约束通过。
完整argv、stdout/stderr、脚本快照SHA及文件保护索引留私有run；
本轮记录封存和staged检查完成后以validation.json与final-head回执为准。
文档检查不代表科学/资源授权或GPU PASS；GPU/NCCL/Redis/M6-B NOT_RUN。

`verify02` 实际exit0、无timeout：封存JSON及全部8个允许变化路径检查通过，
新增协议/模板/来源/任务的输入SHA再次匹配，2068字节保护及2追加不变。
`staged-check01` 实际exit0；完整命令为上方git diff --cached --check。
本次封存只补检查回执/结果，不改变协议、模板、来源、任务或任何运行字节。
最终Git HEAD/tree、父提交/变化统计/干净状态在私有final-head回执中。

## GitHub 审核发布授权补充 / 2026-10-11

用户明确要求“推送github便于ChatGPT审核”。本轮仅发布，不启动M6-B。
ADAPTATION：保留原本地提交 `f2e435cad268b197019b39d6387e0108b8e1fbb2`
及私有原始日志；新审核分支 `codex/task10-g09-protocol-review` 直接以
精确基点 `f44e3fb44e48979298a13efbd9dccad5000c3eef` 为父提交。
仅脱敏STATUS/RESULT/validation中的本机目录并补发布回执，不改协议、模板、
来源ledger、任务或运行代码。公开argv用占位路径，完整原argv仍在私有原回执；
SHA始终指明关联原始日志，脱敏内容不冒充原始字节。
先前“不发布远端”仅为当时授权范围，现由本次用户授权覆盖。

既有GitHub身份SSH443只读ls-remote实际exit0；远端task09分支HEAD与基点完全一致。
后续只普通push本审核分支，创建独立Draft PR，以task09精确基点分支为base；
不推原始含本地目录的TASK10提交、不改main/前序分支，不force或删除历史。
每个Git命令真实exit/stdout/stderr、远端HEAD/tree回读与PR API结果分别保存到
私有 `runs/task10-g09-protocol-20261011/publication/`；API结果没有进程退出码。
新8文件文本检查只覆盖本次增量，不声称完整历史/二进制权利已审计。
G09 OPEN、GPU注入NOT_RUN、M6-B NOT_STARTED；发布完即停，等待精确HEAD审核。

发布检查check01实际exit0：本地macOS26.6.2 arm64/Python3.9.6；8变化文件文本findings0，2068基点文件字节相同，STATUS/GAPS对基点仅追加，协议/模板/ledger/任务对原TASK10提交字节完全相同。检查stdout/stderr/原脚本SHA公开在validation.json publication.checks；完整原argv/日志留私有。最终封存只补此回执。

首次普通push实际exit0：审核提交 acfb5383f3326954e017b6746732bde72113aaa2 / tree ff52fa3952f2fa9b7639274998a170750c693453；远端HEAD及fetch回读tree与本地完全一致，task09基点仍为精确f44e3fb。check02及staged diff检查实际exit0。最后文档封存仅增加该实测发布回执，不改变协议/模板/来源/任务/运行字节；最终精确HEAD/tree与Draft PR链接绑定在PR正文和私有发布回执。
