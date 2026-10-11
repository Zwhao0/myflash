# G02 六种计数口径与论文冲突

PAPER §3.4.3 p40明确“持续超过20个迭代”，§3.4.5 p44写窗口变点位置[1,W-k]、k=1/2、检测1–2迭代；冲突保留。推荐 inclusive_span 为主要论文字面对照，其余仅敏感性诊断；年龄不证明每一步都退化，不能同时声称1–2次最终检测。

令j为当前映射原cp，t为当前最新完成原iteration，R为当前保留右侧样本数（含cp），F为已选A/B。每个门槛必须与同一当前前缀概率/间距/恢复/正向退化/强度合取。

| 选项 | 精确规则 | 仅计数最早边界 | 来源/限制 |
|---|---|---|---|
| inclusive_span | t-j+1>20 | t=j+20 | ADAPTATION: 21 inclusive observed positions; age alone does not prove physical degradation |
| exclusive_span | t-j>20 | t=j+21 | EXTENSION: 21 elapsed gaps, one step later |
| retained_samples | R=len(current retained right[i:])>20 | t=j+20 only with no removals | EXTENSION: rolling-window/removal can erase evidence |
| qualified_prefixes | S(t,j,F)>20; S=previous+1 only same original j, same formula F, current qualified and previous iteration t-1 qualified; otherwise0/reset | first qualified prefix+20 | EXTENSION: missing/invalid prefix, cp drift, lost probability/spacing/recovery/strength reset; not proof of physical continuity |
| k1 | t-j>=1 | t=j+1 | ADAPTATION: original-iteration reinterpretation of PAPER c<=W-1; compressed guard instead N-1-i>=1 |
| k2 | t-j>=2 | t=j+2 | ADAPTATION: original-iteration reinterpretation of PAPER c<=W-2; compressed guard instead N-1-i>=2 |

含首点在j+19为20点false，j+20为21点true；排首点j+20为20间隔false，j+21为21间隔true；retained/streak20false、21true。streak同一原cp/同一公式连续qualified prefix，未合格/非法/缺失/观测不连续/cp漂移均清零，新cp合格从1起。没有资格的老cp不能凭年龄报警，窗口滑出不冻结baseline。

P44的1-based c<=W-k在未删点时对应t-j>=k。压缩轴应使用N-1-i>=k；删点后两者不同，当前native rightmargin0仍不实现任何新k门槛。k1/k2作为主要规则时不能宣称满足p40；采用inclusive时不额外OR进k1/k2。

六个时刻分别保存：独立评估真值起点、当时模型cp、首次概率越线、首次通过其他过滤/强度、首次所选持续性合格、最终告警。最后一项始终null。真值只用于离线评价，不给检测器；“观测22−起点21=1”是完成迭代编号差，同时含两个已完成退化样本，不是CPU拟合或网络/剖析墙钟延迟。

全部七固定场景、两批、A/B、六口径的历史首次时刻见SCENARIO_COMPARISON.json和RESULT.md。sustained A/B:无新门槛22、含首41、排首42、retained41、连续42、k1为22、k2为23。growth20 A的含首在43才联合合格；recovery早期候选不能用未来恢复消掉。这些是历史合成CPU输出，非真实GPU时延。

后续时延应单列：迭代完成→发布→读确认→拟合结束→候选/最终判决→下发→ACK→有效采样→汇总→分析→总时延。跨机时钟误差/同步和工作量须记录。G03剖析max(2.2T,20s)不改；不可用候选年龄替代所有阶段延迟。
