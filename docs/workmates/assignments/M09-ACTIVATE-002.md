# M09-ACTIVATE-002 — repair real service probe timeout construction

状态：assigned

Owner：`backend`（独立工作区 `/mnt/d/Workstation/Projects/cs-board-worktrees/backend`）；PM 负责集成，verification 结论仍以集成区新证据为准。

你不是代码库中的唯一执行者。保留现有 M09 activation/V1/V2、资产和语音改动，不回滚他人修改，不修改集成区看板，不提交、合并或推送。

## 事实与目标

集成区真实 probe 对 IndexTTS 和两套 MiMo 均立即返回通用错误。PM 在当前项目 venv 直接调用 `csboard.adapters.filesystem.service_registry._get_probe_timeout()`，得到：

`ValueError: httpx.Timeout must either include a default, or set all four parameters explicitly.`

当前实现 `httpx.Timeout(connect=2.0, read=5.0)` 与已安装 httpx 不兼容，使所有 HTTP probe 在发出请求前失败。目标是用最小兼容修正构造完整 timeout，并新增不访问网络的回归测试，证明 connect/read/write/pool 均有界且不会抛异常。

## 范围

- 可修改：`csboard/adapters/filesystem/service_registry.py`、直接覆盖 timeout/probe 的现有或新增后端测试、backend worktree 回执 `docs/workmates/receipts/M09-ACTIVATE-002.md`。
- 不得修改服务定义、Secrets、activation pointer、capability 策略、frozen outputs、frontend、assignment 或 board。
- 不启动服务、不执行 renderer、不真实调用外部 provider；PM 集成重启后执行真实 probe。

## 验收

1. `_get_probe_timeout()` 在当前 venv 成功返回 httpx timeout，四类超时均为有限正数；保留 connect 2s/read 5s 的原意，write/pool 取明确合理值。
2. 回归测试覆盖构造成功，并覆盖至少一个 HTTP probe 不再因 timeout 构造进入外层 `PROBE_ERROR`（使用 mock transport/client，不访问网络）。
3. 运行 focused service registry/API tests、scoped `git diff --check`，列出命令、exit code、数量和最终 hashes。
4. 回执 verdict 为 `READY_FOR_VERIFY` 或 `CHANGES_REQUIRED`。

停止条件：若修复需要改变服务契约、真实凭据或 capability 门禁，写 `CHANGES_REQUIRED` 并停止。
