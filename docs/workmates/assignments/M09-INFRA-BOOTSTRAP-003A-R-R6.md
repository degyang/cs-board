# M09-INFRA-BOOTSTRAP-003A-R-R6 — shared ASGI lifecycle static root-cause map

状态：done — static G0 input only; no P3a/P4 authority
Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`；正式 role，主集成区只读调查）
模式：一次、静态、无执行诊断

## Goal

R-R4 和 R-R5 分别在 `TestClient.__enter__` 与一次 `httpx.ASGITransport` 请求前/中观察到共享的 API 生命周期阻塞，而同一临时根的直接 `CapabilityService.snapshot()` 能完成。本票只建立可核查的调用图：`create_app()`、路由/中间件/生命周期、同步 capability handler 及其 sync-to-thread 执行路径。它不重跑任何 HTTP 探测，也不推断 P3a 合同已通过。

按用户确定的 boundary-first vertical slice，本票也不调查或建议 Remotion 内部图片生成的逐图观测/治理；那一层是允许的黑盒，和本次 API lifecycle 根因无关。

## Authoritative inputs

- 集成区及唯一允许写回执的目录：`/mnt/d/Workstation/Projects/cs-board`
- 前序回执：`docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R4.md`、`docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R5.md`
- 目标实现（静态读取）：`backend/mountain_server.py`、`backend/mountain_capability_api.py`、被 `create_app()` 纳入的 router/middleware/lifespan 代码，以及经由静态 import/调用关系可达的同步 dispatch 或依赖构造代码。

## Allowed work

仅使用文本/语法静态检查，例如 `rg`、`nl -ba`、`sed`、`git diff --check`、`git diff -- <P3a scoped paths>`；可创建一个新的、无秘密的 `/tmp/m09-p3a-r6-static-map.txt` 作为中间静态摘录。必须逐项记录：

1. `create_app()` 创建应用、安装 middleware、构造 registry/secret store/dependencies 和纳入 capability router 的精确顺序（文件与行号）。
2. `/api/v1/capabilities` handler 是 sync 还是 async、它到 `CapabilityService.snapshot()` 的精确调用边；若框架将 sync handler 转给 worker/thread pool，只能依据本地安装依赖的源码或已锁定版本代码进行静态说明，并标明证据位置。
3. 可达的 startup/lifespan hooks、request middleware 和 dependency constructors；明确哪些在 capability handler 前、哪些不在该路径中，不能把未调用的 router 当作根因。
4. 已有 R-R4/R-R5 stack marker 与上述静态路径相交的最窄位置，及每个候选是否有直接静态证据。结论必须区分“证据支持”“尚不能判断”和“已排除”。
5. 若静态证据揭示一个明确缺陷，提出最小的后续 **owner + 文件范围 + 验证方法**；仅提出，不修改、不实现。若没有明确缺陷，也必须明确说明下一步需要何种非等价、经 PM 许可的证据。

## Prohibitions / stop conditions

不得运行 Python、pytest、HTTP/ASGI/TestClient/AsyncClient、应用 import、`create_app()`、服务、CLI 或任何脚本；不得启动/重启/停止服务或终止进程；不得修改产品代码、测试、依赖、配置、看板、既有回执或 P3a scoped files。不得执行 P4/P6/P3b/activation/render/task creation。发现需要动态执行才能继续时，停止并在回执中标为 BLOCKED；不要执行等价 HTTP 重试。

## Done predicate and receipt

只写主集成区的新回执 `docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-R-R6.md`。回执首段必须先写明已读取本任务、确认正式 verification role 与主集成区路径、并确认不执行任何动态命令；这段文字是 PM 的显式派发确认。其余内容须包含静态命令清单、精确文件/行号调用图、候选根因矩阵、是否发现可实施缺陷、任何 `/tmp` 中间文件路径、P3a scoped diff 未变的静态检查，及明确结论：本票既不是 P3a PASS/FAIL，也不解锁 P4。完成后停止等待 PM；只有 PM 可安排修复或独立验证。
