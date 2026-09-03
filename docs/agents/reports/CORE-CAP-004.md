# CORE-CAP-004 交付报告

状态：`REVIEW_READY`

基线：`1c5e9ce`。

## 交付

- 新增原生 `GET /api/v1/capabilities`，由 `mountain_server.create_app()` 注入同一动态
  `FilesystemServiceRegistry`；未重新挂载旧 router。
- `CapabilityService` 仅读取 service 定义、凭据配置状态与已有 probe 缓存；GET 不执行
  probe、网络请求或付费操作。
- `providers.providers` 使用动态 `service_id`；DTO 不返回 Secret、服务地址或本地路径。
- `all_available` 聚合六阶段白板流程的真实状态。`generate-illustrations` 仍受未实现的
  外部 candidate Gate 约束，因此不会将 image service 误报为该流程可执行。
- 新增 `tests/test_capabilities_api.py`，覆盖稳定 shape、未 probe、缓存可用/失败、外部
  illustration Gate 和脱敏响应。

## 验证

所有命令均在此工作树执行，退出码为 0：

```text
python -m pytest -q tests/test_mountain_server.py tests/test_mountain_service_api.py tests/test_capabilities_api.py
41 passed in 6.74s

python -m pytest -q tests/test_asset_repository.py tests/test_av_timing.py tests/test_backend_runtime_17.py
25 passed in 26.90s

python -m pytest -q tests/test_cli_csboard.py tests/test_composition.py tests/test_composition_service.py tests/test_csboard_foundation.py tests/test_dynamic_provider_factory.py tests/test_fake_adapters.py tests/test_ffmpeg_media_adapter.py tests/test_illustrations.py tests/test_indextts_adapter.py
72 passed, 3 subtests passed in 7.56s

python -m pytest -q tests/test_input_transaction_11.py tests/test_legacy_bridge.py tests/test_legacy_isolation.py
29 passed in 8.02s

python -m pytest -q tests/test_m07_pr1c_acceptance.py
34 passed in 23.25s

python -m pytest -q tests/test_mountain_api.py tests/test_mountain_asset_api.py tests/test_mountain_bootstrap.py tests/test_mountain_contracts.py tests/test_mountain_server.py tests/test_mountain_service_api.py tests/test_mountain_settings_api.py tests/test_capabilities_api.py
99 passed, 4 skipped in 17.69s

python -m pytest -q [remaining non-overlapping test modules]
244 passed, 1 skipped in 18.46s

git diff --check
exit 0

rg -n 'PROVIDER_PROFILES|mountain_v1_router|api_key|authorization' webapp/mountain_capability_api.py tests/test_capabilities_api.py
exit 1 (no matches)
```

完整 `pytest -q` 在此执行环境的单次 30 秒命令窗口会被截断；以上是不重叠测试分组的完整
回归证据。两组含 `test_mountain_contracts.py` 的运行仅产生既有 jsonschema 弃用警告。

提交、推送和最终 `git diff --check 1c5e9ce...HEAD` 结果将在本报告的交付提交后由 PM 审核。

## Attempt 2：评审纠偏

评审发现 Attempt 1 从单值 Stage 映射推导必需能力，遗漏了 `clone-voice` 执行器实际解析的
`speech_alignment`。现已在 capability application 层声明完整的白板 Stage 依赖图：
`clone-voice` 同时要求 speech synthesis、speech alignment 与 media。聚合不再依赖单值
resolver map。

新增行为覆盖：空动态注册表、五项普通能力的自定义 service_id、alignment 缓存可用/失败，及所有
普通依赖可用时仍仅因 illustration external Gate 不可用。此时 preset item 的 reason 为
`EXTERNAL_STAGE_GATE_REQUIRED`；alignment 失败时则回到 `CAPABILITY_NOT_AVAILABLE`，证明其参与
标准流程聚合。

Attempt 2 命令均以退出码 0 完成：

```text
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_capabilities_api.py tests/test_service_resolver.py tests/test_m07_pr1c_acceptance.py
47 passed in 24.16s

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_mountain_server.py tests/test_mountain_service_api.py tests/test_capabilities_api.py
43 passed in 7.38s

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q [non-overlapping full regression groups]
25 passed; 72 passed, 3 subtests passed; 29 passed; 34 passed; 101 passed, 4 skipped; 244 passed, 1 skipped

git diff --check
exit 0

rg -n 'PROVIDER_PROFILES|mountain_v1_router|api_key|authorization' webapp/mountain_capability_api.py tests/test_capabilities_api.py
exit 1 (no matches)
```

完整回归仍按不重叠分组执行，以适配单命令 30 秒窗口；仅有既有 jsonschema 弃用警告。Attempt 2
提交、推送和相对基线 diff 检查见交付提交。
