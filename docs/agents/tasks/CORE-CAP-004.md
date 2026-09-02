# CORE-CAP-004：Native Mountain capabilities API

- Owner: CORE
- Status: READY
- Priority: P0
- Depends on: none（仅等待 CORE 当前单任务容量）
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- Branch: `feat/mountain-assets-settings-backend`
- Base commit: dispatch 时固定为已批准 CORE-WO-003 delivery

## Goal

为唯一组合根 `webapp/mountain_server.py` 提供原生 `GET /api/v1/capabilities`，从动态
ServiceRegistry/ServiceResolver 与缓存 availability 生成现有 WebUI 可消费的脱敏 DTO，解除
`WEB-INTAKE-003` 的真实 404；不得重新挂载旧固定 Provider router。

## Authoritative evidence

- WEB blocker：分支 `feat/mountain-webui-surface-parity@e573dea` 的
  `docs/agents/reports/WEB-INTAKE-003.md`；
- Web DTO：`web-v2/src/lib/api/types.ts::CapabilitiesResponse`；
- 动态服务事实：`csboard/application/service_resolver.py`、
  `csboard/adapters/filesystem/service_registry.py`；
- 唯一组合根：`webapp/mountain_server.py`。

## Allowed surfaces

- 新增小型 native capability application/view service；
- `webapp/mountain_server.py` 或独立 `mountain_capability_api.py` 的注入式 router；
- 对应 API/ServiceRegistry 行为测试与 `docs/agents/reports/CORE-CAP-004.md`。

## Forbidden surfaces

- `mountain_v1_api.py`、`PROVIDER_PROFILES`、固定六 Provider 假设、Legacy、WebUI/DTO 修改；
- GET 时发起付费/网络 probe；只读缓存的 probe/config 状态；
- 为使按钮可用而伪造 `all_available=true`；Secret、endpoint、绝对路径进入响应；
- 顺手修改 Pipeline、Work Order、媒体或设置 CRUD。

## Acceptance

1. 空/默认 data dir、部分配置、全部配置、未 probe、probe failed/available 均返回 HTTP 200 与稳定
   `CapabilitiesResponse` shape；
2. `providers.providers` 以动态 service_id 或稳定 capability 投影表达，不依赖固定 provider 名；
3. `all_available` 由标准白板流程当前必需 capability 的真实可用性聚合；未实现 external illustration
   Gate 不得被伪装成图片服务可用；
4. `items` 保留 whiteboard/preset 及明确不支持的其他组合，reason_code 与聚合事实一致；
5. 响应不含 secret value、Authorization、endpoint、用户输入或文件路径；
6. `mountain_server.create_app(tmp_path)` 的真实 TestClient 契约覆盖，且 WEB blocker 的 GET 不再 404。

## Gates

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_mountain_server.py tests/test_mountain_service_api.py tests/test_capabilities_api.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check <dispatch-base>...HEAD
! rg -n 'PROVIDER_PROFILES|mountain_v1_router|api_key|authorization' webapp/mountain_capability_api.py tests/test_capabilities_api.py
```

## Stop condition

CORE-WO-003 尚未批准或 CORE 仍工作时不得领取。派发后只完成本端点、提交推送并唤醒 `/root/pm`；
不替 WEB 生成浏览器证据。
