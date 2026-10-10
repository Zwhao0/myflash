# M3: 手动 CUDA Event 剖析与机制验证
用户2026-10-10完整授权M3a–M3d，内部顺序推进后停，不进入M4。
前置: PR1已merged；server64badbf的tree79a1254与PR最新f8316cf相同。开发分支codex/m3-profile从server审核源创建，保留历史。
允许native/flash/tests/scripts的最小M3实现、docs/m3、STATUS/GAPS/本任务。原M1入口和数值断言不改。
M3a: ABI2/control+epoch+边界、Reader尾部恢复与CPU回归。
M3b: 单操作与同stream单设备阻塞Group CUDA Event；复杂路径显式unsupported。
M3c: A无故障、B两种CPU迟到、C GPU依赖、D跨RoCE、E Group、F16rank。
M3d: M2回归、两轮0→1→0、错误/计数/开销验证。
每run<=300s/PG120s；预检>=3072MiB余量、运行末<=2048MiB；仅本run独立进程组timeout结束，已闭合排空对象精确unlink。禁止降频/OOM/网络注入/终止其他作业/系统升级。敏感日志服务器保存。
