# M09-GATE-002 — Implement approved seed-cache guard

## Inputs

- Decision receipt: `docs/workmates/receipts/M09-GATE-001-DECIDE.md`
- Work board: `docs/workmates/board.md`

## Task

Implement the one-line guard approved in the PM decision: in `webapp/mountain_server.py`, call `_cache_seed_template(effective_data_dir)` **only when `data_dir is not None`**.

At line 147 of `mountain_server.py`, change:

```python
        _cache_seed_template(effective_data_dir)
```

to:

```python
        if data_dir is not None:
            _cache_seed_template(effective_data_dir)
```

No other source files may be changed.

## Constraints

- Do not alter `web-v2/`.
- Do not delete the user's `~/.csboard` files.
- Do not commit.
- Do not use test-only cache resets — the guard is the production remedy.

## Verification (run before writing receipt)

1. `pytest tests/test_mountain_bootstrap.py -v` — both tests exit 0.
2. `pytest tests/test_mountain_api.py -v` — all stage endpoint tests still pass.

## Required output

Write `docs/workmates/receipts/M09-GATE-002.md` with:

1. tests run and results (paste output);
2. file changed (exact diff or description);
3. pass/fail against verification criteria;
4. next owner.

Then update only the matching row in `docs/workmates/board.md`.
