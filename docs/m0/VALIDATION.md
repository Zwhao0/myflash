# M0 验证记录与执行口径

任务：`tasks/00_bootstrap.md`；用户追加要求服务器开发。权威工作目录为 `gpu-01:/home/campus/zhangweihao/myflash`。

本地仅阅读工作包、PDF 文本/完整页面及准备传输。会话最初按客户端不存在的 myFLASH 路径调用 shell 失败；发现本地工作包 FLASH_Codex 后曾初始化 Git 和占位，用户明确服务器开发后此本地尝试作废并移除本轮创建的初始化/占位。原始工作包文件保持原样。服务器 SSH 密钥模式失败（255）；通过私有说明中密码认证成功（0），凭证无输出、无传输入项目。

## 实际核验

- 本地参考文件核验完整命令、stdout/stderr 与退出码：`00_local_reference.log`。读取全部 30 页文本；关键示意图与公式完整页面视觉核验：摘录6/7/9/10/12/23/24＝印刷24/25/27/28/30/41/42。原完整 PDF 未提供，只验证摘录 SHA/页数，未重新证明 manifest 中此前做过的原 PDF 像素相等。
- 实际渲染命令（本地、每次退出码0）：`pdftoppm -f P -l P -r 95 -singlefile -png references/chapter3.pdf /tmp/flash-m0-pdf-review/page-P`，P 分别为上述七页；工具 view_image 逐页检查成功。
- 服务器目录创建、逐文件传输哈希与 Git 初始化实际记录：`01_bootstrap.log` / `transfer_manifest.json` / `commands.json`。
- 服务器内容/目录/来源/ignore 边界核验及 Git 快照：`02_verify.log` / 后续 Git 日志。命令详见 `commands.json`，每条含 cwd、stdout/stderr 日志和退出码。

## 验收断言

服务器目录原不存在，创建时再次拒绝复用既有目录；独立 Git 根目录等于目标路径。只传入允许的任务工作包文件和本轮文档，未传入服务器私有说明、DS_Store 或实现。

验证源 PDF SHA 和全部传输文件哈希；未修改的原工作包文档与输入哈希一致；GAPS 仅追加 OPEN 条目；native/flash/scripts/tests 各只有 .gitkeep，无构建、训练、FLASH 实现或实验包。检测所需 ignore 有效，源码/规格不被忽略。

上述验收仅证明 M0 文档与仓库边界，不能称 NCCL/CUDA、Rbeast、共享内存、GPU 实验 PASS。M1–M8/GPU/故障注入均 NOT_RUN。下轮唯一 M1a 只读盘点，尚待审核。
