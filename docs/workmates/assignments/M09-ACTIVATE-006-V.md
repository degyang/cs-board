# M09-ACTIVATE-006-V — independent projection verification

状态：assigned

Owner：`verification`（Claude Code `mimo-v2.5-pro / medium`），只读验证冻结的主集成区 `/mnt/d/workstation/projects/cs-board`。可新写本任务回执和 `.workmates-evidence` JSON；不得修改实现、既有测试、pointer、服务配置、Secrets、frozen outputs 或主看板，不提交/合并/push。

## 冻结目标

- `csboard/application/commands.py` SHA-256 `db452215848e2d840f64b0a4bfb1314e1bd28b6c8ef9e51a1236586200d19782`
- `tests/test_m09_activate_006.py` SHA-256 `8e3af1c9c778bbd651d877d2fcef7fcb2a0eea1a5956016c992fb604d6f8b51c`
- backend 回执：`docs/workmates/receipts/M09-ACTIVATE-006.md`
- 当前 8000：tmux `%23` / PID `240721`；5182：PID `124360`

## 验证标准

1. 验证前后两个冻结文件 hash 不变。
2. 独立运行 `tests/test_m09_activate_006.py` 与直接相关 activation projection/capability tests；允许仅排除既有、环境相关的 `browser_version_uses_renderer_resolver`，必须如实记录。
3. 证明 supported=true 的 create-options 选项 `available=true` 且不存在误导性 `reason`。
4. 证明 supported=false with reason 保留稳定 reason；reason 缺失/空/非字符串时返回 `CAPABILITY_NOT_AVAILABLE`。
5. 只读查询真实 8000 与 5182 create-options：动态信息图均 `available=true` 且无 `reason`；8000 health 服务数仍为 10。不得 POST Task 或调用 provider。
6. `git diff --check` 针对冻结实现/测试通过；运行 `./scripts/workmates verify --role verification --evidence <本轮新 JSON>`。
7. 写 `docs/workmates/receipts/M09-ACTIVATE-006-V.md`，给出 PASS/FAIL/BLOCKED、命令/exit/数量、实时 API 摘要、证据路径与 pre/post hashes。完成后固定客户端保持 idle。

若任何实现 hash 漂移、实时 capability 再次关闭或 API 仍含 reason，停止并给 FAIL/BLOCKED，不自行修复。
