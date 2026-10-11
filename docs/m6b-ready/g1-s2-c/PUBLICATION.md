# 发布与实际 CI（ADAPTATION）

首证据发布：head `814eb7852fe0d0d425b54523e06324fc9440e716` / tree `f336b343dec9587f880006ee55712543bd65d825`，1773文件；普通 push 实际0，远端 head/tree 回读相同。main `ce984ea21a604092312442c7c788f2f4b244fad4`、base `3ba7dad2070ad13466b4f14562ee54fa4a3e818b` 不变。独立 Draft PR13，不合并。

PR CI run38109503450 / job114381935875，completed/success。日志实际 checkout 为临时 merge `80e9e307ecaf9c4b2b65802619ec7d83e6ed1d4b`，Git对象回读其 tree 等于首发布 head tree。原6privacy tests通过，TEXT_CHECK PASS /1773files/findings0。它只验证当前文本规则，不能证明 native、科学、GPU或缺失前测。原 PDF 仍 NOT_SCANNED_BINARY、版权问题待决；历史隐私/版权仍DEFERRED/OPEN。

最后新增 runner 的正式清单函数包括缓存；只读实际函数检查2339文件/含915缓存，native fits0/installations0，源SHA与最终runner相同。完整修正 installer/native runner NOT_RUN；本轮前测缺失不能回填，整体BLOCKED不变。实际拟合684d5c7、CLI-only补测4a4721c和原记录均保持。

本文件记录首发布证据。最终包含本文件和清单修正的精确head/tree及实际checkout CI另绑定在PR13描述与私有publication-receipt.json，避免文件自引用提交SHA。最终仍Draft/open，停止等待独立审核，不执行任务03。
