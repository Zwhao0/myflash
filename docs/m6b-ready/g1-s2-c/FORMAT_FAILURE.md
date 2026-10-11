# 格式检查失败保留（ADAPTATION）

git diff --cached --check 实际 exit2；完整 stdout 证据有原输出尾随空白。原日志不删改、不截断，格式失败另列，不冒称 PASS。私有 diff-format01.stdout/receipt.json 保留全部位置和输出 SHA。科学断言和原 CPU 比较器未改；当前工程整体仍 BLOCKED。
