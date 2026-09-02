# CCF-MANUAL-STAGE-WORKBENCH-17 实际交付回执

## 范围

本轮从 `176202b` 起，仅补齐 §3Y 要求的浏览器工作台行为测试与证据；未接入 Gate API、未新增业务页面、未修改后端。

## §3Y 行为证据

实现/测试提交：`c960bfb test(mountain-web): prove workbench polling isolation`

`web-v2/tests/execution-plan.test.tsx` 的真实测试名称与结果：

- `renders the canonical six cards in fixed order with complete contract fields` — 通过。
- `does not expose automatic plan controls or Gate mutation actions` — 通过。
- `keeps six cards safe when there is no active run` — 通过。
- `clears the previous task identity before the next task request settles` — 通过。
- `keeps B visible when pending A later resolve` — 通过；A `fetchTask` 保持 pending，B 先 resolve。
- `keeps B visible when pending A later reject` — 通过；B 先 resolve，A 随后 reject，A 标题与 error 均不可见。
- `keeps every A marker out of the B page while B is pending and after it completes` — 通过，覆盖标题、Run、Artifact、Input、Unit、Event、Log。
- `lets B win when A resources are still pending and A later rejects` — 通过，Inputs/Units/Events/Logs 各自 reject 后 B 保持。
- `ignores every late A resource success after B has completed` — 通过，A 的 Inputs/Units/Events/Logs 各自 resolve 后仍不显示，B 数据保持。
- `resets cursor, dedup, units, logs and artifacts for run-a to run-b with the same event sequence` — 通过；两个 Run 的 Event 均为 `sequence=1`，B 从 cursor `0` 建立，B 的 Unit/Event/Log/Artifact 覆盖 A。
- `uses an unavailable status for missing stages instead of fabricating pending or attempt zero` — 通过。
- `renders canonical pending status with attempt and completed count` — 通过。
- `renders canonical running status with attempt and completed count` — 通过。
- `renders canonical waiting-external status with attempt and completed count` — 通过。
- `renders canonical waiting-review status with attempt and completed count` — 通过。
- `renders canonical succeeded status with attempt and completed count` — 通过。
- `renders canonical failed status with attempt and completed count` — 通过。
- `renders canonical skipped status with attempt and completed count` — 通过。
- `renders canonical stale status with attempt and completed count` — 通过。
- `renders canonical cancelled status with attempt and completed count` — 通过；以上 9 种均放在 canonical Stage，断言原样标签、`attempt 7` 与 `0/6` 或 `1/6`；unknown Stage 由首个 baseline 用例单独验证。
- `keeps the five resource requests safe after unmount for independent late resolve/reject` — 通过；Inputs resolve、Units reject、Events resolve、Logs reject，卸载后 console error/unhandled rejection 均为 0，timer count 为 0。
- `stops task and resource polling after terminal response, including StrictMode repeat render` — 通过；fake timers 前进 10 秒得到 terminal，调用计数为 `fetchTask=3, fetchUnits=2, fetchEvents=2, fetchLogs=2`，再前进 30 秒仍为相同计数；StrictMode 重复 render 也通过。
- `does not reschedule a resource request that completes after terminal polling stops` — 通过；terminal 切换时 Units/Events/Logs 请求保持 pending，迟到 resolve/reject 后再推进 30 秒，调用计数保持 `fetchTask=2, fetchUnits=1, fetchEvents=1, fetchLogs=1`。

## 门禁结果

- `npm --prefix web-v2 run build`：通过。
- `npm --prefix web-v2 test -- --run`：15 个文件、367 项测试全部通过。
- `/tmp/ccf-manual-stage-workbench-17-test.log` warning scan：`not wrapped in act`、Router Future Flag、Unhandled/unhandled rejection、unmounted state update 均 0 命中。
- `npm --prefix web-v2 run test:contract-checker`：48 项通过（2 个文件）。
- CCF/CCB/WORKBENCH/STAGE-GATE 静态扫描：0 命中。
- project/split/executionMode/manualStages 静态扫描：0 命中。
- localStorage/sessionStorage/Math.random 静态扫描：0 命中。
- `git diff --check f2b15f9...HEAD`：通过。
- 当前分支保持本地提交，未推送；回执提交后工作树保持 clean。

## 限制与审核边界

测试输入均为明确标记的测试 fixture，不代表用户真实制作成果。本回执不代表 PM 审核通过，不进入 `USER_ACCEPTANCE`，等待审核。
