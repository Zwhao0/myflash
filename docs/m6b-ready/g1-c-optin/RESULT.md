# Task03 受控 CPU 诊断 opt-in：工程验收通过

CALLER_ADOPTION_PASS 仅限显式受控 CPU 调用。前置 PR13 精确 head319600d/tree432f09f 的独立审核与 Gate1 ACCEPTED_WITH_DEVIATION 来自本轮负责人决定；915缓存文件历史安装前SHA仍 NOT_CAPTURED，不宣称完整环境保全PASS。默认生产检测器未切换，科学门禁仍 OPEN。

接口：`detect(records, adapter=RbeastAdapter(candidate_c_python="<existing-s2-environment>/bin/python"))`。此绝对路径是既有 task02 execution01/.venv-m5-s2-c/bin/python；没有安装或编译。每实例显式选择，没有全局/environment开关；解释器的venv入口不resolve到系统Python。撤销方式：省略adapter或构造`RbeastAdapter()`，默认命令仍为 `[sys.executable, adapter_source, '--worker']`。flash/change_detection.py 未修改。

候选worker实际导入的原生扩展模块取自sys.modules，核对实际文件SHA256固定1f08fbc9f24d0c00eb21f91f357519f15289ffd1ef18b9e7e0aca47c2596faeb，并要求/proc/self/maps的路径、设备和inode匹配；缺失/身份不符在读取拟合输入、调用rb.beast前exit78/BLOCKED。版本号0.1.25仍检查，但不能代替SHA。记录映射segment权限/offset/device/inode/path；ASLR虚拟地址不进入可比较输出，不调整数值/标签/断言。默认路径仅追加身份观察，观察失败也继续原拟合；C opt-in严格拒绝失败。

最终执行85c949abc6abd64b74241fe7d62d93f24346eb8e/treeafa636f05bcab153716e12c135d81c76d086c23d；此前dd71cf7初验与87d2137默认观察错误路径补验均保留，没有原生失败重试。node-0 Xeon Platinum8463B，现有Python3.12.3/GCC13.3.0、NumPy2.2.6、Rbeast0.1.25。最终7新CPU契约测试、原Reporter4/检测8/算术回归，以及真实detect四调用和原strict-prefix均exit0；初验原strict API及field断言exit0（未修改这些函数/测试）。三阶段实际子命令共22个，全部exit0/无timeout；各自退出码在三份validation中。

最终四调用：默认原.so a7432000…拟合完成/exit0；C.so1f08fbc9…拟合完成/exit0；误选同版本原.so时exit78、native_fit_started=false、raw=null；撤销opt-in后原.so再次拟合完成/exit0。每轮3个实际fit，输出始终final_alert=false/统计证据。最终sustained原45前缀/35fit、原24短前缀/14fit全输出严格相等，原断言未改。最终52fits，三个代码阶段累计63fits；没有11080矩阵重跑。原二进制完整后验重复性历史FAIL没有重测或重分类。ABI/AVX512既有工程审核由前置固定二进制继承；本轮只主张真实加载/拟合，不新做ISA/RNG矩阵。

真实命令/退出码/180s子进程deadline/timeout/stdout/stderr SHA及执行source SHA见evidence各validation.json；本次自有子进程均wait，超时0；worker默认30s。原/C二进制每次pre/post相同；未审计缓存、未补造历史SHA。全环境保全不作PASS。raw-index及raw-public-correspondence绑定私有原件；最终四调用完整JSON公开，prefix完整原件留本run并给SHA。首次bundle引用错误fetch128/parent1保留且在拟合前修复；所有CPU实际回归exit0。没有GPU/NCCL/Redis/M6-B或最终故障告警。

当前调用方：flash.change_detection.detect默认创建原adapter；scripts/m5_replay.py、tests/m5_replay.py、tests/m5_causality.py依各caller的sys.executable；scripts/m5_verify_ddp.py的原GPU入口未运行/未改。scripts/m5_repeatability.py和m5_p1_diagnostic.py使用其历史CapturingAdapter子类/独立native worker，未改。只有新tests/m6b_ready_c_native.py以正式解释器启动并显式将一个detect诊断调用指向C。测试中的C解释器原prefix回放只是CPU回归，不构成生产默认切换。

下一唯一动作：ChatGPT对独立Draft PR精确head及证据技术审核；交付后停止。G01/G02/G13/G04/G09/G20仍OPEN，整体M6B-READY未宣称PASS。
