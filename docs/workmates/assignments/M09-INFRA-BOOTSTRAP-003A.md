# M09-INFRA-BOOTSTRAP-003A — P3a Bootstrap Readiness

`worker_runtime_p3a`，仅实现 P3a，依据独立 PASS 的 P1 与 PLAN-003。

回执：`docs/workmates/receipts/M09-INFRA-BOOTSTRAP-003A.md`。

范围：`csboard/application/capabilities.py`、`csboard/runtime/toolchain.py`（必要时）、service probe read model 与直接 capability tests。不得改 renderer/domain/commands/task create/API submission/legacy/webapp/前端。

要求：实现只读 fail-closed bootstrap/toolchain 诊断，检查 Node、render script、lockfile、Remotion/browser、FFmpeg/ffprobe、service secret presence/probe、external-stage gate；输出 bootstrap_ready、逐项安全诊断和稳定多缺项优先 reason codes。无 P6 evidence 时公开 projection 必为 supported/available=false 与 REAL_SMOKE_EVIDENCE_REQUIRED；绝不能执行 render、创建任务、读取 activation evidence或仅因 node_modules/mock 宣称可用。覆盖单/多缺项、bootstrap ready但unsupported、白板回归和 CLI/API capability read-model 一致。运行 focused + affected suite；出口 READY_FOR_INDEPENDENT_P3A_VERIFICATION。
