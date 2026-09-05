# M09-INFRA-BOOTSTRAP-003A — P3a Bootstrap Readiness Receipt

状态：READY_FOR_VERIFY
范围：仅非-renderer bootstrap readiness 的只读 projection 与其测试；未提交、未推送。

## 本次矩阵 rework

- P3a bootstrap 仅检查五项非-renderer service capability：`text_generation`、`speech_synthesis`、`speech_alignment`、`image_generation`、`media`，以及可注入、只读的 external-stage gate。`rendering` 不在 bootstrap matrix 内。
- external gate 默认缺失即关闭；`false` 和 callable 异常同样以稳定的 `EXTERNAL_STAGE_BLOCKED` fail-closed。没有环境变量或硬编码 ready fallback。
- `has_required_secrets` 与 `get_cached_probe` 的异常都会归约为稳定安全失败；公开 diagnostics 只有 `component`、`ready`、`reason_code`，不泄露路径、异常正文或 secret。
- 多缺项仍输出完整、有序 diagnostics，第一失败项唯一决定 `bootstrap_reason_code`。`bootstrap_checked_at` 为可解析的 UTC ISO-8601 时间。
- bootstrap 就绪时，`infographic-remotion` 仍固定 `supported=false`，reason 为 `REAL_SMOKE_EVIDENCE_REQUIRED`；P3a 未读取 evidence，未创建任务或渲染。
- 白板 projection 回归断言保留。API 与 CLI 各自以独立测试验证它们调用同一 `CapabilityService` read model。

## 测试与核对

- `tests/test_infographic_capability.py` 从原先 4 个测试增长到 **24** 个：external gate missing/false/exception、secret/probe exception、五项非-renderer capability 的 missing/secret/probe 参数化矩阵、多缺项有序完整 diagnostics、UTC 时间、安全诊断、ready-but-unsupported 与 whiteboard。
- `pytest -q tests/test_infographic_capability.py tests/test_capabilities_api.py tests/test_cli_capabilities.py`：**34 passed**，exit 0（1 个既有 Starlette deprecation warning）。
- `git diff --check`：exit 0。
- 已静态确认 `capabilities.py` 不含 `_detect_remotion_readiness`、`_bootstrap_toolchain_checks`、`_browser_present`、`_lockfile_has_pinned_remotion`，也没有 Node、render script、lockfile、browser、FFmpeg 或 ffprobe bootstrap 检查。
- 最终文件确认：`tests/test_infographic_capability.py` 存在且为 regular file。
