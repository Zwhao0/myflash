# TASK10 — G09 故障适用范围与 GPU 实验准入协议

授权：2026-10-11 用户明确要求只制定协议，不实施 GPU 故障注入，不启动 M6-B。
唯一基点 `f44e3fb44e48979298a13efbd9dccad5000c3eef`，
tree `1a4f6cec6597f907f9ebe647c62de921fbcb70e4`。
独立分支 `codex/task10-g09-protocol`，工作区 `m6b-task10-work`。
用户称基点已核验；本轮核验本地 HEAD/tree/干净状态，不补写独立审核 PASS。

## 最小修改范围（ADAPTATION）

- 新增本任务及 `docs/m6b-ready/task10-g09-protocol/` 内协议、空白运行清单、来源和本轮核验结果。
- `GAPS.md`、`STATUS.md` 仅追加；其余已有文件字节不变。
- 不修改任何运行代码、native ABI、测试、fixture、阈值、原始采集或预测。
- 私有本轮命令/日志在项目 `runs/task10-g09-protocol-20261011/`；不发布远端。

接口：仅文档规定未来 public runtime manifest / 私有 injector 与 evaluator 真值 /
封存 predictions / 独立 evaluation；JSON 是空白清单，不是可执行 launcher 配置。
所有 execution authorization 为空/false，不能通过修改一个布尔值绕过准入条款。

检查：本地只读 HEAD/tree/文件边界，所有继承文件字节校验，两文件追加校验，
新增 JSON/本地引用/来源 SHA/关键协议约束及 `git diff --check`。
不为文档变更重复 CPU 算法矩阵或声称 GPU 验收；不安装依赖、不探测服务器。
检查失败保留命令/退出/日志，修正文档后另编号复核；不扩大实现范围。

退出：完成可审阅本地提交，记录精确 HEAD/tree/diff，停止。
下一唯一任务为独立 TASK10 精确 HEAD 协议审核；审核协议不等于批准 M6-B 执行。
G09 实验适用性保持 OPEN，M6-B NOT_STARTED/NOT_RUN。

来源：PAPER `SPEC.md` S3/S4/S6/S7/S8/S9；ADAPTATION 既有任务05/07/08/09
契约与本轮实验预算/评估定义；UPSTREAM 官方 CUDA12.8、NCCL2.27.3、
PyTorch2.8、nvidia-smi 文档；EXTENSION 受控辅助负载和候选层评估。
精确出处及来源文件 SHA 在协议来源表和 SOURCE_LEDGER.json。
