# 检测接口 v1 与旧输出兼容

ADAPTATION task05：函数原有位置参数不变，新规则只由 keyword-only `approved_rules=True` 启用。False为默认且只接受真正bool；未启用时无新字段，保留原AMBIGUOUS_SPEC/unresolved/provisional字段及既有行为。

```python
from flash.change_detection import detect, prefix_replay
from flash.rbeast_adapter import RbeastAdapter

# C选择仍是独立、显式、经原身份门禁的opt-in；路径须为既有隔离环境。
c = RbeastAdapter(candidate_c_python="<existing-approved-C-environment>/bin/python")
evidence = detect(records, adapter=c, approved_rules=True)
replay = prefix_replay(records, adapter=c, approved_rules=True)
```

新证据 `interface_version="flash.detection.approved.v1"`，`approved_packet_head`绑定PR15精确head，`approved_rules={G01:a,G02:inclusive_span,G13:A}`，unresolved仅表示此检测接口之外的G20。这不表示G04/G09等系统缺口已关闭。adapter仍原返回全部raw/PARAMETERS/native日志/version/身份；其历史`scientific_status=AMBIGUOUS_SPEC`保留原模型证据原貌，不用改raw来证明新规则批准。调用新规则不选择C；调用旧规则也不被C选择隐式启用新规则。

候选字段 `model_candidate`只表示合法非padding模型槽；`qualified_candidate`表示当前prefix通过概率、spacing、恢复、正增长和A强度，不含年龄；`detection_trigger`才是它与当前 `t-j+1>20`的合取。`stages.persistence.decision`只是年龄比较，不可单独当成触发。每行原迭代、均值、样本数和过滤stage仍可追踪；padding保留。新路径移除旧 `provisional_duration_candidate`/`provisional_throughput_candidate`，替代以明确资格/触发字段。其他5口径与B不进入 OR/AND。

顶层DETECTION_TRIGGERED表示至少一个检测触发；没有触发且含不足候选时INSUFFICIENT_EVIDENCE；合法但无触发为NO_DETECTION_TRIGGER。非法input为INVALID_INPUT，native身份失败保持BLOCKED，超时/worker/非法raw/配置不符/数值溢出保持INSUFFICIENT_EVIDENCE。多候选不选择winner、不做告警去重、不冻结旧cp/baseline；输出保留每条证据。失败不能当健康或补零。

G13均值单位ms，A与B均无量纲，原始retained count是样本数，inclusive_span是原迭代编号跨度。实测吞吐没有work/walltime输入，明确null；B只是固定工作量代理。新路径对有限合法times仍可能因float64求和/派生溢出拒判，不采用改变算法的稳定均值替换来拟合输出。

顶层及新候选行 `final_alert=False` 恒定；未接生产告警/Reporter/Redis闭环，G20需后续独立授权。撤销是省略`approved_rules`；撤销C是省略adapter或使用`RbeastAdapter()`。本任务没有全局配置、环境变量开关或默认调用方改动。

只读历史复验（禁止native子进程，输出目录必须未存在）：

```sh
<existing-python-3.12> docs/m6b-ready/g2-approved-detector/verify_history.py --output <new-private-dir>
<existing-python-3.12> tests/m6b_ready_approved_detection.py -v
```

历史3.12输出逐字段严格相等在本机3.12.14实测通过；3.9.6 sample std/z末位不同实测失败保留，不声称跨Python版本精确全输出兼容。
