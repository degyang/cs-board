# M09-G0 baseline handoff — source snapshot and merge audit

状态：`HANDOFF_COMPLETE_NEW_SESSION_REQUIRED`

## Authority and source snapshot

- Main integration HEAD: `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`.
- Backend worktree HEAD before handoff: the same commit.
- The commit tracks `webapp/mountain_*`; it does not contain main's uncommitted `backend/` migration.
- Source snapshot: `/tmp/m09-g0-baseline-e34ba6e.tar`.
- Deterministic snapshot SHA-256: `9cd0e7a97bca4218f1a26e2c8fb7120c89cbaaf336dc6228941f45da3fac1859`.

The snapshot contains the source-only `backend/` tree (13 files; no `__pycache__` or `.pyc`) plus the three G0-relevant tests: `tests/test_capabilities_api.py`, `tests/test_cli_capabilities.py`, and `tests/test_infographic_capability.py`. It contains no secrets or real materials.

The current G0 assignment was also added only at the previously absent backend-worktree path. Main/worktree assignment SHA-256 is `9c980fe8be59a4a7958c4d81c9537088e7c49b1bd31859d743545b27f7f16158`.

## Copy / merge boundary

1. `backend/` was absent in the backend worktree, so the 13 source files were **added only**; no existing worktree file was overwritten.
2. The three existing test files were not copied wholesale. Each was three-way merged using common ancestor `e34ba6e`, worker version, and main integration target. All three merge previews exited `0` with no conflict markers.
3. The merged files retain both sides' non-conflicting changes and now exactly hash to the main target:

| Path | SHA-256 |
| --- | --- |
| `backend/mountain_server.py` | `fcb7127244da598e7a110dde1aed970b323a75538fc81e5639a750d4ea51d6dc` |
| `backend/mountain_capability_api.py` | `2fb9e4b34668d7dadd728486bc4e07952fcf39af084cf5f334496948e115a46d` |
| `tests/test_capabilities_api.py` | `e1db9278a5ac0f57b4e47d0dfecc0bf13422dd53fbd1ad169d9994048c2a90f3` |
| `tests/test_cli_capabilities.py` | `100f91754568f91e4c1750e9aa8cbe472e3a132e796910681c8c43d58504f216` |
| `tests/test_infographic_capability.py` | `b9981ba4e119b031440777d77701ee2ed9867df0d16aad7af24f488c5469d6f9` |

All other worker differences were left untouched. No service, render, ffprobe, task creation, test execution, commit, or push occurred during this handoff.

## Re-dispatch condition

The prior `%59` client is retired for G0 because it inherited P2 context. A new formal backend session must be launched only after preflight verifies the assignment is reachable in its worktree and these target hashes match this handoff. This receipt does not make G0 passed or authorize V1/V2/V3/activation.
