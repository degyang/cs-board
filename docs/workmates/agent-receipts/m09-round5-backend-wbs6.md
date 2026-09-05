---
round: m09-round5
agent: backend
wbs: 6
status: done
---

## WBS-6 Receipt: `capabilities` CLI Command

### What was done

Added the `capabilities` subcommand to the CLI so users can query engine availability:

```
python -m cli.csboard capabilities
```

### Files modified

- `cli/csboard.py` — added `capabilities` resource parser (line 218) and handler (line 286)

### Files created

- `tests/test_cli_capabilities.py` — 3 tests

### Verification

- `tests/test_cli_capabilities.py` — 3/3 passed
- Regression suite (99 tests) — all passed, no regressions

### Notes

- The command delegates to `CapabilityService.snapshot()` using the same pattern as `create_options()` in commands.py
- No `action` subparser needed; handler placed before `(args.resource, args.action)` checks
- No webapp imports used
