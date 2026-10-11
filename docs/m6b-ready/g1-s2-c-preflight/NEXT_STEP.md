# 待专项批准的任务02执行清单

请确认上一关PR12精确head `3ba7dad2070ad13466b4f14562ee54fa4a3e818b` 已独立审核通过，并明确批准以下范围。批准后在该固定head创建独立 `codex/m6b-ready-g1-s2-c` Draft分支；先核验远端head/tree，再实施。

1. node-0、当前项目、唯一新run_id，创建 `runs/<run_id>/.venv-m5-s2-c`；已有路径则停。使用现有Python3.12.3，在新环境离线 `pip install --no-index --no-deps --require-hashes -r <locked-file>`，仅装本次已核验C wheel及NumPy2.2.6，不联网下载、重编译或安装系统组件。hash文件引用既有本机wheel，原 `.venv-m5` 不覆盖。
2. 装前/装后记录Python/包metadata/RECORD、实际sys.executable和Rbeast.__file__、真实动态库路径与SHA、ELF/symbol与有效auto ISA。所有原生加载仅在新环境。任何身份/ABI/原.so保护失配立即停，保留完整错误。
3. 在新checkout、仅新解释器按原P1完整argv运行：`tests/m5_real_api.py <new-run>/api`；`scripts/m5_replay.py --input tests/m5_fixtures/records/sustained.json --output <new-run>/replay`；`scripts/m5_p1_strict.py <new-run>/prefix-capture.json <new-run>/replay`。原测试、输入、24参数、seed、断言不变。
4. 按P1 protocol.json的32上下文×20完整reference fits及7 fixtures×20×45前缀，C1/C2两完整批；预计合计11080 native fits、12600前缀、完整24数组/fit，跨同模型/实际ISA/上下文/两批逐字节核验。沿用P1细胞布局及真实ISA观测，不把requested ISA当actual；不要求跨ISA输出相等。原A/B FAIL与3份NOT_CAPTURED保留，不用新C覆盖。
5. 运行已有Reporter/detection/相关CPU回归，原始stdout/stderr/真实child exit/timeout/PID及完整字节证据仅存本run；native错误、非法cpOccPr、缺数据、timeout、原断言不通过均阻塞验收。不重复选择更好看的样本。
6. CPU-only、低优先级；在启动前固化每child deadline与整轮预算，沿用P1已声明的既有上限，不放宽到无限等待。所有本run child wait；超时只结束明确归属本run的PID/PGID，保留partial证据。装后失败回滚方式为不启用新环境；正式调用方不改。
7. 完成后正式环境1424文件/原.so前后核验，STATUS/GAPS只追加，可信脱敏报告、独立Draft PR、普通push、最终head/tree/CI真实checkout回读。wheel不公开，禁止merge/force/history改写，完成即停等审核；不进入任务03。

上述是具体待批准范围，当前安装/原生加载/拟合/严格矩阵/新PR均NOT_RUN。执行期限与原P1脚本一致的确切argv及预算会在原生执行前预声明，必要依赖/原件缺失则BLOCKED，不擅自扩展。
