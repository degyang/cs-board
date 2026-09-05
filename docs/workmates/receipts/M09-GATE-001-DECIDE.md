# M09-GATE-001 — PM Decision

**Date**: 2026-09-05
**Decision**: **approve minimal fix**

---

## Precise intended behavior

Prevent the module-level/default `~/.csboard` startup from populating the process-global seed template cache. The one-line guard is:

> In `webapp/mountain_server.py:create_app`, call `_cache_seed_template(effective_data_dir)` **only when `data_dir is not None`** (i.e., the caller passed an explicit directory).

When `data_dir` is `None` (the production default path via `~/.csboard`), the seed functions still run normally — they populate the data directory on disk. They simply do **not** snapshot that directory into the process-global `_SEED_TEMPLATE_DIR` cache.

When `data_dir` is explicitly provided (e.g., `create_app(tmp_path)` in tests, or a production caller that passes a custom directory), caching proceeds as before — the explicit directory becomes the seed template for subsequent fresh directories.

This ensures the stale `~/.csboard/settings/services/mock-llm.json` never contaminates test or explicit-directory calls.

## Accepted file scope

| File | Change |
|------|--------|
| `webapp/mountain_server.py` | One-line guard: wrap `_cache_seed_template(effective_data_dir)` at line 147 in `if data_dir is not None:`. |

No other source files are changed. The user's `~/.csboard` is not touched. `web-v2/` is not touched.

## Verification criteria for tester

1. **Bootstrap tests pass**: `pytest tests/test_mountain_bootstrap.py -v` — both tests exit 0 without any manual `_SEED_TEMPLATE_DIR = None` reset or `~/.csboard` cleanup.
2. **Stage endpoint tests unaffected**: `pytest tests/test_mountain_api.py -v` — all 13 tests still pass.
3. **No `mock-llm` leakage**: The `/api/v1/services` endpoint returns exactly 6 services (no `mock-llm`) when called via `create_app(tmp_path)`, regardless of what exists in `~/.csboard`.
4. **Module-level app still works**: `python -c "from webapp.mountain_server import app; print(app is not None)"` prints `True`.

## Next owner

`tester_backend` — proceed to `M09-GATE-001-V` verification assignment.
