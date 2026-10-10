# M5-S1 审计交付

范围：PAPER第三章科学语义、UPSTREAM固定Rbeast0.1.25、ADAPTATION当前代码与
EXTENSION既有候选C离线敏感性。精确基线PR8 d2973f5 / tree c81e053。
执行中的最终状态与实际命令/退出/哈希以 validation.json 为准；发布后精确
head/tree及该head真实隐私CI以Draft PR和私有publication回执为准。

结论入口：
- [G01语义与全部参数](G01_SEMANTICS.md)：BEAST窗口重拟合不等同已证明在线run-length递推。
- [G02全部时刻和持续性规则](G02_TIMELINE.md)：20次与1–2次冲突保留。
- [G13两分母](G13_THRESHOLD.md)：A/B严格>0.2，真实吞吐/代理区别明确。
- [待批准决定与S2方案](DECISION_PROPOSAL.md)：不安装、不采纳、不启用告警。
- [完整数值](data/sensitivity.json)、[逐步时间线](data/timeline.json)、
  [首次摘要](data/timeline-summary.json)、[280重放覆盖](data/repeat-coverage.json)、
  [原832文件SHA](data/input-hashes.json)、[引用凭据](data/source-receipts.json)、
  [输出哈希](data/hash-index.json)。

两批×7×20×45=12600前缀严格检查；630个唯一前缀保留所有cp槽与各独立阶段。
没有新增native fits。七固定场景均为合成CPU证据，不是GPU故障实验。
无候选、无效输出、样本不足和padding分别处理；无非法值补零或裁剪。
当前争议 G01/G02/G13 OPEN / REQUIRES_OWNER_DECISION；G04/G09/G20仍OPEN。
final_alert=false，科学有效性/正式runtime采纳/M6 NOT_APPROVED。

复现（使用原证据机器现有Python3.12.3与私有固定sdist，不安装任何包）：
```sh
python3 scripts/m5_s1_sources.py --sdist <fixed-sdist> --output docs/m5/science-s1/data/source-receipts.json
python3 scripts/m5_s1_analysis.py --output docs/m5/science-s1/data
python3 tests/m5_s1_offline.py
python3 scripts/m5_s1_validate.py --run-id m5-s1-validation-01 --sdist <fixed-sdist> --formal-root <formal-original-venv>
```
真实完整argv/私有路径、退出码、原始stdout/stderr留node-0 runs/<run_id>/；公开
命令用占位符和相对日志入口。source SHA和working code hashes记录执行内容，
不能把提交后的文档改动说成已测新算法。validation是CPU检查，不是科学PASS。

开发过程失败保留：本地fixture外层误读（TypeError）；Python3.9标准差与原
Python3.12末位不一致（严格对照拒绝）；固定原生文件非UTF-8解码错误；论文
文本短锚点不唯一；初次私有传输目标目录缺失与早期服务器路径探测失败。
修正仅离线脚本解析/引用和传输路径，不改原数据、过滤断言或加容差。
这些失败/命令回执另存私有runs/m5-s1-access/development-failures，先前M5-R/P1
全部失败与缺失未删除。正式严算在原Python3.12机器验证，本地3.9不是支持的
精确算术环境；不以环境差异放宽阈值或原验收。


## 实际验收收尾

node-0现有CPU/Python3.12.3、Xeon Platinum8463B、Linux x86_64；正式metadata仍
Rbeast0.1.25/NumPy2.2.6，原.so SHA a7432000… 已只读核对。
执行源码提交 `2f8971f4d2402ea64363edba1af7cb2ae97bdd4a`；本次11项实际检查均
exit0：源码/论文引用、12600前缀重算、16新增测试、Reporter4、检测8、算术/
非法输出contract、M4的65fixtures、P1的531840数组回读、隐私6测试、diff、
当前树隐私扫描。832原文件（STATUS/GAPS最终仅追加）、1424正式运行库文件
前后SHA一致；没有新增native fits/依赖/编译/GPU/NCCL/Redis。

`m5-s1-validation-01` 为FAIL，sources1、citation test1；其余检查0。该完整脱敏
回执在 data/validation-attempt01.json，私有11份log/command回执原样保留。
`m5-s1-validation-02` 全部0/PASS，原始日志在 runs/m5-s1-validation-02/，每项
有完整argv/代码与输入快照SHA、输出stdout/stderr SHA和真实环境/退出；公开
validation.json提供相对入口/脱敏argv。旧P1回读脚本输出的machine字段固定
写local macOS，本轮实际执行node-0，以本轮外层机器/命令回执为准，未改原脚本。
新的 native API/真实prefix再次fit、M2/M3编译hook、GPU/Redis/M6均NOT_RUN。

本次16个科学离线测试和完整性审计PASS不等于科学有效性PASS。最终全树检查
将在纳入source-receipts/validation与状态追加后执行，具体head/tree/文件内容
及其真实隐私CI由Draft PR与私有publication回执明确绑定；不沿用PR8或较早
提交CI。此后只发布/核验并停止，下一唯一任务是独立审核M5-S1。
