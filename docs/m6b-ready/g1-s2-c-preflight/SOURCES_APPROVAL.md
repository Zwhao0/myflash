# 来源和批准账本

- 用户消息：`FLASH_M6B_READY_Codex_Tasks 执行本任务包的任务02`。范围解释：执行任务02所允许的只读预检；专项安装/CPU原生拟合批准未核实。
- 约束原件：`FLASH_M6B_READY_Codex_Tasks/02_G1_S2_C_ISOLATED_ACCEPTANCE.md`首段，以及`00_README_任务索引.md`顺序02。它们明确规定交付任务书不等于安装批准、未批只读后停止。
- 前置审核：G0F PR12 head3ba7dad/treea3bbf9d，当前字节/远端head已核验；独立审核结论 NOT_VERIFIED，不能以隐私CI成功代替。
- UPSTREAM：Rbeast0.1.25 sdist固定SHA、Python3.12.3、NumPy2.2.6固定wheel；原件本次静态SHA核验。来源文件逐项SHA见validation.json。
- ADAPTATION：P1单行increment→increment512候选C身份；本次仅静态读取，未修补/重建/安装；保护1424文件和原.so。
- PAPER：SPEC S3的窗口/阈值仍保留，原论文未规定本工程隔离部署步骤。
- EXTENSION：P1固定CPU合成矩阵只作为后续新部署实例的工程重复性验收，不作GPU或生产等价结论。
- 许可：固定P1 SOURCE_LICENSE_AUDIT.md记录package MIT及native第三方notice待决；不由package classifier推出完整再分发许可。wheel只读留在node-0私有runs，公开分发BLOCKED。
- 正式采纳、科学参数/持续性/分母/权重、Redis、GPU、M6-B：NOT_APPROVED/NOT_RUN，需各自后续任务批准。
