# 新增 runner 调用参数修复（ADAPTATION）

首轮采样执行代码固定于 `684d5c7a435fc36877b38e5397e2a1960eb4a354`。新增 runner 未向既有 `tests/m6b_ready_cursor_contract.py` 传入 argparse 强制要求的 `--output`。两批采样按原计划执行，之后保存该调用的 exit 2、原 stderr、首轮 parent exit 1；不改原测试，不覆盖原执行状态。

`4a4721c1426ba19f66b837220db82990987f6750` 仅在新增 runner 添加必需的 `--output` 参数。私有 `finish_acceptance.py` 先验证首轮精确错误与其他已执行命令结果，再执行此前尚未执行的 cursor/extra/privacy 回归及原 P1 完整比较器。既有模型、fixture、阈值、断言、比较器完全不变。补测没有重新安装或重新 native 采样，原始采样目录在补测前后整目录逐文件 SHA 核对。

补测结果独立留证，不将首轮失败改写成 exit 0。参数调用错误不属于候选 C 的数值失败，但仍是本轮失败记录。完整正式环境安装前清单缺口单列在 `FULL_MANIFEST_GAP.md`，整体验收继续 BLOCKED。
