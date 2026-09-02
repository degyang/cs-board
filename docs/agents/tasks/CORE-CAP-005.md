# CORE-CAP-005：修复 capabilities 的集成基线缺口

- Owner: CORE
- Status: REVIEW_READY
- Priority: P0
- Depends on: `CORE-CAP-004=APPROVED`
- Worktree: `/mnt/d/workstation/projects/cs-board-core-cap-repair`
- Branch: `fix/mountain-capability-secret-contract`
- Base commit: `0b99b50`

## Goal

修复 WEB 真实 intake 门禁发现的 `GET /api/v1/capabilities` 500。`CapabilityService` 当前调用
`FilesystemServiceRegistry.has_required_secrets`，但 WEB 集成基线没有这个公开方法；交付必须能直接进入
WEB 分支，而不是依赖 CORE 私有长分支中未随 capability delivery 交付的历史提交。

## Incident evidence

- WEB delivery/report: `0b99b50`、`docs/agents/reports/WEB-INTAKE-003.md`；
- observed response: `500 GET /api/v1/capabilities`；
- traceback: `csboard/application/capabilities.py:102` 调用不存在的
  `FilesystemServiceRegistry.has_required_secrets`；
- `CORE-CAP-004` 的测试只在包含额外历史实现的 CORE 分支通过，未证明 delivery 对固定消费基线闭合。

## Allowed surfaces

- `csboard/adapters/filesystem/service_registry.py`；
- `csboard/application/capabilities.py`（仅在公开契约需要最小调整时）；
- `tests/test_capabilities_api.py` 及聚焦 repository secret availability 的测试；
- `docs/agents/reports/CORE-CAP-005.md`。

## Forbidden surfaces

- `web-v2`、页面、API DTO、Work Order、Stage 执行、媒体链路；
- 读取或回传 Secret 值；
- 用吞异常、固定 capability 响应或 mock 跳过真实 registry；
- 合并其他 backend 长分支历史以掩盖本任务的最小集成缺口。

## Acceptance

1. `FilesystemServiceRegistry` 提供公开 secret-availability 查询，required secrets 全部存在才返回 true；
2. required secrets 为空返回 true；缺失、空值或 secret store 读取失败返回 false，且不泄露 Secret；
3. 真实 `create_app(tmp_path)` 的 `GET /api/v1/capabilities` 返回 200，不再出现 AttributeError；
4. capability 输出继续脱敏，外部插画 gate 和完整六阶段依赖语义不回退；
5. 交付是以 `0b99b50` 为 base 的自包含提交，WEB 可直接消费，无额外隐藏 commit 依赖。

## Gates

```bash
pytest -q tests/test_capabilities_api.py
pytest -q tests/test_service_registry.py tests/test_service_resolver.py
python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from starlette.testclient import TestClient
from webapp.mountain_server import create_app
with TemporaryDirectory() as directory:
    response = TestClient(create_app(Path(directory))).get('/api/v1/capabilities')
    assert response.status_code == 200, response.text
PY
git diff --check 0b99b50...HEAD
```

如实际测试文件名不同，可用 `rg --files tests` 找到同领域文件替换，但不得减少上述行为矩阵。

## Stop condition

提交并推送当前分支；报告记录 commit、逐门禁退出码和脱敏证明。将任务置为 `REVIEW_READY` 并唤醒
CEO。不得自行批准，不得改 WEB 状态或领取下一任务。
