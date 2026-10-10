# M5-P1 结果（2026-10-10）

候选 C 在本轮声明的构建、输入、进程和实际 ISA 范围内工程验证 **PASS**。
仅修改 avx512_pcg_set_seed 的 increment → increment512 一行。正式运行库未替换。

| 判定类别 | 结果 | 证据 |
|---|---|---|
| source/build provenance 与 ABI | PASS | BUILD.md、build-manifest.json、binary-inspection.json |
| RNG 旧内存依赖修复 | PASS | RNG_VALIDATION.md、rng-data.json、独立64个整数输出/复用缓冲区 |
| 原 API / 原 prefix 精确断言 | PASS | STRICT_RESULTS.md、原测试源码未变，C 两断言 exit0 |
| 完整后验严格重复性 | PASS | MATRIX_RESULTS.md、matrix-data.json、完整原数组字节 |
| native 有效性 / 候选及首次 iteration | PASS | DECISION_RESULTS.md；C 两批 native error/crash/timeout/missing raw 均0 |
| Reporter/detection/privacy 与数据完整性 | PASS | validation.json、preservation.json、回归 exit0，当前树隐私 findings0 |
| 科学有效性、正式 runtime 采纳、M6 | NOT_APPROVED/OPEN | G01/G02/G04/G09/G13/G20继续OPEN；final_alert=false |

node-0 Xeon Platinum8463B / Python3.12.3 / GCC13.3 / NumPy2.2.6，项目隔离 CPU
实验。预声明 B1,C1,C2,B2 均只执行一次，各640 reference fits、4900 native decision
fits、6300前缀；合计22160 fits、531840 arrays、25200前缀判断。C 在同模型/实际ISA
下跨同/新进程、affinity/thread控制和两批严格一致；不要求跨ISA后验相等。
B auto/AVX512同模型组有2种完整输出，prefix断言exit1；其API断言exit0和所有
真实成功样本同样保留。A API/prefix均exit1。A/B RNG均仍依赖旧缓冲区。
匹配构建中的B失败/C通过支持此一行修复在本轮范围内的作用，不能外推为所有
生产后验差异的唯一原因，也不能称GPU精确率/召回率或论文延迟复现。

正式环境1424个非pycache文件与基线598个tracked文件实验前后SHA完全一致；
旧严格FAIL、旧三份NOT_CAPTURED与原模型/阈值/fixtures均未改。原命令/stdout/
stderr、wheel和完整第三方源码只在服务器私有runs。许可证/PDF发布问题仍OPEN。
完整公开文件索引与独立本地字节回读见data-index.json和transport-readback.json；
首次导出路径错误、格式检查失败及修正见AUDIT.md、postprocessing.json、local-checks.json。
最终head/tree及该head真实CI回执见独立Draft PR描述和私有publication-receipt.json。

来源：PAPER 为现有SPEC S3窗口/规则；UPSTREAM 为固定0.1.25 release
ext_src/abc_rand_pcg_local_avx512.c:avx512_pcg_set_seed及实际工具链；ADAPTATION
为一行字段修复、隔离构建与完整证据核验；EXTENSION 为固定人工fixture矩阵。
没有GreyHound代码或此前失败FLASH实现。完成本任务后停止，唯一下一步是独立审核
新Draft PR；本轮不合并PR7/新PR，不部署正式wheel，不进入M6。
