# ASSET-PROV-BE-002-V — 生成记录持久化与只读 API 独立验证回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改实现、测试、需求或看板，未添加 skip。

## 冻结目标

| 项 | 值 |
| --- | --- |
| 工作树 | `/mnt/d/Workstation/Projects/cs-board-worktrees/backend` |
| HEAD | `e34ba6e`（`chore(repo): remove legacy web and flatten schemas`） |
| 冻结哈希 | `2ea47f531a5d94bf2951803ac875f574b0c352fa40a45dcdd37b1ff1228a150f` |
| 实现回执 | `cs-board-worktrees/backend/docs/workmates/receipts/ASSET-PROV-BE-002.md` |

---

## 1. Store / Schema / 语义校验审计

| # | 验证项 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| B1 | Schema 校验在写入前执行 | `save_current` / `save_attempt` → `_validate_record` → `self._validator.iter_errors(record)`；schema 无效则 raise `DomainError`，不创建目录或文件 | PASS |
| B2 | 跨字段语义校验 | `_validate_record` 检查 `record_scope == expected_scope`、`asset_id == asset_id`、`identity.task_id == task_id`、`identity.run_id == run_id`；任一不符 → `GENERATION_RECORD_IDENTITY_MISMATCH` | PASS |
| B3 | 路径 task ID 一致性 | `_resolve_project_output_path` 要求 `raw.parts[:2] == ["outputs", task_id]` 且 `len(parts) > 2`；schema 的 `output_path` pattern 也限制 `outputs/<id>/...` | PASS |
| B4 | 绝对路径 / `..` 拒绝 | `_resolve_project_output_path`: `raw.is_absolute()` 或 `..` in parts → `GENERATION_RECORD_PATH_INVALID`；`_validate_route_identity`: route 参数同理 → `GENERATION_RECORD_ROUTE_INVALID` | PASS |
| B5 | Secret 拒绝 | Schema 所有对象 `additionalProperties: false`；store `_validate_record` 调用 schema validator 后才写入 | PASS |
| B6 | 原子 JSON 写入 | `save_current` / `save_attempt` 均在 `task_lock` 内调用 `repository.write_json(target, record)`；`write_json` 使用同目录临时文件 + `os.replace` | PASS |
| B7 | current / attempt 边界 | `save_current` 写入 `generation.json`；`save_attempt` 写入 `attempts/<attempt>.json`；互不替换 | PASS |
| B8 | 读取再次验证 | `read_current` 先 `read_json` 再 `_validate_record(expected_scope="current")`；schema/identity/path 再次校验 | PASS |

## 2. API 路由审计

| # | 验证项 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| B9 | GET generation 返回磁盘原文 | `get_asset_generation` 直接 `return generation_records.read_current(...)`，不重建 DTO | PASS |
| B10 | GET media 仅 task-local | `get_asset_media` → `media_path` → `_resolve_project_output_path` 验证路径在 project_root 内；返回 `FileResponse(path, media_type=mime_type)` | PASS |
| B11 | 结构化错误无路径泄露 | `domain_error_response` 仅返回 `code` / `message` / `retryable` / `details`；NotFoundError / DomainError 不含绝对路径 | PASS |
| B12 | 错误码区分 | NotFoundError → 404 `NOT_FOUND`；DomainError → 400 `GENERATION_RECORD_*` 系列码 | PASS |

## 3. ASGI / TestClient HTTP 传输层验证

> 实现回执明确声明其测试仅直接调用 endpoint 函数，不是 HTTP 传输层验证。本节独立补充。

使用 `starlette.testclient.TestClient` 包裹 `FastAPI(mountain_task_router)`，临时 `CSBOARD_DATA_DIR`，真实 HTTP 请求：

| # | HTTP 测试 | 结果 | 证据 |
| --- | --- | --- | --- |
| H1 | GET generation (image) | 200, `asset_kind=image`, `record_scope=current` | PASS |
| H2 | GET generation (audio) | 200, `asset_kind=audio`, `record_scope=current` | PASS |
| H3 | GET generation (video) | 200, `asset_kind=video`, `record_scope=current` | PASS |
| H4 | GET media (image) | 200, `content-type: image/png`, bytes=16 | PASS |
| H5 | GET media (audio) | 200, `content-type: audio/wav`, bytes=16 | PASS |
| H6 | GET media (video) | 200, `content-type: video/mp4`, bytes=16 | PASS |
| H7 | Missing asset → 404 | 404, `error.code=NOT_FOUND`, response JSON 无 `/tmp` 或 data_dir 路径 | PASS |
| H8 | Path traversal `..%2F..` | 404, response 无绝对路径泄露 | PASS |
| H9 | Missing media (文件已删) | 404, `error.code=NOT_FOUND` | PASS |

全部 9 项 HTTP 传输层验证通过。JSON 响应体中无 `/tmp`、`/home` 或 data_dir 绝对路径。

## 4. Async 路由同步 I/O 风险审查

两个新路由均声明为 `async def`：

```python
@router.get(".../generation")
async def get_asset_generation(task_id, run_id, asset_id):
    return generation_records.read_current(...)   # 同步 I/O

@router.get(".../media")
async def get_asset_media(task_id, run_id, asset_id):
    path, mime = generation_records.media_path(...)  # 同步 I/O
    return FileResponse(path, ...)
```

`read_current` → `repository.read_json` → `Path.read_text` 是同步文件 I/O，在 `async def` 中直接调用会阻塞事件循环。`FileResponse` 由 Starlette 内部以 `anyio` 异步发送，不阻塞。

**风险评估**：`read_json` 读取单个小 JSON 文件（generation record），实际阻塞时间在微秒至低毫秒级；当前项目无高并发场景（本地单用户工具）。此模式与仓库中其他 `async def` 路由（如 `get_artifact_media`）一致，属于既有架构约定。

**结论**：存在理论上的事件循环阻塞风险，但不构成本次验证的阻断缺陷。如未来需高并发，应改为 `def`（FastAPI 自动线程池调度）或使用 `anyio.open_file`。当前不阻断。

## 5. 门禁独立复验

| 命令 | 独立结果 | 与回执一致 |
| --- | --- | --- |
| `CSBOARD_DATA_DIR=/tmp/<fresh> .venv/bin/python -m pytest -q tests/test_generation_record_schema.py tests/test_generation_record_store.py tests/test_mountain_contracts.py tests/test_stage_work_orders.py` | **34 passed, 3 warnings**, exit 0, 8.68s | ✅ 一致 |
| `git diff --check` | exit 0 | ✅ 一致 |

## 6. Diff 范围确认

| 文件 | 变更 | 越权？ |
| --- | --- | --- |
| `csboard/adapters/filesystem/__init__.py` | +1 行导出 `FilesystemGenerationRecordStore` | ❌ 未越权 |
| `webapp/mountain_task_api.py` | +24 行：两个 GET 路由 + store 初始化 | ❌ 未越权 |
| `tests/test_infographic_activation.py` | +8/-1 行（NEXT-BE-001 遗留 clock fixture 修复，非本票） | ❌ 未越权 |
| `csboard/adapters/filesystem/generation_records.py` | 新增文件（store 实现） | ❌ 未越权 |
| `tests/test_generation_record_store.py` | 新增文件（store 测试） | ❌ 未越权 |

未进入：Provider 调用、再生成、二进制替换、下游失效、前端、真实数据、共享看板。

---

## 综合结论

| 维度 | 结论 |
| --- | --- |
| Store schema/语义校验、原子写入、current/attempt 边界、媒体路径、结构化错误 | **PASS** |
| ASGI/TestClient HTTP 传输层（9 项，含 status/JSON/media/404/路径泄露） | **PASS** |
| Async 路由同步 I/O 风险 | 已识别，不阻断（既有架构约定，低并发场景可接受） |
| 门禁 34 passed, exit 0 | **PASS** |
| Diff 未越权 | **PASS** |

**最终判定：PASS**
