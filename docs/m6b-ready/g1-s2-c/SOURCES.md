# 来源与范围

- **PAPER**：现有 `SPEC.md` S3 / 论文第三章；本轮不修改窗口、过滤规则、阈值或科学结论。G01/G02/G04/G09/G13/G20 继续 OPEN。
- **UPSTREAM**：固定 Rbeast 0.1.25 sdist，SHA `8265bd53f9c16bdb1ab103de047288ea1af6875415394abf3ac0104cfb2917ec`；`ext_src/abc_rand_pcg_local_avx512.c:avx512_pcg_set_seed`。候选 C 是先前 P1 仅将 `increment` 改为 `increment512` 的产物，本轮只安装既有 wheel，不修补或编译。原固定 P1 提交 `d2973f5fa66ae99ec7ea09ea7040a11d1b95b845`；版本、来源与许可细节见既有 `docs/m5/patch-p1/{BUILD.md,build-manifest.json,SOURCE_LICENSE_AUDIT.md,minimal.patch}`。MIT 包级声明不能关闭第三方 NOTICE 的既有缺口；wheel 与完整第三方源码不公开。
- **UPSTREAM / ADAPTATION**：现有 Python 3.12.3、固定 NumPy 2.2.6 wheel、已有 C ABI helper。实际解释器、模块、映射原生库、RECORD、ELF、符号、依赖和工具版本以本轮命令输出为准。包版本号不作为 C 身份证明。
- **ADAPTATION**：本轮新增 `scripts/m6b_ready_s2_execute.py`、`scripts/m6b_ready_s2_identity.py`；隔离环境、离线带 hash 安装、进程超时保护、保全与导出。新增 runner 的 CLI 参数错误及完整正式环境前测清单遗漏单列留证，不作为获准豁免。
- **ADAPTATION**：原 `scripts/m5_p1_diagnostic.py:{rng,suite,native_fit}`、`scripts/m5_p1_compare.py:{validate_fit,validate_batch,main}`、`scripts/m5_p1_strict.py`、原 API/prefix 及 CPU 测试；均从已审核基线 `3ba7dad2070ad13466b4f14562ee54fa4a3e818b` 原字节复用。`source-files.json` 记录原 1,517 文件指纹，`model-identity.json` 列出原 24 参数。
- **EXTENSION**：原 P1 固定人工 CPU 矩阵的两批 C 部署验证；32 cells × 20 reference fits、7 fixtures × 20 replays × 45 prefixes 每批。全部参考模型/affinity/thread/请求 ISA 控制保留；按同模型和**实际** ISA 分组要求严格重复，不要求不同 ISA 后验相等，不挑选 ISA 或样本。旧 B/A 与 M5-R 是保全的历史失败，未在正式环境重跑。

`EXPORTER.py` 只导出和脱敏；原比较器输出完整字节保留在 `data/`。标准库另校验每个数组的 dtype/shape/字节数/base64/SHA。进程和路径标识使用稳定别名，浮点数、标签、阈值、后验和断言不脱敏。第三方长 metadata 描述保留私有，公开其 SHA 与安装相关 header。

`FINISHER.py` 只补跑首轮参数错误导致未执行的回归与原比较器，不新增拟合；`NATIVE_GATE_AUDIT.py` 只读检查已有 prerequisite 输出，沿用原 parser 和合法概率范围。两个 helper 的实际源指纹、命令退出和原始文件保护证明与记录一起提供。

`tests/m5_api_fields.py` 的固定输出仍提到旧的 “repeatability FAIL”；本轮没有修改这条历史描述。当前 API/prefix 严格断言和完整两批后验的结果分别报告，不能从这条静态文本推断本轮比较器结果。

正式环境完整安装前清单缺失，整体验收 BLOCKED。CPU 工程结果不等于科学、GPU/NCCL、生产多线程/多机有效性；`final_alert=false`，正式采纳 NOT_APPROVED，M6-B NOT_RUN。历史隐私/再分发事项 DEFERRED/OPEN；不重写历史。
