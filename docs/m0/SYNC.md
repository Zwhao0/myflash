# 服务器为开发源、本地中转 GitHub 的同步边界

ADAPTATION；用户本轮明确授权 GitHub 存放服务器 `myflash` 内容。当前 GitHub 账号 Zwhao0，用户已创建并指定 https://github.com/Zwhao0/myflash；首份 M0 快照已同步并逐文件/tree 核验。不得使用旧失败项目的仓库或历史充当起点。

服务器无法联网，开发在 `gpu-01:/home/campus/zhangweihao/myflash`。仅从该新项目 Git 快照导出，经本地临时中转上传；本地不实现 FLASH。私有 `服务器.md` 保留在用户本机，仓库创建成功后将真实 URL 写入该文件；不会把密码上传 GitHub。

建议目标为私有空仓库 `myflash`，由连接账号授权 ChatGPT GitHub app 访问；若需要公开展示，必须先由用户明确选择公开，不自动公开论文/地址/拓扑日志。

1. 服务器：核验 `git status --porcelain` 与 HEAD；M0 快照无秘密/实现/运行产物。
2. 服务器：在本项目 Git 管理目录导出 `git bundle create .git/m0.bundle --all`，再 `git bundle verify .git/m0.bundle`。bundle 只含该全新仓库 Git 对象，不含连接凭证、ignored 文件或其他项目。
3. 本地：通过已有 SSH 认证中转该 bundle 到本次临时目录；验证 bundle 与 commit/tree/file hash。只读镜像用于传输，不作开发源。
4. GitHub：对用户提供的新目标检查实际存在/权限/当前头，不覆盖不明历史；用本地现有获准 Git 身份或 GitHub connector 上传。若连接没有创建仓库/写权限，需要用户先创建/授权，不能声称上传成功。
5. 完成后核对 GitHub 分支的内容与服务器快照一致，记录双方 commit（若 connector 生成不同提交，按 tree/逐文件 SHA256 校验而不声称 commit相同）。写回真实仓库 URL 到本地 `服务器.md`；更新服务器 STATUS 与同步原始日志，再经中转同步更新，停止 M0。

M0 授权的同步不会启动 GPU、训练、故障注入或 M1。后续阶段每轮若获准同步，仍以服务器提交为源，避免本地与服务器双重修改。

## 本轮实际结果

首份源提交 1296efbd4feca26cb40157e8fd392ee2d9f0cec5，GitHub 提交 19ff3e183ee4cf21b7cb2d001c2b2dcfa6709ff8；31文件 blob 与 tree 957c46dff4979591eafe09f3e35fbf7116f77ec0 完全一致。GitHub main 回读成功；URL 已写本地服务器.md，私有说明/凭证未上传。服务器离线、本地中转，connector 创建提交时作者/时间不同，因此两边 commit/history 不同，但文件树逐轮核验相同。后续不得直接合并不明历史；同步仍以服务器指定提交为内容源。操作证据见04_github_sync.json；本段与STATUS更新从服务器提交后也同步，最终核验见.git/m0-sync-final.log。
