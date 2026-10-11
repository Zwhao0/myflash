# Task02：候选 C 只读预检（2026-10-11）

当前状态 **REQUIRES_OWNER_DECISION**。只读静态预检 PASS；新隔离部署、CPU 原生拟合与严格重复性验收均 NOT_RUN。

node-0 的候选 wheel SHA `a4925769e85d015682712fd18f924d3ad02e4a02e4f8bca9e4280028353c29ce`、内含 `.so` SHA `1f08fbc9f24d0c00eb21f91f357519f15289ffd1ef18b9e7e0aca47c2596faeb`、NumPy wheel SHA `fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249` 及原始 sdist SHA 均匹配任务书/P1 固定清单。Rbeast/NumPy ZIP 完整，RECORD 分别核验22/875个含hash成员、错误0。候选为 cp312 Linux x86_64、ELF64 little-endian machine62；静态元数据不证明新实例已加载，也不证明实际 AVX512 分派。

本地、node-0 原 G0F checkout、远端 G0F head 均为 `3ba7dad2070ad13466b4f14562ee54fa4a3e818b`，本地/node-0 tree `a3bbf9d885e0f2f563f54086fb007f646c826f8d`，checkout均clean。main仍为任务包 `ce984ea…`。另观察到G0-E分支移动到 `3ca5260754b09a5a6b6898c2edcacdc22bb42b72`；仅记录，不自动处理，不用其移动head替换固定G0F源。PR12独立审核通过的原始记录在本聊天尚未核实。

正式 `.venv-m5` 1424个非缓存文件两次SHA清单完全相同，原 `.so` 保持 `a7432000e18465d8e4d2ba895a8618b388007528757718d286fcb82440bbb157`。原仓库1517个tracked文件全部字节保留；本轮报告写于非Git工作包docs目录，未污染PR12分支。首次错用checkout路径的嵌套git exit128保留；修正后的两个git命令exit0。两次SSH完整执行exit0、无timeout，Git远端只读查询exit0。

任务02原文要求“必须有负责人明确授权『固定候选 C wheel 在全新隔离环境的安装、CPU 原生拟合/严格重复性回归』”，并规定未满足时只做只读核验后停止。当前用户明确选择执行任务02；这一选择记录为预检授权，尚未将其写成专项安装/原生拟合批准。见 SOURCES_APPROVAL.md 与 NEXT_STEP.md 的具体执行范围。

未新建分支、提交、推送或Draft PR；这些步骤待前置审核/授权后进行。未安装、下载、重编译、加载原生库、运行拟合或修改正式调用方。历史许可/隐私继续 DEFERRED/OPEN；wheel未复制或公开。G01/G02/G04/G09/G13/G20保持OPEN，final_alert=false，M6-B NOT_RUN。

来源：PAPER为SPEC S3；UPSTREAM为固定Rbeast0.1.25 sdist/P1 manifest及原有Python；ADAPTATION为只读校验/原环境保护及批准门禁；EXTENSION严格人工矩阵仅计划、尚未执行。完整argv、真实退出码、原始日志与stdin源码SHA在私有 `runs/m6b-ready-g1-s2-preflight-20261011/`；公开可审核摘要在validation.json，失败单列failure-index.json。静态预检不能替代runtime/科学验收。

下一唯一动作：负责人确认PR12精确head已独立审核，并明确批准NEXT_STEP.md列出的新隔离离线安装与CPU原生回归；本轮停止。
