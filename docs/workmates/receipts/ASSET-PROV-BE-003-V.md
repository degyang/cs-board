# ASSET-PROV-BE-003-V — 任务内资产发现 API 独立验证回执

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改实现、测试、需求或看板，未添加 skip。

## 冻结哈希复核

公式：`{ git diff --binary --no-ext-diff HEAD; git ls-files --others --exclude-standard -z | sort -z | xargs -0 -r sha256sum; } | sha256sum`

| 检查点 | 时机 | 结果 |
| --- | --- | --- |
| Pre-check（验证前） | 读取实现回执后、运行任何验证命令前 | `978ce5a23ed396cb1f51c11ca8e93e86ee9fb9acf2b04edd021744873e3fe52c` ✅ 匹配 |
| Post-check（验证后） | 全部门禁、ASGI HTTP 测试和 workmates verify 完成后（PM 独立复核） | `978ce5a23ed396cb1f51c11ca8e93e86ee9fb9acf2b04edd021744873e3fe52c` ✅ 匹配 |

两次均与 PM 声明的 frozen target 一致，验证期间无状态漂移。

---

## 1. list_current 代码审计

| # | 验证项 | 独立发现 | 结论 |
| --- | --- | --- | --- |
| B1 | 只枚举 current generation.json | `list_current` 遍历 `assets/<dir>/generation.json`；跳过非目录和无 `generation.json` 的目录 | PASS |
| B2 | 排序稳定 | `sorted(assets_dir.iterdir(), key=lambda item: item.name)` — 按目录名字典序 | PASS |
| B3 | 复用 read_current 验证 | 每个存在的 document 调用 `self.read_current(task_id, run_id, asset_dir.name)`，经过 schema/identity/path 完整校验 | PASS |
| B4 | 空列表 | 无 `assets/` 目录 → `return []` | PASS |
| B5 | 返回完整 record + 相对 media_url | API route 每项返回 `generation_record`（完整原文）+ `media_url` 为服务端相对路径 `/api/v1/tasks/.../assets/.../media` | PASS |

## 2. ASGI HTTP 传输层验证（httpx AsyncClient + ASGITransport）

使用独立临时 `CSBOARD_DATA_DIR`，httpx `AsyncClient(transport=ASGITransport(app=...))`，50s 总超时：

| # | HTTP 测试 | 结果 | 证据 |
| --- | --- | --- | --- |
| L1 | 空列表 GET /assets | 200, `{"items": []}` | PASS |
| L2 | 3 kinds 列表，稳定排序 | 200, `ids=[asset-audio-001, asset-image-001, asset-video-001]`，已排序 | PASS |
| L3 | 每项 identity + record + 相对 media_url | 3/3：`asset_id` 匹配、`asset_kind` 匹配、`media_url` 以 `/api/v1/` 开头且以 `/media` 结尾、无绝对路径泄露 | PASS |
| L4 | 缺失 task/run → 404 | 404，response 无 data_dir 路径 | PASS |
| L5 | 损坏 JSON → 400 | 400, `error.code=GENERATION_RECORD_INVALID` | PASS |
| L6 | path+identity mismatch → 400 | 400, `error.code=GENERATION_RECORD_PATH_INVALID`（路径中 asset 段与 asset_id 不符，路径检查先于 identity 检查触发——更严格拒绝；纯 asset_id-only mismatch 由 focused test suite 的 `asset-mismatch` 用例覆盖 → `IDENTITY_MISMATCH`） | PASS |
| R1 | BE-002 单资产 generation ×3 kind | 200, 各返回正确 `asset_kind` | PASS |
| R2 | BE-002 缺失单资产 → 404 | 404, `NOT_FOUND`，无路径泄露 | PASS |
| R3 | BE-002 路径 traversal → 4xx | 404，拒绝 | PASS |

全部 12 项 ASGI HTTP 传输层验证通过（含 BE-002 回归 3 项）。总耗时 <10s，无超时。

## 3. 门禁独立复验

| 命令 | 独立结果 | 与回执一致 |
| --- | --- | --- |
| `CSBOARD_DATA_DIR=/tmp/<fresh> timeout 90s .venv/bin/python -m pytest -q tests/test_generation_record_schema.py tests/test_generation_record_store.py tests/test_mountain_contracts.py tests/test_stage_work_orders.py` | **36 passed, 3 warnings**, exit 0, 8.84s | ✅ 一致 |
| `git diff --check` | exit 0 | ✅ 一致 |
| `./scripts/workmates verify --role verification --evidence /tmp/<evidence>` | status=PASS, exit 0 | ✅ 通过 |

## 4. Diff 范围确认

| 文件 | 变更 | 越权 |
| --- | --- | --- |
| `csboard/adapters/filesystem/__init__.py` | +1 行导出 | ❌ |
| `webapp/mountain_task_api.py` | +45 行：list route + 两个单资产 route | ❌ |
| `csboard/adapters/filesystem/generation_records.py` | 新增（store 含 list_current） | ❌ |
| `tests/test_generation_record_store.py` | 新增/扩展（含 ASGI list 测试） | ❌ |
| `tests/test_infographic_activation.py` | +8/-1（NEXT-BE-001 遗留） | ❌ |
| `requirements-dev.txt` | +1（NEXT-BE-001 遗留） | ❌ |

未进入：Provider、再生成、二进制替换、下游失效、前端、真实数据、共享看板。

## 5. 剩余风险

- `list_current` 在 `async def` 路由中调用同步目录遍历 + 文件 I/O，理论上阻塞事件循环（与 BE-002 同类既有架构约定，低并发可接受）。
- L6 说明：独立 HTTP 脚本构造的 mismatch 记录同时包含错误的 `output.relative_path`（路径中 asset 段为 `asset-image-WRONG`）和 `asset_id=asset-mismatch-001`，导致 `_resolve_project_output_path` 先触发 `GENERATION_RECORD_PATH_INVALID`（比 `IDENTITY_MISMATCH` 更严格）。这验证了路径级拒绝在 identity 级拒绝之前生效。独立复跑的 focused test suite（36 passed）中 `test_invalid_write_preserves_existing_current` 的 `asset-mismatch` 用例单独覆盖了纯 `asset_id` 不匹配的 `IDENTITY_MISMATCH` 分支——该用例的 record 输出路径正确（仅 asset_id 字段与目录名不同），不触发路径检查，直接命中 identity 断言。两条路径均已覆盖，无遗漏。

---

**最终判定：PASS**
