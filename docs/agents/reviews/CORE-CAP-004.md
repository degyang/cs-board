# CORE-CAP-004 独立评审

- Verdict: `CHANGES_REQUESTED`
- Attempt: 1
- Delivery: `1cec1dc`
- Review base: `1c5e9ce`

## 结论

原生 `GET /api/v1/capabilities` 已消除 404，路由挂载、动态 `service_id`、只读缓存与响应脱敏方向正确；
定向回归也通过。但标准流程的必需能力聚合与真实执行器不一致，暂不能批准。

## 阻断问题

`csboard/application/capabilities.py` 只遍历 `CANONICAL_STAGES` 并通过单值
`STAGE_CAPABILITY_MAP` 聚合。该映射把 `clone-voice` 表达为 `speech_synthesis`，遗漏真实执行器
`csboard/application/commands.py::_exec_clone_voice` 强制解析的 `speech_alignment`；真实执行器还复用
`media`，但该能力可由 `compose-video` 的同一依赖覆盖。

因此 capability 投影不是执行器依赖的真实来源：Whisper/对齐服务失败时，接口虽然可能在单个 service
条目中显示失败，却不参与标准流程必需能力计算。这违反任务 Acceptance 3，也会让后续 Start 门禁与
六阶段真实执行条件漂移。

现有新增测试仅覆盖默认 seed、少量 probe 缓存及 illustration gate；尚未覆盖契约要求的空 registry、
动态自定义 service_id、部分能力，以及 `speech_alignment` 失败/可用对聚合依赖的影响。

## 已复验证据

```text
pytest -q tests/test_mountain_server.py tests/test_mountain_service_api.py tests/test_capabilities_api.py
41 passed

pytest -q tests/test_m07_pr1c_acceptance.py tests/test_service_resolver.py tests/test_dynamic_provider_factory.py
51 passed

git diff --check 1c5e9ce...1cec1dc
通过

forbidden rg gate
通过（零匹配）
```

## Attempt 2 有界纠偏

1. 在 capability application 层建立与真实阶段执行器一致的声明式必需能力图；`clone-voice` 必须同时
   包含 `speech_synthesis`、`speech_alignment` 与其实际复用的 `media`，不得继续从单值 stage map
   推断全部依赖。
2. 保留 external illustration gate 的诚实不可用语义，不为使 Start 可用而伪造图片能力或
   `all_available=true`。
3. 增加行为测试：空 registry、动态自定义 service_id、部分能力、全部普通能力 probe 可用、
   `speech_alignment` 未 probe/失败/可用，以及 external gate 独立保持不可用。
4. GET 仍不得发起 probe/网络调用，DTO 不新增 endpoint、Secret 或绝对路径；不修改 WebUI、旧 router、
   Pipeline、Work Order、设置 CRUD。

复验命令沿用任务契约；另需执行：

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_capabilities_api.py tests/test_service_resolver.py tests/test_m07_pr1c_acceptance.py
```

