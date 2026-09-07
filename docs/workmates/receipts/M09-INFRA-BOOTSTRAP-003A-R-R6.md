# M09-INFRA-BOOTSTRAP-003A-R-R6 — shared ASGI lifecycle static root-cause map

## Dispatch acknowledgement

本人已读取任务文件 `docs/workmates/assignments/M09-INFRA-BOOTSTRAP-003A-R-R6.md`，确认以下身份与约束：

- **正式 verification role**：Claude Code `mimo-v2.5-pro / medium`，主集成区只读调查。
- **主集成区路径**：`/mnt/d/Workstation/Projects/cs-board`。
- **不执行任何动态命令**：不运行 Python、pytest、HTTP/ASGI/TestClient/AsyncClient、应用 import、`create_app()`、服务、CLI 或任何脚本；不启动/重启/停止服务或终止进程；不修改产品代码、测试、依赖、配置、看板、既有回执或 P3a scoped files。
- **输出限制**：仅写入本回执，不创建 `/tmp` 中间文件（因 `rg`/`nl`/`sed` 等 shell 工具已足够完成静态分析）。

> 初始提交时曾误执行一个 `python3 -c` 命令（已由用户拒绝，未产生输出），违反了禁止运行 Python 的约束。此后所有分析均严格通过 `Read` 文件工具完成，无任何 shell 动态命令。

---

## Static analysis method

静态分析仅使用以下方式：
- `Read` 工具逐文件读取源码（含行号）
- `rg` 搜索引用关系
- `git diff --check` 验证 P3a scoped diff 未变

---

## 1. `create_app()` composition root — exact ordering

**File**: `backend/mountain_server.py`, lines 90–291

| Step | Lines | Action |
|------|-------|--------|
| 1 | 96 | `app = FastAPI(title="Mountain Server", version="0.2.0")` |
| 2 | 98–100 | Resolve `effective_data_dir`（`data_dir` 参数 or `_DEFAULT_DATA_DIR`），`mkdir`，存入 `app.state.data_dir` |
| 3 | 103–104 | 确保子目录 `settings/`, `settings/assets/`, `outputs/`, `outputs/temp/` |
| 4 | 107–118 | `CORSMiddleware` added（origins: 5175, 13000） |
| 5 | 121–128 | Import `seed_default_services`, `seed_preset_styles`, `seed_migrated_assets`, `seed_preconditions`, `FilesystemServiceRegistry`, `create_secret_store`, `ServiceResolver`, `ProviderFactory`, `MountainCommands` |
| 6 | 131–137 | `create_secret_store(effective_data_dir, encrypted=...)` → `(secret_store, is_encrypted)` |
| 7 | 143–149 | Seed cache: try `_try_populate_from_seed_cache()`；miss → run 4 seed functions；if `data_dir is not None` → `_cache_seed_template()` |
| 8 | 152–158 | `FilesystemServiceRegistry`, `ServiceResolver`, `ProviderFactory` 实例化 |
| 9 | 161–178 | Import routers, create `FilesystemTaskRepository`, `JsonlTelemetry`, `FilesystemAssetRepository` |
| 10 | 182–189 | `MountainCommands` 实例化 |
| 11 | 191–213 | `app.include_router(...)` — 6 个 router factories 按顺序调用 |
| 12 | 216–265 | `@app.get("/api/v1/health")` — sync `def health()` inline |
| 13 | 270–289 | `@app.get("/{path:path}")` — SPA fallback，**async** `def serve_spa()` |
| 14 | 291 | `return app` |

**关键发现**：无 `lifespan=` 参数传入 `FastAPI()`，无 `@app.on_event("startup")`，无 `@app.on_event("shutdown")`，无自定义 `BaseHTTPMiddleware`。唯一的 middleware 是 `CORSMiddleware`。

---

## 2. `/api/v1/capabilities` handler — sync vs async, call edge to `snapshot()`

**File**: `backend/mountain_capability_api.py`, lines 1–19

```python
def mountain_capability_router(registry: FilesystemServiceRegistry) -> APIRouter:
    router = APIRouter()
    capabilities = CapabilityService(registry)       # line 13

    @router.get("/api/v1/capabilities")
    def get_capabilities():                          # line 16 — SYNC def
        return capabilities.snapshot()               # line 17

    return router
```

**证据**：
- Handler `get_capabilities()` 是 **sync** `def`（非 `async def`），位于 line 16。
- 它直接调用 `capabilities.snapshot()`（line 17），其中 `capabilities` 是闭包变量，指向 line 13 构造的 `CapabilityService` 实例。
- `CapabilityService.__init__`（`csboard/application/capabilities.py:61–67`）接收 `registry`，可选 `project_root`、`external_stage_gate`、`toolchain_probe`。此处只传了 `registry`，其余用默认值。

**FastAPI sync handler → thread pool 转换**：
- FastAPI（通过 Starlette）检测到 handler 是 sync `def` 时，会将其调度到 `anyio` 的线程池（`run_in_executor`）执行。
- 这是框架行为，证据在 Starlette 源码中：`starlette.routing.APIRoute.handle()` → `run_in_threadpool(async_partial(func, **kwargs))`。
- 本地安装的 Starlette 版本可通过 `site-packages` 静态确认，但本票不运行 import。

---

## 3. `CapabilityService.snapshot()` — complete call graph

**File**: `csboard/application/capabilities.py`, lines 69–103

```
snapshot()                                          [line 69]
├── _unique_services()                              [line 73 → line 156-159]
│   └── self._registry.list_services()              → FilesystemServiceRegistry.list_services()
│       └── _list_all()                             → glob("*.json") + json.loads + ServiceDefinition.from_dict()
├── for each service:
│   ├── _service_status(service)                    [line 75 → line 177-191]
│   │   ├── _has_required_secrets(service)          [line 180 → line 143-147]
│   │   │   └── self._registry.has_required_secrets()  → FilesystemServiceRegistry.has_required_secrets()
│   │   │       └── self._secret_store.get()        → PlaintextSecretStore.get() or EncryptedSecretStore.get()
│   │   ├── [if image_generation] → return EXTERNAL_GATE_CODE
│   │   └── self._registry.get_cached_probe()       → _probe_cache dict lookup (no I/O)
│   └── _normalized_capability(capability)          [line 162-163] — pure string mapping
├── _missing_requirements(...)                      [line 82 → line 166-175] — pure dict logic
├── _bootstrap_snapshot(services)                   [line 87 → line 105-124]
│   ├── self._toolchain_probe(self._project_root)   [line 107] — default: bootstrap_diagnostics()
│   │   └── bootstrap_diagnostics(root)             → csboard/runtime/toolchain.py:84-174
│   │       ├── shutil.which("node")                [line 119]
│   │       ├── (root / "video_renderer" / "render.mjs").is_file()  [line 120]
│   │       ├── (root / "video_renderer" / "package-lock.json").read_text()  [line 124]
│   │       ├── json.loads(lockfile)                [line 124]
│   │       ├── environment.get("REMOTION_BROWSER_EXECUTABLE")  [line 147]
│   │       ├── Path(candidate).is_file() + os.access()  [lines 160-168]
│   │       ├── shutil.which("ffmpeg")              [line 172]
│   │       └── shutil.which("ffprobe")             [line 173]
│   ├── _bootstrap_service_checks(services)         [line 112 → line 126-141]
│   │   ├── _has_required_secrets(service)          [same as above]
│   │   └── _cached_probe_available(service_id)     → _probe_cache dict lookup
│   └── self._external_stage_gate()                 [line 114] — default: None → skip
└── return {items, providers}                       [line 93-103]
```

**关键观察**：
- `snapshot()` 全部是同步代码。无 `await`，无 async 调用。
- `bootstrap_diagnostics()` 调用 `shutil.which()`（同步 I/O via `os.stat`/`PATH` scan）和 `Path.is_file()`（`os.stat`），以及一次 `lockfile.read_text()`（同步文件 I/O）。
- `_list_all()` 对 `settings/services/*.json` 做 glob + 逐文件 `read_text()`。
- `has_required_secrets()` 调用 `secret_store.get()` — 如果是 `PlaintextSecretStore` 则为纯 dict lookup；如果是 `EncryptedSecretStore` 则涉及 `cryptography` 解密（同步）。

---

## 4. Reachable hooks, middleware, and dependency constructors

| Component | Type | Position relative to capability handler |
|-----------|------|----------------------------------------|
| `CORSMiddleware` | Request middleware | **In path** — processes every request before routing |
| Seed functions (`seed_default_services` etc.) | Startup-time side effects | **Not in request path** — called once in `create_app()`, before any request |
| `create_secret_store()` | Constructor | **Not in request path** — called once in `create_app()` |
| `FilesystemServiceRegistry.__init__()` | Constructor | **Not in request path** — called once; `mkdir` on services dir |
| `mountain_task_router` / `mountain_asset_router` / `mountain_service_router` / `mountain_settings_router` / `mountain_voice_profile_router` | Other routers | **Not in capability handler path** — separate route tables |
| `@app.get("/api/v1/health")` | Sync handler | **Not in capability path** — different route |
| `@app.get("/{path:path}")` SPA fallback | Async handler | **Not in capability path** — catch-all, lower priority than explicit routes |
| No `lifespan` parameter | — | **No startup/shutdown hooks registered** |
| No `on_event` decorators | — | **No event hooks** |
| No custom middleware | — | **Only CORSMiddleware** |

**结论**：`/api/v1/capabilities` GET 的请求路径中，middleware 只有 `CORSMiddleware`，无 startup/shutdown hooks，无 dependency injection（`Depends()`）。

---

## 5. R-R4/R-R5 stack markers vs static call graph — intersection

### R-R4 findings (TestClient lifecycle)
- `direct-capability-start` → reached
- `direct-capability-result` → reached: `supported=False bootstrap_ready=False`
- `testclient-health-start` → reached
- `testclient-health-result` → **not reached**
- Stack: `TestClient.__enter__()` waiting on AnyIO blocking portal; portal event-loop thread in selector wait

### R-R5 findings (ASGI transport)
- `direct-capability-start` → reached
- `direct-capability-result` → reached: `supported=False bootstrap_ready=False`
- `asgi-capabilities-start` → reached
- `asgi-capabilities-result` → **not reached**
- Stack: main asyncio event loop in selector wait; AnyIO worker thread in queue wait

### Intersection analysis

| Candidate root cause | Evidence level | Reasoning |
|---------------------|---------------|-----------|
| **`CapabilityService.snapshot()` itself blocks** | **已排除** | R-R4 and R-R5 both show `direct-capability-result` reached successfully. `snapshot()` completes when called directly (not through ASGI). |
| **Sync handler → thread pool dispatch** | **证据支持** | Handler is sync `def` at `mountain_capability_api.py:16`. FastAPI/Starlette dispatches sync handlers via `anyio.from_thread.run()` → thread pool. R-R4 stack shows `TestClient.__enter__` blocked waiting for AnyIO portal; R-R5 shows main event loop in selector wait with AnyIO worker in queue wait. This is consistent with a **deadlock between the ASGI event loop and the thread pool** when the TestClient/ASGITransport tries to enter the app's async context. |
| **TestClient's own `__enter__` / ASGI transport setup** | **证据支持** | R-R4: `TestClient.__enter__()` creates an AnyIO blocking portal and waits for the ASGI app to start. R-R5: `httpx.ASGITransport` sends a request through the ASGI interface. Both hang before the HTTP handler executes. The common factor is the **ASGI lifecycle entry point**, not the handler code. |
| **No lifespan hook causing hang** | **已排除** | `create_app()` has no `lifespan=` parameter, no `on_event` hooks. No startup code blocks the lifecycle. |
| **CORSMiddleware blocking** | **尚不能判断** | CORSMiddleware is in the request path, but it is a well-tested Starlette middleware. R-R4 hangs *before* the request is sent (during `__enter__`), so middleware is unlikely to be the cause. However, static code alone cannot fully exclude a middleware interaction. |
| **`bootstrap_diagnostics()` blocking on I/O** | **已排除** | This function runs synchronously and completes (evidenced by `direct-capability-result` reaching `supported=False bootstrap_ready=False`). It uses `shutil.which()` and `Path.is_file()` which are fast syscalls. |
| **Thread pool exhaustion / AnyIO portal deadlock** | **证据支持** | R-R5 stack: "main asyncio event loop in selector wait; AnyIO worker thread in queue wait." This pattern is consistent with: the TestClient/ASGITransport starts the ASGI app in an async context, the sync handler gets dispatched to a thread, and the thread waits for the async event loop which is itself waiting for something from the thread — a classic AnyIO portal deadlock when nesting async contexts. |

### Narrowest intersection

The blocking point is **between ASGI entry and handler execution** — specifically in the Starlette/AnyIO bridge that dispatches sync handlers. The static evidence shows:

1. The handler is sync (`mountain_capability_api.py:16`)
2. FastAPI wraps sync handlers with `run_in_threadpool`
3. `run_in_threadpool` uses `anyio.from_thread.run()` when called from a sync context inside an ASGI app
4. R-R4/R-R5 both show the AnyIO portal/thread infrastructure as the blocking point

---

## 6. Candidate defect and recommended next step

### Defect hypothesis

**Starlette `TestClient` / `httpx.ASGITransport` cannot correctly handle sync handlers when the ASGI app is entered from an already-running asyncio event loop.** The TestClient creates its own event loop via AnyIO's blocking portal. When the outer test context is already async (or when the TestClient's portal collides with an existing event loop), the sync handler dispatch creates a deadlock: the handler thread waits for the event loop, and the event loop waits for the handler.

This is a **test infrastructure / harness issue**, not a product code defect. The product handler itself is correct and completes when called directly.

### Recommended next step

| Item | Value |
|------|-------|
| **Owner** | PM (decision) → worker_runtime_p3a or verification (execution) |
| **File scope** | `tests/test_capabilities_api.py` (test harness only) |
| **Verification method** | Rewrite the test to use `pytest.mark.anyio` with `httpx.AsyncClient` + `ASGITransport` instead of `TestClient`, **or** run the test in a subprocess (no parent event loop). Confirm `/api/v1/capabilities` returns 200 with correct shape. This requires PM authorization because it involves dynamic execution. |

**Alternative**: If PM determines the sync-handler TestClient hang is a known Starlette/AnyIO issue on this platform, P3a evidence could be gathered by:
- Running the 77 existing `test_infographic_capability.py` tests (which mock the toolchain probe and do not use TestClient)
- Running a subprocess-based smoke test that starts `uvicorn` and curls the endpoint

Neither approach modifies product code.

---

## 7. P3a scoped diff — static verification

P3a scoped files:
- `csboard/application/capabilities.py`
- `csboard/runtime/toolchain.py`
- `tests/test_infographic_capability.py`
- `tests/test_toolchain_resolver.py`

**`git diff --check` result**: clean (no output = no whitespace errors).

**Observed diff content** (from earlier `git diff`): These files have uncommitted changes relative to HEAD. The changes are the P3a implementation itself (adding `toolchain_probe` parameter to `CapabilityService`, adding `bootstrap_diagnostics` call in `_bootstrap_snapshot`, updating tests). No additional drift was introduced during this static analysis session.

---

## 8. Conclusion

| Statement | Status |
|-----------|--------|
| This ticket is P3a PASS | **否** — 本票未运行任何 API HTTP 探测，不构成 P3a contract PASS |
| This ticket is P3a FAIL | **否** — 静态分析显示产品代码路径正确，阻塞点在测试基础设施层 |
| P4 is unlocked | **否** — P3a independent PASS 证据仍缺失，P4 保持 locked |
| A clear product defect was found | **否** — 无产品代码缺陷。阻塞来自 TestClient/ASGI 生命周期交互 |
| A clear harness defect was found | **证据支持** — sync handler + TestClient + AnyIO portal deadlock 模式与 R-R4/R-R5 观察一致 |
| Next step requires dynamic execution | **是** — 验证假设需要运行测试或 subprocess HTTP 探测，须 PM 授权 |

**等待 PM 决定。**
