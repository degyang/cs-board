# ASSET-PROV-BE-002-V — 生成记录持久化与只读 API 独立验证

状态：done （PASS）
Owner：verification
工作区：`/mnt/d/Workstation/Projects/cs-board`

## Inputs

- 需求：`docs/Mountain/30-artifact-provenance-and-regeneration.md`
- 任务：`docs/workmates/assignments/ASSET-PROV-BE-002.md`
- 实现工作树：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`
- 实现回执：该工作树 `docs/workmates/receipts/ASSET-PROV-BE-002.md`
- HEAD：`e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`
- 冻结状态哈希：`2ea47f531a5d94bf2951803ac875f574b0c352fa40a45dcdd37b1ff1228a150f`（`git diff --binary HEAD` 加所有未跟踪文件内容清单）

## Required verification

- 逐条对照 BE-002 Done Predicate 审计 store、schema/语义校验、原子 JSON 写入、current/attempt 边界、媒体路径及结构化错误。
- 独立复跑直接与受影响测试，使用新的临时 `CSBOARD_DATA_DIR`；记录命令、退出码、数量、耗时与 skip。
- 实现者回执只证明直接 route endpoint；必须另行通过 ASGI/TestClient，或在新临时端口启动冻结代码并真实 HTTP 调用两个 GET URL。验证 status、磁盘原文 JSON、媒体 bytes/MIME/header、404 错误且无绝对路径泄露。不得以直接函数调用代替。
- 检查新的 `async` route 中同步文件 I/O 是否存在不可接受的事件循环阻塞；如无充分证据，不得因为绕过测试 transport 挂起就默认接受。
- 确认 diff 未进入 Provider、再生成、二进制替换、下游失效、前端或真实数据。

## Constraints and exit

- 只读审查实现；不修改实现、测试、需求或看板，不添加 skip。
- 不使用当前 8000 的真实数据；如启服务，使用临时数据目录和未占用端口，并只清理自己启动的进程。
- 回执写入 `docs/workmates/receipts/ASSET-PROV-BE-002-V.md`，结论必须是 PASS / FAIL / BLOCKED；附证据映射、命令与定位。
