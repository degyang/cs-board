# CORE-CAP-005 独立评审

Verdict: `APPROVED`

## 评审范围

- 契约基线：`0b99b503a4222b1e8674ca4163edbba4aca83a13`；
- 实现提交：`6699d20c9b95cb5962047a2150c81d1f602faf3e`；
- 交付提交：`7ac3cb003327110d58c7d48cf75131d207018d5f`；
- 评审差异：`git diff 0b99b50...7ac3cb0`；
- 交付分支 `fix/mountain-capability-secret-contract` 干净，且与同名远端分支无差异。

差异仅包含契约允许的
`csboard/adapters/filesystem/service_registry.py`、
`tests/test_service_registry.py` 和交付报告；未修改 `web-v2`、API DTO、Work Order、
Stage 执行或媒体链路。实现提交的直接父提交是 `0b99b50`，不存在额外隐藏提交依赖。

## 验收映射

1. `FilesystemServiceRegistry.has_required_secrets` 是公开查询；逐个读取
   `<service_id>_<required_secret>`，仅当全部结果均为非空白字符串时返回 `True`。
2. `all(...)` 对空 required 列表返回 `True`；缺失、空字符串、纯空白字符串和存储读取异常均
   返回 `False`。方法只返回布尔值，不记录也不回传 credential。
3. 真实 `TestClient(create_app(Path(directory)))` 请求
   `GET /api/v1/capabilities` 返回 200，已复现原 AttributeError 消失。
4. 既有 capabilities 契约测试继续证明固定脱敏 shape、外部 illustration gate 以及包含
   speech alignment 的六阶段依赖语义；额外哨兵检查证明配置值和读取异常文本均未进入快照。
5. `6699d20` 直接建立在固定消费基线 `0b99b50` 上，WEB 可直接消费该提交。

## 独立门禁

以下命令均在 `/mnt/d/workstation/projects/cs-board-core-cap-repair` 实际执行并正常退出：

```text
pytest -q tests/test_capabilities_api.py
5 passed, 1 warning in 1.15s
exit 0

pytest -q tests/test_service_registry.py tests/test_service_resolver.py
23 passed in 0.45s
exit 0

python - <<'PY'
# 契约中的 create_app(tmp_path) + GET /api/v1/capabilities 200 断言
PY
exit 0

git diff --check 0b99b50...HEAD
exit 0
```

另行运行只读 reviewer matrix，覆盖空 required（并断言未读取 store）、缺失值、纯空白值、
完整 required 值、store 抛出 `OSError`，以及 capability JSON 对唯一哨兵 secret 与异常文本的
脱敏；输出 `secret availability and redaction matrix: PASS`，exit 0。

## 结论

未发现阻塞性或非阻塞性实现问题。交付满足 `CORE-CAP-005` 的全部行为、边界、脱敏和
自包含基线要求。此处只记录 reviewer verdict；任务状态是否转为 `APPROVED` 及后续 WEB 恢复由
CEO 决定。
