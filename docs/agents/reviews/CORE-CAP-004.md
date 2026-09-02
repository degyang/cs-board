# CORE-CAP-004 独立评审

- Verdict: `APPROVED`
- Approved delivery: `c567c3a`
- Review base: `1c5e9ce`
- Reviewed attempt: 2

## 结论

原生 `GET /api/v1/capabilities` 已通过评审。实现挂载在唯一 Mountain composition root，使用动态
ServiceRegistry 的 `service_id` 与缓存 probe 结果生成稳定 DTO；GET 不发起 probe 或网络请求，响应
不暴露 Secret、endpoint 或绝对路径。

Attempt 1 遗漏的真实执行依赖已修正：白板阶段依赖图明确将 `clone-voice` 表达为
`speech_synthesis + speech_alignment + media`，不再从单值 stage map 推导。Whisper/对齐失败现会参与
必需能力判断；external illustration gate 仍保持诚实不可用，不伪造 `all_available=true`。

## 验收映射

- 空 registry：返回稳定空 providers 投影，流程不可用；
- 默认/未 probe：动态默认服务逐项返回 `NOT_PROBED` 或真实配置状态；
- 动态服务：自定义 service ID 覆盖文本、语音、对齐、渲染和媒体能力；
- 部分/失败：对齐 probe 失败返回 `PROBE_FAILED`，preset reason 为
  `CAPABILITY_NOT_AVAILABLE`；
- 普通依赖全部可用：仍只因 illustration external gate 返回
  `EXTERNAL_STAGE_GATE_REQUIRED`；
- 路由与安全：真实 `create_app(tmp_path)` 的 `/api/v1/capabilities` 为 200，forbidden pattern
  检查为零匹配。

## PM 独立复验

```text
pytest -q tests/test_capabilities_api.py tests/test_service_resolver.py tests/test_m07_pr1c_acceptance.py
47 passed

pytest -q tests/test_mountain_server.py tests/test_mountain_service_api.py tests/test_capabilities_api.py
43 passed

git diff --check 1c5e9ce...c567c3a
通过

rg forbidden gate
通过（零匹配）
```

本评审只批准该交付，不执行合并。
