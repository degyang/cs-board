# M09-ACTIVATE-001 — backend correction receipt

Verdict: **READY_FOR_VERIFY**

## Review corrections

- Restored the public `REAL_SMOKE_EVIDENCE_REQUIRED` value. A missing V3 activation pointer is independently projected as `EVIDENCE_MISSING`; the historical constant is not repurposed to hide that new meaning.
- Restored the CLI architecture guard against `webapp.*` imports.
- Kept the V3 activation tests fail-closed and restored their equivalent V3 coverage for receipt binding, index structure, and every toolchain binding.
- Factored command edges through one capability-service construction seam and added a real (unmocked) `CapabilityService` fixture. It verifies that the capability snapshot, `create_options()`, and task creation all open on the same valid V3 projection; after the accepted MP4 hash is invalidated, all three close and task creation returns `CAPABILITY_NOT_AVAILABLE`.
- `_probe_ok()` now preserves complete `ffprobe -print_format json` stdout. Its regression invokes the installed `ffprobe` against the accepted fixture MP4, whose JSON is multi-line.
- Browser availability/version now use the accepted `video_renderer/browser-resolver.mjs` both in bootstrap and activation. The regression unsets all three configured-browser environment variables and proves the cached-browser resolver path still supplies a version. The pointer now binds the accepted resolver SHA-256.
- The service fingerprint is an opaque digest of stable identity, revision, adapter, endpoint/model, safe configuration, credential availability, and cached probe state. A replacement service with identical readiness now changes that digest and closes activation.
- Activation fixtures are fully self-contained: they construct only pytest-temporary Task/Run/index/manifest/probe documents and generate a short local H.264 with `ffmpeg`. They do not read, copy, or require repository `outputs/` content, and do not invoke Remotion.

The fixture is isolated under pytest's temporary directory. It creates only the permitted temporary task; it does not render or modify canonical outputs.

## Final SHA-256

- `csboard/application/activation.py` — `34bffe0713c1d8f87202ba0cfe73954b7ffe525b5c9a63034fb17f396c5b6995`
- `csboard/application/capabilities.py` — `55a4bd78a92ef0cb7aaa10308f388e0adb80d24fb5607276954a0830f552f6d4`
- `csboard/application/commands.py` — `75bbec8255dd756556b714ae5fe90153f2bd602ecb59e9c50876c3269454e833`
- `csboard/runtime/toolchain.py` — `d6e4bb632178c11ede4d09e6d7ec6327ee8e3b0dae8b1d676a3778e2c80218fb`
- `cli/csboard.py` — `79558633626a1361957f2bd688b73b141156c35c995cfd3f133780a22adb869a`
- `webapp/mountain_capability_api.py` — `e16608ab68b5509b3dc87b5125672b377df300bfa6ab84467bb60caa08c19261`
- `webapp/mountain_server.py` — `972e764aab5ebc2761c3c23c3dd75b9f7f732b2d9180b3d02ed7cb7b96ae0eb2`
- `tests/infographic_activation_fixture.py` — `ddfed65dbc9e7969f2f845ef1b88dca1de55fa62948bd0da9281dc30a0196f09`
- `tests/test_infographic_activation.py` — `53c364cba882ede391d0bfe200ec2194a3a3d4e5fb7d2aef434afa1e47961ad2`
- `tests/test_infographic_activation_projection.py` — `b01399d4f322e3a390afac69f04ac803fbb2b70af3aefba9dceb0714e77b898b`
- `tests/test_infographic_capability.py` — `3cc87c8f2b4d6087acbcb5a59867faebb868319f41c6fec0fa0448b4913dae10`
- `tests/test_cli_capabilities.py` — `7f4bb7d9a898ef504439366efa081ab47d2081838a81f4d624ffd504ae8b52c6`
- `tests/test_toolchain_resolver.py` — `b86499e34c19e842d2c2f9db8d53854dce76738077e2a95f99e23e39758f8bb6`
- `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json` — `54c927873e35575b574f56fcfa1fd55dbed9ef0f68e3381893c223977b50b68f`

## Checks

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_infographic_activation.py tests/test_infographic_activation_projection.py tests/test_infographic_capability.py tests/test_infographic_task_creation.py tests/test_capabilities_api.py tests/test_cli_capabilities.py tests/test_infographic_routing_p4.py tests/test_toolchain_resolver.py` | exit 0; 88 passed (includes self-contained H.264 fixture, real multi-line ffprobe, resolver-without-env, and same-ready service replacement) |
| `CSBOARD_DATA_DIR=<fresh isolated dir> .venv/bin/python scripts/run_backend_test_gate.py --workers 1` | exit 0; 945 passed, 5 warnings, 3 subtests; 123.24 s |
| scoped `git diff --check -- <M09 activation/capability/composition/direct-test paths>` | exit 0 |
| final `sha256sum` for the files above | exit 0 |

No 8000/5182 service was started. No renderer ran, and no canonical task/run was created. The independent verification, integrated API/WebUI behavior, and final visual/video acceptance remain outside this worker task.

The hardened service digest deliberately does not reinterpret the old
readiness-only pointer value as an identity/configuration binding. Therefore
the public projection remains fail-closed until PM/verification issues a fresh
operator pointer from the accepted V3 evidence and current safe service
fingerprint; this correction does not silently activate a replacement service.
