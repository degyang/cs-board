# M09-INFRA-BOOTSTRAP-003A-FIX — P3a 完整 fail-closed 诊断

**CANCELLED / SUPERSEDED — 不得执行。**

此前 `worker_runtime_p3a`，仅修复 `M09-INFRA-BOOTSTRAP-003A-V` 指出的 P3a 阻塞。

取消原因：可见 tmux PLAN-004 已独立确认 renderer/toolchain readiness 唯一归 P2；本票错误地把该职责塞回 P3a。唯一 P3a 写者为可见 tmux 3.2；本票及内部代理不得继续修改任何实现、测试或回执。

回执：`docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A-FIX.md`。

范围：`csboard/application/capabilities.py`、必要的只读 `csboard/runtime/toolchain.py` helper、直接 capability/toolchain/API/CLI tests。不得改 adapters/domain/commands/task create、P2、前端、legacy、submission 或 real-render 配置。

必须实现并测试：

- `_bootstrap_snapshot`/其等价 projection 消费并安全报告 Node、render.mjs、lockfile、锁定 Remotion 依赖、实际 Remotion browser、FFmpeg、ffprobe、service secret/probe、external-stage gate 的每项诊断；无工具路径/secret 泄露。
- 完整稳定 reason-code 优先级和多缺项唯一首因（含 NODE_NOT_FOUND、script/lockfile/remotion/browser/ffmpeg/ffprobe、service secret/probe、EXTERNAL_STAGE_BLOCKED）。
- external stage 成为实际 fail-closed gate，不能硬编码 ready；缺失/false/probe exception 必使 bootstrap_ready=false。
- bootstrap_ready=true 仍不 activation：无 P6 independent evidence 时 supported/available=false / REAL_SMOKE_EVIDENCE_REQUIRED。
- mock/read-only 测试覆盖每项、优先级、异常、external false、CLI/API一致与白板不回归。

禁止 render、真实任务、P6 evidence activation、用户/API/WebUI submission、提交推送。出口 READY_FOR_INDEPENDENT_P3A_VERIFICATION。
