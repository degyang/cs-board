# M09 动态信息图工作分解

状态：规划完成，待派工
日期：2026-09-05
依据：`29-voice-provider-and-infographic-plan.md` 第 5 节
约束：所有新代码禁止调用旧 `webapp/server.py`；`infographic-remotion` 在全部门禁通过前保持 `supported=false`

---

## 1. 当前 main 现状

### 1.1 已存在的基础设施

| 组件 | 位置 | 现状 |
|---|---|---|
| `Engine.INFOGRAPHIC_REMOTION` 枚举 | `csboard/domain/enums.py:8` | ✅ 已定义 |
| Remotion render.mjs | `video_renderer/render.mjs` | ✅ 已有，composition id = `DynamicInfographic`，依赖 Remotion 4.0.515 |
| Remotion src | `video_renderer/src/` | ✅ 已有 index.tsx, root.tsx, types.ts, video.tsx |
| ToolchainResolver.remotion_renderer | `csboard/runtime/toolchain.py:22` | ✅ 已检测，指向 `video_renderer/render.mjs` |
| ToolchainResolver.validate() | `csboard/runtime/toolchain.py:54` | ✅ 缺失时返回 `"remotion_renderer"` |
| CapabilityService INFOGRAPHIC 条目 | `csboard/application/capabilities.py:76-81` | ⚠️ 硬编码 `supported=False`，reason=CAPABILITY_NOT_AVAILABLE |
| Legacy bridge infographic 检测 | `csboard/application/legacy_bridge.py:120-121` | ✅ 按 `reference_mode/job_type` 判断 |
| WhiteboardRendererAdapter | `csboard/adapters/whiteboard/renderer_adapter.py` | ✅ 唯一 RendererPort 实现 |
| ProviderFactory.create_renderer() | `csboard/adapters/provider_factory.py:452-456` | ⚠️ 硬编码返回 WhiteboardRendererAdapter |
| PipelineOrchestrator STAGE_ORDER | `csboard/application/pipeline.py:22` | ✅ 线性六阶段，不区分引擎 |
| commands.py render_visuals | `csboard/application/commands.py:1443` | ⚠️ 通过 ServiceResolver 只能找到 whiteboard renderer |
| commands.py create_task | `csboard/application/commands.py:115,129` | ⚠️ 硬编码 `Engine.WHITEBOARD`，拒绝非 whiteboard |

### 1.2 未提交的进行中工作（音色 Provider，不阻塞 M09）

| 文件 | 状态 | 与 M09 关系 |
|---|---|---|
| `csboard/domain/voice_profile.py` | 新增 | 无关 |
| `csboard/application/voice_profiles.py` | 新增 | 无关 |
| `csboard/adapters/openai_compatible/tts_adapter.py` | 新增 | 无关 |
| `webapp/mountain_voice_profile_api.py` | 新增 | 无关 |
| `web-v2/src/pages/VoiceManagementPage.tsx` | 修改 | 无关 |
| `webapp/mountain_server.py` | 修改 (+2行) | 需确认无冲突 |

以上音色 Provider 变更与 M09 范围不重叠，可并行推进。

---

## 2. 工作分解（8 个包）

### WBS-1：Domain — InfographicPage 模型

**范围：** 在共享内核中定义信息图页面/节点/Cue 的领域模型，不依赖 React 或 Remotion。

| 文件 | 动作 |
|---|---|
| `csboard/domain/infographic.py` | 新增 |

**内容：**
- `InfographicPage`：page_id, title, nodes, cue_start_ms, cue_end_ms
- `InfographicNode`：node_id, kind (text/shape/image/chart), props
- `InfographicCue`：cue_id, trigger_ms, action (enter/exit/emphasize)
- `InfographicStoryboard`：pages, total_duration_ms, metadata
- `voice_units_to_pages()`：将 VoiceUnit + Timeline + Storyboard 转换为 InfographicStoryboard 的纯函数
  - 每个 Voice Unit → 1-2 个 InfographicPage
  - Visual Timing → Cue 时间点
  - 不导入 Remotion，不生成 JS

**依赖：** 无（可立即开始）
**验收：** `test_infographic_domain.py` 覆盖转换逻辑、边界条件（空 Unit、单 Visual、多 Visual）、序列化 round-trip

---

### WBS-2：Adapter — InfographicStoryboardAdapter

**范围：** 将 InfographicStoryboard 序列化为 Remotion props JSON，供 render.mjs 消费。

| 文件 | 动作 |
|---|---|
| `csboard/adapters/remotion/storyboard_adapter.py` | 新增 |
| `csboard/adapters/remotion/__init__.py` | 新增 |

**内容：**
- `InfographicStoryboardAdapter.to_remotion_props(infographic_storyboard, illustrations, audio_paths) -> dict`
  - 输出符合 `video_renderer/src/types.ts` 的 props 结构
  - 包含 pages、elements、audio、duration
  - 图片路径解析为绝对路径（相对于 run_dir）
- 不导入旧 `webapp.server`，不调用旧 `infographic_remotion_v8` 路径

**依赖：** WBS-1
**验收：** `test_infographic_storyboard_adapter.py` 覆盖单页/多页、图片引用、音频映射、props 结构合法性

---

### WBS-3：Adapter — RemotionRendererAdapter

**范围：** 实现 `RendererPort`，调用 `video_renderer/render.mjs` 生成 MP4。

| 文件 | 动作 |
|---|---|
| `csboard/adapters/remotion/renderer_adapter.py` | 新增 |

**内容：**
- `RemotionRendererAdapter(renderer_mjs: Path, node_bin: str, timeout: float)`
- `render(request: RenderRequest) -> RenderResult`：
  1. 读取 timeline/storyboard/illustration-manifact
  2. 调用 `InfographicStoryboardAdapter.to_remotion_props()`
  3. 写 props JSON 到临时文件
  4. `subprocess.run([node, render.mjs, props.json, output.mp4, public_dir])`
  5. 解析输出，返回 `RenderResult`
- `capabilities() -> RendererCapabilities`：engines=("infographic-remotion",)
- 错误统一为 `RuntimeError`，不泄露路径或命令行

**依赖：** WBS-2
**验收：** `test_remotion_renderer_adapter.py` 用 mock subprocess 覆盖成功/超时/非零退出/缺失 node

---

### WBS-4：Capability — 动态 infographic-remotion 可用性

**范围：** CapabilityService 不再硬编码 `supported=False`，改为真实检测。

| 文件 | 动作 |
|---|---|
| `csboard/application/capabilities.py` | 修改 |

**内容：**
- 新增 `INFOGRAPHIC_STAGE_REQUIREMENTS`：与白板共享 text_generation/speech_synthesis/speech_alignment/media，但 rendering 要求 `remotion` 类型
- `snapshot()` 增加 engine-aware 分支：
  - `infographic-remotion` 条目检测 Node、render.mjs、Remotion browser
  - 缺失时返回稳定 reason_code：`REMOTION_NOT_INSTALLED`、`NODE_NOT_FOUND`、`BROWSER_NOT_FOUND`、`RENDER_SCRIPT_MISSING`
- `image_generation` 仍然走 external gate（不因引擎不同而改变）

**依赖：** 无（可立即开始）
**验收：** `test_capabilities_api.py` 增加 infographic 条目的正向/反向用例，mock 缺失组件返回正确 reason_code

---

### WBS-5：API — create_task 接受 infographic-remotion

**范围：** Task 创建和 pipeline 选路支持 engine 参数。

| 文件 | 动作 |
|---|---|
| `csboard/application/commands.py` | 修改 |
| `webapp/mountain_api.py` | 修改（如存在 engine 参数路由） |

**内容：**
- `create_task()` 接受 `engine: Engine` 参数，默认 `Engine.WHITEBOARD`
- 当 `engine=INFOGRAPHIC_REMOTION` 时：
  - 检查 CapabilityService 是否返回 `supported=true`，否则 `CAPABILITY_NOT_AVAILABLE`
  - Task 持久化 engine 字段
- `_exec_render_visuals()` 根据 `task.engine` 选择 renderer：
  - `WHITEBOARD` → `ServiceResolver.resolve("rendering")` → WhiteboardRendererAdapter
  - `INFOGRAPHIC_REMOTION` → `ServiceResolver.resolve("rendering")` 或直接构造 RemotionRendererAdapter
- `_exec_plan_storyboard()` 根据 engine 选择 storyboard adapter（白板 vs 信息图）

**依赖：** WBS-3, WBS-4
**验收：** `test_infographic_task_creation.py` 覆盖 engine 参数校验、capability 检查、task 持久化 engine

---

### WBS-6：CLI — engine 选择与 remotion renderer

**范围：** CLI 命令支持 `--engine` 参数。

| 文件 | 动作 |
|---|---|
| `cli/csboard.py` | 修改 |

**内容：**
- `task create` 增加 `--engine {whiteboard,infographic-remotion}`，默认 whiteboard
- `pipeline run` / `stage run render-visuals` 根据 task.engine 自动选路
- `capabilities` 命令显示 infographic-remotion 可用性
- 输出 JSON 包含 engine 字段

**依赖：** WBS-5
**验收：** `test_cli_csboard.py` 增加 engine 参数解析、capability 显示

---

### WBS-7：测试 — fake E2E、恢复、错误脱敏

**范围：** 端到端测试覆盖 infographic 路径。

| 文件 | 动作 |
|---|---|
| `tests/test_infographic_e2e.py` | 新增 |

**内容：**
- `test_infographic_pipeline_fake_e2e`：使用 fake adapters 跑完六阶段，验证 infographic 路径产出 render-manifest
- `test_infographic_pipeline_resume`：中途失败后 resume，验证幂等性
- `test_infographic_capability_missing_node`：Node 不可用时返回正确错误码
- `test_infographic_capability_missing_browser`：无浏览器时返回正确错误码
- `test_infographic_error_sanitization`：错误消息不含完整路径、API Key
- `test_infographic_legacy_readonly`：旧 infographic 任务只读，不进入新流程
- `test_whiteboard_still_works`：白板路径回归不受 infographic 影响

**依赖：** WBS-5
**验收：** 全部测试通过，无 skip

---

### WBS-8：迁移边界 — 禁止旧路径

**范围：** 确保新 infographic 代码不调用旧 `webapp/server.py`。

| 文件 | 动作 |
|---|---|
| `tests/test_no_legacy_imports.py` | 新增（如尚不存在） |

**内容：**
- 静态检查 `csboard/adapters/remotion/` 下所有 `.py` 文件不 import `webapp.server` 或 `webapp.*`
- 静态检查 `csboard/application/capabilities.py` 不 import `webapp`
- CI gate：任何新增 adapter 不得导入旧 webapp 模块

**依赖：** 无（可立即开始）
**验收：** 测试通过

---

## 3. 依赖图与执行顺序

```
WBS-1 (Domain) ──→ WBS-2 (StoryboardAdapter) ──→ WBS-3 (RendererAdapter) ──┐
                                                                              │
WBS-4 (Capability) ──────────────────────────────────────────────────────────┤
                                                                              │
WBS-8 (Migration boundary) ──────────────────────────────────────────────────┤
                                                                              ↓
                                                            WBS-5 (API/Commands)
                                                                    │
                                                                    ↓
                                                            WBS-6 (CLI)
                                                                    │
                                                                    ↓
                                                            WBS-7 (E2E Tests)
```

**可立即并行：** WBS-1, WBS-4, WBS-8
**串行依赖：** WBS-2 → WBS-3 → WBS-5 → WBS-6 → WBS-7

---

## 4. 验收清单（对应 29 文档第 6 节）

- [ ] `InfographicStoryboardAdapter` 将 VoiceUnit/Timeline 转换为 Remotion props
- [ ] `RemotionRendererAdapter` 通过 `RendererPort` 生成 render-manifest，不导入旧 webapp
- [ ] Task/CLI/WebUI/Skills 对 `engine=infographic-remotion` 读取同一 Capability
- [ ] CapabilityService 对 Node/Remotion/Browser/RenderScript 缺失返回稳定 reason_code
- [ ] fake E2E 测试覆盖 infographic 六阶段完整路径
- [ ] 恢复/重试测试通过
- [ ] 旧 infographic 任务只读
- [ ] 错误消息脱敏
- [ ] 白板路径回归不受影响
- [ ] 所有输出进入 `outputs/<task_id>/runs/<run_id>/`

---

## 5. 不在 M09 范围

- 自定义参考风格（visual_source=custom-reference）
- 真实短文案成片验收（需要 MiMo TTS + Remotion 全链路就绪）
- 旧 webapp/server.py 删除或迁移
- 桌面端
- auto/selective 编排
