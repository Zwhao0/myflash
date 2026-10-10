# M4 离线两阶段定位
用户 2026-10-10 审核 M3 后完整授权 M4；内部顺序实施，完成后停止。消息 M4d 后半段截断，已请求补充；已明确的离线范围继续。
起点：服务器 a1ed7e2b5a6c0c6e3ae8d032567add2189fe1a79/tree177745dd097536c46e3ef5d72d77bd5e6b717184，与未合并 PR2 最新30ca740完整tree相同。分支codex/m4-localization，保留M3全部历史，不从main开始。
最小任务顺序：a输入契约/校验；b两阶段+敏感性/独立scores；c固定手算fixture与CLI；d已有真实数据离线回放；e有限真实多组正常验证（具体实验约束待剩余消息）。
允许新增flash/profile_input.py、flash/localization.py、scripts/m4_*、tests/m4_*、docs/m4/**、本任务，更新STATUS/GAPS/ARCHITECTURE/PLAN。native、Reader、M1–M3源/数据/断言不改。
接口：schema1 normalized records + 显式parallel states + completeness manifest；独立CLI JSON输入输出。单位us/count元素/sample独立scope。外部evaluator持有真值，算法不接收目标rank/场景类别。
测试：CPU手算固定数据+拒绝污染/缺失/重复/无效/共享Group/身份问题；已有M3白名单与raw一致性回放；每fixture保存输入/手算期望/输出/命令/退出。
退出：有效离线分析0（含无候选/临时候选）；坏数据2；规格分歧在JSON内AMBIGUOUS_SPEC；不把0当完整判决复现。CPU无GPU资源清理；raw只读，不写回M3。
禁止BOCD/Rbeast/Redis/闭环/恢复/MoE/降频/OOM/网络干扰/其它作业终止。来源分类见docs/m4/SOURCES。
