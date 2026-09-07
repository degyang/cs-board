# M09-G0-LIFECYCLE-001-V — independent boundary verification

结论：**PASS**

Owner：verification（Claude Code `mimo-v2.5-pro / medium`）。
只读验证，未修改产品、测试、看板或公开 capability。

## 冻结验收面

| 项 | 值 |
| --- | --- |
| Assignment | `assignments/M09-G0-LIFECYCLE-001-V.md` |
| G0 lifecycle receipt | backend worktree `receipts/M09-G0-LIFECYCLE-001-R.md` |
| Baseline receipt | backend worktree `receipts/M09-BASELINE-CAPABILITY-001.md` |
| Backend worktree HEAD | `e34ba6e`（`chore(repo): remove legacy web and flatten schemas`） |
| Permitted scope files | `backend/mountain_server.py`, `backend/mountain_capability_api.py`, `tests/test_capabilities_api.py`, `tests/test_cli_capabilities.py`, `csboard/application/capabilities.py` |

## 验证项

### 1. Diff 范围

| 变更文件 | G0 scope | 说明 |
| --- | --- | --- |
| `backend/mountain_server.py` | ✅ | 新增 untracked 文件；含 `CSBOARD_TEST_SKIP_MODULE_APP=1` guard |
| `backend/mountain_capability_api.py` | ✅ | 新增 untracked 文件；async handler |
| `csboard/application/capabilities.py` | ✅ | `toolchain_probe` constructor injection + `_toolchain_checks()` |
| `tests/test_capabilities_api.py` | ✅ | httpx ASGI transport 替代 TestClient；新增 infographic `supported=false` 断言 |
| `tests/test_cli_capabilities.py` | ✅ | `webapp→backend` import 检查重命名 |
| `tests/test_infographic_capability.py` | baseline | `_cap()` helper + `TOOLCHAIN_COMPONENTS` 常量（baseline capability 任务） |
| `csboard/adapters/filesystem/__init__.py` | 非 G0 | ASSET-PROV 工作（generation records import） |
| `requirements-dev.txt` | 非 G0 | ASSET-PROV 工作（Pillow 依赖） |
| `tests/test_infographic_activation.py` | 非 G0 | 既有 fixture 修复 |
| `webapp/mountain_task_api.py` | 非 G0 | ASSET-PROV 工作（asset endpoints） |

**无 activation/renderer/V1/V2/V3/ffprobe/task creation/service restart/public submission 改动。未越权。**

### 2. Bounded lifecycle proof

```text
GET /api/v1/capabilities → HTTP 200
Top-level keys: ['items', 'providers']
Infographic supported: False
No residual data.
```

**PASS。**

### 3. Scoped tests

```text
.venv/bin/python -m pytest -q tests/test_capabilities_api.py tests/test_cli_capabilities.py
→ 10 passed in 3.53s, exit 0
```

**PASS：全绿。**

### 4. Combined gate

```text
.venv/bin/python -m pytest -q tests/test_capabilities_api.py tests/test_infographic_capability.py tests/test_cli_capabilities.py
→ 41 passed, 1 failed in 5.32s, exit 1
```

唯一失败：

```text
tests/test_infographic_capability.py::test_bootstrap_ready_still_requires_real_smoke_evidence
expected: REAL_SMOKE_EVIDENCE_REQUIRED
actual:   EVIDENCE_MISSING
```

这是 V3 后 activation gate，保留不删不改。无其它 failure，无 scope drift。**PASS。**

### 5. toolchain_probe constructor injection

| 测试 | 结果 |
| --- | --- |
| `None` probe → fail-closed `NODE_NOT_FOUND` | PASS |
| Throwing probe → fail-closed `NODE_NOT_FOUND` | PASS |
| Malformed probe（wrong shape）→ fail-closed `NODE_NOT_FOUND` | PASS |
| Valid probe → 7 toolchain components all ready | PASS |
| Infographic `supported=False` even with all-ready toolchain | PASS |
| `_toolchain_checks` 不读取 activation/P6 evidence | PASS |
| 不把 public support 置真 | PASS |

**PASS。**

### 6. Hygiene

- `git diff --check`：exit 0。
- 无残余 pytest 进程。
- 无 V1/V2/V3/activation/render/ffprobe/task creation/service restart evidence。

**PASS。**

## 综合结论

| 维度 | 结论 |
| --- | --- |
| Diff 范围仅涉及 G0 scope 文件 | **PASS** |
| Bounded lifecycle proof（HTTP 200, items/providers, infographic unsupported） | **PASS** |
| Scoped tests 全绿（10/10） | **PASS** |
| Combined gate 唯一保留 failure 为 activation gate（EVIDENCE_MISSING） | **PASS** |
| toolchain_probe 注入 fail-closed、不读 activation/P6、不置 public support | **PASS** |
| 无 scope drift、无 V1/V2/V3/activation/render 改动 | **PASS** |

**最终判定：PASS**

此 PASS 仅授权 PM 派发 V1（controlled local real Remotion invocation），不自动开放 create-options 或 public submission。
